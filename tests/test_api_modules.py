import unittest

from backend.services.api_modules import build_module_catalog


class TestApiModules(unittest.TestCase):
    def test_catalog_has_expected_module_ids_and_readable_names(self):
        catalog = build_module_catalog(
            auditor_ok=True,
            ffmpeg_ok=True,
            photoshop_ok=True,
            umcli_ok=True,
            wechat_ok=True,
            ytdlp_ok=True,
        )

        modules = {item["id"]: item for item in catalog["modules"]}

        self.assertEqual(
            set(modules),
            {
                "fetcher",
                "encoder",
                "decryptor",
                "assets",
                "workbench",
                "editor",
                "photoshop",
                "filebrowser",
                "wechat_moments",
                "auditor",
            },
        )
        self.assertEqual(modules["fetcher"]["name"], "媒体获取")
        self.assertEqual(modules["assets"]["status"], "ready")
        self.assertTrue(modules["editor"]["experimental"])

    def test_catalog_marks_missing_dependencies(self):
        catalog = build_module_catalog(
            auditor_ok=False,
            ffmpeg_ok=False,
            photoshop_ok=False,
            umcli_ok=False,
            wechat_ok=False,
            ytdlp_ok=False,
        )
        modules = {item["id"]: item for item in catalog["modules"]}

        self.assertEqual(modules["fetcher"]["status"], "dep_missing")
        self.assertEqual(modules["encoder"]["status"], "dep_missing")
        self.assertEqual(modules["workbench"]["status"], "dep_missing")
        self.assertEqual(modules["assets"]["status"], "ready")
        self.assertEqual(modules["editor"]["status"], "staged")

    def test_experimental_modules_are_staged_when_available(self):
        catalog = build_module_catalog(
            auditor_ok=True,
            ffmpeg_ok=True,
            photoshop_ok=True,
            umcli_ok=True,
            wechat_ok=True,
            ytdlp_ok=True,
        )
        modules = {item["id"]: item for item in catalog["modules"]}

        self.assertEqual(modules["wechat_moments"]["status"], "staged")
        self.assertEqual(modules["auditor"]["status"], "staged")
        self.assertTrue(modules["filebrowser"]["experimental"])


if __name__ == "__main__":
    unittest.main()
