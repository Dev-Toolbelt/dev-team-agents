"""`devteam skills` — the providers' user-level skill directories (ADR-0020).

Every test runs against ``$DEVTEAM_USER_HOME`` pinned by ``StoreTestCase`` to a temp
directory, so none of them can read or write the developer's real ``~/.claude/skills``.
"""

from __future__ import annotations

import json
import os
import stat
import unittest
import zipfile

from devteam_support import StoreTestCase

from devteam import compat, errors


def write_skill(directory, name, description="does a thing", extra=""):
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "SKILL.md").write_text(
        "---\nname: {}\ndescription: {}\n{}---\n\n# {}\n\nBody.\n".format(name, description, extra, name),
        encoding="utf-8",
    )
    return directory


class GlobalSkillsTestCase(StoreTestCase):
    def setUp(self):
        super().setUp()
        # The roots honor these before `~`; an ambient value must not leak into a test.
        for name in ("CODEX_HOME", "XDG_CONFIG_HOME"):
            saved = os.environ.pop(name, None)
            if saved is not None:
                self.addCleanup(os.environ.__setitem__, name, saved)
        self.claude_root = self.user_home / ".claude" / "skills"
        self.agents_root = self.user_home / ".agents" / "skills"
        self.codex_root = self.user_home / ".codex" / "skills"
        self.opencode_root = self.user_home / ".config" / "opencode" / "skills"

    def cli_json(self, *args, expect=0):
        code, out, err = self.run_cli("skills", *args, "--json")
        self.assertEqual(code, expect, "exit {} (wanted {}): {} {}".format(code, expect, out, err))
        return json.loads(out) if out.strip() else None


class ListAndShowTest(GlobalSkillsTestCase):
    def test_empty_home_lists_every_root_as_absent(self):
        payload = self.cli_json("list")
        self.assertEqual(payload["count"], 0)
        self.assertEqual([r["id"] for r in payload["roots"]], ["claude", "agents", "codex", "opencode"])
        self.assertTrue(all(r["exists"] is False for r in payload["roots"]))

    def test_list_reports_providers_per_physical_root(self):
        write_skill(self.claude_root / "alpha", "alpha")
        write_skill(self.agents_root / "beta", "beta")
        payload = self.cli_json("list")
        by_name = {s["name"]: s for s in payload["skills"]}
        self.assertEqual(by_name["alpha"]["providers"], ["claude", "opencode"])
        self.assertEqual(by_name["beta"]["providers"], ["codex", "opencode"])
        self.assertEqual(by_name["alpha"]["status"], "ok")

    def test_provider_filter_selects_the_roots_that_provider_reads(self):
        write_skill(self.claude_root / "alpha", "alpha")
        write_skill(self.codex_root / "gamma", "gamma")
        names = {s["name"] for s in self.cli_json("list", "--provider", "codex")["skills"]}
        self.assertEqual(names, {"gamma"})
        names = {s["name"] for s in self.cli_json("list", "--provider", "opencode")["skills"]}
        self.assertEqual(names, {"alpha"})

    def test_dot_entries_and_files_are_not_skills(self):
        write_skill(self.codex_root / ".system" / "bundled", "bundled")
        self.codex_root.mkdir(parents=True, exist_ok=True)
        (self.codex_root / ".DS_Store").write_text("x", encoding="utf-8")
        (self.codex_root / "notes.txt").write_text("x", encoding="utf-8")
        self.assertEqual(self.cli_json("list", "--provider", "codex")["count"], 0)

    def test_malformed_entries_are_reported_not_raised(self):
        (self.claude_root / "empty").mkdir(parents=True)
        write_skill(self.claude_root / "renamed", "other-name")
        by_name = {s["name"]: s for s in self.cli_json("list")["skills"]}
        self.assertEqual(by_name["empty"]["status"], "malformed")
        self.assertIn("SKILL.md", by_name["empty"]["error"])
        self.assertIn("does not match", by_name["renamed"]["error"])

    def test_folded_description_and_nested_keys_are_read_leniently(self):
        skill = self.claude_root / "folded"
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text(
            "---\nname: folded\ndescription: >\n  first line\n  second line\n"
            "metadata:\n  author: someone\nallowed-tools:\n  - Read\n---\nBody\n",
            encoding="utf-8",
        )
        entry = self.cli_json("list")["skills"][0]
        self.assertEqual(entry["status"], "ok")
        self.assertEqual(entry["description"], "first line second line")

    def test_show_returns_body_and_files(self):
        skill = write_skill(self.claude_root / "alpha", "alpha")
        (skill / "references").mkdir()
        (skill / "references" / "more.md").write_text("x", encoding="utf-8")
        payload = self.cli_json("show", "alpha")
        self.assertIn("Body.", payload["body"])
        self.assertEqual(payload["files"], ["SKILL.md", "references/more.md"])
        self.assertFalse(payload["files_truncated"])

    def test_show_ambiguous_name_needs_root(self):
        write_skill(self.claude_root / "twin", "twin")
        write_skill(self.agents_root / "twin", "twin")
        self.cli_json("show", "twin", expect=errors.EXIT_USAGE)
        self.assertEqual(self.cli_json("show", "twin", "--root", "agents")["root"], "agents")

    def test_list_creates_nothing(self):
        self.cli_json("list")
        self.assertFalse(self.user_home.exists())
        self.assertFalse(self.home.exists())


