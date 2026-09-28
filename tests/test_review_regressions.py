"""One test per defect the M1 review found.

Named after the failure rather than the function, so a regression report says
what broke instead of which unit it lived in.
"""

import json
import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

from devteam_support import StoreTestCase

from devteam import bind, gitignore, hooks, jsonio, lock, migrate, paths, project, registry, versions
from devteam.errors import ConflictError, EnvError, UsageError


class ContainmentTest(StoreTestCase):
    """A committed symlink must not relocate or delete anything."""

    def setUp(self):
        super().setUp()
        self.install_version("3.0.0", activate=True)

    def test_symlinked_claude_directory_is_refused_not_followed(self):
        root = self.new_project()
        outside = self.tmp / "outside"
        outside.mkdir()
        (root / ".claude").symlink_to(outside, target_is_directory=True)

        with self.assertRaises(ConflictError):
            bind.bind(root, provider_names=["claude"])
        self.assertEqual(sorted(p.name for p in outside.iterdir()), [])

    def test_symlinked_install_dir_cannot_destroy_the_target(self):
        root = self.new_project()
        victim = self.tmp / "documents"
        (victim / "scripts").mkdir(parents=True)
        (victim / "scripts" / "my-work.sh").write_text("IRREPLACEABLE\n", encoding="utf-8")
        (root / project.PROJECT_DIR).symlink_to(victim, target_is_directory=True)

        with self.assertRaises(ConflictError):
            bind.bind(root, provider_names=["claude"], mode="vendored")
        self.assertEqual(
            (victim / "scripts" / "my-work.sh").read_text(encoding="utf-8"), "IRREPLACEABLE\n"
        )

    def test_bind_artifact_symlink_into_the_store_is_not_mistaken_for_an_escape(self):
        """The containment check must not follow the artifact it is checking."""
        root = self.new_project()
        bind.bind(root, provider_names=["claude"])
        # A second bind re-materialises over its own links; this used to refuse.
        bind.bind(root, provider_names=["claude"])
        self.assertTrue((root / ".claude" / "agents" / "dev-team").is_symlink())


class NoDestructionTest(StoreTestCase):
    """Real content is quarantined; only symlinks are unlinked."""

    def setUp(self):
        super().setUp()
        self.install_version("3.0.0", activate=True)

    def _planted(self, root, relative, marker):
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(marker, encoding="utf-8")
        return target

    def test_unbind_quarantines_user_files_inside_a_copy_artifact(self):
        root = self.new_project()
        bind.bind(root, provider_names=["claude"], mode="copy")
        planted = self._planted(root, Path(".claude/skills/unit/my-notes.md"), "COPYLOSS\n")

        report = bind.unbind(root)
        self.assertFalse(planted.exists())
        self.assertTrue(report["quarantined"])
        survivors = [
            path
            for entry in report["quarantined"]
            for path in Path(entry["to"]).rglob("my-notes.md")
        ]
        self.assertTrue(survivors, "the planted file must exist in quarantine")
        self.assertEqual(survivors[0].read_text(encoding="utf-8"), "COPYLOSS\n")

    def test_unbind_quarantines_user_files_inside_a_vendored_tree(self):
        root = self.new_project()
        bind.bind(root, provider_names=["claude"], mode="vendored")
        planted = self._planted(
            root, Path(project.PROJECT_DIR) / "agents" / "my-own.md", "IRREPLACEABLE\n"
        )

        report = bind.unbind(root)
        self.assertFalse(planted.exists())
        survivors = [
            path
            for entry in report["quarantined"]
            for path in Path(entry["to"]).rglob("my-own.md")
        ]
        self.assertTrue(survivors)
        self.assertEqual(survivors[0].read_text(encoding="utf-8"), "IRREPLACEABLE\n")

    def test_resync_quarantines_instead_of_deleting(self):
        root = self.new_project()
        result = bind.bind(root, provider_names=["claude"], mode="copy")
        planted = self._planted(root, Path(".claude/skills/unit/keep.md"), "SYNCCOPY\n")

        bind.sync_project(result["project_id"])
        quarantine_root = self.home / "data" / "quarantine"
        survivors = list(quarantine_root.rglob("keep.md"))
        self.assertTrue(survivors, "re-sync must not delete a real directory outright")
        self.assertEqual(survivors[0].read_text(encoding="utf-8"), "SYNCCOPY\n")

    def test_unbind_with_a_pathless_manifest_entry_does_not_delete_the_project(self):
        root = self.new_project()
        result = bind.bind(root, provider_names=["claude"])
        (root / "src").mkdir()
        (root / "src" / "main.py").write_text("print('mine')\n", encoding="utf-8")

        manifest_path = bind.manifest_file(result["project_id"])
        manifest = jsonio.read_json(manifest_path)
        manifest["artifacts"].append({"path": "", "kind": "copy"})
        jsonio.write_json_atomic(manifest_path, manifest)

        report = bind.unbind(root)
        self.assertTrue(root.is_dir())
        self.assertTrue((root / "src" / "main.py").is_file())
        self.assertTrue(any(p["path"] == "" for p in report["problems"]))


