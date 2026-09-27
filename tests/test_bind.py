"""Bind, sync, unbind: artifacts, modes, idempotency and ignore blocks."""

import os
import subprocess
import unittest

from devteam_support import StoreTestCase

from devteam import bind, gitignore, project, providers, registry, versions
from devteam.errors import ConflictError, EnvError


class BindTest(StoreTestCase):
    def setUp(self):
        super().setUp()
        self.install_version("3.0.0", activate=True)

    def test_bind_creates_identity_artifacts_and_no_framework_copy(self):
        root = self.new_project()
        result = bind.bind(root, provider_names=["claude"])

        self.assertTrue(result["identity_created"])
        self.assertTrue((root / ".claude" / "agents" / "dev-team").exists())
        self.assertTrue((root / ".claude" / "commands" / "devteam").exists())
        # The project holds identity plus the runtime-root pointer — no vendored tree.
        self.assertEqual(
            sorted(p.name for p in (root / project.PROJECT_DIR).iterdir()),
            ["core", "project.json"],
        )
        pointer = root / project.PROJECT_DIR / "core"
        self.assertTrue((pointer / "scripts").is_dir())
        self.assertTrue((pointer / "templates").is_dir())
        entry = registry.get(result["project_id"])
        self.assertEqual(entry["mode"], result["mode"])
        self.assertIsNone(entry["pin"])

    def test_every_skill_is_linked_including_the_depth_one_layout(self):
        root = self.new_project()
        bind.bind(root, provider_names=["claude"])
        linked = sorted(p.name for p in (root / ".claude" / "skills").iterdir())
        self.assertIn("project-context", linked)
        self.assertIn("unit", linked)
        # `skills/skill-creator/SKILL.md` sits one level up; the v2 installer's
        # two-level loop skipped it.
        self.assertIn("skill-creator", linked)

    def test_bind_is_idempotent(self):
        root = self.new_project()
        first = bind.bind(root, provider_names=["claude"])
        second = bind.bind(root, provider_names=["claude"])
        self.assertEqual(first["project_id"], second["project_id"])
        self.assertFalse(second["identity_created"])
        self.assertEqual(len(registry.entries()), 1)
        entries = gitignore.read_managed_entries(root / ".gitignore")
        self.assertEqual(len(entries), len(set(entries)))

    def test_gitignore_block_ignores_memory_but_not_project_json(self):
        root = self.new_project()
        bind.bind(root, provider_names=["claude"])
        entries = gitignore.read_managed_entries(root / ".gitignore")
        self.assertIn(".dev-team-agents/user-data/", entries)
        self.assertNotIn(".dev-team-agents/project.json", entries)

    def test_bind_artifacts_are_excluded_locally_not_in_gitignore(self):
        root = self.new_project()
        bind.bind(root, provider_names=["claude"])
        shared = gitignore.read_managed_entries(root / ".gitignore")
        local = gitignore.read_managed_entries(root / ".git" / "info" / "exclude")
        self.assertNotIn(".claude/agents/dev-team", shared)
        self.assertIn(".claude/agents/dev-team", local)
        # git therefore sees no provider artifact as untracked
        status = subprocess.run(
            ["git", "status", "--porcelain"], cwd=str(root), stdout=subprocess.PIPE, check=True
        ).stdout.decode()
        self.assertNotIn(".claude", status)

    def test_copy_mode_materialises_real_directories(self):
        root = self.new_project()
        result = bind.bind(root, provider_names=["claude"], mode="copy")
        self.assertEqual(result["mode"], "copy")
        target = root / ".claude" / "agents" / "dev-team"
        self.assertFalse(target.is_symlink())
        self.assertTrue((target / "backend-developer.md").is_file())
        self.assertEqual(registry.get(result["project_id"])["mode"], "copy")

    def test_link_mode_points_into_the_resolved_version(self):
        root = self.new_project()
        bind.bind(root, provider_names=["claude"], mode="link")
        target = root / ".claude" / "agents" / "dev-team"
        self.assertTrue(target.is_symlink())
        self.assertIn("versions/3.0.0/agents", os.readlink(str(target)))

    def test_switching_modes_replaces_artifacts_without_touching_identity(self):
        root = self.new_project()
        first = bind.bind(root, provider_names=["claude"], mode="link")
        second = bind.bind(root, provider_names=["claude"], mode="copy")
        self.assertEqual(first["project_id"], second["project_id"])
        self.assertFalse((root / ".claude" / "agents" / "dev-team").is_symlink())

    def test_an_unmanaged_path_in_the_way_is_a_conflict_not_an_overwrite(self):
        root = self.new_project()
        target = root / ".claude" / "agents" / "dev-team"
        target.mkdir(parents=True)
        (target / "mine.md").write_text("user content\n", encoding="utf-8")
        with self.assertRaises(ConflictError):
            bind.bind(root, provider_names=["claude"])
        self.assertTrue((target / "mine.md").is_file())

    def test_pin_survives_a_change_of_current(self):
        self.install_version("3.1.0")
        root = self.new_project()
        result = bind.bind(root, provider_names=["claude"], pin="3.0.0")
        versions.set_current("3.1.0")
        synced = bind.sync_project(result["project_id"])
        self.assertEqual(synced["version"], "3.0.0")

    def test_sync_all_moves_unpinned_projects_only(self):
        self.install_version("3.1.0")
        free = self.new_project("free")
        held = self.new_project("held")
        bind.bind(free, provider_names=["claude"])
        held_result = bind.bind(held, provider_names=["claude"], pin="3.0.0")
        versions.set_current("3.1.0")

        summary = bind.sync_all()
        self.assertEqual(summary["problems"], [])
        by_path = {item["path"]: item["version"] for item in summary["synced"]}
        self.assertEqual(by_path[str(free.resolve())], "3.1.0")
        self.assertEqual(by_path[str(held.resolve())], "3.0.0")
        self.assertEqual(registry.get(held_result["project_id"])["pin"], "3.0.0")

    def test_sync_all_reports_a_missing_path_without_aborting_the_rest(self):
        import shutil

        good = self.new_project("good")
        gone = self.new_project("gone")
        bind.bind(good, provider_names=["claude"])
        bind.bind(gone, provider_names=["claude"])
        shutil.rmtree(str(gone))

        summary = bind.sync_all()
        self.assertEqual(len(summary["synced"]), 1)
        self.assertEqual(len(summary["problems"]), 1)

    def test_unknown_provider_is_rejected(self):
        root = self.new_project()
        with self.assertRaises(Exception):
            bind.bind(root, provider_names=["emacs"])

    def test_unbind_removes_artifacts_but_keeps_identity_and_memory(self):
        root = self.new_project()
        result = bind.bind(root, provider_names=["claude"])
        memory = root / project.PROJECT_DIR / "user-data"
        memory.mkdir(parents=True, exist_ok=True)
        (memory / "session-summary.md").write_text("keep me\n", encoding="utf-8")

        report = bind.unbind(root)
        self.assertFalse((root / ".claude" / "agents" / "dev-team").exists())
        self.assertTrue((root / project.PROJECT_DIR / "project.json").is_file())
        self.assertEqual((memory / "session-summary.md").read_text(encoding="utf-8"), "keep me\n")
        self.assertIsNone(registry.get(result["project_id"]))
        self.assertGreater(len(report["unlinked"]), 0)
        self.assertEqual(report["problems"], [])

    def test_stale_real_directories_are_quarantined_never_deleted(self):
        """A vendored bind followed by a link bind must not destroy the trees."""
        root = self.new_project()
        result = bind.bind(root, provider_names=["claude"], mode="vendored")
        self.assertTrue((root / project.PROJECT_DIR / "agents").is_dir())

        second = bind.bind(root, provider_names=["claude"], mode="link")
        self.assertFalse((root / project.PROJECT_DIR / "agents").exists())
        moved = [item["path"] for item in second["pruned"]["quarantined"]]
        self.assertIn(".dev-team-agents/agents", moved)
        for item in second["pruned"]["quarantined"]:
            self.assertTrue(os.path.isdir(item["to"]), item["to"])

    def test_vendored_mode_uses_relative_links_so_a_clone_resolves_them(self):
        root = self.new_project()
        bind.bind(root, provider_names=["claude"], mode="vendored")
        link = root / ".claude" / "agents" / "dev-team"
        self.assertTrue(link.is_symlink())
        target = os.readlink(str(link))
        self.assertFalse(os.path.isabs(target))
        self.assertEqual(target, "../../.dev-team-agents/agents")

    def test_explicit_link_mode_fails_loudly_when_symlinks_are_impossible(self):
        root = self.new_project()
        original = bind.symlink_supported
        bind.symlink_supported = lambda _root: False
        self.addCleanup(setattr, bind, "symlink_supported", original)
        with self.assertRaises(EnvError):
            bind.resolve_mode("link", root)
        mode, reason = bind.resolve_mode("auto", root)
        self.assertEqual(mode, "copy")
        self.assertIsNotNone(reason)


class ProviderDetectionTest(StoreTestCase):
    def test_detect_defaults_to_claude(self):
        root = self.new_project()
        self.assertEqual(providers.detect(root), ["claude"])

    def test_detect_finds_opencode_and_codex_markers(self):
        root = self.new_project()
        (root / ".opencode").mkdir()
        (root / ".codex").mkdir()
        (root / ".claude").mkdir()
        self.assertEqual(providers.detect(root), ["claude", "opencode", "codex"])


if __name__ == "__main__":
    unittest.main()
