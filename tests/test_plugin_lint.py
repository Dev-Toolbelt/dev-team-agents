"""Self-test for helpers/plugin-lint.sh against temp copies of a valid manifest."""

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
LINT = REPO / "helpers" / "plugin-lint.sh"

MANIFEST = {
    "schema": 1,
    "name": "demo",
    "title": "Demo",
    "description": "A demo plugin.",
    "config": [
        {"key": "paths", "type": "string_list", "label": "P", "help": "h", "default": []},
        {"key": "on", "type": "boolean", "label": "O", "help": "h", "default": False},
        {"key": "n", "type": "integer", "label": "N", "help": "h", "default": 3, "min": 1, "max": 5},
        {"key": "mode", "type": "enum", "label": "M", "help": "h", "default": "a",
         "options": [{"value": "a", "label": "A"}]},
    ],
    "actions": [{"id": "run", "label": "Run", "help": "h", "runtime": "bash",
                 "script": "scripts/run.sh", "output": "log"}],
    "status": {"runtime": "python3", "script": "scripts/status.py"},
    "hooks": {"stop": "hooks/stop.sh"},
}


class PluginLintTest(unittest.TestCase):
    def build(self, mutate=None, skip=()):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, True)
        m = json.loads(json.dumps(MANIFEST))
        if mutate:
            mutate(m)
        p = tmp / "demo"
        (p / "scripts").mkdir(parents=True)
        (p / "hooks").mkdir()
        (tmp / "_schema").mkdir()
        files = {"scripts/run.sh": "echo hi\n", "scripts/status.py": "print(1)\n", "hooks/stop.sh": "exit 0\n"}
        for rel, body in files.items():
            if rel not in skip:
                (p / rel).write_text(body)
        (p / "plugin.json").write_text(json.dumps(m))
        return tmp

    def run_lint(self, root):
        return subprocess.run(["bash", str(LINT), str(root)], capture_output=True, text=True)

    def test_valid(self):
        r = self.run_lint(self.build())
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(r.stdout, "")

    def assert_fails(self, root, needle):
        r = self.run_lint(root)
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn(needle, r.stdout)
        self.assertTrue(r.stdout.startswith("plugin-lint: demo: "))

    def test_name_mismatch(self):
        self.assert_fails(self.build(lambda m: m.update(name="other")), "does not match directory")

    def test_script_escape(self):
        self.assert_fails(self.build(lambda m: m["actions"][0].update(script="../x.sh")), "without '..'")

    def test_missing_script(self):
        self.assert_fails(self.build(skip=("scripts/run.sh",)), "script not found")

    def test_wrong_default_type(self):
        self.assert_fails(self.build(lambda m: m["config"][1].update(default="no")), "does not match type")

    def test_options_without_enum(self):
        self.assert_fails(self.build(lambda m: m["config"][0].update(options=[{"value": "a", "label": "A"}])),
                          "options only allowed")

    def test_bash_syntax(self):
        root = self.build()
        (root / "demo/scripts/run.sh").write_text("if then\n")
        self.assert_fails(root, "bash syntax error")


if __name__ == "__main__":
    unittest.main()
