"""Delivery of PostToolUse hints per provider, the widened matchers, and the opencode exit code.

ADR-0047 (delivery), ADR-0050 (repair ledger), ADR-0051 (branch overlap). The shared
emit-now-or-queue step lives in `devteam_hints_deliver` (scripts/hooks/lib/context-hints.sh).
"""

import json
import os
import subprocess
import unittest

from devteam_support import REPO_ROOT, StoreTestCase, make_git_project, requires_bash

import codex_hooks_merge
from devteam import branch_overlap, hooks, providers, repairs

LIB = REPO_ROOT / "scripts" / "hooks" / "lib" / "context-hints.sh"
POST_TOOL_USE = REPO_ROOT / "scripts" / "hooks" / "post-tool-use.sh"

#: How a PostToolUse hint reaches the model, per provider. Fails when a provider is added
#: without a case. `payload` is the hook payload shape that provider sends.
POST_TOOL_USE_DELIVERY = {
    "claude": ("now", {"hook_event_name": "PostToolUse", "session_id": "s1", "tool_name": "Bash"}),
    "codex": ("now", {"hook_event_name": "PostToolUse", "session_id": "s1", "tool_name": "Bash"}),
    "opencode": ("queued", {"sessionID": "s1", "tool": "bash"}),
}

#: The shell and edit tool names each provider reports, as the sub-scripts and matchers must see them.
EDIT_TOOLS = {"claude": "Edit", "codex": "apply_patch", "opencode": "edit"}


class DeliveryMapTest(unittest.TestCase):
    def test_every_provider_has_a_delivery_case(self):
        self.assertEqual(set(POST_TOOL_USE_DELIVERY), set(providers.ALL_PROVIDERS))
        self.assertEqual(set(EDIT_TOOLS), set(providers.ALL_PROVIDERS))


