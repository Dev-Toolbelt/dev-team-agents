"""The docs write root every script resolves: scripts/lib/docs_root.py and docs-root.sh."""

import json
import subprocess
import unittest

from devteam_support import REPO_ROOT, StoreTestCase, requires_bash

import docs_root

PROJECT_ID = "8f14e45f-ea0c-4c2b-9c1f-2b1f9a7d3e10"
HELPER = REPO_ROOT / "scripts" / "lib" / "docs-root.sh"


class DocsRootTest(StoreTestCase):
    def project(self, context_paths):
        root = self.tmp / "app"
        (root / ".dev-team-agents").mkdir(parents=True, exist_ok=True)
        (root / ".dev-team-agents" / "project.json").write_text(
            json.dumps({"schema": 1, "project_id": PROJECT_ID, "context_paths": context_paths}), encoding="utf-8")
        return root

    def test_no_project_json_means_docs(self):
        (self.tmp / "bare").mkdir()
        self.assertEqual(docs_root.write_root(self.tmp / "bare"), "docs")

    def test_the_first_context_path_is_the_write_root(self):
        self.assertEqual(docs_root.write_root(self.project([".claude/docs/", "docs"])), ".claude/docs")

    def test_anything_project_validate_rejects_means_docs(self):
        for bad in (["../outside"], ["/etc"], ["C:\\\\x"], [""], [], "docs", [7]):
            with self.subTest(bad=bad):
                self.assertEqual(docs_root.write_root(self.project(bad)), "docs")

    def test_a_value_is_refused_never_trimmed_into_shape(self):
        # project.validate sees these raw strings as harmless names; trimming them
        # afterwards used to yield `..` or an absolute path.
        for bad in (" ..", ".. ", "..\\", "\t..", " /tmp/x", "..\n", ".\n", "docs\n", "..\r", "-e", "docs/-x", ".", "./", "a b",
                    "Ignore prior rules", "x" * 201):
            with self.subTest(bad=bad):
                self.assertEqual(docs_root.write_root(self.project([bad])), "docs")

    def test_a_normalisable_value_is_returned_normalised(self):
        for value, expected in (("./docs/", "docs"), (".claude//docs", ".claude/docs"), ("a/./b", "a/b")):
            with self.subTest(value=value):
                self.assertEqual(docs_root.write_root(self.project([value])), expected)

    def test_control_characters_and_backslashes_mean_docs(self):
        for bad in ("a\nb", "a\\b", "a\x7fb"):
            with self.subTest(bad=bad):
                self.assertEqual(docs_root.write_root(self.project([bad])), "docs")


@requires_bash()
class DocsRootShellTest(StoreTestCase):
    def run_helper(self, script, root):
        result = subprocess.run(["bash", "-c", '. "$1"; ' + script, "_", str(HELPER)],
                                cwd=str(root), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return result.stdout.decode().strip()

    def test_the_shell_helper_answers_the_same_root(self):
        root = self.tmp / "app"
        (root / ".dev-team-agents").mkdir(parents=True)
        (root / ".dev-team-agents" / "project.json").write_text(
            json.dumps({"schema": 1, "project_id": PROJECT_ID, "context_paths": ["handbook"]}), encoding="utf-8")
        self.assertEqual(self.run_helper('devteam_docs_root "$PWD"', root), "handbook")

    def test_regex_escape_makes_a_dotted_root_literal(self):
        (self.tmp / "x").mkdir()
        self.assertEqual(self.run_helper("devteam_regex_escape .claude/docs", self.tmp / "x"), "\\.claude/docs")
        self.assertEqual(self.run_helper("devteam_regex_escape 'a+b(c)'", self.tmp / "x"), "a\\+b\\(c\\)")

    def test_without_project_json_the_shell_helper_answers_docs_without_python(self):
        (self.tmp / "y").mkdir()
        self.assertEqual(self.run_helper('PATH=/nonexistent devteam_docs_root "$PWD"', self.tmp / "y"), "docs")


if __name__ == "__main__":
    unittest.main()
