"""Every hook runs from the project root, whatever directory the session is in.

A provider runs a hook in the session's CURRENT directory. A Claude Code session keeps the
directory a Bash call `cd`-ed into, and Codex may be started in a subdirectory; with a relative
command every hook then failed as a "non-blocking error" — the task board stayed empty and the
credential guard did not run. These tests drive the real registered command from a subdirectory,
through the real dispatcher and CLI, on every provider.
"""

import json
import os
import re
import shutil
import subprocess
import unittest
from pathlib import Path

from devteam_support import REPO_ROOT, StoreTestCase, requires_bash

from devteam import bind, hooks, providers, tasks, versions

SUBDIR = Path("apps") / "api"
AGENT = "backend-developer"


def _claude_spawn(session):
    return {
        "session_id": session, "cwd": "", "tool_use_id": "c1", "hook_event_name": "PreToolUse",
        "tool_name": "Agent",
        "tool_input": {"description": "add the endpoint", "prompt": "p", "subagent_type": AGENT},
    }


def _codex_spawn(session):
    return {
        "session_id": session, "cwd": "", "tool_use_id": "c1", "hook_event_name": "PreToolUse",
        "tool_name": "spawn_agent", "tool_input": {"agent_type": AGENT, "message": "add the endpoint"},
    }


def _claude_command(root):
    settings = json.loads((root / hooks.SETTINGS_FILE).read_text(encoding="utf-8"))
    return settings["hooks"]["PreToolUse"][0]["hooks"][0]["command"]


def _codex_command(root):
    data = json.loads((root / providers.CODEX_HOOKS_FILE).read_text(encoding="utf-8"))
    return data["hooks"]["PreToolUse"][0]["hooks"][0]["command"]


#: How each provider reaches its hooks. A registered command is run from a subdirectory; opencode
#: registers none — its plugin spawns the dispatcher itself — so its case is the plugin's `cwd`.
#: One entry per provider in `providers.ALL_PROVIDERS`: a provider added without a case fails
#: `test_every_provider_has_its_hook_root_decided`.
CASES = {
    "claude": {"command": _claude_command, "spawn": _claude_spawn, "env": "CLAUDE_PROJECT_DIR"},
    "codex": {"command": _codex_command, "spawn": _codex_spawn, "env": None},
    "opencode": None,
}

#: The shells a provider may run a hook command through: Claude Code uses `/bin/sh`, Codex the
#: user's `$SHELL`. Each one present on this machine is exercised.
SHELLS = [shell for shell in ("/bin/sh", "bash", "zsh", "fish") if shutil.which(shell)]


class ProviderParityTest(unittest.TestCase):
    def test_every_provider_has_its_hook_root_decided(self):
        self.assertEqual(set(CASES), set(providers.ALL_PROVIDERS))

    def test_the_opencode_plugin_runs_its_hooks_from_the_project_directory(self):
        source = (REPO_ROOT / "opencode" / "plugin" / "dev-team-agents.ts").read_text(encoding="utf-8")
        spawns = re.findall(r"spawn\(\"bash\", \[script\], \{([^}]*)\}", source)
        self.assertTrue(spawns, "the plugin no longer spawns its hooks with bash")
        for options in spawns:
            self.assertIn("cwd: directory", options)


class ClaudeCommandTest(unittest.TestCase):
    def test_the_v2_installer_writes_the_same_command_as_the_bind(self):
        text = (REPO_ROOT / "scripts" / "install.sh").read_text(encoding="utf-8")
        start = text.index("_hook_cmd() {")
        end = text.index("\nPRE_TOOL_USE_HOOK=", start)
        functions = text[start:end]
        for _event, script in hooks.EVENTS:
            with self.subTest(script=script):
                shell = functions + '\nc="$(_hook_cmd ' + script + ')"\nprintf "%s\\n" "$c"\nprintf "%s" "$(_json_str "$c")"\n'
                out = subprocess.run(["bash", "-c", shell], stdout=subprocess.PIPE, check=True, text=True).stdout
                command, escaped = out.split("\n", 1)
                self.assertEqual(command, hooks.command_for(script))
                self.assertEqual(json.loads('"' + escaped + '"'), command)

    def test_the_command_stays_relative(self):
        for _event, script in hooks.EVENTS:
            command = hooks.command_for(script)
            self.assertNotIn(str(REPO_ROOT), command)
            self.assertIn("{}/{}".format(hooks.HOOK_DIR, script), command)


