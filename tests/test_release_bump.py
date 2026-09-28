"""Coverage for `.github/scripts/release/bump-homebrew-formula.sh`.

This logic shipped as two inline `run:` blocks in `.github/workflows/release.yml`
and had therefore never executed: the only way to run it was to push a real
`vX.Y.Z` tag. `packaging/README.md` says so outright — "It has never been
triggered". These tests are what replaces "we dry-ran it once by hand".

Every test drives the real bash script through ``subprocess`` against a **copy**
of the real `packaging/homebrew/devteam.rb` in a temp dir, and asserts on the
file content afterwards, never on stdout. Asserting on stdout would pass for a
script that prints the right lines and writes the wrong ones — which is the
failure mode a formula bump actually has.

Unlike the rest of `tests/`, this module does not import ``devteam_support``:
nothing here needs a store or a source tree, and staying import-free keeps the
module runnable both as ``python3 -m unittest tests.test_release_bump`` from the
repo root and under CI's ``unittest discover -s tests -t tests``.

`ArgumentContractTest` covers the flags as the *tests* spell them; that is not
the same thing as covering the flags the *workflow* spells, so
`WorkflowContractTest` extracts the real invocation out of
`.github/workflows/release.yml` and drives the script with it. Without that, a
flag renamed in the script and in this module together would leave the workflow
calling a flag nothing accepts — the one failure the extraction from YAML was
supposed to make testable.

Two of the classes here exist because review found the extracted script accepting
a bump it should have refused, in both cases exiting 0 with a wrong digest on
disk. `ArgumentContractTest` covers the wrong-`--repo` case that the original
wrong-repo test could not reach (its formula still held a placeholder tag, so the
verification missed for the wrong reason), and `AmbiguousFormulaTest` covers a
formula with more than one rewritable line. Both pair the refusal with a run that
must still succeed, because a script that refused everything would otherwise pass
them.
"""

from __future__ import annotations

import os
import re
import shlex
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / ".github" / "scripts" / "release" / "bump-homebrew-formula.sh"
REAL_FORMULA = REPO_ROOT / "packaging" / "homebrew" / "devteam.rb"
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "release.yml"
REPO_SLUG = "Dev-Toolbelt/dev-team-agents"

# Digests that are structurally valid but obviously synthetic, so a leak into a
# real file is recognisable at a glance rather than looking like a stale hash.
DIGEST_A = "a" * 64
DIGEST_B = "0123456789abcdef" * 4

URL_PREFIX = "url \"https://github.com/{}/archive/refs/tags/".format(REPO_SLUG)

# ── The two Homebrew spellings of a digest, and why only one of them counts ──
# The script's sed is anchored on the literal `sha256 "` — `s#(sha256 ")[^"]+(")#`.
# So it rewrites a `sha256 "<hex>"` STRING line, and it cannot touch a
# `sha256 cellar: :any_skip_relocation, arm64_sequoia: "<hex>"` KEYWORD line,
# which is how a perfectly ordinary `bottle do` block spells its per-platform
# digests. Both start with `sha256 `, so a helper that only counted that prefix
# reported six failures for a formula the script had handled correctly — the
# stable digest rewritten, the bottle digests left exactly as they were.
#
# The tripwire the prefix count was there for is still needed, and it is narrower
# than it looked: a SECOND `sha256 "…"` string literal anywhere in the file would
# be clobbered with the release digest by that unanchored pattern. That is the
# case worth failing on. Distinguishing the two shapes is what lets the failure
# message say which of them a contributor is looking at.
def _string_line_re(directive):
    """``<directive> "…"`` occupying the whole (stripped) line."""
    return re.compile(r"^" + re.escape(directive) + r' "[^"]*"$')


def _keyword_line_re(directive):
    """``<directive> <name>: …`` — ruby keyword arguments, e.g. a bottle digest."""
    return re.compile(r"^" + re.escape(directive) + r" [A-Za-z_][A-Za-z0-9_]*:")


