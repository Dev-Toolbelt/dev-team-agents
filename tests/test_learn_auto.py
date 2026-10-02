"""`/devteam:learn --auto` skips the approval question and stays inside what the session touched.

The flag lives in `commands/learn.md`; the scope it uses has one canonical home,
`skills/shared/feature-learn/SKILL.md` § Scope Derivation. Every provider renders the command from
the same source, so each rendered copy must still carry the flag and the pointer to that section.
"""

import re
import sys
import unittest

from devteam_support import REPO_ROOT

sys.path.insert(0, str(REPO_ROOT / "scripts" / "lib"))

import render_provider  # noqa: E402
from devteam import providers  # noqa: E402

LEARN = REPO_ROOT / "commands" / "learn.md"
FEATURE_LEARN = REPO_ROOT / "skills" / "shared" / "feature-learn" / "SKILL.md"
LIB = render_provider.load_lib(REPO_ROOT / "scripts" / "lib")


def _render_claude(body):
    return render_provider.render_command_claude("learn", body, LEARN)["content"]


def _render_opencode(body):
    meta = LIB["commands"]["commands"]["learn"]
    out = render_provider.render_command_opencode("learn", meta, body, "model", None, LIB["tool_map"])
    return out["snippet_entry"]["template"]


def _render_codex(body):
    meta = LIB["commands"]["commands"]["learn"]
    return render_provider.render_command_codex("learn", meta, body, "model", None, LIB["tool_map"])["content"]


#: One renderer per provider in ALL_PROVIDERS — adding a provider without a case fails here.
RENDERERS = {
    "claude": _render_claude,
    "codex": _render_codex,
    "opencode": _render_opencode,
}


def _scope_section():
    text = FEATURE_LEARN.read_text(encoding="utf-8")
    match = re.search(r"^## Scope Derivation\n(.*?)(?=^## )", text, re.S | re.M)
    return match.group(1) if match else ""


class LearnAutoFlagTest(unittest.TestCase):
    def test_every_supported_provider_has_a_renderer_case(self):
        self.assertEqual(set(RENDERERS), set(providers.ALL_PROVIDERS))

    def test_every_provider_receives_the_flag_and_the_scope_pointer(self):
        _, body = render_provider.parse_frontmatter(LEARN.read_text(encoding="utf-8"))
        for provider, render in RENDERERS.items():
            with self.subTest(provider=provider):
                rendered = render(body)
                self.assertIn("| `--auto` |", rendered)
                self.assertIn("§ Scope Derivation", rendered)
                self.assertIn("go straight to Step 4", rendered)

    def test_dry_run_still_wins_over_auto(self):
        row = next(line for line in LEARN.read_text(encoding="utf-8").splitlines()
                   if line.startswith("| `--dry-run` |"))
        self.assertIn("wins over `--auto`", row)

    def test_auto_never_skips_the_reuse_rule_confirmation(self):
        self.assertIn("is never skipped", LEARN.read_text(encoding="utf-8"))


class ScopeDerivationTest(unittest.TestCase):
    def test_the_cascade_has_its_three_outcomes(self):
        section = _scope_section()
        self.assertTrue(section, "feature-learn has no '## Scope Derivation' section")
        for rule in ("**Branch scope:**", "**Session scope:**", "Nothing in scope"):
            self.assertIn(rule, section)

    def test_branch_scope_starts_at_the_merge_base(self):
        self.assertIn("git merge-base <base> HEAD", _scope_section())

    def test_session_scope_reuses_the_learn_marker_and_the_hook_rule(self):
        section = _scope_section()
        self.assertIn(".learn-last-run", section)
        self.assertIn("scripts/hooks/lib/touched-paths.sh", section)

    def test_the_command_does_not_restate_the_cascade(self):
        body = LEARN.read_text(encoding="utf-8")
        self.assertNotIn("git merge-base", body)
        self.assertNotIn("**Branch scope:**", body)


if __name__ == "__main__":
    unittest.main()
