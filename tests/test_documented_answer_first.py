"""Sprint execution looks in the project's documents before it asks (ADR-0064).

The rule lives in `interaction-patterns`; the other files only point at it. Each
provider's rendered sprint command must carry the approval marker and the rule.
"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from devteam_support import REPO_ROOT

sys.path.insert(0, str(REPO_ROOT / "scripts" / "lib"))

from devteam import backlog, providers  # noqa: E402

RENDERER = REPO_ROOT / "scripts" / "lib" / "render_provider.py"
RULE = "Documented Answer First"
MARKER = "PLAN_APPROVED:"


def _sprint_claude(target):
    return (target / ".claude/commands/devteam/sprint.md").read_text(encoding="utf-8")


def _sprint_opencode(target):
    raw = (target / ".opencode/commands.snippet.jsonc").read_text(encoding="utf-8")
    snippet = json.loads("\n".join(l for l in raw.splitlines() if not l.startswith("//")))
    return snippet["devteam:sprint"]["template"]


def _sprint_codex(target):
    return (target / ".codex/skills/devteam-sprint/SKILL.md").read_text(encoding="utf-8")


#: One entry per provider in `providers.ALL_PROVIDERS`; the parity guard below
#: fails the moment a provider is added without its own case.
SPRINT_READERS = {
    "claude": _sprint_claude,
    "opencode": _sprint_opencode,
    "codex": _sprint_codex,
}


def _source(relative):
    return (REPO_ROOT / relative).read_text(encoding="utf-8")


class RenderedSprintTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.targets = {}
        for provider in providers.ALL_PROVIDERS:
            target = Path(cls._tmp.name) / provider
            target.mkdir()
            subprocess.run(
                [sys.executable, str(RENDERER), "--provider", provider,
                 "--source-dir", str(REPO_ROOT), "--target-dir", str(target)],
                check=True, capture_output=True, text=True,
            )
            cls.targets[provider] = target

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def test_every_provider_has_a_parity_case(self):
        self.assertEqual(set(SPRINT_READERS), set(providers.ALL_PROVIDERS))

    def test_each_rendered_sprint_marks_the_plan_approved_and_points_at_the_rule(self):
        for provider in providers.ALL_PROVIDERS:
            with self.subTest(provider=provider):
                body = SPRINT_READERS[provider](self.targets[provider])
                self.assertIn(MARKER, body)
                self.assertIn(RULE, body)


class RuleHomesTest(unittest.TestCase):
    def test_the_rule_has_one_home(self):
        body = _source("skills/shared/interaction-patterns/SKILL.md")
        self.assertEqual(body.count(f"## {RULE}\n"), 1)
        self.assertIn("Searched:", body)

    def test_scope_lock_no_longer_stops_before_looking(self):
        body = _source("skills/shared/spec-gate/SKILL.md")
        scope_lock = body[body.index("## Scope Lock"):body.index("<HARD-GATE>", body.index("## Scope Lock"))]
        self.assertIn(RULE, scope_lock)
        self.assertIn("Stop and ask only", scope_lock)

    def test_the_relay_never_answers_an_approval_gate(self):
        body = _source("skills/shared/interaction-patterns/SKILL.md")
        relay = body[body.index("## Sub-agent Question Relay"):body.index('## "Other" Option Rule')]
        self.assertIn("never answer an approval gate", relay)
        self.assertIn("that is not an approval gate", relay)

    def test_existing_code_never_settles_a_question(self):
        body = _source("skills/shared/interaction-patterns/SKILL.md")
        self.assertIn("Existing code is never an explicit answer", body)

    def test_assumptions_reach_the_user(self):
        body = _source("commands/sprint.md")
        self.assertIn("followed by each task's `Assumptions`", body)
        self.assertIn("every `Assumptions` entry of the run", body)

    def test_test_authors_get_the_marker(self):
        self.assertIn("Test authors are spawned with the same `PLAN_APPROVED:`", _source("commands/sprint.md"))

    def test_plan_mode_honours_the_marker(self):
        self.assertIn(MARKER, _source("skills/shared/plan-mode/SKILL.md"))

    def test_preflight_requires_the_documents_tasks_decide_from(self):
        body = _source("commands/sprint.md")
        self.assertIn("the documents the tasks decide from", body)


class RefsFieldTest(unittest.TestCase):
    def test_refs_does_not_disturb_the_task_block(self):
        text = (
            "### TASK-001 — Name\n"
            "**Agent**: backend-developer\n"
            "**Wave**: A\n"
            "**Spec**: docs/specs/a.md\n"
            "**Covers**: S1, S2\n"
            "**Refs**: docs/development/architecture.md § Queues\n"
            "**Depends on**: none\n"
            "**Status**: [ ] Pending\n"
        )
        tasks = backlog.parse(text)["tasks"]
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0]["id"], "TASK-001")
        self.assertEqual(tasks[0]["covers"], ["S1", "S2"])
        self.assertEqual(tasks[0]["depends_on"], [])
        self.assertEqual(tasks[0]["status"], "pending")


if __name__ == "__main__":
    unittest.main()
