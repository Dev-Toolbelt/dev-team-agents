"""Vendored third-party skills: pinned content, and every provider receives the whole folder.

The skills under `skills/third-party/` carry references, scripts and data beside
their SKILL.md, so a provider that received only the SKILL.md would hand agents a
skill whose instructions point at files that are not there.
"""

import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest import mock

from devteam_support import REPO_ROOT, StoreTestCase, requires_bash

from devteam import bind, providers, versions

THIRD_PARTY = REPO_ROOT / "skills" / "third-party"
MANIFEST = json.loads((THIRD_PARTY / "sources.json").read_text(encoding="utf-8"))

#: Where a bound project exposes a third-party skill, per provider. One entry per
#: provider in `providers.ALL_PROVIDERS` — the parity guard fails when one is added
#: without its own case.
SKILL_PATHS = {
    "claude": ".claude/skills/{name}",
    "opencode": ".opencode/skills/dev-team-agents/third-party/{name}",
    "codex": ".codex/skills/dev-team-agents/third-party/{name}",
}

TOOLS = {"claude": (), "opencode": ("bash", "python3", "jq"), "codex": ("bash", "python3")}

#: One routing skill per category of vendored skill (ADR-0047).
ROUTING_SKILLS = (
    REPO_ROOT / "skills" / "design" / "third-party-design-skills" / "SKILL.md",
    REPO_ROOT / "skills" / "shared" / "third-party-writing-skills" / "SKILL.md",
)