class ManagedBlockNewlineTest(StoreTestCase):
    def test_crlf_file_keeps_crlf(self):
        target = self.tmp / ".gitignore"
        target.write_bytes(b"node_modules\r\n*.log\r\n")
        gitignore.apply_managed_block(target, [".claude/agents/dev-team"])
        raw = target.read_bytes()
        self.assertTrue(raw.startswith(b"node_modules\r\n*.log\r\n"))
        self.assertEqual(raw.count(b"\r\n"), raw.count(b"\n"))

    def test_crlf_application_is_idempotent(self):
        target = self.tmp / ".gitignore"
        target.write_bytes(b"dist\r\n")
        entries = [".claude/agents/dev-team"]
        gitignore.apply_managed_block(target, entries)
        changed, action = gitignore.apply_managed_block(target, entries)
        self.assertFalse(changed)
        self.assertEqual(action, "unchanged")


class PinTest(StoreTestCase):
    def setUp(self):
        super().setUp()
        self.install_version("3.0.0", activate=True)
        self.install_version("3.1.0")

    def test_plain_rebind_keeps_an_existing_pin(self):
        root = self.new_project()
        result = bind.bind(root, provider_names=["claude"], pin="3.0.0")
        versions.set_current("3.1.0")

        again = bind.bind(root, provider_names=["claude"])
        self.assertEqual(again["version"], "3.0.0")
        self.assertEqual(registry.get(result["project_id"])["pin"], "3.0.0")

    def test_release_then_rebind_follows_current(self):
        root = self.new_project()
        result = bind.bind(root, provider_names=["claude"], pin="3.0.0")
        registry.set_pin(result["project_id"], None)
        versions.set_current("3.1.0")
        again = bind.bind(root, provider_names=["claude"])
        self.assertEqual(again["version"], "3.1.0")


class VersionStoreGuardTest(StoreTestCase):
    def test_store_use_refuses_an_incomplete_version(self):
        """A hand-made directory is listed (so doctor can flag it) but not activated."""
        self.install_version("3.0.0", activate=True)
        (versions.version_dir("3.9.0")).mkdir(parents=True)
        self.assertIn("3.9.0", versions.installed())
        with self.assertRaises(EnvError):
            versions.set_current("3.9.0")
        self.assertEqual(versions.current(), "3.0.0")

    def test_staging_directory_is_not_reported_as_a_version(self):
        self.install_version("3.0.0", activate=True)
        (paths.versions_dir() / "3.2.0.incoming").mkdir(parents=True)
        self.assertEqual(versions.installed(), ["3.0.0"])

    def test_failed_force_install_leaves_the_previous_tree_intact(self):
        self.install_version("3.0.0", activate=True)
        broken = self.tmp / "broken"
        broken.mkdir()
        with self.assertRaises(UsageError):
            versions.install_from_tree(broken, version="3.0.0", force=True)
        self.assertTrue((versions.version_dir("3.0.0") / "agents").is_dir())


class LockOwnershipTest(StoreTestCase):
    def test_a_stolen_lock_is_not_released_by_its_previous_holder(self):
        first = lock.store_lock("registry")
        first.acquire()
        # Simulate the holder being judged stale and the lock re-taken.
        owner = first.path / "owner.json"
        owner.write_text(json.dumps({"pid": 1, "acquired_at": 0, "token": "other"}), encoding="utf-8")

        first.release()
        self.assertTrue(first.lost)
        self.assertTrue(first.path.is_dir(), "the new holder's lock must survive")

    def test_a_live_holder_is_never_judged_stale(self):
        held = lock.store_lock("core")
        held.acquire()
        self.addCleanup(held.release)
        owner = held.path / "owner.json"
        body = json.loads(owner.read_text(encoding="utf-8"))
        body["acquired_at"] = 0  # ancient, but this process is alive
        owner.write_text(json.dumps(body), encoding="utf-8")

        taker = lock.Lock(held.path, timeout=0.3, stale_after=0.1)
        with self.assertRaises(ConflictError):
            taker.acquire()


