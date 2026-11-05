"""The SubagentStop supervision gate (ADR-0062 decision 4), on every provider."""

import json
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from devteam_support import REPO_ROOT, requires_bash

from devteam import hooks, providers

HOOKS = REPO_ROOT / "scripts" / "hooks"
CLAUDE_GATE = HOOKS / "subagent-supervise.sh"
CODEX_DISPATCHER = HOOKS / "subagent-stop.sh"

#: Where each provider runs the gate. opencode has no SubagentStop event: nothing to wire.
GATE_EVENT = {"claude": "SubagentStop", "codex": "SubagentStop", "opencode": None}


def banner(agent):
    return "done\n\n**Ran on:**\n\n| Agent | Tier | Model | Effort |\n|---|---|---|---|\n| `{}` | `t` | `m` | `e` |".format(agent)


def payload(agent, message, **extra):
    base = {"hook_event_name": "SubagentStop", "agent_type": agent, "last_assistant_message": message,
            "stop_hook_active": False}
    return dict(base, **extra)


def run(script, data):
    raw = data if isinstance(data, str) else json.dumps(data)
    proc = subprocess.run(["bash", str(script)], input=raw, capture_output=True, text=True, timeout=60)
    return proc.returncode, proc.stdout


@requires_bash()
class GateTest(unittest.TestCase):
    def held(self, data, script=CLAUDE_GATE):
        code, out = run(script, data)
        self.assertEqual(code, 0)
        if not out.strip():
            return None
        decision = json.loads(out)
        self.assertEqual(decision["decision"], "block")
        return decision["reason"]

    def test_missing_banner_is_held_and_told_what_to_append(self):
        reason = self.held(payload("backend-developer", "all done"))
        self.assertIn("Ran on", reason)
        self.assertIn("| `backend-developer` |", reason)

    def test_banner_present_is_not_held(self):
        self.assertIsNone(self.held(payload("backend-developer", banner("backend-developer"))))

    def test_a_namespaced_agent_is_not_ours(self):
        for agent in ("other-plugin:code-reviewer", "dev-team-agents:backend-developer"):
            with self.subTest(agent=agent):
                self.assertIsNone(self.held(payload(agent, "x")))

    def test_a_banner_of_another_agent_does_not_count(self):
        self.assertIsNotNone(self.held(payload("backend-developer", banner("frontend-developer"))))

    def test_reviewer_needs_the_review_result_marker(self):
        lint = (REPO_ROOT / "helpers" / "agent-lint.sh").read_text(encoding="utf-8")
        for agent in re.search(r'^REVIEW_RESULT_AGENTS="([^"]*)"', lint, re.M).group(1).split():
            with self.subTest(agent=agent):
                reason = self.held(payload(agent, banner(agent)))
                self.assertIn("review-result: findings=", reason)
                done = banner(agent) + "\n<!-- review-result: findings=0 -->"
                self.assertIsNone(self.held(payload(agent, done)))

    def test_built_in_and_unknown_agents_are_never_held(self):
        for agent in ("Explore", "general-purpose", "Plan", "nonexistent-agent"):
            with self.subTest(agent=agent):
                self.assertIsNone(self.held(payload(agent, "no banner")))

    def test_only_an_explicit_false_stop_hook_active_is_held(self):
        for value in (True, "true", "false", 1, 0, None):
            with self.subTest(value=value):
                self.assertIsNone(self.held(payload("backend-developer", "x", stop_hook_active=value)))
        data = payload("backend-developer", "x")
        del data["stop_hook_active"]
        self.assertIsNone(self.held(data))

    def test_reviewer_list_matches_the_lint(self):
        lint = (REPO_ROOT / "helpers" / "agent-lint.sh").read_text(encoding="utf-8")
        lint_agents = set(re.search(r'^REVIEW_RESULT_AGENTS="([^"]*)"', lint, re.M).group(1).split())
        gate = (HOOKS / "lib" / "subagent-supervision.sh").read_text(encoding="utf-8")
        gate_agents = set(re.findall(r'"([a-z-]+)"', re.search(r"REVIEWERS = \{([^}]*)\}", gate).group(1)))
        self.assertEqual(lint_agents, gate_agents)

    def test_task_board_review_agents_are_the_marker_agents_minus_seo(self):
        # seo-specialist emits the marker but runs next to frontend-developer, so it opens no In Review window.
        from devteam import review_triggers
        lint = (REPO_ROOT / "helpers" / "agent-lint.sh").read_text(encoding="utf-8")
        lint_agents = set(re.search(r'^REVIEW_RESULT_AGENTS="([^"]*)"', lint, re.M).group(1).split())
        self.assertEqual(lint_agents - set(review_triggers.REVIEW_AGENTS), {"seo-specialist"})
        self.assertLessEqual(set(review_triggers.REVIEW_AGENTS), lint_agents)

    def test_malformed_or_incomplete_payloads_print_nothing(self):
        for data in ("", "not json", "[]", "{}", json.dumps({"agent_type": "backend-developer"}),
                     json.dumps({"agent_type": "../x", "last_assistant_message": "y"})):
            with self.subTest(data=data):
                self.assertIsNone(self.held(data))

    def test_codex_dispatcher_relays_the_block_and_exits_zero(self):
        reason = self.held(payload("backend-developer", "x"), script=CODEX_DISPATCHER)
        self.assertIn("Ran on", reason)
        self.assertIsNone(self.held(payload("backend-developer", banner("backend-developer")), script=CODEX_DISPATCHER))
        self.assertIsNone(self.held(payload("Explore", "x"), script=CODEX_DISPATCHER))
        self.assertIsNone(self.held("garbage", script=CODEX_DISPATCHER))

    def test_a_held_stop_skips_the_later_sub_scripts_and_swallows_their_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            hooks_dir = root / "scripts" / "hooks"
            (hooks_dir / "subagent-stop").mkdir(parents=True)
            (hooks_dir / "lib").mkdir()
            (root / "scripts" / "lib").mkdir()
            (root / "agents").mkdir()
            shutil.copy(CODEX_DISPATCHER, hooks_dir / "subagent-stop.sh")
            shutil.copy(HOOKS / "subagent-stop" / "00-supervision.sh", hooks_dir / "subagent-stop")
            shutil.copy(HOOKS / "lib" / "subagent-supervision.sh", hooks_dir / "lib")
            shutil.copy(REPO_ROOT / "scripts" / "lib" / "python.sh", root / "scripts" / "lib")
            shutil.copy(REPO_ROOT / "agents" / "backend-developer.md", root / "agents")
            mark = root / "board-ran"
            (hooks_dir / "subagent-stop" / "01-probe.sh").write_text(
                'cat >/dev/null\necho "not a decision"\ntouch "{}"\n'.format(mark), encoding="utf-8")
            script = hooks_dir / "subagent-stop.sh"
            self.assertIsNotNone(self.held(payload("backend-developer", "x"), script=script))
            self.assertFalse(mark.exists())
            self.assertIsNone(self.held(payload("backend-developer", banner("backend-developer")), script=script))
            self.assertTrue(mark.exists())