class BumpFormulaTestCase(unittest.TestCase):
    """Base: one throwaway copy of the real formula per test."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="release-bump-test-"))
        self.addCleanup(shutil.rmtree, str(self.tmp), True)
        self.formula = self.tmp / "devteam.rb"
        shutil.copyfile(str(REAL_FORMULA), str(self.formula))

    # ── helpers ─────────────────────────────────────────────────────────────

    def bump(self, tag, sha256, formula=None, repo=REPO_SLUG, extra=()):
        """Run the script; returns ``(code, stdout, stderr)``.

        ``--repo`` is always passed explicitly (never left to
        ``GITHUB_REPOSITORY``) so a test's result cannot depend on the
        environment it happens to run in. ``env`` is deliberately empty of that
        variable for the same reason.
        """
        argv = ["bash", str(SCRIPT)]
        if tag is not None:
            argv += ["--tag", tag]
        if sha256 is not None:
            argv += ["--sha256", sha256]
        argv += ["--formula", str(self.formula if formula is None else formula)]
        if repo is not None:
            argv += ["--repo", repo]
        argv += list(extra)

        result = subprocess.run(
            argv,
            cwd=str(self.tmp),
            env={"PATH": "/usr/bin:/bin:/usr/sbin:/sbin"},
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        return (
            result.returncode,
            result.stdout.decode("utf-8", "replace"),
            result.stderr.decode("utf-8", "replace"),
        )

    def read(self):
        return self.formula.read_text(encoding="utf-8")

    def string_literal_line(self, text, directive):
        """The single ``<directive> "…"`` line — the one shape the script rewrites.

        Lines in the other recognised shape (``<directive> <name>: …``, ruby
        keyword arguments — a ``bottle do`` block's per-platform digests are
        spelled that way) are counted separately and ignored: the script's
        pattern requires the literal ``<directive> "`` and provably cannot reach
        them. Anything in neither shape is a hard failure naming the line,
        because this helper then does not know whether the script would rewrite
        it or not, and a guess in either direction is worse than a stop.
        """
        prefix = directive + " "
        candidates = [ln.strip() for ln in text.splitlines() if ln.strip().startswith(prefix)]
        string_re = _string_line_re(directive)
        keyword_re = _keyword_line_re(directive)

        literals = [ln for ln in candidates if string_re.match(ln)]
        keywords = [ln for ln in candidates if not string_re.match(ln) and keyword_re.match(ln)]
        unknown = [ln for ln in candidates if ln not in literals and ln not in keywords]

        if unknown:
            self.fail(
                "unrecognised `{0} …` line shape in the formula:\n  {1}\n"
                "This helper classifies `{0} \"…\"` (the shape the bump script's sed "
                "rewrites) and `{0} <name>: …` (ruby keyword arguments, e.g. a "
                "`bottle do` digest, which that sed cannot reach). It cannot tell "
                "which of the two the line above behaves like, so WIDEN THIS HELPER "
                "— teach _string_line_re/_keyword_line_re the shape — rather than "
                "dropping the check.".format(directive, "\n  ".join(unknown))
            )

        if len(literals) > 1:
            self.fail(
                "the formula carries {0} `{1} \"…\"` string literals:\n  {2}\n"
                "THE SCRIPT WOULD CORRUPT YOUR FORMULA. Its sed pattern is "
                "`s#({1} \")[^\"]+(\")#…#` with no line anchor beyond that, so every "
                "one of those lines is rewritten with the release value. Fix the "
                "script (anchor the pattern at the directive that should change) — "
                "do not relax this assertion.\n"
                "If what you added was a `bottle do` block, its digests are spelled "
                "`sha256 <platform>: \"…\"` and are ignored here precisely because "
                "the script cannot touch them; a plain `{1} \"…\"` is a different "
                "thing.".format(len(literals), directive, "\n  ".join(literals))
            )

        self.assertEqual(
            len(literals),
            1,
            "no `{0} \"…\"` line in the formula at all, so the bump script has "
            "nothing to rewrite (it would exit 1 on its own verification). Lines "
            "starting with `{0} ` that were found, in the keyword-argument shape "
            "the script cannot rewrite: {1}".format(directive, keywords or "none"),
        )
        return literals[0]

    def assert_bumped_to(self, tag, sha256):
        content = self.read()
        self.assertEqual(
            self.string_literal_line(content, "url"),
            '{}{}.tar.gz"'.format(URL_PREFIX, tag),
        )
        self.assertEqual(
            self.string_literal_line(content, "sha256"),
            'sha256 "{}"'.format(sha256),
        )

    def assert_only_url_and_sha256_changed(self, before, after):
        """Every other line is byte-identical.

        This is the assertion that catches a greedy or under-anchored regex —
        the failure mode that has bitten this repository before (an auto-fix
        whose `sed` deleted whole lines it only meant to touch). Line count and
        line order are compared too, so an inserted or dropped line fails here
        even if no surviving line changed.

        The exemption is the two ``<directive> "…"`` string literals and nothing
        else: a `bottle do` block's `sha256 <platform>: "…"` lines also start
        with `sha256 `, and exempting those by prefix would make a rewrite that
        clobbered a bottle digest invisible here.
        """
        before_lines = before.splitlines()
        after_lines = after.splitlines()
        self.assertEqual(
            len(before_lines), len(after_lines), "the rewrite changed the number of lines"
        )
        rewritable = (_string_line_re("url"), _string_line_re("sha256"))
        for index, (old, new) in enumerate(zip(before_lines, after_lines)):
            stripped = old.strip()
            if any(pattern.match(stripped) for pattern in rewritable):
                continue
            self.assertEqual(new, old, "line {} changed but should not have".format(index + 1))

    def assert_untouched(self, before):
        self.assertEqual(self.read(), before, "formula was modified by a run that should have failed")

    LICENSE_LINE = '  license "MIT"'

    def splice_into_formula(self, block):
        """Rewrite the fixture with ``block`` inserted after its `license` line.

        After `license` because that is where Homebrew itself puts `bottle` and
        `resource` blocks, and because it lands the spliced directives *after*
        the stable `url`/`sha256` pair. The stable pair is therefore the first
        occurrence in the file — the ordering that a "rewrite only the first
        match" script would get right by luck. The tests using this helper are
        about the script not depending on that luck.
        """
        original = self.read()
        self.assertIn(
            self.LICENSE_LINE,
            original,
            "the real formula no longer has a `{}` line to splice at, so this "
            "fixture builds nothing".format(self.LICENSE_LINE.strip()),
        )
        mutated = original.replace(self.LICENSE_LINE, self.LICENSE_LINE + "\n" + block, 1)
        self.assertNotEqual(mutated, original, "the fixture splice did not apply")
        self.formula.write_text(mutated, encoding="utf-8")
        return mutated


class RewriteTest(BumpFormulaTestCase):
    """The happy paths, including the one the inline sed was written for."""

    def test_placeholder_formula_gets_the_tag_and_digest(self):
        before = self.read()
        # Guard the fixture itself: if the real formula stops carrying these
        # placeholders, this test would silently stop proving anything.
        self.assertIn("vX.Y.Z.tar.gz", before)
        self.assertIn("REPLACE_WITH_SHA256_OF_RELEASE_TARBALL", before)

        code, _out, err = self.bump("v2.49.0", DIGEST_A)
        self.assertEqual(code, 0, err)
        self.assert_bumped_to("v2.49.0", DIGEST_A)
        self.assert_only_url_and_sha256_changed(before, self.read())

    def test_running_twice_with_the_same_inputs_is_a_no_op(self):
        code, _out, err = self.bump("v2.49.0", DIGEST_A)
        self.assertEqual(code, 0, err)
        once = self.read()

        code, _out, err = self.bump("v2.49.0", DIGEST_A)
        self.assertEqual(code, 0, err)
        self.assertEqual(self.read(), once, "a second identical run changed the file")

    def test_an_already_bumped_formula_is_rewritten_to_a_new_release(self):
        """The second-release case: real tag + real digest already in place.

        The inline sed was written for exactly this — its anchors match "a
        placeholder OR a previous real value" — and it is the one case a first
        release can never exercise, so it had never run.
        """
        code, _out, err = self.bump("v2.49.0", DIGEST_A)
        self.assertEqual(code, 0, err)
        bumped_once = self.read()
        # Asserted on the two lines, not on the whole file: the formula's header
        # comment quotes the placeholder string while explaining it, and that
        # comment must survive the rewrite untouched. (It does go stale once a
        # real bump lands — see the note at the bottom of this module.)
        self.assert_bumped_to("v2.49.0", DIGEST_A)

        code, _out, err = self.bump("v3.0.1", DIGEST_B)
        self.assertEqual(code, 0, err)
        self.assert_bumped_to("v3.0.1", DIGEST_B)
        self.assertNotIn(DIGEST_A, self.read())
        self.assert_only_url_and_sha256_changed(bumped_once, self.read())

    def test_the_rewritten_formula_still_parses_as_ruby(self):
        """Fails — not skips — where ruby is absent.

        This used to `skipTest`. It was the wrong call, and the reason is written
        down elsewhere in this repository: `.github/scripts/ci/04-packaging.sh`
        states "A gate that skips is not a gate", and it backs that up by
        *failing* when ruby is missing rather than skipping its own `ruby -c`
        checks. The asymmetry mattered because the two run in different jobs —
        `.github/workflows/ci.yml`'s `packaging` job installs ruby explicitly, its
        `python` job (which runs this suite) does not, and relies entirely on the
        runner image happening to ship one. A skip there is an unproven formula
        rewrite reported as a pass.

        If this fails in CI, the fix is the same `apt-get install -y ruby` step the
        packaging job already has, added to the python job — not a skip.
        """
        self.assertIsNotNone(
            shutil.which("ruby"),
            "ruby is not on PATH, so it cannot be proved that the rewritten formula "
            "is still valid ruby — and an unrunnable check has not passed. Install "
            "ruby (macOS ships /usr/bin/ruby; Debian: `sudo apt-get install -y "
            "ruby`), the same dependency .github/scripts/ci/04-packaging.sh "
            "requires for its own `ruby -c` gate.",
        )
        code, _out, err = self.bump("v2.49.0", DIGEST_A)
        self.assertEqual(code, 0, err)
        check = subprocess.run(
            ["ruby", "-c", str(self.formula)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(check.returncode, 0, check.stderr.decode("utf-8", "replace"))


class MalformedTagTest(BumpFormulaTestCase):
    """A tag that is not exactly vMAJOR.MINOR.PATCH must not reach the file."""

    def test_malformed_tags_are_refused_and_the_formula_is_untouched(self):
        for tag in (
            "v.1.2.3",      # the dot-before-major typo
            "1.2.3",        # missing the v
            "vX.Y.Z",       # the formula's own placeholder, pasted back in
            "v1.2",         # not three components
            "v1.2.3.4",     # four
            "v1.2.3-rc1",   # pre-release suffix — install.sh resolves plain tags
            "release-1.2.3",
            "",             # empty: must be a usage error, not a wildcard match
        ):
            with self.subTest(tag=tag):
                before = self.read()
                code, _out, err = self.bump(tag if tag else None, DIGEST_A)
                self.assertNotEqual(code, 0, "tag {!r} was accepted".format(tag))
                self.assertTrue(err.strip(), "refusal produced no message on stderr")
                self.assert_untouched(before)


class MalformedDigestTest(BumpFormulaTestCase):
    """The digest is the value users' machines trust — the checks are strict."""

    def test_malformed_digests_are_refused_and_the_formula_is_untouched(self):
        for digest in (
            "abc123",                                     # too short
            DIGEST_A[:63],                                # off by one, short
            DIGEST_A + "a",                               # off by one, long
            DIGEST_A.upper(),                             # uppercase hex
            "g" * 64,                                     # right length, not hex
            DIGEST_A[:-1] + "z",                          # one non-hex character
            "REPLACE_WITH_SHA256_OF_RELEASE_TARBALL",     # the literal placeholder
            "NO_RELEASE_SHA256_DOES_NOT_EXIST_YET",       # the cask's placeholder
            "0" * 64,                                     # winget's visibly-wrong zeros
            "",                                           # empty
        ):
            with self.subTest(digest=digest):
                before = self.read()
                code, _out, err = self.bump("v2.49.0", digest if digest else None)
                if digest == "0" * 64:
                    # Structurally valid hex: the script cannot know it is fake,
                    # and refusing it would mean maintaining a blocklist of
                    # "suspicious" digests. Pinned here so the asymmetry with
                    # the other placeholders is a recorded decision, not a gap.
                    self.assertEqual(code, 0, err)
                    self.assert_bumped_to("v2.49.0", digest)
                    continue
                self.assertNotEqual(code, 0, "digest {!r} was accepted".format(digest))
                self.assertTrue(err.strip(), "refusal produced no message on stderr")
                self.assert_untouched(before)


