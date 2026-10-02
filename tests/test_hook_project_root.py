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
        spawns = re.findall(r"spawn\(\"bash\", bashArgs\(script\), \{([^}]*)\}", source)
        self.assertTrue(spawns, "the plugin no longer spawns its hooks with bash")
        for options in spawns:
            self.assertIn("cwd: directory", options)

    def test_the_opencode_plugin_heals_through_the_core_pointer(self):
        source = (REPO_ROOT / "opencode" / "plugin" / "dev-team-agents.ts").read_text(encoding="utf-8")
        self.assertIn('"core-dir"', source)
        self.assertIn('"self-heal.sh"', source)


class CodexCommandTest(unittest.TestCase):
    """`codex_hooks_merge.command_for`, the command `install-codex.sh` writes, per platform."""

    def _merge(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "codex_hooks_merge", REPO_ROOT / "scripts" / "lib" / "codex_hooks_merge.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_posix_gets_the_root_walk(self):
        merge = self._merge()
        self.assertEqual(merge.command_for(hooks.HOOK_DIR, "stop.sh", windows=False), _command("codex", "stop.sh"))

    def test_windows_walks_to_the_root_in_a_form_cmd_exe_can_parse(self):
        bash = "C:\\Program Files\\Git\\bin\\bash.exe"
        command = self._merge().command_for(hooks.HOOK_DIR, "stop.sh", windows=True, bash_path=bash)
        self.assertTrue(command.startswith('""' + bash + '" -c "'), command)
        self.assertTrue(command.endswith('""'), command)
        self.assertIn("pwd -P", command)
        self.assertNotIn("'", command)


@requires_bash()
class ClaudeCommandTest(unittest.TestCase):
    def test_the_v2_installer_writes_the_same_command_as_the_bind(self):
        text = (REPO_ROOT / "scripts" / "install.sh").read_text(encoding="utf-8")
        start = text.index("_HOOK_TEMPLATE=")
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


def _command(provider, script):
    """The command each provider registers, built from the one walk both share."""
    if provider == "claude":
        return hooks.command_for(script)
    return "env -u BASH_ENV -u ENV bash -c '{}'".format(hooks.ROOT_WALK.format(hooks=hooks.HOOK_DIR, pointer=hooks.CORE_POINTER, fallback=".", script=script))


@requires_bash()
class RootWalkTest(unittest.TestCase):
    """Where the command lands, on trees a bind does not build: nested roots, worktrees."""

    PROBE = 'pwd -P > "{out}/pwd"; cat > "{out}/stdin"; exit "${{PROBE_EXIT:-0}}"\n'

    def setUp(self):
        import tempfile
        self.tmp = Path(tempfile.mkdtemp(prefix="hook-root-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.out = self.tmp / "out"
        self.out.mkdir()

    def root(self, path):
        hooks_dir = path / hooks.HOOK_DIR
        hooks_dir.mkdir(parents=True)
        (hooks_dir / "probe.sh").write_text(self.PROBE.format(out=self.out), encoding="utf-8")
        return path

    def run_from(self, provider, cwd, env_extra=None, exit_code=0):
        env = dict(os.environ)
        env.pop("CLAUDE_PROJECT_DIR", None)
        env.update(env_extra or {})
        env["PROBE_EXIT"] = str(exit_code)
        cwd.mkdir(parents=True, exist_ok=True)
        result = subprocess.run(
            ["/bin/sh", "-c", _command(provider, "probe.sh")], cwd=str(cwd), input=b'{"x": 1}',
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, timeout=30, check=False,
        )
        ran_in = (self.out / "pwd").read_text(encoding="utf-8").strip() if (self.out / "pwd").exists() else None
        return result, ran_in

    def test_a_project_below_the_git_toplevel_is_found_from_its_subdirectory(self):
        outer = self.tmp / "monorepo"
        outer.mkdir()
        subprocess.run(["git", "init", "-q", str(outer)], check=True)
        package = self.root(outer / "packages" / "svc")
        for provider in ("claude", "codex"):
            with self.subTest(provider=provider):
                result, ran_in = self.run_from(provider, package / "src" / "deep")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(ran_in, str(package.resolve()))

    def test_a_worktree_without_hooks_runs_them_from_the_checkout_holding_it(self):
        main = self.root(self.tmp / "main")
        worktree = main / ".worktrees" / "feat" / "x"
        (worktree / ".dev-team-agents").mkdir(parents=True)  # a partial one: no hooks
        for provider in ("claude", "codex"):
            with self.subTest(provider=provider):
                _result, ran_in = self.run_from(provider, worktree / "apps" / "api")
                self.assertEqual(ran_in, str(main.resolve()))

    def test_a_worktree_with_its_own_hooks_runs_them_there(self):
        self.root(self.tmp / "main")
        worktree = self.root(self.tmp / "main" / ".worktrees" / "y")
        for provider in ("claude", "codex"):
            with self.subTest(provider=provider):
                _result, ran_in = self.run_from(provider, worktree / "apps")
                self.assertEqual(ran_in, str(worktree.resolve()))

    def test_claude_falls_back_to_the_project_dir_when_no_ancestor_has_hooks(self):
        root = self.root(self.tmp / "opened-here")
        elsewhere = self.tmp / "elsewhere"
        result, ran_in = self.run_from("claude", elsewhere, {"CLAUDE_PROJECT_DIR": str(root)})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(ran_in, str(root.resolve()))

    def test_a_directory_entered_through_a_symlink_finds_the_real_root(self):
        root = self.root(self.tmp / "proj")
        (root / "apps" / "api").mkdir(parents=True)
        link = self.tmp / "shortcut"
        link.symlink_to(root / "apps" / "api")
        for provider in ("claude", "codex"):
            with self.subTest(provider=provider):
                env = dict(os.environ, PROBE_EXIT="0")
                env.pop("CLAUDE_PROJECT_DIR", None)
                # `cd` through the link so the logical $PWD is the link, not the target.
                subprocess.run(
                    ["/bin/sh", "-c", 'cd "{}" && {}'.format(link, _command(provider, "probe.sh"))],
                    input=b"", stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, timeout=30, check=True,
                )
                self.assertEqual((self.out / "pwd").read_text(encoding="utf-8").strip(), str(root.resolve()))

    def test_stdin_and_a_blocking_exit_reach_the_provider(self):
        root = self.root(self.tmp / "proj")
        for provider in ("claude", "codex"):
            with self.subTest(provider=provider):
                result, _ran_in = self.run_from(provider, root / "a", exit_code=2)
                # PreToolUse exit 2 is how the credential guard blocks a call.
                self.assertEqual(result.returncode, 2)
                self.assertEqual((self.out / "stdin").read_text(encoding="utf-8"), '{"x": 1}')


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
            self.assertEqual(command, _command(provider, "pre-tool-use.sh"))
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


@requires_bash()
class SelfHealTest(HookFromSubdirectoryTest):
    """`.dev-team-agents/scripts` deleted under a bound project (a `git rebase` onto a commit that
    still vendored it does exactly that): the next hook re-binds and runs, on every provider that
    registers a command. opencode's plugin is covered by `tests/js/opencode-plugin.test.mjs`."""

    def _break(self, root):
        link = root / ".dev-team-agents" / "scripts"
        if link.is_symlink() or link.is_file():
            link.unlink()
        else:
            shutil.rmtree(str(link))
        self.assertTrue((root / hooks.CORE_POINTER).is_file())

    def _env(self, case, root):
        env = dict(os.environ)
        env.pop("CLAUDE_PROJECT_DIR", None)
        if case["env"]:
            env[case["env"]] = str(root)
        return env

    def test_bind_writes_the_core_pointer(self):
        root, _ = self._bound("claude")
        self.assertEqual((root / hooks.CORE_POINTER).read_text(encoding="utf-8").strip(), Path(paths_core()).as_posix())

    def test_the_next_hook_restores_the_link_and_reaches_the_board(self):
        for provider, case in CASES.items():
            if case is None:
                continue
            if provider in providers.DELEGATED_INSTALLERS and shutil.which("python3") is None:
                continue
            with self.subTest(provider=provider):
                root, project_id = self._bound(provider)
                command = case["command"](root)
                self._break(root)
                session = "heal-" + provider
                result = self._run("/bin/sh", command, root / SUBDIR, case["spawn"](session), self._env(case, root))
                self.assertEqual(result.returncode, 0, result.stderr.decode("utf-8", "replace"))
                self.assertTrue((root / hooks.HOOK_DIR / "pre-tool-use.sh").is_file())
                (task,) = self._agents(root, project_id, session)
                self.assertEqual(task["agent_type"], AGENT)

    @unittest.skipIf(hasattr(os, "geteuid") and os.geteuid() == 0, "root ignores the read-only directory")
    def test_when_the_rebind_fails_the_hooks_run_from_the_store_and_say_so(self):
        for provider, case in CASES.items():
            if case is None:
                continue
            if provider in providers.DELEGATED_INSTALLERS and shutil.which("python3") is None:
                continue
            with self.subTest(provider=provider):
                root, project_id = self._bound(provider)
                command = case["command"](root)
                self._break(root)
                project_dir = root / ".dev-team-agents"
                project_dir.chmod(0o555)  # the re-bind cannot write the link back
                self.addCleanup(project_dir.chmod, 0o755)
                session = "store-" + provider
                result = self._run("/bin/sh", command, root, case["spawn"](session), self._env(case, root))
                project_dir.chmod(0o755)
                self.assertEqual(result.returncode, 0, result.stderr.decode("utf-8", "replace"))
                self.assertIn(b"running the hooks from the store", result.stderr)
                (task,) = self._agents(root, project_id, session)
                self.assertEqual(task["agent_type"], AGENT)

    def test_an_unbound_tree_without_the_pointer_behaves_as_before(self):
        root, _ = self._bound("claude")
        self._break(root)
        (root / hooks.CORE_POINTER).unlink()
        result = self._run("/bin/sh", _claude_command(root), root, _claude_spawn("none"), self._env(CASES["claude"], root))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b"No such file", result.stderr)


def paths_core():
    from devteam import paths

    return paths.core_dir()


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

    def test_wire_rewrites_only_our_command_and_keeps_siblings_and_keys(self):
        root = self.tmp / "siblings"
        (root / ".claude").mkdir(parents=True)
        settings = root / hooks.SETTINGS_FILE
        ours = {"type": "command", "command": self.OLD.format("stop.sh"), "timeout": 5}
        sibling = {"type": "command", "command": "./mine.sh"}
        settings.write_text(json.dumps({"hooks": {"Stop": [{"hooks": [ours, sibling]}]}}), encoding="utf-8")
        hooks.wire(root)
        (stop,) = json.loads(settings.read_text(encoding="utf-8"))["hooks"]["Stop"]
        self.assertEqual(stop["hooks"], [dict(ours, command=hooks.command_for("stop.sh")), sibling])

    @requires_bash()
    def test_the_v2_installer_rewrites_the_relative_command_and_keeps_the_rest(self):
        text = (REPO_ROOT / "scripts" / "install.sh").read_text(encoding="utf-8")
        functions = text[text.index("_HOOK_TEMPLATE="):text.index("\nif [ ! -f \"$SETTINGS_FILE\" ]")]
        start = text.index("    # An entry written before the command found the project root")
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
