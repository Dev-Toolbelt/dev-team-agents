"""An approved plan's steps reach the task board only through each provider's native task list.

`skills/shared/plan-mode/SKILL.md` § Task List Mirroring names the tool per provider, because
skills are read raw by every provider; agent and command bodies are rewritten at render time
from `scripts/lib/tool-map.json`. Both must cover every provider in `providers.ALL_PROVIDERS`.
"""

import json
import re
import sys
import unittest

from devteam_support import REPO_ROOT

sys.path.insert(0, str(REPO_ROOT / "scripts" / "lib"))

import render_provider  # noqa: E402
from devteam import providers  # noqa: E402

#: The native task-list tool per provider — one entry per provider in ALL_PROVIDERS, so adding a
#: provider without deciding its tool fails here instead of shipping a board that stays empty.
NATIVE_TASK_TOOL = {
    "claude": "TaskCreate",
    "codex": "update_plan",
    "opencode": "todowrite",
}

PLAN_MODE = REPO_ROOT / "skills" / "shared" / "plan-mode" / "SKILL.md"
TOOL_MAP = REPO_ROOT / "scripts" / "lib" / "tool-map.json"


def _mirroring_section():
    text = PLAN_MODE.read_text(encoding="utf-8")
    match = re.search(r"^## Task List Mirroring\n(.*?)(?=^## )", text, re.S | re.M)
    return match.group(1) if match else ""


class TaskListMirroringTest(unittest.TestCase):
    def test_every_supported_provider_has_a_native_task_tool_decided(self):
        self.assertEqual(set(NATIVE_TASK_TOOL), set(providers.ALL_PROVIDERS))

    def test_plan_mode_names_the_task_tool_of_every_provider(self):
        section = _mirroring_section()
        self.assertTrue(section, "plan-mode has no '## Task List Mirroring' section")
        for provider, tool in NATIVE_TASK_TOOL.items():
            self.assertIn("`{}`".format(tool), section, provider)

    def test_tasks_are_created_on_approval_only(self):
        section = _mirroring_section()
        self.assertIn("On approval", section)
        self.assertIn("never before", section)

    def test_the_tool_map_sends_every_claude_task_tool_to_the_providers_native_one(self):
        tool_map = json.loads(TOOL_MAP.read_text(encoding="utf-8"))["providers"]
        for provider, tool in NATIVE_TASK_TOOL.items():
            if provider == "claude":  # the identity case: bodies already use Claude's names
                continue
            rewrites = tool_map[provider].get("tool_rewrites", {})
            for claude_name in ("TaskCreate", "TaskUpdate", "TodoWrite"):
                self.assertEqual(rewrites.get(claude_name), tool, "{}: {}".format(provider, claude_name))

    def test_codex_bodies_get_update_plan_for_every_claude_task_tool(self):
        body = "Create them with TaskCreate, move them with TaskUpdate, or TodoWrite."
        rendered = render_provider.apply_codex_body_rewrites(body)
        self.assertNotRegex(rendered, r"\b(TaskCreate|TaskUpdate|TodoWrite)\b")
        self.assertEqual(rendered.count("update_plan"), 3)


if __name__ == "__main__":
    unittest.main()
