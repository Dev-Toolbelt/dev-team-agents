"""ADR-0018: manifest-declared plugins, their settings file and the `devteam plugin` CLI.

The fixture core carries tiny fake plugins, never the real graphify scripts: what is
under test is the machinery (discovery, validation, settings, coercion, the script
runner and its environment), and a fake plugin lets each test state exactly what the
script prints and how it exits.
"""

from __future__ import annotations

import copy
import json
import os
import signal
import stat
import subprocess
import sys
import threading
import time
import unittest
from pathlib import Path

from devteam_support import CLI, REPO_ROOT, StoreTestCase, requires_posix_modes

from devteam import bind, plugins, project
from devteam.errors import ConflictError, EnvError, UsageError

MISSING_BINARY = "definitely-not-installed-xyz"

DEMO = {
    "schema": 1,
    "name": "demo",
    "title": "Demo",
    "description": "A fake plugin for the tests.",
    "homepage": "https://example.com/demo",
    "requires": [{"binary": "sh", "install_hint": "install sh"}],
    "config": [
        {"key": "names", "type": "string_list", "label": "Names", "help": "h", "required": True, "default": []},
        {"key": "flag", "type": "boolean", "label": "Flag", "help": "h", "default": False},
        {"key": "count", "type": "integer", "label": "Count", "help": "h", "default": 5, "min": 1, "max": 10},
        {
            "key": "mode",
            "type": "enum",
            "label": "Mode",
            "help": "h",
            "default": "fast",
            "options": [{"value": "fast", "label": "Fast"}, {"value": "slow", "label": "Slow"}],
        },
        {"key": "label", "type": "string", "label": "Label", "help": "h", "default": "", "placeholder": "e.g. main"},
    ],
    "actions": [
        {"id": "detect", "label": "Detect", "help": "h", "runtime": "python3", "script": "scripts/detect.py",
         "output": "config", "requires_enabled": False, "timeout_seconds": 30},
        {"id": "probe", "label": "Probe", "help": "h", "runtime": "python3", "script": "scripts/probe.py",
         "output": "json", "requires_enabled": True, "timeout_seconds": 30},
        {"id": "say", "label": "Say", "help": "h", "runtime": "bash", "script": "scripts/say.sh",
         "output": "log", "requires_enabled": True, "timeout_seconds": 30},
        {"id": "boom", "label": "Boom", "help": "h", "runtime": "bash", "script": "scripts/boom.sh",
         "output": "log", "requires_enabled": False, "timeout_seconds": 30},
        {"id": "slow", "label": "Slow", "help": "h", "runtime": "bash", "script": "scripts/slow.sh",
         "output": "log", "requires_enabled": False, "timeout_seconds": 1},
        {"id": "junk", "label": "Junk", "help": "h", "runtime": "bash", "script": "scripts/junk.sh",
         "output": "json", "requires_enabled": False, "timeout_seconds": 30},
        {"id": "hang", "label": "Hang", "help": "h", "runtime": "bash", "script": "scripts/hang.sh",
         "output": "log", "requires_enabled": False, "timeout_seconds": 60},
        {"id": "leak", "label": "Leak", "help": "h", "runtime": "bash", "script": "scripts/leak.sh",
         "output": "log", "requires_enabled": False, "timeout_seconds": 1},
    ],
    "status": {"runtime": "python3", "script": "scripts/status.py", "timeout_seconds": 5},
    "hooks": {"stop": "hooks/stop.sh"},
}

NEEDY = {
    "schema": 1,
    "name": "needy",
    "title": "Needy",
    "description": "Needs a binary nobody has.",
    "requires": [{"binary": MISSING_BINARY, "install_hint": "/devteam:install needy"}],
    "actions": [
        {"id": "go", "label": "Go", "help": "h", "runtime": "bash", "script": "scripts/go.sh",
         "output": "log", "requires_enabled": False},
    ],
}

# Named like the plugin that replaced `graphify.json`, so the legacy mapping applies.
GRAPHIFY = {
    "schema": 1,
    "name": "graphify",
    "title": "Graphify (fake)",
    "description": "Stands in for the real plugin.",
    "config": [
        {"key": "targetPaths", "type": "string_list", "label": "Paths", "help": "h", "required": True, "default": []},
        {"key": "auto_refresh", "type": "boolean", "label": "Auto", "help": "h", "default": False},
    ],
}

SCRIPTS = {
    "demo/scripts/detect.py": 'import json\nprint(json.dumps({"names": ["src"], "bogus": 1, "count": "not-an-int"}))\n',
    "demo/scripts/probe.py": (
        "import json, os\n"
        'keys = ["DEVTEAM_PROJECT_ROOT", "DEVTEAM_PLUGIN_DIR", "DEVTEAM_PLUGIN_SETTINGS",\n'
        '        "DEVTEAM_PLUGIN_CONFIG", "DEVTEAM_PLUGIN_CONFIG_TRUNCATED", "DEVTEAM_STATE_DIR"]\n'
        "out = {k: os.environ.get(k) for k in keys}\n"
        'out["cwd"] = os.getcwd()\n'
        "print(json.dumps(out))\n"
    ),
    "demo/scripts/say.sh": "echo out-line\necho err-line >&2\n",
    "demo/scripts/boom.sh": "echo before-failure\necho bad >&2\nexit 7\n",
    "demo/scripts/slow.sh": "sleep 5\n",
    "demo/scripts/junk.sh": "echo not json\n",
    "demo/scripts/hang.sh": 'echo $$ > "$DEVTEAM_PROJECT_ROOT/.hang.pid"\nsleep 60 &\nwait\n',
    "demo/scripts/leak.sh": 'python3 -c "import os,time; os.setsid(); time.sleep(8)" &\nsleep 30\n',
    "demo/scripts/status.py": (
        "import json, os, sys\n"
        'if os.path.exists(os.path.join(os.environ["DEVTEAM_PROJECT_ROOT"], ".status-fail")):\n'
        "    sys.exit(3)\n"
        'print(json.dumps({"summary": "all good", "facts": [{"label": "Nodes", "value": 42}]}))\n'
    ),
    "demo/hooks/stop.sh": "exit 0\n",
    "needy/scripts/go.sh": "echo went\n",
}