class InstallTest(GlobalSkillsTestCase):
    def test_install_for_every_provider_uses_the_fewest_roots(self):
        # opencode reads the claude and agents roots, so it needs no copy of its own.
        source = write_skill(self.tmp / "src" / "alpha", "alpha")
        payload = self.cli_json("install", "--source", str(source))
        roots = sorted(item["root"] for item in payload["installed"])
        self.assertEqual(roots, ["agents", "claude"])
        for root in (self.claude_root, self.agents_root):
            self.assertTrue((root / "alpha" / "SKILL.md").is_file())
        self.assertFalse((self.opencode_root / "alpha").exists())
        self.assertFalse((self.codex_root / "alpha").exists(), "nothing new goes to ~/.codex/skills")
        self.assertTrue(source.is_dir(), "the source is copied, never moved")
        self.assertEqual(payload["also_present"], [])

    def test_opencode_alone_installs_into_its_own_root(self):
        source = write_skill(self.tmp / "src" / "alpha", "alpha")
        payload = self.cli_json("install", "--source", str(source), "--provider", "opencode")
        self.assertEqual([item["root"] for item in payload["installed"]], ["opencode"])

    def test_claude_and_opencode_share_one_root(self):
        source = write_skill(self.tmp / "src" / "alpha", "alpha")
        payload = self.cli_json(
            "install", "--source", str(source), "--provider", "claude", "--provider", "opencode"
        )
        self.assertEqual([item["root"] for item in payload["installed"]], ["claude"])

    def test_a_copy_in_another_root_the_provider_reads_is_reported(self):
        write_skill(self.opencode_root / "alpha", "alpha")
        source = write_skill(self.tmp / "src" / "alpha", "alpha")
        payload = self.cli_json("install", "--source", str(source), "--provider", "claude")
        self.assertEqual([o["root"] for o in payload["also_present"]], ["opencode"])

    def test_a_listed_only_root_is_never_written(self):
        source = write_skill(self.tmp / "src" / "alpha", "alpha")
        self.cli_json("install", "--source", str(source), "--root", "codex", expect=errors.EXIT_USAGE)
        self.assertFalse((self.codex_root / "alpha").exists())

    def test_install_one_provider(self):
        source = write_skill(self.tmp / "src" / "alpha", "alpha")
        payload = self.cli_json("install", "--source", str(source), "--provider", "claude")
        self.assertEqual([item["root"] for item in payload["installed"]], ["claude"])

    def test_install_uses_frontmatter_name_not_folder_name(self):
        source = write_skill(self.tmp / "src" / "some-folder", "real-name")
        self.cli_json("install", "--source", str(source), "--provider", "claude")
        self.assertTrue((self.claude_root / "real-name").is_dir())

    def test_conflict_refused_before_any_root_is_written(self):
        write_skill(self.agents_root / "alpha", "alpha", description="old")
        source = write_skill(self.tmp / "src" / "alpha", "alpha")
        self.cli_json("install", "--source", str(source), expect=errors.EXIT_CONFLICT)
        self.assertFalse((self.claude_root / "alpha").exists())

    def test_replace_quarantines_the_previous_copy(self):
        write_skill(self.claude_root / "alpha", "alpha", description="old")
        source = write_skill(self.tmp / "src" / "alpha", "alpha", description="new")
        payload = self.cli_json("install", "--source", str(source), "--provider", "claude", "--replace")
        item = payload["installed"][0]
        self.assertTrue(item["replaced"])
        self.assertIn("old", (self.tmp / item["quarantined_to"] / "SKILL.md").read_text(encoding="utf-8"))
        self.assertIn("new", (self.claude_root / "alpha" / "SKILL.md").read_text(encoding="utf-8"))

    def test_invalid_source_is_a_usage_error(self):
        bad = self.tmp / "src" / "bad"
        bad.mkdir(parents=True)
        (bad / "SKILL.md").write_text("---\nname: Bad Name\ndescription: x\n---\n", encoding="utf-8")
        self.cli_json("install", "--source", str(bad), expect=errors.EXIT_USAGE)
        (bad / "SKILL.md").write_text("no frontmatter", encoding="utf-8")
        self.cli_json("install", "--source", str(bad), expect=errors.EXIT_USAGE)
        self.cli_json("install", "--source", str(self.tmp / "missing"), expect=errors.EXIT_USAGE)

    def test_install_zip_with_a_single_top_folder(self):
        archive = self.tmp / "alpha.zip"
        with zipfile.ZipFile(str(archive), "w") as bundle:
            bundle.writestr("alpha/SKILL.md", "---\nname: alpha\ndescription: zipped\n---\nBody\n")
            bundle.writestr("alpha/references/x.md", "x")
        payload = self.cli_json("install", "--source", str(archive), "--provider", "claude")
        self.assertEqual(payload["description"], "zipped")
        self.assertTrue((self.claude_root / "alpha" / "references" / "x.md").is_file())

    def test_zip_slip_is_refused(self):
        archive = self.tmp / "evil.skill"
        with zipfile.ZipFile(str(archive), "w") as bundle:
            bundle.writestr("SKILL.md", "---\nname: evil\ndescription: x\n---\n")
            bundle.writestr("../../escaped.txt", "x")
        self.cli_json("install", "--source", str(archive), expect=errors.EXIT_USAGE)
        self.assertFalse((self.tmp / "escaped.txt").exists())
        self.assertFalse((self.claude_root / "evil").exists())

    def test_zip_symlink_member_is_refused(self):
        archive = self.tmp / "link.zip"
        with zipfile.ZipFile(str(archive), "w") as bundle:
            bundle.writestr("SKILL.md", "---\nname: link\ndescription: x\n---\n")
            info = zipfile.ZipInfo("pointer")
            info.external_attr = (stat.S_IFLNK | 0o777) << 16
            bundle.writestr(info, "/etc/passwd")
        self.cli_json("install", "--source", str(archive), expect=errors.EXIT_USAGE)

    def test_non_archive_file_is_refused(self):
        stray = self.tmp / "skill.txt"
        stray.write_text("x", encoding="utf-8")
        self.cli_json("install", "--source", str(stray), expect=errors.EXIT_USAGE)

    @unittest.skipUnless(os.name == "posix", "symlinks need privileges on Windows")
    def test_link_creates_a_symlink_to_the_source(self):
        source = write_skill(self.tmp / "src" / "alpha", "alpha")
        payload = self.cli_json("install", "--source", str(source), "--provider", "claude", "--link")
        self.assertTrue(payload["linked"])
        self.assertTrue((self.claude_root / "alpha").is_symlink())
        entry = self.cli_json("list", "--provider", "claude")["skills"][0]
        self.assertTrue(entry["is_symlink"])
        self.assertFalse(entry["managed"])

    @unittest.skipUnless(os.name == "posix", "symlinks need privileges on Windows")
    def test_symlink_inside_a_copied_source_is_refused(self):
        source = write_skill(self.tmp / "src" / "alpha", "alpha")
        os.symlink("/etc", str(source / "etc"))
        self.cli_json("install", "--source", str(source), "--provider", "claude", expect=errors.EXIT_USAGE)


