"""The two runtime links — `.dev-team-agents/scripts` and `/templates` — against the real tree.

They replaced one `core` pointer that claimed to resolve every project-relative reference
and resolved none: the framework's text says `.dev-team-agents/scripts/new-adr.sh`, the
pointer made `.dev-team-agents/core/scripts/new-adr.sh`. Every test here that asks
"does it resolve?" installs THIS repository's own tree, not the minimal fixture — a
fixture only proves the fixture's paths exist, which is how the gap went unseen.
"""

import os
import re
import subprocess
import unittest
from pathlib import Path

from devteam_support import REPO_ROOT, StoreTestCase, requires_bash

from devteam import bind, hooks, jsonio, project, versions

#: Where the framework names a runtime path: the text an agent reads and the hooks run.
SHIPPED = ("agents", "commands", "skills", "templates", "scripts/hooks", "CLAUDE-md")
REFERENCE = re.compile(r"\.dev-team-agents/((?:scripts|templates)/[A-Za-z0-9_./-]+)")

#: Cited so it can be FOUND AND REMOVED — a pre-1.9.1 v2 hook the health check and the
#: graphify skill clean up. Its absence is the healthy state, in every layout.
LEGACY_CITATIONS = {"scripts/hooks/stop/02-graphify-refresh.sh"}


def cited_runtime_paths():
    """Every `.dev-team-agents/{scripts,templates}/…` path the shipped text names."""
    found = set()
    for top in SHIPPED:
        for path in (REPO_ROOT / top).rglob("*"):
            if not path.is_file() or path.suffix not in {".md", ".sh", ".txt", ".ts"}:
                continue
            for match in REFERENCE.finditer(path.read_text(encoding="utf-8", errors="replace")):
                cited = match.group(1).rstrip(".")
                # A placeholder, a glob, or a prefix cut off at one (`install-*.sh`
                # stops matching at the `*`) is a pattern, not a path anyone runs.
                if any(ch in cited for ch in "<>*{}$") or cited.endswith("-"):
                    continue
                if cited in LEGACY_CITATIONS:
                    continue
                found.add(cited)
    return sorted(found)


class RealTreeRuntimeLinksTest(StoreTestCase):
    def setUp(self):
        super().setUp()
        versions.install_from_tree(REPO_ROOT, version="3.0.0", force=True, make_current=True)

    def _assert_every_cited_path_resolves(self, mode):
        root = self.new_project("real-" + mode)
        bind.bind(root, provider_names=["claude"], mode=mode)
        install_dir = root / project.PROJECT_DIR
        cited = cited_runtime_paths()
        self.assertGreater(len(cited), 20, "the scan found almost nothing — the regex is wrong")
        missing = [path for path in cited if not (install_dir / path).exists()]
        self.assertEqual(missing, [], "cited by the framework, absent in a {} bind".format(mode))

    def test_every_cited_runtime_path_resolves_in_a_link_bind(self):
        self._assert_every_cited_path_resolves("link")

    def test_every_cited_runtime_path_resolves_in_a_copy_bind(self):
        self._assert_every_cited_path_resolves("copy")

    def test_the_reuse_and_design_token_gates_find_their_script(self):
        # Both Stop sub-scripts `exit 0` when their lint is absent — the gates were
        # silently off in every project bound with the `core` pointer.
        root = self.new_project("gates")
        bind.bind(root, provider_names=["claude"], mode="link")
        for lint in ("reuse-lint.sh", "design-token-lint.sh"):
            self.assertTrue((root / project.PROJECT_DIR / "scripts" / lint).is_file(), lint)


