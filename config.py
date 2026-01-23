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
