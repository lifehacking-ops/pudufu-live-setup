# 프드프 라이브 OBS 자동 세팅 — Mac 안내 (구글 드라이브 배포)

Windows는 exe 하나로 끝나지만, Mac은 아직 앱으로 만들지 않아서 **구글 드라이브 폴더를 열고 터미널에서 실행**합니다.
세팅 내용(장면 6개, 배너, 송출 프로필, 웹캠·모니터 자동 연결)은 Windows와 같습니다.

## 폴더 구조

구글 드라이브의 `obs 배너 세팅기` 폴더를 이렇게 둡니다. 프로그램은 `--assets` 옵션으로 옆의 `배너/assets` 폴더를 읽습니다.

```
obs 배너 세팅기/               ← 구글 드라이브
├── pudufu-live-setup/        ← 프로그램 (이 폴더)
│   ├── setup_live.py
│   ├── requirements.txt
│   └── ...
└── 배너/
    └── assets/               ← 강사 배너
        ├── live_top_01_logo@2x.png        ← 로고 (이름 고정)
        ├── live_ticker_01_gift@2x.png     ← 하단 띠배너 (이름 고정)
        ├── 1. 가격X 배너/                  ← 이름순으로 돌아가며 표시, 장수 자유
        │   ├── live_01_intro@2x.png
        │   └── ...
        └── 2. 가격O 배너/
            ├── live_03_price@2x.png
            └── ...
```

강사마다 다른 배너를 쓰려면 `배너/김강사/assets` 처럼 폴더를 나누고, 실행할 때 `--assets` 경로만 바꾸면 됩니다.

앞부분은 **관리자**가, 뒷부분은 **강사**가 보면 됩니다.

---

## 1. 관리자가 할 일

### 1-1. 프로그램 올리기

`pudufu-live-setup` 폴더를 드라이브에 올릴 때 아래는 **빼고** 올립니다. 내 Mac 경로가 박혀 있어 다른 Mac에서 동작하지 않거나, 불필요한 것들입니다.

- `.venv/`, `.venv-tk/` (가상환경)
- `.git/`
- `dist/` (Windows exe), `packages/`
- `__pycache__/`

```bash
# 드라이브에 올릴 복사본 만들기 (대상 경로는 내 드라이브 위치에 맞게)
rsync -a --exclude '.venv*' --exclude '.git' --exclude 'dist' --exclude 'packages' \
      --exclude '__pycache__' --exclude '.DS_Store' \
      ~/Desktop/code/pudufu-live-setup/ "<드라이브>/obs 배너 세팅기/pudufu-live-setup/"
```

코드를 고치면 같은 명령을 다시 돌리면 됩니다. 드라이브가 동기화하므로 강사는 받을 것이 없습니다.

### 1-2. 배너 올리기

`배너/assets/`를 위 구조대로 채웁니다. 올리기 전에 빠진 것이 없는지 확인합니다.

```bash
cd ~/Desktop/code/pudufu-live-setup
.venv-tk/bin/python -c "from setup_live import banner_problems; from pathlib import Path; print(banner_problems(Path('<배너/assets 경로>')) or '배너 OK')"
```

빠진 파일이 있으면 강사가 실행할 때도 어떤 파일이 없는지 알려 주고 멈춥니다.

---

## 2. 강사가 할 일

### 2-1. 준비

1. **OBS 설치.** Mac은 자동 설치를 하지 않습니다. https://obsproject.com 에서 macOS용을 받아 `응용 프로그램`에 넣어 주세요. 이미 있으면 건너뜁니다.
2. **OBS 종료.** 켜져 있으면 Dock 아이콘 우클릭 → 종료.
3. **구글 드라이브 데스크톱 앱**으로 `obs 배너 세팅기` 폴더가 Finder에 보여야 합니다. 보이지 않으면 https://www.google.com/drive/download 에서 설치하고 로그인하세요.
4. Finder에서 `obs 배너 세팅기` 폴더를 우클릭 → **오프라인 사용 가능**을 켜 주세요. 파일이 아직 내려받아지지 않아 실행이 멈추는 것을 막습니다.

