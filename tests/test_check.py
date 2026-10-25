"""`devteam check` (ADR-0049, docs/specs/devteam-check.md).

Every test builds a throwaway git repository with a `main` branch holding the decisions and a
feature branch holding the change, then runs the real CLI (or `check.run`) against it.
"""

import json
import os
import subprocess
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from devteam_support import REPO_ROOT, StoreTestCase, requires_bash

from devteam import check as check_module
from devteam import providers
from devteam.check import parse_rows
from test_reuse_lint import HEADER, ReuseLintTest

ENV = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@e", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@e")

#: The justification option names where the justification lands: push has no PR body yet.
JUSTIFY = {"push": "Justify in the commit message", "pr": "Justify in the PR body"}
#: Where each provider's rendered command text lands under the render target. Fails when a
#: provider is added without a case. opencode renders every command into one snippet file.
RENDERED = {
    "claude": lambda name: ".claude/commands/devteam/{}.md".format(name),
    "opencode": lambda name: ".opencode/commands.snippet.jsonc",
    "codex": lambda name: ".codex/skills/devteam-{}/SKILL.md".format(name),
}

ADR = (
    "# ADR-0001: Retry policy\n\n**Status:** Accepted\n**Applies to:** `src/*`\n\n"
    "`MAX_RETRIES` is 3 for every outbound call.\n"
)
MODAL = r"| modal | code-pattern | Use the shared Modal | `new Modal\(` | src/Modal.tsx | src/* | | |"


