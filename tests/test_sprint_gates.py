"""The sprint's own gates: who may own a task, and when findings are applied unasked."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from devteam_support import REPO_ROOT

sys.path.insert(0, str(REPO_ROOT / "scripts" / "lib"))

from devteam import providers  # noqa: E402

RENDERER = REPO_ROOT / "scripts" / "lib" / "render_provider.py"


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


class SprintFindingsGateTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.bodies = {}
        for provider in providers.ALL_PROVIDERS:
            target = Path(cls._tmp.name) / provider
            target.mkdir()
            subprocess.run(
                [sys.executable, str(RENDERER), "--provider", provider,
                 "--source-dir", str(REPO_ROOT), "--target-dir", str(target)],
                check=True, capture_output=True, text=True,
            )
            cls.bodies[provider] = SPRINT_READERS[provider](target)

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def test_every_provider_has_a_parity_case(self):
        self.assertEqual(set(SPRINT_READERS), set(providers.ALL_PROVIDERS))

    def test_auto_applies_findings_and_the_stops_remain(self):
        for provider, body in self.bodies.items():
            with self.subTest(provider=provider):
                gate = body[body.index("Findings → when `review_gate_mode`"):]
                self.assertIn("is `auto`, apply them as **Apply all**", gate)
                self.assertIn("asking only about QUESTION rows", gate)
                self.assertIn("Review Loop); otherwise one ", gate)
                self.assertIn("`[SPEC-DRIFT]` or a BLOCKING still open after that pass", gate)
                self.assertIn("**Accept and continue** is not offered", gate)
                self.assertIn("A task `NOT RUN` has no findings to ask about", body)

    def test_the_command_owns_the_review_and_delegation_is_sequential(self):
        for provider, body in self.bodies.items():
            with self.subTest(provider=provider):
                self.assertIn("Step 5 owns the review", body)
                self.assertIn("one at a time inside WORKTREE_PATH", body)


class RosterTest(unittest.TestCase):
    def test_every_agent_the_backlog_assigns_is_in_the_roster(self):
        roster = _source("skills/architecture/orchestration/SKILL.md")
        roster = roster[roster.index("## Agent Roster"):roster.index("## Spawn Integrity")]
        backlog = _source("skills/shared/backlog-template/SKILL.md")
        table = backlog[backlog.index("### Agent Assignment Table"):backlog.index("## Gated Layout")]
        assigned = {
            name for row in table.splitlines() if row.startswith("|")
            for cell in row.split("|")[2:4]
            for name in cell.split("`")[1::2]
        }
        self.assertIn("software-architect", assigned)
        for name in assigned:
            with self.subTest(agent=name):
                self.assertIn(f"| `{name}` |", roster)


if __name__ == "__main__":
    unittest.main()