def write_plugin_tree(core_source, extra=None):
    root = Path(core_source) / "plugins"
    for manifest in (DEMO, NEEDY, GRAPHIFY):
        directory = root / manifest["name"]
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "plugin.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    for rel, body in SCRIPTS.items():
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")
    for rel, body in (extra or {}).items():
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")


class PluginTestCase(StoreTestCase):
    extra_plugin_files = None

    def setUp(self):
        super().setUp()
        write_plugin_tree(self.source, self.extra_plugin_files)
        self.install_version("3.0.0", activate=True)
        self.root = self.new_project()
        result = bind.bind(self.root, provider_names=["claude"])
        self.pid = result["project_id"]
        self.ctx = plugins.Context(self.root, self.pid)

    def settings_file(self, name="demo"):
        return self.root / project.PROJECT_DIR / plugins.SETTINGS_DIR / "{}.json".format(name)

    def cli(self, *args):
        code, out, err = self.run_cli("plugin", *args, "--path", str(self.root), "--json")
        try:
            body = json.loads(out)
        except ValueError:
            body = None
        return code, body, err


class ManifestValidationTest(unittest.TestCase):
    def problems(self, mutate, dirname="demo"):
        manifest = copy.deepcopy(DEMO)
        mutate(manifest)
        return plugins.validate_manifest(manifest, dirname=dirname)

    def test_a_correct_manifest_has_no_problems(self):
        self.assertEqual(plugins.validate_manifest(DEMO, dirname="demo"), [])

    def test_the_shipped_graphify_manifest_is_valid(self):
        path = REPO_ROOT / "plugins" / "graphify" / "plugin.json"
        if not path.is_file():
            self.skipTest("plugins/graphify is not present in this tree")
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(plugins.validate_manifest(data, dirname="graphify"), [])

    def test_required_keys_types_and_unknown_keys(self):
        self.assertTrue(self.problems(lambda m: m.pop("title")))
        self.assertTrue(self.problems(lambda m: m.update(extra=1)))
        self.assertTrue(self.problems(lambda m: m.update(schema=2)))
        self.assertTrue(self.problems(lambda m: m.update(title="")))
        self.assertTrue(self.problems(lambda m: m.update(title="x" * 41)))
        self.assertTrue(self.problems(lambda m: m.update(homepage="http://insecure")))
        self.assertTrue(plugins.validate_manifest([], dirname="demo"))

    def test_the_name_must_match_the_pattern_and_the_directory(self):
        self.assertTrue(self.problems(lambda m: m.update(name="Bad_Name")))
        self.assertTrue(self.problems(lambda m: None, dirname="other"))

    def test_scripts_must_be_relative_and_stay_inside(self):
        for bad in ("../escape.sh", "/etc/passwd", "a/../../b.sh", "sp ace.sh", ""):
            with self.subTest(script=bad):
                self.assertTrue(self.problems(lambda m: m["actions"][0].update(script=bad)))
                self.assertTrue(self.problems(lambda m: m["hooks"].update(stop=bad)))
                self.assertTrue(self.problems(lambda m: m["status"].update(script=bad)))

    def test_runtime_and_output_are_enums(self):
        self.assertTrue(self.problems(lambda m: m["actions"][0].update(runtime="zsh")))
        self.assertTrue(self.problems(lambda m: m["actions"][0].update(output="xml")))
        self.assertTrue(self.problems(lambda m: m["status"].update(runtime="node")))

    def test_ids_keys_and_timeouts(self):
        self.assertTrue(self.problems(lambda m: m["actions"][1].update(id="detect")))
        self.assertTrue(self.problems(lambda m: m["config"][1].update(key="names")))
        self.assertTrue(self.problems(lambda m: m["actions"][0].update(timeout_seconds=0)))
        self.assertTrue(self.problems(lambda m: m["actions"][0].update(timeout_seconds=3601)))
        self.assertTrue(self.problems(lambda m: m["status"].update(timeout_seconds=31)))
        self.assertTrue(self.problems(lambda m: m["actions"][0].update(timeout_seconds=True)))

    def test_config_fields_need_a_type_default_and_options_for_enums(self):
        self.assertTrue(self.problems(lambda m: m["config"][0].update(type="date")))
        self.assertTrue(self.problems(lambda m: m["config"][0].pop("default")))
        self.assertTrue(self.problems(lambda m: m["config"][3].pop("options")))
        self.assertTrue(self.problems(lambda m: m["config"][1].update(default="yes")))
        self.assertTrue(self.problems(lambda m: m["config"][3].update(default="missing")))

    def test_requires_and_hooks_shape(self):
        self.assertTrue(self.problems(lambda m: m["requires"][0].pop("install_hint")))
        self.assertTrue(self.problems(lambda m: m["requires"][0].update(binary="a b")))
        self.assertTrue(self.problems(lambda m: m["hooks"].update(post_tool_use="x.sh")))


class DiscoveryTest(PluginTestCase):
    def test_valid_plugins_are_found_and_the_schema_directory_is_not_one(self):
        self.assertEqual(sorted(self.ctx.plugins), ["demo", "graphify", "needy"])
        self.assertEqual(self.ctx.invalid, [])

    def test_invalid_manifests_are_reported_and_skipped(self):
        version_dir = self.ctx.version_dir
        broken = version_dir / "plugins" / "broken"
        broken.mkdir()
        (broken / "plugin.json").write_text("{not json", encoding="utf-8")
        mismatch = version_dir / "plugins" / "mismatch"
        mismatch.mkdir()
        (mismatch / "plugin.json").write_text(json.dumps(dict(DEMO, name="other")), encoding="utf-8")
        (version_dir / "plugins" / "nomanifest").mkdir()
        found, invalid = plugins.discover(version_dir)
        self.assertEqual(sorted(found), ["demo", "graphify", "needy"])
        self.assertEqual(sorted(item["name"] for item in invalid), ["broken", "mismatch", "nomanifest"])

    def test_a_core_version_without_a_plugins_tree_has_no_plugins(self):
        found, invalid = plugins.discover(self.tmp / "nowhere")
        self.assertEqual((found, invalid), ({}, []))

    def test_the_runtime_link_resolves_to_the_core_tree(self):
        link = self.root / project.PROJECT_DIR / "plugins"
        self.assertTrue(link.is_symlink())
        self.assertTrue((link / "demo" / "plugin.json").is_file())


