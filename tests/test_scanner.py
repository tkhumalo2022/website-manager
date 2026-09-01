import tempfile
import unittest
from pathlib import Path

from scan_websites import detect_stack, scan


class ScannerTests(unittest.TestCase):
    def test_detects_next_project(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "site"
            root.mkdir()
            (root / "package.json").write_text('{"dependencies":{"next":"latest"}}', encoding="utf-8")
            self.assertEqual(detect_stack(root), "Next.js")
            results = scan([Path(directory)], max_depth=2)
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["website_name"], "site")


if __name__ == "__main__":
    unittest.main()
