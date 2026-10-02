"""v2 -> v3 migration, and the diagnostics that reconcile identity."""

import json
import os
import shutil
import subprocess
import unittest
from pathlib import Path

from devteam_support import StoreTestCase

from devteam import bind, doctor, migrate, project, quarantine, registry, versions
from devteam.errors import ConflictError, UsageError


class MigrationTest(StoreTestCase):
    def setUp(self):
        super().setUp()
        self.install_version("3.0.0", activate=True)

    def _legacy_project(self, name="legacy"):
        """A project that looks exactly like a v2 vendored install."""
        root = self.new_project(name)
        bind.bind(root, provider_names=["claude"], mode="vendored")
        memory = root / project.PROJECT_DIR / "user-data"
        memory.mkdir(parents=True, exist_ok=True)
        (memory / "session-summary.md").write_text("## old entry\n", encoding="utf-8")
        (root / "docs" / "note.md").write_text("project knowledge\n", encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=str(root), check=True, stdout=subprocess.DEVNULL)
        subprocess.run(
            ["git", "commit", "-qm", "install"],
            cwd=str(root),
            check=True,
            stdout=subprocess.DEVNULL,
            env=self._git_env(),
        )
        bind.unbind(root, keep_artifacts=True)
        return root

    def _install_sh_project(self, name="installed"):
        """A v2 install as `install.sh` left it: no bind ever ran, so no manifest.

        `_legacy_project` builds its tree with a vendored bind, whose manifest outlives
        the unbind — and a later bind prunes whatever that manifest names, removing the
        very tree a real v2 project keeps. Deleting it reproduces what users have.
        """
        root = self._legacy_project(name)
        bind.manifest_file(project.load(root)["project_id"]).unlink()
        return root

    @staticmethod
    def _git_env():
        import os

        return dict(
            os.environ,
            GIT_AUTHOR_NAME="t",
            GIT_AUTHOR_EMAIL="t@e",
            GIT_COMMITTER_NAME="t",
            GIT_COMMITTER_EMAIL="t@e",
        )

    def test_detect_recognises_a_vendored_install(self):
        root = self._legacy_project()
        found = migrate.detect(root)
        self.assertTrue(found["is_v2"])
        self.assertIn("agents", found["vendored_trees"])
        self.assertTrue(found["has_user_data"])

    def test_plan_changes_nothing_on_disk(self):
        root = self._legacy_project()
        before = sorted(p.name for p in (root / project.PROJECT_DIR).iterdir())
        preview = migrate.plan(root)
        after = sorted(p.name for p in (root / project.PROJECT_DIR).iterdir())
        self.assertEqual(before, after)
        self.assertTrue(any("quarantine" in action for action in preview["actions"]))

    def test_plan_reports_git_tracked_paths(self):
        root = self._legacy_project()
        preview = migrate.plan(root)
        self.assertIn(".dev-team-agents/agents", preview["git_tracked"])

    def test_plan_refuses_a_project_that_was_never_installed(self):
        root = self.new_project("fresh")
        with self.assertRaises(UsageError):
            migrate.plan(root)

    def test_apply_preserves_memory_and_knowledge_and_quarantines_the_tree(self):
        root = self._legacy_project()
        result = migrate.apply(root)

        memory = root / project.PROJECT_DIR / "user-data" / "session-summary.md"
        self.assertEqual(memory.read_text(encoding="utf-8"), "## old entry\n")
        self.assertEqual(
            (root / "docs" / "note.md").read_text(encoding="utf-8"), "project knowledge\n"
        )
        # Two pointers, not one: layout 2 splits a project's own state into a
        # machine-local directory (`state-dir`) and a portable one (`memory-dir`),
        # and the bind this migration performs writes both (ADR-0013).
        self.assertEqual(
            sorted(p.name for p in (root / project.PROJECT_DIR).iterdir()),
            ["memory-dir", "plugins", "project.json", "resolved", "scripts", "state-dir", "templates", "user-data"],
        )
        moved = {item["from"] for item in result["quarantined"]}
        self.assertIn(".dev-team-agents/agents", moved)
        for item in result["quarantined"]:
            self.assertTrue(Path(item["to"]).exists(), item["to"])

    def test_apply_rebinds_against_the_store(self):
        root = self._legacy_project()
        result = migrate.apply(root)
        link = root / ".claude" / "agents" / "dev-team"
        self.assertTrue(link.exists())
        self.assertEqual(registry.get(result["project_id"])["path"], str(root.resolve()))
        self.assertEqual(result["version"], "3.0.0")

    def test_apply_reports_the_git_removal_instead_of_doing_it(self):
        root = self._legacy_project()
        result = migrate.apply(root)
        self.assertTrue(result["git_tracked"])
        still_tracked = subprocess.run(
            ["git", "ls-files", ".dev-team-agents/agents"],
            cwd=str(root),
            stdout=subprocess.PIPE,
            check=True,
        ).stdout.decode()
        self.assertIn(".dev-team-agents/agents", still_tracked)

    def test_plan_names_the_committed_v2_links_before_any_bind(self):
        # Before a bind there is no manifest; the plan reads the committed link
        # targets from git instead, so the untrack list is complete up front.
        root = self._install_sh_project()
        preview = migrate.plan(root)
        self.assertIn(".claude/agents/dev-team", preview["git_tracked_artifacts"])
        self.assertTrue(all(not p.startswith(".dev-team-agents/") for p in preview["git_tracked_artifacts"]))

    def test_apply_lists_the_bind_artifacts_git_still_tracks(self):
        root = self._legacy_project()
        result = migrate.apply(root)
        self.assertIn(".claude/agents/dev-team", result["git_tracked_artifacts"])