class CorePointerUpgradeTest(StoreTestCase):
    """A project bound while bind still made a `core` pointer, synced after the change."""

    def setUp(self):
        super().setUp()
        self.install_version("3.0.0", activate=True)

    def _bound_with_core_pointer(self):
        root = self.new_project("pointer-era")
        result = bind.bind(root, provider_names=["claude"], mode="link")
        project_id = result["project_id"]
        install_dir = root / project.PROJECT_DIR
        # Rebuild what that bind left: `core` instead of the two links, recorded in
        # the manifest, and the hooks written through it.
        for name in bind.RUNTIME_TREES:
            (install_dir / name).unlink()
        os.symlink(str(versions.require("3.0.0")), str(install_dir / "core"))
        manifest = bind.read_manifest(project_id)
        manifest["artifacts"] = [
            item for item in manifest["artifacts"] if item["path"] not in {
                "{}/{}".format(project.PROJECT_DIR, name) for name in bind.RUNTIME_TREES
            }
        ] + [{"path": "{}/core".format(project.PROJECT_DIR), "kind": "link"}]
        jsonio.write_json_atomic(bind.manifest_file(project_id), manifest)
        settings = jsonio.read_json(root / hooks.SETTINGS_FILE)
        for entries in settings["hooks"].values():
            for entry in entries:
                for hook in entry["hooks"]:
                    hook["command"] = hook["command"].replace(
                        hooks.HOOK_DIR, hooks.CORE_POINTER_HOOK_DIR
                    )
        jsonio.write_json_atomic(root / hooks.SETTINGS_FILE, settings, mode=0o644, dir_mode=None)
        return root, project_id

    def test_sync_retires_the_pointer_and_creates_both_links(self):
        root, project_id = self._bound_with_core_pointer()
        bind.sync_project(project_id)
        install_dir = root / project.PROJECT_DIR
        self.assertFalse(os.path.lexists(str(install_dir / "core")))
        for name in bind.RUNTIME_TREES:
            self.assertTrue((install_dir / name).is_symlink(), name)

    def test_sync_rewrites_the_hooks_in_place_without_a_second_entry(self):
        root, project_id = self._bound_with_core_pointer()
        bind.sync_project(project_id)
        settings = jsonio.read_json(root / hooks.SETTINGS_FILE)
        for event, script in hooks.EVENTS:
            commands = [h["command"] for e in settings["hooks"][event] for h in e["hooks"]]
            self.assertEqual(len(commands), 1, event)
            self.assertIn("{}/{}".format(hooks.HOOK_DIR, script), commands[0])
            self.assertTrue((root / hooks.HOOK_DIR / script).exists(), commands[0])


@requires_bash()
class ProviderInstallerGuardTest(StoreTestCase):
    """`ensure_claude_framework` must never mirror a tree into — or through — a bound project."""

    def setUp(self):
        super().setUp()
        self.install_version("3.0.0", activate=True)

    def test_a_bound_project_gets_no_framework_copy_and_the_store_is_untouched(self):
        root = self.new_project("provider")
        bind.bind(root, provider_names=["claude"], mode="link")
        store_scripts = versions.require("3.0.0") / "scripts"
        before = sorted(p.name for p in store_scripts.iterdir())
        source = self.tmp / "source"
        subprocess.run(
            [
                "bash",
                "-c",
                'source "$1"; ensure_claude_framework "$2" "$3"',
                "_",
                str(REPO_ROOT / "scripts" / "lib" / "ensure-claude-framework.sh"),
                str(root),
                str(source),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
        )
        install_dir = root / project.PROJECT_DIR
        for name in ("agents", "commands", "skills"):
            self.assertFalse((install_dir / name).exists(), name)
        self.assertTrue((install_dir / "scripts").is_symlink())
        self.assertEqual(sorted(p.name for p in store_scripts.iterdir()), before)


@requires_bash()
class V2ToolGuardTest(StoreTestCase):
    """The v2 installers refuse to run inside a bound project now that they resolve there."""

    def setUp(self):
        super().setUp()
        versions.install_from_tree(REPO_ROOT, version="3.0.0", force=True, make_current=True)

    def _run(self, root, script, *args):
        return subprocess.run(
            ["bash", ".dev-team-agents/scripts/" + script, *args],
            cwd=str(root),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def test_update_rollback_and_fix_symlinks_refuse_and_name_the_cli_command(self):
        root = self.new_project("guarded")
        bind.bind(root, provider_names=["claude"], mode="link")
        expected = {"update.sh": "devteam update", "rollback.sh": "devteam pin",
                    "fix-symlinks.sh": "devteam sync"}
        for script, instead in expected.items():
            result = self._run(root, script)
            self.assertEqual(result.returncode, 2, (script, result.stderr))
            self.assertIn(instead, result.stderr.decode(), script)

    def test_update_check_mode_still_runs_read_only(self):
        root = self.new_project("check")
        bind.bind(root, provider_names=["claude"], mode="link")
        result = self._run(root, "update.sh", "--check")
        self.assertNotIn(b"v2 install tool", result.stderr)


if __name__ == "__main__":
    unittest.main()
