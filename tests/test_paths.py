"""Store layout per platform, and the $DEVTEAM_HOME override."""

import os
import unittest

from devteam_support import StoreTestCase  # noqa: F401  (path bootstrap)

from devteam import paths


class PlatformLayoutTest(unittest.TestCase):
    def setUp(self):
        self._saved = {k: os.environ.get(k) for k in ("DEVTEAM_HOME", "DEVTEAM_PLATFORM", "APPDATA", "LOCALAPPDATA")}
        os.environ.pop("DEVTEAM_HOME", None)

    def tearDown(self):
        for key, value in self._saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def test_macos_splits_core_data_and_cache(self):
        os.environ["DEVTEAM_PLATFORM"] = "darwin"
        self.assertIn("Application Support/dev-team-agents/core", str(paths.core_dir()))
        self.assertIn("Application Support/dev-team-agents/data", str(paths.data_dir()))
        self.assertIn("Caches/dev-team-agents", str(paths.cache_dir()))

    def test_windows_puts_data_in_roaming_and_core_in_local(self):
        os.environ["DEVTEAM_PLATFORM"] = "win32"
        os.environ["APPDATA"] = r"C:\Users\t\AppData\Roaming"
        os.environ["LOCALAPPDATA"] = r"C:\Users\t\AppData\Local"
        self.assertIn("Roaming", str(paths.data_dir()))
        self.assertIn("Local", str(paths.core_dir()))
        self.assertIn("Local", str(paths.cache_dir()))

    def test_linux_follows_xdg(self):
        os.environ["DEVTEAM_PLATFORM"] = "linux"
        os.environ["XDG_DATA_HOME"] = "/tmp/xdg-data"
        self.addCleanup(os.environ.pop, "XDG_DATA_HOME", None)
        self.assertEqual(str(paths.core_dir()), "/tmp/xdg-data/dev-team-agents/core")

    def test_devteam_home_overrides_every_platform(self):
        os.environ["DEVTEAM_HOME"] = "/tmp/explicit"
        for platform in ("darwin", "win32", "linux"):
            os.environ["DEVTEAM_PLATFORM"] = platform
            self.assertEqual(str(paths.core_dir()), "/tmp/explicit/core")
            self.assertEqual(str(paths.data_dir()), "/tmp/explicit/data")
            self.assertEqual(str(paths.cache_dir()), "/tmp/explicit/cache")

    def test_current_is_a_file_not_a_symlink_path(self):
        os.environ["DEVTEAM_HOME"] = "/tmp/explicit"
        self.assertEqual(str(paths.current_file()), "/tmp/explicit/core/current")


if __name__ == "__main__":
    unittest.main()
