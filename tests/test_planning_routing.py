"""Planning routing: a plain-language planning request takes the /devteam:plan path on every provider.

The routing section is written by setup-assistant into each provider's instruction
file, and the health check detects and rewrites the v1 section that spawned three
planning agents in parallel. These are prose contracts, so the test pins the
phrases the health check and the setup step depend on.
"""

import re
import sys
import unittest

from devteam_support import REPO_ROOT

sys.path.insert(0, str(REPO_ROOT / "scripts" / "lib"))

import render_provider  # noqa: E402
from devteam import command_usage, providers  # noqa: E402

#: The instruction file each provider reads. One entry per provider in
#: `providers.ALL_PROVIDERS` — the parity guard fails when a provider is added
#: without saying where its routing section goes.
INSTRUCTION_FILES = {
    "claude": "CLAUDE.md",
    "opencode": "AGENTS.md",
    "codex": "AGENTS.md",
}

#: How `/devteam:sprint` surfaces on each provider — the bridge from an approved
#: plan to execution must exist everywhere the plan does.
SPRINT_EXPOSED = {
    "claude": "/devteam:sprint",
    "opencode": "/devteam:sprint",
    "codex": "$devteam-sprint",
}

V2_MARKER = "<!-- devteam:planning-routing v2 -->"
STALE_NEEDLE = "spawn these three agents **in parallel"

AUTO_ROUTING = REPO_ROOT / "skills/shared/auto-routing/SKILL.md"
SETUP = REPO_ROOT / "agents/setup-assistant.md"
CHECKS = REPO_ROOT / "skills/shared/setup-health-check/references/checks-list.md"
FIXES = REPO_ROOT / "skills/shared/setup-health-check/references/fix-patterns.md"
BACKLOG = REPO_ROOT / "skills/shared/backlog-template/SKILL.md"
PLAN = REPO_ROOT / "commands/plan.md"
RELAY = REPO_ROOT / "skills/shared/interaction-patterns/SKILL.md"


def _section(text, heading):
    start = text.index(heading)
    end = re.search(r"\n#{1,3} ", text[start + len(heading):])
    return text[start:start + len(heading) + end.start()] if end else text[start:]


class PlanningRoutingTest(unittest.TestCase):
    def test_every_provider_has_an_instruction_file(self):
        self.assertEqual(set(INSTRUCTION_FILES), set(providers.ALL_PROVIDERS))

    def test_setup_writes_the_section_for_every_provider(self):
        step5 = _section(SETUP.read_text(encoding="utf-8"), "### Step 5 — Generate the dev-team-agents Section")
        for provider, filename in INSTRUCTION_FILES.items():
            with self.subTest(provider=provider):
                self.assertIn(f"`{provider}`", step5)
                self.assertIn(f"`{filename}`", step5)

    def test_template_routes_planning_through_the_plan_command(self):
        planning = _section(AUTO_ROUTING.read_text(encoding="utf-8"), "### Auto-Routing: Planning")
        self.assertIn(V2_MARKER, planning)
        self.assertIn("`/devteam:plan`", planning)
        self.assertIn("`$devteam-plan`", planning)
        self.assertNotIn(STALE_NEEDLE, planning)

    def test_health_check_detects_the_v1_section_and_writes_v2(self):
        self.assertIn(STALE_NEEDLE, CHECKS.read_text(encoding="utf-8"))
        self.assertIn(V2_MARKER, FIXES.read_text(encoding="utf-8"))

    def test_single_overview_path_is_not_reintroduced(self):
        legacy = "docs/backlog/overview.md"
        for root in ("agents", "commands", "skills", "templates"):
            for path in (REPO_ROOT / root).rglob("*.md"):
                text = path.read_text(encoding="utf-8")
                if legacy in text:
                    with self.subTest(path=str(path.relative_to(REPO_ROOT))):
                        self.assertEqual(path, BACKLOG, "only backlog-template may name the legacy overview")

    def test_plan_command_relays_sub_agent_questions(self):
        self.assertIn("## Sub-agent Question Relay", RELAY.read_text(encoding="utf-8"))
        self.assertIn("§ Sub-agent Question Relay", PLAN.read_text(encoding="utf-8"))


def _template_block():
    text = AUTO_ROUTING.read_text(encoding="utf-8")
    start = text.index("```markdown\n## dev-team-agents")
    end = text.index("\n```", start + 3)
    return text[start:end + 4]


