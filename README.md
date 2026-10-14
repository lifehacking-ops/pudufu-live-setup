# 프드프 라이브 OBS 자동 세팅

강사에게 exe 하나를 전달하면, 실행 → "세팅 시작" 만으로 OBS 강의 세팅이 끝난다. 유튜브 연결은 OBS 설정 → 방송에서 '계정 연결'로 로그인한다.

## 실행하면 하는 일

1. OBS 설치 확인. 없으면 최신 OBS를 내려받아 조용히 설치 (Windows).
2. 배너를 강사 PC에 복사. exe 옆에 `assets` 폴더가 있으면 그 강사 배너를, 없으면 exe에 내장된 기본 프드프 배너를 쓴다.
3. `template/scenes.json`(장면 6개)을 강사 PC용으로 변환해 설치.
   - Mac 전용 소스(macOS 웹캠·화면 캡쳐)를 Windows 소스로 교체
   - 중복 웹캠·화면 소스를 하나로 합치고, 이미지 경로를 강사 PC 경로로 교체
   - 마이크·데스크탑 오디오는 "기본 장치"로 설정
4. 송출 프로필 생성 (1080p30, x264 6000kbps, 송출처 YouTube). 강사는 OBS 설정 → 방송에서 '계정 연결'로 유튜브 로그인.
5. OBS 실행 후 obs-websocket으로 웹캠·모니터를 자동 연결.

## 파일

| 경로 | 용도 |
|---|---|
| `setup_live.py` | 프로그램 본체. GUI 또는 `--no-gui` 지정 시 CLI |
| `template/scenes.json` | OBS에서 내보낸 장면 컬렉션 원본 (Mac). 수정 시 OBS에서 다시 내보내 교체 |
| `assets/` | 기본 프드프 배너 (exe에 내장). 강사 배너 폴더의 양식 |
| `make_package.py` | 강사 전달용 zip 만들기 |
| `tests/` | 배너 처리·zip 만들기 테스트 (`python -m unittest discover tests`) |
| `.github/workflows/build-windows.yml` | GitHub Actions에서 Windows exe 빌드 |

## 설정값 (setup_live.py 상단)

- `VIDEO` : 해상도·FPS·비트레이트.
- `WS_PASSWORD` : obs-websocket 비밀번호 (강사 PC OBS에 기록됨).

## Windows exe 만들기

1. 이 폴더를 GitHub 저장소에 push.
2. Actions → "Build Windows exe" 실행 (push 시 자동).
3. Artifacts에서 `PudufuLiveSetup.exe`를 받아 `dist/PudufuLiveSetup/`에 둔다.
   (`gh run download <run id> --dir dist`)

## 강사에게 전달하기

exe는 모든 강사 공통이고, 배너만 강사별로 바꾼다. 배너가 바뀌어도 exe를 다시 빌드할 필요 없다.

1. 강사 배너 폴더를 `assets/`와 같은 구조로 만든다.
   - `live_top_01_logo@2x.png`, `live_ticker_01_gift@2x.png` : 파일 이름 그대로 (로고·하단 띠)
   - `1. 가격X 배너/`, `2. 가격O 배너/` : 폴더 안 그림을 이름순으로 돌려 보여 준다. 장수는 자유, 빈 폴더는 안 됨
2. zip을 만든다. Finder로 압축하지 말 것 (Windows에서 한글 이름이 깨질 수 있음).
   ```bash
   .venv/bin/python make_package.py 김강사 "~/Desktop/김강사 배너"
   # → packages/프드프 라이브 세팅_김강사.zip (exe + assets + 사용법.txt)
   ```
3. zip을 강사에게 보낸다. 강사는 압축을 풀고 exe를 실행한다.
   압축을 풀지 않고 안에서 바로 실행하면 프로그램이 막고 "압축을 먼저 풀어 달라"고 안내한다.

빠진 배너가 있으면 zip 만들 때와 강사 실행 때 모두 어떤 파일이 없는지 알려 주고 멈춘다.
완료 화면에 "강사 배너 적용" / "기본 프드프 배너 적용"이 표시된다.

## Mac에서 개발·테스트

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python setup_live.py                       # GUI
.venv/bin/python setup_live.py --no-gui                   # 창 없이 바로 실행
```

## 알려진 제약

- Windows 변환본은 실제 Windows PC에서 한 번 검증이 필요하다 (Mac에서는 Mac 변환본만 검증됨).
- Mac에서 화면 캡쳐·카메라 권한은 OS가 묻는다. 거부하면 해당 소스가 비어 보인다.
- 장면 템플릿의 "프드프 로고"는 원본 설정대로 x=-700 위치라 캔버스 왼쪽 밖으로 대부분 나가 있다. 의도가 아니면 OBS에서 위치를 고친 뒤 JSON을 다시 내보내면 된다.