class ViewShapeTest(PluginTestCase):
    VIEW_KEYS = {
        "name", "title", "description", "homepage", "enabled", "source", "settings_file",
        "requirements", "ready", "configured", "config_fields", "config", "unknown_config",
        "actions", "hooks", "status",
    }

    def test_list_payload_shape(self):
        code, body, _ = self.cli("list")
        self.assertEqual(code, 0)
        self.assertTrue(body["ok"])
        self.assertEqual(body["project_id"], self.pid)
        self.assertEqual([p["name"] for p in body["plugins"]], ["demo", "graphify", "needy"])
        for view in body["plugins"]:
            self.assertEqual(set(view), self.VIEW_KEYS)

    def test_show_payload_for_a_disabled_plugin(self):
        code, body, _ = self.cli("show", "demo")
        self.assertEqual(code, 0)
        self.assertEqual(set(body), self.VIEW_KEYS | {"ok"})
        self.assertFalse(body["enabled"])
        self.assertEqual(body["source"], "none")
        self.assertEqual(body["settings_file"], ".dev-team-agents/plugin-settings/demo.json")
        self.assertEqual(body["requirements"], [{"binary": "sh", "found": True, "install_hint": "install sh"}])
        self.assertTrue(body["ready"])
        self.assertFalse(body["configured"])
        self.assertEqual(body["config"], {"names": [], "flag": False, "count": 5, "mode": "fast", "label": ""})
        self.assertEqual(body["hooks"], ["stop"])
        self.assertIsNone(body["status"])
        self.assertEqual(body["homepage"], "https://example.com/demo")
        self.assertEqual(
            body["actions"][0],
            {"id": "detect", "label": "Detect", "help": "h", "output": "config",
             "requires_enabled": False, "writes": False, "timeout_seconds": 30},
        )
        # No timeout in the manifest -> the documented default of 300.
        _, needy, _ = self.cli("show", "needy")
        self.assertEqual(needy["actions"][0]["timeout_seconds"], 300)
        # Config fields are the manifest entries, unchanged (min/max/options/placeholder included).
        self.assertEqual(body["config_fields"], DEMO["config"])
        count = next(f for f in body["config_fields"] if f["key"] == "count")
        self.assertEqual((count["min"], count["max"]), (1, 10))
        mode = next(f for f in body["config_fields"] if f["key"] == "mode")
        self.assertEqual(mode["options"][0], {"value": "fast", "label": "Fast"})
        self.assertTrue(next(a for a in body["actions"] if a["id"] == "say")["writes"])

    def test_homepage_is_null_when_the_manifest_has_none(self):
        _, body, _ = self.cli("show", "needy")
        self.assertIsNone(body["homepage"])
        self.assertFalse(body["ready"])
        self.assertEqual(body["requirements"][0]["found"], False)

    def test_show_of_an_unknown_plugin_is_a_usage_error(self):
        code, body, _ = self.cli("show", "nope")
        self.assertEqual(code, 2)
        self.assertFalse(body["ok"])

    def test_an_unbound_path_is_a_usage_error(self):
        code, out, _ = self.run_cli("plugin", "list", "--path", str(self.tmp / "empty"), "--json")
        self.assertEqual(code, 2)

    def test_status_appears_only_while_enabled_and_a_failing_script_yields_null(self):
        plugins.enable(self.ctx, "demo")
        _, body, _ = self.cli("show", "demo")
        self.assertEqual(body["status"], {"summary": "all good", "facts": [{"label": "Nodes", "value": "42"}]})
        (self.root / ".status-fail").write_text("x", encoding="utf-8")
        code, body, _ = self.cli("show", "demo")
        self.assertEqual(code, 0)
        self.assertIsNone(body["status"])
        plugins.disable(self.ctx, "demo")
        (self.root / ".status-fail").unlink()
        _, body, _ = self.cli("show", "demo")
        self.assertIsNone(body["status"])


class EnableDisableTest(PluginTestCase):
    def test_enable_refuses_without_the_binary_and_names_every_hint(self):
        code, body, _ = self.cli("enable", "needy")
        self.assertEqual(code, 3)
        self.assertIn("/devteam:install needy", body["hint"])
        self.assertFalse(self.settings_file("needy").exists())

    def test_force_enables_anyway(self):
        code, body, _ = self.cli("enable", "needy", "--force")
        self.assertEqual(code, 0)
        self.assertTrue(body["plugin"]["enabled"])
        self.assertTrue(body["changed"])
        self.assertFalse(body["seeded"])
        self.assertFalse(body["plugin"]["ready"])

    def test_enable_seeds_config_from_a_config_output_action(self):
        code, body, _ = self.cli("enable", "demo")
        self.assertEqual(code, 0)
        self.assertEqual(set(body), {"ok", "plugin", "changed", "seeded"})
        self.assertTrue(body["seeded"])
        self.assertTrue(body["changed"])
        self.assertEqual(body["plugin"]["config"]["names"], ["src"])
        # An unknown key and a value of the wrong type in the answer are dropped.
        stored = json.loads(self.settings_file().read_text(encoding="utf-8"))
        self.assertEqual(stored, {"schema": 1, "enabled": True, "config": {"names": ["src"]}})
        self.assertTrue(body["plugin"]["configured"])

    def test_enable_twice_changes_nothing_the_second_time(self):
        plugins.enable(self.ctx, "demo")
        before = self.settings_file().read_text(encoding="utf-8")
        result = plugins.enable(self.ctx, "demo")
        self.assertFalse(result["changed"])
        self.assertFalse(result["seeded"])
        self.assertEqual(self.settings_file().read_text(encoding="utf-8"), before)

    def test_a_plugin_without_a_seed_action_enables_with_empty_config(self):
        result = plugins.enable(self.ctx, "graphify")
        self.assertTrue(result["changed"])
        self.assertFalse(result["seeded"])
        self.assertEqual(
            json.loads(self.settings_file("graphify").read_text(encoding="utf-8")),
            {"schema": 1, "enabled": True, "config": {}},
        )

    def test_disable_keeps_the_config(self):
        plugins.enable(self.ctx, "demo")
        code, body, _ = self.cli("disable", "demo")
        self.assertEqual(code, 0)
        self.assertEqual(set(body), {"ok", "plugin", "changed"})
        self.assertTrue(body["changed"])
        self.assertFalse(body["plugin"]["enabled"])
        self.assertEqual(body["plugin"]["config"]["names"], ["src"])
        stored = json.loads(self.settings_file().read_text(encoding="utf-8"))
        self.assertEqual(stored["enabled"], False)
        self.assertEqual(stored["config"], {"names": ["src"]})

    def test_disable_of_a_plugin_that_was_never_enabled_writes_nothing(self):
        result = plugins.disable(self.ctx, "demo")
        self.assertFalse(result["changed"])
        self.assertFalse(self.settings_file().exists())

    def test_re_enable_does_not_reseed(self):
        plugins.enable(self.ctx, "demo")
        plugins.config_set(self.ctx, "demo", "names", '["lib"]')
        plugins.disable(self.ctx, "demo")
        result = plugins.enable(self.ctx, "demo")
        self.assertFalse(result["seeded"])
        self.assertEqual(result["plugin"]["config"]["names"], ["lib"])


