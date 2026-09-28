"""Store layout per platform, and the $DEVTEAM_HOME override."""

import os
import unittest

from devteam_support import StoreTestCase  # noqa: F401  (path bootstrap)

from devteam import paths


class PlatformLayoutTest(unittest.TestCase):
    def setUp(self):
        self._saved = {
            k: os.environ.get(k)
            for k in (
                "DEVTEAM_HOME",
                "DEVTEAM_PLATFORM",
                "APPDATA",
                "LOCALAPPDATA",
                "DEVTEAM_MACHINE_ID",
            )
        }
        os.environ.pop("DEVTEAM_HOME", None)
        os.environ.pop("DEVTEAM_MACHINE_ID", None)

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

    def test_machine_local_paths_resolve_inside_data_dir_on_every_platform(self):
        # `DEVTEAM_MACHINE_ID` short-circuits `machine_id()` before any file I/O, so
        # this can run against the real per-platform `data_dir()` (no `$DEVTEAM_HOME`
        # override) without ever touching a real user directory.
        fixed_id = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
        os.environ[paths.MACHINE_ID_ENV] = fixed_id
        for platform in ("darwin", "win32", "linux"):
            os.environ["DEVTEAM_PLATFORM"] = platform
            if platform == "win32":
                os.environ["APPDATA"] = r"C:\Users\t\AppData\Roaming"
                os.environ["LOCALAPPDATA"] = r"C:\Users\t\AppData\Local"
            data_parts = paths.data_dir().parts
            for resolved in (
                paths.machine_id_file(),
                paths.machine_dir(fixed_id),
                paths.registry_file(fixed_id),
                paths.machine_project_dir("pid", fixed_id),
                paths.locks_dir(),
            ):
                self.assertEqual(
                    resolved.parts[: len(data_parts)], data_parts, (platform, resolved)
                )


class MachineLocalClassifierTest(unittest.TestCase):
    """`is_machine_local_record` / `path_is_machine_local` — the one place that
    decides which side of the portable/machine-local split a record belongs on.
    """

    def test_is_machine_local_record_is_basename_and_case_folded(self):
        # A review found `Credentials.local.json` classified as portable, even
        # though macOS APFS and Windows hand the very same file to anything that
        # opens `credentials.local.json`.
        self.assertTrue(paths.is_machine_local_record("credentials.local.json"))
        self.assertTrue(paths.is_machine_local_record("Credentials.local.json"))
        self.assertTrue(paths.is_machine_local_record("CREDENTIALS.LOCAL.JSON"))
        self.assertTrue(paths.is_machine_local_record(".notifier-state"))
        self.assertTrue(paths.is_machine_local_record("state.json"))
        self.assertFalse(paths.is_machine_local_record("session-summary.md"))
        self.assertFalse(paths.is_machine_local_record("graphify.json"))

    def test_audit_log_is_machine_local(self):
        # ADR-0010: the credential audit trail records reads that happened on THIS
        # machine. Two machines appending to one portable log would need merge
        # semantics nothing here has, so it must classify the same way
        # `credentials.local.json` does.
        self.assertTrue(paths.is_machine_local_record("audit.log"))
        self.assertTrue(paths.is_machine_local_record("AUDIT.LOG"))
        self.assertTrue(paths.path_is_machine_local("projects/pid/audit.log"))

    def test_path_is_machine_local_matches_any_component_not_just_the_first(self):
        # A review found that checking only `Path(rel).parts[0]` sent
        # `env/credentials.local.json` to the portable subtree, because `"env"`
        # itself isn't a machine-local name — only its child is.
        self.assertTrue(paths.path_is_machine_local("env/credentials.local.json"))
        self.assertTrue(paths.path_is_machine_local(".cache/state.json"))
        self.assertTrue(paths.path_is_machine_local("credentials.local.json"))
        self.assertFalse(paths.path_is_machine_local("session-summary.md"))
        self.assertFalse(paths.path_is_machine_local("graphify.json"))
        self.assertFalse(paths.path_is_machine_local("notes/session-summary.md"))


class CredentialPathsTest(StoreTestCase):
    """Where reference layers, secret values and the audit log each live (ADR-0010).

    The reference layer and the value store must resolve to different subtrees —
    that separation is the whole design, so it is pinned here rather than assumed.
    """

    def test_global_and_project_reference_layers_are_distinct_files(self):
        global_file = paths.credentials_file(None)
        project_file = paths.credentials_file("proj-1")
        self.assertEqual(global_file.name, "global.json")
        self.assertEqual(project_file.name, "proj-1.json")
        self.assertEqual(global_file.parent, project_file.parent)
        self.assertEqual(global_file.parent, paths.credentials_dir())

    def test_secrets_dir_is_machine_local_and_separate_from_credentials_dir(self):
        # The reference layer is portable precisely because it holds no value; the
        # value store must never sit inside the tree a portable export would take.
        self.assertNotEqual(paths.secrets_dir(), paths.credentials_dir())
        self.assertTrue(str(paths.secrets_dir()).startswith(str(paths.machine_dir())))
        self.assertFalse(str(paths.credentials_dir()).startswith(str(paths.machine_dir())))

    def test_audit_log_lives_under_this_projects_machine_directory(self):
        log_path = paths.audit_log("proj-1")
        self.assertEqual(log_path.name, "audit.log")
        self.assertEqual(log_path.parent, paths.machine_project_dir("proj-1"))


if __name__ == "__main__":
    unittest.main()
