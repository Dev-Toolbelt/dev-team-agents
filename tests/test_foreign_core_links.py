"""Bind artifacts committed from another machine: links into *that* machine's core store.

A project bound on a Mac and committed carries `.claude/agents/dev-team ->
/Users/<name>/Library/Application Support/dev-team-agents/core/versions/<v>/agents`.
On a Windows checkout without symlink support git writes each link as a plain file
holding that path. `bind` used to refuse it as foreign ("was not created by
dev-team-agents"), with no repair to offer.
"""

import json
import os
import shutil
import subprocess
from pathlib import Path

from devteam_support import REPO_ROOT, StoreTestCase, requires_bash

from devteam import bind, providers, versions
from test_windows_link_stubs import FORMATS, TOOLS

MAC_CORE = "/Users/someone/Library/Application Support/dev-team-agents/core/versions/2.50.2"
WIN_CORE = "C:\\Users\\willa\\AppData\\Local\\dev-team-agents\\core\\versions\\2.50.2"

#: Claude artifact -> its tree under a core version, as a committed bind links it.
CLAUDE_LINKS = {
    ".claude/agents/dev-team": "agents",
    ".claude/commands/devteam": "commands",
    ".claude/skills/project-context": "skills/shared/project-context",
}

#: Runtime links every provider's bind writes under `.dev-team-agents/`.
RUNTIME_LINKS = {".dev-team-agents/scripts": "scripts", ".dev-team-agents/templates": "templates"}


class CoreLinkTextTest(StoreTestCase):
    def test_a_core_store_target_on_any_machine_is_recognised(self):
        for target in (
            MAC_CORE + "/agents",
            MAC_CORE + "/skills/shared/project-context",
            MAC_CORE + "/skills",
            "/c/Users/willa/AppData/Local/dev-team-agents/core/versions/2.50.2/agents",
            "\\\\?\\C:\\Users\\willa\\core\\versions\\2.50.2\\agents",
            WIN_CORE + "\\commands",
            "/home/x/.local/share/dev-team-agents/core/versions/3.0.0-dev.1/templates/",
            "/srv/custom-home/core/versions/2.49.1/scripts",
            MAC_CORE + "/plugins",
        ):
            with self.subTest(target=target):
                self.assertTrue(bind._is_core_link_text(target))

    def test_other_targets_are_not(self):
        for target in (
            "",
            MAC_CORE,  # the version dir itself, not a tree a bind links
            MAC_CORE + "/README.md",
            MAC_CORE + "/agents/backend-developer.md",
            MAC_CORE + "/skills/a/b/c",
            "/Users/someone/core/versions/latest/agents",
            "../core/versions/2.50.2/agents",  # relative: a bind never writes one
            "core/versions/2.50.2/agents",
            "/a/core/versions/1.0.0/skills/../..",
            "/a/core/versions/1.0.0/skills/./x",
            "/Users/someone/projects/core-versions/2.50.2/agents",
            "../../.dev-team-agents/agents",
            "# agents\nsee core/versions/2.50.2/agents",
        ):
            with self.subTest(target=target):
                self.assertFalse(bind._is_core_link_text(target))


class ForeignCoreLinkBindTest(StoreTestCase):
    def setUp(self):
        super().setUp()
        self.install_version("3.0.0", activate=True)
        self._count = 0

    def _project(self, links, encode):
        self._count += 1
        root = self.new_project("foreign-{}".format(self._count))
        for rel, tree in links.items():
            path = root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(encode(MAC_CORE + "/" + tree))
        return root

    def test_bind_replaces_each_stub_format_and_quarantines_the_stub(self):
        for fmt, encode in FORMATS.items():
            with self.subTest(fmt=fmt):
                root = self._project({**CLAUDE_LINKS, **RUNTIME_LINKS}, encode)
                code, out, err = self.run_cli("--json", "bind", str(root), "--provider", "claude", "--mode", "link")
                self.assertEqual(code, 0, out + err)
                for rel in list(CLAUDE_LINKS) + list(RUNTIME_LINKS):
                    self.assertTrue((root / rel).is_symlink(), rel)
                retired = {item["path"] for item in json.loads(out).get("retired", [])}
                self.assertTrue(set(CLAUDE_LINKS) <= retired, retired)

    def test_bind_reports_the_committed_links_it_replaced_as_tracked(self):
        root = self._project(CLAUDE_LINKS, FORMATS["git-plain"])
        subprocess.run(["git", "add", "-A"], cwd=str(root), check=True, capture_output=True)
        code, out, err = self.run_cli("--json", "bind", str(root), "--provider", "claude", "--mode", "link")
        self.assertEqual(code, 0, out + err)
        self.assertTrue(set(CLAUDE_LINKS) <= set(json.loads(out)["tracked_artifacts"]))
        self.assertIn("git rm -r --cached", err)

    def test_bind_over_an_untracked_project_reports_nothing_tracked(self):
        root = self.new_project("clean")
        code, out, err = self.run_cli("--json", "bind", str(root), "--provider", "claude", "--mode", "link")
        self.assertEqual(code, 0, out + err)
        self.assertEqual(json.loads(out)["tracked_artifacts"], [])

    def test_bind_replaces_a_dangling_symlink_into_another_machines_store(self):
        root = self.new_project("dangling")
        for rel, tree in CLAUDE_LINKS.items():
            path = root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            os.symlink(MAC_CORE + "/" + tree, str(path))
        code, out, err = self.run_cli("--json", "bind", str(root), "--provider", "claude", "--mode", "link")
        self.assertEqual(code, 0, out + err)
        for rel in CLAUDE_LINKS:
            self.assertTrue(Path(os.readlink(str(root / rel))).exists(), rel)

    def test_a_project_file_at_the_same_path_is_still_refused(self):
        root = self.new_project("own")
        path = root / ".claude/agents/dev-team"
        path.parent.mkdir(parents=True)
        path.write_text("# my own agent\n\nsee core/versions/2.50.2/agents\n", encoding="utf-8")
        code, out, _ = self.run_cli("--json", "bind", str(root), "--provider", "claude", "--mode", "link")
        self.assertEqual(code, 4)
        self.assertIn("was not created by", json.loads(out)["error"])
        self.assertTrue(path.is_file() and not path.is_symlink())

    def test_a_stub_outside_the_project_is_not_managed(self):
        outside = self.tmp / "elsewhere" / "dev-team"
        outside.parent.mkdir()
        outside.write_text(MAC_CORE + "/agents", encoding="utf-8")
        root = self.new_project("outside")
        self.assertFalse(bind._is_managed_path(".claude/agents/dev-team", outside, set(), root))


