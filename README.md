# 프드프 라이브 OBS 자동 세팅

강사에게 exe 하나를 전달하면, 실행 → 송출처·스트림 키 입력 → "세팅 시작" 만으로 OBS 강의 세팅이 끝난다.

## 실행하면 하는 일

1. OBS 설치 확인. 없으면 최신 OBS를 내려받아 조용히 설치 (Windows).
2. 로고·띠배너·가격 배너 이미지를 강사 PC에 복사.
3. `template/scenes.json`(장면 6개)을 강사 PC용으로 변환해 설치.
   - Mac 전용 소스(macOS 웹캠·화면 캡쳐)를 Windows 소스로 교체
   - 중복 웹캠·화면 소스를 하나로 합치고, 이미지 경로를 강사 PC 경로로 교체
   - 마이크·데스크탑 오디오는 "기본 장치"로 설정
4. 송출 프로필 생성 (1080p30, x264 6000kbps, YouTube 또는 pudufu RTMP + 스트림 키).
5. OBS 실행 후 obs-websocket으로 웹캠·모니터를 자동 연결.

## 파일

| 경로 | 용도 |
|---|---|
| `setup_live.py` | 프로그램 본체. GUI 또는 `--key` 지정 시 CLI |
| `template/scenes.json` | OBS에서 내보낸 장면 컬렉션 원본 (Mac). 수정 시 OBS에서 다시 내보내 교체 |
| `assets/` | 로고, 띠배너, 가격 공개 전/후 배너 |
| `.github/workflows/build-windows.yml` | GitHub Actions에서 Windows exe 빌드 |

## 설정값 (setup_live.py 상단)

- `PUDUFU_RTMP_SERVER` : pudufu 송출 서버 주소. 비워 두면 실행 시 입력창이 뜬다.
- `VIDEO` : 해상도·FPS·비트레이트.
- `WS_PASSWORD` : obs-websocket 비밀번호 (강사 PC OBS에 기록됨).

## Windows exe 만들기

1. 이 폴더를 GitHub 저장소에 push.
2. Actions → "Build Windows exe" 실행 (push 시 자동).
3. Artifacts에서 `PudufuLiveSetup.exe` 다운로드 후 강사에게 전달.

## Mac에서 개발·테스트

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python setup_live.py                       # GUI
.venv/bin/python setup_live.py --dest youtube --key XXXX   # 창 없이 바로 실행
```

## 알려진 제약

- Windows 변환본은 실제 Windows PC에서 한 번 검증이 필요하다 (Mac에서는 Mac 변환본만 검증됨).
- Mac에서 화면 캡쳐·카메라 권한은 OS가 묻는다. 거부하면 해당 소스가 비어 보인다.
- 장면 템플릿의 "프드프 로고"는 원본 설정대로 x=-700 위치라 캔버스 왼쪽 밖으로 대부분 나가 있다. 의도가 아니면 OBS에서 위치를 고친 뒤 JSON을 다시 내보내면 된다.
