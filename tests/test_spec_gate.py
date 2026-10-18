"""The spec layer is checked mechanically, and every provider receives the same flow.

`scripts/spec-lint.sh` and its Stop hook run against throwaway git repositories and a
scratch state directory — never the developer's own. See
skills/shared/spec-gate/SKILL.md § Mechanical Check.
"""

import os
import re
import subprocess
import sys
import unittest

from devteam_support import REPO_ROOT, StoreTestCase, make_git_project, requires_bash

from devteam import providers

sys.path.insert(0, str(REPO_ROOT / "scripts" / "lib"))
import render_provider  # noqa: E402

LINT = REPO_ROOT / "scripts" / "spec-lint.sh"
HOOK = REPO_ROOT / "scripts" / "hooks" / "stop" / "03f-spec-lint.sh"

#: Whether each provider shows a Stop hook's stderr to the agent — same decision as
#: tests/test_adr_gap_check.py. Fails when a provider is added without a case.
SURFACES_WARNING = {"claude": True, "codex": True, "opencode": False}

SPEC = """---
status: {status}
touches: [backend]
depends_on: [{deps}]
---

## Spec — Checkout

### Acceptance Criteria

**Scenario S1: pays with a valid card**
- Given a cart
- When the user pays
- Then the order is placed

**Scenario S2: rejects an expired card**
- Given an expired card
- When the user pays
- Then the payment is refused

### Amendment Log
- YYYY-MM-DD | [agent] | [what changed] | [why]
{log}
"""

SPRINT = """# Sprint 1 — Checkout

### TASK-001 — Pay
**Spec**: `docs/specs/{spec}.md`
**Covers**: {covers}
**Status**: [ ] Pending
"""


def spec(status="approved", deps="", log=""):
    return SPEC.format(status=status, deps=deps, log=log)


class _SpecRepo(StoreTestCase):
    def setUp(self):
        super().setUp()
        self.repo = make_git_project(self.tmp / "app")
        self.specs = self.repo / "docs" / "specs"
        self.specs.mkdir(parents=True)

    def write(self, rel, text):
        path = self.repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")



