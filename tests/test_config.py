import json
import os
import tempfile
import unittest

from config import ConfigManager, Credentials, WebsiteProfile


class ConfigTests(unittest.TestCase):
    def test_saved_config_never_contains_direct_secret_values(self):
        manager = ConfigManager()
        profile = WebsiteProfile(
            name="site",
            url="https://example.com",
            credentials=Credentials(
                type="api_key",
                api_key_name="X-Key",
                api_key_env="SITE_KEY",
                api_key_value="must-not-be-saved",
            ),
        )
        manager.add_profile(profile)
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "config.json")
            manager.save_config(path)
            with open(path, encoding="utf-8") as handle:
                text = handle.read()
            self.assertNotIn("must-not-be-saved", text)
            payload = json.loads(text)
            self.assertEqual(payload["profiles"]["site"]["credentials"]["api_key_env"], "SITE_KEY")

    def test_legacy_http_post_maps_to_tkws_signed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "config.json")
            with open(path, "w", encoding="utf-8") as handle:
                json.dump({
                    "profiles": {
                        "legacy": {
                            "url": "https://example.com",
                            "upload_method": "http_post",
                            "credentials": {"type": "none"}
                        }
                    }
                }, handle)
            manager = ConfigManager()
            manager.load_config(path)
            self.assertEqual(manager.get_profile("legacy").upload_method, "tkws_signed")


if __name__ == "__main__":
    unittest.main()
