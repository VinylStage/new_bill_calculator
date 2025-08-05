# -*- coding: utf-8 -*-
import os
import sys
import pandas as pd
from src.receipt_parser import (
    extract_text_from_image,
    classify_receipt,
    find_date,
    find_amount
)
from src.bill_calculator import solve_knapsack
import config

def validate_amounts(df):
    """Validates that all amounts are within a reasonable range."""
    min_amount = 1000
    max_amount = 99999

    invalid_amounts_df = df[(df['Amount'] < min_amount) | (df['Amount'] > max_amount)]

    if not invalid_amounts_df.empty:
        print("\n!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print("!!! 경고: 비정상적인 금액이 감지되어 작업을 중단합니다.")
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print("\n아래 파일들의 금액을 확인하고 수동으로 수정해야 합니다.")
        print("문제가 되는 파일:")
        for _, row in invalid_amounts_df.iterrows():
            print(f"  - 파일명: {row['Filename']}, 추출된 금액: {row['Amount']}원")
        
        print("\n[조치 방법]")
        print("1. `src/receipt_parser.py`의 금액 추출 로직을 수정하세요.")
        print("2. 또는, 원본 이미지 파일의 해상도를 개선하거나 노이즈를 제거하세요.")
        print("3. 수정한 후, 이 스크립트를 다시 실행해주세요.")
        return False
    
    print("\n--- 1.5. 금액 검증 완료 ---")
    print("  - 모든 금액이 정상 범위 내에 있습니다. 다음 단계를 계속 진행합니다.")
    return True

def process_all_receipts():
    """Main function to orchestrate the entire receipt processing workflow."""
    # Ensure output directory exists
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)

    print("--- 1. 영수증 정보 추출 시작 ---")
    image_files = [f for f in os.listdir(config.IMAGE_DIR) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    
    if not image_files:
        print(f"{config.IMAGE_DIR} 에서 이미지 파일을 찾을 수 없습니다.")
        return

    all_receipt_data = []
    for filename in image_files:
        image_path = os.path.join(config.IMAGE_DIR, filename)
        print(f"  - 처리 중: {filename}")
        text = extract_text_from_image(image_path)
        if not text:
            continue

        receipt_type = classify_receipt(text)
        date = find_date(text)
        amount = find_amount(text, receipt_type)
        all_receipt_data.append([filename, date, amount, receipt_type])

    df = pd.DataFrame(all_receipt_data, columns=['Filename', 'Date', 'Amount', 'Type'])
    df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0).astype(int)

    if not validate_amounts(df):
        sys.exit(1)

    print("\n--- 2. 데이터 정렬 및 번호 매기기 ---")
    df.sort_values(by='Date', inplace=True)
    df.insert(0, 'No.', range(1, 1 + len(df)))

    print("--- 3. 최적 합계 계산 (Knapsack) ---")
    calc_df = df[['No.', 'Amount']].copy()
    calc_df.rename(columns={'No.': 'Item'}, inplace=True)

    best_sum, included_ids = solve_knapsack(calc_df, config.BILL_LIMIT)
    all_ids = set(df['No.'].tolist())
    excluded_ids = all_ids - set(included_ids)

    print(f"  - 최적 합계: {best_sum}")
    print(f"  - 제외될 항목 No.: {sorted(list(excluded_ids))}")

    print("--- 4. 최종 결과 생성 ---")
    df['제외유무'] = df['No.'].apply(lambda x: 'Y' if x in excluded_ids else 'N')

    output_path = os.path.join(config.OUTPUT_DIR, config.FINAL_CSV_NAME)
    df.to_csv(output_path, index=False, encoding='utf-8-sig')

    print(f"\n>>> 작업 완료! 최종 결과가 다음 파일에 저장되었습니다:")
    print(f">>> {output_path}")

if __name__ == "__main__":
    process_all_receipts()
