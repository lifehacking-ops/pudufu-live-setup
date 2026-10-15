"""OBS 실행 파일 찾기 테스트 (Windows 경로 규칙을 Mac에서 임시 폴더로 흉내)."""
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import setup_live as sl  # noqa: E402


class FindObsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def exe_in(self, folder: Path) -> Path:
        p = folder / "bin" / "64bit" / "obs64.exe"
        p.parent.mkdir(parents=True)
        p.write_bytes(b"MZ")
        return p

    def test_install_dir_from_registry(self):
        exe = self.exe_in(self.tmp / "D" / "Tools" / "obs-studio")
        self.assertEqual(sl.pick_obs_exe([str(self.tmp / "nope"), str(self.tmp / "D" / "Tools" / "obs-studio")]), exe)

    def test_quoted_registry_value_and_direct_exe_path(self):
        exe = self.exe_in(self.tmp / "obs-studio")
        self.assertEqual(sl.pick_obs_exe([f'"{exe}"']), exe)
        self.assertEqual(sl.pick_obs_exe([f'"{self.tmp / "obs-studio"}"']), exe)

    def test_nothing_installed(self):
        self.assertIsNone(sl.pick_obs_exe([str(self.tmp / "a"), "", str(self.tmp / "b")]))


if __name__ == "__main__":
    unittest.main()