class UntrackTest(StoreTestCase):
    """`--untrack`: the one git command the CLI runs, on exactly the plan's paths."""

    def setUp(self):
        super().setUp()
        self.install_version("3.0.0", activate=True)

    _git_env = staticmethod(MigrationTest._git_env)
    _legacy_project = MigrationTest._legacy_project
    _install_sh_project = MigrationTest._install_sh_project

    def _tracked(self, root, *paths):
        result = subprocess.run(
            ["git", "ls-files", "--", *paths], cwd=str(root), stdout=subprocess.PIPE, check=True
        )
        return result.stdout.decode().split()

    def test_apply_with_untrack_empties_the_index_of_the_plan_paths_only(self):
        root = self._install_sh_project()
        preview = migrate.plan(root, provider_names=["claude"], mode="link")
        listed = preview["git_tracked"] + preview["git_tracked_artifacts"]
        self.assertTrue(listed)
        result = migrate.apply(root, provider_names=["claude"], mode="link", untrack_paths=True)
        self.assertIsNone(result["untrack_problem"])
        self.assertEqual(self._tracked(root, *listed), [])
        # Nothing outside the plan left the index, and nothing was committed.
        self.assertEqual(self._tracked(root, "docs/note.md"), ["docs/note.md"])
        head = subprocess.run(
            ["git", "log", "--oneline"], cwd=str(root), stdout=subprocess.PIPE, check=True
        ).stdout.decode().splitlines()
        self.assertEqual(len(head), 1 + 1)  # the fixture's two commits, no new one

    def test_apply_without_untrack_leaves_the_index_alone(self):
        root = self._install_sh_project()
        result = migrate.apply(root, provider_names=["claude"], mode="link")
        self.assertEqual(result["untracked"], [])
        self.assertTrue(self._tracked(root, *result["git_tracked"]))

    def test_the_cli_refuses_untrack_without_apply(self):
        root = self._install_sh_project()
        code, _, _ = self.run_cli("--json", "migrate", str(root), "--untrack")
        self.assertEqual(code, 2)

    def test_untrack_outside_a_git_work_tree_reports_instead_of_failing(self):
        plain = self.tmp / "not-git"
        plain.mkdir()
        done, problem = migrate.untrack(plain, ["anything"])
        self.assertEqual(done, [])
        self.assertIn("not inside a git work tree", problem)


