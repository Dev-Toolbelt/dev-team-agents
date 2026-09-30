"""`devteam skills` — the providers' user-level skill directories (ADR-0017).

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
    def test_install_directory_into_each_providers_target_root(self):
        source = write_skill(self.tmp / "src" / "alpha", "alpha")
        payload = self.cli_json("install", "--source", str(source))
        roots = sorted(item["root"] for item in payload["installed"])
        self.assertEqual(roots, ["agents", "claude", "opencode"])
        for root in (self.claude_root, self.agents_root, self.opencode_root):
            self.assertTrue((root / "alpha" / "SKILL.md").is_file())
        self.assertFalse((self.codex_root / "alpha").exists(), "nothing new goes to ~/.codex/skills")
        self.assertTrue(source.is_dir(), "the source is copied, never moved")

    def test_install_one_provider(self):
        source = write_skill(self.tmp / "src" / "alpha", "alpha")
        payload = self.cli_json("install", "--source", str(source), "--provider", "claude")
        self.assertEqual([item["root"] for item in payload["installed"]], ["claude"])

    def test_install_uses_frontmatter_name_not_folder_name(self):
        source = write_skill(self.tmp / "src" / "some-folder", "real-name")
        self.cli_json("install", "--source", str(source), "--provider", "claude")
        self.assertTrue((self.claude_root / "real-name").is_dir())

    def test_conflict_refused_before_any_root_is_written(self):
        write_skill(self.opencode_root / "alpha", "alpha", description="old")
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


class ClassificationTest(unittest.TestCase):
    def test_reads_are_read_only_and_writes_are_gated(self):
        self.assertEqual(compat.classify(("skills", "list")), "read-only")
        self.assertEqual(compat.classify(("skills", "show")), "read-only")
        self.assertEqual(compat.classify(("skills", "install")), "mutating")
        self.assertEqual(compat.classify(("skills", "remove")), "mutating")


if __name__ == "__main__":
    unittest.main()
