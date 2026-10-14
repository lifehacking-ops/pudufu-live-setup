#!/usr/bin/env python3
"""강사 전달용 zip 만들기.

    python make_package.py 강사이름 강사배너폴더 [--exe 경로] [--out 폴더]

강사배너폴더는 레포의 assets 폴더와 같은 구조여야 한다(로고·띠배너 파일 이름 고정, 슬라이드쇼 폴더 장수 자유).
zip 안 이름은 UTF-8 플래그 + NFC로 넣어 Windows에서 한글이 깨지거나 자모가 분리되지 않게 한다.
"""
import argparse
import sys
import zipfile
from pathlib import Path

from setup_live import IMAGE_EXT, banner_problems, nfc

EXE_NAME = "PudufuLiveSetup.exe"
GUIDE = """프드프 라이브 OBS 세팅 사용법

1. 이 압축 파일을 먼저 풀어 주세요. (마우스 오른쪽 클릭 → 압축 풀기)
   압축을 풀지 않고 안에서 바로 실행하면 배너가 적용되지 않습니다.
2. 압축을 푼 폴더에서 PudufuLiveSetup.exe를 실행하고 '세팅 시작'을 누르세요.
   OBS가 없으면 자동으로 설치합니다. 관리자 권한 창이 뜨면 '예'를 눌러 주세요.
3. 세팅이 끝나면 OBS 메뉴 [설정] → [방송] → '계정 연결'로 유튜브에 로그인하세요.
4. OBS 오른쪽 아래 '방송 시작'을 누르면 송출이 시작됩니다.

※ assets 폴더는 강사님 배너입니다. 이름을 바꾸거나 지우지 마세요.
"""


def make_package(name: str, banners: Path, exe: Path, out_dir: Path) -> Path:
    problems = banner_problems(banners)
    if problems:
        raise SystemExit("배너 폴더를 확인해 주세요:\n- " + "\n- ".join(problems))
    if not exe.is_file():
        raise SystemExit(f"exe가 없습니다: {exe}")
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / nfc(f"프드프 라이브 세팅_{name}.zip")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(exe, EXE_NAME)
        z.writestr("사용법.txt", GUIDE.replace("\n", "\r\n").encode("utf-8-sig"))
        for f in sorted(banners.rglob("*")):
            if f.is_file() and f.suffix.lower() in IMAGE_EXT and not f.name.startswith("."):
                z.write(f, "assets/" + nfc(f.relative_to(banners).as_posix()))
    return out


def main():
    here = Path(__file__).resolve().parent
    ap = argparse.ArgumentParser(description="강사 전달용 zip 만들기")
    ap.add_argument("name", help="강사 이름 (zip 파일 이름에 들어감)")
    ap.add_argument("banners", type=Path, help="강사 배너 폴더 (assets와 같은 구조)")
    ap.add_argument("--exe", type=Path, default=here / "dist" / "PudufuLiveSetup" / EXE_NAME)
    ap.add_argument("--out", type=Path, default=here / "packages")
    a = ap.parse_args()
    out = make_package(a.name, a.banners, a.exe, a.out)
    print(f"완료: {out}")


if __name__ == "__main__":
    sys.exit(main())
