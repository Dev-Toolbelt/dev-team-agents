"""Bind, sync, unbind: artifacts, modes, idempotency and ignore blocks."""

import os
import subprocess
import unittest
from pathlib import Path

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
        # The project holds identity plus the two runtime links — no vendored tree.
        # Two pointers, not one: layout 2 splits a project's own state into a
        # machine-local directory (`state-dir`) and a portable one (`memory-dir`),
        # and a bind writes both (ADR-0013).
        self.assertEqual(
            sorted(p.name for p in (root / project.PROJECT_DIR).iterdir()),
            ["memory-dir", "project.json", "resolved", "scripts", "state-dir", "templates"],
        )
        for name in ("scripts", "templates"):
            link = root / project.PROJECT_DIR / name
            self.assertTrue(link.is_symlink() and link.is_dir(), name)
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

    def test_unbind_keeps_the_pointers_a_layout_2_project_needs_to_find_its_memory(self):
        """A layout-2 project's memory is in the store, and the two pointers are the only
        record of where. Unbind used to remove them as "generated projections", leaving
        `project.json` still saying `layout: 2` while nothing could resolve the store paths
        — so the next writer fell back to the in-project layout-1 path and created a fresh,
        empty `user-data/state.json` beside a store copy holding the real state. Observed on
        this repository's own unbind.
        """
        root = self.new_project()
        result_bind = bind.bind(root, provider_names=["claude"])
        pid = result_bind["project_id"]
        self.assertEqual(project.layout(root), project.CURRENT_LAYOUT)
        state_pointer = root / project.PROJECT_DIR / project.STATE_DIR_POINTER
        memory_pointer = root / project.PROJECT_DIR / project.MEMORY_DIR_POINTER
        before = state_pointer.read_text(encoding="utf-8")
        self.assertTrue(before.strip())

        result = bind.unbind(root)

        self.assertTrue(state_pointer.exists(), "state-dir must survive an unbind")
        self.assertTrue(memory_pointer.exists(), "memory-dir must survive an unbind")
        self.assertEqual(state_pointer.read_text(encoding="utf-8"), before)
        # Reported as kept, not silently left behind.
        self.assertIn(".dev-team-agents/state-dir", result["kept"])
        self.assertIn(".dev-team-agents/memory-dir", result["kept"])
        self.assertNotIn(".dev-team-agents/state-dir", result["unlinked"])
        # And still ignored, or the unbind trades two untracked files for a clean block.
        local = gitignore.read_managed_entries(root / ".git" / "info" / "exclude")
        self.assertIn(".dev-team-agents/state-dir", local)
        self.assertIn(".dev-team-agents/memory-dir", local)
        # The rest of the block is gone — this is still an unbind.
        self.assertNotIn(".claude/agents/dev-team", local)

    def test_unbind_removes_the_directories_it_emptied(self):
        """An unbind used to leave `.claude/agents`, `.claude/commands`, `.claude/skills`
        and `.dev-team-agents/resolved` behind as empty directories — four directories the
        project did not have before the bind and does not need after it.
        """
        root = self.new_project()
        bind.bind(root, provider_names=["claude"])
        for rel in (".claude/agents", ".claude/commands", ".claude/skills",
                    ".dev-team-agents/resolved"):
            self.assertTrue((root / rel).is_dir(), rel)

        result = bind.unbind(root)

        for rel in (".claude/agents", ".claude/commands", ".claude/skills",
                    ".dev-team-agents/resolved"):
            self.assertFalse((root / rel).exists(), "{} should have been pruned".format(rel))
            self.assertIn(rel, result["removed_dirs"])
        # `.dev-team-agents` itself survives: `project.json` and the two pointers are in it.
        self.assertTrue((root / ".dev-team-agents").is_dir())
        self.assertTrue((root / ".claude" / "settings.json").exists())

    def test_unbind_keeps_a_directory_that_still_holds_something_of_the_user_s(self):
        """`rmdir` is the whole safety argument: a directory with anything left in it
        refuses to go, so this needs no knowledge of what a user may have added.
        """
        root = self.new_project()
        bind.bind(root, provider_names=["claude"])
        mine = root / ".claude" / "skills" / "my-own-notes.md"
        mine.write_text("mine\n", encoding="utf-8")

        result = bind.unbind(root)

        self.assertTrue(mine.exists(), "a user's own file must survive")
        self.assertTrue((root / ".claude" / "skills").is_dir())
        self.assertNotIn(".claude/skills", result["removed_dirs"])
        # The siblings that really were empty are still pruned.
        self.assertIn(".claude/agents", result["removed_dirs"])

    def test_unbind_still_removes_the_resolved_preference_projection(self):
        """The fix must not turn into "keep every projection". `resolved/preferences.json`
        is regenerated from the three-layer cascade, carries nothing of its own, and has no
        reason to outlive the bind.
        """
        root = self.new_project()
        bind.bind(root, provider_names=["claude"])
        resolved = root / project.PROJECT_DIR / "resolved" / "preferences.json"
        self.assertTrue(resolved.exists())
        result = bind.unbind(root)
        self.assertFalse(resolved.exists())
        self.assertNotIn(".dev-team-agents/resolved/preferences.json", result["kept"])

    def test_gitignore_block_never_ignores_project_json(self):
        """`project.json` is committed identity (ADR-0008), so it must never reach the
        managed block. This used to also assert `.dev-team-agents/user-data/` was in the
        block, which **pinned a bug**: a fresh bind records layout 2, where memory lives in
        the store and the project has no `user-data/` at all, so the line named a directory
        that never existed. Writing it unconditionally also meant a sync after `upgrade`
        put back the two lines `upgrade.RETIRED_GITIGNORE_ENTRIES` had just retired. The
        layout-1 direction is asserted separately, below.
        """
        root = self.new_project()
        bind.bind(root, provider_names=["claude"])
        entries = gitignore.read_managed_entries(root / ".gitignore")
        self.assertNotIn(".dev-team-agents/project.json", entries)
        self.assertEqual(project.layout(root), project.CURRENT_LAYOUT)
        self.assertNotIn(".dev-team-agents/user-data/", entries)
        # The entries that are not about the legacy directory are still written.
        self.assertIn(".dev-team-agents/resolved/", entries)

    def test_gitignore_block_ignores_the_memory_directory_on_layout_1(self):
        """The other direction, so the fix above cannot become "never write them": while a
        project's memory is still inside it, the directory line and the negation that keeps
        `graphify.json` tracked within it both have to be there.
        """
        root = self.new_project()
        bind.bind(root, provider_names=["claude"])
        project.set_layout(root, project.LAYOUT_MEMORY_IN_PROJECT)
        entries = bind.project_gitignore_entries(root)
        self.assertIn(".dev-team-agents/user-data/", entries)
        self.assertIn("!.dev-team-agents/user-data/graphify.json", entries)

    def test_bind_artifacts_are_excluded_locally_not_in_gitignore(self):
        root = self.new_project()
        bind.bind(root, provider_names=["claude"])
        shared = gitignore.read_managed_entries(root / ".gitignore")
        local = gitignore.read_managed_entries(root / ".git" / "info" / "exclude")
        self.assertNotIn(".claude/agents/dev-team", shared)
        self.assertIn(".claude/agents/dev-team", local)
        # git therefore sees no provider artifact as untracked — only the project's own
        # settings file, which bind merged its hooks into and the team must commit.
        status = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=all"],
            cwd=str(root),
            stdout=subprocess.PIPE,
            check=True,
        ).stdout.decode()
        claude_lines = [line for line in status.splitlines() if ".claude" in line]
        self.assertEqual(claude_lines, ["?? .claude/settings.json"])

    def test_the_settings_file_is_never_excluded_so_add_all_stages_it(self):
        # It used to be in the exclude block, so on a project that had not committed it
        # yet `git add -A` skipped the one file that carries the hooks to a teammate.
        root = self.new_project()
        bind.bind(root, provider_names=["claude"])
        local = gitignore.read_managed_entries(root / ".git" / "info" / "exclude")
        self.assertNotIn(".claude/settings.json", local)
        subprocess.run(["git", "add", "-A"], cwd=str(root), check=True)
        staged = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            cwd=str(root),
            stdout=subprocess.PIPE,
            check=True,
        ).stdout.decode()
        self.assertIn(".claude/settings.json", staged.splitlines())

    def test_sync_drops_the_settings_line_from_an_older_exclude_block(self):
        root = self.new_project()
        result = bind.bind(root, provider_names=["claude"])
        exclude = root / ".git" / "info" / "exclude"
        stale = gitignore.read_managed_entries(exclude) + [".claude/settings.json"]
        gitignore.apply_managed_block(exclude, sorted(stale))
        bind.sync_project(result["project_id"])
        self.assertNotIn(".claude/settings.json", gitignore.read_managed_entries(exclude))
        self.assertIn(".claude/agents/dev-team", gitignore.read_managed_entries(exclude))

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
        # `.as_posix()`, not the raw `os.readlink()` string: on Windows, a
        # symlink's absolute target always reads back with the `\\?\`
        # extended-length prefix — that is how NTFS reparse points store an
        # absolute substitute name — regardless of what `os.symlink` was given.
        # The prefix only changes the drive/root component; the rest of the
        # path, which is what this assertion actually cares about, is unaffected.
        self.assertIn("versions/3.0.0/agents", Path(os.readlink(str(target))).as_posix())

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
        from devteam_support import rmtree

        good = self.new_project("good")
        gone = self.new_project("gone")
        bind.bind(good, provider_names=["claude"])
        bind.bind(gone, provider_names=["claude"])
        rmtree(str(gone))

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
