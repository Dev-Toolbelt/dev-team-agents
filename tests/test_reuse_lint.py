"""The reuse-rule lint sees what an agent actually changed, and the Stop hook tells it.

`scripts/reuse-lint.sh` used to check only `<base>...HEAD`, abort under `pipefail` in
a repository without `origin/HEAD`, split a `\\|` regex alternation across table cells,
and treat an invalid regex as "no match". Its Stop hook ran it `--quiet` and passed on
exit 1, which no provider shows the agent. These tests run the real scripts against a
throwaway git repository and a scratch state directory — never the developer's own.
"""

import os
import subprocess

from devteam_support import REPO_ROOT, StoreTestCase, make_git_project, requires_bash

from devteam import providers

LINT = REPO_ROOT / "scripts" / "reuse-lint.sh"
HOOK = REPO_ROOT / "scripts" / "hooks" / "stop" / "03c-reuse-lint.sh"

#: Whether each provider shows a Stop hook's exit-2 stderr to the agent. The scripts are
#: provider-agnostic (no provider variable reaches the Stop environment), so every
#: assertion below holds for all of them; the map records who sees the finding — the
#: opencode plugin logs it instead — and fails when a provider is added undecided.
SURFACES_FINDING = {"claude": True, "codex": True, "opencode": False}

HEADER = "| name | type | rule | detection | canonical_ref | scope | severity | added |\n|---|---|---|---|---|---|---|---|\n"
ENV = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@e", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@e")


