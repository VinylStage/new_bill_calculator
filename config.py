# -*- coding: utf-8 -*-

# --- 경로 설정 ---
# 영수증 이미지가 저장된 디렉토리
IMAGE_DIR = "./receipt_images"

# 최종 결과 CSV 파일이 저장될 디렉토리
OUTPUT_DIR = "./output"

# 저장될 최종 CSV 파일의 이름
FINAL_CSV_NAME = "receipt_summary.csv"


# --- 계산기 설정 ---
# 계산기에서 사용할 최대 한도 금액
BILL_LIMIT = 100000


# --- OCR 설정 ---
# 고정확도 tessdata 모델 디렉토리 (None이면 시스템 기본 모델 사용)
TESSDATA_DIR = "./tessdata"

# 이미지의 짧은 변이 이 값보다 작으면 OCR 전에 확대합니다
OCR_MIN_SHORT_SIDE = 1000

# 확대 배율 상한
OCR_MAX_UPSCALE = 3


# --- 금액 수동 지정 ---
# OCR이 금액을 잘못 읽는 영수증은 파일명을 키로 실제 금액을 직접 지정합니다.
# 분할 결제(더치페이)에서 본인 카드 승인분이 자동으로 잡히지 않을 때 사용하세요.
# 예: AMOUNT_OVERRIDES = {"paper-8.jpg": 11000}
AMOUNT_OVERRIDES = {}


# --- 로깅 설정 ---
# 로그 파일이 저장될 디렉토리
LOG_DIR = "logs"

# 어플리케이션의 로깅 레벨 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
LOG_LEVEL = "DEBUG"


# --- 파일 이름 변경 설정 ---
# 파일 이름 변경 기능 활성화 여부
RENAME_FILES = True

# 원본 파일 백업 여부
BACKUP_ORIGINAL = True

# 원본 파일 백업 디렉토리
BACKUP_DIR = "./receipt_images_backup"
