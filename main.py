# -*- coding: utf-8 -*-
import os
import sys
import logging
import argparse
from datetime import datetime
import pandas as pd
import shutil
from src.receipt_parser import (
    extract_text_from_image,
    classify_receipt,
    find_date,
    find_time,
    find_amount
)
from src.bill_calculator import solve_knapsack
import config

__version__ = "1.0.0"


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        prog="receipt-calculator",
        description="영수증 이미지에서 정보를 추출하고 최적 합계를 계산합니다.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  python main.py                      기본 실행
  python main.py -v                   상세 로그 출력
  python main.py -q                   출력 최소화
  python main.py -i ./images -o ./out 사용자 지정 디렉토리
  python main.py --no-rename          파일 이름 변경 건너뛰기
  python main.py --limit 50000        한도 금액 설정
        """
    )

    # Version
    parser.add_argument(
        "-V", "--version",
        action="version",
        version=f"%(prog)s {__version__}"
    )

    # Verbosity options (mutually exclusive)
    verbosity = parser.add_mutually_exclusive_group()
    verbosity.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="상세한 로그를 콘솔에 출력합니다"
    )
    verbosity.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="콘솔 출력을 최소화합니다 (에러만 출력)"
    )

    # Directory options
    parser.add_argument(
        "-i", "--input-dir",
        type=str,
        default=config.IMAGE_DIR,
        metavar="DIR",
        help=f"영수증 이미지 디렉토리 (기본값: {config.IMAGE_DIR})"
    )
    parser.add_argument(
        "-o", "--output-dir",
        type=str,
        default=config.OUTPUT_DIR,
        metavar="DIR",
        help=f"결과 출력 디렉토리 (기본값: {config.OUTPUT_DIR})"
    )

    # Processing options
    parser.add_argument(
        "--no-rename",
        action="store_true",
        help="파일 이름 변경을 건너뜁니다"
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="원본 파일 백업을 건너뜁니다"
    )
    parser.add_argument(
        "-l", "--limit",
        type=int,
        default=config.BILL_LIMIT,
        metavar="AMOUNT",
        help=f"최대 한도 금액 (기본값: {config.BILL_LIMIT})"
    )

    # Dry run
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="실제 파일 변경 없이 시뮬레이션만 수행합니다"
    )

    return parser.parse_args()

def setup_logging(verbose=False, quiet=False):
    """Configures logging with optional console output based on verbosity."""
    log_level_map = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL
    }

    # Get log level from config, default to INFO if invalid
    log_level_str = config.LOG_LEVEL.upper()
    log_level = log_level_map.get(log_level_str, logging.INFO)

    # Create logs directory
    os.makedirs(config.LOG_DIR, exist_ok=True)

    # Generate timestamp for log files
    timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')

    # Standard log format for files
    file_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(funcName)s - %(message)s')
    # Simpler format for console
    console_format = logging.Formatter('%(message)s')

    # Get root logger and clear existing handlers
    root_logger = logging.getLogger('')
    root_logger.handlers = []
    root_logger.setLevel(logging.DEBUG)  # Capture all, filter at handler level

    # General debug log file handler
    debug_log_path = os.path.join(config.LOG_DIR, f"{timestamp}-debug.log")
    debug_handler = logging.FileHandler(debug_log_path, encoding='utf-8')
    debug_handler.setLevel(log_level)
    debug_handler.setFormatter(file_format)
    root_logger.addHandler(debug_handler)

    # Error-specific log file handler
    error_log_path = os.path.join(config.LOG_DIR, f"{timestamp}-error.log")
    error_handler = logging.FileHandler(error_log_path, encoding='utf-8')
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(file_format)
    root_logger.addHandler(error_handler)

    # Console handler based on verbosity
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_format)

    if quiet:
        console_handler.setLevel(logging.ERROR)
    elif verbose:
        console_handler.setLevel(logging.DEBUG)
    else:
        console_handler.setLevel(logging.INFO)

    root_logger.addHandler(console_handler)


def rename_receipt_files(df, input_dir, do_rename=True, do_backup=True, dry_run=False):
    """Renames receipt files based on their sorted order (1, 2, 3...)."""
    if not do_rename:
        logging.info("  - 파일 이름 변경 기능이 비활성화되어 있습니다.")
        return df

    # Backup original files if enabled
    if do_backup:
        os.makedirs(config.BACKUP_DIR, exist_ok=True)
        logging.info(f"  - 원본 파일을 {config.BACKUP_DIR}에 백업 중...")
        if not dry_run:
            for _, row in df.iterrows():
                original_path = os.path.join(input_dir, row['Filename'])
                backup_path = os.path.join(config.BACKUP_DIR, row['Filename'])
                if os.path.exists(original_path):
                    shutil.copy2(original_path, backup_path)
        logging.info("  - 백업 완료")

    if dry_run:
        logging.info("  - [DRY-RUN] 파일 이름 변경을 시뮬레이션합니다...")
        new_filenames = []
        for idx, row in df.iterrows():
            _, ext = os.path.splitext(row['Filename'])
            final_name = f"{row['No.']}{ext}"
            new_filenames.append(final_name)
            logging.info(f"  - [DRY-RUN] {row['Filename']} → {final_name}")
        df['Filename'] = new_filenames
        return df

    # Step 1: Rename to temporary names to avoid conflicts
    temp_mappings = []
    for idx, row in df.iterrows():
        original_filename = row['Filename']
        original_path = os.path.join(input_dir, original_filename)
        _, ext = os.path.splitext(original_filename)
        temp_name = f"_temp_{row['No.']}{ext}"
        temp_path = os.path.join(input_dir, temp_name)
        if os.path.exists(original_path):
            os.rename(original_path, temp_path)
            temp_mappings.append((temp_path, row['No.'], ext, original_filename))

    # Step 2: Rename from temporary names to final names
    new_filenames = []
    for temp_path, no, ext, original_filename in temp_mappings:
        final_name = f"{no}{ext}"
        final_path = os.path.join(input_dir, final_name)
        os.rename(temp_path, final_path)
        new_filenames.append(final_name)
        logging.info(f"  - 파일 이름 변경: {original_filename} → {final_name}")

    # Update the Filename column in DataFrame
    df['Filename'] = new_filenames
    logging.info("  - 파일 이름 변경 완료")

    return df


def validate_amounts(df):
    """Validates that all amounts are within a reasonable range."""
    min_amount = 1000
    max_amount = 99999

    invalid_amounts_df = df[(df['Amount'] < min_amount) | (df['Amount'] > max_amount)]

    if not invalid_amounts_df.empty:
        logging.error("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        logging.error("!!! 경고: 비정상적인 금액이 감지되어 작업을 중단합니다.")
        logging.error("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        logging.error("\n아래 파일들의 금액을 확인하고 수동으로 수정해야 합니다.")
        logging.error("문제가 되는 파일:")
        for _, row in invalid_amounts_df.iterrows():
            logging.error(f"  - 파일명: {row['Filename']}, 추출된 금액: {row['Amount']}원")
        
        logging.error("\n[조치 방법]")
        logging.error(f"1. `{config.LOG_DIR}` 폴더에 생성된 최신 로그 파일(*-debug.log)을 열어 OCR로 추출된 전체 텍스트를 확인하세요.")
        logging.error("2. `src/receipt_parser.py`의 금액 추출 로직을 디버깅하거나 수정하세요.")
        logging.error("3. 또는, 원본 이미지 파일의 해상도를 개선하거나 노이즈를 제거하세요.")
        logging.error("4. 수정한 후, 이 스크립트를 다시 실행해주세요.")
        return False
    
    logging.info("--- 1.5. 금액 검증 완료 ---")
    logging.info("  - 모든 금액이 정상 범위 내에 있습니다. 다음 단계를 계속 진행합니다.")
    return True

def process_all_receipts(args):
    """Main function to orchestrate the entire receipt processing workflow."""
    input_dir = args.input_dir
    output_dir = args.output_dir
    bill_limit = args.limit
    do_rename = not args.no_rename and config.RENAME_FILES
    do_backup = not args.no_backup and config.BACKUP_ORIGINAL
    dry_run = args.dry_run

    os.makedirs(output_dir, exist_ok=True)

    if dry_run:
        logging.info(">>> [DRY-RUN 모드] 실제 파일 변경 없이 시뮬레이션합니다.")

    logging.info("--- 1. 영수증 정보 추출 시작 ---")
    logging.info(f"  - 입력 디렉토리: {input_dir}")
    logging.info(f"  - 출력 디렉토리: {output_dir}")
    logging.info(f"  - 한도 금액: {bill_limit:,}원")

    image_files = [f for f in os.listdir(input_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]

    if not image_files:
        logging.warning(f"{input_dir} 에서 이미지 파일을 찾을 수 없습니다.")
        return

    logging.info(f"  - 발견된 이미지: {len(image_files)}개")

    all_receipt_data = []
    for filename in image_files:
        image_path = os.path.join(input_dir, filename)
        logging.info(f"  - 처리 중: {filename}")
        text = extract_text_from_image(image_path)
        if not text:
            continue

        receipt_type = classify_receipt(text)
        date = find_date(text)
        time = find_time(text)
        amount = find_amount(text, receipt_type)
        all_receipt_data.append([filename, date, time, amount, receipt_type])
        logging.debug(f"    날짜: {date}, 시간: {time}, 금액: {amount}, 유형: {receipt_type}")

    df = pd.DataFrame(all_receipt_data, columns=['Filename', 'Date', 'Time', 'Amount', 'Type'])
    df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0).astype(int)

    if not validate_amounts(df):
        sys.exit(1)

    logging.info("--- 2. 데이터 정렬 및 번호 매기기 ---")
    # Create DateTime column for proper sorting
    df['DateTime'] = df['Date'] + ' ' + df['Time']
    df.sort_values(by='DateTime', inplace=True)
    df.reset_index(drop=True, inplace=True)
    df.insert(0, 'No.', range(1, 1 + len(df)))
    # Drop the temporary DateTime column
    df.drop(columns=['DateTime'], inplace=True)

    logging.info("--- 2.5. 파일 이름 변경 ---")
    df = rename_receipt_files(df, input_dir, do_rename, do_backup, dry_run)

    logging.info("--- 3. 최적 합계 계산 (Knapsack) ---")
    calc_df = df[['No.', 'Amount']].copy()
    calc_df.rename(columns={'No.': 'Item'}, inplace=True)

    best_sum, included_ids = solve_knapsack(calc_df, bill_limit)
    all_ids = set(df['No.'].tolist())
    excluded_ids = all_ids - set(included_ids)

    logging.info(f"  - 최적 합계: {best_sum:,}원")
    logging.info(f"  - 제외될 항목 No.: {sorted(list(excluded_ids))}")

    logging.info("--- 4. 최종 결과 생성 ---")
    df['제외유무'] = df['No.'].apply(lambda x: 'Y' if x in excluded_ids else 'N')

    # Convert date format to Korean style (1월 6일) for report
    df['Date'] = pd.to_datetime(df['Date']).apply(lambda x: f"{x.month}월 {x.day}일")

    output_path = os.path.join(output_dir, config.FINAL_CSV_NAME)
    if not dry_run:
        df.to_csv(output_path, index=False, encoding='utf-8-sig')

    logging.info(f"\n>>> 작업 완료! 최종 결과가 다음 파일에 저장되었습니다:")
    logging.info(f">>> {output_path}")


def main():
    """Entry point for the CLI."""
    args = parse_args()
    setup_logging(verbose=args.verbose, quiet=args.quiet)
    process_all_receipts(args)


if __name__ == "__main__":
    main()