class CompactRoutingTest(unittest.TestCase):
    """The section is loaded on every turn, by every provider: it stays small and neutral."""

    V3_MARKER = "<!-- devteam:routing v3 -->"
    VERBOSE_NEEDLE = "#### `backend-developer`"

    ROUTED = {
        "backend-developer", "frontend-developer", "ui-ux-designer", "database-specialist",
        "devops-specialist", "backend-test-specialist", "frontend-test-specialist",
        "code-reviewer", "security-specialist", "qa-specialist", "technical-writer",
        "mobile-developer", "seo-specialist",
    }
    KEYS = (
        "PROJECT_TYPE", "TESTS_REQUIRED", "CICD_PLATFORM", "GRAPHIFY", "BACKLOG_LOCATION",
        "CLOUD_PROVIDER", "ISSUE_TRACKER", "ISSUE_TRACKER_ACCESS", "INACTIVE_AGENTS",
    )

    def test_block_stays_within_its_line_budget(self):
        # Fences included, as the skill states.
        self.assertLessEqual(len(_template_block().splitlines()), 50)

    def test_block_names_no_provider_path(self):
        # One text for CLAUDE.md and AGENTS.md: no provider path may appear in it.
        block = _template_block()
        for needle in (".claude/", ".codex/", ".opencode/"):
            self.assertNotIn(needle, block)

    def test_block_keeps_what_commands_and_checks_read(self):
        block = _template_block()
        for needle in (self.V3_MARKER, V2_MARKER, "AUTO_ROUTING: disabled") + tuple(k + ":" for k in self.KEYS):
            self.assertIn(needle, block)

    def test_every_routed_agent_exists(self):
        names = set()
        for line in _template_block().splitlines():
            if line.startswith("| `"):
                names.update(re.findall(r"`([a-z-]+)`", line.split("|")[1]))
        self.assertEqual(names, self.ROUTED)
        for name in names:
            with self.subTest(agent=name):
                self.assertTrue((REPO_ROOT / "agents" / (name + ".md")).is_file())

    def test_health_check_migrates_the_verbose_section(self):
        self.assertIn(self.VERBOSE_NEEDLE, CHECKS.read_text(encoding="utf-8"))
        self.assertNotIn(self.VERBOSE_NEEDLE, _template_block())
        self.assertIn("devteam:routing v3", FIXES.read_text(encoding="utf-8"))

    def test_unedited_is_judged_against_the_shipped_legacy_block(self):
        legacy = FIXES.parent / "legacy-routing-v2.md"
        self.assertIn("legacy-routing-v2.md", FIXES.read_text(encoding="utf-8"))
        text = legacy.read_text(encoding="utf-8")
        self.assertIn(self.VERBOSE_NEEDLE, text)
        self.assertIn("### Language", text)


TEST_GATE_COMMANDS = ("fix", "backend", "frontend", "fullstack", "mobile", "refactor", "relayout", "audit", "sprint")


class TestGateTest(unittest.TestCase):
    """A Codex- or opencode-only project keeps TESTS_REQUIRED in AGENTS.md only."""

    def setUp(self):
        self.lib = render_provider.load_lib(REPO_ROOT / "scripts" / "lib")
        self.meta = self.lib["commands"]["commands"]

    def _rendered(self, name):
        tm = self.lib["tool_map"]
        _, body = render_provider.parse_frontmatter((REPO_ROOT / "commands" / (name + ".md")).read_text(encoding="utf-8"))
        codex = render_provider.render_command_codex(name, self.meta[name], body, "m", None, tm)
        return {
            "claude": body,
            "opencode": render_provider.render_command_opencode(name, self.meta[name], body, "m", None, tm)["snippet_entry"]["template"],
            "codex": "".join(item["content"] for item in (codex if isinstance(codex, list) else [codex])),
        }

    def test_the_rule_reads_both_instruction_files(self):
        gate = _section(AUTO_ROUTING.read_text(encoding="utf-8"), "## Test Gate")
        for filename in set(INSTRUCTION_FILES.values()):
            self.assertIn("`%s`" % filename, gate)
        self.assertIn("Contradiction Guard", gate)
        self.assertIn("No section, or no key | `yes`", gate)
        self.assertIn("exactly one of", gate)

    def test_every_gated_command_resolves_through_the_rule_on_every_provider(self):
        for name in TEST_GATE_COMMANDS:
            rendered = self._rendered(name)
            self.assertEqual(set(rendered), set(providers.ALL_PROVIDERS))
            for provider, text in rendered.items():
                with self.subTest(command=name, provider=provider):
                    self.assertIn("`skills/shared/auto-routing/SKILL.md` § Test Gate", text)
                    self.assertNotIn("`CLAUDE.md` → `## dev-team-agents`", text)

    def test_no_command_or_agent_reads_the_gate_from_claude_md_alone(self):
        for root in ("commands", "agents"):
            for path in (REPO_ROOT / root).glob("*.md"):
                with self.subTest(path=path.name):
                    self.assertNotIn("`CLAUDE.md` → `## dev-team-agents` section → `TESTS_REQUIRED`", path.read_text(encoding="utf-8"))

    def test_test_culture_agents_use_the_rule(self):
        for name in ("backend-test-specialist", "frontend-test-specialist", "backend-developer"):
            with self.subTest(agent=name):
                self.assertIn("§ Test Gate", (REPO_ROOT / "agents" / (name + ".md")).read_text(encoding="utf-8"))


