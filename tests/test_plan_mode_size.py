"""A required plan is either a small-change plan or a full one, and every home of that rule agrees.

`skills/shared/plan-mode/SKILL.md` § Plan Size owns the conditions, `templates/plan-template.md`
owns both formats, and `skills/shared/project-context/SKILL.md` keys its trivial-task exception to
the same conditions. Skills and templates reach every provider raw — nothing rewrites them at
render time — so checking the canonical files covers every provider. Commands are rendered: on the
delegated providers a `conditional` command's PLAN GATE becomes a shorter note, which must carry
the same sizes.
"""

import json
import re
import sys
import unittest

from devteam_support import REPO_ROOT

sys.path.insert(0, str(REPO_ROOT / "scripts" / "lib"))

import render_provider  # noqa: E402
from devteam import providers  # noqa: E402

PLAN_MODE = REPO_ROOT / "skills" / "shared" / "plan-mode" / "SKILL.md"
TEMPLATE = REPO_ROOT / "templates" / "plan-template.md"
PROJECT_CONTEXT = REPO_ROOT / "skills" / "shared" / "project-context" / "SKILL.md"

APPROVAL_CLOSER = "Awaiting your approval before proceeding."

#: How each provider receives a `conditional` command's PLAN GATE — one entry per provider in
#: ALL_PROVIDERS, so adding a provider without deciding it fails here.
CONDITIONAL_GATE = {
    "claude": "verbatim",
    "codex": "softened",
    "opencode": "softened",
}


def _plan_size_section():
    text = PLAN_MODE.read_text(encoding="utf-8")
    match = re.search(r"^### Plan Size\n(.*?)(?=^## |^---)", text, re.S | re.M)
    return match.group(1) if match else ""


def _compact_form():
    text = TEMPLATE.read_text(encoding="utf-8")
    marker = text.find("COMPACT FORM — small changes only")
    return text[marker:] if marker >= 0 else ""


class PlanSizeTest(unittest.TestCase):
    def test_plan_mode_defines_both_sizes(self):
        section = _plan_size_section()
        self.assertTrue(section, "plan-mode has no '### Plan Size' section")
        self.assertIn("**Small change**", section)
        self.assertIn("**Full**", section)

    def test_small_change_lists_its_six_conditions(self):
        conditions = re.findall(r"^\d\. ", _plan_size_section(), re.M)
        self.assertEqual(len(conditions), 6)

    def test_small_change_upgrades_to_a_full_plan(self):
        section = _plan_size_section()
        self.assertIn("Upgrade on contact", section)
        self.assertIn("§ Replanning During Execution", section)
        self.assertIn("continue from Step 2", section)

    def test_plan_format_fills_only_the_picked_form(self):
        self.assertIn("fill in only the form § Plan Size picked", PLAN_MODE.read_text(encoding="utf-8"))

    def test_template_has_a_compact_form_with_its_own_closer(self):
        compact = _compact_form()
        self.assertTrue(compact, "plan-template.md has no compact form")
        for field in ("**Change:**", "**File:**", "**Validation:**"):
            self.assertIn(field, compact)
        self.assertIn(APPROVAL_CLOSER, compact)
        self.assertNotIn("### Steps", compact)
        self.assertNotIn("Par.", compact)

    def test_full_form_closer_is_kept(self):
        text = TEMPLATE.read_text(encoding="utf-8")
        # One closer per form: full and compact.
        self.assertEqual(text.count(APPROVAL_CLOSER), 2)

    def test_trivial_task_exception_uses_the_same_bar(self):
        text = PROJECT_CONTEXT.read_text(encoding="utf-8")
        line = next((l for l in text.splitlines() if l.startswith("**Trivial-task exception**")), "")
        self.assertIn("§ Plan Size", line)



def _conditional_commands():
    meta = json.loads((REPO_ROOT / "scripts" / "lib" / "commands.json").read_text(encoding="utf-8"))
    for name, entry in sorted(meta["commands"].items()):
        body_path = REPO_ROOT / "commands" / "{}.md".format(name)
        if entry.get("plan_gate") == "conditional" and body_path.exists():
            body = body_path.read_text(encoding="utf-8")
            if "**PLAN GATE" in body:
                yield name, body


class ConditionalGateTest(unittest.TestCase):
    def test_every_provider_has_its_conditional_gate_decided(self):
        self.assertEqual(set(CONDITIONAL_GATE), set(providers.ALL_PROVIDERS))

    def test_there_are_conditional_commands_to_check(self):
        self.assertTrue(list(_conditional_commands()))

    def test_every_provider_sizes_the_plan_of_a_conditional_command(self):
        for name, body in _conditional_commands():
            for provider in providers.ALL_PROVIDERS:
                with self.subTest(command=name, provider=provider):
                    rendered = render_provider.soften_plan_gate(body, provider, "conditional")
                    if CONDITIONAL_GATE[provider] == "verbatim":
                        self.assertEqual(rendered, body)
                        continue
                    self.assertNotIn("**PLAN GATE", rendered)
                    self.assertIn("§ Plan Size", rendered)
                    self.assertIn("§ When a Plan Is Required", rendered)
                    self.assertIn("every agent it spawns", rendered)
                    self.assertIn("§ Task List Mirroring", rendered)
                    self.assertNotIn("execute directly", rendered.lower())


if __name__ == "__main__":
    unittest.main()
