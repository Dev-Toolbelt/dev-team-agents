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

from devteam import providers  # noqa: E402

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

    def test_tasks_are_created_only_once_the_plan_is_approved(self):
        section = _section()
        self.assertIn("approved", section)
        self.assertIn("never before", section)


if __name__ == "__main__":
    unittest.main()
