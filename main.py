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
    find_amount,
    detect_split_payment
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

    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="금액이 불확실해도 확인 없이 진행합니다 (자동화용)"
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


def describe_uncertainty(text, amount):
    """Returns a human-readable reason the amount deserves a look, or None if it
    looks trustworthy."""
    if not str(amount).isdigit():
        return "금액을 찾지 못했습니다."

    value = int(amount)
    if value < 1000:
        return f"금액이 비정상적으로 낮습니다: {value:,}원"
    if value > 99999:
        return f"금액이 비정상적으로 높습니다: {value:,}원"

    split = detect_split_payment(text)
    if split:
        bill_total, charged = split
        return (f"분할 결제로 보입니다. 영수증 전체는 {bill_total:,}원이고 "
                f"이 카드 승인분은 {charged:,}원입니다.")
    return None


def review_amount(filename, amount, reason):
    """Asks the user to confirm, correct, or skip a receipt whose amount is uncertain.

    Returns the amount to use, or None to leave the receipt out entirely."""
    print(f"\n  [확인 필요] {filename}")
    print(f"  → {reason}")
    while True:
        try:
            answer = input("  이 금액으로 진행할까요? [Y=진행 / n=이 영수증 제외 / 숫자=금액 직접 입력]: ").strip()
        except (EOFError, KeyboardInterrupt):
            # Not attached to a terminal (piped, cron): keep the detected value.
            print()
            logging.info(f"    입력을 받을 수 없어 감지된 금액({amount})을 그대로 사용합니다.")
            return amount

        if answer == "" or answer.lower() in ("y", "yes"):
            return amount
        if answer.lower() in ("n", "no"):
            return None

        digits = answer.replace(",", "").replace("원", "").strip()
        if digits.isdigit():
            return digits
        print("  Y, n, 또는 금액(숫자)을 입력해주세요.")


def validate_amounts(df):
    """Validates that all amounts are within a reasonable range."""
    min_amount = 1000
    max_amount = 99999

    invalid_amounts_df = df[(df['Amount'] < min_amount) | (df['Amount'] > max_amount)]

    if not invalid_amounts_df.empty:
        logging.error("=" * 60)
        logging.error("  영수증 인식에 실패한 파일이 있습니다.")
        logging.error("  아래 파일을 다시 촬영하여 교체해주세요.")
        logging.error("=" * 60)
        for _, row in invalid_amounts_df.iterrows():
            amount = row['Amount']
            if amount == 0:
                reason = "금액을 전혀 읽을 수 없었습니다 (이미지가 너무 흐리거나 글자가 잘렸을 수 있습니다)"
            elif amount < min_amount:
                reason = f"금액이 너무 낮게 추출되었습니다 (추출값: {amount}원 / OCR 오인식으로 추정됩니다)"
            else:
                reason = f"금액이 비정상적으로 높게 추출되었습니다 (추출값: {amount:,}원 / OCR 오인식으로 추정됩니다)"
            logging.error(f"\n  [재촬영 필요] {row['Filename']}")
            logging.error(f"  → {reason}")
            logging.error(f"  → 영수증 전체가 선명하게 나오도록, 정면에서 가까이 촬영해주세요.")
        logging.error("\n" + "=" * 60)
        logging.error("  위 파일 교체 후 다시 실행해주세요.")
        logging.error("=" * 60)
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
    interactive = not args.non_interactive

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

        override = config.AMOUNT_OVERRIDES.get(filename)
        if override is not None:
            logging.info(f"    수동 지정 금액 적용: {amount} → {override:,}원")
            amount = str(override)
        elif interactive:
            reason = describe_uncertainty(text, amount)
            if reason:
                amount = review_amount(filename, amount, reason)
                if amount is None:
                    logging.info(f"    사용자 요청으로 {filename} 을(를) 제외했습니다.")
                    continue

        all_receipt_data.append([filename, date, time, amount, receipt_type])
        logging.debug(f"    날짜: {date}, 시간: {time}, 금액: {amount}, 유형: {receipt_type}")

    df = pd.DataFrame(all_receipt_data, columns=['Filename', 'Date', 'Time', 'Amount', 'Type'])
    df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0).astype(int)

    if not validate_amounts(df):
        sys.exit(1)

    logging.info("--- 2. 데이터 정렬 ---")
    # Create DateTime column for proper sorting
    df['DateTime'] = df['Date'] + ' ' + df['Time']
    df.sort_values(by='DateTime', inplace=True)
    df.reset_index(drop=True, inplace=True)
    # Temporary index for knapsack calculation
    df.insert(0, 'TempIdx', range(1, 1 + len(df)))

    logging.info("--- 3. 최적 합계 계산 (Knapsack) ---")
    calc_df = df[['TempIdx', 'Amount']].copy()
    calc_df.rename(columns={'TempIdx': 'Item'}, inplace=True)

    best_sum, included_ids = solve_knapsack(calc_df, bill_limit)
    all_ids = set(df['TempIdx'].tolist())
    excluded_ids = all_ids - set(included_ids)

    logging.info(f"  - 최적 합계: {best_sum:,}원")
    logging.info(f"  - 제외될 항목: {len(excluded_ids)}개")

    # Mark excluded items
    df['제외유무'] = df['TempIdx'].apply(lambda x: 'Y' if x in excluded_ids else 'N')

    # Split into included and excluded DataFrames
    df_included = df[df['제외유무'] == 'N'].copy()
    df_excluded = df[df['제외유무'] == 'Y'].copy()

    logging.info("--- 4. 포함 항목 번호 매기기 및 파일 이름 변경 ---")
    # Number only included items (1, 2, 3...)
    df_included['No.'] = range(1, 1 + len(df_included))

    # Rename only included files
    df_included = rename_receipt_files(df_included, input_dir, do_rename, do_backup, dry_run)

    # Excluded items: no number, keep original filename
    df_excluded['No.'] = ''

    # Combine: included first, then excluded at bottom
    df = pd.concat([df_included, df_excluded], ignore_index=True)

    # Drop temporary columns
    df.drop(columns=['TempIdx', 'DateTime'], inplace=True)

    # Reorder columns: No. first
    cols = ['No.', 'Filename', 'Date', 'Time', 'Amount', 'Type', '제외유무']
    df = df[cols]

    logging.info("--- 5. 최종 결과 생성 ---")

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