class PreRootMigrationTest(StoreTestCase):
    """A pre-v2.1.0 install converted in one `migrate`, no script to run first."""

    def setUp(self):
        super().setUp()
        self.install_version("3.0.0", activate=True)

    _git_env = staticmethod(MigrationTest._git_env)

    def _pre_root_project(self, name="pre-root", stale_identity=False):
        root = self.new_project(name)
        legacy = root / ".claude" / "dev-team-agents"
        for rel, text in (
            ("agents/backend-developer.md", "# agent\n"),
            ("scripts/hooks/stop.sh", "#!/bin/sh\n"),
            ("workflows/bug-fix.md", "# workflow\n"),
            ("skills/removed/old-skill/SKILL.md", "# gone since v2.0\n"),
        ):
            (legacy / rel).parent.mkdir(parents=True, exist_ok=True)
            (legacy / rel).write_text(text, encoding="utf-8")
        claude = root / ".claude"
        (claude / "agents").mkdir()
        os.symlink("../dev-team-agents/agents", str(claude / "agents" / "dev-team"))
        (claude / "skills").mkdir()
        os.symlink("../dev-team-agents/skills/removed/old-skill", str(claude / "skills" / "old-skill"))
        (claude / "user-data").mkdir()
        (claude / "user-data" / "session-summary.md").write_text("## kept\n", encoding="utf-8")
        (claude / "docs").mkdir()
        (claude / "docs" / "project.md").write_text("# project\n", encoding="utf-8")
        (claude / "settings.json").write_text(
            json.dumps(
                {
                    "hooks": {
                        "Stop": [
                            {"hooks": [{"type": "command", "command": ".claude/dev-team-agents/scripts/hooks/stop.sh"}]}
                        ]
                    },
                    "permissions": {"allow": ["Bash(npm test)"]},
                }
            ),
            encoding="utf-8",
        )
        subprocess.run(["git", "add", "-A"], cwd=str(root), check=True, stdout=subprocess.DEVNULL)
        subprocess.run(
            ["git", "commit", "-qm", "v2.0 install"],
            cwd=str(root),
            check=True,
            stdout=subprocess.DEVNULL,
            env=self._git_env(),
        )
        if stale_identity:
            # What a refused bind used to leave: an unregistered identity on layout 2.
            project.ensure(root)
        return root

    def test_detect_and_plan_describe_the_pre_root_shape_without_writing(self):
        root = self._pre_root_project()
        preview = migrate.plan(root, provider_names=["claude"], mode="link")
        self.assertEqual(preview["layout"], "pre-root")
        self.assertEqual(preview["install_dir"], ".claude/dev-team-agents")
        self.assertIn("workflows", preview["detected"]["vendored_trees"])
        self.assertEqual(preview["memory_moves"], [{"from": ".claude/user-data", "to": ".dev-team-agents/user-data"}])
        self.assertEqual(preview["context_paths_added"], [".claude/docs"])
        self.assertIn(".claude/user-data", preview["git_tracked"])
        self.assertIn(".claude/agents/dev-team", preview["git_tracked_artifacts"])
        self.assertFalse((root / project.PROJECT_DIR).exists())

    def test_apply_converts_it_keeps_memory_and_docs_and_repoints_the_hooks(self):
        root = self._pre_root_project()
        result = migrate.apply(root, provider_names=["claude"], mode="link", untrack_paths=True)
        self.assertFalse((root / ".claude" / "dev-team-agents").exists())
        self.assertTrue(result["quarantine_dir"])
        # Memory moved, not quarantined; the project is on layout 1 for `upgrade`.
        self.assertEqual(
            (root / project.PROJECT_DIR / "user-data" / "session-summary.md").read_text(encoding="utf-8"),
            "## kept\n",
        )
        self.assertEqual(project.layout(root), project.LAYOUT_MEMORY_IN_PROJECT)
        # Docs left in place, and visible to agents.
        self.assertTrue((root / ".claude" / "docs" / "project.md").is_file())
        self.assertIn(".claude/docs", project.context_paths(root))
        # The pre-root hook entry was rewritten in place, and the user's keys kept.
        settings = json.loads((root / ".claude" / "settings.json").read_text(encoding="utf-8"))
        stops = [h["command"] for e in settings["hooks"]["Stop"] for h in e["hooks"]]
        self.assertEqual(len(stops), 1)
        self.assertIn(".dev-team-agents/scripts/hooks/stop.sh", stops[0])
        self.assertNotIn(".claude/dev-team-agents", stops[0])
        self.assertEqual(settings["permissions"], {"allow": ["Bash(npm test)"]})
        # The link the bind recreates points into the store; the one it does not is gone.
        # Resolved on both sides: Windows reports the link target with a `\\?\` prefix and the
        # temp home under its 8.3 short name.
        agents = os.path.normcase(os.path.realpath(str(root / ".claude" / "agents" / "dev-team")))
        self.assertTrue(agents.startswith(os.path.normcase(os.path.realpath(str(self.home)))), agents)
        self.assertFalse(os.path.lexists(str(root / ".claude" / "skills" / "old-skill")))
        self.assertIn(".claude/skills/old-skill", result["retired_links"])
        # doctor has nothing left to say about the old install or tracked artifacts.
        findings = doctor.run(project_root=root)["findings"]
        # Only layout 1 remains to report: `devteam upgrade` is the next, separate step.
        about_v2 = [f for f in findings if f["level"] != "ok" and f["category"] != "layout"]
        self.assertEqual(about_v2, [])

    def test_a_stale_unregistered_identity_is_adopted_and_moved_to_layout_1(self):
        root = self._pre_root_project(stale_identity=True)
        stale_id = project.load(root)["project_id"]
        self.assertEqual(project.layout(root), project.LAYOUT_MEMORY_IN_STORE)
        preview = migrate.plan(root, provider_names=["claude"], mode="link")
        self.assertTrue(preview["adopts_identity"])
        result = migrate.apply(root, provider_names=["claude"], mode="link")
        self.assertEqual(result["project_id"], stale_id)
        self.assertTrue(result["adopted_identity"])
        self.assertEqual(project.layout(root), project.LAYOUT_MEMORY_IN_PROJECT)

    def test_two_memory_directories_are_refused_before_anything_moves(self):
        root = self._pre_root_project()
        inner = root / ".claude" / "dev-team-agents" / "user-data"
        inner.mkdir()
        (inner / "session-summary.md").write_text("## other\n", encoding="utf-8")
        with self.assertRaises(ConflictError):
            migrate.plan(root, provider_names=["claude"], mode="link")
        self.assertTrue((root / ".claude" / "user-data" / "session-summary.md").is_file())

    def test_the_cli_plan_and_apply_json(self):
        root = self._pre_root_project()
        code, out, err = self.run_cli("--json", "migrate", str(root), "--provider", "claude", "--mode", "link")
        self.assertEqual(code, 0, err)
        self.assertEqual(json.loads(out)["layout"], "pre-root")
        code, out, err = self.run_cli(
            "--json", "migrate", str(root), "--provider", "claude", "--mode", "link", "--apply", "--untrack"
        )
        self.assertEqual(code, 0, err)
        payload = json.loads(out)
        for key in ("layout", "adopted_identity", "memory_moved", "context_paths_added", "retired_links", "untracked", "untrack_problem"):
            self.assertIn(key, payload)
        self.assertTrue(payload["untracked"])