class SerializationTest(PluginTestCase):
    def test_the_file_is_exactly_indent_two_sorted_with_a_trailing_newline(self):
        plugins.enable(self.ctx, "demo")
        plugins.config_set(self.ctx, "demo", "count", "7")
        text = self.settings_file().read_text(encoding="utf-8")
        expected = json.dumps(
            {"schema": 1, "enabled": True, "config": {"count": 7, "names": ["src"]}},
            indent=2,
            sort_keys=True,
        ) + "\n"
        self.assertEqual(text, expected)

    def test_the_bash_dispatcher_substring_is_present(self):
        plugins.enable(self.ctx, "graphify")
        self.assertIn('  "enabled": true', self.settings_file("graphify").read_text(encoding="utf-8"))
        plugins.disable(self.ctx, "graphify")
        text = self.settings_file("graphify").read_text(encoding="utf-8")
        self.assertIn('  "enabled": false', text)
        self.assertNotIn('"enabled": true', text)

    @requires_posix_modes
    def test_the_file_is_world_readable_because_it_is_committed(self):
        plugins.enable(self.ctx, "graphify")
        mode = stat.S_IMODE(self.settings_file("graphify").stat().st_mode)
        self.assertEqual(mode, 0o644)

    def test_no_temporary_file_is_left_beside_it(self):
        plugins.enable(self.ctx, "graphify")
        names = sorted(p.name for p in self.settings_file("graphify").parent.iterdir())
        self.assertEqual(names, ["graphify.json"])


class ConfigTest(PluginTestCase):
    def test_get_returns_the_effective_config_or_one_key(self):
        code, body, _ = self.cli("config", "get", "demo")
        self.assertEqual(code, 0)
        self.assertEqual(body["plugin"], "demo")
        self.assertEqual(body["config"]["count"], 5)
        code, body, _ = self.cli("config", "get", "demo", "count")
        self.assertEqual((body["plugin"], body["key"], body["value"]), ("demo", "count", 5))
        code, body, _ = self.cli("config", "get", "demo", "nope")
        self.assertEqual(code, 2)

    def test_set_coerces_by_declared_type(self):
        cases = [
            ("count", "3", 3),
            ("flag", "true", True),
            ("names", '["a","b"]', ["a", "b"]),
            ("mode", "slow", "slow"),
            ("label", "hello world", "hello world"),
        ]
        for key, raw, expected in cases:
            with self.subTest(key=key):
                code, body, _ = self.cli("config", "set", "demo", key, raw)
                self.assertEqual(code, 0)
                self.assertEqual(set(body), {"ok", "plugin", "key", "value"})
                self.assertEqual(body["value"], expected)
                self.assertEqual(body["plugin"]["config"][key], expected)

    def test_a_wrong_type_is_a_usage_error_and_writes_nothing(self):
        for key, raw in (
            ("count", "abc"),
            ("count", "3.5"),
            ("count", "99"),
            ("count", "0"),
            ("flag", "maybe"),
            ("names", "not json"),
            ("names", '"a string"'),
            ("names", "[1, 2]"),
            ("mode", "warp"),
            ("nope", "x"),
        ):
            with self.subTest(key=key, raw=raw):
                code, body, _ = self.cli("config", "set", "demo", key, raw)
                self.assertEqual(code, 2)
                self.assertFalse(body["ok"])
        self.assertFalse(self.settings_file().exists())

    def test_only_non_default_values_are_stored(self):
        plugins.config_set(self.ctx, "demo", "count", "9")
        plugins.config_set(self.ctx, "demo", "flag", "false")
        stored = json.loads(self.settings_file().read_text(encoding="utf-8"))
        self.assertEqual(stored["config"], {"count": 9})
        plugins.config_set(self.ctx, "demo", "count", "5")
        stored = json.loads(self.settings_file().read_text(encoding="utf-8"))
        self.assertEqual(stored["config"], {})

    def test_set_on_a_disabled_plugin_does_not_enable_it(self):
        plugins.config_set(self.ctx, "demo", "count", "2")
        self.assertFalse(json.loads(self.settings_file().read_text(encoding="utf-8"))["enabled"])

    def test_unset_restores_the_default(self):
        plugins.config_set(self.ctx, "demo", "count", "9")
        code, body, _ = self.cli("config", "unset", "demo", "count")
        self.assertEqual(code, 0)
        self.assertEqual(set(body), {"ok", "plugin", "key", "removed"})
        self.assertTrue(body["removed"])
        self.assertEqual(body["plugin"]["config"]["count"], 5)
        code, body, _ = self.cli("config", "unset", "demo", "count")
        self.assertEqual(code, 0)
        self.assertFalse(body["removed"])
        code, body, _ = self.cli("config", "unset", "demo", "nope")
        self.assertEqual(code, 2)

    def test_unknown_stored_keys_are_kept_and_reported(self):
        target = self.settings_file()
        target.parent.mkdir(parents=True)
        target.write_text(
            json.dumps({"schema": 1, "enabled": True, "config": {"retired": [1], "count": 8}}), encoding="utf-8"
        )
        _, body, _ = self.cli("show", "demo")
        self.assertEqual(body["unknown_config"], ["retired"])
        self.assertNotIn("retired", body["config"])
        plugins.config_set(self.ctx, "demo", "flag", "true")
        stored = json.loads(target.read_text(encoding="utf-8"))
        self.assertEqual(stored["config"], {"retired": [1], "count": 8, "flag": True})
        # ...and an unknown key can still be removed by name.
        result = plugins.config_unset(self.ctx, "demo", "retired")
        self.assertTrue(result["removed"])
        self.assertNotIn("retired", json.loads(target.read_text(encoding="utf-8"))["config"])

    def test_configured_needs_every_required_key_non_empty(self):
        self.assertFalse(plugins.build_view(self.ctx, self.ctx.plugin("demo"))["configured"])
        plugins.config_set(self.ctx, "demo", "names", '["src"]')
        self.assertTrue(plugins.build_view(self.ctx, self.ctx.plugin("demo"))["configured"])

    def test_a_malformed_settings_file_is_an_environment_error_and_is_not_overwritten(self):
        target = self.settings_file()
        target.parent.mkdir(parents=True)
        target.write_text("{oops", encoding="utf-8")
        code, body, _ = self.cli("config", "set", "demo", "count", "3")
        self.assertEqual(code, 3)
        self.assertEqual(target.read_text(encoding="utf-8"), "{oops")


