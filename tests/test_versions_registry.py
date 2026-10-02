"""The versioned core, pinning, garbage collection and the registry."""

import unittest

from devteam_support import StoreTestCase

from devteam import bind, paths, registry, versions
from devteam.errors import ConflictError, EnvError, UsageError


class VersionStoreTest(StoreTestCase):
    def test_install_detects_the_version_from_the_changelog(self):
        version = versions.install_from_tree(self.source)
        self.assertEqual(version, "3.0.0")
        self.assertTrue((versions.version_dir("3.0.0") / "agents").is_dir())

    def test_first_install_becomes_current_and_later_ones_do_not(self):
        self.install_version("3.0.0")
        self.assertEqual(versions.current(), "3.0.0")
        self.install_version("3.1.0")
        self.assertEqual(versions.current(), "3.0.0")

    def test_reinstalling_without_force_is_a_conflict(self):
        versions.install_from_tree(self.source, version="3.0.0")
        with self.assertRaises(ConflictError):
            versions.install_from_tree(self.source, version="3.0.0")

    def test_rejects_a_tree_that_is_not_dev_team_agents(self):
        empty = self.tmp / "empty"
        empty.mkdir()
        with self.assertRaises(UsageError):
            versions.install_from_tree(empty, version="3.0.0")

    def test_rejects_a_non_semver_version(self):
        with self.assertRaises(UsageError):
            versions.install_from_tree(self.source, version="latest")
        for sloppy in ("1.2.3-", "1.2.3\n"):
            with self.subTest(version=sloppy):
                with self.assertRaises(UsageError):
                    versions.install_from_tree(self.source, version=sloppy)

    def test_hostile_version_operands_are_rejected(self):
        self.install_version("3.0.0")
        for bad in ("../x", "/abs", "a/b", "..", "", "-x", "3.0.0/../..", "3.0", "..\\x", None):
            with self.subTest(version=bad):
                # Typed on the command line: a usage error.
                with self.assertRaises(UsageError):
                    paths.validate_version(bad)
                # Read back from the store: a broken store, which doctor reports.
                with self.assertRaises(EnvError):
                    versions.require(bad)
                with self.assertRaises(EnvError):
                    versions.resolve(bad or "..")

    def test_non_ascii_digits_are_not_a_version(self):
        self.assertFalse(paths.is_version_name("\u0661.\u0662.\u0663"))

    def test_a_stray_directory_the_guard_refuses_is_not_listed_as_installed(self):
        self.install_version("3.0.0")
        (paths.versions_dir() / "1.2.3-").mkdir()
        self.assertEqual(versions.installed(), ["3.0.0"])

    def test_valid_version_names_still_resolve(self):
        self.install_version("3.0.0")
        self.assertEqual(versions.resolve("3.0.0"), "3.0.0")
        self.assertTrue(versions.require("3.0.0").is_dir())

    def test_semver_ordering_is_numeric_not_lexicographic(self):
        for version in ("2.9.0", "2.10.0", "2.10.1"):
            self.install_version(version)
        self.assertEqual(versions.installed(), ["2.9.0", "2.10.0", "2.10.1"])

    def test_a_pre_release_sorts_before_its_release_per_semver(self):
        for version in ("2.49.0", "2.49.0-dev.10", "2.48.0", "2.49.0-dev.2", "2.49.0-alpha"):
            self.install_version(version)
        self.assertEqual(
            versions.installed(), ["2.48.0", "2.49.0-alpha", "2.49.0-dev.2", "2.49.0-dev.10", "2.49.0"]
        )

    def test_current_must_point_at_an_installed_version(self):
        self.install_version("3.0.0")
        with self.assertRaises(EnvError):
            versions.set_current("9.9.9")

    def test_resolve_without_any_version_is_an_environment_error(self):
        with self.assertRaises(EnvError):
            versions.resolve()

    def test_a_partial_install_never_becomes_visible(self):
        broken = self.tmp / "broken"
        broken.mkdir()
        for name in versions.CORE_TREES:
            (broken / name).mkdir()
        (broken / "skills").rmdir()
        with self.assertRaises(UsageError):
            versions.install_from_tree(broken, version="4.0.0")
        self.assertNotIn("4.0.0", versions.installed())


class GarbageCollectionTest(StoreTestCase):
    def test_gc_keeps_current_and_every_pinned_version(self):
        self.install_version("3.0.0", activate=True)
        self.install_version("3.1.0")
        self.install_version("3.2.0")
        versions.set_current("3.2.0")
        project_root = self.new_project("pinned")
        bind.bind(project_root, provider_names=["claude"], pin="3.0.0")

        preview = versions.gc(dry_run=True)
        self.assertEqual(preview["would_remove"], ["3.1.0"])
        self.assertEqual(preview["removed"], [])

        applied = versions.gc(dry_run=False)
        self.assertEqual(applied["removed"], ["3.1.0"])
        self.assertEqual(sorted(versions.installed()), ["3.0.0", "3.2.0"])


class RegistryTest(StoreTestCase):
    def test_upsert_then_update_keeps_one_entry(self):
        root = self.new_project()
        registry.upsert("id-1", root, ["claude"], "link")
        registry.upsert("id-1", root, ["claude", "codex"], "copy")
        entries = registry.entries()
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries["id-1"]["mode"], "copy")
        self.assertEqual(entries["id-1"]["providers"], ["claude", "codex"])

    def test_same_identity_at_a_second_existing_path_is_refused(self):
        first = self.new_project("one")
        second = self.new_project("two")
        registry.upsert("id-1", first, ["claude"], "link")
        with self.assertRaises(ConflictError):
            registry.upsert("id-1", second, ["claude"], "link")

    def test_relocate_moves_an_identity_to_a_new_path(self):
        first = self.new_project("one")
        second = self.new_project("two")
        registry.upsert("id-1", first, ["claude"], "link")
        previous, now = registry.relocate("id-1", second)
        self.assertEqual(previous, str(first.resolve()))
        self.assertEqual(now, str(second.resolve()))
        self.assertEqual(len(registry.entries()), 1)

    def test_rejects_an_unknown_mode(self):
        with self.assertRaises(EnvError):
            registry.upsert("id-1", self.new_project(), ["claude"], "teleport")

    def test_malformed_registry_is_reported_not_replaced(self):
        from devteam import paths

        paths.registry_file().parent.mkdir(parents=True, exist_ok=True)
        paths.registry_file().write_text("[]", encoding="utf-8")
        with self.assertRaises(EnvError):
            registry.entries()


if __name__ == "__main__":
    unittest.main()