class BindOverV2Test(StoreTestCase):
    """A bind run straight over a v2 install — the path a user took before `bind` refused it.

    `bind` adopted the old relative links and left the vendored tree in git; `doctor`
    then reported `status: ok`, because its v2 check only ran without `project.json`.
    """

    def setUp(self):
        super().setUp()
        self.install_version("3.0.0", activate=True)

    _git_env = staticmethod(MigrationTest._git_env)
    _legacy_project = MigrationTest._legacy_project
    _install_sh_project = MigrationTest._install_sh_project

    def _bound_over_v2(self):
        """What a bind over v2 left before it was refused: real v2 trees plus a bind.

        Built by binding with the two runtime trees moved aside and putting them back
        afterwards — a bind today refuses to link over them, which is the point.
        """
        root = self._install_sh_project("bound-over-v2")
        install_dir = root / project.PROJECT_DIR
        parked = {}
        for name in bind.RUNTIME_TREES:
            if not (install_dir / name).exists():
                # A tree v2's installer never shipped (`plugins/`, ADR-0019).
                continue
            parked[name] = install_dir.parent / ("parked-" + name)
            (install_dir / name).rename(parked[name])
        bind.bind(root, provider_names=["claude"], mode="link")
        for name, path in parked.items():
            (install_dir / name).unlink()
            path.rename(install_dir / name)
        return root

    def test_the_bind_command_refuses_a_v2_install_and_points_at_migrate(self):
        root = self._install_sh_project()
        code, out, _ = self.run_cli("--json", "bind", str(root), "--provider", "claude", "--mode", "link")
        self.assertEqual(code, 4)
        payload = json.loads(out)
        self.assertFalse(payload["ok"])
        self.assertIn("devteam migrate", payload["hint"])
        self.assertIsNone(project.load(root) and registry.get(project.load(root)["project_id"]))

    def _pre_root_project(self, name="pre-root"):
        """A pre-v2.1.0 install: the tree under `.claude/`, and the link it committed."""
        root = self.new_project(name)
        legacy = root / ".claude" / "dev-team-agents" / "agents"
        legacy.mkdir(parents=True)
        (legacy / "backend-developer.md").write_text("# agent\n", encoding="utf-8")
        (root / ".claude" / "agents").mkdir()
        os.symlink("../dev-team-agents/agents", str(root / ".claude" / "agents" / "dev-team"))
        return root

    def test_migrate_restores_the_registered_id_when_project_json_is_gone(self):
        root = self._bound_over_v2()
        registered = project.load(root)["project_id"]
        (root / project.PROJECT_DIR / "project.json").unlink()

        preview = migrate.plan(root, provider_names=["claude"], mode="link")
        self.assertEqual(preview["restores_identity"], registered)
        self.assertFalse(any("new project_id" in action for action in preview["actions"]))
        self.assertFalse((root / project.PROJECT_DIR / "project.json").exists())

        result = migrate.apply(root, provider_names=["claude"], mode="link")
        self.assertEqual(result["project_id"], registered)
        self.assertEqual(result["restored_identity"], registered)
        self.assertEqual(list(registry.entries()), [registered])
        self.assertEqual(migrate.leftover_trees(root), [])

    def test_the_bind_command_refuses_a_pre_root_install_in_every_mode_and_writes_nothing(self):
        # Found binding a real project: this shape passed the v2 refusal, collided on
        # its own committed link, and left `project.json` behind.
        for mode in ("link", "vendored"):
            with self.subTest(mode):
                root = self._pre_root_project("pre-root-" + mode)
                code, out, _ = self.run_cli(
                    "--json", "bind", str(root), "--provider", "claude", "--mode", mode
                )
                self.assertEqual(code, 4)
                payload = json.loads(out)
                self.assertIn(".claude/dev-team-agents", payload["error"])
                self.assertIn("devteam migrate", payload["hint"])
                self.assertFalse((root / project.PROJECT_DIR).exists())

    def test_a_first_bind_that_collides_leaves_no_project_json(self):
        # Every destination is checked before the identity is written.
        root = self.new_project("collides")
        (root / ".claude" / "agents").mkdir(parents=True)
        (root / ".claude" / "agents" / "dev-team").write_text("mine\n", encoding="utf-8")
        with self.assertRaises(ConflictError) as caught:
            bind.bind(root, provider_names=["claude"], mode="link")
        self.assertIn("devteam bind", caught.exception.hint)
        self.assertIsNone(project.load(root))
        self.assertFalse((root / project.PROJECT_DIR).exists())
        self.assertEqual((root / ".claude" / "agents" / "dev-team").read_text(encoding="utf-8"), "mine\n")

    def test_the_bind_command_still_accepts_an_explicit_vendored_bind(self):
        root = self._install_sh_project()
        code, _, err = self.run_cli("bind", str(root), "--provider", "claude", "--mode", "vendored")
        self.assertEqual(code, 0, err)

    def test_sync_refuses_a_project_bound_over_v2_and_points_at_migrate(self):
        # The runtime links live where the v2 trees still are. Linking beside them is
        # impossible, and leaving them would run the hooks from the old v2 scripts —
        # so sync refuses with the one command that clears the way.
        root = self._bound_over_v2()
        project_id = project.load(root)["project_id"]
        with self.assertRaises(ConflictError) as caught:
            bind.sync_project(project_id)
        self.assertIn("devteam migrate", caught.exception.hint)
        self.assertEqual(caught.exception.details["reason"], bind.V2_INSTALL_REASON)
        # Nothing of the user's was touched.
        self.assertFalse((root / project.PROJECT_DIR / "scripts").is_symlink())

    def test_upgrade_on_a_registered_project_without_project_json_says_not_bound(self):
        root = self._bound_over_v2()
        (root / project.PROJECT_DIR / "project.json").unlink()
        code, out, _ = self.run_cli("--json", "upgrade", str(root))
        self.assertEqual(code, 2)
        payload = json.loads(out)
        self.assertEqual(payload["details"]["reason"], bind.NOT_BOUND_REASON)
        self.assertIn("registered id", payload["hint"])

    def test_doctor_reports_the_leftover_tree_after_a_bind(self):
        root = self._bound_over_v2()
        report = doctor.run(project_root=root)
        leftover = [f for f in report["findings"] if f["category"] == "project" and f["level"] == "warn"]
        self.assertTrue(leftover, report["findings"])
        self.assertIn("devteam migrate", leftover[0]["hint"])

    def test_doctor_reports_tracked_artifacts_with_the_exact_untrack_command(self):
        root = self._bound_over_v2()
        report = doctor.run(project_root=root)
        tracked = [f for f in report["findings"] if f["category"] == "bind" and "tracked by git" in f["message"]]
        self.assertEqual(len(tracked), 1, report["findings"])
        self.assertIn("git rm -r --cached", tracked[0]["hint"])
        self.assertIn(".claude/agents/dev-team", tracked[0]["hint"])
        # The project's own settings file is merged into, not owned: never untracked.
        self.assertNotIn(".claude/settings.json", tracked[0]["hint"])

    def test_a_vendored_bind_is_neither_a_leftover_nor_a_tracking_problem(self):
        root = self.new_project("vendored-by-choice")
        bind.bind(root, provider_names=["claude"], mode="vendored")
        subprocess.run(["git", "add", "-A"], cwd=str(root), check=True, stdout=subprocess.DEVNULL)
        report = doctor.run(project_root=root)
        messages = [f["message"] for f in report["findings"] if f["level"] != "ok"]
        self.assertFalse(any("v2 vendored install" in m or "tracked by git" in m for m in messages), messages)

    def test_a_clean_link_bind_reports_no_tracked_artifacts(self):
        root = self.new_project("clean")
        bind.bind(root, provider_names=["claude"], mode="link")
        subprocess.run(["git", "add", "-A"], cwd=str(root), check=True, stdout=subprocess.DEVNULL)
        manifest = bind.read_manifest(project.load(root)["project_id"])
        self.assertEqual(bind.tracked_artifacts(root, manifest), [])


