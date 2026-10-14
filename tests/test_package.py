"""강사 전달용 zip 만들기 테스트."""
import shutil
import sys
import tempfile
import unicodedata
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import make_package as mp  # noqa: E402
import setup_live as sl  # noqa: E402
from test_banners import make_banners  # noqa: E402


class PackageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.exe = self.tmp / "PudufuLiveSetup.exe"
        self.exe.write_bytes(b"MZ fake")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_zip_has_exe_banners_and_guide_with_utf8_nfc_names(self):
        banners = self.tmp / "김강사 배너"
        make_banners(banners, nfd=True)
        out = mp.make_package("김강사", banners, self.exe, self.tmp / "out")
        self.assertEqual(out.name, "프드프 라이브 세팅_김강사.zip")
        with zipfile.ZipFile(out) as z:
            infos = z.infolist()
            names = [i.filename for i in infos]
        self.assertIn("PudufuLiveSetup.exe", names)
        self.assertIn("사용법.txt", names)
        want = sorted("assets/" + f.relative_to(sl.BASE / "assets").as_posix() for f in (sl.BASE / "assets").rglob("*.png"))
        self.assertEqual(sorted(n for n in names if n.startswith("assets/")), want)
        for i in infos:
            self.assertEqual(i.filename, unicodedata.normalize("NFC", i.filename))
            if not i.filename.isascii():
                self.assertTrue(i.flag_bits & 0x800, f"UTF-8 플래그 없음: {i.filename}")

    def test_incomplete_banners_are_rejected(self):
        banners = self.tmp / "b"
        make_banners(banners, skip=("live_top_01_logo@2x.png",))
        with self.assertRaises(SystemExit) as cm:
            mp.make_package("김강사", banners, self.exe, self.tmp / "out")
        self.assertIn("live_top_01_logo@2x.png", str(cm.exception))
        self.assertFalse((self.tmp / "out").exists())


class ZipRunGuardTests(unittest.TestCase):
    def test_running_inside_zip_on_windows_is_detected(self):
        p = Path(r"C:\Users\kim\AppData\Local\Temp\Temp1_프드프 라이브 세팅_김강사.zip")
        self.assertTrue(sl.running_inside_zip(p))
        self.assertFalse(sl.running_inside_zip(Path(r"C:\Users\kim\Downloads\프드프 라이브 세팅_김강사")))


if __name__ == "__main__":
    unittest.main()