class ArgumentContractTest(BumpFormulaTestCase):
    """The flag names the workflow is written against, and the --repo fallback."""

    def test_missing_formula_path_is_refused(self):
        code, _out, err = self.bump("v2.49.0", DIGEST_A, formula=self.tmp / "nope.rb")
        self.assertNotEqual(code, 0)
        self.assertIn("not found", err)

    def test_no_repo_and_no_github_repository_fails_instead_of_guessing(self):
        code, _out, err = self.bump("v2.49.0", DIGEST_A, repo=None)
        self.assertNotEqual(code, 0)
        self.assertTrue(err.strip())

    def test_github_repository_is_used_when_repo_is_not_passed(self):
        """Actions never passes --repo; this is the path release.yml takes."""
        before = self.read()
        result = subprocess.run(
            [
                "bash", str(SCRIPT),
                "--tag", "v2.49.0",
                "--sha256", DIGEST_A,
                "--formula", str(self.formula),
            ],
            cwd=str(self.tmp),
            env={"PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "GITHUB_REPOSITORY": REPO_SLUG},
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr.decode("utf-8", "replace"))
        self.assert_bumped_to("v2.49.0", DIGEST_A)
        self.assert_only_url_and_sha256_changed(before, self.read())

    def test_a_wrong_repo_fails_and_leaves_the_formula_byte_identical(self):
        """The url anchor includes owner/repo, so a mismatch matches nothing.

        This is the run that exposes whether the write is staged. The sha256
        anchor is NOT tied to the repo, so it matches and would be rewritten
        while the url anchor misses — meaning an unstaged rewrite leaves a
        formula on disk carrying a new digest against its old url.

        An earlier version of this test asserted exactly that half-written
        state, on the grounds that it was the behaviour carried over from the
        inline `sed`. That was a defect being pinned, not a feature: the only
        thing standing between it and a published bad formula was the workflow
        exiting before its commit step. The script now rewrites into a sibling
        temp file and renames it over the target only after both checks pass, so
        a failed run must leave the formula BYTE-IDENTICAL. Do not weaken this
        assertion back to "the url is still the old one" — that is satisfied by
        the broken behaviour too.
        """
        before = self.read()
        code, _out, err = self.bump("v2.49.0", DIGEST_A, repo="someone-else/other-repo")
        self.assertNotEqual(code, 0)
        self.assertIn("url line was not updated", err)
        self.assertNotIn(DIGEST_A, self.read(), "the digest was written by a run that failed")
        self.assert_untouched(before)

    def test_a_wrong_repo_is_refused_even_when_the_url_already_carries_the_tag(self):
        """The case the test above cannot reach: the url anchor misses, but the
        url already *reads* correct for the requested tag.

        `test_a_wrong_repo_fails_and_leaves_the_formula_byte_identical` bumps a
        PLACEHOLDER formula, so its url says `vX.Y.Z` and the verification —
        whatever it is anchored on — cannot find the requested tag. That run dies
        for the right reason by accident.

        Bump the same formula to a real tag first, and the accident disappears.
        The url line then contains `archive/refs/tags/v1.0.0.tar.gz` no matter
        which repository it points at, and the digest anchor
        (`sha256 "<digest>"`) never carried a repository at all. So with a
        verification anchored on those two fragments, a run passing a WRONG
        `--repo` and a DIFFERENT digest rewrote the digest, left the url alone,
        found both fragments present and exited 0 — the formula on disk claiming
        one repository's digest for another repository's tarball, reported as
        success.

        Which is why the url check is anchored on the whole
        `url "https://github.com/<repo>/archive/refs/tags/<tag>.tar.gz"` line.
        Do not narrow it back to the tag fragment to make some other test pass:
        every assertion below is satisfied by the defective script except the
        exit code and the digest.
        """
        code, _out, err = self.bump("v1.0.0", DIGEST_A)
        self.assertEqual(code, 0, err)
        legitimate = self.read()
        self.assert_bumped_to("v1.0.0", DIGEST_A)

        code, _out, err = self.bump("v1.0.0", DIGEST_B, repo="Attacker/wrong-repo")
        self.assertNotEqual(
            code, 0, "a bump for the wrong repository was accepted and reported success"
        )
        self.assertIn("url line was not updated", err)
        self.assertNotIn(
            DIGEST_B,
            self.read(),
            "the wrong repository's digest was written into the formula",
        )
        self.assert_untouched(legitimate)

    def test_unknown_argument_is_refused(self):
        before = self.read()
        code, _out, err = self.bump("v2.49.0", DIGEST_A, extra=["--force"])
        self.assertNotEqual(code, 0)
        self.assertIn("unknown argument", err)
        self.assert_untouched(before)


class DigestVerificationBranchTest(BumpFormulaTestCase):
    """The `sha256` half of the post-rewrite verification, and its staged write.

    `test_a_wrong_repo_fails_and_leaves_the_formula_byte_identical` above reaches
    the `url` verification branch only: the sha256 anchor is not tied to `--repo`,
    so on that run it always matches. Its mirror needs a formula whose digest is
    not a rewritable string literal, and `sha256 :no_check` is the real Homebrew
    spelling of exactly that. The sed's `(sha256 ")` anchor misses it, the url
    rewrite lands, and the verification has to refuse the whole run.

    Deleting the script's two

        grep -qF "sha256 \\"${SHA256}\\"" "$STAGED" || die "sha256 line was not …"

    lines leaves every other test in this module green. It fails here on all
    three assertions: the exit code, the message, and — the load-bearing one —
    the file, which without those lines lands on disk carrying a NEW url against
    a digest nothing verified.
    """

    def test_a_digest_that_is_not_a_string_literal_fails_and_leaves_the_file_alone(self):
        original = self.read()
        mutated = re.sub(
            r'^(\s*)sha256 "[^"]*"$', r"\1sha256 :no_check", original, flags=re.M
        )
        self.assertNotEqual(
            mutated,
            original,
            "the fixture mutation did not apply — no `sha256 \"…\"` line in the real "
            "formula to turn into `sha256 :no_check`, so this test is proving nothing",
        )
        self.formula.write_text(mutated, encoding="utf-8")
        before = self.read()

        code, _out, err = self.bump("v2.49.0", DIGEST_A)
        self.assertNotEqual(
            code, 0, "a formula whose digest could not be rewritten was accepted"
        )
        self.assertIn("sha256 line was not updated", err)
        self.assertNotIn(
            "v2.49.0", self.read(), "the url was written by a run that failed"
        )
        self.assert_untouched(before)

        # The control, for the same reason EscapedRepoTest runs one: without it a
        # script that refused every formula would also pass the block above. The
        # only difference between the two runs is the digest line's shape.
        self.formula.write_text(original, encoding="utf-8")
        code, _out, err = self.bump("v2.49.0", DIGEST_A)
        self.assertEqual(code, 0, err)
        self.assert_bumped_to("v2.49.0", DIGEST_A)


class AmbiguousFormulaTest(BumpFormulaTestCase):
    """More than one rewritable line → refuse; a `bottle do` block → still bump.

    The two halves are one subject. `sed` replaces every match, and the
    verification afterwards only proves the wanted values are present
    *somewhere*, so a formula carrying two rewritable digests had both replaced
    by the release digest and still exited 0. That is silent corruption of a
    value users' machines are told to trust, and it is invisible to
    `assert_only_url_and_sha256_changed`, which exempts exactly those lines.

    The script refuses that formula rather than rewriting the first match only:
    picking the first is a guess about which digest is the stable one, right for
    a conventionally-ordered formula and silently wrong for any other.

    But a refusal is only correct if it is narrow. The digests in an ordinary
    `bottle do` block are spelled `sha256 <platform>: "…"`, carry no `sha256 "`
    for the anchor to find, and are not ambiguity — a script that refused those
    would refuse the first formula Homebrew ever bottles. That control is the
    second test here, and the distinction between the two is the whole point.
    """

    RESOURCE_BLOCK = """
  resource "vendored" do
    url "https://example.com/vendored-1.2.3.tar.gz"
    sha256 "1111111111111111111111111111111111111111111111111111111111111111"
  end
"""

    # A second url matching the *url* anchor specifically: same repository, same
    # `archive/refs/tags/…tar.gz` shape. A resource url pointing anywhere else
    # (as in RESOURCE_BLOCK above) is provably out of that anchor's reach and
    # must NOT be treated as ambiguous — which the digest test below relies on,
    # since it splices exactly such a url and expects the sha256 branch to fire.
    SECOND_TAG_URL_BLOCK = """
  resource "sibling" do
    url "https://github.com/Dev-Toolbelt/dev-team-agents/archive/refs/tags/v0.0.1.tar.gz"
  end
"""

    BOTTLE_DIGESTS = (
        "2" * 64,
        "3" * 64,
        "4" * 64,
    )
    BOTTLE_BLOCK = """
  bottle do
    sha256 cellar: :any_skip_relocation, arm64_sequoia: "{}"
    sha256 cellar: :any_skip_relocation, ventura:       "{}"
    sha256 cellar: :any_skip_relocation, x86_64_linux:  "{}"
  end
""".format(*BOTTLE_DIGESTS)

    def test_a_second_string_literal_digest_is_refused_and_the_file_is_untouched(self):
        before = self.splice_into_formula(self.RESOURCE_BLOCK)
        self.assertEqual(
            before.count('sha256 "'), 2, "the fixture does not carry two digest literals"
        )

        code, _out, err = self.bump("v2.49.0", DIGEST_A)
        self.assertNotEqual(
            code,
            0,
            "a formula with two rewritable digests was accepted — check whether the "
            "vendored digest now reads as the release digest, because that is what "
            "this run did before the guard existed",
        )
        self.assertIn("sha256", err)
        self.assertIn("Refusing rather than guessing", err)
        self.assertNotIn(
            DIGEST_A, self.read(), "the release digest was written by a run that failed"
        )
        # Byte-identical, and by construction rather than by cleanup: the refusal
        # happens before the staging file is created at all.
        self.assert_untouched(before)

    def test_a_second_url_matching_the_anchor_is_refused(self):
        before = self.splice_into_formula(self.SECOND_TAG_URL_BLOCK)

        code, _out, err = self.bump("v2.49.0", DIGEST_A)
        self.assertNotEqual(code, 0, "a formula with two rewritable urls was accepted")
        self.assertIn("url", err)
        self.assertIn("Refusing rather than guessing", err)
        self.assertNotIn(
            "v2.49.0", self.read(), "the tag was written by a run that failed"
        )
        self.assert_untouched(before)

    def test_a_bottle_blocks_keyword_digests_are_not_ambiguous_and_the_bump_lands(self):
        """The control, and the reason the refusal is counted the way it is.

        Every line in `BOTTLE_BLOCK` starts with `sha256 `, so a guard that
        counted that prefix would refuse this formula — the ordinary output of
        Homebrew bottling the tap's own formula. The script counts what its `sed`
        can actually match (`sha256 "`), which these lines do not carry, so the
        stable digest is rewritten and all three bottle digests survive.
        """
        before = self.splice_into_formula(self.BOTTLE_BLOCK)

        code, _out, err = self.bump("v2.49.0", DIGEST_A)
        self.assertEqual(
            code,
            0,
            "a formula with an ordinary `bottle do` block was refused; the guard is "
            "counting the `sha256 ` prefix instead of the `sha256 \"` the sed "
            "matches.\nstderr:\n{}".format(err),
        )
        self.assert_bumped_to("v2.49.0", DIGEST_A)
        for digest in self.BOTTLE_DIGESTS:
            self.assertIn(
                digest,
                self.read(),
                "bottle digest {}… was clobbered with the release digest".format(
                    digest[:8]
                ),
            )
        # The keyword-argument lines are not exempt from this comparison, so it
        # is what proves they came through byte-identical.
        self.assert_only_url_and_sha256_changed(before, self.read())


class WorkflowContractTest(BumpFormulaTestCase):
    """Drive the script with the flags `.github/workflows/release.yml` really passes.

    Every other test in this module builds its own argv, so the workflow's copy
    of the contract is verified by nothing: rename `--sha256` in the script and in
    `bump()` together and the suite stays green while the release job starts
    failing on `unknown argument: --sha256` — the precise failure that moving the
    logic out of two inline `run:` blocks was supposed to make testable.

    The invocation is extracted textually. The python suite is stdlib-only (3.9
    floor, no pyyaml), and a hand-rolled YAML parser would be a second thing to
    get wrong; but a *silent* extraction failure would turn this into a test that
    always passes, so every step of the extraction fails loudly instead.

    Discriminating in both directions, via one subprocess run:

      * a flag the workflow passes that the script no longer accepts → the script
        exits non-zero with `unknown argument`;
      * a flag the script newly requires that the workflow does not pass → the
        script exits non-zero with `… is required`;
      * a flag the workflow passes that this test cannot supply a value for → a
        hard failure here, not a skip.
    """

    # `--repo` is deliberately absent: the workflow's own comment says it is
    # omitted so the script takes GITHUB_REPOSITORY, and the env below supplies
    # that. If a future workflow does pass `--repo`, it gets this value and the
    # env var is dropped, so the test follows the workflow either way.
    VALUES = {"--tag": "v2.49.0", "--sha256": DIGEST_A}

    def extract_invocation(self):
        """``(script_path, [flags])`` from the one `bash …bump-homebrew-formula.sh` call."""
        basename = SCRIPT.name
        lines = WORKFLOW.read_text(encoding="utf-8").splitlines()
        starts = [
            index
            for index, line in enumerate(lines)
            if line.strip().startswith("bash ") and basename in line
        ]
        self.assertEqual(
            len(starts),
            1,
            "expected exactly one `bash …/{}` invocation in {}, found {}. "
            "If the workflow now invokes the script some other way (a composite "
            "action, a `./` call, a matrix loop), teach this extractor that shape "
            "— a workflow whose invocation cannot be found is a workflow this "
            "test is not checking.".format(basename, WORKFLOW.name, len(starts)),
        )

        index = starts[0]
        collected = []
        while True:
            stripped = lines[index].strip()
            continues = stripped.endswith("\\")
            collected.append(stripped[:-1] if continues else stripped)
            if not continues:
                break
            index += 1
            self.assertLess(
                index, len(lines), "the invocation's line continuation runs off the file"
            )

        tokens = shlex.split(" ".join(collected))
        self.assertEqual(
            "bash", tokens[0], "unexpected invocation shape: {}".format(tokens)
        )
        self.assertTrue(
            tokens[1].endswith(basename), "unexpected script path: {!r}".format(tokens[1])
        )
        return tokens[1], tokens[2:]

    def test_the_workflows_own_flags_drive_the_script_successfully(self):
        script_path, rest = self.extract_invocation()

        # The path the workflow names must be the script this module tests, or the
        # rest of the file is coverage for something the release never runs.
        self.assertTrue(
            (REPO_ROOT / script_path).resolve() == SCRIPT.resolve(),
            "release.yml invokes {!r}, but this module tests {}".format(
                script_path, SCRIPT
            ),
        )

        # Pair the flags with their (shell-expanded) values, so a dangling flag or
        # a positional argument is a failure rather than a silently dropped token.
        self.assertEqual(
            0, len(rest) % 2, "flags and values do not pair up: {}".format(rest)
        )
        pairs = list(zip(rest[::2], rest[1::2]))
        for flag, _value in pairs:
            self.assertTrue(
                flag.startswith("--"), "expected a `--flag`, found {!r}".format(flag)
            )

        argv = ["bash", str(SCRIPT)]
        for flag, workflow_value in pairs:
            if flag == "--formula":
                # The one value that is a real path rather than a shell variable:
                # assert the workflow points at the formula that exists, then swap
                # in the throwaway copy so the run does not rewrite the tree.
                self.assertTrue(
                    (REPO_ROOT / workflow_value).is_file(),
                    "release.yml passes --formula {!r}, which is not a file in this "
                    "tree".format(workflow_value),
                )
                self.assertEqual(
                    REAL_FORMULA.resolve(), (REPO_ROOT / workflow_value).resolve()
                )
                argv += [flag, str(self.formula)]
            elif flag in self.VALUES:
                argv += [flag, self.VALUES[flag]]
            else:
                self.fail(
                    "release.yml passes {!r} and this test has no value to supply "
                    "for it. Add one to WorkflowContractTest.VALUES — a flag the "
                    "workflow passes that the test skips is a flag nothing "
                    "checks.".format(flag)
                )

        env = {"PATH": "/usr/bin:/bin:/usr/sbin:/sbin"}
        if "--repo" not in dict(pairs):
            env["GITHUB_REPOSITORY"] = REPO_SLUG

        before = self.read()
        result = subprocess.run(
            argv,
            cwd=str(self.tmp),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        stderr = result.stderr.decode("utf-8", "replace")
        self.assertEqual(
            0,
            result.returncode,
            "the flags release.yml passes do not drive the script successfully.\n"
            "argv: {}\nstderr:\n{}".format(argv, stderr),
        )
        self.assert_bumped_to("v2.49.0", DIGEST_A)
        self.assert_only_url_and_sha256_changed(before, self.read())


class EscapedRepoTest(BumpFormulaTestCase):
    """`--repo` is interpolated into an ERE, so its metacharacters must be escaped."""

    def test_a_repo_with_a_regex_metacharacter_does_not_match_a_different_repo(self):
        """`Dev.Toolbelt` must not match the literal `Dev-Toolbelt` in the url.

        Deliberately discriminating in both directions, because a test that only
        asserted the failure would also pass for a script that rejects every
        repo it is given:

          * `Dev.Toolbelt/dev-team-agents` differs from the formula's real
            `Dev-Toolbelt/dev-team-agents` by exactly one character, and that
            character is an unescaped-ERE wildcard. Before the escape was added
            the pattern matched, the url line was rewritten to the new tag, both
            verifications passed and the script exited 0 — a bump accepted for
            the wrong repository.
          * the same run with the literal repo, immediately after, must still
            succeed on the same file. That is what proves the failure above came
            from the escaping and not from a blanket refusal.
        """
        before = self.read()
        code, _out, err = self.bump("v2.49.0", DIGEST_A, repo="Dev.Toolbelt/dev-team-agents")
        self.assertNotEqual(
            code, 0, "a repo differing only at a regex metacharacter was accepted"
        )
        self.assertIn("url line was not updated", err)
        self.assert_untouched(before)

        code, _out, err = self.bump("v2.49.0", DIGEST_A, repo=REPO_SLUG)
        self.assertEqual(code, 0, err)
        self.assert_bumped_to("v2.49.0", DIGEST_A)


class NoStrayFilesTest(BumpFormulaTestCase):
    """The rewrite is staged in a sibling temp file, which must never survive.

    The staging file is created next to the formula (same filesystem, so the
    move into place is a rename) and is dot-prefixed, so these assertions list
    the whole directory rather than probing for a name — a hidden leftover is
    still a leftover. The retired `sed -i.bak` backup is covered by the same
    listing.
    """

    def assert_only_the_formula_remains(self):
        self.assertEqual(
            sorted(p.name for p in self.tmp.iterdir()),
            ["devteam.rb"],
            "the rewrite left a stray file behind",
        )

    def test_a_successful_run_leaves_no_temp_or_backup_file(self):
        code, _out, err = self.bump("v2.49.0", DIGEST_A)
        self.assertEqual(code, 0, err)
        self.assert_only_the_formula_remains()

    def test_a_failed_run_leaves_no_temp_or_backup_file(self):
        """The trap path: verification fails after the staging file exists."""
        code, _out, _err = self.bump("v2.49.0", DIGEST_A, repo="someone-else/other-repo")
        self.assertNotEqual(code, 0)
        self.assert_only_the_formula_remains()


class FilePermissionsTest(BumpFormulaTestCase):
    """The rename must not hand the formula the temp file's mode.

    `mktemp` creates its file 0600. A staged rewrite that did not carry the
    target's permission bits across would silently tighten (or, under a
    different umask, loosen) the mode of a file the release PR then commits.
    The fixture is chmod'ed to a mode that is neither 0600 nor the umask
    default, so either accident fails here.
    """

    def test_a_successful_run_preserves_the_permission_bits(self):
        self.formula.chmod(0o640)
        before_mode = self.formula.stat().st_mode & 0o7777
        self.assertEqual(before_mode, 0o640, "the fixture's own chmod did not take")

        code, _out, err = self.bump("v2.49.0", DIGEST_A)
        self.assertEqual(code, 0, err)
        self.assert_bumped_to("v2.49.0", DIGEST_A)
        self.assertEqual(
            self.formula.stat().st_mode & 0o7777,
            before_mode,
            "the rewrite changed the formula's permission bits",
        )

    # ── The two writability preconditions ───────────────────────────────────
    # Both are branched on euid rather than skipped. root ignores permission bits
    # entirely, so under root the condition these tests describe cannot be
    # created — but "the run succeeds" IS the correct behaviour there, and
    # asserting it keeps the test discriminating: a script that had started
    # refusing every formula would still fail this, where a skip would pass.

    def test_a_read_only_formula_is_refused_before_anything_is_staged(self):
        """The formula's own mode matters, even though it is never written in place.

        `cp -p` hands that mode to the staging file, and the rewrite is then
        redirected into the staged copy — so a 0444 formula yields a 0444 staging
        file that `>` cannot open. Without the up-front check the run dies on a
        bare `Permission denied` from the middle of the script, naming a temp file
        the user has never heard of.

        This is why `[ -w "$FORMULA" ]` was kept alongside the directory check
        rather than replaced by it: it guards the `cp -p` + redirect pair, not an
        in-place write. Removing it does not make the bump work on a read-only
        formula; it only makes the failure incomprehensible.
        """
        self.formula.chmod(0o444)
        before = self.read()

        code, _out, err = self.bump("v2.49.0", DIGEST_A)

        if os.geteuid() == 0:
            self.assertEqual(code, 0, err)
            self.assert_bumped_to("v2.49.0", DIGEST_A)
            return

        self.assertNotEqual(code, 0, "a read-only formula was accepted")
        self.assertIn("not writable", err)
        self.assert_untouched(before)
        self.assertEqual(
            sorted(p.name for p in self.tmp.iterdir()),
            ["devteam.rb"],
            "the refused run left a staging file behind",
        )

    def test_a_read_only_directory_is_refused_naming_the_directory(self):
        """The half a file-only check missed: `mktemp` and `mv` both act on the dir.

        A 0666 formula inside a 0555 directory satisfies `[ -w "$FORMULA" ]` and
        fails anyway, because the staging file cannot be created next to it. The
        message has to name the directory — that is the difference between a
        one-line fix and a confused bug report.
        """
        nested = self.tmp / "ro"
        nested.mkdir()
        formula = nested / "devteam.rb"
        shutil.copyfile(str(REAL_FORMULA), str(formula))
        formula.chmod(0o666)
        nested.chmod(0o555)
        # Restored before the tree is removed, or the cleanup leaks a temp dir.
        self.addCleanup(nested.chmod, 0o755)
        before = formula.read_text(encoding="utf-8")

        code, _out, err = self.bump("v2.49.0", DIGEST_A, formula=formula)

        if os.geteuid() == 0:
            self.assertEqual(code, 0, err)
            return

        self.assertNotEqual(
            code, 0, "a formula in a read-only directory was accepted"
        )
        self.assertIn(str(nested), err, "the refusal does not name the directory")
        # The precondition's own message, not `mktemp`'s. Both name the directory,
        # so matching the path alone would pass for a script with no directory
        # check at all — which is exactly the state this test was written against.
        self.assertIn("cannot write in", err)
        self.assertEqual(
            formula.read_text(encoding="utf-8"),
            before,
            "formula was modified by a run that should have failed",
        )


# NOTE — a behaviour preserved here that is arguably wrong, recorded rather than
# fixed because `packaging/homebrew/devteam.rb` is not this module's file:
# the formula's header comment block ("PLACEHOLDER VALUES — replace before this
# formula is published", quoting `REPLACE_WITH_SHA256_OF_RELEASE_TARBALL`) is
# correctly left untouched by the rewrite, which means the published formula will
# carry a comment claiming its own real url/sha256 are placeholders. That is a
# formula-authoring fix, not a rewrite-script one.

if __name__ == "__main__":
    unittest.main()
