# 프드프 라이브 OBS 자동 세팅 — Mac 안내 (GitHub에서 받기)

Windows는 exe 하나로 끝나지만, Mac은 아직 앱으로 만들지 않아서 **GitHub에서 프로그램을 받아 터미널에서 실행**합니다.
세팅 내용(장면 6개, 배너, 송출 프로필, 웹캠·모니터 자동 연결)은 Windows와 같습니다.

- 프로그램: https://github.com/lifehacking-ops/pudufu-live-setup (공개 저장소)
- 강사 배너: 저장소에 없습니다. 관리자가 강사별로 따로 전달합니다.

앞부분은 **관리자**가, 뒷부분은 **강사**가 보면 됩니다.

---

## 1. 관리자가 할 일

### 1-1. 프로그램 고치기

코드를 고쳐서 `main`에 푸시하면 끝입니다. 강사는 다음에 실행할 때 `git pull`로 받아 갑니다.

### 1-2. 강사 배너 전달

강사 배너는 아래 구조의 `assets` 폴더 하나입니다. 이 폴더를 zip으로 묶어 메일·메신저 등으로 보냅니다.

```
assets/
├── live_top_01_logo@2x.png        ← 로고 (이름 고정)
├── live_ticker_01_gift@2x.png     ← 하단 띠배너 (이름 고정)
├── 1. 가격X 배너/                  ← 이름순으로 돌아가며 표시, 장수 자유
│   ├── live_01_intro@2x.png
│   └── ...
└── 2. 가격O 배너/
    ├── live_03_price@2x.png
    └── ...
```

보내기 전에 빠진 것이 없는지 확인합니다.

```bash
cd ~/Desktop/code/pudufu-live-setup
.venv/bin/python -c "from setup_live import banner_problems; from pathlib import Path; print(banner_problems(Path('<assets 폴더 경로>')) or '배너 OK')"
```

빠진 파일이 있으면 강사가 실행할 때도 어떤 파일이 없는지 알려 주고 멈춥니다.

---

## 2. 강사가 할 일

### 2-1. 준비

1. **OBS 설치.** Mac은 자동 설치를 하지 않습니다. https://obsproject.com 에서 macOS용을 받아 `응용 프로그램`에 넣어 주세요. 이미 있으면 건너뜁니다.
2. **OBS 종료.** 켜져 있으면 Dock 아이콘 우클릭 → 종료.
3. **배너 놓기.** 받은 zip을 풀어서 나온 `assets` 폴더를 **데스크탑**에 둡니다. 다른 곳에 두면 2-2의 셋째 줄에서 경로만 바꾸면 됩니다.

### 2-2. 처음 한 번: 받고 실행

`응용 프로그램 → 유틸리티 → 터미널`을 열고, 아래를 한 줄씩 붙여 넣어 실행합니다.

```bash
git clone https://github.com/lifehacking-ops/pudufu-live-setup.git ~/pudufu-live-setup
python3 -m venv ~/pudufu-venv && ~/pudufu-venv/bin/pip install -r ~/pudufu-live-setup/requirements.txt
~/pudufu-venv/bin/python ~/pudufu-live-setup/setup_live.py --no-gui --assets ~/Desktop/assets
```

- 첫 줄에서 "명령어 라인 개발자 도구를 설치하시겠습니까?" 창이 뜰 수 있습니다. **설치**를 누르고, 끝나면 첫 줄부터 다시 실행하세요.
- 셋째 줄의 `~/Desktop/assets`가 배너 위치입니다. 배너를 다른 곳에 뒀다면 `--assets ` 까지 입력한 뒤 Finder에서 `assets` 폴더를 터미널 창으로 끌어다 놓으면 경로가 들어갑니다.

실행하면 진행 상황이 터미널에 표시되고, 마지막에 OBS가 자동으로 켜집니다.

### 2-3. 다음부터: 최신으로 받고 실행

```bash
git -C ~/pudufu-live-setup pull
~/pudufu-venv/bin/python ~/pudufu-live-setup/setup_live.py --no-gui --assets ~/Desktop/assets
```

배너가 바뀌었으면 새로 받은 `assets` 폴더로 데스크탑의 것을 바꾼 뒤 실행하면 됩니다.

### 2-4. 권한 허용

OBS가 처음 켜질 때 macOS가 **카메라**, **마이크**, **화면 기록** 권한을 묻습니다. 모두 **허용**해 주세요.
거부하면 해당 소스가 검게 보입니다. 나중에 바꾸려면 `시스템 설정 → 개인정보 보호 및 보안`에서 OBS를 켜고 OBS를 다시 실행하세요.

### 2-5. 유튜브 연결

세팅이 끝나면 OBS 메뉴 `설정 → 방송 → 계정 연결`로 유튜브에 로그인합니다.
이후 OBS 오른쪽 아래 `방송 시작`을 누르면 송출됩니다.

---

## 3. 문제가 생기면

| 메시지 / 증상 | 원인과 조치 |
|---|---|
| `Mac에는 OBS가 없습니다` | OBS를 `응용 프로그램` 폴더에 설치한 뒤 다시 실행 |
| `OBS가 이미 켜져 있습니다` | OBS를 완전히 종료(Dock 우클릭 → 종료)하고 다시 실행 |
| `배너 폴더를 확인해 주세요: …` | 아래 줄에 없는 파일·폴더가 나옵니다. `--assets` 경로가 zip을 푼 `assets` 폴더를 가리키는지 확인 |
| `command not found: git` / `python3` | 2-2의 개발자 도구 설치 창에서 **설치** 후 다시 실행 |
| `destination path ... already exists` | 이미 받아 둔 상태입니다. 2-3의 명령을 쓰세요 |
| `git pull`에서 오류 | 받은 폴더 안 파일을 고친 경우입니다. `rm -rf ~/pudufu-live-setup` 후 2-2의 첫 줄부터 다시 실행 |
| 웹캠·화면이 검게 나옴 | 2-4 권한 허용 후 OBS 재실행 |
| 세팅을 다시 하고 싶음 | 같은 명령을 다시 실행하면 장면·배너·프로필을 덮어씀 |

실행 결과 마지막 줄에 `✅ 세팅 완료`가 보이면 정상입니다. 그 위 "배너 설치:" 줄에 `강사 배너(…/assets)`가 찍혀야 받은 배너가 적용된 것입니다.

---

## 4. Windows exe와 다른 점

| | Windows (exe) | Mac (이 문서) |
|---|---|---|
| 받는 방법 | exe·배너가 든 zip을 전달받음 | GitHub에서 `git clone`, 이후 `git pull` |
| 실행 방법 | exe 더블클릭 → 세팅 시작 | 터미널에서 명령 실행 |
| OBS 설치 | 없으면 자동 설치 | 직접 설치해야 함 |
| 강사 배너 | exe 옆 `assets` 폴더 | `--assets` 로 전달받은 `assets` 폴더 지정 |
| 화면 캡쳐 | Windows 모니터 캡쳐 | macOS 화면 캡쳐(주 모니터 자동 지정) |

Mac 강사가 늘어나면 `.app`으로 빌드해 더블클릭만으로 되게 만들 수 있습니다. (README.md 참고)