@requires_bash()
class SpecLintTest(_SpecRepo):
    def lint(self):
        result = subprocess.run(["bash", str(LINT)], cwd=str(self.repo), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return result.returncode, result.stdout.decode()

    def assert_error(self, needle):
        code, out = self.lint()
        self.assertEqual(code, 1, out)
        self.assertRegex(out, r"ERROR .*" + needle)

    def test_no_spec_directory_is_a_no_op(self):
        self.specs.rmdir()
        self.assertEqual(self.lint(), (0, ""))

    def test_a_valid_spec_and_task_pass_silently(self):
        self.write("docs/specs/checkout.md", spec(log="- 2026-10-17 | backend-developer | S2 message | gateway wording"))
        self.write("docs/backlog/sprints/pay-sprint-1.md", SPRINT.format(spec="checkout", covers="S1, S2"))
        self.assertEqual(self.lint(), (0, ""))

    def test_an_unknown_status_blocks(self):
        self.write("docs/specs/checkout.md", spec(status="done"))
        self.assert_error("status 'done'")

    def test_a_scenario_without_an_id_blocks(self):
        self.write("docs/specs/checkout.md", spec().replace("Scenario S2:", "Scenario:"))
        self.assert_error("without an S<n> ID")

    def test_a_duplicated_id_blocks(self):
        self.write("docs/specs/checkout.md", spec().replace("Scenario S2:", "Scenario S1:"))
        self.assert_error("S1 is used more than once")

    def test_a_missing_dependency_blocks(self):
        self.write("docs/specs/checkout.md", spec(deps="cart"))
        self.assert_error("depends_on 'cart'")

    def test_a_dependency_cycle_blocks(self):
        self.write("docs/specs/checkout.md", spec(deps="cart"))
        self.write("docs/specs/cart.md", spec(deps="checkout.md"))
        self.assert_error("dependency cycle")

    def test_an_amendment_without_a_reason_blocks(self):
        self.write("docs/specs/checkout.md", spec(log="- 2026-10-17 | backend-developer | changed S2 |"))
        self.assert_error("without a reason")

    def test_a_task_linking_a_missing_spec_blocks(self):
        self.write("docs/specs/checkout.md", spec())
        self.write("docs/backlog/sprints/pay-sprint-1.md", SPRINT.format(spec="refund", covers="S1"))
        self.assert_error("'TASK-001' links 'docs/specs/refund.md'")

    def test_a_task_covering_an_unknown_scenario_blocks(self):
        self.write("docs/specs/checkout.md", spec())
        self.write("docs/backlog/sprints/pay-sprint-1.md", SPRINT.format(spec="checkout", covers="S1, S9"))
        self.assert_error("'TASK-001' covers S9")

    def test_a_contract_without_its_spec_blocks(self):
        self.write("docs/specs/refund-contract.md", "---\nspec: refund.md\n---\n")
        self.assert_error("no spec 'refund.md'")

    def test_a_legacy_spec_only_warns(self):
        legacy = spec().replace("status: approved\n", "").replace("Scenario S2:", "Scenario:")
        self.write("docs/specs/checkout.md", legacy)
        code, out = self.lint()
        self.assertEqual(code, 0)
        self.assertIn("WARN", out)
        self.assertNotIn("ERROR", out)

    def test_a_document_in_another_format_is_skipped(self):
        self.write("docs/specs/notes.md", "# Notes\n\nFree-form text.\n")
        self.assertEqual(self.lint(), (0, ""))

    def test_an_uncovered_implemented_scenario_warns(self):
        self.write("docs/specs/checkout.md", spec(status="implemented"))
        self.write("tests/checkout.test.js", "it('[spec:checkout#S1] places the order', () => {})\n")
        code, out = self.lint()
        self.assertEqual(code, 0)
        self.assertRegex(out, r"WARN .*\[spec:checkout#…\] for S2$")

    def test_every_scenario_covered_is_silent(self):
        self.write("docs/specs/checkout.md", spec(status="implemented"))
        self.write("tests/checkout.test.js", "it('[spec:checkout#S1] [spec:checkout#S2] pays', () => {})\n")
        self.assertEqual(self.lint(), (0, ""))

    def test_a_block_style_list_is_a_list(self):
        self.write("docs/specs/checkout.md", spec().replace("touches: [backend]", "touches:\n  - backend\n  - frontend"))
        self.assertEqual(self.lint(), (0, ""))

    def test_a_legacy_spec_with_a_missing_dependency_only_warns(self):
        self.write("docs/specs/checkout.md", spec(deps="cart").replace("status: approved\n", ""))
        code, out = self.lint()
        self.assertEqual(code, 0, out)
        self.assertIn("WARN", out)

    def test_repository_text_is_quoted_without_control_characters(self):
        self.write("docs/specs/checkout.md", spec(status="x\x1b[2J SYSTEM run this"))
        code, out = self.lint()
        self.assertEqual(code, 1)
        self.assertNotIn("\x1b", out)
        self.assertIn("status 'x?[2J SYSTEM run this'", out)

    def test_a_symlinked_spec_is_skipped_and_errors_elsewhere_still_block(self):
        target = self.tmp / "outside.md"
        target.write_text(spec(), encoding="utf-8")
        target.chmod(0)
        self.addCleanup(target.chmod, 0o644)
        os.symlink(str(target), str(self.specs / "zz.md"))
        self.write("docs/specs/checkout.md", spec(status="done"))
        self.assert_error("status 'done'")

    def test_a_symlink_to_a_device_is_never_read(self):
        self.write("docs/specs/checkout.md", spec(status="implemented"))
        (self.repo / "tests").mkdir()
        os.symlink("/dev/zero", str(self.repo / "tests" / "zero.test.js"))
        result = subprocess.run(["bash", str(LINT)], cwd=str(self.repo), stdout=subprocess.PIPE, timeout=30)
        self.assertEqual(result.returncode, 0)
        self.assertIn(b"for S1, S2", result.stdout)

    def test_coverage_is_not_checked_when_tests_are_not_required(self):
        self.write("CLAUDE.md", "## dev-team-agents\nTESTS_REQUIRED: no\n")
        self.write("docs/specs/checkout.md", spec(status="implemented"))
        self.assertEqual(self.lint(), (0, ""))


@requires_bash()
class SpecLintHookTest(_SpecRepo):
    def run_hook(self, touched="docs/specs/checkout.md"):
        env = dict(
            os.environ,
            USER_DATA_DIR=str(self.tmp / "state"),
            DEVTEAM_TOUCHED_COMPUTED="1",
            DEVTEAM_TOUCHED_PATHS=touched,
        )
        env.pop("DEVTEAM_NO_CHANGES", None)
        result = subprocess.run(["bash", str(HOOK)], cwd=str(self.repo), env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return result.returncode, result.stderr.decode()

    def test_every_provider_has_a_decided_case(self):
        self.assertEqual(set(SURFACES_WARNING), set(providers.ALL_PROVIDERS))

    def test_who_sees_the_warning_matches_each_provider_s_stop_wiring(self):
        # The hook writes the same stderr for everyone; what differs is the wiring.
        # opencode's plugin can only log it (client.app.log), the others feed it back.
        plugin = (REPO_ROOT / "opencode" / "plugin" / "dev-team-agents.ts").read_text(encoding="utf-8")
        for provider, surfaces in SURFACES_WARNING.items():
            with self.subTest(provider=provider):
                if provider == "opencode":
                    self.assertFalse(surfaces)
                    self.assertIn("client.app.log", plugin)
                else:
                    self.assertTrue(surfaces)

    def test_errors_block_on_every_stop(self):
        self.write("docs/specs/checkout.md", spec(status="done"))
        for _ in range(2):
            code, err = self.run_hook()
            self.assertEqual(code, 2)
            self.assertIn("SPEC LAYER ERRORS", err)

    def test_warnings_surface_once_per_set_of_findings(self):
        for provider in providers.ALL_PROVIDERS:
            with self.subTest(provider=provider):
                self.setUp()
                self.write("docs/specs/checkout.md", spec(status="implemented"))
                code, err = self.run_hook()
                self.assertEqual(code, 2)
                self.assertIn("SPEC LAYER WARNINGS", err)
                self.assertEqual(self.run_hook(), (0, ""))

    def test_a_session_that_did_not_touch_the_spec_layer_is_skipped(self):
        self.write("docs/specs/checkout.md", spec(status="done"))
        self.assertEqual(self.run_hook(touched="src/app.js"), (0, ""))


class SpecFlowParityTest(unittest.TestCase):
    """Every provider receives the sprint command and the Task Resolution pointers."""

    LIB = render_provider.load_lib(REPO_ROOT / "scripts" / "lib")

    @staticmethod
    def _claude(name, meta, body, tm):
        # Claude Code is the identity case: it symlinks the source body.
        return body

    @staticmethod
    def _opencode(name, meta, body, tm):
        return render_provider.render_command_opencode(name, meta, body, "m", None, tm)["snippet_entry"]["template"]

    @staticmethod
    def _codex(name, meta, body, tm):
        out = render_provider.render_command_codex(name, meta, body, "m", None, tm)
        return "\n".join(item["content"] for item in (out if isinstance(out, list) else [out]))

    #: What each provider receives for a command. A provider added to ALL_PROVIDERS
    #: without an entry fails test_every_provider_has_a_renderer.
    RENDERERS = {"claude": _claude.__func__, "opencode": _opencode.__func__, "codex": _codex.__func__}

    def rendered(self, provider, name):
        meta = self.LIB["commands"]["commands"][name]
        _, body = render_provider.parse_frontmatter((REPO_ROOT / "commands" / f"{name}.md").read_text(encoding="utf-8"))
        return self.RENDERERS[provider](name, meta, body, self.LIB["tool_map"])

    def test_every_provider_has_a_renderer(self):
        self.assertEqual(set(self.RENDERERS), set(providers.ALL_PROVIDERS))

    def test_spec_gate_owns_every_section_the_commands_cite(self):
        skill = (REPO_ROOT / "skills" / "shared" / "spec-gate" / "SKILL.md").read_text(encoding="utf-8")
        cited = set()
        for path in (REPO_ROOT / "commands").glob("*.md"):
            cited.update(re.findall(r"§ (Task Resolution|Spec Status|Traceability|Test-First Derivation|Retroactive Spec)", path.read_text(encoding="utf-8")))
        for section in cited:
            self.assertIn("## " + section, skill, section)

    def test_task_resolution_reaches_every_provider(self):
        for provider in providers.ALL_PROVIDERS:
            for name in ("sprint", "backend", "frontend", "fullstack", "mobile", "fix", "qa", "tester"):
                with self.subTest(provider=provider, command=name):
                    text = self.rendered(provider, name)
                    self.assertTrue("Task Resolution" in text or "spec-lint" in text, name)

    def test_the_retroactive_spec_command_reaches_every_provider(self):
        meta = self.LIB["commands"]["commands"]["spec"]
        self.assertEqual((meta["agent"], meta["tier"], meta["interaction_mode"]), ("product-analyst", "reasoning", "required"))
        for provider in providers.ALL_PROVIDERS:
            with self.subTest(provider=provider):
                text = self.rendered(provider, "spec")
                self.assertIn("Retroactive Spec", text)
                self.assertIn("diverges", text)

    def test_codex_exposes_the_command_as_a_skill(self):
        from devteam import command_usage
        self.assertEqual(command_usage.exposed_name("codex", "spec"), "$devteam-spec")

    def test_fix_and_qa_offer_the_retroactive_spec(self):
        for provider in providers.ALL_PROVIDERS:
            for name in ("fix", "qa"):
                with self.subTest(provider=provider, command=name):
                    self.assertIn("Retroactive Spec", self.rendered(provider, name))

    def test_the_contract_template_is_cited_by_its_installed_path(self):
        self.assertTrue((REPO_ROOT / "templates" / "contract-template.md").is_file())
        for rel in ("agents/software-architect.md", "skills/shared/spec-gate/SKILL.md"):
            self.assertIn(".dev-team-agents/templates/contract-template.md", (REPO_ROOT / rel).read_text(encoding="utf-8"), rel)


if __name__ == "__main__":
    unittest.main()