def _load_helper():
    spec = importlib.util.spec_from_file_location(
        "third_party_skills", REPO_ROOT / "helpers" / "third-party-skills.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


helper = _load_helper()


def _files(root):
    return sorted(p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file())


class ThirdPartyManifestTest(unittest.TestCase):
    def test_routing_skills_name_every_provider_path_and_skill(self):
        texts = [path.read_text(encoding="utf-8") for path in ROUTING_SKILLS]
        for path, text in zip(ROUTING_SKILLS, texts):
            for provider, template in SKILL_PATHS.items():
                with self.subTest(routing=path.parent.name, provider=provider):
                    self.assertIn("`{}/`".format(template.format(name="<name>")), text)
        for name in MANIFEST["skills"]:
            with self.subTest(skill=name):
                self.assertTrue(any("`{}`".format(name) in text for text in texts))

    def test_impeccable_ships_no_executable(self):
        # ADR-0047: its launcher downloads and runs an engine binary nobody here pins.
        self.assertFalse((THIRD_PARTY / "impeccable" / "scripts").exists())

    def test_stop_slop_ships_markdown_only(self):
        # Pinned at the repository root (`path: "."`), so anything upstream adds would be vendored.
        root = THIRD_PARTY / "stop-slop"
        for path in root.rglob("*"):
            if path.is_file():
                with self.subTest(file=path.name):
                    self.assertTrue(path.suffix == ".md" or path.name == "LICENSE")
                    self.assertFalse(os.access(path, os.X_OK))

    def test_vendored_trees_match_their_recorded_hash(self):
        result = subprocess.run(
            [sys.executable, "-I", str(REPO_ROOT / "helpers" / "third-party-skills.py"), "verify"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_every_entry_is_pinned_to_a_full_commit_with_a_license(self):
        for name, entry in MANIFEST["skills"].items():
            with self.subTest(skill=name):
                self.assertRegex(entry["commit"], r"^[0-9a-f]{40}$")
                self.assertTrue(entry["license"])
                for license_file in entry["license_files"]:
                    self.assertTrue((THIRD_PARTY / name / Path(license_file).name).is_file())


@requires_bash()
class ThirdPartyDeliveryTest(StoreTestCase):
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

    def _require_tools(self, provider):
        missing = [tool for tool in TOOLS[provider] if shutil.which(tool) is None]
        if missing:
            self.skipTest("{} needs {}".format(provider, ", ".join(missing)))

    def test_every_provider_has_a_case(self):
        self.assertEqual(set(SKILL_PATHS), set(providers.ALL_PROVIDERS))
        self.assertEqual(set(TOOLS), set(providers.ALL_PROVIDERS))

    def test_every_provider_receives_the_whole_skill_folder(self):
        for provider in providers.ALL_PROVIDERS:
            with self.subTest(provider=provider):
                self._require_tools(provider)
                root = self.new_project("third-party-{}".format(provider))
                bind.bind(root, provider_names=[provider], mode="link")
                for name in MANIFEST["skills"]:
                    exposed = root / SKILL_PATHS[provider].format(name=name)
                    self.assertTrue((exposed / "SKILL.md").is_file(), exposed)
                    self.assertEqual(_files(exposed.resolve()), _files(THIRD_PARTY / name), name)

    def test_a_projects_own_copy_is_kept_and_the_bind_succeeds(self):
        name = sorted(MANIFEST["skills"])[0]
        for provider in providers.ALL_PROVIDERS:
            for mode in ("link", "vendored"):
                with self.subTest(provider=provider, mode=mode):
                    self._require_tools(provider)
                    root = self.new_project("own-copy-{}-{}".format(provider, mode))
                    own = root / ".claude" / "skills" / name / "SKILL.md"
                    own.parent.mkdir(parents=True)
                    own.write_text("---\nname: {}\ndescription: mine\n---\n".format(name), encoding="utf-8")
                    warnings = []
                    emitter = mock.Mock(warn=warnings.append)

                    bind.bind(root, provider_names=[provider], mode=mode, emitter=emitter)

                    self.assertFalse(own.parent.is_symlink())
                    self.assertIn("description: mine", own.read_text(encoding="utf-8"))
                    if provider == "claude" or mode == "vendored":
                        self.assertTrue(any(name in w for w in warnings), warnings)
                    manifest = bind.read_manifest(bind.project.load(root)["project_id"])
                    claimed = {item["path"] for item in manifest["artifacts"]}
                    self.assertNotIn(".claude/skills/{}".format(name), claimed)


def _tarball(members):
    """An in-memory .tar.gz of ``(name, data_or_None, kind)`` under a `repo-sha/` root."""
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        for name, data, kind in members:
            info = tarfile.TarInfo("repo-sha/" + name)
            if kind == "symlink":
                info.type = tarfile.SYMTYPE
                info.linkname = data
                tar.addfile(info)
                continue
            info.size = len(data)
            info.mode = 0o755 if kind == "exec" else 0o644
            tar.addfile(info, io.BytesIO(data))
    buffer.seek(0)
    return buffer


SKILL = b"---\nname: demo\ndescription: d\n---\n"
ENTRY = {
    "repo": "owner/repo",
    "commit": "0" * 40,
    "path": "skills/demo",
    "license": "MIT",
    "license_files": ["LICENSE"],
    "exclude": ["scripts/**"],
}


class ThirdPartyExtractionTest(unittest.TestCase):
    @contextmanager
    def _served(self, members):
        with mock.patch.object(helper.urllib.request, "urlopen", return_value=_tarball(members)):
            yield

    def _fetch(self, members, entry=ENTRY):
        dest = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, dest, True)
        with self._served(members):
            helper.fetch(entry, dest)
        return dest

    def test_a_repository_root_skill_is_extracted_with_its_excludes(self):
        entry = dict(ENTRY, path=".", exclude=["README.md"])
        helper.validate_entry("demo", entry)
        dest = self._fetch([
            ("SKILL.md", SKILL, "file"),
            ("references/a.md", b"a", "file"),
            ("README.md", b"r", "file"),
            ("LICENSE", b"MIT", "file"),
        ], entry)
        self.assertEqual(_files(dest), ["LICENSE", "SKILL.md", "references/a.md"])

    @unittest.skipIf(os.name == "nt", "Windows has no POSIX executable bit: chmod only toggles read-only and os.access(X_OK) is true for every file")
    def test_extracts_the_subset_with_modes_and_licenses_and_honors_excludes(self):
        dest = self._fetch([
            ("skills/demo/SKILL.md", SKILL, "file"),
            ("skills/demo/tool.sh", b"#!/bin/sh\n", "exec"),
            ("skills/demo/scripts/launcher", b"x", "exec"),
            ("skills/other/SKILL.md", SKILL, "file"),
            ("LICENSE", b"MIT", "file"),
        ])
        self.assertEqual(_files(dest), ["LICENSE", "SKILL.md", "tool.sh"])
        self.assertTrue(os.access(dest / "tool.sh", os.X_OK))
        self.assertFalse(os.access(dest / "SKILL.md", os.X_OK))

    @unittest.skipIf(os.name == "nt", "Windows has no POSIX executable bit: chmod only toggles read-only and os.access(X_OK) is true for every file")
    def test_mode_change_changes_the_hash(self):
        dest = self._fetch([("skills/demo/SKILL.md", SKILL, "file"), ("LICENSE", b"MIT", "file")])
        before = helper.tree_hash(dest)
        os.chmod(dest / "SKILL.md", 0o755)
        self.assertNotEqual(before, helper.tree_hash(dest))

    def test_refuses_unsafe_archives(self):
        cases = {
            "symlink": [("skills/demo/SKILL.md", SKILL, "file"), ("skills/demo/x", "/etc/passwd", "symlink")],
            "dotdot": [("skills/demo/../../evil", b"x", "file")],
            "no-skill": [("skills/demo/README.md", b"x", "file"), ("LICENSE", b"MIT", "file")],
            "no-license": [("skills/demo/SKILL.md", SKILL, "file")],
            "license-collision": [("skills/demo/SKILL.md", SKILL, "file"), ("skills/demo/LICENSE", b"a", "file"), ("LICENSE", b"b", "file")],
        }
        for label, members in cases.items():
            with self.subTest(case=label), self.assertRaises(ValueError):
                self._fetch(members)

    def test_archive_and_skill_size_caps_stop_extraction(self):
        members = [("skills/demo/SKILL.md", SKILL, "file"), ("skills/demo/big", b"x" * 64, "file"), ("LICENSE", b"MIT", "file")]
        for cap in ("MAX_ARCHIVE_BYTES", "MAX_SKILL_BYTES"):
            with self.subTest(cap=cap), mock.patch.object(helper, cap, 32), self.assertRaises(ValueError):
                self._fetch(members)

    def test_case_variant_license_collision_is_refused(self):
        with self.assertRaises(ValueError):
            self._fetch([("skills/demo/SKILL.md", SKILL, "file"), ("skills/demo/license", b"a", "file"), ("LICENSE", b"b", "file")])

    def test_rejects_unpinned_or_unsafe_manifest_entries(self):
        bad = {
            "branch": dict(ENTRY, commit="main"),
            "path": dict(ENTRY, path="../x"),
            "dot-slash path": dict(ENTRY, path="./"),
            "empty path": dict(ENTRY, path=""),
            "missing path": {k: v for k, v in ENTRY.items() if k != "path"},
            "license": dict(ENTRY, license_files=["SKILL.md"]),
        }
        for label, entry in bad.items():
            with self.subTest(case=label), self.assertRaises(ValueError):
                helper.validate_entry("demo", entry)
        with self.assertRaises(ValueError):
            helper.validate_entry("../demo", ENTRY)

    def test_tree_hash_refuses_a_symlinked_directory(self):
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root, True)
        (root / "SKILL.md").write_text("x", encoding="utf-8")
        os.symlink(str(root.parent), str(root / "escape"))
        with self.assertRaises(ValueError):
            helper.tree_hash(root)


if __name__ == "__main__":
    unittest.main()