### 2-2. 터미널에서 실행

`응용 프로그램 → 유틸리티 → 터미널`을 열고, 아래를 한 줄씩 붙여 넣어 실행합니다.

```bash
cd "<pudufu-live-setup 폴더 경로>"
python3 -m venv ~/pudufu-venv && ~/pudufu-venv/bin/pip install -r requirements.txt
~/pudufu-venv/bin/python setup_live.py --no-gui --assets "../배너/assets"
```

- 첫 줄: `cd ` 까지 입력한 뒤, Finder에서 `pudufu-live-setup` 폴더를 터미널 창으로 끌어다 놓으면 경로가 들어갑니다. 그리고 Enter.
- `python3`를 처음 실행하면 "명령어 라인 개발자 도구를 설치하시겠습니까?" 창이 뜰 수 있습니다. **설치**를 누르고 끝난 뒤 둘째 줄부터 다시 실행하세요.
- 둘째 줄은 처음 한 번만 필요합니다. 다음부터는 첫째·셋째 줄만 실행하면 됩니다.
- 가상환경은 드라이브 폴더가 아니라 홈 폴더(`~/pudufu-venv`)에 만듭니다. 드라이브 안에 만들면 파일 수천 개가 동기화됩니다.

실행하면 진행 상황이 터미널에 표시되고, 마지막에 OBS가 자동으로 켜집니다.

### 2-3. 권한 허용

OBS가 처음 켜질 때 macOS가 **카메라**, **마이크**, **화면 기록** 권한을 묻습니다. 모두 **허용**해 주세요.
거부하면 해당 소스가 검게 보입니다. 나중에 바꾸려면 `시스템 설정 → 개인정보 보호 및 보안`에서 OBS를 켜고 OBS를 다시 실행하세요.

### 2-4. 유튜브 연결

세팅이 끝나면 OBS 메뉴 `설정 → 방송 → 계정 연결`로 유튜브에 로그인합니다.
이후 OBS 오른쪽 아래 `방송 시작`을 누르면 송출됩니다.

---

## 3. 문제가 생기면

| 메시지 / 증상 | 원인과 조치 |
|---|---|
| `Mac에는 OBS가 없습니다` | OBS를 `응용 프로그램` 폴더에 설치한 뒤 다시 실행 |
| `OBS가 이미 켜져 있습니다` | OBS를 완전히 종료(Dock 우클릭 → 종료)하고 다시 실행 |
| `배너 폴더를 확인해 주세요: …` | 아래 줄에 없는 파일·폴더가 나옵니다. 경로가 맞는지, 관리자가 `배너/assets`를 채웠는지 확인 |
| `command not found: python3` | 2-2의 개발자 도구 설치 창에서 **설치** 후 다시 실행 |
| `No such file or directory: requirements.txt` | 첫 줄 `cd`가 `pudufu-live-setup` 폴더가 아닙니다. 경로 확인 |
| 웹캠·화면이 검게 나옴 | 2-3 권한 허용 후 OBS 재실행 |
| 세팅을 다시 하고 싶음 | 같은 명령을 다시 실행하면 장면·배너·프로필을 덮어씀 |

실행 결과 마지막 줄에 `✅ 세팅 완료`가 보이면 정상입니다. 그 위 "배너 설치:" 줄에 `강사 배너(…/배너/assets)`가 찍혀야 드라이브 배너가 적용된 것입니다.

---

## 4. Windows exe와 다른 점

| | Windows (exe) | Mac (이 문서) |
|---|---|---|
| 실행 방법 | exe 더블클릭 → 세팅 시작 | 터미널에서 명령 실행 |
| OBS 설치 | 없으면 자동 설치 | 직접 설치해야 함 |
| 강사 배너 | exe 옆 `assets` 폴더 | `--assets` 로 드라이브의 `배너/assets` 지정 |
| 화면 캡쳐 | Windows 모니터 캡쳐 | macOS 화면 캡쳐(주 모니터 자동 지정) |

Mac 강사가 늘어나면 `.app`으로 빌드해 더블클릭만으로 되게 만들 수 있습니다. (README.md 참고)