def materialize_v2_links(root):
    """Replace every `.claude/` link of a v2 install with a real copy of its target.

    What a tool that copies a project dereferencing links leaves — and what a
    checkout without symlink support produces as text files instead.
    """
    copied = []
    for base in (root / ".claude" / "agents", root / ".claude" / "commands", root / ".claude" / "skills"):
        if not base.is_dir():
            continue
        for child in sorted(base.iterdir()):
            if not child.is_symlink():
                continue
            target = child.resolve()
            child.unlink()
            shutil.copytree(str(target), str(child))
            copied.append(child.relative_to(root).as_posix())
    return copied


class V2CopiesTest(StoreTestCase):
    """A v2 install whose `.claude/` links were materialized as real copies.

    Found migrating a real project: `bind` refused the copies as foreign, and a
    `migrate` that had already quarantined the tree left a project neither command
    could take further.
    """

    def setUp(self):
        super().setUp()
        self.install_version("3.0.0", activate=True)

    _git_env = staticmethod(MigrationTest._git_env)
    _legacy_project = MigrationTest._legacy_project
    _install_sh_project = MigrationTest._install_sh_project

    def _copies_project(self, name="copies"):
        root = self._install_sh_project(name)
        copied = materialize_v2_links(root)
        self.assertIn(".claude/agents/dev-team", copied)
        subprocess.run(["git", "add", "-A"], cwd=str(root), check=True, stdout=subprocess.DEVNULL)
        subprocess.run(
            ["git", "commit", "-qm", "copies"],
            cwd=str(root),
            check=True,
            stdout=subprocess.DEVNULL,
            env=self._git_env(),
        )
        return root, copied

    def _interrupted(self, name="interrupted"):
        """What a migrate that quarantined the tree and then had its bind refused left."""
        root, copied = self._copies_project(name)
        project_id = project.load(root)["project_id"]
        for found in migrate.detect(root)["vendored_trees"]:
            quarantine.move(root / project.PROJECT_DIR / found, project_id, group="v2-install")
        self.assertFalse(migrate.detect(root)["is_v2"])
        return root, copied

    def test_v2_copy_recognises_copies_and_link_files_but_not_project_content(self):
        root, _ = self._copies_project()
        version_dir = versions.require(versions.resolve(None))
        self.assertTrue(bind.v2_copy(".claude/agents/dev-team", root / ".claude/agents/dev-team", version_dir))
        self.assertTrue(
            bind.v2_copy(".claude/skills/unit", root / ".claude/skills/unit", version_dir)
        )
        link_file = root / ".claude" / "commands" / "devteam"
        shutil.rmtree(str(link_file))
        link_file.write_text("../../.dev-team-agents/commands", encoding="utf-8")
        self.assertTrue(bind.v2_copy(".claude/commands/devteam", link_file, version_dir))

        own = root / ".claude" / "agents" / "dev-team"
        (own / "notes.txt").write_text("mine\n", encoding="utf-8")
        self.assertFalse(bind.v2_copy(".claude/agents/dev-team", own, version_dir))
        skill = root / ".claude" / "skills" / "unit" / "SKILL.md"
        skill.write_text("---\nname: something-else\n---\n", encoding="utf-8")
        self.assertFalse(bind.v2_copy(".claude/skills/unit", skill.parent, version_dir))

    def test_bind_refuses_copies_with_the_v2_reason_and_writes_nothing(self):
        root, copied = self._interrupted()
        before = (root / project.PROJECT_DIR / "project.json").read_text(encoding="utf-8")
        code, out, _ = self.run_cli("--json", "bind", str(root), "--provider", "claude", "--mode", "link")
        self.assertEqual(code, 4)
        payload = json.loads(out)
        self.assertEqual(payload["details"]["reason"], bind.V2_INSTALL_REASON)
        self.assertIn("devteam migrate", payload["hint"])
        self.assertEqual((root / project.PROJECT_DIR / "project.json").read_text(encoding="utf-8"), before)
        for rel in copied:
            self.assertFalse((root / rel).is_symlink(), rel)

    def test_migrate_quarantines_the_copies_with_the_tree_and_binds(self):
        root, copied = self._copies_project()
        preview = migrate.plan(root, provider_names=["claude"], mode="link")
        self.assertEqual(sorted(preview["v2_copies"]), sorted(copied))
        self.assertTrue(set(copied) <= set(preview["git_tracked"]))

        result = migrate.apply(root, provider_names=["claude"], mode="link")
        moved = {item["from"] for item in result["quarantined"]}
        self.assertTrue(set(copied) <= moved)
        self.assertIn("{}/agents".format(project.PROJECT_DIR), moved)
        for rel in copied:
            self.assertTrue((root / rel).is_symlink(), rel)
        agents = Path(result["quarantine_dir"]) / "claude" / "agents" / "dev-team" / "backend-developer.md"
        self.assertTrue(agents.is_file())
        self.assertEqual(migrate.leftover_trees(root), [])

    def test_migrate_finishes_an_interrupted_migration_and_keeps_the_identity(self):
        root, copied = self._interrupted()
        project_id = project.load(root)["project_id"]
        preview = migrate.plan(root, provider_names=["claude"], mode="link")
        self.assertTrue(preview["adopts_identity"])
        self.assertEqual(sorted(preview["v2_copies"]), sorted(copied))

        result = migrate.apply(root, provider_names=["claude"], mode="link")
        self.assertEqual(result["project_id"], project_id)
        for rel in copied:
            self.assertTrue((root / rel).is_symlink(), rel)

    def test_a_refused_bind_moves_nothing(self):
        root, copied = self._copies_project("refused")
        # A project-owned directory at a framework path: still foreign, still refused.
        own = root / ".claude" / "skills" / "project-context"
        shutil.rmtree(str(own))
        own.mkdir()
        (own / "SKILL.md").write_text("---\nname: mine\n---\n", encoding="utf-8")
        identity = (root / project.PROJECT_DIR / "project.json").read_text(encoding="utf-8")

        with self.assertRaises(ConflictError):
            migrate.apply(root, provider_names=["claude"], mode="link")
        self.assertEqual(migrate.detect(root)["vendored_trees"], migrate.plan(root)["detected"]["vendored_trees"])
        self.assertTrue((root / project.PROJECT_DIR / "agents").is_dir())
        self.assertFalse((root / project.PROJECT_DIR / "agents").is_symlink())
        for rel in copied:
            if rel != ".claude/skills/project-context":
                self.assertTrue((root / rel).exists() and not (root / rel).is_symlink(), rel)
        self.assertEqual((root / project.PROJECT_DIR / "project.json").read_text(encoding="utf-8"), identity)
        self.assertEqual(list(registry.entries()), [])


