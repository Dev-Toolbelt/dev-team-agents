"""An approved plan's steps reach the task board only through each provider's native task list.

`skills/shared/plan-mode/SKILL.md` § Task List Mirroring names the tool per provider itself,
because skills are read raw by every provider — nothing rewrites them at render time. Its rules
must also match how the board (`scripts/lib/devteam/tasks.py`) recognises a task.
"""

import re
import sys
import unittest

from devteam_support import REPO_ROOT

sys.path.insert(0, str(REPO_ROOT / "scripts" / "lib"))

import render_provider  # noqa: E402
from devteam import providers, tasks  # noqa: E402
from test_tasks import (  # noqa: E402
    T0, BoardCase, codex_plan, opencode_todos, task_create, task_update, todo, todo_write,
)

#: Every task-list tool a provider exposes — one entry per provider in ALL_PROVIDERS, so adding a
#: provider without deciding its tool fails here instead of shipping a board that stays empty.
NATIVE_TASK_TOOLS = {
    "claude": ("TaskCreate", "TaskUpdate", "TodoWrite"),
    "codex": ("update_plan",),
    "opencode": ("todowrite",),
}

PLAN_MODE = REPO_ROOT / "skills" / "shared" / "plan-mode" / "SKILL.md"


def _section():
    text = PLAN_MODE.read_text(encoding="utf-8")
    match = re.search(r"^## Task List Mirroring\n(.*?)(?=^## )", text, re.S | re.M)
    return match.group(1) if match else ""


def _row(tool):
    for line in _section().splitlines():
        if line.startswith("| `{}`".format(tool)):
            return line
    return ""


class TaskListMirroringTest(unittest.TestCase):
    def test_every_supported_provider_has_its_task_tools_decided(self):
        self.assertEqual(set(NATIVE_TASK_TOOLS), set(providers.ALL_PROVIDERS))

    def test_the_skill_names_every_task_tool_of_every_provider(self):
        self.assertTrue(_section(), "plan-mode has no '## Task List Mirroring' section")
        for provider, tools in NATIVE_TASK_TOOLS.items():
            for tool in tools:
                self.assertIn("`{}`".format(tool), _section(), provider)

    def test_no_provider_is_told_to_send_a_status_its_tool_rejects(self):
        # Codex update_plan and Claude TaskUpdate have no `cancelled`; Claude drops with `deleted`.
        for tool in ("update_plan", "TaskCreate", "TodoWrite"):
            self.assertNotIn("cancelled", _row(tool), tool)
        self.assertIn("deleted", _row("TaskCreate"))

    def test_whole_list_tools_are_described_as_whole_list(self):
        for tool in ("TodoWrite", "update_plan", "todowrite"):
            self.assertIn("Whole list", _row(tool), tool)

    def test_titles_and_ids_are_frozen_because_the_board_matches_on_them(self):
        section = _section()
        self.assertIn("never rename or renumber", section)
        self.assertIn("step-N", _row("todowrite"))

    def test_tasks_are_created_only_after_approval_and_the_strategy_gate(self):
        when = [line for line in _section().splitlines() if line.startswith("- **When**")]
        self.assertTrue(when)
        self.assertIn("Execution Strategy Gate", _section())

    def test_the_rules_the_board_depends_on_are_all_stated(self):
        section = _section()
        for rule in ("**One list per plan**", "**Aborted run**", "**Reviews**", "**Par.** group"):
            self.assertIn(rule, section)
        self.assertIn("priority", _row("todowrite"))

    def test_replanning_keeps_the_original_step_numbers(self):
        text = PLAN_MODE.read_text(encoding="utf-8")
        replan = text[text.index("## Replanning During Execution"):]
        self.assertIn("keeping their original step numbers", replan)

def _mirrored(provider, session, steps):
    """The call a whole-list provider sends for ``steps`` — ``[(n, action, status)]`` — per the skill."""
    titled = [("Step {}: {}".format(n, action), status, n) for n, action, status in steps]
    if provider == "claude-todowrite":
        return todo_write(session, [todo(title, status) for title, status, _ in titled])
    if provider == "codex":
        return codex_plan(session, [(title, status) for title, status, _ in titled])
    return opencode_todos(session, [("step-{}".format(n), title, status) for title, status, n in titled])


class MirroredPlanOnTheBoardTest(BoardCase):
    """What the skill's rules produce on the board, through the real record/view code."""

    WHOLE_LIST = ("claude-todowrite", "codex", "opencode")

    def board(self, session):
        sessions = [s for p in self.view(now=T0 + 100) for s in p["sessions"] if s["session_id"] == session]
        return sorted((t["content"], t["column"]) for t in sessions[0]["tasks"])

    def test_a_replan_that_keeps_the_numbers_shows_every_step_once(self):
        for provider in self.WHOLE_LIST:
            with self.subTest(provider=provider):
                session = "s-" + provider
                self.rec(_mirrored(provider, session, [(1, "A", "pending"), (2, "B", "pending"), (3, "C", "pending")]))
                self.rec(_mirrored(provider, session, [(1, "A", "completed"), (2, "B", "in_progress"), (3, "C", "pending")]), now=T0 + 10)
                # Replan: drop step 3, add step 4 — numbers kept, the dropped step omitted.
                self.rec(_mirrored(provider, session, [(1, "A", "completed"), (2, "B", "in_progress"), (4, "D", "pending")]), now=T0 + 20)
                self.assertEqual(self.board(session), [
                    ("Step 1: A", "done"), ("Step 2: B", "in_progress"), ("Step 4: D", "todo"),
                ])

    def test_renumbering_a_finished_step_would_show_it_twice(self):
        # Why the skill freezes titles: on a whole-list tool a renamed step is a different task.
        for provider in ("claude-todowrite", "codex"):
            with self.subTest(provider=provider):
                session = "r-" + provider
                self.rec(_mirrored(provider, session, [(1, "A", "completed"), (2, "B", "pending")]))
                self.rec(_mirrored(provider, session, [(1, "B", "pending"), (2, "A", "completed")]), now=T0 + 10)
                done = [c for c, col in self.board(session) if col == "done"]
                self.assertEqual(len(done), 2, done)

    def test_claude_drops_a_step_with_deleted(self):
        self.rec(task_create("c1", "Step 1: A", {"id": "1"}))
        self.rec(task_create("c1", "Step 2: B", {"id": "2"}), now=T0 + 1)
        self.rec(task_update("c1", "2", "deleted"), now=T0 + 2)
        self.assertEqual(self.board("c1"), [("Step 1: A", "todo")])

    def test_a_step_title_is_capped_at_the_apps_bound(self):
        self.rec(_mirrored("codex", "long", [(1, "x" * 5000, "pending")]))
        (content, _), = self.board("long")
        self.assertEqual(len(content), tasks.MAX_TASK_TEXT)


class RenderedCommandsReachTheRuleTest(unittest.TestCase):
    """The orchestrating session of a plan-gated command must reach § Task List Mirroring on every provider."""

    def test_a_conditional_command_points_at_the_rule_on_every_provider(self):
        body = (REPO_ROOT / "commands" / "backend.md").read_text(encoding="utf-8")
        for provider in providers.ALL_PROVIDERS:
            with self.subTest(provider=provider):
                rendered = render_provider.soften_plan_gate(body, provider, "conditional")
                self.assertIn("plan-mode/SKILL.md", rendered)
                if provider != "claude":
                    self.assertIn("Task List Mirroring", rendered)


if __name__ == "__main__":
    unittest.main()
