"""Symlink stubs: a pre-v2.1.0 install committed from Windows Git Bash / MSYS.

There the v2 links (`.claude/agents/dev-team`, `.claude/skills/*`, ...) are regular
files (git mode 100644) holding a symlink stub rather than a symlink. `bind` used to
refuse them as foreign and `migrate` did not see them as a v2 install.
"""

import json
import os
import subprocess
import unittest
from pathlib import Path
from unittest import mock

import shutil

from devteam_support import REPO_ROOT, StoreTestCase, requires_bash

from devteam import bind, migrate, project, providers, versions
from devteam.errors import ConflictError

# Byte-exact copy of a real MSYS stub for `../dev-team-agents/agents` (58 bytes).
REAL_INTXLNK = bytes.fromhex(
    "496e74784c4e4b01" "2e002e002f006400"
    "65007600" "2d007400" "65006100" "6d002d00"
    "6100670065006e00" "74007300" "2f006100"
    "67006500" "6e007400" "7300"
)


def _intxlnk(target):
    return b"IntxLNK\x01" + target.encode("utf-16-le")


def _cygwin_bom(target):
    return b"!<symlink>" + b"\xff\xfe" + target.encode("utf-16-le") + b"\0\0"


def _cygwin_utf8(target):
    return b"!<symlink>" + target.encode("utf-8") + b"\0"


def _git_plain(target):
    return target.encode("utf-8")


#: Every stub encoding a checkout can write, name -> encoder.
FORMATS = {
    "intxlnk": _intxlnk,
    "cygwin-bom": _cygwin_bom,
    "cygwin-utf8": _cygwin_utf8,
    "git-plain": _git_plain,
}


class ReadLinkStubTest(StoreTestCase):
    def _write(self, name, raw):
        path = self.tmp / name
        path.write_bytes(raw)
        return path

    def test_the_real_msys_bytes_decode_to_the_link_target(self):
        self.assertEqual(len(REAL_INTXLNK), 58)
        self.assertEqual(REAL_INTXLNK, _intxlnk("../dev-team-agents/agents"))
        path = self._write("real", REAL_INTXLNK)
        self.assertEqual(providers.read_link_stub(path), "../dev-team-agents/agents")

    def test_each_format_decodes_to_its_target(self):
        for name, encode in FORMATS.items():
            with self.subTest(fmt=name):
                path = self._write("stub-" + name, encode("../dev-team-agents/skills/x"))
                self.assertEqual(providers.read_link_stub(path), "../dev-team-agents/skills/x")

    def test_trailing_nuls_and_whitespace_are_stripped(self):
        path = self._write("nul", _intxlnk("../a/b") + b"\0\0")
        self.assertEqual(providers.read_link_stub(path), "../a/b")
        path = self._write("nl", _git_plain("../a/b") + b"\n")
        self.assertEqual(providers.read_link_stub(path), "../a/b")

    def test_a_utf8_bom_is_not_part_of_the_target(self):
        for name, raw in (
            ("plain", b"\xef\xbb\xbf../a/b"),
            ("cygwin", b"!<symlink>\xef\xbb\xbf../a/b\0"),
        ):
            with self.subTest(case=name):
                self.assertEqual(providers.read_link_stub(self._write(name, raw)), "../a/b")

    def test_a_big_endian_stub_is_not_one(self):
        raw = b"!<symlink>\xfe\xff" + "../a/b".encode("utf-16-be")
        self.assertIsNone(providers.read_link_stub(self._write("be", raw)))
        raw = b"IntxLNK\x01\xfe\xff" + "../a/b".encode("utf-16-be")
        self.assertIsNone(providers.read_link_stub(self._write("be-intx", raw)))

    def test_things_that_are_not_stubs_return_none(self):
        random_binary = bytes(range(256)) * 4
        oversized = _git_plain("a" * (providers.LINK_STUB_MAX + 1))
        multiline = _git_plain("one\ntwo")
        for name, raw in (
            ("random", random_binary),
            ("oversized", oversized),
            ("multiline", multiline),
            ("empty", b""),
            ("bad-utf8", b"\xff\xfe\xfa"),
        ):
            with self.subTest(case=name):
                self.assertIsNone(providers.read_link_stub(self._write(name, raw)))

    def test_directories_symlinks_and_missing_paths_return_none(self):
        directory = self.tmp / "dir"
        directory.mkdir()
        self.assertIsNone(providers.read_link_stub(directory))
        self.assertIsNone(providers.read_link_stub(self.tmp / "missing"))
        target = self._write("target", _git_plain("../x"))
        link = self.tmp / "link"
        try:
            os.symlink(str(target), str(link))
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable")
        self.assertIsNone(providers.read_link_stub(link))


