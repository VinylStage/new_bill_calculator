# 영수증 처리 애플리케이션

이 애플리케이션은 영수증 이미지에서 정보를 추출하고, 금액을 검증하며, 최적의 합계를 계산하여 CSV 파일로 정리해 줍니다.

## 🚀 시작하기

### 1. 사전 준비 (최초 1회)

*   **Python 3 설치:** 시스템에 Python 3가 설치되어 있어야 합니다.
*   **Tesseract OCR 설치:** 이미지에서 텍스트를 추출하기 위해 Tesseract OCR이 설치되어 있어야 합니다.
    *   **macOS:** 터미널에서 다음 명령어를 실행합니다.
        ```bash
        brew install tesseract tesseract-lang
        ```
    *   **Windows/Linux:** Tesseract 공식 문서(https://tesseract-ocr.github.io/tessdoc/Installation.html)를 참조하여 설치합니다.
*   **필수 Python 라이브러리 설치:** 프로젝트 루트 디렉토리에서 다음 명령어를 실행하여 필요한 라이브러리들을 설치합니다.
    ```bash
    pip install -r requirements.txt
    ```

### 2. 영수증 이미지 준비

*   처리하고자 하는 모든 영수증 이미지 파일(`.png`, `.jpg`, `.jpeg` 등)을 다음 디렉토리로 옮겨주세요.
    ```
    ./receipt_images/
    ```

### 3. 설정 확인 (선택 사항)

*   `config.py` 파일을 열어 애플리케이션의 설정을 확인하거나 변경할 수 있습니다.
    ```python
    # config.py 예시
    IMAGE_DIR = "./receipt_images"  # 영수증 이미지가 저장된 디렉토리
    OUTPUT_DIR = "./output"         # 최종 결과 CSV 파일이 저장될 디렉토리
    FINAL_CSV_NAME = "receipt_summary.csv" # 최종 CSV 파일의 이름
    BILL_LIMIT = 100000             # 계산기에서 사용할 최대 한도 금액
    ```

## 🏃‍♀️ 애플리케이션 실행

*   프로젝트 루트 디렉토리에서 다음 명령어를 실행하여 애플리케이션을 시작합니다.
    ```bash
    python3 main.py
    ```

## 📊 결과 확인

*   스크립트 실행 시 `output` 디렉토리가 자동으로 생성되며, 최종 결과 CSV 파일은 이 디렉토리에 저장됩니다.
    ```
    ./output/receipt_summary.csv
    ```
*   **중요: 금액 검증 경고**
    *   스크립트 실행 중 비정상적인 금액(예: 10만원 이상 또는 1천원 미만)이 감지되면, 해당 파일명과 함께 경고 메시지가 출력되고 스크립트가 **중단**됩니다.
    *   이 경우, 출력된 메시지를 참조하여 `receipt_images` 폴더의 원본 이미지를 확인하거나 `src/receipt_parser.py`의 `find_amount` 함수 로직을 수정해야 합니다. 수정한 후 스크립트를 다시 실행해주세요.

## 🔄 추가 영수증 처리

*   새로운 영수증이 생기면, `receipt_images` 폴더에 이미지를 넣고 `python3 main.py` 명령어를 다시 실행하기만 하면 모든 과정이 자동으로 업데이트됩니다.