class LegacyTest(PluginTestCase):
    def write_legacy(self, content=None):
        legacy = project.legacy_memory_dir(self.root) / "graphify.json"
        legacy.parent.mkdir(parents=True, exist_ok=True)
        legacy.write_text(
            json.dumps(content if content is not None else {"targetPaths": ["src"], "auto_refresh": True}),
            encoding="utf-8",
        )
        return legacy

    def test_the_legacy_file_reads_as_enabled_with_source_legacy(self):
        self.write_legacy()
        _, body, _ = self.cli("show", "graphify")
        self.assertTrue(body["enabled"])
        self.assertEqual(body["source"], "legacy")
        self.assertEqual(body["config"], {"targetPaths": ["src"], "auto_refresh": True})
        self.assertTrue(body["configured"])

    def test_only_the_mapped_plugin_reads_a_legacy_file(self):
        self.write_legacy()
        _, body, _ = self.cli("show", "demo")
        self.assertEqual(body["source"], "none")

    def test_the_settings_file_wins_over_the_legacy_one(self):
        self.write_legacy()
        plugins.disable(self.ctx, "graphify")
        _, body, _ = self.cli("show", "graphify")
        self.assertEqual(body["source"], "settings")
        self.assertFalse(body["enabled"])

    def test_disable_of_a_legacy_plugin_keeps_its_config(self):
        self.write_legacy()
        result = plugins.disable(self.ctx, "graphify")
        self.assertTrue(result["changed"])
        stored = json.loads(self.settings_file("graphify").read_text(encoding="utf-8"))
        self.assertEqual(stored, {"schema": 1, "enabled": False, "config": {"targetPaths": ["src"], "auto_refresh": True}})

    def test_migrate_moves_the_file_and_keeps_every_byte_of_content(self):
        legacy = self.write_legacy({"targetPaths": ["src", "lib"], "extra": {"k": 1}})
        report = plugins.migrate_legacy(self.root)
        self.assertEqual(report["moved"], ["graphify"])
        self.assertFalse(legacy.exists())
        stored = json.loads(self.settings_file("graphify").read_text(encoding="utf-8"))
        self.assertEqual(
            stored, {"schema": 1, "enabled": True, "config": {"targetPaths": ["src", "lib"], "extra": {"k": 1}}}
        )
        _, body, _ = self.cli("show", "graphify")
        self.assertEqual(body["source"], "settings")
        self.assertEqual(body["unknown_config"], ["extra"])

    def test_migrate_is_idempotent(self):
        self.write_legacy()
        plugins.migrate_legacy(self.root)
        before = self.settings_file("graphify").read_text(encoding="utf-8")
        report = plugins.migrate_legacy(self.root)
        self.assertEqual(report, {"moved": [], "skipped": []})
        self.assertEqual(self.settings_file("graphify").read_text(encoding="utf-8"), before)

    def test_migrate_never_touches_either_file_when_the_target_exists(self):
        plugins.disable(self.ctx, "graphify")  # no-op: nothing there yet
        plugins.config_set(self.ctx, "graphify", "auto_refresh", "true")
        legacy = self.write_legacy({"targetPaths": ["old"]})
        before_new = self.settings_file("graphify").read_text(encoding="utf-8")
        before_old = legacy.read_text(encoding="utf-8")
        report = plugins.migrate_legacy(self.root)
        self.assertEqual(report["moved"], [])
        self.assertEqual([item["plugin"] for item in report["skipped"]], ["graphify"])
        self.assertEqual(self.settings_file("graphify").read_text(encoding="utf-8"), before_new)
        self.assertEqual(legacy.read_text(encoding="utf-8"), before_old)

    def test_an_unreadable_legacy_file_is_left_alone(self):
        legacy = project.legacy_memory_dir(self.root) / "graphify.json"
        legacy.parent.mkdir(parents=True, exist_ok=True)
        legacy.write_text("{broken", encoding="utf-8")
        report = plugins.migrate_legacy(self.root)
        self.assertEqual(report["moved"], [])
        self.assertEqual(len(report["skipped"]), 1)
        self.assertEqual(legacy.read_text(encoding="utf-8"), "{broken")
        self.assertFalse(self.settings_file("graphify").exists())

    def test_bind_migrates_the_legacy_file(self):
        self.write_legacy()
        bind.bind(self.root, provider_names=["claude"])
        self.assertTrue(self.settings_file("graphify").is_file())
        self.assertFalse((project.legacy_memory_dir(self.root) / "graphify.json").exists())
        # A second bind is a no-op.
        before = self.settings_file("graphify").read_text(encoding="utf-8")
        bind.bind(self.root, provider_names=["claude"])
        self.assertEqual(self.settings_file("graphify").read_text(encoding="utf-8"), before)

    def test_sync_migrates_too(self):
        self.write_legacy()
        bind.sync_project(self.pid)
        self.assertTrue(self.settings_file("graphify").is_file())