class V2LinkFileTest(StoreTestCase):
    def setUp(self):
        super().setUp()
        self.install_version("3.0.0", activate=True)
        self.version_dir = versions.require(versions.resolve(None))
        self.root = self.new_project("stubs")

    def _stub(self, rel, raw):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        return path

    def test_a_stub_into_the_install_is_a_v2_copy_in_every_format(self):
        for name, encode in FORMATS.items():
            for target in ("../dev-team-agents/agents", "../../.dev-team-agents/agents"):
                with self.subTest(fmt=name, target=target):
                    path = self._stub(".claude/agents/dev-team", encode(target))
                    self.assertTrue(
                        bind.v2_copy(".claude/agents/dev-team", path, self.version_dir, self.root)
                    )

    def test_backslash_targets_are_handled(self):
        path = self._stub(".claude/agents/dev-team", _intxlnk("..\\dev-team-agents\\agents"))
        self.assertTrue(bind._v2_link_file(path, self.root))

    def test_an_absolute_target_inside_the_install_is_accepted(self):
        target = (self.root / ".dev-team-agents" / "agents").as_posix()
        path = self._stub(".claude/agents/dev-team", _intxlnk(target))
        self.assertTrue(bind._v2_link_file(path, self.root))

    def test_a_stub_escaping_the_install_is_rejected(self):
        for target in (
            "../../etc",
            "../other/dev-team-agents-x",
            "../../../dev-team-agents/agents",
            "../dev-team-agents-x/agents",
            "/etc/passwd",
        ):
            for name, encode in FORMATS.items():
                with self.subTest(fmt=name, target=target):
                    path = self._stub(".claude/agents/dev-team", encode(target))
                    self.assertFalse(bind._v2_link_file(path, self.root))
                    self.assertFalse(
                        bind.v2_copy(".claude/agents/dev-team", path, self.version_dir, self.root)
                    )

    def test_a_stub_reached_through_a_symlinked_parent_is_not_this_projects(self):
        elsewhere = self.tmp / "elsewhere" / ".codex" / "skills"
        elsewhere.mkdir(parents=True)
        (elsewhere / "dev-team-agents").write_bytes(_intxlnk("../../.dev-team-agents/skills"))
        try:
            os.symlink(str(elsewhere.parent), str(self.root / ".codex"))
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable")
        stub = self.root / ".codex" / "skills" / "dev-team-agents"
        self.assertFalse(bind._v2_link_file(stub, self.root))
        self.assertNotIn(".codex/skills/dev-team-agents", bind.v2_copies(self.version_dir, self.root))

    def test_an_msys_drive_path_reads_as_its_windows_drive(self):
        with mock.patch.object(bind.os, "name", "nt"):
            self.assertEqual(bind._msys_drive_path("/c/proj/x"), "c:/proj/x")
            self.assertEqual(bind._msys_drive_path("/c"), "c:/")
            self.assertEqual(bind._msys_drive_path("/etc/passwd"), "/etc/passwd")
            self.assertEqual(bind._msys_drive_path("../a"), "../a")
        with mock.patch.object(bind.os, "name", "posix"):
            self.assertEqual(bind._msys_drive_path("/c/proj/x"), "/c/proj/x")

    def test_a_plain_project_markdown_file_is_not_a_link(self):
        path = self._stub(".claude/commands/devteam", b"# my own command\n\nbody\n")
        self.assertFalse(bind.v2_copy(".claude/commands/devteam", path, self.version_dir, self.root))
        path = self._stub(".claude/commands/devteam", b"notes about .dev-team-agents\n")
        self.assertFalse(bind._v2_link_file(path, self.root))


def _git(root, *args, env=None):
    return subprocess.run(
        ["git"] + list(args), cwd=str(root), check=True, stdout=subprocess.PIPE, env=env
    ).stdout.decode()


_COUNTER = [0]


