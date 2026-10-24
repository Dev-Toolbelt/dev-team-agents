"""The docs write root every script resolves: scripts/lib/docs_root.py and docs-root.sh."""

import json
import shutil
import subprocess
import sys
import unittest

from devteam_support import REPO_ROOT, StoreTestCase, requires_bash

import docs_root

PROJECT_ID = "8f14e45f-ea0c-4c2b-9c1f-2b1f9a7d3e10"
HELPER = REPO_ROOT / "scripts" / "lib" / "docs-root.sh"
RESOLVER = REPO_ROOT / "scripts" / "lib" / "docs_root.py"
SHIM = REPO_ROOT / "scripts" / "doc-path.sh"


class DocsRootTest(StoreTestCase):
    def project(self, context_paths, **extra):
        root = self.tmp / "app"
        (root / ".dev-team-agents").mkdir(parents=True, exist_ok=True)
        data = dict({"schema": 1, "project_id": PROJECT_ID, "context_paths": context_paths}, **extra)
        (root / ".dev-team-agents" / "project.json").write_text(json.dumps(data), encoding="utf-8")
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


class DocLayoutTest(StoreTestCase):
    def project(self, docs_layout=None, context_paths=("docs",)):
        root = self.tmp / "app"
        (root / ".dev-team-agents").mkdir(parents=True, exist_ok=True)
        data = {"schema": 1, "project_id": PROJECT_ID, "context_paths": list(context_paths)}
        if docs_layout is not None:
            data["docs_layout"] = docs_layout
        (root / ".dev-team-agents" / "project.json").write_text(json.dumps(data), encoding="utf-8")
        return root

    def test_an_absent_key_or_file_is_the_development_layout(self):
        self.assertEqual(docs_root.layout(self.project()), "development")
        (self.tmp / "bare").mkdir()
        self.assertEqual(docs_root.layout(self.tmp / "bare"), "development")

    def test_a_bad_layout_means_development_but_keeps_the_write_root(self):
        # A mistyped docs_layout must not silently drop context_paths[0].
        for paths in (("handbook",), ("mydocs",)):
            with self.subTest(paths=paths):
                root = self.project("gatd", context_paths=paths)
                self.assertEqual(docs_root.layout(root), "development")
                self.assertEqual(docs_root.write_root(root), paths[0])
                self.assertEqual(docs_root.doc_path(root, "adr"), paths[0] + "/development/adrs/")

    def test_a_bad_layout_never_lets_an_invalid_context_path_through(self):
        for paths in (["../out"], ["/etc"], []):
            with self.subTest(paths=paths):
                self.assertEqual(docs_root.write_root(self.project("gatd", context_paths=paths)), "docs")

    def test_the_development_layout_keeps_todays_paths(self):
        root = self.project()
        self.assertEqual(docs_root.doc_path(root, "adr"), "docs/development/adrs/")
        self.assertEqual(docs_root.doc_path(root, "data-model"), "docs/development/database.md")
        self.assertEqual(docs_root.doc_path(root, "prd"), "")
        self.assertEqual(docs_root.readonly_paths(root), [])

    def test_the_gated_layout_resolves_under_the_write_root(self):
        root = self.project("gated", context_paths=(".claude/docs", "docs"))
        self.assertEqual(docs_root.layout(root), "gated")
        self.assertEqual(docs_root.doc_path(root, "adr"), ".claude/docs/adr/")
        self.assertEqual(docs_root.doc_path(root, "prd"), ".claude/docs/prd.md")
        self.assertEqual(docs_root.doc_path(root, "backlog-readme"), "")
        self.assertEqual(docs_root.readonly_paths(root), [".claude/docs/source/", ".claude/docs/design/prototypes/"])

    def test_an_unknown_key_raises(self):
        with self.assertRaises(KeyError):
            docs_root.doc_path(self.project(), "nope")

    def run_cli(self, *args):
        result = subprocess.run([sys.executable, "-I", str(RESOLVER), *args],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return result.returncode, result.stdout.decode()

    def test_the_cli_answers_every_question(self):
        root = str(self.project("gated", context_paths=("handbook",)))
        self.assertEqual(self.run_cli(root), (0, "handbook\n"))
        self.assertEqual(self.run_cli("--layout", root), (0, "gated\n"))
        self.assertEqual(self.run_cli("--path", "nfr", root), (0, "handbook/nfr.md\n"))
        self.assertEqual(self.run_cli("--path", "backlog-readme", root), (0, "\n"))
        self.assertEqual(self.run_cli("--readonly", root), (0, "handbook/source/\nhandbook/design/prototypes/\n"))
        code, out = self.run_cli("--writable", root)
        self.assertEqual(code, 0)
        self.assertIn("handbook/glossary.md", out.splitlines())
        self.assertFalse(any(line.endswith(("source/", "prototypes/")) for line in out.splitlines()))
        self.assertEqual(self.run_cli("--path", "nope", root)[0], 2)
        self.assertEqual(self.run_cli("--path")[0], 2)
        self.assertEqual(self.run_cli("--bogus", root)[0], 2)


@requires_bash()
class DocPathShimTest(StoreTestCase):
    def shim(self, root, *args):
        result = subprocess.run(["bash", str(SHIM), *args], cwd=str(root), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return result.returncode, result.stdout.decode()

    def test_the_shim_resolves_from_the_project_root(self):
        root = self.tmp / "app"
        (root / ".dev-team-agents").mkdir(parents=True)
        (root / ".dev-team-agents" / "project.json").write_text(json.dumps(
            {"schema": 1, "project_id": PROJECT_ID, "context_paths": ["docs"], "docs_layout": "gated"}))
        self.assertEqual(self.shim(root, "data-model"), (0, "docs/data-model.md\n"))
        self.assertEqual(self.shim(root, "--layout"), (0, "gated\n"))
        self.assertEqual(self.shim(root, "--readonly"), (0, "docs/source/\ndocs/design/prototypes/\n"))
        writable = self.shim(root, "--writable")[1].splitlines()
        self.assertIn("docs/prd.md", writable)
        self.assertIn("docs/data-model.md", writable)
        self.assertNotIn("docs/source/", writable)
        self.assertNotIn("docs/design/prototypes/", writable)
        self.assertEqual(len(writable), len(set(writable)))
        self.assertEqual(self.shim(root, "nope")[0], 2)
        self.assertEqual(self.shim(root)[0], 2)
        self.assertEqual(self.shim(root, "--bogus")[0], 2)

    def test_without_project_json_the_shim_answers_the_development_layout(self):
        (self.tmp / "bare").mkdir()
        self.assertEqual(self.shim(self.tmp / "bare", "adr"), (0, "docs/development/adrs/\n"))
        self.assertEqual(self.shim(self.tmp / "bare", "--layout"), (0, "development\n"))


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

    def test_without_the_map_the_fallback_path_stays_under_the_write_root(self):
        lib = self.tmp / "lib"
        shutil.copytree(str(HELPER.parent), str(lib), ignore=shutil.ignore_patterns("__pycache__"))
        (lib / "doc-layouts.json").unlink()
        root = self.tmp / "app"
        (root / ".dev-team-agents").mkdir(parents=True)
        (root / ".dev-team-agents" / "project.json").write_text(
            json.dumps({"schema": 1, "project_id": PROJECT_ID, "context_paths": ["handbook"]}), encoding="utf-8")
        result = subprocess.run(["bash", "-c", '. "$1"; devteam_doc_path "$PWD" adr', "_", str(lib / "docs-root.sh")],
                                cwd=str(root), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual(result.stdout.decode(), "handbook/development/adrs/\n")

    def test_without_project_json_the_shell_helper_answers_docs_without_python(self):
        (self.tmp / "y").mkdir()
        self.assertEqual(self.run_helper('PATH=/nonexistent devteam_docs_root "$PWD"', self.tmp / "y"), "docs")


if __name__ == "__main__":
    unittest.main()