class SingleFileSourceTest(GlobalSkillsTestCase):
    """A picked `.md` file: its folder only when that folder is the skill's own."""

    def test_a_loose_skill_md_installs_only_that_file(self):
        downloads = self.tmp / "Downloads"
        write_skill(downloads, "loose")
        (downloads / "project" / "node_modules").mkdir(parents=True)
        (downloads / "unrelated.pdf").write_text("x", encoding="utf-8")
        payload = self.cli_json("install", "--source", str(downloads / "SKILL.md"), "--provider", "claude")
        self.assertEqual(payload["source_kind"], "file")
        self.assertEqual(sorted(p.name for p in (self.claude_root / "loose").iterdir()), ["SKILL.md"])

    def test_skill_md_in_the_skills_own_folder_installs_the_folder(self):
        folder = write_skill(self.tmp / "src" / "alpha", "alpha")
        (folder / "references").mkdir()
        (folder / "references" / "more.md").write_text("x", encoding="utf-8")
        payload = self.cli_json("install", "--source", str(folder / "SKILL.md"), "--provider", "claude")
        self.assertEqual(payload["source_kind"], "folder")
        self.assertTrue((self.claude_root / "alpha" / "references" / "more.md").is_file())

    def test_any_md_file_with_frontmatter_is_a_single_file_skill(self):
        source = self.tmp / "my-note.md"
        source.write_text("---\nname: note-skill\ndescription: x\n---\nBody\n", encoding="utf-8")
        payload = self.cli_json("install", "--source", str(source), "--provider", "claude")
        self.assertEqual(payload["name"], "note-skill")
        self.assertTrue((self.claude_root / "note-skill" / "SKILL.md").is_file())

    def test_link_needs_a_folder(self):
        source = write_skill(self.tmp / "Downloads", "loose") / "SKILL.md"
        body = self.cli_json("install", "--source", str(source), "--provider", "claude", "--link",
                             expect=errors.EXIT_USAGE)
        self.assertEqual(body["details"]["reason"], "invalid-source")

    def test_a_folder_too_big_to_be_one_skill_is_refused(self):
        from unittest import mock
        from devteam import global_skills
        from devteam.errors import UsageError

        folder = write_skill(self.tmp / "src" / "alpha", "alpha")
        for index in range(5):
            (folder / "f{}.txt".format(index)).write_text("x", encoding="utf-8")
        with mock.patch.object(global_skills, "MAX_ARCHIVE_MEMBERS", 3):
            with self.assertRaisesRegex(UsageError, "does not look like one skill"):
                global_skills.install(str(folder), providers=["claude"])
        self.assertFalse((self.claude_root / "alpha").exists())