@requires_bash()
class ReuseLintTest(StoreTestCase):
    def setUp(self):
        super().setUp()
        self.repo = make_git_project(self.tmp / "app")
        (self.repo / "src" / "api").mkdir(parents=True)
        (self.repo / "src" / "web").mkdir(parents=True)
        (self.repo / "src" / "Modal.tsx").write_text("export {}\n", encoding="utf-8")
        (self.repo / "docs" / "development").mkdir(parents=True)
        self.state = self.tmp / "state"

    def git(self, *args):
        subprocess.run(["git", *args], cwd=str(self.repo), check=True, env=ENV, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def registry(self, *rows):
        (self.repo / "docs" / "development" / "reuse-guidelines.md").write_text(HEADER + "".join(r + "\n" for r in rows), encoding="utf-8")
        self.git("add", "-A")
        self.git("commit", "-qm", "registry")

    def write(self, rel, text):
        path = self.repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def lint(self, *args, env=None):
        result = subprocess.run(["bash", str(LINT), *args], cwd=str(self.repo), env=env or ENV, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return result.returncode, result.stdout.decode() + result.stderr.decode()

    def hook(self):
        env = dict(ENV, USER_DATA_DIR=str(self.state))
        env.pop("DEVTEAM_NO_CHANGES", None)
        result = subprocess.run(["bash", str(HOOK)], cwd=str(self.repo), env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return result.returncode, result.stderr.decode()

    MODAL = r"| modal | code-pattern | Use the shared Modal | `\b(new Modal\(\|<div class=\"modal)` | src/Modal.tsx | | | |"

    def test_absent_registry_is_a_no_op(self):
        self.write("src/a.ts", "new Modal(\n")
        self.assertEqual(self.lint(), (0, ""))

    def test_old_five_column_registry_still_works(self):
        (self.repo / "docs" / "development" / "reuse-guidelines.md").write_text(
            "| name | type | rule | detection | canonical_ref |\n|---|---|---|---|---|\n"
            "| toast | code-pattern | Use toast | `react-hot-toast` | src/Modal.tsx |\n",
            encoding="utf-8",
        )
        self.write("src/a.ts", "import 'react-hot-toast'\n")
        code, out = self.lint()
        self.assertEqual(code, 1)
        self.assertIn("matches 'toast'", out)

    def test_uncommitted_change_without_origin_head_is_caught(self):
        # No remote at all: the old lint aborted with 128 before reading the diff.
        self.registry(self.MODAL)
        self.write("src/a.ts", "const m = new Modal(\n")
        code, out = self.lint()
        self.assertEqual(code, 1, out)
        self.assertIn("src/a.ts: matches 'modal'", out)

    def test_escaped_pipe_alternation_matches_either_branch(self):
        self.registry(self.MODAL)
        self.write("src/b.tsx", '<div class="modal">\n')
        code, out = self.lint()
        self.assertEqual(code, 1, out)
        self.assertNotIn("trailing backslash", out)

    def test_untracked_file_is_checked(self):
        self.registry(self.MODAL)
        self.write("src/new.ts", "x = new Modal(\n")
        self.assertIn("src/new.ts", self.lint()[1])

    def test_committed_change_on_a_branch_is_checked(self):
        self.registry(self.MODAL)
        base = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=str(self.repo), stdout=subprocess.PIPE).stdout.decode().strip()
        self.git("checkout", "-qb", "feature")
        self.write("src/a.ts", "new Modal(\n")
        self.git("add", "-A")
        self.git("commit", "-qm", "feature")
        code, out = self.lint(env=dict(ENV, REUSE_LINT_DIFF_RANGE="%s...HEAD" % base))
        self.assertEqual(code, 1, out)

    def test_scope_limits_a_rule_to_its_paths(self):
        self.registry("| toast | code-pattern | Use toast | `react-hot-toast` | src/Modal.tsx | src/web/* | | |")
        self.write("src/api/x.ts", "import 'react-hot-toast'\n")
        self.assertEqual(self.lint()[0], 0)
        self.write("src/web/deep/y.ts", "import 'react-hot-toast'\n")
        code, out = self.lint()
        self.assertEqual(code, 1)
        self.assertIn("src/web/deep/y.ts", out)
        self.assertNotIn("src/api/x.ts", out)

    def test_advisory_reports_but_passes(self):
        self.registry("| toast | code-pattern | Use toast | `react-hot-toast` | src/Modal.tsx | | advisory | |")
        self.write("src/a.ts", "import 'react-hot-toast'\n")
        code, out = self.lint()
        self.assertEqual(code, 0)
        self.assertIn("ADVISORY", out)

    def test_path_convention(self):
        self.registry("| upl | path-convention | Uploads under src/upload | `path:*Upload*=>src/upload/` | src | | | |")
        self.write("src/FileUpload.ts", "x\n")
        self.assertEqual(self.lint()[0], 1)

    def test_invalid_regex_is_a_finding_not_a_silent_pass(self):
        self.registry("| bad | code-pattern | x | `(unclosed` | src/Modal.tsx | | | |")
        self.write("src/a.ts", "(unclosed\n")
        code, out = self.lint()
        self.assertEqual(code, 1)
        self.assertIn("invalid detection regex", out)

    def test_validate_reports_broken_rows(self):
        self.registry(self.MODAL, "| bad | code-pattern | x | `(unclosed` | gone.ts | | loud | 17/10 |", "| r | review-rule | x | (review-only) | src | src/api/* | | 2026-10-17 |")
        code, out = self.lint("--validate")
        self.assertEqual(code, 1)
        for fragment in ("not a valid extended regex", "'gone.ts' does not exist", "severity must be", "added must be"):
            self.assertIn(fragment, out)
        self.assertNotIn("rule 'modal'", out)
        self.assertNotIn("rule 'r'", out)

    def test_added_line_starting_with_plus_plus_is_content(self):
        # In a hunk, an added `++x;` is the line `+++x;` — not a file header.
        self.registry(r"| inc | code-pattern | No pre-increment | `^\+\+[a-z]` | src/Modal.tsx | | | |")
        self.write("src/a.ts", "x\n")
        self.git("add", "-A")
        self.git("commit", "-qm", "base")
        self.write("src/a.ts", "x\n++counter;\n")
        code, out = self.lint()
        self.assertEqual(code, 1, out)
        self.assertIn("src/a.ts: matches 'inc'", out)

    def test_paths_with_non_ascii_and_spaces_are_reported_exactly(self):
        self.registry(self.MODAL)
        for rel in ("src/\u00e9.ts", "src/sp ace.ts"):
            self.write(rel, "x\n")
        self.git("add", "-A")
        self.git("commit", "-qm", "base")
        for rel in ("src/\u00e9.ts", "src/sp ace.ts"):
            self.write(rel, "x\nnew Modal(\n")
        code, out = self.lint()
        self.assertEqual(code, 1, out)
        self.assertIn("src/\u00e9.ts: matches", out)
        self.assertIn("src/sp ace.ts: matches", out)
        self.assertNotIn("\t", out)

    def test_installed_framework_and_symlinks_are_never_scanned(self):
        self.registry(self.MODAL)
        self.write(".dev-team-agents/skills/x/SKILL.md", "new Modal(\n")
        outside = self.tmp / "outside.ts"
        outside.write_text("new Modal(\n", encoding="utf-8")
        os.symlink(str(outside), str(self.repo / "src" / "link.ts"))
        self.assertEqual(self.lint(), (0, ""))

    def test_user_diff_settings_cannot_switch_the_gate_off(self):
        self.registry(self.MODAL)
        self.write("src/a.ts", "x\n")
        self.git("add", "-A")
        self.git("commit", "-qm", "base")
        self.write("src/a.ts", "x\nnew Modal(\n")
        for key, value in (("diff.noprefix", "true"), ("diff.mnemonicPrefix", "true")):
            with self.subTest(key=key):
                self.git("config", key, value)
                self.assertEqual(self.lint()[0], 1)
                self.git("config", "--unset", key)

    def test_names_git_would_quote_are_still_checked(self):
        self.registry(self.MODAL)
        names = ('src/q"x.ts', "src/back\\slash.ts")
        for rel in names:
            self.write(rel, "x\n")
        self.git("add", "-A")
        self.git("commit", "-qm", "base")
        for rel in names:
            self.write(rel, "x\nnew Modal(\n")
        self.write('src/new"q.ts', "new Modal(\n")
        out = self.lint()[1]
        for rel in names + ('src/new"q.ts',):
            self.assertIn(rel + ": matches", out)

    def test_back_references_are_refused(self):
        self.registry(r"| br | code-pattern | x | `(a)\1` | src/Modal.tsx | | | |")
        code, out = self.lint("--validate")
        self.assertEqual(code, 1)
        self.assertIn("back-references", out)

    def test_large_untracked_file_is_skipped_and_said(self):
        self.registry(self.MODAL)
        self.write("src/big.ts", "new Modal(\n" + "x" * 1100000 + "\n")
        code, out = self.lint()
        self.assertEqual(code, 0)
        self.assertIn("SKIPPED", out)

    def test_validate_flags_an_unescaped_pipe(self):
        self.registry("| p | code-pattern | x | `a|b` | src/Modal.tsx | | | |")
        code, out = self.lint("--validate")
        self.assertEqual(code, 1)
        self.assertIn("cells (max 8)", out)

    def test_every_provider_has_a_decided_case(self):
        self.assertEqual(set(SURFACES_FINDING), set(providers.ALL_PROVIDERS))

    def test_hook_exits_2_once_per_set_of_findings(self):
        for provider in providers.ALL_PROVIDERS:
            with self.subTest(provider=provider):
                self.setUp()
                self.registry(self.MODAL)
                self.write("src/a.ts", "new Modal(\n")
                code, err = self.hook()
                self.assertEqual(code, 2)
                self.assertIn("REUSE RULE VIOLATION", err)
                self.assertIn("src/a.ts", err)
                self.assertEqual(self.hook(), (0, ""))
                self.write("src/b.ts", "new Modal(\n")
                self.assertEqual(self.hook()[0], 2)

    def test_hook_warns_again_when_findings_return_after_a_clean_run(self):
        self.registry(self.MODAL)
        self.write("src/a.ts", "new Modal(\n")
        self.assertEqual(self.hook()[0], 2)
        (self.repo / "src" / "a.ts").unlink()
        self.assertEqual(self.hook(), (0, ""))
        self.write("src/a.ts", "new Modal(\n")
        self.assertEqual(self.hook()[0], 2)

    def test_hook_stays_quiet_on_advisory_only(self):
        self.registry("| toast | code-pattern | Use toast | `react-hot-toast` | src/Modal.tsx | | advisory | |")
        self.write("src/a.ts", "import 'react-hot-toast'\n")
        self.assertEqual(self.hook(), (0, ""))
