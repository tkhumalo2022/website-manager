import tempfile
import unittest
from pathlib import Path

from config import WebsiteProfile
from core.uploader import Uploader


class UploaderTests(unittest.TestCase):
    def test_logo_category(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "brand-logo.png"
            path.write_bytes(b"png")
            category, mime_type = Uploader._detect_upload_metadata(path, path.name)
            self.assertEqual(category, "logo")
            self.assertEqual(mime_type, "image/png")

    def test_dry_run_does_not_need_network(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "hello.txt"
            path.write_text("hello", encoding="utf-8")
            profile = WebsiteProfile(name="site", url="https://example.com")
            self.assertTrue(Uploader(profile).upload_file(str(path), dry_run=True))


if __name__ == "__main__":
    unittest.main()