class RemoveTest(GlobalSkillsTestCase):
    def test_remove_moves_a_directory_to_quarantine(self):
        write_skill(self.claude_root / "alpha", "alpha")
        payload = self.cli_json("remove", "alpha")
        self.assertEqual(payload["action"], "quarantined")
        self.assertFalse((self.claude_root / "alpha").exists())
        from pathlib import Path

        self.assertTrue((Path(payload["quarantined_to"]) / "SKILL.md").is_file())
        self.assertIn(str(self.home), payload["quarantined_to"])

    @unittest.skipUnless(os.name == "posix", "symlinks need privileges on Windows")
    def test_remove_unlinks_a_symlink_and_keeps_its_target(self):
        target = write_skill(self.tmp / "elsewhere" / "alpha", "alpha")
        self.claude_root.mkdir(parents=True)
        os.symlink(str(target), str(self.claude_root / "alpha"))
        payload = self.cli_json("remove", "alpha")
        self.assertEqual(payload["action"], "unlinked")
        self.assertIsNone(payload["quarantined_to"])
        self.assertTrue((target / "SKILL.md").is_file())

    @unittest.skipUnless(os.name == "posix", "symlinks need privileges on Windows")
    def test_a_skill_managed_by_the_core_store_is_refused(self):
        self.install_version("3.0.0", activate=True)
        from devteam import paths

        core_skill = paths.core_dir() / "versions" / "3.0.0" / "skills" / "testing" / "unit"
        self.assertTrue(core_skill.is_dir(), core_skill)
        self.claude_root.mkdir(parents=True)
        os.symlink(str(core_skill), str(self.claude_root / "unit"))
        entry = self.cli_json("list", "--provider", "claude")["skills"][0]
        self.assertTrue(entry["managed"])
        self.cli_json("remove", "unit", expect=errors.EXIT_CONFLICT)
        self.assertTrue((self.claude_root / "unit").is_symlink())

    def test_missing_and_ambiguous_names(self):
        self.cli_json("remove", "nothing", expect=errors.EXIT_USAGE)
        write_skill(self.claude_root / "twin", "twin")
        write_skill(self.agents_root / "twin", "twin")
        self.cli_json("remove", "twin", expect=errors.EXIT_USAGE)
        self.assertEqual(self.cli_json("remove", "twin", "--root", "agents")["root"], "agents")
        self.assertTrue((self.claude_root / "twin").is_dir())

    def test_unknown_root_is_a_usage_error(self):
        self.cli_json("remove", "x", "--root", "nope", expect=errors.EXIT_USAGE)