@requires_bash()
class HookFromSubdirectoryTest(StoreTestCase):
    def setUp(self):
        super().setUp()
        # The real hooks and installers: a stub tree would prove only the stub.
        versions.install_from_tree(REPO_ROOT, version="9.9.9", force=True, make_current=True)
        # The Codex installer looks at ~/.codex/prompts; keep it off the real home.
        home = os.environ.get("HOME")
        os.environ["HOME"] = str(self.tmp / "fake-home")
        (self.tmp / "fake-home").mkdir()
        self.addCleanup(lambda: os.environ.__setitem__("HOME", home) if home else os.environ.pop("HOME", None))

    def _bound(self, provider):
        root = self.new_project("root-" + provider)
        project_id = bind.bind(root, provider_names=[provider], mode="link")["project_id"]
        Path(tasks.tasks_dir(root, project_id)).parent.mkdir(parents=True, exist_ok=True)
        (root / SUBDIR).mkdir(parents=True)
        return root, project_id

    def _run(self, shell, command, cwd, payload, env):
        return subprocess.run(
            [shell, "-c", command], cwd=str(cwd), input=json.dumps(payload).encode("utf-8"),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, timeout=60, check=False,
        )

    def _agents(self, root, project_id, session):
        path = Path(tasks.tasks_dir(root, project_id)) / (session + ".json")
        if not path.exists():
            return []
        return [t for t in json.loads(path.read_text(encoding="utf-8"))["tasks"] if t.get("kind") == "agent"]

    def test_a_spawn_from_a_subdirectory_reaches_the_board(self):
        for provider, case in CASES.items():
            if case is None:
                continue
            if provider in providers.DELEGATED_INSTALLERS and shutil.which("python3") is None:
                continue
            root, project_id = self._bound(provider)
            command = case["command"](root)
            for shell in SHELLS:
                with self.subTest(provider=provider, shell=shell):
                    session = "s-{}-{}".format(provider, Path(shell).name)
                    env = dict(os.environ)
                    env.pop("CLAUDE_PROJECT_DIR", None)
                    if case["env"]:
                        env[case["env"]] = str(root)
                    result = self._run(shell, command, root / SUBDIR, case["spawn"](session), env)
                    self.assertEqual(result.returncode, 0, result.stderr.decode("utf-8", "replace"))
                    (task,) = self._agents(root, project_id, session)
                    self.assertEqual(task["agent_type"], AGENT)

    def test_claude_without_the_variable_still_runs_from_the_root(self):
        root, project_id = self._bound("claude")
        env = dict(os.environ)
        env.pop("CLAUDE_PROJECT_DIR", None)
        result = self._run("/bin/sh", _claude_command(root), root, _claude_spawn("s-plain"), env)
        self.assertEqual(result.returncode, 0, result.stderr.decode("utf-8", "replace"))
        self.assertEqual(len(self._agents(root, project_id, "s-plain")), 1)


class RewriteTest(StoreTestCase):
    """A project wired with the relative command is fixed by the next sync, in place."""

    OLD = "env -u BASH_ENV -u ENV .dev-team-agents/scripts/hooks/{}"
    THIRD_PARTY = {"matcher": "Bash", "hooks": [{"type": "command", "command": "./my-own-hook.sh"}]}

    def test_wire_rewrites_the_relative_command_and_keeps_the_rest(self):
        root = self.tmp / "wired"
        (root / ".claude").mkdir(parents=True)
        settings = root / hooks.SETTINGS_FILE
        settings.write_text(json.dumps({"hooks": {
            "PreToolUse": [
                {"matcher": "Edit|Write", "hooks": [{"type": "command", "command": self.OLD.format("pre-tool-use.sh")}]},
                self.THIRD_PARTY,
            ],
            "Stop": [{"hooks": [{"type": "command", "command": self.OLD.format("stop.sh")}]}],
        }}), encoding="utf-8")
        hooks.wire(root)
        data = json.loads(settings.read_text(encoding="utf-8"))
        pre = data["hooks"]["PreToolUse"]
        self.assertEqual(len(pre), 2)
        self.assertEqual(pre[0]["hooks"][0]["command"], hooks.command_for("pre-tool-use.sh"))
        self.assertEqual(pre[0]["matcher"], "Edit|Write")
        self.assertEqual(pre[1], self.THIRD_PARTY)
        (stop,) = data["hooks"]["Stop"]
        self.assertEqual(stop["hooks"][0]["command"], hooks.command_for("stop.sh"))


    def test_the_v2_installer_rewrites_the_relative_command_and_keeps_the_rest(self):
        text = (REPO_ROOT / "scripts" / "install.sh").read_text(encoding="utf-8")
        functions = text[text.index("_hook_cmd() {"):text.index("\nif [ ! -f \"$SETTINGS_FILE\" ]")]
        start = text.index("    # An entry written before the command entered the project root")
        end = text.index("PYEOF\n    fi\n", start) + len("PYEOF\n    fi\n")
        settings = self.tmp / "settings.json"
        settings.write_text(json.dumps({"hooks": {
            "PreToolUse": [
                {"matcher": "Edit|Write", "hooks": [{"type": "command", "command": self.OLD.format("pre-tool-use.sh")}]},
                self.THIRD_PARTY,
            ],
            "PostToolUse": [{"matcher": "X", "hooks": [{"type": "command", "command": self.OLD.format("post-tool-use.sh")}]}],
        }}), encoding="utf-8")
        script = 'SETTINGS_FILE="{}"\n{}\n{}'.format(settings, functions, text[start:end])
        subprocess.run(["bash", "-c", script], stdout=subprocess.PIPE, check=True)
        data = json.loads(settings.read_text(encoding="utf-8"))
        pre = data["hooks"]["PreToolUse"]
        self.assertEqual(pre[0]["hooks"][0]["command"], hooks.command_for("pre-tool-use.sh"))
        self.assertEqual(pre[0]["matcher"], "Edit|Write")
        self.assertEqual(pre[1], self.THIRD_PARTY)
        post = data["hooks"]["PostToolUse"][0]
        self.assertEqual((post["matcher"], post["hooks"][0]["command"]), ("X", hooks.command_for("post-tool-use.sh")))


if __name__ == "__main__":
    unittest.main()
