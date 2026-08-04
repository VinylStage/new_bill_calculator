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
* **Tesseract OCR 5.x 설치**: 아래 [OS별 설치 가이드](#tesseract-ocr-설치-가이드) 참조
* **고정확도 한국어 모델 다운로드**: 아래 [고정확도 모델 설치](#고정확도-모델-tessdata_best-설치) 참조
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

# OCR 설정
TESSDATA_DIR = "./tessdata"             # 고정확도 모델 경로 (None이면 시스템 기본)
OCR_MIN_SHORT_SIDE = 1000               # 이보다 작은 이미지는 OCR 전에 확대
OCR_MAX_UPSCALE = 3                     # 확대 배율 상한

# 금액 수동 지정 (OCR이 못 맞히는 영수증)
AMOUNT_OVERRIDES = {}                   # 예: {"paper-8.jpg": 11000}
```

## 실행 방법

### 기본 실행

```bash
poetry run python main.py
```

### CLI 옵션

```
usage: receipt-calculator [-h] [-V] [-v | -q] [-i DIR] [-o DIR]
                          [--no-rename] [--no-backup] [-l AMOUNT]
                          [--non-interactive] [--dry-run]

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
  --non-interactive     금액 확인 없이 진행 (자동화용)
  --dry-run             시뮬레이션 모드 (실제 변경 없음)
```

### 금액 확인 (인터랙티브)

금액이 불확실한 영수증을 만나면 실행 중에 확인을 요청합니다.

```
  [확인 필요] paper-8.jpg
  → 분할 결제로 보입니다. 영수증 전체는 33,500원이고 이 카드 승인분은 11,000원입니다.
  이 금액으로 진행할까요? [Y=진행 / n=이 영수증 제외 / 숫자=금액 직접 입력]:
```

| 입력 | 동작 |
|---|---|
| `Y`, `y`, 엔터 | 감지된 금액으로 진행 |
| `n`, `N` | **이 영수증을 목록에서 제외**하고 계속 진행 |
| `11000` 같은 숫자 | 입력한 금액으로 대체 (`11,000`, `11000원` 형태도 인식) |

확인을 요청하는 경우는 다음 세 가지입니다.

- 분할 결제로 감지된 경우
- 금액을 전혀 찾지 못한 경우
- 금액이 1,000원 미만이거나 100,000원 이상인 경우

`--non-interactive` 를 주면 확인 없이 감지된 금액으로 진행합니다. 파이프·cron 등 입력을 받을 수 없는 환경에서도 자동으로 감지된 금액을 사용합니다.

매번 같은 값을 입력하기 번거로우면 `config.py`의 `AMOUNT_OVERRIDES`에 미리 지정해둘 수 있습니다. 지정된 파일은 확인을 건너뜁니다.

```python
AMOUNT_OVERRIDES = {
    "paper-8.jpg": 11000,
}
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
1. 이미지 전처리 (작은 이미지는 확대 + 샤프닝) 후 OCR
2. 영수증 유형 분류 → 유형별 로직으로 날짜 / 시간 / 금액 추출
3. 금액이 불확실하면 사용자에게 확인 (인터랙티브)
4. 금액 검증 (1,000원 ~ 100,000원)
5. 날짜+시간 기준 정렬
6. 최적 합계 계산 (Knapsack) → 제외 항목 결정
7. 포함 항목만 번호 매기기 (1, 2, 3...)
8. 포함 항목만 파일 이름 변경 (원본 백업 후)
9. CSV 출력 (포함 항목 → 제외 항목 순서)
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

정상 범위는 **1,000원 이상 100,000원 미만**입니다.

기본(인터랙티브) 모드에서는 범위를 벗어난 금액을 발견하면 실행 중에 확인을 요청합니다. 이 자리에서 올바른 금액을 입력하거나 `n`으로 해당 영수증을 제외하면 그대로 진행됩니다. → [금액 확인 (인터랙티브)](#금액-확인-인터랙티브)

확인 없이 잘못된 금액을 그대로 두거나 `--non-interactive`로 실행한 경우에는:

1. 경고 메시지 출력
2. 스크립트 중단
3. `logs/` 폴더의 로그에서 OCR 원문과 금액 후보를 확인 후 재실행

로그에는 어떤 후보 중에서 어떤 값을 왜 골랐는지가 남으므로, 금액이 이상할 때 가장 먼저 확인할 곳입니다.

## 지원 영수증 유형

- 커피빈 앱 영수증
- 스타벅스 앱 영수증
- 하나카드 앱 영수증
- 신한카드 앱 영수증 / 실물 영수증
- 삼성카드 앱 영수증
- 그 외 일반 영수증 (`기타`로 분류 후 범용 로직으로 금액 추출)

### 금액 추출 규칙

영수증에는 실제 결제액이 아닌데 금액처럼 보이는 숫자가 섞여 있습니다.

- **해피콘 쿠폰잔액** (예: `486,900`) — 카카오페이 "굿딜" 상품 결제 시 잔액을 50만원으로 잡아두고 차감하는 방식이라 생기는 값으로, 결제액과 무관합니다.
- **가맹점 주소 번지수** (예: `203,204호`)
- **적립/잔여 포인트**

이런 값을 걸러내기 위해 두 가지 장치를 둡니다.

1. `잔액 / 잔여 / 포인트 / 적립 / 주소`가 포함된 줄은 금액 후보에서 제외합니다.
2. 남은 후보 중 **가장 큰 값이 아니라 가장 자주 등장하는 값**을 고릅니다. 실제 결제액은 `총매출액`, `합계금액`, `받은금액` 등으로 여러 번 반복되지만 노이즈는 보통 한 번만 나오기 때문입니다.

### 분할 결제(더치페이) 처리

여러 명이 나눠 결제한 영수증에서는 **영수증 합계가 아니라 본인 카드로 승인된 금액**을 청구해야 합니다.

```
합    계::        33,500      ← 3명 전체 금액
카    드::        33,500
공 급 가::        30,455
부 가 세::         3,045
[승인번호]  KIS  05010915
[카드매출]        11,000      ← 실제 청구할 금액
  - 공 급 가      10,000
  - 부 가 세       1,000
```

`[카드매출]` 줄은 큰 볼드체라 OCR이 자주 뭉갭니다(`SE 1100` 등). 그래서 글자 대신 **부가세가 정확히 10%라는 점**을 이용합니다.

- 텍스트에서 `공급가 : 부가세 = 10 : 1` 관계인 숫자 쌍을 모두 찾아 각각의 합(= 결제액)을 구합니다.
- 이런 쌍이 **2개 이상**이고 뒤쪽 금액이 앞쪽보다 작으면 분할 결제로 판단하고, **문서 뒤쪽(카드 승인 블록)의 금액**을 사용합니다.
- 이때 로그에 아래와 같은 경고가 출력되므로 값을 꼭 확인하세요.

```
분할 결제로 보입니다. 영수증 전체 금액 33,500원 중 이 카드 승인분 11,000원을 사용합니다.
```

## 의존성

- Python 3.13+
- pandas
- Pillow
- Tesseract OCR 5.x (시스템 설치 필요)

## 지원 OS

- macOS (Apple Silicon / Intel)
- Linux · WSL2 (Ubuntu/Debian)
- Windows 10/11



## Tesseract OCR 설치 가이드

설치 후 아래 명령으로 검증하세요. `kor`과 `eng`가 모두 보여야 합니다.

```bash
tesseract --version
tesseract --list-langs
```

### macOS

```bash
brew install tesseract tesseract-lang
```

`tesseract` 포뮬러에는 `eng`, `osd`, `snum`만 들어 있으므로 **한국어를 쓰려면 `tesseract-lang`이 반드시 필요**합니다.

| 아키텍처 | tessdata 경로 |
|---|---|
| Apple Silicon | `/opt/homebrew/share/tessdata/` |
| Intel | `/usr/local/share/tessdata/` |

### Linux · WSL2 (Ubuntu / Debian)

```bash
sudo apt update
sudo apt install -y tesseract-ocr tesseract-ocr-kor tesseract-ocr-eng
```

시스템 tessdata 경로는 `/usr/share/tesseract-ocr/5/tessdata/` 입니다.

**Ubuntu 22.04 이하**는 기본 저장소의 Tesseract가 4.1.1이라 5.x PPA를 추가해야 합니다.

```bash
sudo add-apt-repository -y ppa:alex-p/tesseract-ocr5
sudo apt update
sudo apt install -y tesseract-ocr tesseract-ocr-kor
```

| Ubuntu | 기본 저장소 버전 | PPA 필요 |
|---|---|---|
| 24.04 이상 | 5.3.4+ | 불필요 |
| 22.04 / 20.04 | 4.1.1 | **필요** |

> PPA는 `bionic`~`plucky` 시리즈만 지원합니다. 25.10 이후 버전에는 PPA가 없으니 기본 저장소를 쓰세요.
> 또한 `noble`/`plucky` PPA에는 엔진만 있고 개별 언어팩이 없으므로, 언어팩은 배포판 저장소에서 받습니다.

### Windows 10/11

**설치 프로그램 (권장)** — [UB Mannheim 빌드](https://github.com/UB-Mannheim/tesseract/wiki)가 공식 권장 Windows 배포판입니다.

1. [tesseract-ocr-w64-setup-5.5.3.20260724.exe](https://github.com/tesseract-ocr/tesseract/releases/download/5.5.3/tesseract-ocr-w64-setup-5.5.3.20260724.exe) 다운로드 (약 25MB, 64비트 전용)
2. 설치 마법사에서 **"Additional language data (download)"** 를 펼쳐 **Korean** 체크 (설치 중 인터넷 연결 필요)
3. 기본 경로 `C:\Program Files\Tesseract-OCR` 에 설치

> ⚠️ 언인스톨러가 **설치 디렉토리를 통째로 삭제**합니다. 기존 파일이 있는 폴더(예: `C:\Tools`)에 설치하지 마세요.
> 한국어를 빠뜨렸다면 설치 프로그램을 다시 실행해 언어만 추가하면 됩니다.

**PATH 등록** (PowerShell, 관리자 권한):

```powershell
$old = [Environment]::GetEnvironmentVariable('Path','Machine')
[Environment]::SetEnvironmentVariable('Path', $old + ';C:\Program Files\Tesseract-OCR', 'Machine')
```

관리자 권한 없이 사용자 단위로 하려면 `'Machine'` 을 `'User'` 로 바꾸세요. 등록 후 **터미널을 새로 열어야** 반영됩니다. GUI로 하려면 `Win+R` → `sysdm.cpl` → 고급 → 환경 변수에서 `Path`에 위 경로를 추가합니다.

> `setx PATH ...` 는 값이 1024자에서 잘리고 변수 확장이 깨지므로 사용하지 마세요.

**패키지 매니저** — 편하지만 버전이 뒤처집니다.

```powershell
winget install -e --id UB-Mannheim.TesseractOCR   # 5.4.0 (upstream보다 오래됨)
choco install tesseract                            # 5.3.4
```

최신 버전이 필요하면 위의 설치 프로그램을 직접 받으세요.

---

## 고정확도 모델 (tessdata_best) 설치

기본 설치되는 한국어 모델은 속도를 우선한 경량판(`tessdata_fast`, 약 1.7MB)입니다. 이 프로젝트는 정확도를 우선한 `tessdata_best`(약 12MB)를 사용합니다. 실제 영수증으로 측정했을 때 한글 항목명 인식이 눈에 띄게 개선되었습니다.

프로젝트 루트에 `tessdata/` 디렉토리를 만들고 모델을 받으세요 (합계 약 27MB, `.gitignore` 처리됨).

**macOS / Linux / WSL:**

```bash
mkdir -p ./tessdata
for L in kor eng; do
  curl -fL -o "./tessdata/$L.traineddata" \
    "https://raw.githubusercontent.com/tesseract-ocr/tessdata_best/main/$L.traineddata"
done
```

**Windows (PowerShell):**

```powershell
$ProgressPreference = 'SilentlyContinue'
New-Item -ItemType Directory -Force -Path .\tessdata | Out-Null
foreach ($L in 'kor','eng') {
  Invoke-WebRequest -Uri "https://raw.githubusercontent.com/tesseract-ocr/tessdata_best/main/$L.traineddata" `
                    -OutFile ".\tessdata\$L.traineddata"
}
```

> **`kor`과 `eng`를 반드시 둘 다 받아야 합니다.** `--tessdata-dir`은 검색 경로를 추가하는 게 아니라 **완전히 대체**하므로, 한쪽만 받으면 시스템에 설치된 나머지 언어로 폴백하지 않고 그대로 실패합니다.

`tessdata/` 디렉토리가 없으면 시스템에 설치된 기본 모델로 자동 폴백하므로, 이 단계를 건너뛰어도 동작은 합니다. 경로는 `config.py`의 `TESSDATA_DIR`에서 바꿀 수 있고, `None`으로 두면 항상 시스템 모델을 사용합니다.