class HooksTest(StoreTestCase):
    def setUp(self):
        super().setUp()
        self.install_version("3.0.0", activate=True)

    def test_bind_registers_all_four_dispatchers(self):
        root = self.new_project()
        bind.bind(root, provider_names=["claude"])
        settings = jsonio.read_json(root / hooks.SETTINGS_FILE)
        for event, script in hooks.EVENTS:
            commands = [
                hook["command"]
                for entry in settings["hooks"][event]
                for hook in entry["hooks"]
            ]
            self.assertTrue(any(script in command for command in commands), event)
            self.assertTrue(any("core/scripts/hooks" in command for command in commands))
        self.assertIs(settings["includeCoAuthoredBy"], False)

    def test_wiring_preserves_unrelated_settings_and_does_not_duplicate(self):
        root = self.new_project()
        settings_path = root / hooks.SETTINGS_FILE
        jsonio.write_json_atomic(
            settings_path,
            {"model": "opus", "hooks": {"Stop": [{"hooks": [{"type": "command", "command": "mine.sh"}]}]}},
            mode=0o644,
            dir_mode=None,
        )
        bind.bind(root, provider_names=["claude"])
        bind.bind(root, provider_names=["claude"])

        settings = jsonio.read_json(settings_path)
        self.assertEqual(settings["model"], "opus")
        stop_commands = [
            hook["command"] for entry in settings["hooks"]["Stop"] for hook in entry["hooks"]
        ]
        self.assertIn("mine.sh", stop_commands)
        self.assertEqual(sum("stop.sh" in c for c in stop_commands), 1)

    def test_a_v2_hook_path_is_rewritten_in_place(self):
        root = self.new_project()
        legacy = "env -u BASH_ENV -u ENV .dev-team-agents/scripts/hooks/stop.sh"
        jsonio.write_json_atomic(
            root / hooks.SETTINGS_FILE,
            {"hooks": {"Stop": [{"hooks": [{"type": "command", "command": legacy}]}]}},
            mode=0o644,
            dir_mode=None,
        )
        bind.bind(root, provider_names=["claude"])
        settings = jsonio.read_json(root / hooks.SETTINGS_FILE)
        commands = [
            hook["command"] for entry in settings["hooks"]["Stop"] for hook in entry["hooks"]
        ]
        self.assertEqual(len(commands), 1)
        self.assertIn("core/scripts/hooks/stop.sh", commands[0])

    def test_unbind_removes_only_our_hook_entries(self):
        root = self.new_project()
        settings_path = root / hooks.SETTINGS_FILE
        jsonio.write_json_atomic(
            settings_path, {"model": "opus"}, mode=0o644, dir_mode=None
        )
        bind.bind(root, provider_names=["claude"])
        bind.unbind(root)

        settings = jsonio.read_json(settings_path)
        self.assertTrue(settings_path.is_file(), "settings.json belongs to the project")
        self.assertEqual(settings["model"], "opus")
        self.assertEqual(hooks.registered_events(root), [])


class RuntimeRootTest(StoreTestCase):
    def test_project_relative_framework_paths_resolve(self):
        self.install_version("3.0.0", activate=True)
        root = self.new_project()
        bind.bind(root, provider_names=["claude"])
        pointer = root / project.PROJECT_DIR / "core"
        # The paths 116 shipped references use.
        self.assertTrue((pointer / "scripts").is_dir())
        self.assertTrue((pointer / "templates" / "plan-template.md").is_file())
        self.assertTrue((pointer / "agents").is_dir())


class FileModeTest(StoreTestCase):
    def test_committed_files_are_readable_and_store_files_are_not(self):
        self.install_version("3.0.0", activate=True)
        root = self.new_project()
        bind.bind(root, provider_names=["claude"])

        project_mode = (root / project.PROJECT_DIR / "project.json").stat().st_mode & 0o777
        self.assertEqual(project_mode, 0o644)
        registry_mode = paths.registry_file().stat().st_mode & 0o777
        self.assertEqual(registry_mode, 0o600)
        data_mode = (self.home / "data").stat().st_mode & 0o777
        self.assertEqual(data_mode, 0o700)
        # The machine subtree is created on the same terms as the rest of the store:
        # it holds the registry, so a group-readable directory would expose the list
        # of every project on the machine.
        machine_mode = paths.machine_dir().stat().st_mode & 0o777
        self.assertEqual(machine_mode, 0o700)
        machine_id_mode = paths.machine_id_file().stat().st_mode & 0o777
        self.assertEqual(machine_id_mode, 0o600)


