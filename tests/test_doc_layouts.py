"""The docs layout map, scripts/lib/doc-layouts.json, and project.json `docs_layout` (ADR-0045).

The map is the one answer to where a fact category's document lives per layout; these tests
keep it well-formed and keep its two mirrors — the layout names in project.py and the
development column in lib/docs-root.sh — from drifting.
"""

import json
import os
import re
import shutil
import subprocess
import unittest

from devteam_support import REPO_ROOT, StoreTestCase, requires_bash

from devteam import project, shells
from devteam.errors import EnvError

MAP_FILE = REPO_ROOT / "scripts" / "lib" / "doc-layouts.json"
SHELL_LIB = REPO_ROOT / "scripts" / "lib" / "docs-root.sh"
SHIM = REPO_ROOT / "scripts" / "doc-path.sh"
PROJECT_ID = "8f14e45f-ea0c-4c2b-9c1f-2b1f9a7d3e10"
FIELDS = {"owns", "owner", "readonly"}


def layout_map():
    return json.loads(MAP_FILE.read_text(encoding="utf-8"))


class DocLayoutsSchemaTest(unittest.TestCase):
    def setUp(self):
        self.data = layout_map()
        self.layouts = self.data["layouts"]

    def test_the_default_and_new_project_layouts_are_declared_layouts(self):
        self.assertEqual(self.data["default_layout"], "development")
        self.assertIn(self.data["new_project_layout"], self.layouts)
        self.assertEqual(len(set(self.layouts)), len(self.layouts))

    def test_every_key_has_its_fields_and_a_column_per_layout(self):
        for key, entry in self.data["docs"].items():
            with self.subTest(key=key):
                self.assertEqual(set(entry), FIELDS | set(self.layouts))
                self.assertIsInstance(entry["owns"], str)
                self.assertTrue(entry["owns"].strip())
                self.assertIsInstance(entry["readonly"], bool)
                self.assertTrue(any(entry[layout] for layout in self.layouts), "a key no layout has")

    def test_every_path_is_a_plain_relative_path(self):
        for key, entry in self.data["docs"].items():
            for layout in self.layouts:
                value = entry[layout]
                if value is None:
                    continue
                with self.subTest(key=key, layout=layout):
                    self.assertIsInstance(value, str)
                    self.assertFalse(value.startswith("/"))
                    self.assertNotIn("..", value.split("/"))
                    self.assertRegex(value, r"^[A-Za-z0-9._/-]+$")

    def test_every_owner_is_a_real_agent(self):
        agents = {path.stem for path in (REPO_ROOT / "agents").glob("*.md")}
        for key, entry in self.data["docs"].items():
            with self.subTest(key=key):
                self.assertIn(entry["owner"], agents)

    def test_read_only_paths_exist_in_the_gated_layout_only(self):
        readonly = {k: e for k, e in self.data["docs"].items() if e["readonly"]}
        self.assertTrue(readonly)
        for key, entry in readonly.items():
            with self.subTest(key=key):
                self.assertTrue(entry["gated"])
                self.assertIsNone(entry["development"])

    def test_no_writable_path_contains_or_sits_inside_a_read_only_one(self):
        # The embedded learn pass stages paths under `doc-path.sh --writable`; a writable `design/`
        # would quietly widen that to `design/prototypes/`.
        for layout in self.layouts:
            entries = [e for e in self.data["docs"].values() if e.get(layout)]
            readonly = [e[layout].rstrip("/") + "/" for e in entries if e["readonly"]]
            writable = [e[layout].rstrip("/") + "/" for e in entries if not e["readonly"]]
            for ro in readonly:
                for rw in writable:
                    with self.subTest(layout=layout, readonly=ro, writable=rw):
                        self.assertFalse(ro.startswith(rw) or rw.startswith(ro))

    def test_the_layout_names_project_py_falls_back_to_match_the_map(self):
        self.assertEqual(tuple(self.layouts), project._FALLBACK_DOCS_LAYOUTS)
        self.assertEqual(project.docs_layouts(), tuple(self.layouts))
        self.assertEqual(project.DEFAULT_DOCS_LAYOUT, self.data["default_layout"])


