"""`scripts/hooks/pre-tool-use/05-readonly-docs-guard.sh` — read-only raw inputs, every provider.

In a project whose project.json says `"docs_layout": "gated"`, the folders doc-layouts.json
flags `readonly` (under the docs write root) refuse an edit, overwrite or delete of an existing
file and accept a new one. The development layout, a non-edit tool and a path elsewhere are
never refused. Each provider's edit tool is replayed in the shape its hook (or, for opencode,
its plugin) sends.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from devteam_support import REPO_ROOT, requires_bash
from devteam.providers import ALL_PROVIDERS

GUARD = REPO_ROOT / "scripts" / "hooks" / "pre-tool-use" / "05-readonly-docs-guard.sh"
DISPATCHER = REPO_ROOT / "scripts" / "hooks" / "pre-tool-use.sh"
PROJECT_ID = "8f14e45f-ea0c-4c2b-9c1f-2b1f9a7d3e10"


def _patch(header, path):
    body = "+x\n" if header == "Add" else "@@\n-a\n+b\n" if header == "Update" else ""
    return "*** Begin Patch\n*** {} File: {}\n{}*** End Patch\n".format(header, path, body)


def claude_edit(path):
    return {"session_id": "s", "tool_name": "Edit", "tool_input": {"file_path": path, "old_string": "a", "new_string": "b"}}


def claude_write(path):
    return {"session_id": "s", "tool_name": "Write", "tool_input": {"file_path": path, "content": "x"}}


def claude_delete(path):
    return None  # Claude Code has no file-delete tool; a delete is a Bash `rm`, out of scope.


def opencode_edit(path):
    args = {"filePath": path, "oldString": "a", "newString": "b"}
    return {"sessionID": "s", "tool": "edit", "tool_name": "Edit", "tool_input": args, "args": args}


def opencode_write(path):
    args = {"filePath": path, "content": "x"}
    return {"sessionID": "s", "tool": "write", "tool_name": "Write", "tool_input": args, "args": args}


def opencode_delete(path):
    return {"sessionID": "s", "tool": "patch", "args": {"patchText": _patch("Delete", path)}}


def codex_edit(path):
    return {"session_id": "s", "turn_id": "t", "tool_name": "apply_patch", "tool_input": {"input": _patch("Update", path)}}


def codex_write(path):
    return {"session_id": "s", "turn_id": "t", "tool_name": "apply_patch", "tool_input": {"input": _patch("Add", path)}}


def codex_delete(path):
    return {"session_id": "s", "turn_id": "t", "tool_name": "apply_patch", "tool_input": {"input": _patch("Delete", path)}}


#: (edit existing, create/overwrite, delete) per provider in ALL_PROVIDERS — a provider added
#: without a case fails test_every_provider_has_a_fixture.
CALLS = {
    "claude": (claude_edit, claude_write, claude_delete),
    "opencode": (opencode_edit, opencode_write, opencode_delete),
    "codex": (codex_edit, codex_write, codex_delete),
}

#: A read per provider: never refused, whatever it names.
READS = {
    "claude": lambda p: {"session_id": "s", "tool_name": "Read", "tool_input": {"file_path": p}},
    "opencode": lambda p: {"sessionID": "s", "tool": "read", "tool_name": "Read", "tool_input": {"filePath": p},
                           "args": {"filePath": p}},
    "codex": lambda p: {"session_id": "s", "tool_name": "Bash", "tool_input": {"command": "cat " + p}},
}


@requires_bash()
class ReadonlyDocsGuardTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, True)
        self.layout("gated")
        (self.root / "docs" / "source").mkdir(parents=True)
        (self.root / "docs" / "design" / "prototypes" / "2026-10-01-login").mkdir(parents=True)
        (self.root / "docs" / "source" / "kickoff.md").write_text("raw\n", encoding="utf-8")
        (self.root / "docs" / "design" / "prototypes" / "2026-10-01-login" / "index.html").write_text("x", encoding="utf-8")
        (self.root / "docs" / "prd.md").write_text("prd\n", encoding="utf-8")

    def layout(self, value, context_paths=None):
        data = {"schema": 1, "project_id": PROJECT_ID, "context_paths": context_paths or ["docs"]}
        if value is not None:
            data["docs_layout"] = value
        (self.root / ".dev-team-agents").mkdir(exist_ok=True)
        (self.root / ".dev-team-agents" / "project.json").write_text(json.dumps(data), encoding="utf-8")

    def run_guard(self, payload, script=GUARD):
        env = {k: v for k, v in os.environ.items() if k != "CLAUDE_PROJECT_DIR"}
        return subprocess.run(["bash", str(script)], input=json.dumps(payload), capture_output=True, text=True,
                              cwd=self.root, env=env)

    def assertRefused(self, payload, folder="docs/source/"):
        result = self.run_guard(payload)
        self.assertEqual(result.returncode, 2, "expected a refusal: {} {}".format(payload, result.stderr))
        self.assertIn(folder, result.stderr)
        self.assertIn("skills/shared/doc-flow/SKILL.md § Read-only Inputs", result.stderr)
        self.assertIn("derive a working doc that cites it instead", result.stderr)

    def assertAllowed(self, payload):
        result = self.run_guard(payload)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")

    def each(self, index):
        return [(provider, CALLS[provider][index]) for provider in ALL_PROVIDERS]

    def test_every_provider_has_a_fixture(self):
        self.assertEqual(set(CALLS), set(ALL_PROVIDERS))
        self.assertEqual(set(READS), set(ALL_PROVIDERS))

    def test_editing_an_existing_raw_input_is_refused(self):
        for _, make in self.each(0):
            self.assertRefused(make("docs/source/kickoff.md"))
            self.assertRefused(make(str(self.root / "docs" / "source" / "kickoff.md")))
            self.assertRefused(make("docs/design/prototypes/2026-10-01-login/index.html"), "docs/design/prototypes/")

    def test_overwriting_an_existing_raw_input_is_refused(self):
        for _, make in self.each(1):
            self.assertRefused(make("docs/source/kickoff.md"))

    def test_deleting_an_existing_raw_input_is_refused(self):
        for _, make in self.each(2):
            payload = make("docs/source/kickoff.md")
            if payload is not None:
                self.assertRefused(payload)

    def test_creating_a_new_raw_input_is_allowed(self):
        for _, make in self.each(1):
            self.assertAllowed(make("docs/source/2026-10-23-meeting.md"))
            self.assertAllowed(make("docs/design/prototypes/2026-10-23-signup/index.html"))

    def test_a_path_outside_the_readonly_folders_is_allowed(self):
        for index in range(3):
            for _, make in self.each(index):
                payload = make("docs/prd.md")
                if payload is not None:
                    self.assertAllowed(payload)

    def test_a_dotdot_path_is_normalized(self):
        for _, make in self.each(0):
            self.assertRefused(make("docs/prd/../source/kickoff.md"))
            self.assertAllowed(make("docs/source/../prd.md"))

    def test_a_symlink_inside_a_readonly_folder_is_refused(self):
        (self.root / "elsewhere").mkdir()
        os.symlink(self.root / "elsewhere", self.root / "docs" / "source" / "linked")
        for _, make in self.each(1):
            self.assertRefused(make("docs/source/linked/new.md"))

    def test_the_development_layout_never_refuses(self):
        for value in (None, "development"):
            self.layout(value)
            for _, make in self.each(0):
                self.assertAllowed(make("docs/source/kickoff.md"))

    def test_a_non_edit_tool_is_allowed(self):
        for provider in ALL_PROVIDERS:
            with self.subTest(provider=provider):
                self.assertAllowed(READS[provider]("docs/source/kickoff.md"))

    def test_the_readonly_folders_follow_the_docs_write_root(self):
        self.layout("gated", [".claude/docs"])
        (self.root / ".claude" / "docs" / "source").mkdir(parents=True)
        (self.root / ".claude" / "docs" / "source" / "kickoff.md").write_text("raw\n", encoding="utf-8")
        for _, make in self.each(0):
            self.assertRefused(make(".claude/docs/source/kickoff.md"), ".claude/docs/source/")
            self.assertAllowed(make("docs/source/kickoff.md"))

    def test_a_codex_move_onto_an_existing_raw_input_is_refused(self):
        patch = "*** Begin Patch\n*** Update File: docs/prd.md\n*** Move to: docs/source/kickoff.md\n@@\n-a\n+b\n*** End Patch\n"
        self.assertRefused({"tool_name": "apply_patch", "tool_input": {"input": patch}})

    def test_a_claude_notebook_edit_is_covered(self):
        (self.root / "docs" / "source" / "n.ipynb").write_text("{}", encoding="utf-8")
        self.assertRefused({"tool_name": "NotebookEdit", "tool_input": {"notebook_path": "docs/source/n.ipynb"}})

    def test_the_dispatcher_propagates_the_refusal(self):
        result = self.run_guard(claude_edit("docs/source/kickoff.md"), DISPATCHER)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("readonly-docs-guard", result.stderr)

    def worktree(self, where, value="gated"):
        """A worktree checkout at ``where`` carrying its own committed project.json."""
        (where / ".dev-team-agents").mkdir(parents=True)
        data = {"schema": 1, "project_id": PROJECT_ID, "context_paths": ["docs"], "docs_layout": value}
        (where / ".dev-team-agents" / "project.json").write_text(json.dumps(data), encoding="utf-8")
        (where / "docs" / "source").mkdir(parents=True)
        (where / "docs" / "source" / "kickoff.md").write_text("raw\n", encoding="utf-8")
        return where

    def test_a_worktree_inside_the_project_is_judged_by_its_own_project_json(self):
        wt = self.worktree(self.root / ".worktrees" / "feat" / "login")
        for _, make in self.each(0):
            self.assertRefused(make(".worktrees/feat/login/docs/source/kickoff.md"))
            self.assertRefused(make(str(wt / "docs" / "source" / "kickoff.md")))
        for _, make in self.each(1):
            self.assertAllowed(make(".worktrees/feat/login/docs/source/new.md"))

    def test_a_worktree_outside_the_project_is_covered(self):
        sibling = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, sibling, True)
        wt = self.worktree(sibling / "feat" / "login")
        self.layout("development")  # the session's own project would let everything through
        for _, make in self.each(0):
            self.assertRefused(make(str(wt / "docs" / "source" / "kickoff.md")))
            self.assertAllowed(make("docs/source/kickoff.md"))

    def test_a_development_worktree_of_a_gated_project_is_not_refused(self):
        self.worktree(self.root / ".worktrees" / "feat" / "old", "development")
        for _, make in self.each(0):
            self.assertAllowed(make(".worktrees/feat/old/docs/source/kickoff.md"))

    def test_a_symlink_outside_pointing_into_a_readonly_folder_is_refused(self):
        os.symlink(self.root / "docs" / "source", self.root / "docs" / "notes")
        os.symlink(self.root / "docs" / "source" / "kickoff.md", self.root / "docs" / "kick.md")
        for _, make in self.each(0):
            self.assertRefused(make("docs/notes/kickoff.md"))
            self.assertRefused(make("docs/kick.md"))
        for _, make in self.each(1):
            self.assertAllowed(make("docs/notes/brand-new.md"))

    def test_a_symlink_in_another_project_pointing_into_a_gated_readonly_folder_is_refused(self):
        other = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, other, True)
        (other / ".dev-team-agents").mkdir()
        (other / ".dev-team-agents" / "project.json").write_text(json.dumps(
            {"schema": 1, "project_id": PROJECT_ID, "context_paths": ["docs"], "docs_layout": "development"}), encoding="utf-8")
        (other / "docs").mkdir()
        os.symlink(self.root / "docs" / "source" / "kickoff.md", other / "docs" / "kick.md")
        env = {k: v for k, v in os.environ.items() if k != "CLAUDE_PROJECT_DIR"}
        for provider, make in self.each(0):
            with self.subTest(provider=provider):
                result = subprocess.run(["bash", str(GUARD)], input=json.dumps(make(str(other / "docs" / "kick.md"))),
                                        capture_output=True, text=True, cwd=other, env=env)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertIn("docs/source/", result.stderr)

    def test_a_case_variant_on_a_case_insensitive_filesystem_is_refused(self):
        if not (self.root / "DOCS" / "SOURCE" / "KICKOFF.MD").exists():
            self.skipTest("filesystem is case-sensitive")
        if sys.platform not in ("darwin", "win32"):
            self.skipTest("case folding applies on darwin and win32 only")
        for _, make in self.each(0):
            self.assertRefused(make("docs/Source/kickoff.md"))
            self.assertRefused(make("Docs/SOURCE/Kickoff.md"))
        for _, make in self.each(1):
            self.assertAllowed(make("docs/Source/brand-new.md"))

    def test_a_malformed_payload_is_allowed(self):
        result = subprocess.run(["bash", str(GUARD)], input='{"tool_name":"Edit", nope', capture_output=True,
                                text=True, cwd=self.root)
        self.assertEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
