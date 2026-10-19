"""The ADR-scope Stop check names the Accepted ADRs whose `Applies to` paths were touched.

It runs the real script against a throwaway git repository and a scratch state
directory — never the developer's own — and drives the touched-path set through the
same environment variables the Stop dispatcher exports.
"""

import os
import subprocess

from devteam_support import REPO_ROOT, StoreTestCase, make_git_project, requires_bash

from devteam import providers

HOOK = REPO_ROOT / "scripts" / "hooks" / "stop" / "03h-adr-scope-check.sh"

#: Whether each provider shows a Stop hook's stderr to the agent — the same split as
#: 03e-adr-gap-check.sh. The script is provider-agnostic; the parity guard fails when a
#: provider is added without deciding its case.
SURFACES_WARNING = {"claude": True, "codex": True, "opencode": False}

ADR_DIR = "docs/development/adrs"


def adr_text(title, status="Accepted", applies=None):
    lines = ["# %s" % title, "", "**Date:** 2026-10-19  ", "**Status:** %s  " % status]
    if applies is not None:
        lines.append("**Applies to:** %s  " % applies)
    lines += ["", "## Context", "", "Text."]
    return "\n".join(lines) + "\n"


@requires_bash()
class AdrScopeCheckTest(StoreTestCase):
    def setUp(self):
        super().setUp()
        self.repo = make_git_project(self.tmp / "app")
        (self.repo / ADR_DIR).mkdir(parents=True)
        self.state = self.tmp / "state"

    def write_adr(self, name, **kwargs):
        (self.repo / ADR_DIR / name).write_text(adr_text("ADR: " + name, **kwargs), encoding="utf-8")

    def run_hook(self, *touched):
        env = dict(
            os.environ,
            USER_DATA_DIR=str(self.state),
            DEVTEAM_TOUCHED_COMPUTED="1",
            DEVTEAM_TOUCHED_PATHS="\n".join(touched),
        )
        env.pop("DEVTEAM_NO_CHANGES", None)
        # The timeout is part of the contract: a crafted pattern must never stall a Stop.
        result = subprocess.run(["bash", str(HOOK)], cwd=str(self.repo), env=env,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=20)
        return result.returncode, result.stderr.decode()

    def test_every_provider_has_a_decided_case(self):
        self.assertEqual(set(SURFACES_WARNING), set(providers.ALL_PROVIDERS))

    def test_warns_once_for_a_governed_path(self):
        for provider in providers.ALL_PROVIDERS:
            with self.subTest(provider=provider):
                self.setUp()
                self.write_adr("0001-bind.md", applies="`src/bind.py`, `scripts/install-*.sh`")
                code, err = self.run_hook("src/bind.py", "README.md")
                self.assertEqual(code, 2)
                self.assertIn("CODE GOVERNED BY AN ADR CHANGED", err)
                self.assertIn("%s/0001-bind.md" % ADR_DIR, err)
                self.assertIn("- src/bind.py", err)
                self.assertNotIn("README.md", err)
                self.assertEqual(self.run_hook("src/bind.py", "README.md"), (0, ""))

    def test_a_new_governed_path_warns_again(self):
        self.write_adr("0001-bind.md", applies="`src/bind.py`, `scripts/install-*.sh`")
        self.assertEqual(self.run_hook("src/bind.py")[0], 2)
        self.assertEqual(self.run_hook("src/bind.py")[0], 0)
        self.assertEqual(self.run_hook("src/bind.py", "scripts/install-codex.sh")[0], 2)

    def test_star_crosses_directories(self):
        self.write_adr("0002-lib.md", applies="`scripts/*.py`")
        code, err = self.run_hook("scripts/lib/devteam/paths.py")
        self.assertEqual(code, 2)
        self.assertIn("- scripts/lib/devteam/paths.py", err)

    def test_an_adr_touched_this_session_is_skipped(self):
        self.write_adr("0001-bind.md", applies="`src/bind.py`")
        self.assertEqual(self.run_hook("src/bind.py", "%s/0001-bind.md" % ADR_DIR), (0, ""))

    def test_only_accepted_adrs_count(self):
        self.write_adr("0001-old.md", status="Superseded by ADR-0002", applies="`src/*`")
        self.write_adr("0003-draft.md", status="Proposed", applies="`src/*`")
        self.assertEqual(self.run_hook("src/bind.py"), (0, ""))

    def test_silent_without_an_applies_to_line(self):
        self.write_adr("0001-bind.md")
        self.assertEqual(self.run_hook("src/bind.py"), (0, ""))

    def test_both_status_spellings_are_read(self):
        (self.repo / ADR_DIR / "0004-madr.md").write_text(
            "# ADR: madr\n\n**Status**: Accepted\n**Applies to**: `src/x.py`\n", encoding="utf-8")
        self.assertEqual(self.run_hook("src/x.py")[0], 2)

    def test_a_pattern_is_never_evaluated(self):
        marker = self.tmp / "pwned"
        self.write_adr("0001-evil.md", applies="`$(touch %s)`, `src/*`" % marker)
        self.assertEqual(self.run_hook("src/a.py")[0], 2)
        self.assertFalse(marker.exists())

    def test_a_symlinked_adr_is_not_read(self):
        outside = self.tmp / "outside.md"
        outside.write_text(adr_text("ADR: outside", applies="`src/*`"), encoding="utf-8")
        (self.repo / ADR_DIR / "0005-link.md").symlink_to(outside)
        self.assertEqual(self.run_hook("src/a.py"), (0, ""))

    def test_a_backtracking_pattern_finishes_fast(self):
        self.write_adr("0001-slow.md", applies="`*a*a*a*a*a*b`, `*a*a*a*a*a*a*a*a*a*a*a*a*b`, `src/*`")
        code, err = self.run_hook("a" * 1000, "src/x.py")
        self.assertEqual(code, 2)
        self.assertIn("- src/x.py", err)
        self.assertNotIn("aaaa", err)

    def test_a_filename_with_a_control_character_is_skipped(self):
        self.write_adr("0001-x\n  - injected.md", applies="`src/*`")
        self.assertEqual(self.run_hook("src/x.py"), (0, ""))

    def test_the_title_is_sanitized_and_capped(self):
        (self.repo / ADR_DIR / "0006-long.md").write_text(
            "# T\x1b[31m" + "x" * 500 + "\n\n**Status:** Accepted\n**Applies to:** `src/*`\n", encoding="utf-8")
        code, err = self.run_hook("src/x.py")
        self.assertEqual(code, 2)
        self.assertNotIn("\x1b", err)
        self.assertNotIn("x" * 250, err)

    def test_regex_metacharacters_in_a_pattern_are_literal(self):
        self.write_adr("0008-meta.md", applies="`src/a.b`, `lib/(x|y).py`")
        self.assertEqual(self.run_hook("src/aXb", "lib/x.py"), (0, ""))
        self.assertEqual(self.run_hook("src/a.b")[0], 2)

    def test_a_filename_with_a_bidi_override_is_skipped(self):
        self.write_adr("0009-x\u202egnp.md", applies="`src/*`")
        self.assertEqual(self.run_hook("src/x.py"), (0, ""))

    def test_an_extended_glob_group_is_skipped(self):
        self.write_adr("0007-ext.md", applies="`+(+(?|??))+(+(?|??))X`, `src/*`")
        code, err = self.run_hook("scripts/lib/devteam/glob", "src/x.py")
        self.assertEqual(code, 2)
        self.assertNotIn("scripts/lib/devteam/glob", err)