class RegistrationTest(unittest.TestCase):
    def test_every_provider_has_its_case(self):
        self.assertEqual(set(GATE_EVENT), set(providers.ALL_PROVIDERS))

    def test_the_gate_is_wired_where_decided(self):
        for provider in providers.ALL_PROVIDERS:
            with self.subTest(provider=provider):
                if provider == "claude":
                    self.assertIn((GATE_EVENT[provider], "subagent-supervise.sh"), hooks.EVENTS)
                    self.assertNotIn(("SubagentStop", "subagent-stop.sh"), hooks.EVENTS)
                elif provider == "codex":
                    self.assertIn(GATE_EVENT[provider], providers.CODEX_MANAGED_EVENTS)
                    self.assertTrue((HOOKS / "subagent-stop" / "00-supervision.sh").is_file())
                else:
                    self.assertIsNone(GATE_EVENT[provider])

    def test_the_legacy_installer_wires_the_same_script(self):
        text = (REPO_ROOT / "scripts" / "install.sh").read_text(encoding="utf-8")
        self.assertIn('_inject_hook "SubagentStop" "$SUBAGENT_SUPERVISE_HOOK" "hooks/subagent-supervise.sh"', text)
        self.assertNotIn("subagent-stop.sh", text)


if __name__ == "__main__":
    unittest.main()