class RunTest(PluginTestCase):
    def test_an_undeclared_action_is_a_usage_error(self):
        code, body, _ = self.cli("run", "demo", "nope")
        self.assertEqual(code, 2)
        self.assertFalse(body["ok"])

    def test_requires_enabled_on_a_disabled_plugin_is_a_conflict(self):
        code, body, _ = self.cli("run", "demo", "say")
        self.assertEqual(code, 4)
        self.assertIn("plugin enable", body["hint"])

    def test_a_missing_requirement_refuses_with_exit_three(self):
        code, body, _ = self.cli("run", "needy", "go")
        self.assertEqual(code, 3)
        self.assertIn("/devteam:install needy", body["hint"])

    def test_a_log_action_returns_the_merged_output_tail(self):
        plugins.enable(self.ctx, "demo")
        code, body, _ = self.cli("run", "demo", "say")
        self.assertEqual(code, 0)
        self.assertEqual(
            set(body), {"plugin", "action", "ok", "exit_code", "duration_ms", "output", "log_tail"}
        )
        self.assertTrue(body["ok"])
        self.assertEqual((body["plugin"], body["action"], body["exit_code"]), ("demo", "say", 0))
        self.assertIsNone(body["output"])
        self.assertIn("out-line", body["log_tail"])
        self.assertIn("err-line", body["log_tail"])
        self.assertIsInstance(body["duration_ms"], int)

    def test_a_failing_script_is_not_a_cli_error(self):
        code, body, _ = self.cli("run", "demo", "boom")
        self.assertEqual(code, 0)
        self.assertFalse(body["ok"])
        self.assertEqual(body["exit_code"], 7)
        self.assertIn("before-failure", body["log_tail"])
        self.assertIn("bad", body["log_tail"])
        self.assertIsNone(body["output"])

    def test_a_config_output_action_is_parsed_and_never_written(self):
        code, body, _ = self.cli("run", "demo", "detect")
        self.assertEqual(code, 0)
        self.assertTrue(body["ok"])
        self.assertEqual(body["output"], {"names": ["src"], "bogus": 1, "count": "not-an-int"})
        self.assertEqual(body["log_tail"], "")
        self.assertFalse(self.settings_file().exists())

    def test_a_json_action_that_prints_junk_fails_with_the_reason(self):
        code, body, _ = self.cli("run", "demo", "junk")
        self.assertEqual(code, 0)
        self.assertFalse(body["ok"])
        self.assertIsNone(body["output"])
        self.assertIn("JSON", body["log_tail"])

    def test_a_timeout_kills_the_script_and_reports_it(self):
        result = plugins.run(self.ctx, "demo", "slow")
        self.assertFalse(result["ok"])
        self.assertEqual(result["exit_code"], plugins.TIMEOUT_EXIT_CODE)
        self.assertIn("timed out", result["log_tail"])
        self.assertLess(result["duration_ms"], 4500)

    def test_the_script_environment_and_working_directory(self):
        plugins.enable(self.ctx, "demo")
        plugins.config_set(self.ctx, "demo", "count", "8")
        result = plugins.run(self.ctx, "demo", "probe")
        env = result["output"]
        self.assertEqual(Path(env["DEVTEAM_PROJECT_ROOT"]).resolve(), self.root.resolve())
        self.assertEqual(Path(env["cwd"]).resolve(), self.root.resolve())
        self.assertEqual(Path(env["DEVTEAM_PLUGIN_DIR"]).resolve(), (self.ctx.version_dir / "plugins" / "demo").resolve())
        self.assertEqual(Path(env["DEVTEAM_PLUGIN_SETTINGS"]).resolve(), self.settings_file().resolve())
        self.assertEqual(Path(env["DEVTEAM_STATE_DIR"]), project.state_dir(self.root, self.pid))
        config = json.loads(env["DEVTEAM_PLUGIN_CONFIG"])
        self.assertEqual(config["count"], 8)
        self.assertEqual(config["mode"], "fast")

    def test_a_script_escaping_the_plugin_directory_is_refused(self):
        outside = self.tmp / "outside.sh"
        outside.write_text("echo pwned\n", encoding="utf-8")
        plugin = self.ctx.plugin("demo")
        link = plugin.dir / "scripts" / "link.sh"
        link.symlink_to(outside)
        with self.assertRaises(EnvError):
            plugins._script_path(plugin, "scripts/link.sh")
        with self.assertRaises(EnvError):
            plugins._script_path(plugin, "scripts/missing.sh")

    def test_the_interpreter_is_fixed_by_the_cli_not_taken_from_the_file(self):
        manifest = copy.deepcopy(DEMO)
        manifest["actions"][0]["runtime"] = "/bin/evil"
        self.assertTrue(plugins.validate_manifest(manifest, dirname="demo"))


