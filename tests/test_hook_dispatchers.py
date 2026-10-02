"""Hook dispatchers and the PreToolUse guards, across every provider's payload shape.

Dispatchers: a refusal (exit 2) must survive another sub-script's exit 1, and a Stop block must
not repeat once Claude Code reports ``stop_hook_active``. Guards: each provider spells the same
Bash call differently, and a guard that only knows one spelling silently stops guarding.
"""

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from devteam_support import REPO_ROOT, requires_bash
from devteam.providers import ALL_PROVIDERS

HOOKS = REPO_ROOT / "scripts" / "hooks"
CRED = "credentials.local.json"

DISPATCHERS = {
    "pre-tool-use.sh": "pre-tool-use",
    "post-tool-use.sh": "post-tool-use",
    "user-prompt-submit.sh": "user-prompt-submit",
    "stop.sh": "stop",
}


def _stub(path, code, message=""):
    path.parent.mkdir(parents=True, exist_ok=True)
    body = "#!/usr/bin/env bash\ncat >/dev/null || true\n"
    if message:
        body += f"echo '{message}' >&2\n"
    path.write_text(body + f"exit {code}\n")


@requires_bash()
class DispatcherTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.hooks = self.tmp / "hooks"
        self.hooks.mkdir()
        for name in DISPATCHERS:
            shutil.copy(HOOKS / name, self.hooks / name)
        self.work = self.tmp / "work"
        self.work.mkdir()

    def run_dispatcher(self, name, codes, payload="{}"):
        sub = self.hooks / DISPATCHERS[name]
        for i, code in enumerate(codes, 1):
            _stub(sub / f"0{i}-s.sh", code, f"msg-{i}" if code else "")
        return subprocess.run(
            ["bash", str(self.hooks / name)], input=payload, capture_output=True, text=True, cwd=self.work
        )

    def test_exit_2_wins_over_an_earlier_exit_1(self):
        for name in DISPATCHERS:
            with self.subTest(dispatcher=name):
                for sub in (self.hooks / DISPATCHERS[name],):
                    shutil.rmtree(sub, ignore_errors=True)
                self.assertEqual(self.run_dispatcher(name, [1, 2, 1]).returncode, 2)

    def test_exit_2_first_is_kept(self):
        for name in DISPATCHERS:
            with self.subTest(dispatcher=name):
                shutil.rmtree(self.hooks / DISPATCHERS[name], ignore_errors=True)
                self.assertEqual(self.run_dispatcher(name, [2, 1]).returncode, 2)

    def test_first_non_zero_wins_when_there_is_no_refusal(self):
        for name in DISPATCHERS:
            with self.subTest(dispatcher=name):
                shutil.rmtree(self.hooks / DISPATCHERS[name], ignore_errors=True)
                self.assertEqual(self.run_dispatcher(name, [0, 3, 1]).returncode, 3)

    def test_all_zero_is_zero(self):
        shutil.rmtree(self.hooks / "stop", ignore_errors=True)
        self.assertEqual(self.run_dispatcher("stop.sh", [0, 0]).returncode, 0)

    def test_stop_blocks_without_stop_hook_active(self):
        for payload in ("{}", '{"stop_hook_active": false}'):
            with self.subTest(payload=payload):
                shutil.rmtree(self.hooks / "stop", ignore_errors=True)
                result = self.run_dispatcher("stop.sh", [2], payload)
                self.assertEqual(result.returncode, 2)

    def test_stop_hook_active_reports_but_does_not_block_again(self):
        for payload in ('{"stop_hook_active": true}', '{"stop_hook_active":true,"session_id":"s"}'):
            with self.subTest(payload=payload):
                shutil.rmtree(self.hooks / "stop", ignore_errors=True)
                result = self.run_dispatcher("stop.sh", [1, 2], payload)
                self.assertEqual(result.returncode, 0)
                self.assertIn("msg-2", result.stderr)

    def test_stop_hook_active_does_not_hide_other_failures(self):
        result = self.run_dispatcher("stop.sh", [1], '{"stop_hook_active": true}')
        self.assertEqual(result.returncode, 1)

    def test_stop_payload_temp_file_honours_tmpdir(self):
        self.assertIn('"${TMPDIR:-/tmp}/devteam-stop-payload', (HOOKS / "stop.sh").read_text())


