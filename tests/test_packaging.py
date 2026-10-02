"""The distribution scaffold in ``packaging/`` — does the declared payload run?

``packaging/homebrew/devteam.rb`` has never been through ``brew install`` (there
is no tap — see ``packaging/README.md``), so nothing has ever proved that the
files its ``install`` block picks out are *enough* to start the CLI. That is the
gap this module closes: it reads the payload out of the formula, stages exactly
those paths into a temp tree with the formula's own layout and shebang rewrite,
and runs the result. A missing module shows up here as an ``ImportError`` from a
real subprocess, not as a bug report from the first person to ``brew install``.

Two rules shape the code below:

* **The payload is parsed, never hardcoded.** A hardcoded file list would keep
  passing after someone edited the formula, which is the one failure this module
  exists to catch. Any line *containing* ``.install`` that the parser does not
  understand is a hard failure naming the line, never a skip — but see "What this
  module does not prove" below for the lines it never looks at.
* **Nothing imports the ``devteam`` package.** Unlike the rest of the suite this
  module does not use ``devteam_support``: importing the package would put the
  *repository's* ``scripts/lib`` on ``sys.path`` and quietly satisfy imports the
  staged payload is missing. ``REPO_ROOT`` is therefore derived locally, and the
  staged CLI is only ever reached through ``subprocess``.

WHAT THIS MODULE DOES NOT PROVE
===============================
Stated because a green run here reads like "the formula is fine", and these are
the edges of that claim.

* **Only the ``.install`` lines of the ``install`` block are read.** The parser
  collects what those lines stage and proves that set is *sufficient* to start
  the CLI. It says nothing about the rest of the block: a subsequent
  ``rm_f libexec/"scripts/lib/devteam/registry.py"``, a ``mv``, a conditional, or
  any other ruby is invisible to it, so it cannot prove nothing *subtracts* from
  the payload afterwards. Every test here would stay green while ``brew install``
  shipped a package missing a module the CLI imports at startup. Deciding what
  the parser should do about arbitrary ruby is a bigger question than this
  module; the honest position is that the ``.install`` lines are checked and the
  rest of the block is not.
* **Nothing here checks that the declared python still exists in homebrew-core.**
  ``depends_on "python@X.Y"`` is pinned against the formula's own derivation of
  the interpreter (see ``test_python_dependency_and_interpreter_path_name_the_same_formula``),
  which is an internal-consistency check: it cannot tell whether homebrew-core
  still ships that formula. Only ``packaging/verify-formula-locally.sh`` resolves
  the real ``brew info python3`` and reports the drift, and it needs ``brew``, so
  it runs on no CI job that runs this suite. That drift is not hypothetical — the
  formula's own comment records it happening once already, from ``python@3.12``.
  It is named here rather than tested because a test for it would have to reach
  the network or shell out to Homebrew, and this module does neither.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FORMULA = REPO_ROOT / "packaging" / "homebrew" / "devteam.rb"
CASK = REPO_ROOT / "packaging" / "homebrew" / "devteam-app.rb"

# The `def install ... end` method body, matched on the two-space indent Homebrew
# formulas use for method definitions. Anchored rather than "first `end` found",
# so a future nested block inside `install` does not truncate the payload.
INSTALL_BLOCK_RE = re.compile(r"^  def install$(.*?)^  end$", re.M | re.S)

# The two line shapes the formula uses today. Both install *into* the parenthesised
# libexec directory, which is Homebrew's semantics for `(dir).install <src>`.
FILE_INSTALL_RE = re.compile(r'^\(libexec/"([^"]+)"\)\.install\s+"([^"]+)"$')
GLOB_INSTALL_RE = re.compile(r'^\(libexec/"([^"]+)"\)\.install\s+Dir\["([^"]+)"\]$')

# `\.install\b` deliberately does not match `.install_symlink` (`_` is a word
# character, so the boundary fails there) — the symlink line is asserted
# separately and is not part of the copied payload.
ANY_INSTALL_RE = re.compile(r"\.install\b")

INREPLACE_RE = re.compile(
    r'^inreplace\s+libexec/"([^"]+)",$\s*^"([^"]+)",$\s*^"(#!#\{python3\})"$',
    re.M,
)

SHEBANG_SYMLINK_RE = re.compile(
    r'^bin\.install_symlink\s+libexec/"([^"]+)"\s*=>\s*"([^"]+)"$', re.M
)

IMPORT_FAILURE_RE = re.compile(r"\b(ImportError|ModuleNotFoundError)\b")

# ── The python the formula installs, and the one it invokes ──────────────────
# The version used to be written three times (`depends_on`, the `Formula[...]`
# lookup, the `pythonX.Y` basename) and drifted: the formula still said
# python@3.12 after homebrew-core's python3 had moved on. It now appears once,
# on `depends_on`, and `install` derives the interpreter from that dependency.
# The regexes below pin both halves of that derivation, so a rewrite that
# reintroduces a second literal fails here rather than at someone's shebang.
# Not `$`-anchored, because the tool this assertion exists to protect is not
# either: `packaging/verify-formula-locally.sh` reads the dependency with
#     awk '/^[[:space:]]*depends_on[[:space:]]*"python@/ { match($0, /"[^"]+"/); … }'
# which takes the FIRST quoted string on the line and tolerates anything after
# it. An anchored regex here refused `depends_on "python@3.14" # was python@3.12`
# — a line the tool reads perfectly well — and reported it as "no depends_on line
# in the formula", which sends a contributor looking for a missing line that is
# right there. The assertion loses nothing by matching what awk matches: what
# makes a second python version impossible is PY_DEP_LITERAL_RE counting the
# literals, not the end-of-line anchor.
DEPENDS_ON_PY_RE = re.compile(r'^depends_on\s*"python@(\d+\.\d+)"', re.M)

# `<local> = deps.find { |dep| dep.name.start_with?("python@") }&.name` — the
# backreference forces the block parameter and its use to be the same name.
PY_DEP_LOOKUP_RE = re.compile(
    r'^(\w+) = deps\.find \{ \|(\w+)\| \2\.name\.start_with\?\("python@"\) \}&\.name$',
    re.M,
)

# `python3 = formula_opt_bin(<local>)/<local>.sub("@", "")` — again backreferenced,
# so the directory and the basename cannot be built from different variables.
PY_INTERPRETER_RE = re.compile(
    r'^python3 = formula_opt_bin\((\w+)\)/\1\.sub\("@", ""\)$',
    re.M,
)

PY_DEP_LITERAL_RE = re.compile(r'"python@\d+\.\d+"')
PY_BASENAME_LITERAL_RE = re.compile(r'"python\d+\.\d+"')


def code_only(text):
    """``text``'s lines, indentation stripped and whole-line comments dropped.

    Used for the formula and for the CLI entry point — both are files whose
    comments quote the very strings the assertions look for, and ``#`` starts a
    comment in ruby and python alike.

    The formula's header and its `depends_on` comment name python versions in
    prose on purpose — that drift is the reason the derivation exists — so
    counting version literals has to look at code, or it would count the
    narrative. The entry point has the same hazard in the other direction: a
    bootstrap replaced by an absolute path, with the old expression preserved in a
    `# was: …` note, satisfies a raw substring check.

    Bound: only WHOLE-LINE comments are dropped, so a trailing `code  # comment`
    keeps its comment. That is deliberate — stripping trailing `#` correctly
    needs a real tokeniser for either language (`"#!#{python3}"` in the formula is
    a `#` inside a string) — and it is sufficient for both files, where no code
    line starts with `#`.
    """
    return "\n".join(
        stripped
        for stripped in (line.strip() for line in text.splitlines())
        if not stripped.startswith("#")
    )


def parse_install_payload(formula_text):
    """Return ``[(libexec_relative_dir, [repo-relative source paths])]``.

    Raises ``ValueError`` naming the offending line for anything it cannot read.
    A parser that shrugged and skipped would report a green payload test for a
    formula that installs nothing.
    """
    block = INSTALL_BLOCK_RE.search(formula_text)
    if block is None:
        raise ValueError("no `def install` ... `end` block found in the formula")

    payload = []
    for raw in block.group(1).splitlines():
        line = raw.strip()
        if not ANY_INSTALL_RE.search(line):
            continue
        single = FILE_INSTALL_RE.match(line)
        if single:
            payload.append((single.group(1), [single.group(2)]))
            continue
        globbed = GLOB_INSTALL_RE.match(line)
        if globbed:
            # `is_file()` filters directories out. `Dir[…]` in ruby returns them
            # too, and a glob wide enough to match one (`scripts/lib/devteam/*`,
            # say) made `setUp` die with `IsADirectoryError` from `shutil.copy2`
            # as soon as `__pycache__` existed — which on CI is always, since
            # `.github/scripts/ci/03-python.sh` runs `compileall` before the
            # tests. Skipping is also the more faithful staging: `brew install`
            # builds from a git tag tarball, which carries no `__pycache__`.
            # A glob that matched nothing but directories still fails below.
            matched = sorted(
                str(p.relative_to(REPO_ROOT))
                for p in REPO_ROOT.glob(globbed.group(2))
                if p.is_file()
            )
            if not matched:
                raise ValueError(
                    "the formula's glob matches nothing in this tree: "
                    "Dir[{!r}] — the package was probably moved or renamed, and "
                    "`brew install` would stage an empty directory".format(globbed.group(2))
                )
            payload.append((globbed.group(1), matched))
            continue
        raise ValueError(
            "unrecognised install line in the formula: {!r}\n"
            "This test stages the payload by parsing these lines, so an "
            "unparsed shape means the payload is no longer being verified. "
            "Teach FILE_INSTALL_RE / GLOB_INSTALL_RE the new shape rather "
            "than relaxing the parser.".format(line)
        )
    if not payload:
        raise ValueError("the formula's `install` block installs nothing into libexec")
    return payload


class FormulaPayloadTest(unittest.TestCase):
    """Parsing and cross-checking the formula without running anything."""

    def setUp(self):
        self.formula_text = FORMULA.read_text(encoding="utf-8")

    def payload(self):
        try:
            return parse_install_payload(self.formula_text)
        except ValueError as exc:
            self.fail(str(exc))

    def test_every_install_line_parses_and_resolves(self):
        # Catches an install line pointing at a path that no longer exists — the
        # formula would fail at `brew install` time with a Homebrew error that
        # names a tarball path, not the source file someone renamed here.
        for dest, sources in self.payload():
            self.assertTrue(dest.startswith("scripts/"), "unexpected libexec dest: " + dest)
            for source in sources:
                self.assertTrue(
                    (REPO_ROOT / source).is_file(),
                    "formula installs {!r}, which does not exist in this tree".format(source),
                )

    def test_entry_point_finds_its_package_as_a_sibling_under_scripts(self):
        # The formula's comment justifies its two-directory layout with this exact
        # expression. Asserting it against the real file means a refactor of the
        # entry point's bootstrap cannot silently invalidate the formula's reason
        # for preserving `scripts/cli` and `scripts/lib` as siblings.
        #
        # Compared against `code_only()`, not the raw text: the assertion passed
        # for an entry point whose bootstrap had been replaced by an absolute path
        # with the old expression left behind in a `# was: …` comment — which is
        # precisely how such a refactor gets written, and precisely the case this
        # is supposed to catch. Same helper the formula checks use; see its
        # docstring for the one bound (whole-line comments only).
        entry = (REPO_ROOT / "scripts" / "cli" / "devteam").read_text(encoding="utf-8")
        self.assertIn(
            'Path(__file__).resolve().parent.parent / "lib"',
            code_only(entry),
            "scripts/cli/devteam no longer bootstraps `scripts/lib` as a sibling "
            "of its own directory. packaging/homebrew/devteam.rb preserves that "
            "exact layout in libexec because of this expression — if the bootstrap "
            "changed, the formula's install block has to change with it.",
        )

    def test_package_holds_only_python_files_so_the_glob_covers_it(self):
        # The formula stages `scripts/lib/devteam/*.py`. A data file added to the
        # package (a JSON schema, a bundled template) would be silently left out
        # of the bottle and fail at runtime for brew users only. If this fails,
        # either move the data file out of the package or widen the formula's
        # glob — do not delete this test.
        # A subpackage is covered only by its own `Dir[".../<name>/*.py"]` line.
        package = REPO_ROOT / "scripts" / "lib" / "devteam"
        formula = FORMULA.read_text(encoding="utf-8")
        strays = sorted(
            str(entry.relative_to(package))
            for entry in package.rglob("*")
            if "__pycache__" not in entry.parts
            and (
                (entry.is_file() and entry.suffix != ".py")
                or (entry.is_dir() and 'Dir["scripts/lib/devteam/{}/*.py"]'.format(
                    entry.relative_to(package).as_posix()) not in formula)
            )
        )
        self.assertEqual(
            [],
            strays,
            "non-.py files in scripts/lib/devteam/ are not matched by the "
            "formula's Dir[\"scripts/lib/devteam/*.py\"] glob: {}".format(strays),
        )

    def test_shebang_rewrite_has_something_to_rewrite(self):
        # `inreplace` raises when its search string is absent, so a changed
        # shebang in the entry point breaks `brew install` outright. Assert the
        # formula's search string and the real first line still agree.
        match = INREPLACE_RE.search("\n".join(
            line.strip() for line in self.formula_text.splitlines()
        ))
        self.assertIsNotNone(
            match, "could not find the formula's `inreplace` of the shebang"
        )
        target, search, replacement = match.group(1), match.group(2), match.group(3)
        # The replacement must interpolate the `python3` local the `install` block
        # derives from the declared dependency. A hardcoded `#!/usr/bin/env python3`
        # or a literal path here would ignore `depends_on` entirely and leave brew
        # users on whatever python their PATH happens to have.
        self.assertEqual("#!#{python3}", replacement)
        self.assertIsNotNone(
            PY_INTERPRETER_RE.search(code_only(self.formula_text)),
            "the interpolated `python3` is not assigned from the declared dependency",
        )
        installed_names = {
            "{}/{}".format(dest, Path(source).name)
            for dest, sources in self.payload()
            for source in sources
        }
        self.assertIn(
            target,
            installed_names,
            "the formula rewrites {!r}, which its install block never staged".format(target),
        )
        source_file = Path(target).name
        first_line = (REPO_ROOT / "scripts" / "cli" / source_file).read_text(
            encoding="utf-8"
        ).splitlines()[0]
        self.assertEqual(search, first_line)

    def test_symlinked_binary_points_at_a_staged_file(self):
        # `bin.install_symlink` is the only thing that puts `devteam` on PATH, and
        # it repeats the libexec path by hand. If the install block's destination
        # moves and this line does not, brew installs a dangling symlink — and the
        # cask below depends on that exact binary name existing.
        match = SHEBANG_SYMLINK_RE.search("\n".join(
            line.strip() for line in self.formula_text.splitlines()
        ))
        self.assertIsNotNone(match, "the formula no longer symlinks a binary into bin")
        libexec_path, binary_name = match.group(1), match.group(2)
        self.assertEqual("devteam", binary_name)
        installed_names = {
            "{}/{}".format(dest, Path(source).name)
            for dest, sources in self.payload()
            for source in sources
        }
        self.assertIn(libexec_path, installed_names)

    def test_python_dependency_and_interpreter_path_name_the_same_formula(self):
        # Brew must not install one python and invoke another. The formula makes
        # that impossible by construction rather than by agreement: the version is
        # written once, on `depends_on`, and `install` reads it back off `deps`.
        # This test asserts the construction — that there is exactly one literal,
        # and that the interpreter really is derived from it.
        code = code_only(self.formula_text)

        declared = DEPENDS_ON_PY_RE.search(code)
        self.assertIsNotNone(
            declared,
            "no `depends_on \"python@X.Y\"` line in the formula. "
            "packaging/verify-formula-locally.sh finds the dependency by that "
            "prefix (leading whitespace and a trailing comment are fine; it takes "
            "the first quoted string on the line) and resolves it against `brew "
            "info python3` to report drift, so the literal stays.",
        )
        version = declared.group(1)

        # One literal, and it is the `depends_on` one. This is the assertion that
        # replaces comparing two hand-written versions: a second site cannot drift
        # from the first if there is no second site.
        literals = PY_DEP_LITERAL_RE.findall(code)
        self.assertEqual(
            ['"python@{}"'.format(version)],
            literals,
            "the python version must appear exactly once in the formula's code, on "
            "the `depends_on` line — `install` derives the interpreter from it. "
            "Found: {}".format(literals),
        )
        # Nor may the `pythonX.Y` basename be written out again: that was the third
        # of the three original sites, and the one whose drift only surfaces as a
        # shebang pointing at a file that is not in the dependency's opt_bin.
        self.assertEqual(
            [],
            PY_BASENAME_LITERAL_RE.findall(code),
            "the interpreter basename is derived from the dependency name; do not "
            "hardcode `pythonX.Y`",
        )

        # The derivation itself, both halves, on the same local variable.
        lookup = PY_DEP_LOOKUP_RE.search(code)
        self.assertIsNotNone(
            lookup,
            "`install` no longer reads the python dependency off `deps`. If the "
            "derivation was rewritten, teach PY_DEP_LOOKUP_RE the new spelling — "
            "do not drop the assertion, or the two can silently disagree again.",
        )
        interpreter = PY_INTERPRETER_RE.search(code)
        self.assertIsNotNone(
            interpreter,
            "`python3` is no longer built as `formula_opt_bin(<dep>)/<dep>.sub(\"@\", \"\")`",
        )
        self.assertEqual(
            lookup.group(1),
            interpreter.group(1),
            "`install` looks up the dependency into `{}` but builds the interpreter "
            "from `{}` — brew would install one python and invoke another".format(
                lookup.group(1), interpreter.group(1)
            ),
        )

        # NOTE — there was an assertion here that the formula's `python@X.Y` ->
        # `pythonX.Y` transformation produces the right basename, written as
        #     derived = "python@{}".format(version).replace("@", "", 1)
        #     self.assertEqual("python" + version, derived)
        # Both sides were computed from `version` alone, so it asserted a property
        # of `str.replace` and held for every possible input — including a formula
        # with no `.sub("@", "")` in it at all. The formula's real transformation is
        # already pinned, by PY_INTERPRETER_RE above: that regex matches only
        # `.sub("@", "")` on the same local the lookup assigned, so a rewrite to
        # `.sub("@", "-")` or to a different variable fails there. Nothing is lost
        # by its absence; re-adding it would need ruby in the loop to mean anything.

    def test_cask_still_depends_on_the_cli_formula(self):
        # ADR-0011 decided the app is a client of the CLI; the architecture review
        # of M4.1 found this line missing and named the failure it allows (an older
        # CLI writing a newer store). Its removal is a regression, not a cleanup.
        cask_text = CASK.read_text(encoding="utf-8")
        self.assertIsNotNone(
            re.search(r'^\s*depends_on\s+formula:\s*"devteam"\s*$', cask_text, re.M),
            "packaging/homebrew/devteam-app.rb no longer declares "
            "`depends_on formula: \"devteam\"` (ADR-0011)",
        )

    def test_cask_version_sha256_and_url_agree_with_each_other(self):
        # `.github/scripts/ci/04-packaging.sh` checks exactly this class of
        # consistency for the three winget manifests — version, digest and
        # InstallerUrl must be on the scaffold together or off it together, because
        # a hand-coordinated bump lands in some of the places and not the others.
        # The cask got no equivalent check at all: its three values could disagree
        # in any combination and CI would stay green (its only cask assertion is an
        # advisory grep for the sha256 placeholder string).
        #
        # WHAT CANNOT BE ASSERTED HERE: the artifact does not exist. There is no
        # `.dmg` to hash, so nothing can prove the digest is the digest OF the
        # download, nor that the url resolves, nor that the version matches an
        # `Info.plist`. `packaging/verify-formula-locally.sh` has no cask mode, and
        # `brew audit --cask` (which would check codesign and notarisation) cannot
        # pass until a signed build ships. What is checkable is that the three
        # values tell the same story — which is what the winget checks do too.
        cask_text = CASK.read_text(encoding="utf-8")
        code = code_only(cask_text)

        version = re.search(r'^version "([^"]+)"$', code, re.M)
        self.assertIsNotNone(version, "the cask no longer declares a `version`")
        digest = re.search(r'^sha256 "([^"]+)"$', code, re.M)
        self.assertIsNotNone(digest, "the cask no longer declares a `sha256`")
        url = re.search(r"^url \"([^\"]+)\"$", code, re.M)
        self.assertIsNotNone(url, "the cask no longer declares a `url`")

        version, digest, url = version.group(1), digest.group(1), url.group(1)

        # The url must build its paths from `#{version}`, never repeat the literal.
        # This is the same one-site rule the formula's python dependency follows,
        # and the reason is the same: two hand-written copies of a version drift,
        # and here the drift means a cask that downloads the wrong release.
        self.assertIn(
            "#{version}",
            url,
            "the cask's url does not interpolate `#{{version}}`: {!r}. A literal "
            "version in the url is a second site to bump.".format(url),
        )
        self.assertNotIn(
            version,
            url.replace("#{version}", ""),
            "the cask's url repeats the literal version {!r} as well as "
            "interpolating it: {!r}".format(version, url),
        )

        # Version and digest must be on the same side of "has this shipped?".
        # A real 64-hex digest under a placeholder version (or a placeholder digest
        # under a real version) is the half-finished bump, and it is the state that
        # reads as released without being releasable.
        unreleased_version = version == "0.0.0-unreleased"
        unreleased_digest = digest == "NO_RELEASE_SHA256_DOES_NOT_EXIST_YET"
        self.assertEqual(
            unreleased_version,
            unreleased_digest,
            "the cask's version and sha256 disagree about whether the app has "
            "shipped: version {!r}, sha256 {!r}. Both are placeholders today (see "
            "the file's own header and packaging/README.md); when a real build "
            "ships, both change in the same commit.".format(version, digest),
        )
        if not unreleased_digest:
            self.assertRegex(
                digest,
                r"^[0-9a-f]{64}$",
                "the cask declares a non-placeholder sha256 that is not 64 "
                "lowercase hex characters — `brew install` refuses that outright",
            )


#: This class runs the staged entry point **through its own ``#!`` line**, which
#: Windows does not honour, and it chmods that file executable, which NTFS has no
#: notion of. ``FormulaPayloadTest`` above only reads the formula's text and stays
#: portable, so the gate is per-class rather than per-module.
#:
#: Defined locally, not imported: this module deliberately does not import
#: ``devteam_support`` (see the module docstring above).
_requires_shebangs = unittest.skipUnless(
    os.name == "posix", "the staged CLI is invoked through a #! line"
)


@_requires_shebangs
class StagedPayloadRunTest(unittest.TestCase):
    """Stage the formula's payload for real, then run the CLI out of it."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="devteam-packaging-"))
        self.addCleanup(shutil.rmtree, str(self.tmp), True)
        self.libexec = self.tmp / "libexec"
        try:
            payload = parse_install_payload(FORMULA.read_text(encoding="utf-8"))
        except ValueError as exc:
            self.fail(str(exc))

        for dest, sources in payload:
            target_dir = self.libexec / dest
            target_dir.mkdir(parents=True, exist_ok=True)
            for source in sources:
                shutil.copy2(str(REPO_ROOT / source), str(target_dir / Path(source).name))

        # The formula's `inreplace`, applied verbatim but pointed at the interpreter
        # running this suite instead of the brewed one. Fail loudly when the search
        # string is absent: `inreplace` does exactly that, and a silent no-op here
        # would leave the shebang on the machine's `python3`, testing the wrong
        # interpreter and hiding the breakage.
        self.cli = self.libexec / "scripts" / "cli" / "devteam"
        original = self.cli.read_text(encoding="utf-8")
        self.assertIn(
            "#!/usr/bin/env python3",
            original,
            "the formula's inreplace search string is not in the staged entry point",
        )
        self.cli.write_text(
            original.replace("#!/usr/bin/env python3", "#!" + sys.executable, 1),
            encoding="utf-8",
        )
        self.cli.chmod(0o755)

        # `testpath` in the formula's `test do` block exists before the command
        # runs, so the store root is pre-created here too — the assertion is about
        # `core`/`data`, not about the home directory itself.
        self.home = self.tmp / "store"
        self.home.mkdir()

    def run_staged(self, *args):
        """Run the staged CLI through its rewritten shebang, in a scrubbed env.

        ``PYTHONPATH`` is deliberately not forwarded: inheriting one from the
        developer's shell (or from a test runner) could satisfy an import the
        staged payload is missing, which is the single thing this class exists to
        detect. ``HOME`` points inside the temp tree for the same reason.
        """
        env = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "HOME": str(self.tmp / "fakehome"),
            "DEVTEAM_HOME": str(self.home),
        }
        (self.tmp / "fakehome").mkdir(exist_ok=True)
        result = subprocess.run(
            [str(self.cli), *args],
            cwd=str(self.tmp),  # outside the repo: nothing may resolve relative to it
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        return (
            result.returncode,
            result.stdout.decode("utf-8", "replace"),
            result.stderr.decode("utf-8", "replace"),
        )

    def assert_json_command(self, *args):
        code, out, err = self.run_staged(*args)
        # Checked before the exit code: an import failure also fails the exit-code
        # assertion, and this message is the one that says *why*.
        self.assertIsNone(
            IMPORT_FAILURE_RE.search(err),
            "`devteam {}` could not import a module from the payload "
            "packaging/homebrew/devteam.rb stages.\n"
            "The formula installs only `scripts/cli/devteam` and "
            "`scripts/lib/devteam/*.py`. If a module was added outside that "
            "package, or a non-.py file was added inside it, widen the "
            "formula's install block — the CLI is broken for every brew user "
            "until you do.\nstderr:\n{}".format(" ".join(args), err),
        )
        # BOTH streams, and this is not tidiness. Under `--json` the CLI writes a
        # *handled* error as a JSON envelope on STDOUT and leaves stderr empty
        # (devteam/output.py, `Emitter.fail`) — so this assertion used to report
        # the whole diagnosis of a broken command as
        #     AssertionError: 0 != 3 : stderr:
        # while `{"error": "…", "hint": "…"}` sat unread in `out`. The unhandled
        # case (the ImportError above) does land on stderr, which is why both are
        # printed rather than one being swapped for the other.
        self.assertEqual(
            0,
            code,
            "`devteam {}` exited {} from the staged payload.\n"
            "stdout:\n{}\nstderr:\n{}".format(
                " ".join(args), code, out or "(empty)", err or "(empty)"
            ),
        )
        body = json.loads(out)  # raises unless stdout is exactly one JSON document
        self.assertIsInstance(body, dict)
        self.assertIs(True, body.get("ok"))
        return body

    def test_path_json_runs_from_the_staged_payload(self):
        body = self.assert_json_command("path", "--json")
        # Proves DEVTEAM_HOME was honoured, i.e. the store really is the temp one
        # and the assertion about untouched directories below means something.
        self.assertTrue(
            body["core"].startswith(str(self.home)),
            "DEVTEAM_HOME was not honoured: `core` resolved to {!r}, outside the "
            "temp store {!r}. Every isolation claim in this class rests on this — "
            "without it the run below could be reading, or creating, the "
            "developer's real store.".format(body["core"], str(self.home)),
        )

    def test_version_json_runs_from_the_staged_payload(self):
        body = self.assert_json_command("version", "--json")
        # `installed` is empty in a store nothing was ever installed into; the key
        # being present is the contract, its emptiness is the isolation.
        self.assertEqual([], body["installed"])

    def test_the_staged_run_imports_every_module_the_formula_stages(self):
        """Pin the size of the import net this class relies on.

        Running the staged CLI is a complete import check only because
        `devteam/cli.py` imports the whole package eagerly at startup: one
        `devteam path --json` touches every module, so a module the formula failed
        to stage shows up as an ImportError. Nothing enforced that. Make the
        imports lazy — a plausible change, and one with real reasons behind it
        (startup time, an optional dependency) — and the net silently shrinks to
        whatever `path` and `version` happen to reach, while every test above stays
        green for a formula that no longer stages `quarantine.py`.

        So the net is measured, not assumed: run the staged entry point and compare
        the `devteam.*` modules that ended up in `sys.modules` against the staged
        file list. The two must be equal. (They cannot be unequal in the other
        direction: the staged tree is the only thing on `sys.path`, so nothing
        outside it is importable.)
        """
        probe = (
            "import json, runpy, sys, traceback\n"
            "cli = sys.argv[1]\n"
            "sys.argv = ['devteam'] + sys.argv[2:]\n"
            "try:\n"
            "    runpy.run_path(cli, run_name='__main__')\n"
            "except SystemExit as exc:\n"
            "    status = exc.code\n"
            # Any other exception is reported rather than raised, so the failure
            # below is "the staged CLI failed: <traceback>" and not the useless
            # "the probe did not report".
            "except BaseException:\n"
            "    status = traceback.format_exc()\n"
            "else:\n"
            "    status = None\n"
            "names = sorted(n for n in sys.modules"
            " if n == 'devteam' or n.startswith('devteam.'))\n"
            "sys.stderr.write('PROBE:' + json.dumps({'status': status,"
            " 'modules': names}) + '\\n')\n"
        )
        env = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "HOME": str(self.tmp / "fakehome"),
            "DEVTEAM_HOME": str(self.home),
        }
        (self.tmp / "fakehome").mkdir(exist_ok=True)
        # No PYTHONPATH, and cwd outside the repository — the same isolation
        # `run_staged` documents. The entry point puts the staged `scripts/lib` on
        # `sys.path` itself; that is the only source of `devteam` here.
        result = subprocess.run(
            [sys.executable, "-c", probe, str(self.cli), "path", "--json"],
            cwd=str(self.tmp),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        err = result.stderr.decode("utf-8", "replace")
        marker = [line for line in err.splitlines() if line.startswith("PROBE:")]
        self.assertEqual(
            1,
            len(marker),
            "the import probe did not report.\nstdout:\n{}\nstderr:\n{}".format(
                result.stdout.decode("utf-8", "replace") or "(empty)", err or "(empty)"
            ),
        )
        report = json.loads(marker[0][len("PROBE:"):])
        self.assertIn(
            report["status"],
            (0, None),
            "the staged CLI failed under the probe: {}".format(report),
        )

        package = self.libexec / "scripts" / "lib" / "devteam"
        staged = sorted(
            ".".join(path.relative_to(package).with_suffix("").parts).replace(".__init__", "")
            for path in package.rglob("*.py")
            if path.relative_to(package).as_posix() != "__init__.py"
        )
        imported = sorted(
            name.split(".", 1)[1] for name in report["modules"] if name != "devteam"
        )
        self.assertIn("devteam", report["modules"], "the package itself was not imported")
        self.assertEqual(
            staged,
            imported,
            "the staged run no longer imports every module the formula stages.\n"
            "staged but never imported: {}\n"
            "This is the assertion that keeps the rest of this class honest: a "
            "single `devteam path --json` is a complete import check for the "
            "payload only while `devteam/cli.py` imports the package eagerly. If "
            "imports were deliberately made lazy, this test has to be replaced by "
            "something that still reaches every module (importing each staged "
            "module by name in the staged tree, for instance) — not deleted, or "
            "the payload stops being verified for whatever the lazy path skips."
            .format(sorted(set(staged) - set(imported)) or "none"),
        )

    def test_read_only_commands_create_no_store(self):
        # Mirrors the formula's own `test do` block. If this ever fails, the
        # formula's smoke test is wrong about `devteam path` being read-only and
        # `brew test devteam` would fail on a real machine — fix the formula (or
        # the command), not this assertion.
        for args in (("path", "--json"), ("version", "--json")):
            self.assert_json_command(*args)
            self.assertFalse(
                (self.home / "core").exists(), "`devteam {}` created core/".format(args[0])
            )
            self.assertFalse(
                (self.home / "data").exists(), "`devteam {}` created data/".format(args[0])
            )


if __name__ == "__main__":
    unittest.main()