class DocsLayoutKeyTest(StoreTestCase):
    def project(self, **extra):
        root = self.tmp / "app"
        (root / ".dev-team-agents").mkdir(parents=True, exist_ok=True)
        data = dict({"schema": 1, "project_id": PROJECT_ID, "context_paths": ["docs"]}, **extra)
        (root / ".dev-team-agents" / "project.json").write_text(json.dumps(data), encoding="utf-8")
        return root

    def test_an_absent_key_means_development(self):
        self.assertEqual(project.docs_layout(self.project()), "development")
        (self.tmp / "bare").mkdir()
        self.assertEqual(project.docs_layout(self.tmp / "bare"), "development")

    def test_every_declared_layout_is_accepted(self):
        for layout in layout_map()["layouts"]:
            with self.subTest(layout=layout):
                self.assertEqual(project.docs_layout(self.project(docs_layout=layout)), layout)

    def test_a_bad_value_is_rejected(self):
        for bad in ("Gated", "", "legacy", 2, None, True, ["gated"]):
            with self.subTest(bad=bad):
                root = self.project(docs_layout=bad)
                with self.assertRaises(EnvError):
                    project.load(root)


SPEC_LINT_HOOK = REPO_ROOT / "scripts" / "hooks" / "stop" / "03f-spec-lint.sh"
#: The keys whose docs the spec lint reads; the hook's trigger must match each of their paths.
SPEC_LAYER_KEYS = ("specs", "sprints", "backlog-index", "design-flows", "design-screens", "evals")


class SpecLintTriggerDriftTest(unittest.TestCase):
    def test_the_hook_trigger_matches_every_spec_layer_path_of_every_layout(self):
        text = SPEC_LINT_HOOK.read_text(encoding="utf-8")
        found = re.search(r"^SPEC_LAYER_RE='([^']+)'$", text, re.M)
        self.assertIsNotNone(found, "03f-spec-lint.sh no longer defines SPEC_LAYER_RE")
        # ERE and Python agree on this subset (groups, alternation, `\.`, `$`).
        trigger = re.compile("(^|/)docs/" + found.group(1))
        docs = layout_map()["docs"]
        for key in SPEC_LAYER_KEYS:
            for name in layout_map()["layouts"]:
                rel = docs[key].get(name)
                if not rel:
                    continue
                with self.subTest(key=key, layout=name):
                    sample = "docs/" + rel + ("feature.md" if rel.endswith("/") else "")
                    self.assertRegex(sample, trigger)


@requires_bash()
class ShellFallbackTest(StoreTestCase):
    def no_python_path(self):
        """A PATH holding only what docs-root.sh needs besides Python."""
        bin_dir = self.tmp / "bin"
        bin_dir.mkdir(exist_ok=True)
        for tool in ("dirname",):
            target = bin_dir / tool
            if not target.exists():
                os.symlink(shutil.which(tool), str(target))
        return str(bin_dir)

    def run_shell(self, script, cwd, path=None):
        env = dict(os.environ)
        if path is not None:
            env["PATH"] = path
        result = subprocess.run([shells.bash_path(), "-c", '. "$1"; ' + script, "_", str(SHELL_LIB)],
                                cwd=str(cwd), env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return result.returncode, result.stdout.decode()

    def test_the_shell_default_table_mirrors_the_development_column(self):
        (self.tmp / "bare").mkdir()
        for key, entry in layout_map()["docs"].items():
            with self.subTest(key=key):
                code, out = self.run_shell('devteam_doc_path "$PWD" ' + key, self.tmp / "bare")
                self.assertEqual(code, 0)
                expected = "docs/" + entry["development"] if entry["development"] else ""
                self.assertEqual(out, expected + "\n")

    def test_without_python_a_gated_project_gets_the_development_defaults(self):
        root = self.tmp / "app"
        (root / ".dev-team-agents").mkdir(parents=True)
        (root / ".dev-team-agents" / "project.json").write_text(json.dumps(
            {"schema": 1, "project_id": PROJECT_ID, "context_paths": ["handbook"], "docs_layout": "gated"}))
        self.assertEqual(self.run_shell('devteam_doc_path "$PWD" adr', root, path=self.no_python_path()),
                         (0, "docs/development/adrs/\n"))
        self.assertEqual(self.run_shell('devteam_docs_layout "$PWD"', root, path=self.no_python_path()),
                         (0, "development\n"))
        self.assertEqual(self.run_shell('devteam_doc_readonly "$PWD"', root, path=self.no_python_path()), (0, ""))

    def test_an_unknown_key_returns_2_with_or_without_python(self):
        (self.tmp / "bare").mkdir()
        self.assertEqual(self.run_shell('devteam_doc_path "$PWD" nope', self.tmp / "bare")[0], 2)

    def test_the_shim_is_executable(self):
        self.assertTrue(os.access(str(SHIM), os.X_OK))
        self.assertIn("set -euo pipefail", SHIM.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
