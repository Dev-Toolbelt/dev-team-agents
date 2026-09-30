"""Plugin hook dispatchers, the graphify plugin's scripts and the deprecation wrapper.

Everything is driven through subprocess in a throwaway git repository, with a fake
`graphify` binary on PATH so no test needs the real tool.
"""

import json
import os
import shutil
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

from devteam_support import REPO_ROOT, requires_bash

PLUGIN = REPO_ROOT / "plugins" / "graphify"
PRE = REPO_ROOT / "scripts" / "hooks" / "pre-tool-use" / "02d-plugins.sh"
STOP = REPO_ROOT / "scripts" / "hooks" / "stop" / "99a-plugins.sh"
OLD_HINT = REPO_ROOT / "scripts" / "hooks" / "pre-tool-use" / "02-graphify-hint.sh"
WRAPPER = REPO_ROOT / "scripts" / "graphify-refresh.sh"
GLOB_INPUT = '{"tool_name":"Glob","tool_input":{}}'


def settings_text(enabled, config=None):
    return json.dumps({"schema": 1, "enabled": enabled, "config": config or {}},
                      indent=2, sort_keys=True) + "\n"


@requires_bash()
class PluginHookTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.root = self.tmp / "proj"
        self.root.mkdir()
        self.git("init", "-q")
        self.git("config", "user.email", "t@t")
        self.git("config", "user.name", "t")
        (self.root / "src").mkdir()
        (self.root / "src" / "a.py").write_text("x = 1\n")
        self.git("add", "-A")
        self.git("commit", "-qm", "init")
        self.bin = self.tmp / "bin"
        self.bin.mkdir()
        self.calls = self.tmp / "graphify-calls"
        fake = self.bin / "graphify"
        fake.write_text('#!/usr/bin/env bash\necho "$@" >> "%s"\nmkdir -p "$2/graphify-out"\n'
                        'echo {} > "$2/graphify-out/graph.json"\n' % self.calls)
        fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
        self.state = self.tmp / "state"

    def git(self, *args):
        subprocess.run(["git", *args], cwd=self.root, check=True, capture_output=True)

    def env(self, **extra):
        env = {k: v for k, v in os.environ.items() if not k.startswith("DEVTEAM_")}
        env["PATH"] = "%s:%s" % (self.bin, env["PATH"])
        env["CLAUDE_PROJECT_DIR"] = str(self.root)
        env["DEVTEAM_STATE_DIR"] = str(self.state)
        env.update(extra)
        return env

    def run_script(self, script, *args, stdin="", **extra):
        return subprocess.run(["bash", str(script), *args], cwd=self.root, input=stdin,
                              capture_output=True, text=True, env=self.env(**extra))

    def settings(self, enabled=True, config=None):
        d = self.root / ".dev-team-agents" / "plugin-settings"
        d.mkdir(parents=True, exist_ok=True)
        (d / "graphify.json").write_text(settings_text(enabled, config))

    def graph(self):
        (self.root / "graphify-out").mkdir(exist_ok=True)
        (self.root / "graphify-out" / "graph.json").write_text("{}")

    # -- PreToolUse dispatcher ----------------------------------------------------

    def test_pre_dispatcher_is_silent_without_settings(self):
        self.graph()
        r = self.run_script(PRE, stdin=GLOB_INPUT)
        self.assertEqual((r.returncode, r.stdout), (0, ""))

    def test_pre_dispatcher_runs_enabled_plugin_hook(self):
        self.graph()
        self.settings(True)
        r = self.run_script(PRE, stdin=GLOB_INPUT)
        self.assertEqual(r.returncode, 0)
        self.assertIn("Knowledge graph exists", r.stdout)

    def test_pre_dispatcher_hint_fires_once(self):
        self.graph()
        self.settings(True)
        first = self.run_script(PRE, stdin=GLOB_INPUT)
        second = self.run_script(PRE, stdin=GLOB_INPUT)
        self.assertIn("graphify", first.stdout)
        self.assertEqual(second.stdout, "")

    def test_pre_dispatcher_skips_disabled_plugin(self):
        self.graph()
        self.settings(False)
        r = self.run_script(PRE, stdin=GLOB_INPUT)
        self.assertEqual((r.returncode, r.stdout), (0, ""))

    def test_pre_hook_ignores_non_search_tools(self):
        self.graph()
        self.settings(True)
        r = self.run_script(PRE, stdin='{"tool_name":"Bash"}')
        self.assertEqual(r.stdout, "")

    def test_legacy_hint_defers_to_settings_file(self):
        self.graph()
        self.settings(True)
        r = self.run_script(OLD_HINT, stdin=GLOB_INPUT, DEVTEAM_STATE_DIR=str(self.state))
        self.assertEqual(r.stdout, "")

    def test_legacy_hint_still_fires_without_settings(self):
        self.graph()
        r = self.run_script(OLD_HINT, stdin=GLOB_INPUT)
        self.assertIn("Knowledge graph exists", r.stdout)

    # -- Stop dispatcher and hook -------------------------------------------------

    def test_stop_skips_when_auto_refresh_false(self):
        self.settings(True, {"targetPaths": ["src"], "auto_refresh": False})
        r = self.run_script(STOP)
        self.assertEqual(r.returncode, 0)
        self.assertFalse(self.calls.exists())

    def test_stop_rebuilds_when_auto_refresh_true(self):
        self.settings(True, {"targetPaths": ["src"], "auto_refresh": True})
        r = self.run_script(STOP, "--quiet")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(self.calls.exists())
        self.assertTrue((self.root / "graphify-out" / "graph.json").exists())
        state = json.loads((self.state / "state.json").read_text())
        self.assertEqual(state["graphify_last_run"],
                         subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.root,
                                        capture_output=True, text=True).stdout.strip())
        self.assertIn("graphify_last_run_at", state)

    def test_stop_skips_disabled_and_no_changes(self):
        self.settings(False, {"targetPaths": ["src"], "auto_refresh": True})
        self.run_script(STOP)
        self.assertFalse(self.calls.exists())
        self.settings(True, {"targetPaths": ["src"], "auto_refresh": True})
        self.run_script(STOP, DEVTEAM_NO_CHANGES="1")
        self.assertFalse(self.calls.exists())

    # -- refresh.sh and the wrapper -----------------------------------------------

    def test_refresh_forces_without_args_and_skips_with_if_changed(self):
        self.settings(True, {"targetPaths": ["src"]})
        refresh = PLUGIN / "scripts" / "refresh.sh"
        r = self.run_script(refresh, DEVTEAM_PROJECT_ROOT=str(self.root))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.calls.unlink()
        r = self.run_script(refresh, "--if-changed", DEVTEAM_PROJECT_ROOT=str(self.root))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse(self.calls.exists(), "unchanged tree must not rebuild")
        r = self.run_script(refresh, DEVTEAM_PROJECT_ROOT=str(self.root))
        self.assertTrue(self.calls.exists(), "no args forces a rebuild")

    def test_refresh_fails_on_empty_target_paths(self):
        self.settings(True, {"targetPaths": []})
        r = self.run_script(PLUGIN / "scripts" / "refresh.sh", DEVTEAM_PROJECT_ROOT=str(self.root))
        self.assertNotEqual(r.returncode, 0)

    def test_refresh_reads_legacy_config(self):
        legacy = self.root / ".dev-team-agents" / "user-data"
        legacy.mkdir(parents=True)
        (legacy / "graphify.json").write_text('{"targetPaths": ["src"]}')
        r = self.run_script(PLUGIN / "scripts" / "refresh.sh", DEVTEAM_PROJECT_ROOT=str(self.root))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(self.calls.exists())

    def test_wrapper_warns_and_execs_plugin_script(self):
        self.settings(True, {"targetPaths": ["src"]})
        r = self.run_script(WRAPPER)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("deprecated", r.stderr)
        self.assertTrue(self.calls.exists(), "first run has no graphify-out, so --if-changed builds")

    # -- detect.py and status.sh --------------------------------------------------

    def detect(self, root):
        r = subprocess.run(["python3", str(PLUGIN / "scripts" / "detect.py")], cwd=root,
                           capture_output=True, text=True, env=self.env())
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def tree(self, name, dirs=(), files=()):
        root = self.tmp / name
        for d in dirs:
            (root / d).mkdir(parents=True)
        for f in files:
            (root / f).parent.mkdir(parents=True, exist_ok=True)
            (root / f).write_text("")
        root.mkdir(exist_ok=True)
        return root

    def test_detect_node(self):
        root = self.tree("node", ["src", "lib", "node_modules", "docs"], ["package.json", "yarn.lock"])
        self.assertEqual(self.detect(root), {"targetPaths": ["src", "lib"],
                                             "manifestPaths": ["package.json", "yarn.lock"]})

    def test_detect_python_includes_packages(self):
        root = self.tree("py", ["src"], ["pyproject.toml", "mypkg/__init__.py", "docs/x.md"])
        out = self.detect(root)
        self.assertEqual(out["targetPaths"], ["src", "mypkg"])
        self.assertEqual(out["manifestPaths"], ["pyproject.toml"])

    def test_detect_go(self):
        root = self.tree("go", ["cmd", "internal", "vendor"], ["go.mod"])
        self.assertEqual(self.detect(root)["targetPaths"], ["cmd", "internal"])

    def test_detect_laravel(self):
        root = self.tree("php", ["app", "routes", "database/migrations", "src"],
                         ["composer.json", "artisan", "composer.lock"])
        out = self.detect(root)
        self.assertEqual(out["targetPaths"], ["app", "routes", "database/migrations"])
        self.assertEqual(out["manifestPaths"], ["composer.json", "composer.lock"])

    def test_detect_unknown_stack(self):
        root = self.tree("unknown", ["src", "build", "misc"])
        self.assertEqual(self.detect(root), {"targetPaths": ["src"], "manifestPaths": []})

    def test_detect_empty_tree(self):
        self.assertEqual(self.detect(self.tree("empty")), {"targetPaths": [], "manifestPaths": []})

    def test_status_without_graph_is_valid_json(self):
        r = self.run_script(PLUGIN / "scripts" / "status.sh", DEVTEAM_PROJECT_ROOT=str(self.root))
        self.assertEqual(r.returncode, 0)
        data = json.loads(r.stdout)
        self.assertIn("No graph", data["summary"])
        self.assertTrue(all({"label", "value"} <= set(f) for f in data["facts"]))

    def test_status_after_build_reports_commit(self):
        self.settings(True, {"targetPaths": ["src"]})
        self.run_script(PLUGIN / "scripts" / "refresh.sh", DEVTEAM_PROJECT_ROOT=str(self.root))
        r = self.run_script(PLUGIN / "scripts" / "status.sh", DEVTEAM_PROJECT_ROOT=str(self.root))
        data = json.loads(r.stdout)
        self.assertIn("Graph built at", data["summary"])
        self.assertIn("up to date", [f["value"] for f in data["facts"]])


if __name__ == "__main__":
    unittest.main()