class HostileNameTest(GlobalSkillsTestCase):
    """A name is matched among a root's children, never joined onto its path."""

    def setUp(self):
        super().setUp()
        write_skill(self.claude_root / "alpha", "alpha")
        (self.user_home / ".claude" / "other.txt").write_text("keep me", encoding="utf-8")

    def test_traversal_names_are_refused_by_show_and_remove(self):
        for name in ("..", ".", "../skills", "alpha/..", "a/b", "a\\b", str(self.user_home), "C:evil", ".hidden"):
            for command in ("show", "remove"):
                with self.subTest(command=command, name=name):
                    self.cli_json(command, name, "--root", "claude", expect=errors.EXIT_USAGE)
        self.assertTrue((self.user_home / ".claude" / "other.txt").is_file())
        self.assertTrue((self.claude_root / "alpha").is_dir())
        self.assertFalse(self.home.exists() and any(self.home.rglob("other.txt")))

    def test_nul_is_refused_in_process(self):
        from devteam import global_skills
        from devteam.errors import UsageError

        with self.assertRaises(UsageError):
            global_skills.remove("alpha\\0", "claude")


class RollbackTest(GlobalSkillsTestCase):
    """An I/O failure part-way leaves every root as it was, with no staging left over."""

    def _stages(self):
        return [
            p for root in (self.claude_root, self.agents_root) if root.is_dir()
            for p in root.iterdir() if p.name.startswith(".devteam-staging-")
        ]

    def test_a_failed_copy_installs_nothing_and_leaves_no_stage(self):
        from unittest import mock
        from devteam import global_skills

        source = write_skill(self.tmp / "src" / "alpha", "alpha")
        real_copytree = global_skills.shutil.copytree
        calls = []

        def failing(src, dst, **kwargs):
            calls.append(dst)
            if len(calls) == 2:
                raise OSError("disk full")
            return real_copytree(src, dst, **kwargs)

        with mock.patch.object(global_skills.shutil, "copytree", side_effect=failing):
            with self.assertRaises(OSError):
                global_skills.install(str(source), providers=["claude", "codex"])
        self.assertFalse((self.claude_root / "alpha").exists())
        self.assertFalse((self.agents_root / "alpha").exists())
        self.assertEqual(self._stages(), [])

    def test_a_failed_swap_restores_what_was_replaced(self):
        from unittest import mock
        from devteam import global_skills

        write_skill(self.claude_root / "alpha", "alpha", description="old claude")
        write_skill(self.agents_root / "alpha", "alpha", description="old agents")
        source = write_skill(self.tmp / "src" / "alpha", "alpha", description="new")
        real_replace = global_skills.os.replace
        calls = []

        def failing(src, dst):
            calls.append(dst)
            if len(calls) == 2:
                raise OSError("device busy")
            return real_replace(src, dst)

        with mock.patch.object(global_skills.os, "replace", side_effect=failing):
            with self.assertRaises(OSError):
                global_skills.install(str(source), providers=["claude", "codex"], replace=True)
        self.assertIn("old claude", (self.claude_root / "alpha" / "SKILL.md").read_text(encoding="utf-8"))
        self.assertIn("old agents", (self.agents_root / "alpha" / "SKILL.md").read_text(encoding="utf-8"))
        self.assertEqual(self._stages(), [])

    def test_a_stale_stage_is_swept_into_quarantine(self):
        stale = self.claude_root / ".devteam-staging-alpha-abc123"
        write_skill(stale, "alpha")
        source = write_skill(self.tmp / "src" / "beta", "beta")
        self.cli_json("install", "--source", str(source), "--provider", "claude")
        self.assertFalse(stale.exists())
        self.assertTrue(any(p.name == stale.name for p in self.home.rglob(".devteam-staging-*")))