@requires_bash()
class HintDeliveryTest(StoreTestCase):
    def setUp(self):
        super().setUp()
        self.repo = make_git_project(self.tmp / "app")
        self.state = self.tmp / "state"
        self.state.mkdir()

    def deliver(self, payload, lines="first hint\nsecond \"quoted\" hint"):
        script = '. "{}"; devteam_hints_init || exit 9; devteam_hints_deliver s1 "$PAYLOAD" "$LINES"'.format(LIB)
        env = {"PATH": os.environ["PATH"], "HOME": str(self.tmp), "USER_DATA_DIR": str(self.state),
               "PAYLOAD": json.dumps(payload), "LINES": lines}
        result = subprocess.run(["bash", "-c", script], cwd=str(self.repo), env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def test_each_provider_gets_its_delivery(self):
        for provider, (mode, payload) in POST_TOOL_USE_DELIVERY.items():
            with self.subTest(provider=provider):
                for leftover in self.state.glob(".context-*"):
                    leftover.unlink()
                out = self.deliver(payload)
                if mode == "now":
                    data = json.loads(out)["hookSpecificOutput"]
                    self.assertEqual(data["hookEventName"], "PostToolUse")
                    self.assertEqual(
                        data["additionalContext"],
                        '[DEVTEAM:HINT] first hint\n[DEVTEAM:HINT] second "quoted" hint\n',
                    )
                    self.assertFalse((self.state / ".context-hints-s1").exists())
                else:
                    self.assertEqual(out, "")
                    self.assertEqual((self.state / ".context-hints-s1").read_text().splitlines(),
                                     ["first hint", 'second "quoted" hint'])

    def test_a_failure_event_is_answered_with_the_failure_event_name(self):
        out = self.deliver({"hook_event_name": "PostToolUseFailure", "session_id": "s1"}, "h")
        self.assertEqual(json.loads(out)["hookSpecificOutput"]["hookEventName"], "PostToolUseFailure")

    def test_a_hint_is_emitted_once_per_session(self):
        payload = {"hook_event_name": "PostToolUse", "session_id": "s1"}
        self.assertTrue(self.deliver(payload, "same"))
        self.assertEqual(self.deliver(payload, "same"), "")


class MatcherTest(unittest.TestCase):
    def test_claude_matcher_reaches_shell_and_edit_tools(self):
        tools = hooks.MATCHERS["PostToolUse"].split("|")
        for tool in ("Bash", "Edit", "MultiEdit", "Write", "NotebookEdit"):
            self.assertIn(tool, tools)

    def test_the_previous_claude_matcher_is_rewritten_in_place(self):
        self.assertIn(
            "TodoWrite|TaskCreate|TaskUpdate|Agent|Task|Bash|mcp__.*create_pull_request|mcp__.*merge_pull_request",
            hooks.PREVIOUS_MATCHERS["PostToolUse"],
        )
        self.assertNotIn(hooks.MATCHERS["PostToolUse"], hooks.PREVIOUS_MATCHERS["PostToolUse"])

    def test_codex_matcher_reaches_its_shell_and_patch_tools(self):
        import re

        pattern = re.compile(codex_hooks_merge.MATCHERS["PostToolUse"])
        for tool in ("Bash", "apply_patch", "spawn_agent", "wait_agent", "close_agent"):
            self.assertTrue(pattern.fullmatch(tool) or pattern.search(tool), tool)

    def test_install_sh_ships_the_same_claude_matcher(self):
        text = (REPO_ROOT / "scripts" / "install.sh").read_text(encoding="utf-8")
        self.assertGreaterEqual(text.count(hooks.MATCHERS["PostToolUse"]), 3)


class ExitCodeTest(unittest.TestCase):
    def test_the_opencode_payload_exit_code_is_read(self):
        failed = {"sessionID": "s", "tool": "bash", "args": {"command": "npm test"}, "exit_code": 1, "output": "ok-looking"}
        passed = dict(failed, exit_code=0)
        self.assertEqual(repairs.classify(failed)[0], False)
        self.assertEqual(repairs.classify(passed)[0], True)


@requires_bash()
class DispatcherLatencyTest(StoreTestCase):
    """A no-op shell or edit payload never reaches python: every sub-script leaves in bash."""

    def test_no_subscript_forks_python_for_a_plain_shell_call(self):
        fake = self.tmp / "bin"
        fake.mkdir()
        marker = self.tmp / "python-ran"
        stub = fake / "python3"
        stub.write_text('#!/bin/sh\necho "$@" >> "{}"\nexit 0\n'.format(marker))
        stub.chmod(0o755)
        repo = make_git_project(self.tmp / "app")
        for payload in (
            {"hook_event_name": "PostToolUse", "session_id": "s1", "tool_name": "Bash", "tool_input": {"command": "ls"},
             "tool_response": {"stdout": "a", "exit_code": 0}},
            {"hook_event_name": "PostToolUse", "session_id": "s1", "tool_name": "Edit", "tool_input": {"file_path": "x.py"}},
        ):
            env = {"PATH": "{}:{}".format(fake, os.environ["PATH"]), "HOME": str(self.tmp), "DEVTEAM_PY_STUB": "1"}
            subprocess.run(["bash", str(POST_TOOL_USE)], input=json.dumps(payload), cwd=str(repo), env=env,
                           capture_output=True, text=True)
        self.assertFalse(marker.exists(), marker.read_text() if marker.exists() else "")


@requires_bash()
class RepairGateTest(StoreTestCase):
    """03-repair-detect.sh decides from the payload and a $TMPDIR sentinel before any state lookup."""

    def setUp(self):
        super().setUp()
        self.repo = make_git_project(self.tmp / "app")
        self.state = self.tmp / "state"
        self.state.mkdir()
        self.bin = self.tmp / "bin"
        self.bin.mkdir()
        self.marker = self.tmp / "python-ran"
        stub = self.bin / "python3"
        stub.write_text('#!/bin/sh\necho ran >> "{}"\nexit 0\n'.format(self.marker))
        stub.chmod(0o755)
        self.tmpdir = self.tmp / "tmpdir"
        self.tmpdir.mkdir()

    def run_hook(self, response):
        payload = {"hook_event_name": "PostToolUse", "session_id": "s1", "tool_name": "Bash",
                   "tool_input": {"command": "make build"}, "tool_response": response}
        env = {"PATH": "{}:{}".format(self.bin, os.environ["PATH"]), "HOME": str(self.tmp),
               "USER_DATA_DIR": str(self.state), "TMPDIR": str(self.tmpdir)}
        subprocess.run(["bash", str(REPO_ROOT / "scripts/hooks/post-tool-use/03-repair-detect.sh")],
                       input=json.dumps(payload), cwd=str(self.repo), env=env, capture_output=True, text=True)
        return self.marker.exists()

    def test_a_successful_call_with_no_open_window_forks_nothing(self):
        self.assertFalse(self.run_hook({"stdout": "ok", "exit_code": 0}))

    def test_a_failure_takes_the_slow_path(self):
        self.assertTrue(self.run_hook({"stderr": "boom", "exit_code": 2}))

    def test_an_open_window_sentinel_takes_the_slow_path(self):
        (self.tmpdir / "devteam-repair-open-s1").write_text("")
        self.assertTrue(self.run_hook({"stdout": "ok", "exit_code": 0}))


@requires_bash()
class OverlapGateTest(StoreTestCase):
    """04-branch-overlap.sh leaves in bash unless a refresher sentinel says some cache holds a branch."""

    def setUp(self):
        super().setUp()
        self.repo = make_git_project(self.tmp / "app")
        self.state = self.tmp / "state"
        self.state.mkdir()
        (self.state / ".branch-overlap.json").write_text('{"base": "refs/remotes/origin/main", "branches": []}')
        self.bin = self.tmp / "bin"
        self.bin.mkdir()
        self.marker = self.tmp / "python-ran"
        stub = self.bin / "python3"
        stub.write_text('#!/bin/sh\necho ran >> "{}"\nexit 0\n'.format(self.marker))
        stub.chmod(0o755)
        self.tmpdir = self.tmp / "tmpdir"
        self.tmpdir.mkdir()

    def run_hook(self, tool="Edit"):
        payload = {"hook_event_name": "PostToolUse", "session_id": "s1", "tool_name": tool,
                   "tool_input": {"file_path": "x.py"}}
        env = {"PATH": "{}:{}".format(self.bin, os.environ["PATH"]), "HOME": str(self.tmp),
               "USER_DATA_DIR": str(self.state), "TMPDIR": str(self.tmpdir)}
        subprocess.run(["bash", str(REPO_ROOT / "scripts/hooks/post-tool-use/04-branch-overlap.sh")],
                       input=json.dumps(payload), cwd=str(self.repo), env=env, capture_output=True, text=True)
        return self.marker.exists()

    def test_no_sentinel_means_nothing_is_resolved_or_forked(self):
        self.assertFalse(self.run_hook())

    def test_a_sentinel_lets_the_hook_compare_hunks(self):
        directory = self.tmpdir / "devteam-branch-overlap"
        directory.mkdir()
        (directory / "k").write_text("")
        self.assertTrue(self.run_hook())

    def test_the_refresher_sentinel_follows_the_cache_contents(self):
        old = os.environ.get("TMPDIR")
        os.environ["TMPDIR"] = str(self.tmpdir)
        self.addCleanup(lambda: os.environ.__setitem__("TMPDIR", old) if old is not None else os.environ.pop("TMPDIR", None))
        directory = self.tmpdir / "devteam-branch-overlap"
        branch_overlap._set_sentinel(str(self.state), True)
        self.assertEqual(len(list(directory.iterdir())), 1)
        branch_overlap._set_sentinel(str(self.state), False)
        self.assertEqual(list(directory.iterdir()), [])


class RepairSentinelTest(StoreTestCase):
    def test_the_sentinel_follows_the_window(self):
        state = self.tmp / "state"
        state.mkdir()
        tmpdir = self.tmp / "tmpdir"
        tmpdir.mkdir()
        old = os.environ.get("TMPDIR")
        os.environ["TMPDIR"] = str(tmpdir)
        self.addCleanup(lambda: os.environ.__setitem__("TMPDIR", old) if old is not None else os.environ.pop("TMPDIR", None))
        sentinel = tmpdir / "devteam-repair-open-s1"
        fail = {"tool_name": "Bash", "tool_input": {"command": "make build"}, "tool_response": {"exit_code": 2, "stderr": "x"}}
        ok = {"tool_name": "Bash", "tool_input": {"command": "make build"}, "tool_response": {"exit_code": 0, "stdout": "y"}}
        repairs.process(str(state), "s1", fail)
        self.assertTrue(sentinel.exists())
        repairs.process(str(state), "s1", ok)
        self.assertFalse(sentinel.exists())


class BaseRefFallbackTest(StoreTestCase):
    def test_a_missing_origin_head_is_resolved_from_the_remote(self):
        remote = self.tmp / "remote.git"
        subprocess.run(["git", "init", "--bare", "-b", "trunk", str(remote)], check=True, capture_output=True)
        repo = make_git_project(self.tmp / "app")
        git = lambda *a: subprocess.run(["git", "-C", str(repo)] + list(a), check=True, capture_output=True, text=True)
        git("branch", "-M", "trunk")
        git("remote", "add", "origin", str(remote))
        git("push", "-q", "origin", "trunk")
        git("fetch", "-q", "origin")
        subprocess.run(["git", "-C", str(repo), "remote", "set-head", "origin", "-d"], capture_output=True)
        sym = subprocess.run(["git", "-C", str(repo), "symbolic-ref", "--quiet", "refs/remotes/origin/HEAD"],
                             capture_output=True)
        self.assertNotEqual(sym.returncode, 0)

        self.assertEqual(branch_overlap._base_ref(str(repo)), "refs/remotes/origin/trunk")
        # The fallback answer stays in memory: the user's remote HEAD is not recorded.
        self.assertNotEqual(subprocess.run(["git", "-C", str(repo), "symbolic-ref", "--quiet", "refs/remotes/origin/HEAD"],
                                           capture_output=True).returncode, 0)


if __name__ == "__main__":
    unittest.main()