def _windows_stub_project(case, fmt):
    """A pre-v2.1.0 install as Git Bash committed it: links are 100644 stub files."""
    encode = FORMATS[fmt]
    _COUNTER[0] += 1
    root = case.new_project("win-{}-{}".format(fmt, _COUNTER[0]))
    legacy = root / ".claude" / "dev-team-agents"
    for name in ("agents", "commands", "scripts", "skills", "templates", "workflows"):
        (legacy / name).mkdir(parents=True, exist_ok=True)
        (legacy / name / "keep.md").write_text("# " + name + "\n", encoding="utf-8")
    (legacy / "scripts" / "hooks").mkdir()
    (legacy / "scripts" / "hooks" / "stop.sh").write_text("#!/bin/sh\n", encoding="utf-8")
    claude = root / ".claude"
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
                }
            }
        ),
        encoding="utf-8",
    )
    stubs = {
        ".claude/agents/dev-team": "../dev-team-agents/agents",
        ".claude/commands/devteam": "../dev-team-agents/commands",
        ".claude/skills/project-context": "../dev-team-agents/skills/shared/project-context",
        ".claude/skills/unit": "../dev-team-agents/skills/testing/unit",
    }
    for rel, target in stubs.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_bytes(encode(target))
    own = claude / "commands" / "create-site.md"
    own.write_text("# create the site\n", encoding="utf-8")
    env = MIGRATE_ENV()
    _git(root, "add", "-A")
    _git(root, "-c", "core.symlinks=false", "commit", "-qm", "v2.0 install", env=env)
    return root, sorted(stubs)


def MIGRATE_ENV():
    return dict(
        os.environ,
        GIT_AUTHOR_NAME="t",
        GIT_AUTHOR_EMAIL="t@e",
        GIT_COMMITTER_NAME="t",
        GIT_COMMITTER_EMAIL="t@e",
    )


class WindowsStubProjectTest(StoreTestCase):
    def setUp(self):
        super().setUp()
        self.install_version("3.0.0", activate=True)

    def test_the_fixture_commits_the_stubs_as_regular_files(self):
        root, stubs = _windows_stub_project(self, "intxlnk")
        listing = _git(root, "ls-files", "-s", "--", *stubs)
        self.assertEqual(listing.count("100644"), len(stubs))

    def test_bind_refuses_with_the_v2_reason_not_the_foreign_path_error(self):
        for fmt in FORMATS:
            with self.subTest(fmt=fmt):
                root, stubs = _windows_stub_project(self, fmt)
                code, out, _ = self.run_cli("--json", "bind", str(root), "--provider", "claude", "--mode", "link")
                self.assertEqual(code, 4)
                payload = json.loads(out)
                self.assertIn("devteam migrate", payload["hint"])
                self.assertTrue(payload["details"]["path"].endswith(".claude/dev-team-agents"))
                self.assertNotIn("was not created by", payload["error"])
                for rel in stubs:
                    self.assertTrue((root / rel).is_file() and not (root / rel).is_symlink(), rel)

    def test_the_plan_lists_the_stubs_as_copies_and_as_git_tracked(self):
        for fmt in FORMATS:
            with self.subTest(fmt=fmt):
                root, stubs = _windows_stub_project(self, fmt)
                preview = migrate.plan(root, provider_names=["claude"], mode="link")
                self.assertEqual(sorted(preview["v2_copies"]), stubs)
                self.assertTrue(set(stubs) <= set(preview["git_tracked"]))
                self.assertNotIn(".claude/commands/create-site.md", preview["v2_copies"])

    def test_apply_with_untrack_quarantines_binds_and_keeps_project_files(self):
        for fmt in FORMATS:
            with self.subTest(fmt=fmt):
                root, stubs = _windows_stub_project(self, fmt)
                result = migrate.apply(
                    root, provider_names=["claude"], mode="link", untrack_paths=True
                )
                moved = {item["from"] for item in result["quarantined"]}
                self.assertTrue(set(stubs) <= moved)
                quarantine_dir = Path(result["quarantine_dir"])
                kept = [p for p in quarantine_dir.rglob("*") if p.is_file()]
                self.assertTrue(any(p.name == "dev-team" for p in kept))
                for rel in stubs:
                    self.assertTrue((root / rel).is_symlink(), rel)
                self.assertEqual(
                    (root / ".claude/commands/create-site.md").read_text(encoding="utf-8"),
                    "# create the site\n",
                )
                self.assertTrue(project.load(root))
                index = _git(root, "ls-files", "--", *stubs).split()
                self.assertEqual(index, [])
                self.assertIn(
                    ".claude/commands/create-site.md",
                    _git(root, "ls-files", "--", ".claude/commands").split(),
                )
                self.assertEqual(migrate.leftover_trees(root), [])


