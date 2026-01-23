# 영수증 처리 애플리케이션

영수증 이미지에서 정보를 추출하고, 한도 금액 내 최적 조합을 계산하여 CSV 파일로 정리합니다.

## 주요 기능

- **OCR 텍스트 추출**: 영수증 이미지에서 텍스트 자동 추출
- **날짜/시간 인식**: 영수증의 날짜와 시간을 추출하여 시간순 정렬
- **최적 합계 계산**: Knapsack 알고리즘으로 한도 내 최적 조합 계산
- **자동 파일 이름 변경**: 포함된 영수증만 1, 2, 3... 번호로 파일명 변경
- **원본 백업**: 파일 이름 변경 전 원본 자동 백업
- **CLI 지원**: 다양한 명령줄 옵션 제공

## 시작하기

### 1. 사전 준비 (최초 1회)

* **Python 3.13+**: 시스템에 Python 3.13 이상이 설치되어 있어야 합니다.
* **Tesseract OCR 설치:**
    * **macOS:**
        ```bash
        brew install tesseract tesseract-lang
        ```
    * **Windows/Linux:** [Tesseract 공식 문서](https://tesseract-ocr.github.io/tessdoc/Installation.html) 참조
* **Poetry로 의존성 설치:**
    ```bash
    poetry install --no-root
    ```

### 2. 영수증 이미지 준비

처리할 영수증 이미지 파일(`.png`, `.jpg`, `.jpeg`)을 다음 디렉토리에 넣으세요:
```
./receipt_images/
```

### 3. 설정 확인 (선택 사항)

`config.py` 파일에서 설정을 변경할 수 있습니다:
```python
# 경로 설정
IMAGE_DIR = "./receipt_images"          # 영수증 이미지 디렉토리
OUTPUT_DIR = "./output"                 # 결과 출력 디렉토리
FINAL_CSV_NAME = "receipt_summary.csv"  # 최종 CSV 파일명

# 계산기 설정
BILL_LIMIT = 100000                     # 최대 한도 금액

# 로깅 설정
LOG_DIR = "logs"                        # 로그 디렉토리
LOG_LEVEL = "DEBUG"                     # 로그 레벨

# 파일 이름 변경 설정
RENAME_FILES = True                     # 파일 이름 변경 활성화
BACKUP_ORIGINAL = True                  # 원본 백업 활성화
BACKUP_DIR = "./receipt_images_backup"  # 백업 디렉토리
```

## 실행 방법

### 기본 실행

```bash
poetry run python main.py
```

### CLI 옵션

```
usage: receipt-calculator [-h] [-V] [-v | -q] [-i DIR] [-o DIR]
                          [--no-rename] [--no-backup] [-l AMOUNT] [--dry-run]

옵션:
  -h, --help            도움말 표시
  -V, --version         버전 정보 출력
  -v, --verbose         상세한 로그 출력 (DEBUG 레벨)
  -q, --quiet           최소 출력 (에러만)
  -i, --input-dir DIR   영수증 이미지 디렉토리
  -o, --output-dir DIR  결과 출력 디렉토리
  -l, --limit AMOUNT    최대 한도 금액
  --no-rename           파일 이름 변경 건너뛰기
  --no-backup           원본 백업 건너뛰기
  --dry-run             시뮬레이션 모드 (실제 변경 없음)
```

### 사용 예시

```bash
# 기본 실행
poetry run python main.py

# 상세 로그 출력
poetry run python main.py -v

# 시뮬레이션 (파일 변경 없음)
poetry run python main.py --dry-run

# 한도 금액 5만원으로 설정
poetry run python main.py --limit 50000

# 사용자 지정 디렉토리
poetry run python main.py -i ./my_images -o ./my_output
```

## 처리 흐름

```
1. 영수증 이미지 OCR
2. 날짜 + 시간 추출
3. 날짜+시간 기준 정렬
4. 최적 합계 계산 (Knapsack) → 제외 항목 결정
5. 포함 항목만 번호 매기기 (1, 2, 3...)
6. 포함 항목만 파일 이름 변경 (원본 백업 후)
7. CSV 출력 (포함 항목 → 제외 항목 순서)
```

## 파일명 변경 규칙

**포함된 영수증 (제외유무=N)**
- 시간순으로 1.PNG, 2.PNG, 3.PNG... 로 이름 변경
- 원본은 `receipt_images_backup/`에 백업

**제외된 영수증 (제외유무=Y)**
- 원본 파일명 유지 (예: IMG_6204.PNG)
- CSV에서 맨 아래에 배치, 번호 없음

```
예시:
IMG_6203.PNG  →  1.PNG   (포함, 1월 6일)
IMG_6207.PNG  →  2.PNG   (포함, 1월 13일)
IMG_6204.PNG  →  IMG_6204.PNG (제외, 원본 유지)
```

## 결과 확인

### CSV 파일

```
./output/receipt_summary.csv
```

| No. | Filename | Date | Time | Amount | Type | 제외유무 |
|-----|----------|------|------|--------|------|---------|
| 1 | 1.PNG | 1월 6일 | 12:40:40 | 12000 | 하나카드 | N |
| 2 | 2.PNG | 1월 13일 | 12:24:41 | 14500 | 하나카드 | N |
| ... | ... | ... | ... | ... | ... | ... |
| | IMG_6204.PNG | 1월 7일 | 11:53:19 | 10500 | 하나카드 | Y |

### 기타 출력

- **원본 백업**: `./receipt_images_backup/`
- **로그 파일**: `./logs/YYYYMMDD-HHMMSS-debug.log`

## 금액 검증

비정상적인 금액(10만원 이상 또는 1천원 미만) 감지 시:
1. 경고 메시지 출력
2. 스크립트 중단
3. `logs/` 폴더의 로그 파일에서 OCR 결과 확인

## 지원 영수증 유형

- 커피빈 앱 영수증
- 스타벅스 앱 영수증
- 하나카드 앱 영수증
- 신한카드 앱 영수증
- 삼성카드 앱 영수증

## 의존성

- Python 3.13+
- pandas
- Pillow
- Tesseract OCR (시스템 설치 필요)

## 지원 OS

- Apple Silicon macOS