class UpgradeAndPathsTest(PluginTestCase):
    def test_plugin_settings_is_a_project_owned_record(self):
        from devteam import paths

        self.assertIn("plugin-settings", paths.PROJECT_OWNED_RECORDS)
        self.assertIn("graphify.json", paths.PROJECT_OWNED_RECORDS)

    def test_upgrade_leaves_the_settings_directory_in_the_project(self):
        from devteam import upgrade

        root = self.new_project("v2")
        memory = project.legacy_memory_dir(root)
        memory.mkdir(parents=True)
        (memory / "session-summary.md").write_text("## s\n", encoding="utf-8")
        result = bind.bind(root, provider_names=["claude"])
        self.assertEqual(project.layout(root), 1)
        ctx = plugins.Context(root, result["project_id"])
        plugins.enable(ctx, "graphify")
        target = root / project.PROJECT_DIR / plugins.SETTINGS_DIR / "graphify.json"
        before = target.read_text(encoding="utf-8")
        upgrade.apply(root)
        self.assertEqual(project.layout(root), project.CURRENT_LAYOUT)
        self.assertEqual(target.read_text(encoding="utf-8"), before)

    def test_plugins_is_a_runtime_tree_and_the_schema_number_is_declared(self):
        from devteam import compat

        self.assertIn("plugins", bind.RUNTIME_TREES)
        self.assertEqual(compat.store_schemas()["plugin_settings"], plugins.SCHEMA)

    def test_the_writing_commands_are_classified_as_mutating(self):
        from devteam import compat

        for path in (
            ("plugin", "enable"),
            ("plugin", "disable"),
            ("plugin", "config", "set"),
            ("plugin", "config", "unset"),
            ("plugin", "run"),
        ):
            self.assertEqual(compat.classify(path), "mutating", path)
        for path in (("plugin", "list"), ("plugin", "show"), ("plugin", "config", "get")):
            self.assertEqual(compat.classify(path), "read-only", path)

    def test_a_pinned_older_core_without_plugins_still_binds(self):
        import shutil

        self.install_version("3.1.0")
        shutil.rmtree(str(self.ctx.version_dir.parent / "3.1.0" / "plugins"))
        other = self.new_project("older")
        result = bind.bind(other, provider_names=["claude"], pin="3.1.0")
        self.assertFalse(os.path.lexists(str(other / project.PROJECT_DIR / "plugins")))
        self.assertEqual(result["version"], "3.1.0")