class ProviderStubParityTest(StoreTestCase):
    """Every provider's v2 stub is recognised, quarantined and bound over.

    One case per provider in `providers.ALL_PROVIDERS`: the guard fails when a
    provider is added without one, as in `test_provider_ownership.py`.
    """

    #: provider -> (stub path, install-relative target) a v2 install of it committed.
    STUBS = {
        "claude": (".claude/skills/project-context", "../dev-team-agents/skills/shared/project-context"),
        "codex": (".codex/skills/dev-team-agents", "../../.dev-team-agents/skills"),
        "opencode": (".opencode/skills/dev-team-agents", "../../.dev-team-agents/skills"),
    }

    def setUp(self):
        super().setUp()
        self.install_version("3.0.0", activate=True)
        self.version_dir = versions.require(versions.resolve(None))

    def test_every_provider_has_a_stub_case(self):
        self.assertEqual(set(self.STUBS), set(providers.ALL_PROVIDERS))

    def test_each_providers_stub_is_reported_as_a_v2_copy(self):
        for provider in providers.ALL_PROVIDERS:
            rel, target = self.STUBS[provider]
            for fmt, encode in FORMATS.items():
                with self.subTest(provider=provider, fmt=fmt):
                    root, _ = _windows_stub_project(self, "intxlnk")
                    stub = root / rel
                    stub.parent.mkdir(parents=True, exist_ok=True)
                    stub.write_bytes(encode(target))
                    self.assertIn(rel, bind.v2_copies(self.version_dir, root))

    def test_a_foreign_stub_is_still_refused_for_each_provider(self):
        for provider in providers.ALL_PROVIDERS:
            rel, _ = self.STUBS[provider]
            with self.subTest(provider=provider):
                root, _ = _windows_stub_project(self, "intxlnk")
                stub = root / rel
                stub.parent.mkdir(parents=True, exist_ok=True)
                stub.write_bytes(_intxlnk("../../somewhere/else"))
                self.assertNotIn(rel, bind.v2_copies(self.version_dir, root))


#: Tools each provider's real installer needs, as in `test_provider_ownership.py`.
TOOLS = {"claude": (), "opencode": ("bash", "python3", "jq"), "codex": ("bash", "python3")}


@requires_bash()
class ProviderStubMigrationTest(StoreTestCase):
    """The delegated providers' installers run for real, so migrate's bind is the real one."""

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

    def _require_tools(self, provider):
        missing = [t for t in TOOLS[provider] if shutil.which(t) is None]
        if missing:
            self.skipTest("{} needs {}".format(provider, ", ".join(missing)))

    def test_each_delegated_v2_link_is_a_path_its_installer_owns(self):
        version_dir = versions.require(versions.resolve(None))
        root = self.new_project("targets")
        for provider in providers.ALL_PROVIDERS:
            rel, _ = ProviderStubParityTest.STUBS[provider]
            if rel not in providers.V2_SKILL_LINKS:
                continue
            with self.subTest(provider=provider):
                self._require_tools(provider)
                self.assertIn(rel, providers.delegated_targets(provider, version_dir, root))

    def test_bind_over_each_providers_stub_refuses_with_the_v2_reason(self):
        for provider in providers.ALL_PROVIDERS:
            rel, target = ProviderStubParityTest.STUBS[provider]
            with self.subTest(provider=provider):
                self._require_tools(provider)
                root = self.new_project("bind-" + provider)
                stub = root / rel
                stub.parent.mkdir(parents=True, exist_ok=True)
                stub.write_bytes(_intxlnk(target))
                code, out, _ = self.run_cli(
                    "--json", "bind", str(root), "--provider", provider, "--mode", "link"
                )
                self.assertEqual(code, 4, out)
                self.assertEqual(json.loads(out)["details"]["reason"], bind.V2_INSTALL_REASON)
                self.assertTrue(stub.is_file() and not stub.is_symlink(), rel)

    def test_each_providers_stub_is_quarantined_by_migrate(self):
        for provider in providers.ALL_PROVIDERS:
            rel, target = ProviderStubParityTest.STUBS[provider]
            with self.subTest(provider=provider):
                missing = [t for t in TOOLS[provider] if shutil.which(t) is None]
                if missing:
                    self.skipTest("{} needs {}".format(provider, ", ".join(missing)))
                root, _ = _windows_stub_project(self, "intxlnk")
                stub = root / rel
                stub.parent.mkdir(parents=True, exist_ok=True)
                stub.write_bytes(_intxlnk(target))
                result = migrate.apply(root, provider_names=[provider], mode="link")
                self.assertIn(rel, {item["from"] for item in result["quarantined"]})
                self.assertFalse(stub.is_file() and not stub.is_symlink(), rel)
                quarantined = [
                    p for p in Path(result["quarantine_dir"]).rglob(stub.name) if p.is_file()
                ]
                self.assertTrue(quarantined, rel)


if __name__ == "__main__":
    unittest.main()