def _payload(provider, command):
    """The Bash call as each provider's hook (or, for opencode, its plugin) spells it."""
    return {
        "claude": {"tool_name": "Bash", "tool_input": {"command": command, "description": "x"}},
        "codex": {"tool_name": "Bash", "tool_input": {"command": command}},
        "opencode": {"sessionID": "s", "tool": "bash", "args": {"command": command}},
        "opencode-aliased": {
            "sessionID": "s",
            "tool": "bash",
            "tool_name": "Bash",
            "tool_input": {"command": command},
            "args": {"command": command},
        },
    }[provider]


#: One payload spelling per provider; a provider added to ALL_PROVIDERS with no entry fails below.
PROVIDER_PAYLOADS = {"claude": ["claude"], "codex": ["codex"], "opencode": ["opencode", "opencode-aliased"]}


@requires_bash()
class GuardPayloadShapeTest(unittest.TestCase):
    def setUp(self):
        self.repo = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.repo, True)
        env = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull}
        subprocess.run(["git", "init", "-q"], cwd=self.repo, env=env, check=True)

    def run_guard(self, script, shape, command):
        return subprocess.run(
            ["bash", str(HOOKS / "pre-tool-use" / script)],
            input=json.dumps(_payload(shape, command)),
            capture_output=True,
            text=True,
            cwd=self.repo,
        )

    def test_every_provider_has_a_fixture(self):
        self.assertEqual(set(PROVIDER_PAYLOADS), set(ALL_PROVIDERS))

    def test_credential_guard_refuses_a_dump_for_every_provider_shape(self):
        for provider in ALL_PROVIDERS:
            for shape in PROVIDER_PAYLOADS[provider]:
                with self.subTest(provider=provider, shape=shape):
                    result = self.run_guard("03-credential-guard.sh", shape, "cat " + CRED)
                    self.assertEqual(result.returncode, 2, result.stderr)

    def test_credential_guard_refuses_a_forced_add_for_every_provider_shape(self):
        for provider in ALL_PROVIDERS:
            for shape in PROVIDER_PAYLOADS[provider]:
                with self.subTest(provider=provider, shape=shape):
                    result = self.run_guard("03-credential-guard.sh", shape, "git add -f " + CRED)
                    self.assertEqual(result.returncode, 2, result.stderr)

    def test_credential_guard_allows_an_ordinary_command_for_every_provider_shape(self):
        for provider in ALL_PROVIDERS:
            for shape in PROVIDER_PAYLOADS[provider]:
                with self.subTest(provider=provider, shape=shape):
                    self.assertEqual(self.run_guard("03-credential-guard.sh", shape, "ls -la").returncode, 0)

    def test_full_suite_guard_blocks_an_untouched_full_run_for_every_provider_shape(self):
        for provider in ALL_PROVIDERS:
            for shape in PROVIDER_PAYLOADS[provider]:
                with self.subTest(provider=provider, shape=shape):
                    result = self.run_guard("02c-full-suite-guard.sh", shape, "pytest")
                    self.assertEqual(result.returncode, 2, result.stderr)

    def test_a_non_shell_tool_is_ignored(self):
        payload = {"sessionID": "s", "tool": "read", "args": {"command": "cat " + CRED}}
        for script in ("03-credential-guard.sh", "02c-full-suite-guard.sh"):
            result = subprocess.run(
                ["bash", str(HOOKS / "pre-tool-use" / script)],
                input=json.dumps(payload), capture_output=True, text=True, cwd=self.repo,
            )
            self.assertEqual(result.returncode, 0, script)


if __name__ == "__main__":
    unittest.main()