@unittest.skipUnless(os.name == "posix", "symlinks need privileges on Windows")
class LinkAndManagedTest(GlobalSkillsTestCase):
    def test_link_onto_itself_is_refused(self):
        write_skill(self.claude_root / "alpha", "alpha")
        self.cli_json(
            "install", "--source", str(self.claude_root / "alpha"), "--provider", "claude",
            "--link", "--replace", expect=errors.EXIT_USAGE,
        )
        self.assertTrue((self.claude_root / "alpha" / "SKILL.md").is_file())
        self.assertFalse((self.claude_root / "alpha").is_symlink())

    def test_link_from_the_core_store_is_refused(self):
        self.install_version("3.0.0", activate=True)
        from devteam import paths

        core_skill = paths.core_dir() / "versions" / "3.0.0" / "skills" / "testing" / "unit"
        self.cli_json(
            "install", "--source", str(core_skill), "--provider", "claude", "--link",
            expect=errors.EXIT_USAGE,
        )

    def test_a_root_symlinked_into_the_core_makes_its_children_managed(self):
        self.install_version("3.0.0", activate=True)
        from devteam import paths

        core_skills = paths.core_dir() / "versions" / "3.0.0" / "skills" / "testing"
        (self.user_home / ".claude").mkdir(parents=True)
        os.symlink(str(core_skills), str(self.claude_root))
        entry = self.cli_json("list", "--provider", "claude")["skills"][0]
        self.assertFalse(entry["is_symlink"])
        self.assertTrue(entry["managed"])
        body = self.cli_json("remove", "unit", "--root", "claude", expect=errors.EXIT_CONFLICT)
        self.assertEqual(body["details"]["reason"], "managed")
        self.assertTrue((core_skills / "unit" / "SKILL.md").is_file())

    def test_conflict_reasons_are_distinct(self):
        write_skill(self.claude_root / "alpha", "alpha")
        source = write_skill(self.tmp / "src" / "alpha", "alpha")
        body = self.cli_json("install", "--source", str(source), "--provider", "claude", expect=errors.EXIT_CONFLICT)
        self.assertEqual(body["details"]["reason"], "exists")

    def test_remove_reports_where_a_symlink_pointed(self):
        target = write_skill(self.tmp / "elsewhere" / "alpha", "alpha")
        self.claude_root.mkdir(parents=True)
        os.symlink(str(target), str(self.claude_root / "alpha"))
        payload = self.cli_json("remove", "alpha")
        self.assertEqual(payload["link_target"], str(target))