@requires_bash()
class ForeignCoreLinkProviderParityTest(StoreTestCase):
    """Every provider's bind replaces the shared runtime links committed from another machine."""

    def setUp(self):
        super().setUp()
        versions.install_from_tree(REPO_ROOT, version="9.9.9", force=True, make_current=True)
        self._home = os.environ.get("HOME")
        fake_home = self.tmp / "fake-home"
        fake_home.mkdir()
        os.environ["HOME"] = str(fake_home)
        self.addCleanup(self._restore_home)

    def _restore_home(self):
        if self._home is None:
            os.environ.pop("HOME", None)
        else:
            os.environ["HOME"] = self._home

    def test_every_provider_has_a_tools_case(self):
        self.assertEqual(set(TOOLS), set(providers.ALL_PROVIDERS))

    #: provider -> (artifact path its bind owns, core tree a committed link names).
    PROVIDER_LINKS = {
        "claude": (".claude/agents/dev-team", "agents"),
        "codex": (".codex/skills/dev-team-agents", "skills"),
        "opencode": (".opencode/skills/dev-team-agents", "skills"),
    }

    def test_every_provider_has_a_link_case(self):
        self.assertEqual(set(self.PROVIDER_LINKS), set(providers.ALL_PROVIDERS))

    def test_each_providers_own_link_stub_is_replaced(self):
        for provider in providers.ALL_PROVIDERS:
            with self.subTest(provider=provider):
                missing = [t for t in TOOLS[provider] if shutil.which(t) is None]
                if missing:
                    self.skipTest("{} needs {}".format(provider, ", ".join(missing)))
                rel, tree = self.PROVIDER_LINKS[provider]
                root = self.new_project("own-" + provider)
                stub = root / rel
                stub.parent.mkdir(parents=True, exist_ok=True)
                stub.write_text(MAC_CORE + "/" + tree, encoding="utf-8")
                code, out, err = self.run_cli(
                    "--json", "bind", str(root), "--provider", provider, "--mode", "link"
                )
                self.assertEqual(code, 0, out + err)
                self.assertTrue(stub.is_symlink() or stub.is_dir(), rel)
                # Moved, never deleted (No-Destruction Rule), on every provider.
                retired = {item["path"]: item["to"] for item in json.loads(out).get("retired", [])}
                self.assertIn(rel, retired)
                self.assertEqual(Path(retired[rel]).read_text(encoding="utf-8"), MAC_CORE + "/" + tree)

    #: delegated provider -> a file target its installer rewrites with `cp -f`.
    DELEGATED_FILES = {
        "codex": ".codex/agents/backend-developer.toml",
        "opencode": ".opencode/agents/backend-developer.md",
    }

    def test_every_delegated_provider_has_a_file_case(self):
        self.assertEqual(set(self.DELEGATED_FILES), set(providers.DELEGATED_INSTALLERS))

    def test_a_core_shaped_symlink_at_an_installer_file_is_not_written_through(self):
        for provider, rel in self.DELEGATED_FILES.items():
            with self.subTest(provider=provider):
                missing = [t for t in TOOLS[provider] if shutil.which(t) is None]
                if missing:
                    self.skipTest("{} needs {}".format(provider, ", ".join(missing)))
                outside = self.tmp / ("outside-" + provider) / "core" / "versions" / "9.9.9" / "skills" / "a"
                outside.mkdir(parents=True)
                victim = outside / "SKILL.md"
                victim.write_text("untouched\n", encoding="utf-8")
                root = self.new_project("through-" + provider)
                link = root / rel
                link.parent.mkdir(parents=True, exist_ok=True)
                os.symlink(str(victim), str(link))
                code, out, err = self.run_cli(
                    "--json", "bind", str(root), "--provider", provider, "--mode", "link"
                )
                self.assertEqual(code, 0, out + err)
                self.assertEqual(victim.read_text(encoding="utf-8"), "untouched\n")
                self.assertTrue(link.is_file() and not link.is_symlink(), rel)

    def test_each_providers_bind_replaces_runtime_stubs(self):
        for provider in providers.ALL_PROVIDERS:
            with self.subTest(provider=provider):
                missing = [t for t in TOOLS[provider] if shutil.which(t) is None]
                if missing:
                    self.skipTest("{} needs {}".format(provider, ", ".join(missing)))
                root = self.new_project("parity-" + provider)
                for rel, tree in RUNTIME_LINKS.items():
                    path = root / rel
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(MAC_CORE + "/" + tree, encoding="utf-8")
                code, out, err = self.run_cli(
                    "--json", "bind", str(root), "--provider", provider, "--mode", "link"
                )
                self.assertEqual(code, 0, out + err)
                for rel in RUNTIME_LINKS:
                    self.assertTrue((root / rel).is_symlink(), rel)