@requires_bash()
class _Branch(StoreTestCase):
    def setUp(self):
        super().setUp()
        self.repo = self.tmp / "app"
        self.repo.mkdir()
        self.git("init", "-q", "-b", "main")
        self.write("README.md", "# app\n")
        self.write("src/Modal.tsx", "export {}\n")

    def git(self, *args):
        subprocess.run(["git", *args], cwd=str(self.repo), check=True, env=ENV, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def write(self, rel, text):
        path = self.repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def commit(self, message="c"):
        self.git("add", "-A")
        self.git("commit", "-qm", message)

    def base(self, adr=ADR, config="MAX_RETRIES = 3\n", rows=()):
        if adr is not None:
            self.write("docs/development/adrs/0001-retry-policy.md", adr)
        if config is not None:
            self.write("src/config.py", config)
        if rows:
            self.write("docs/development/reuse-guidelines.md", HEADER + "".join(r + "\n" for r in rows))
        self.commit("base")
        self.git("checkout", "-q", "-b", "feature")

    def check(self, *extra, base="main"):
        args = ["--json", "check", "--path", str(self.repo)] + (["--base", base] if base else []) + list(extra)
        code, out, err = self.run_cli(*args)
        try:
            data = json.loads(out)
        except ValueError:
            data = {"raw": out, "err": err}
        return code, data

    def kinds(self, data):
        return sorted((f["kind"], f["source_type"], f["source"], f["path"]) for f in data.get("findings", []))

    def conflicts(self, data):
        return [f for f in data.get("findings", []) if f["kind"] == "conflict"]


class CheckAdrTest(_Branch):
    def test_base_adr_with_a_changed_number_is_a_conflict(self):  # [spec:devteam-check#S1] [spec:devteam-check#S7]
        self.base()
        self.write("src/config.py", "MAX_RETRIES = 5\n")
        self.commit()
        code, data = self.check()
        self.assertEqual(code, 1)
        (conflict,) = self.conflicts(data)
        self.assertEqual((conflict["source"], conflict["path"], conflict["line"]), ("ADR-0001", "src/config.py", 1))
        for part in ("MAX_RETRIES", "3", "5", "ADR-0001"):
            self.assertIn(part, conflict["reason"])
        self.assertEqual(data["conflicts"], 1)

    def test_the_working_tree_counts_as_part_of_the_branch(self):  # [spec:devteam-check#S9]
        self.base()
        self.write("src/config.py", "MAX_RETRIES = 5\n")
        self.assertEqual(self.check()[0], 1)

    def test_a_changed_governed_line_not_cited_by_the_adr_is_a_lead(self):  # [spec:devteam-check#S1]
        self.base(config="TIMEOUT = 3\n")
        self.write("src/config.py", "TIMEOUT = 5\n")
        code, data = self.check()
        self.assertEqual(code, 0)
        self.assertEqual(self.kinds(data), [("lead", "adr", "ADR-0001", "src/config.py")])

    def test_the_same_value_or_an_added_only_line_is_not_a_number_change(self):  # [spec:devteam-check#S7]
        self.base()
        self.write("src/config.py", "MAX_RETRIES = 3\nMAX_RETRIES_EXTRA = 9\n# retry\nMAX_RETRIES = 3  # same\n")
        self.assertEqual(self.check()[0], 0)

    def test_a_path_the_adr_does_not_govern_never_conflicts(self):  # [spec:devteam-check#S1]
        self.base(config=None)
        self.write("lib/config.py", "MAX_RETRIES = 3\n")
        self.commit()
        self.write("lib/config.py", "MAX_RETRIES = 5\n")
        code, data = self.check()
        self.assertEqual((code, data["findings"]), (0, []))

    def test_a_proposed_base_adr_does_not_govern(self):  # [spec:devteam-check#S1]
        self.base(adr=ADR.replace("Accepted", "Proposed"))
        self.write("src/config.py", "MAX_RETRIES = 5\n")
        self.assertEqual(self.check()[1]["findings"], [])

    def test_an_adr_introduced_on_the_branch_is_only_a_lead(self):  # [spec:devteam-check#S2]
        self.base(adr=None)
        self.write("docs/development/adrs/0002-retries.md", ADR.replace("0001", "0002"))
        self.write("src/config.py", "MAX_RETRIES = 5\n")
        code, data = self.check()
        self.assertEqual(code, 0)
        self.assertEqual(self.conflicts(data), [])
        self.assertIn(("lead", "adr", "ADR-0002", "src/config.py"), self.kinds(data))

    def test_editing_a_base_adr_is_a_lead_of_its_own_and_not_a_self_conflict(self):  # [spec:devteam-check#S3]
        self.base(adr=ADR.replace("`src/*`", "`src/*`, `docs/*`"))
        self.write("docs/development/adrs/0001-retry-policy.md", ADR.replace("`src/*`", "`src/*`, `docs/*`") + "MAX_RETRIES is 4.\n")
        code, data = self.check()
        self.assertEqual(code, 0)
        self.assertEqual(self.conflicts(data), [])
        self.assertIn(("lead", "adr", "ADR-0001", "docs/development/adrs/0001-retry-policy.md"), self.kinds(data))
        self.assertTrue(any("edits ADR-0001" in f["reason"] for f in data["findings"]))

    def test_rewriting_a_base_adr_never_hides_the_conflict_it_would_remove(self):  # [spec:devteam-check#S3]
        self.base()
        self.write("docs/development/adrs/0001-retry-policy.md", ADR.replace("is 3", "is 5"))
        self.write("src/config.py", "MAX_RETRIES = 5\n")
        code, data = self.check()
        self.assertEqual(code, 1)
        self.assertEqual(len(self.conflicts(data)), 1)
        self.assertTrue(any(f["kind"] == "lead" and "edits ADR-0001" in f["reason"] for f in data["findings"]))

    def test_dropping_the_applies_to_line_on_the_branch_still_conflicts(self):  # [spec:devteam-check#S3]
        self.base()
        self.write("docs/development/adrs/0001-retry-policy.md", ADR.replace("**Applies to:** `src/*`\n", ""))
        self.write("src/config.py", "MAX_RETRIES = 5\n")
        self.assertEqual(self.check()[0], 1)

    def test_an_adr_added_on_the_base_after_the_branch_point_is_not_a_branch_edit(self):  # [spec:devteam-check#S3]
        self.base()
        self.git("checkout", "-q", "main")
        self.write("docs/development/adrs/0002-timeouts.md", ADR.replace("0001", "0002"))
        self.commit("main adds an ADR")
        self.git("checkout", "-q", "feature")
        self.write("README.md", "# app\nx\n")
        _, data = self.check()
        self.assertFalse(any("edits ADR-0002" in f["reason"] for f in data["findings"]))
        self.write("src/config.py", "MAX_RETRIES = 5\n")
        self.assertTrue(any(f["source"] == "ADR-0002" and f["kind"] == "conflict" for f in self.check()[1]["findings"]))

    def test_clean_branch_exits_zero_with_no_findings(self):  # [spec:devteam-check#S8]
        self.base()
        self.write("README.md", "# app\nmore\n")
        code, data = self.check()
        self.assertEqual((code, data["findings"], data["conflicts"], data["leads"]), (0, [], 0, 0))

    def test_no_adr_directory_and_no_reuse_guidelines(self):  # [spec:devteam-check#S14]
        self.base(adr=None, config=None)
        self.write("src/a.py", "x = 1\n")
        code, data = self.check()
        self.assertEqual((code, data["findings"]), (0, []))


class CheckReuseTest(_Branch):
    def test_added_line_matching_a_base_rule_is_a_conflict(self):  # [spec:devteam-check#S4]
        self.base(adr=None, rows=(MODAL,))
        self.write("src/view.ts", "const a = 1\nnew Modal(1)\n")
        code, data = self.check()
        self.assertEqual(code, 1)
        (conflict,) = self.conflicts(data)
        self.assertEqual((conflict["source"], conflict["path"], conflict["line"]), ("modal", "src/view.ts", 2))
        self.assertEqual(conflict["ref"], "src/Modal.tsx")

    def test_advisory_rows_lead_and_out_of_scope_rows_are_silent(self):  # [spec:devteam-check#S5]
        advisory = MODAL.replace("| src/* | | |", "| src/* | advisory | |")
        self.base(adr=None, rows=(advisory,))
        self.write("src/view.ts", "new Modal(1)\n")
        self.write("lib/other.ts", "new Modal(1)\n")
        code, data = self.check()
        self.assertEqual(code, 0)
        self.assertEqual(self.kinds(data), [("lead", "reuse", "modal", "src/view.ts")])

    def test_removed_lines_are_not_checked(self):  # [spec:devteam-check#S6]
        self.write("src/view.ts", "new Modal(1)\n")
        self.base(adr=None, config=None, rows=(MODAL,))
        self.write("src/view.ts", "const ok = 1\n")
        code, data = self.check()
        self.assertEqual((code, data["findings"]), (0, []))

    def test_a_row_added_on_the_branch_is_only_a_lead(self):  # [spec:devteam-check#S4]
        self.base(adr=None, rows=())
        self.write("docs/development/reuse-guidelines.md", HEADER + MODAL + "\n")
        self.write("src/view.ts", "new Modal(1)\n")
        code, data = self.check()
        self.assertEqual(code, 0)
        self.assertEqual(self.kinds(data), [("lead", "reuse", "modal", "src/view.ts")])

    def test_rewriting_or_dropping_a_base_row_never_hides_its_conflict(self):  # [spec:devteam-check#S4]
        self.base(adr=None, rows=(MODAL,))
        self.write("docs/development/reuse-guidelines.md", HEADER)
        self.write("src/view.ts", "new Modal(1)\n")
        code, data = self.check()
        self.assertEqual(code, 1)
        self.assertEqual(len(self.conflicts(data)), 1)
        self.assertTrue(any(f["kind"] == "lead" and "edits or drops" in f["reason"] for f in data["findings"]))

    def test_a_row_added_on_the_base_after_the_branch_point_is_not_a_branch_edit(self):  # [spec:devteam-check#S4]
        self.base(adr=None, rows=(MODAL,))
        self.git("checkout", "-q", "main")
        self.write("docs/development/reuse-guidelines.md", HEADER + MODAL + "\n" + MODAL.replace("modal", "toast").replace("Modal", "Toast") + "\n")
        self.commit("main adds a rule")
        self.git("checkout", "-q", "feature")
        self.write("README.md", "# app\nx\n")
        self.assertFalse(any("edits or drops" in f["reason"] for f in self.check()[1]["findings"]))

    def test_a_catastrophic_pattern_times_out_into_a_lead_and_never_hangs(self):  # [spec:devteam-check#S4]
        row = "| evil | code-pattern | r | `(a+)+$` | src/Modal.tsx | src/* | | |"
        self.base(adr=None, rows=(row,))
        self.write("src/view.ts", "a" * 60 + "!\n")
        with mock.patch.object(check_module, "GREP_TIMEOUT", 1):
            started = time.monotonic()
            result = check_module.run(path=str(self.repo), base="main")
            elapsed = time.monotonic() - started
        self.assertLess(elapsed, 30)
        self.assertEqual(result["conflicts"], 0)
        self.assertTrue(all(f["kind"] == "lead" for f in result["findings"]))
        if elapsed >= 1:
            self.assertTrue(any("timed out" in f["reason"] for f in result["findings"]))

    def test_every_git_call_carries_a_timeout(self):  # [spec:devteam-check#S4]
        self.base()
        with mock.patch.object(check_module.subprocess, "run", wraps=subprocess.run) as spy:
            check_module.run(path=str(self.repo), base="main")
        self.assertTrue(spy.call_args_list)
        for call in spy.call_args_list:
            self.assertIn("timeout", call.kwargs, call.args)

    def test_installed_framework_files_are_never_scanned(self):  # [spec:devteam-check#S4]
        self.base(adr=None, rows=(MODAL,))
        self.write(".dev-team-agents/x.ts", "new Modal(1)\n")
        self.assertEqual(self.check()[1]["findings"], [])


class CheckCommandTest(_Branch):
    def test_exit_three_for_a_missing_base_ref_and_for_a_non_repository(self):  # [spec:devteam-check#S9] [spec:devteam-check#S15]
        self.base()
        code, data = self.check(base="nope")
        self.assertEqual(code, 3)
        self.assertFalse(data.get("ok", False))
        code, _, _ = self.run_cli("--json", "check", "--path", str(self.tmp))
        self.assertEqual(code, 3)

    def test_base_defaults_to_the_origin_default_branch(self):  # [spec:devteam-check#S9]
        self.base()
        self.git("update-ref", "refs/remotes/origin/main", "main")
        self.git("symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/main")
        self.write("src/config.py", "MAX_RETRIES = 5\n")
        code, data = self.check(base=None)
        self.assertEqual((code, data["base"], data["base_resolved_from"]), (1, "origin/main", "origin default branch"))

    def test_the_diff_starts_at_the_merge_base_not_the_base_tip(self):  # [spec:devteam-check#S9]
        self.base()
        self.git("checkout", "-q", "main")
        self.write("src/other.py", "MAX_RETRIES = 9\n")
        self.commit("main moves on")
        self.git("checkout", "-q", "feature")
        self.write("README.md", "# app\nx\n")
        code, data = self.check()
        self.assertEqual((code, data["changed_files"]), (0, 1))

    def test_json_lists_each_finding_with_kind_source_path_and_reason(self):  # [spec:devteam-check#S10]
        self.base()
        self.write("src/config.py", "MAX_RETRIES = 5\n")
        _, data = self.check()
        for key in ("path", "base", "merge_base", "changed_files", "sources", "findings", "conflicts", "leads", "problems"):
            self.assertIn(key, data)
        for finding in data["findings"]:
            self.assertTrue({"kind", "source", "path", "reason"} <= set(finding))
        self.assertEqual(data["problems"], self.conflicts(data))

    def test_text_output_marks_conflicts_and_leads(self):  # [spec:devteam-check#S10]
        self.base()
        self.write("src/config.py", "MAX_RETRIES = 5\n")
        code, out, _ = self.run_cli("check", "--path", str(self.repo), "--base", "main")
        self.assertEqual(code, 1)
        self.assertIn("CONFLICT [ADR-0001] src/config.py:1", out)

    def test_check_active_false_does_not_stop_a_direct_run(self):  # [spec:devteam-check#S13]
        self.base()
        self.write(".dev-team-agents/resolved/preferences.json", json.dumps({"check_active": False}))
        self.write("src/config.py", "MAX_RETRIES = 5\n")
        self.assertEqual(self.check()[0], 1)

    def test_check_active_defaults_to_true(self):  # [spec:devteam-check#S13]
        defaults = json.loads((REPO_ROOT / "scripts" / "lib" / "preferences-defaults.json").read_text())
        self.assertIs(defaults["check_active"], True)


class PreflightParityTest(unittest.TestCase):
    """One procedure in the shared skill, a one-step pointer in each command, on every provider."""

    SKILL = REPO_ROOT / "skills" / "shared" / "git-workflow" / "SKILL.md"

    @classmethod
    def setUpClass(cls):
        cls.out = tempfile.TemporaryDirectory()
        cls.rendered = {}
        for provider in providers.ALL_PROVIDERS:
            target = Path(cls.out.name) / provider
            target.mkdir()
            subprocess.run(
                ["bash", str(REPO_ROOT / "scripts" / "render-provider.sh"), "--provider", provider,
                 "--source-dir", str(REPO_ROOT), "--target-dir", str(target), "--commands-only"],
                check=True, capture_output=True,
            )
            cls.rendered[provider] = {
                name: (target / RENDERED[provider](name)).read_text(encoding="utf-8") for name in ("push", "pr")
            }

    @classmethod
    def tearDownClass(cls):
        cls.out.cleanup()

    def skill_section(self):
        text = self.SKILL.read_text(encoding="utf-8")
        start = text.index("## Decision Check Pre-flight")
        return text[start:]

    def test_every_provider_has_a_case(self):
        self.assertEqual(set(RENDERED), set(providers.ALL_PROVIDERS))

    def test_the_skill_carries_the_one_procedure(self):  # [spec:devteam-check#S11] [spec:devteam-check#S12] [spec:devteam-check#S13] [spec:devteam-check#S15] [spec:devteam-check#S17]
        section = self.skill_section()
        for part in ("devteam --json check", "check_active", "Exit 3", "Fix it first", "Abort", "AskUserQuestion",
                     JUSTIFY["push"], JUSTIFY["pr"]):
            self.assertIn(part, section)

    def test_each_rendered_command_points_at_the_skill_with_its_justification_variant(self):  # [spec:devteam-check#S11] [spec:devteam-check#S12]
        for provider, commands in self.rendered.items():
            for name, text in commands.items():
                with self.subTest(provider=provider, command=name):
                    if provider == "opencode":  # one snippet file holds every command
                        self.assertIn("Decision Check Pre-flight", text)
                        self.assertIn(JUSTIFY[name], text)
                        continue
                    self.assertIn("Decision Check Pre-flight", text)
                    self.assertIn("**{}**".format(JUSTIFY[name]), text)
                    self.assertNotIn(JUSTIFY["pr" if name == "push" else "push"], text)
                    self.assertNotIn("devteam --json check", text)

    def test_the_stop_reminder_still_exists_independently(self):  # [spec:devteam-check#S16]
        self.assertTrue((REPO_ROOT / "scripts" / "hooks" / "stop" / "03h-adr-scope-check.sh").is_file())
        self.assertNotIn("check.py", (REPO_ROOT / "scripts" / "hooks" / "stop" / "03h-adr-scope-check.sh").read_text())


@requires_bash()
class GlobParityTest(unittest.TestCase):
    """`check.py` and the Stop-hook reminder read `**Applies to:**` globs the same way."""

    HOOK = REPO_ROOT / "scripts" / "hooks" / "stop" / "03h-adr-scope-check.sh"
    TABLE = [
        ("src/*", ["src/a.py", "src/deep/a.py", "src", "lib/src/a.py", "srcx/a.py"]),
        ("a?c.py", ["abc.py", "ac.py", "a/c.py", "abbc.py"]),
        ("*.md", ["README.md", "docs/a.md", "a.mdx", "md"]),
        ("docs/**", ["docs/a", "docs/a/b", "docs"]),
        ("a.b/*", ["a.b/x", "aXb/x"]),
        ("x+y/*", ["x+y/a", "xxy/a", "xy/a"]),
        ("(a)/*", ["(a)/b", "a/b"]),
        ("[x]/*", ["[x]/a", "x/a"]),
        ("a|b", ["a|b", "a", "b"]),
        ("$HOME/*", ["$HOME/a", "HOME/a"]),
        ("v{1,2}/*", ["v{1,2}/a", "v1/a"]),
        ("^caret", ["^caret", "caret"]),
        ("back\\slash", ["back\\slash", "backslash"]),
    ]

    def shell_matches(self, pattern, path):
        script = (
            "eval \"$(sed -n '/^glob_to_ere()/,/^}/p' \"$1\")\"; "
            "printf '%s\\n' \"$3\" | grep -Eq \"$(glob_to_ere \"$2\")\""
        )
        return subprocess.run(["bash", "-c", script, "_", str(self.HOOK), pattern, path]).returncode == 0

    def test_the_two_glob_readers_agree(self):
        for pattern, paths in self.TABLE:
            globs = check_module._globs("**Applies to:** `{}`".format(pattern))
            self.assertEqual(len(globs), 1, pattern)
            for path in paths:
                with self.subTest(pattern=pattern, path=path):
                    self.assertEqual(globs[0].fullmatch(path) is not None, self.shell_matches(pattern, path))


@requires_bash()
class ReuseRowParityTest(_Branch):
    """`check.parse_rows` must read a registry the way `scripts/reuse-lint.sh` does (fixtures from test_reuse_lint)."""

    ALT = ReuseLintTest.MODAL  # an escaped-pipe regex alternation
    LINT = REPO_ROOT / "scripts" / "reuse-lint.sh"

    CASES = {
        "alternation first branch": (ALT, "src/a.tsx", "new Modal(1)\n", "blocking"),
        "alternation second branch": (ALT, "src/a.tsx", '<div class="modal">\n', "blocking"),
        "alternation no match": (ALT, "src/a.tsx", "<span>\n", None),
        "scope covers": (ALT.replace("| | | |", "| src/web/* | | |"), "src/web/a.tsx", "new Modal(1)\n", "blocking"),
        "scope excludes": (ALT.replace("| | | |", "| src/web/* | | |"), "src/api/a.ts", "new Modal(1)\n", None),
        "scope star is everywhere": (ALT.replace("| | | |", "| * | | |"), "lib/a.ts", "new Modal(1)\n", "blocking"),
        "scope list": (ALT.replace("| | | |", "| src/api/*, src/web/* | | |"), "src/web/a.ts", "new Modal(1)\n", "blocking"),
        "advisory": (ALT.replace("| | | |", "| | advisory | |"), "src/a.ts", "new Modal(1)\n", "advisory"),
        "blocking explicit": (ALT.replace("| | | |", "| | blocking | |"), "src/a.ts", "new Modal(1)\n", "blocking"),
        "five columns": ("| toast | code-pattern | Use toast | `react-hot-toast` | src/Modal.tsx |", "src/a.ts", "import 'react-hot-toast'\n", "blocking"),
        "backticks and spaces": ("|  toast  | code-pattern | Use toast |  `react-hot-toast`  | src/Modal.tsx | src/* | advisory | |", "src/a.ts", "react-hot-toast\n", "advisory"),
        "posix classes (python re reads them as a plain set)": ("| ticket | code-pattern | Use tickets | `[[:upper:]]{2}-[[:digit:]]+` | src/Modal.tsx | | | |", "src/a.ts", "see AB-12\n", "blocking"),
        "posix classes no match": ("| ticket | code-pattern | Use tickets | `[[:upper:]]{2}-[[:digit:]]+` | src/Modal.tsx | | | |", "src/a.ts", "see d]-12 ab-12\n", None),
        "ere interval and group": ("| retry | code-pattern | Use retry | `(ab){2,3}c` | src/Modal.tsx | | | |", "src/a.ts", "ababc\n", "blocking"),
        "design rule is not mechanical": ("| tone | design-rule | Keep it calm | | | | | |", "src/a.ts", "anything\n", None),
    }

    def lint_verdict(self, name):
        result = subprocess.run(["bash", str(self.LINT)], cwd=str(self.repo), env=ENV, capture_output=True, text=True)
        out = result.stdout + result.stderr
        flagged = [l for l in out.splitlines() if "'{}'".format(name) in l or " {}".format(name) in l]
        if any("BLOCKED" in l for l in flagged):
            return "blocking"
        if any("ADVISORY" in l for l in flagged):
            return "advisory"
        return None

    def check_verdict(self, name):
        _, data = self.check()
        kinds = {f["kind"] for f in data["findings"] if f["source"] == name and f["source_type"] == "reuse"}
        if "conflict" in kinds:
            return "blocking"
        if "lead" in kinds:
            return "advisory"
        return None

    def test_both_read_the_registry_the_same_way(self):  # [spec:devteam-check#S4] [spec:devteam-check#S5]
        for index, (label, (row, path, line, expected)) in enumerate(self.CASES.items()):
            with self.subTest(case=label):
                self.repo = self.tmp / "case{}".format(index)
                self.repo.mkdir()
                self.git("init", "-q", "-b", "main")
                self.write("src/Modal.tsx", "export {}\n")
                self.write("docs/development/reuse-guidelines.md", HEADER + row + "\n")
                self.commit("registry")
                self.git("checkout", "-q", "-b", "feature")
                self.write(path, line)
                name = row.strip("| ").split("|")[0].strip()
                self.assertEqual(self.lint_verdict(name), expected, "reuse-lint.sh disagrees with the fixture")
                self.assertEqual(self.check_verdict(name), expected, "check.py disagrees with reuse-lint.sh")

    def test_parse_rows_reads_cells_like_the_lint(self):  # [spec:devteam-check#S4]
        rows = parse_rows(HEADER + self.ALT + "\n" + "| toast | code-pattern | r | `x` | src/Modal.tsx |\n")
        self.assertEqual([r.name for r in rows], ["modal", "toast"])
        self.assertEqual(rows[0].detect, r'(\bnew Modal\(|<div class="modal)')
        self.assertEqual((rows[1].scope, rows[1].severity), ("", ""))
        self.assertEqual(parse_rows(None), [])


if __name__ == "__main__":
    unittest.main()