class WorktreeTest(StoreTestCase):
    def setUp(self):
        super().setUp()
        self.install_version("3.0.0", activate=True)

    @staticmethod
    def _git(root, *args):
        subprocess.run(
            ["git", *args],
            cwd=str(root),
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=dict(
                os.environ,
                GIT_AUTHOR_NAME="t",
                GIT_AUTHOR_EMAIL="t@e",
                GIT_COMMITTER_NAME="t",
                GIT_COMMITTER_EMAIL="t@e",
            ),
        )

    def _commit_identity(self, root):
        """project.json is committed — that is what carries identity to a worktree."""
        self._git(root, "add", "-f", str(Path(project.PROJECT_DIR) / "project.json"))
        self._git(root, "commit", "-qm", "devteam identity")

    def _worktree(self, root, name="wt"):
        target = self.tmp / name
        subprocess.run(
            ["git", "worktree", "add", "-q", str(target), "-b", name],
            cwd=str(root),
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return target

    def test_a_linked_worktree_binds_without_an_identity_collision(self):
        root = self.new_project("mainrepo")
        result = bind.bind(root, provider_names=["claude"])
        self._commit_identity(root)
        worktree = self._worktree(root)

        wt_result = bind.bind(worktree, provider_names=["claude"])
        self.assertEqual(wt_result["project_id"], result["project_id"])
        entry = registry.get(result["project_id"])
        self.assertEqual(entry["path"], str(root.resolve()))
        self.assertIn(str(worktree.resolve()), entry["worktrees"])
        self.assertEqual(len(registry.entries()), 1)

    def test_unbinding_a_worktree_keeps_the_shared_exclude_block(self):
        root = self.new_project("mainrepo")
        bind.bind(root, provider_names=["claude"])
        self._commit_identity(root)
        worktree = self._worktree(root)
        bind.bind(worktree, provider_names=["claude"])

        exclude = bind._local_exclude_file(root)
        before = gitignore.read_managed_entries(exclude)
        self.assertTrue(before)

        bind.unbind(worktree)
        self.assertEqual(gitignore.read_managed_entries(exclude), before)


class ConcurrencyTest(StoreTestCase):
    def test_two_parallel_binds_both_land_in_the_registry(self):
        """The spec's composition scenario, which no unit test covered."""
        self.install_version("3.0.0", activate=True)
        first = self.new_project("par-one")
        second = self.new_project("par-two")

        processes = [
            subprocess.Popen(
                [sys.executable, str(Path(__file__).resolve().parent.parent / "scripts" / "cli" / "devteam"), "bind", str(path), "--json"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=dict(os.environ),
            )
            for path in (first, second)
        ]
        for process in processes:
            out, err = process.communicate(timeout=120)
            self.assertEqual(process.returncode, 0, err.decode("utf-8", "replace"))
            json.loads(out)

        entries = registry.entries()
        self.assertEqual(len(entries), 2)
        bound = {entry["path"] for entry in entries.values()}
        self.assertEqual(bound, {str(first.resolve()), str(second.resolve())})


class LegacyV2MigrationTest(StoreTestCase):
    """Migration is tested against a HAND-BUILT v2 layout, not the new code's output.

    The original fixture created its "v2 install" with `bind(mode="vendored")`, which
    never writes a `settings.json`, a `user-data/state.json` or the v2 hook paths — so
    it could not catch that migrating a real v2 project left every hook pointing at a
    directory the migration had just moved to quarantine.
    """

    def setUp(self):
        super().setUp()
        self.install_version("3.0.0", activate=True)

    def _v2_project(self, name="legacy"):
        root = self.new_project(name)
        install = root / project.PROJECT_DIR
        for tree in ("agents", "commands", "skills", "scripts", "templates"):
            (install / tree).mkdir(parents=True, exist_ok=True)
            (install / tree / "file.md").write_text("# v2 {}\n".format(tree), encoding="utf-8")
        (install / "agents" / "MY-CUSTOM.md").write_text("# hand written\n", encoding="utf-8")
        (install / "scripts" / "hooks").mkdir(parents=True, exist_ok=True)
        (install / "scripts" / "hooks" / "stop.sh").write_text("true\n", encoding="utf-8")
        (install / "user-data").mkdir(parents=True, exist_ok=True)
        (install / "user-data" / "session-summary.md").write_text(
            "## 2026-01-01 | v2 memory\n", encoding="utf-8"
        )
        legacy_command = "env -u BASH_ENV -u ENV .dev-team-agents/scripts/hooks/{}"
        jsonio.write_json_atomic(
            root / hooks.SETTINGS_FILE,
            {
                "includeCoAuthoredBy": False,
                "model": "opus",
                "hooks": {
                    "Stop": [
                        {"hooks": [{"type": "command", "command": legacy_command.format("stop.sh")}]}
                    ],
                    "SessionStart": [
                        {
                            "hooks": [
                                {
                                    "type": "command",
                                    "command": legacy_command.format("session-start.sh"),
                                }
                            ]
                        }
                    ],
                },
            },
            mode=0o644,
            dir_mode=None,
        )
        return root

    def test_migration_rewires_hooks_that_pointed_at_the_quarantined_tree(self):
        root = self._v2_project()
        migrate.apply(root)

        settings = jsonio.read_json(root / hooks.SETTINGS_FILE)
        for event, script in hooks.EVENTS:
            commands = [
                hook["command"]
                for entry in settings["hooks"][event]
                for hook in entry["hooks"]
            ]
            self.assertEqual(len(commands), 1, event)
            self.assertIn("core/scripts/hooks/" + script, commands[0])
            # The path the rewritten hook names must actually exist.
            self.assertTrue((root / commands[0].split()[-1]).exists(), commands[0])
        self.assertEqual(settings["model"], "opus")

    def test_migration_quarantines_a_hand_written_file_instead_of_deleting_it(self):
        root = self._v2_project()
        result = migrate.apply(root)
        survivors = [
            path
            for entry in result["quarantined"]
            for path in Path(entry["to"]).rglob("MY-CUSTOM.md")
        ]
        self.assertTrue(survivors, "a hand-written agent must survive in quarantine")
        self.assertEqual(survivors[0].read_text(encoding="utf-8"), "# hand written\n")

    def test_migration_preserves_memory(self):
        root = self._v2_project()
        migrate.apply(root)
        memory = root / project.PROJECT_DIR / "user-data" / "session-summary.md"
        self.assertEqual(memory.read_text(encoding="utf-8"), "## 2026-01-01 | v2 memory\n")


class DesignRuleTest(unittest.TestCase):
    """The rows in `docs/development/reuse-guidelines.md` that no regex can enforce.

    Each of those rows says a violation is the *absence* of a call, so nothing in the
    lint can see it. A test that scans the tree can, as long as it names the sanctioned
    callers explicitly — and the point of naming them is that adding one is then a
    deliberate edit here rather than a line that slips in unreviewed.
    """

    PACKAGE = Path(__file__).resolve().parent.parent / "scripts" / "lib" / "devteam"

    def test_only_the_credential_resolver_reads_a_secret_backend(self):
        # `devteam_credential_read`: every credential value is read through
        # `creds.get_value`, which resolves the layer, checks scope and audits. A module
        # that reaches `secrets.get` directly gets the value with none of that, and the
        # audit trail then has a hole exactly where someone would look for one.
        #
        # `creds.py` is the sanctioned home: `get_value` is the audited path,
        # `import_file` verifies a value it just wrote, and `check` probes presence for
        # `doctor` without disclosing it. All three are inside the resolver.
        allowed = {"creds.py", "secrets.py"}
        offenders = []
        for module in sorted(self.PACKAGE.glob("*.py")):
            if module.name in allowed:
                continue
            text = module.read_text(encoding="utf-8")
            for lineno, line in enumerate(text.splitlines(), 1):
                stripped = line.strip()
                if stripped.startswith("#"):
                    continue
                if "secrets.get(" in line or "secrets_module.get(" in line:
                    offenders.append("{}:{}".format(module.name, lineno))
        self.assertEqual(
            offenders,
            [],
            "these read a secret backend outside creds.py, bypassing the scope check and "
            "the audit line: {}".format(offenders),
        )


if __name__ == "__main__":
    unittest.main()