class DoctorTest(StoreTestCase):
    def test_reports_an_empty_store_as_a_failure(self):
        report = doctor.run(project_root=None)
        self.assertEqual(report["status"], "fail")
        self.assertTrue(any(f["category"] == "store" for f in report["findings"]))

    def test_healthy_bind_reports_ok(self):
        self.install_version("3.0.0", activate=True)
        root = self.new_project()
        bind.bind(root, provider_names=["claude"])
        report = doctor.run(project_root=root)
        self.assertEqual(report["status"], "ok")

    def test_a_hostile_pin_in_the_registry_is_a_finding_not_an_abort(self):
        self.install_version("3.0.0", activate=True)
        root = self.new_project()
        project_id = bind.bind(root, provider_names=["claude"])["project_id"]
        registry.set_pin(project_id, "../../elsewhere")
        report = doctor.run(project_root=root)
        self.assertEqual(report["status"], "fail")
        self.assertTrue(any(f["category"] == "bind" for f in report["findings"]))

    def test_the_hook_finding_counts_every_registered_dispatcher(self):
        from devteam import hooks

        self.install_version("3.0.0", activate=True)
        root = self.new_project()
        bind.bind(root, provider_names=["claude"])
        report = doctor.run(project_root=root)
        message = [f["message"] for f in report["findings"] if f["category"] == "hooks"][0]
        self.assertTrue(message.startswith("{} dispatchers".format(len(hooks.EVENTS))), message)

    def test_missing_artifacts_are_a_warning_pointing_at_sync(self):
        self.install_version("3.0.0", activate=True)
        root = self.new_project()
        bind.bind(root, provider_names=["claude"])
        shutil.rmtree(str(root / ".claude" / "agents" / "dev-team"), ignore_errors=True)
        (root / ".claude" / "agents" / "dev-team").unlink(missing_ok=True)
        report = doctor.run(project_root=root)
        self.assertEqual(report["status"], "warn")
        self.assertTrue(any("sync" in (f.get("hint") or "") for f in report["findings"]))

    def test_a_moved_project_is_reconciled_by_identity(self):
        self.install_version("3.0.0", activate=True)
        root = self.new_project("before-move")
        result = bind.bind(root, provider_names=["claude"])
        moved = self.tmp / "after-move"
        shutil.move(str(root), str(moved))

        report = doctor.run(project_root=moved)
        self.assertTrue(any(a["action"] == "relocated" for a in report["actions"]))
        self.assertEqual(registry.get(result["project_id"])["path"], str(moved.resolve()))
        self.assertEqual(len(registry.entries()), 1)

    def test_the_same_identity_at_two_live_paths_is_reported_not_merged(self):
        self.install_version("3.0.0", activate=True)
        original = self.new_project("origin")
        result = bind.bind(original, provider_names=["claude"])
        fork = self.tmp / "fork"
        shutil.copytree(str(original), str(fork), symlinks=True)

        report = doctor.run(project_root=fork)
        self.assertEqual(report["status"], "fail")
        collision = [f for f in report["findings"] if f["category"] == "identity"]
        self.assertTrue(collision)
        self.assertIn("two paths", collision[0]["message"])
        # Nothing was merged or re-pointed.
        self.assertEqual(registry.get(result["project_id"])["path"], str(original.resolve()))

    def test_reassign_identity_resolves_the_fork_case(self):
        self.install_version("3.0.0", activate=True)
        original = self.new_project("origin")
        bind.bind(original, provider_names=["claude"])
        fork = self.tmp / "fork"
        shutil.copytree(str(original), str(fork), symlinks=True)

        before = project.load(fork)["project_id"]
        doctor.run(project_root=fork, reassign_identity=True)
        after = project.load(fork)["project_id"]
        self.assertNotEqual(before, after)
        bind.bind(fork, provider_names=["claude"])
        self.assertEqual(len(registry.entries()), 2)

    def test_stale_pointer_to_an_uninstalled_version_is_a_failure(self):
        self.install_version("3.0.0", activate=True)
        shutil.rmtree(str(versions.version_dir("3.0.0")))
        report = doctor.run(project_root=None)
        self.assertEqual(report["status"], "fail")

    def _project_findings(self, root):
        report = doctor.run(project_root=root)
        return [f for f in report["findings"] if f["category"] == "project"]

    def test_an_unbound_v2_vendored_install_points_at_migrate(self):
        # No `devteam bind` was ever run here — just the vendored tree a v2
        # install leaves under `.dev-team-agents/`, same as `migrate.detect`
        # itself recognises. `devteam bind` cannot fold this in; only
        # `devteam migrate` knows to quarantine it instead of clobbering it.
        root = self.new_project("vendored")
        install_dir = root / project.PROJECT_DIR
        (install_dir / "agents").mkdir(parents=True)
        (install_dir / "agents" / "backend-developer.md").write_text(
            "# agent\n", encoding="utf-8"
        )
        findings = self._project_findings(root)
        self.assertTrue(findings)
        self.assertIn("devteam migrate", findings[0]["hint"])

    def test_a_pre_root_install_points_at_migrate(self):
        # The shape `scripts/migrate-to-root.sh` targets: the framework still
        # sitting at `.claude/dev-team-agents/` instead of the project root.
        root = self.new_project("prerooted")
        (root / ".claude" / "dev-team-agents").mkdir(parents=True)
        findings = self._project_findings(root)
        self.assertTrue(findings)
        self.assertIn("devteam migrate", findings[0]["hint"])

    def test_a_directory_with_no_legacy_shape_still_gets_the_bind_hint(self):
        root = self.new_project("fresh")
        findings = self._project_findings(root)
        self.assertTrue(findings)
        self.assertIn("devteam bind", findings[0]["hint"])


if __name__ == "__main__":
    unittest.main()