class ArchiveEdgeTest(GlobalSkillsTestCase):
    def _zip(self, name, members):
        archive = self.tmp / name
        with zipfile.ZipFile(str(archive), "w") as bundle:
            for member in members:
                if isinstance(member, tuple):
                    bundle.writestr(*member)
                else:
                    bundle.writestr(member, "x")
        return archive

    SKILL = ("SKILL.md", "---\nname: zipped\ndescription: x\n---\n")

    def test_backslash_and_drive_letter_members_are_refused(self):
        for bad in ("..\\escape.txt", "C:/evil.txt", "C:\\evil.txt"):
            with self.subTest(member=bad):
                archive = self._zip("bad.zip", [self.SKILL, bad])
                self.cli_json("install", "--source", str(archive), expect=errors.EXIT_USAGE)

    def test_limits_are_enforced(self):
        from unittest import mock
        from devteam import global_skills
        from devteam.errors import UsageError

        archive = self._zip("big.zip", [self.SKILL, ("blob.bin", "y" * 4096), "a", "b"])
        with mock.patch.object(global_skills, "MAX_ARCHIVE_BYTES", 1024):
            with self.assertRaisesRegex(UsageError, "expands"):
                global_skills.install(str(archive), providers=["claude"])
        with mock.patch.object(global_skills, "MAX_ARCHIVE_MEMBERS", 2):
            with self.assertRaisesRegex(UsageError, "entries"):
                global_skills.install(str(archive), providers=["claude"])

    def test_encrypted_member_is_refused(self):
        archive = self._zip("enc.zip", [self.SKILL])
        data = bytearray(archive.read_bytes())
        # Set the "encrypted" general-purpose flag bit in the central directory entry.
        index = data.rfind(b"PK\x01\x02")
        self.assertGreaterEqual(index, 0)
        data[index + 8] |= 0x1
        archive.write_bytes(bytes(data))
        self.cli_json("install", "--source", str(archive), expect=errors.EXIT_USAGE)

    def test_macosx_debris_is_not_installed(self):
        archive = self._zip("mac.zip", [("zipped/SKILL.md", self.SKILL[1]), "__MACOSX/zipped/._SKILL.md"])
        self.cli_json("install", "--source", str(archive), "--provider", "claude")
        self.assertFalse((self.claude_root / "zipped" / "__MACOSX").exists())
        self.assertFalse((self.user_home / ".claude" / "__MACOSX").exists())

    @unittest.skipUnless(os.name == "posix", "no POSIX permission bits on this filesystem")
    def test_executable_bit_survives_extraction(self):
        archive = self.tmp / "exec.zip"
        with zipfile.ZipFile(str(archive), "w") as bundle:
            bundle.writestr(*self.SKILL)
            info = zipfile.ZipInfo("scripts/run.sh")
            info.external_attr = (stat.S_IFREG | 0o4755) << 16
            bundle.writestr(info, "#!/bin/sh\n")
        self.cli_json("install", "--source", str(archive), "--provider", "claude")
        mode = stat.S_IMODE((self.claude_root / "zipped" / "scripts" / "run.sh").stat().st_mode)
        self.assertTrue(mode & 0o100, oct(mode))
        self.assertFalse(mode & 0o4000, "setuid must never survive")


class FrontmatterTest(unittest.TestCase):
    def test_inline_comment_is_not_part_of_the_value(self):
        from devteam.global_skills import read_frontmatter

        fields, _ = read_frontmatter("---\nname: foo # the name\ndescription: 'a # b'\n---\n")
        self.assertEqual(fields["name"], "foo")
        self.assertEqual(fields["description"], "a # b")

    def test_indented_dashes_inside_a_block_do_not_close_the_frontmatter(self):
        from devteam.global_skills import read_frontmatter

        fields, body = read_frontmatter("---\nname: foo\ndescription: |\n  line\n  ---\n  more\n---\nBody\n")
        self.assertEqual(fields["description"], "line\n---\nmore")
        self.assertEqual(body, "Body")


class ClassificationTest(unittest.TestCase):
    def test_reads_are_read_only_and_writes_are_gated(self):
        self.assertEqual(compat.classify(("skills", "list")), "read-only")
        self.assertEqual(compat.classify(("skills", "show")), "read-only")
        self.assertEqual(compat.classify(("skills", "install")), "mutating")
        self.assertEqual(compat.classify(("skills", "remove")), "mutating")


if __name__ == "__main__":
    unittest.main()
