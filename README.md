# 영수증 처리 애플리케이션

이 애플리케이션은 영수증 이미지에서 정보를 추출하고, 금액을 검증하며, 최적의 합계를 계산하여 CSV 파일로 정리해 줍니다.

## 주요 기능

- **OCR 텍스트 추출**: 영수증 이미지에서 텍스트 자동 추출
- **날짜/시간 인식**: 영수증의 날짜와 시간을 추출하여 시간순 정렬
- **자동 파일 이름 변경**: 시간순으로 1, 2, 3... 번호로 파일 이름 자동 변경
- **원본 백업**: 파일 이름 변경 전 원본 자동 백업
- **최적 합계 계산**: Knapsack 알고리즘으로 한도 내 최적 조합 계산
- **CLI 지원**: 다양한 명령줄 옵션 제공

## 시작하기

### 1. 사전 준비 (최초 1회)

* **Python 3 설치:** 시스템에 Python 3가 설치되어 있어야 합니다.
* **Tesseract OCR 설치:** 이미지에서 텍스트를 추출하기 위해 Tesseract OCR이 설치되어 있어야 합니다.
    * **macOS:** 터미널에서 다음 명령어를 실행합니다.
        ```bash
        brew install tesseract tesseract-lang
        ```
    * **Windows/Linux:** Tesseract 공식 문서(https://tesseract-ocr.github.io/tessdoc/Installation.html)를 참조하여 설치합니다.
* **필수 Python 라이브러리 설치:** Poetry를 사용하여 의존성을 설치합니다.
    ```bash
    poetry install --no-root
    ```

### 2. 영수증 이미지 준비

* 처리하고자 하는 모든 영수증 이미지 파일(`.png`, `.jpg`, `.jpeg`)을 다음 디렉토리로 옮겨주세요.
    ```
    ./receipt_images/
    ```

### 3. 설정 확인 (선택 사항)

* `config.py` 파일을 열어 애플리케이션의 설정을 확인하거나 변경할 수 있습니다.
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

## 애플리케이션 실행

### 기본 실행

```bash
poetry run python main.py
```

### CLI 옵션

```
usage: receipt-calculator [-h] [-V] [-v | -q] [-i DIR] [-o DIR]
                          [--no-rename] [--no-backup] [-l AMOUNT] [--dry-run]

영수증 이미지에서 정보를 추출하고 최적 합계를 계산합니다.

옵션:
  -h, --help            도움말 표시
  -V, --version         버전 정보 출력
  -v, --verbose         상세한 로그를 콘솔에 출력합니다
  -q, --quiet           콘솔 출력을 최소화합니다 (에러만 출력)
  -i, --input-dir DIR   영수증 이미지 디렉토리 (기본값: ./receipt_images)
  -o, --output-dir DIR  결과 출력 디렉토리 (기본값: ./output)
  --no-rename           파일 이름 변경을 건너뜁니다
  --no-backup           원본 파일 백업을 건너뜁니다
  -l, --limit AMOUNT    최대 한도 금액 (기본값: 100000)
  --dry-run             실제 파일 변경 없이 시뮬레이션만 수행합니다
```

### 사용 예시

```bash
# 기본 실행
poetry run python main.py

# 상세 로그 출력
poetry run python main.py -v

# 조용한 모드 (에러만 출력)
poetry run python main.py -q

# 시뮬레이션 (실제 파일 변경 없음)
poetry run python main.py --dry-run

# 한도 금액 5만원으로 설정
poetry run python main.py --limit 50000

# 사용자 지정 디렉토리
poetry run python main.py -i ./my_images -o ./my_output

# 파일 이름 변경 없이 실행
poetry run python main.py --no-rename
```

## 처리 흐름

```
1. 영수증 이미지 OCR
2. 날짜 + 시간 추출
3. 날짜+시간 기준 정렬 (빠른 순)
4. 번호 매기기 (1, 2, 3...)
5. 원본 백업 → 파일 이름 변경
6. 최적 합계 계산 (Knapsack)
7. CSV 출력
```

## 파일명 변경 예시

```
원본               정렬 후 시간순
IMG_6203.PNG  →   1.PNG   (2026-01-06 09:30)
IMG_6207.PNG  →   2.PNG   (2026-01-06 14:22)
IMG_6204.PNG  →   3.PNG   (2026-01-07 11:45)
```

## 결과 확인

* 최종 결과 CSV 파일:
    ```
    ./output/receipt_summary.csv
    ```
* CSV 파일 컬럼:
    - `No.`: 시간순 번호
    - `Filename`: 파일명 (변경 후)
    - `Date`: 날짜
    - `Time`: 시간
    - `Amount`: 금액
    - `Type`: 영수증 유형
    - `제외유무`: 최적 합계에서 제외 여부 (Y/N)

* 원본 파일 백업:
    ```
    ./receipt_images_backup/
    ```

* 로그 파일:
    ```
    ./logs/YYYYMMDD-HHMMSS-debug.log
    ./logs/YYYYMMDD-HHMMSS-error.log
    ```

## 금액 검증 경고

스크립트 실행 중 비정상적인 금액(10만원 이상 또는 1천원 미만)이 감지되면:
1. 해당 파일명과 함께 경고 메시지가 출력됩니다
2. 스크립트가 **중단**됩니다
3. `logs` 폴더의 로그 파일을 확인하여 OCR 결과를 검토하세요

## 지원되는 영수증 유형

* 커피빈 앱 영수증
* 스타벅스 앱 영수증
* 하나카드 앱 영수증
* 신한카드 앱 영수증
* 삼성카드 앱 영수증

## 지원되는 OS

* Apple Silicon macOS