class SprintCommandTest(unittest.TestCase):
    def setUp(self):
        self.lib = render_provider.load_lib(REPO_ROOT / "scripts" / "lib")
        self.meta = self.lib["commands"]["commands"]

    def test_every_provider_has_a_sprint_case(self):
        self.assertEqual(set(SPRINT_EXPOSED), set(providers.ALL_PROVIDERS))

    def test_sprint_is_registered_and_exposed(self):
        self.assertIn("sprint", self.meta)
        self.assertIn("sprint", self.meta["plan"]["related"])
        for provider, name in SPRINT_EXPOSED.items():
            with self.subTest(provider=provider):
                self.assertEqual(command_usage.exposed_name(provider, "sprint"), name)

    def test_sprint_renders_the_wave_loop_on_every_provider(self):
        tm = self.lib["tool_map"]
        _, body = render_provider.parse_frontmatter((REPO_ROOT / "commands/sprint.md").read_text(encoding="utf-8"))
        rendered = {
            "claude": body,
            "opencode": render_provider.render_command_opencode("sprint", self.meta["sprint"], body, "m", None, tm)["snippet_entry"]["template"],
            "codex": "".join(
                item["content"]
                for item in (lambda out: out if isinstance(out, list) else [out])(
                    render_provider.render_command_codex("sprint", self.meta["sprint"], body, "m", None, tm)
                )
            ),
        }
        self.assertEqual(set(rendered), set(providers.ALL_PROVIDERS))
        for provider, text in rendered.items():
            with self.subTest(provider=provider):
                self.assertIn("Run the waves, in order", text)
                self.assertIn("sprint/<scope-slug>-<n>", text)

    def test_plan_offers_the_sprint_command_without_starting_it(self):
        close = _section(PLAN.read_text(encoding="utf-8"), "## Sequence")
        self.assertIn("/devteam:sprint <scope-slug> 1", close)
        self.assertIn("never start it unasked", close)

    def test_sprint_gates_are_pinned(self):
        self.assertEqual(self.meta["sprint"]["plan_gate"], "required")
        self.assertEqual(self.meta["sprint"]["interaction_mode"], "optional")
        self.assertEqual(self.meta["sprint"]["tier"], self.meta["architect"]["tier"])

    def test_architect_relays_on_every_provider(self):
        tm = self.lib["tool_map"]
        _, body = render_provider.parse_frontmatter((REPO_ROOT / "commands/architect.md").read_text(encoding="utf-8"))
        rendered = {
            "claude": body,
            "opencode": render_provider.render_command_opencode("architect", self.meta["architect"], body, "m", None, tm)["snippet_entry"]["template"],
            "codex": "".join(
                item["content"]
                for item in (lambda out: out if isinstance(out, list) else [out])(
                    render_provider.render_command_codex("architect", self.meta["architect"], body, "m", None, tm)
                )
            ),
        }
        self.assertEqual(set(rendered), set(providers.ALL_PROVIDERS))
        for provider, text in rendered.items():
            with self.subTest(provider=provider):
                self.assertIn("Sub-agent Question Relay", text)
                self.assertIn("WORKTREE_PATH", text)

    def test_spawn_prompt_paths_win_the_worktree_cascade(self):
        for rel in ("skills/shared/worktree/SKILL.md", "skills/shared/worktree/references/session-protocol.md"):
            with self.subTest(path=rel):
                self.assertIn("| 0 | Spawn prompt carries `WORKTREE_PATH` and `BRANCH` |", (REPO_ROOT / rel).read_text(encoding="utf-8"))
        for path in sorted((REPO_ROOT / "agents").glob("*.md")):
            text = path.read_text(encoding="utf-8")
            if "## Worktree Isolation" in text:
                with self.subTest(agent=path.stem):
                    self.assertIn("spawn-prompt `WORKTREE_PATH`/`BRANCH` → session file", text)


if __name__ == "__main__":
    unittest.main()
