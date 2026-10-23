"""강사별 배너 폴더 처리 테스트. 실행: python -m unittest discover tests"""
import shutil
import sys
import tempfile
import unicodedata
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import setup_live as sl  # noqa: E402

DEFAULT = sl.BASE / "assets"


def make_banners(root: Path, nfd=False, skip=(), price_count=None):
    """기본 배너와 같은 구조의 강사 배너 폴더를 만든다."""
    for f in DEFAULT.rglob("*.png"):
        rel = f.relative_to(DEFAULT).as_posix()
        if rel in skip:
            continue
        if nfd:
            rel = unicodedata.normalize("NFD", rel)
        out = root / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, out)
    if price_count is not None:  # 가격O 폴더 장수 바꾸기
        folder = next(p for p in root.iterdir() if p.is_dir() and "O" in p.name)
        for p in sorted(folder.iterdir())[price_count:]:
            p.unlink()


class BannerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_no_folder_next_to_exe_uses_builtin(self):
        self.assertEqual(sl.banner_source(self.tmp), (DEFAULT, False))

    def test_folder_next_to_exe_is_used(self):
        make_banners(self.tmp / "assets")
        self.assertEqual(sl.banner_source(self.tmp), (self.tmp / "assets", True))

    def test_explicit_folder_wins_over_folder_next_to_exe(self):
        make_banners(self.tmp / "assets")
        make_banners(self.tmp / "드라이브" / "배너" / "assets")
        chosen = self.tmp / "드라이브" / "배너" / "assets"
        self.assertEqual(sl.banner_source(self.tmp, chosen), (chosen, True))

    def test_explicit_folder_is_used_even_when_it_is_missing(self):
        """없는 경로를 넘기면 기본 배너로 조용히 빠지지 않고 그대로 돌려줘 banner_problems가 알려 주게 한다."""
        chosen = self.tmp / "없는폴더"
        self.assertEqual(sl.banner_source(self.tmp, chosen), (chosen, True))
        self.assertTrue(sl.banner_problems(chosen))

    def test_builtin_banners_are_complete(self):
        self.assertEqual(sl.banner_problems(DEFAULT), [])

    def test_missing_logo_is_reported(self):
        make_banners(self.tmp, skip=("live_top_01_logo@2x.png",))
        self.assertEqual(sl.banner_problems(self.tmp), ["live_top_01_logo@2x.png 파일이 없습니다"])

    def test_empty_slideshow_folder_is_reported(self):
        make_banners(self.tmp)
        folder = next(p for p in self.tmp.iterdir() if p.is_dir() and "X" in p.name)
        for p in folder.iterdir():
            p.unlink()
        self.assertEqual(sl.banner_problems(self.tmp), ["'1. 가격X 배너' 폴더에 그림이 없습니다"])

    def test_different_banner_count_is_fine(self):
        make_banners(self.tmp, price_count=3)
        self.assertEqual(sl.banner_problems(self.tmp), [])

    def test_mac_zip_nfd_names_are_accepted_and_installed_as_nfc(self):
        src, dst = self.tmp / "src", self.tmp / "dst"
        make_banners(src, nfd=True)
        self.assertEqual(sl.banner_problems(src), [])
        sl.install_banners(src, dst)
        want = sorted(f.relative_to(DEFAULT).as_posix() for f in DEFAULT.rglob("*.png"))
        got = sorted(f.relative_to(dst).as_posix() for f in dst.rglob("*.png"))
        self.assertEqual(got, want)

    def test_install_removes_old_files_and_ignores_junk(self):
        src, dst = self.tmp / "src", self.tmp / "dst"
        make_banners(src)
        (src / ".DS_Store").write_text("x")
        (dst / "1_혜택 공개 전").mkdir(parents=True)
        sl.install_banners(src, dst)
        self.assertFalse((dst / "1_혜택 공개 전").exists())
        self.assertFalse((dst / ".DS_Store").exists())


if __name__ == "__main__":
    unittest.main()
