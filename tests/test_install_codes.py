"""OBS 설치 프로그램 종료 코드 → 강사 안내 문구 테스트."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import setup_live as sl  # noqa: E402


class InstallCodeTests(unittest.TestCase):
    def test_success_has_no_error(self):
        self.assertIsNone(sl.install_error(0))

    def test_files_in_use_asks_reboot(self):
        msg = sl.install_error(6)
        self.assertIn("재부팅", msg)
        self.assertIn("코드 6", msg)

    def test_known_failure_codes(self):
        for code in (3, 4, 5, 1223):
            self.assertIsNotNone(sl.install_error(code), code)

    def test_unknown_code_keeps_waiting(self):
        # 모르는 코드는 설치가 됐을 수도 있으니 실행 파일 찾기로 넘긴다.
        self.assertIsNone(sl.install_error(2))


if __name__ == "__main__":
    unittest.main()