class HardeningTest(PluginTestCase):
    def write_legacy(self, content):
        legacy = project.legacy_memory_dir(self.root) / "graphify.json"
        legacy.parent.mkdir(parents=True, exist_ok=True)
        legacy.write_text(json.dumps(content), encoding="utf-8")
        return legacy

    # -- validation ---------------------------------------------------------------

    def test_a_trailing_newline_does_not_pass_a_pattern_check(self):
        manifest = copy.deepcopy(DEMO)
        manifest["actions"][0]["script"] = "scripts/detect.py\n"
        self.assertTrue(plugins.validate_manifest(manifest, dirname="demo"))
        self.assertTrue(plugins.validate_manifest(dict(DEMO, name="demo\n"), dirname="demo"))

    def test_a_huge_integer_or_deeply_nested_json_is_a_usage_error(self):
        code, body, _ = self.cli("config", "set", "demo", "count", "9" * 6000)
        self.assertEqual(code, 2)
        self.assertFalse(body["ok"])
        code, body, _ = self.cli("config", "set", "demo", "names", "[" * 200000)
        self.assertEqual(code, 2)
        self.assertFalse(body["ok"])

    def test_a_value_over_the_size_cap_is_a_usage_error(self):
        code, body, _ = self.cli("config", "set", "demo", "label", "x" * (plugins.MAX_VALUE_BYTES + 1))
        self.assertEqual(code, 2)
        self.assertFalse(self.settings_file().exists())

    def test_an_oversized_config_is_not_passed_inline(self):
        plugins.enable(self.ctx, "demo")
        plugins.config_set(self.ctx, "demo", "label", "x" * 40000)
        plugins.config_set(self.ctx, "demo", "names", json.dumps(["y" * 1000] * 40))
        env = plugins.run(self.ctx, "demo", "probe")["output"]
        self.assertIsNone(env["DEVTEAM_PLUGIN_CONFIG"])
        self.assertEqual(env["DEVTEAM_PLUGIN_CONFIG_TRUNCATED"], "1")
        self.assertEqual(
            json.loads(self.settings_file().read_text(encoding="utf-8"))["config"]["label"], "x" * 40000
        )

    def test_a_small_config_is_passed_inline_and_not_flagged(self):
        plugins.enable(self.ctx, "demo")
        env = plugins.run(self.ctx, "demo", "probe")["output"]
        self.assertIsNotNone(env["DEVTEAM_PLUGIN_CONFIG"])
        self.assertIsNone(env["DEVTEAM_PLUGIN_CONFIG_TRUNCATED"])

    # -- list surfaces invalid manifests -------------------------------------------

    def test_list_reports_an_invalid_manifest(self):
        broken = self.ctx.version_dir / "plugins" / "broken"
        broken.mkdir()
        (broken / "plugin.json").write_text("{not json", encoding="utf-8")
        code, body, _ = self.cli("list")
        self.assertEqual(code, 0)
        self.assertEqual([p["name"] for p in body["plugins"]], ["demo", "graphify", "needy"])
        self.assertEqual([i["name_or_dir"] for i in body["invalid"]], ["broken"])
        self.assertIn("cannot read manifest", body["invalid"][0]["problem"])
        code, out, _ = self.run_cli("plugin", "list", "--path", str(self.root))
        self.assertEqual(code, 0)
        self.assertIn("warning: invalid plugin manifest 'broken'", out)

    def test_list_has_an_empty_invalid_key_when_all_are_valid(self):
        _, body, _ = self.cli("list")
        self.assertEqual(body["invalid"], [])

    # -- locking --------------------------------------------------------------------

    def test_every_mutation_reads_and_writes_under_the_lock(self):
        events = []
        depth = {"n": 0}
        real_lock, real_read, real_write = plugins.store_lock, plugins.read_settings, plugins._write_body

        class Recording:
            def __init__(self, inner):
                self.inner = inner

            def __enter__(self):
                depth["n"] += 1
                return self.inner.__enter__()

            def __exit__(self, *exc):
                depth["n"] -= 1
                return self.inner.__exit__(*exc)

        plugins.store_lock = lambda name, **kw: Recording(real_lock(name, **kw))
        plugins.read_settings = lambda *a, **kw: (events.append(("read", depth["n"])), real_read(*a, **kw))[1]
        plugins._write_body = lambda *a, **kw: (events.append(("write", depth["n"])), real_write(*a, **kw))[1]
        self.addCleanup(setattr, plugins, "store_lock", real_lock)
        self.addCleanup(setattr, plugins, "read_settings", real_read)
        self.addCleanup(setattr, plugins, "_write_body", real_write)

        plugins.enable(self.ctx, "demo")
        plugins.config_set(self.ctx, "demo", "flag", "true")
        plugins.config_unset(self.ctx, "demo", "flag")
        plugins.disable(self.ctx, "demo")
        writes = [e for e in events if e[0] == "write"]
        self.assertGreaterEqual(len(writes), 4)
        self.assertTrue(all(depth_ == 1 for _, depth_ in writes), events)
        # The read that feeds each write happens inside the same lock: no write is
        # preceded only by unlocked reads.
        previous = None
        for kind, level in events:
            if kind == "write":
                self.assertEqual(previous, ("read", 1), events)
            previous = (kind, level)

    def test_concurrent_writers_do_not_lose_updates(self):
        plugins.enable(self.ctx, "demo")
        errors = []

        def work(key, values):
            try:
                for value in values:
                    plugins.config_set(self.ctx, "demo", key, value)
            except Exception as exc:  # noqa: BLE001
                errors.append(exc)

        threads = [
            threading.Thread(target=work, args=("label", ["a%d" % i for i in range(15)])),
            threading.Thread(target=work, args=("count", [str(i % 9 + 1) for i in range(15)])),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(errors, [])
        config = json.loads(self.settings_file().read_text(encoding="utf-8"))["config"]
        self.assertEqual(config["label"], "a14")
        self.assertEqual(config["count"], 6)

    # -- legacy move on write --------------------------------------------------------

    def test_config_set_on_a_legacy_plugin_completes_the_move(self):
        legacy = self.write_legacy({"targetPaths": ["src"], "extra": 1})
        plugins.config_set(self.ctx, "graphify", "auto_refresh", "true")
        self.assertFalse(legacy.exists())
        stored = json.loads(self.settings_file("graphify").read_text(encoding="utf-8"))
        self.assertEqual(
            stored,
            {"schema": 1, "enabled": True,
             "config": {"targetPaths": ["src"], "extra": 1, "auto_refresh": True}},
        )

    def test_config_unset_and_disable_on_a_legacy_plugin_complete_the_move(self):
        legacy = self.write_legacy({"targetPaths": ["src"], "auto_refresh": True})
        plugins.config_unset(self.ctx, "graphify", "auto_refresh")
        self.assertFalse(legacy.exists())
        self.assertEqual(
            json.loads(self.settings_file("graphify").read_text(encoding="utf-8"))["config"],
            {"targetPaths": ["src"]},
        )
        legacy = self.write_legacy({"targetPaths": ["lib"]})
        self.settings_file("graphify").unlink()
        plugins.disable(self.ctx, "graphify")
        self.assertFalse(legacy.exists())
        self.assertFalse(json.loads(self.settings_file("graphify").read_text(encoding="utf-8"))["enabled"])

    def test_a_no_op_write_leaves_the_legacy_file_alone(self):
        legacy = self.write_legacy({"targetPaths": ["src"]})
        plugins.config_unset(self.ctx, "graphify", "auto_refresh")  # declared, not stored
        self.assertTrue(legacy.exists())
        self.assertFalse(self.settings_file("graphify").exists())

    def test_identical_legacy_content_is_unlinked_silently(self):
        content = {"targetPaths": ["src"], "auto_refresh": True}
        legacy = self.write_legacy(content)
        settings = self.settings_file("graphify")
        settings.parent.mkdir(parents=True, exist_ok=True)
        settings.write_text(json.dumps({"schema": 1, "enabled": True, "config": content}), encoding="utf-8")
        report = plugins.migrate_legacy(self.root)
        self.assertEqual(report, {"moved": [], "skipped": []})
        self.assertFalse(legacy.exists())

    def test_different_legacy_content_is_still_a_conflict(self):
        legacy = self.write_legacy({"targetPaths": ["old"]})
        settings = self.settings_file("graphify")
        settings.parent.mkdir(parents=True, exist_ok=True)
        settings.write_text(json.dumps({"schema": 1, "enabled": True, "config": {"targetPaths": ["new"]}}))
        report = plugins.migrate_legacy(self.root)
        self.assertEqual(len(report["skipped"]), 1)
        self.assertTrue(legacy.exists())

    # -- process group ---------------------------------------------------------------

    @unittest.skipUnless(os.name == "posix", "process groups are POSIX")
    def test_sigterm_to_the_cli_kills_the_scripts_process_group(self):
        pid_file = self.root / ".hang.pid"
        proc = subprocess.Popen(
            [sys.executable, str(CLI), "plugin", "run", "demo", "hang", "--path", str(self.root), "--json"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=dict(os.environ),
        )
        self.addCleanup(proc.kill)
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline and not (pid_file.exists() and pid_file.read_text().strip()):
            time.sleep(0.05)
        script_pid = int(pid_file.read_text().strip())
        proc.send_signal(signal.SIGTERM)
        proc.communicate(timeout=15)
        self.assertNotEqual(proc.returncode, 0)
        gone = False
        for _ in range(60):
            try:
                os.kill(script_pid, 0)
            except ProcessLookupError:
                gone = True
                break
            time.sleep(0.1)
        self.assertTrue(gone, "the script outlived the CLI")

    @unittest.skipUnless(os.name == "posix", "process groups are POSIX")
    def test_a_timeout_returns_even_when_a_descendant_holds_the_pipe(self):
        started = time.monotonic()
        result = plugins.run(self.ctx, "demo", "leak")
        self.assertEqual(result["exit_code"], plugins.TIMEOUT_EXIT_CODE)
        self.assertFalse(result["ok"])
        self.assertLess(time.monotonic() - started, 6.5)


if __name__ == "__main__":
    unittest.main()