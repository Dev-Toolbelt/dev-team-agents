#!/usr/bin/env bash
# 04-packaging.sh — distribution packaging gate (Homebrew formulas + winget manifests).
#
# WHY THIS FILE EXISTS
# ====================
# Nothing in CI read `packaging/` before this gate existed. The only verification
# was `packaging/README.md`'s "Verification" section: three commands a human is
# asked to run by hand. So a Homebrew formula could stop being valid ruby, or the
# three winget manifests could silently disagree about the version, and the build
# would stay green.
#
# The README's own runbook names the failure mode outright — a version bump must
# update `PackageVersion` "in all three files together" AND rename the version
# directory the manifests live in. That is four edits, by hand, coordinated by
# nothing. Three of the winget checks below exist for exactly that edit.
#
# ENFORCEMENT POLICY
# ==================
# Same two wrappers, same meaning, as `.github/scripts/ci/01-lint.sh`. Read that
# file's ENFORCEMENT POLICY header — it is the canonical statement of what
# `blocking` and `advisory` mean and when to pick which, and this script
# deliberately does not restate it. There is no third tier here either, and the
# exit-code nuance carries over unchanged: `advisory` softens *findings* (exit 1)
# only, while exit 2 or higher means the check itself could not run, which is
# always blocking. A gate that skips is not a gate.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$REPO_ROOT"

HOMEBREW_DIR="packaging/homebrew"
WINGET_ROOT="packaging/winget/manifests"

# Where the expected release origin is DERIVED from, not declared. See
# RELEASE_PREFIX in the winget program below for why this file and not another.
ORIGIN_SOURCE="scripts/install.sh"

ADVISORY_HITS=()

blocking() {
  local label="$1"; shift
  echo "─ ${label} [BLOCKING] ──────────────────────────────────────"
  "$@"
}

advisory() {
  local label="$1"; shift
  echo "─ ${label} [ADVISORY] ──────────────────────────────────────"
  local rc=0
  "$@" || rc=$?
  if [ "$rc" -ge 2 ]; then
    echo "  ${label} failed to run (exit ${rc}) — that is always blocking."
    return "$rc"
  fi
  if [ "$rc" -ne 0 ]; then
    echo "  ADVISORY — findings above do NOT fail the build. See PROMOTE WHEN in this script."
    ADVISORY_HITS+=("$label")
  fi
  return 0
}

# ── Tooling preflight ───────────────────────────────────────────────────────
# Both tools are hard requirements, not optional accelerants. A missing one is
# exit 2 by the policy above ("a check that cannot run is not a check that
# passed"), so CI fails loudly and a contributor running this by hand gets a
# message that says what to install. The CI job sets both up explicitly rather
# than inheriting whatever the runner image happens to ship — the same reasoning
# that produced `.github/shellcheck.pin`.
echo "─ tooling ─────────────────────────────────────────────────────"

if ! command -v ruby >/dev/null 2>&1; then
  echo "  ruby is not on PATH, so the Homebrew formulas cannot be syntax-checked."
  echo "  This gate needs it — install ruby and re-run:"
  echo "    macOS:  /usr/bin/ruby is usually present; otherwise 'brew install ruby'"
  echo "    Debian: sudo apt-get install -y ruby"
  echo "  (CI installs it in the 'packaging' job of .github/workflows/ci.yml.)"
  exit 2
fi
echo "  ruby $(ruby -e 'print RUBY_VERSION')"

# pyyaml: try, install once, then fail. Deliberately NOT "skip the YAML checks if
# pyyaml is absent" — that shape turns the three checks that actually catch a
# botched version bump into decoration on any runner without the package. A
# hand-rolled YAML parser is the other wrong answer: it would disagree with the
# parser winget itself uses, which is the only opinion that matters.
if python3 -c 'import yaml' >/dev/null 2>&1; then
  echo "  pyyaml $(python3 -c 'import yaml; print(yaml.__version__)')"
else
  echo "  pyyaml is not importable — attempting one install"
  python3 -m pip install --quiet --disable-pip-version-check pyyaml || true
  if python3 -c 'import yaml' >/dev/null 2>&1; then
    echo "  pyyaml $(python3 -c 'import yaml; print(yaml.__version__)') (installed just now)"
  else
    echo "  pyyaml is still not importable after 'python3 -m pip install pyyaml'."
    echo "  The winget manifest checks cannot run without a real YAML parser, and"
    echo "  this gate does not skip them. Install it and re-run:"
    echo "    python3 -m pip install pyyaml    (or: pipx / your distro's python3-yaml)"
    exit 2
  fi
fi

# ── Homebrew ────────────────────────────────────────────────────────────────

# `ruby -c` parses the formula and nothing more. That is the whole point: a
# formula is ruby source, Homebrew evaluates it, and a syntax error makes it
# unloadable regardless of whether the values inside are right.
#
# WHAT THIS GATE DOES NOT COVER, AND WHERE THAT LIVES INSTEAD
# A parse is not an evaluation. Nothing here runs `brew style`, `brew audit`,
# `brew install` or `brew test`, so a formula that parses but installs the wrong
# files, or whose `install` block raises at runtime, passes this check.
# `packaging/verify-formula-locally.sh` is what covers that: reading it, it
# builds a tarball from HEAD, drops a temporary copy of the formula (the tracked
# file is never written, which it asserts at exit) into a throwaway `brew tap-new
# --no-git` tap, and runs `brew style`, `brew audit --formula`, `brew audit
# --strict --online`, `brew install --build-from-source`, `brew test` and a smoke
# test of the installed binary, then tears the tap and the install down again.
# It deliberately does NOT run `brew audit --new`: every new-formula check in
# Homebrew 7 is gated on the core tap, so on a private-tap formula `--new` is
# byte-identical to `--strict --online` and says nothing about homebrew-core
# eligibility. That script records the measurement and the file:line citations.
#
# That script is deliberately NOT called from this gate: its own preflight
# requires `brew` on PATH, and the runner here is ubuntu-latest. It is a
# maintainer-run check on a macOS machine with Homebrew, not a CI step.
#
# So the accurate division is: this gate catches a formula that stopped being
# parseable, for free, wherever CI runs at all. That is NOT "on every push" — an
# earlier version of this comment claimed it and was wrong. `ci.yml`'s trigger
# policy scopes `push` to `main` and to tags; every other branch is covered by
# `pull_request` only, and that workflow's own header states the trade-off
# outright ("a branch with no open PR no longer gets CI on push"). So the real
# coverage is: every pull request, plus pushes to `main` and to tags. A packaging
# change sitting on a branch with no open PR is unchecked until the PR exists.
#
# `packaging/verify-formula-locally.sh` catches everything a real Homebrew would
# object to, when a maintainer runs it. What NEITHER covers is the published path
# — no tap hosts this formula, and no release tarball has been installed from one
# (packaging/README.md).
homebrew_syntax() {
  local rc=0 f
  for f in "$HOMEBREW_DIR/devteam.rb" "$HOMEBREW_DIR/devteam-app.rb"; do
    if [ ! -f "$f" ]; then
      echo "  MISSING: $f"
      rc=1
      continue
    fi
    if ruby -c "$f" >/dev/null 2>&1; then
      echo "  $f — Syntax OK"
    else
      echo "  $f — ruby syntax error:"
      ruby -c "$f" 2>&1 | sed 's/^/    /'
      rc=1
    fi
  done
  return "$rc"
}

blocking "homebrew: ruby syntax" homebrew_syntax

# ── winget ──────────────────────────────────────────────────────────────────

# One python program, because every check here is a cross-file comparison and
# splitting them across shell invocations would mean re-parsing the manifests
# once per check.
#
# SOURCE OF TRUTH for the required-field lists: the JSON schema each manifest
# declares in its own `# yaml-language-server: $schema=` header,
# https://aka.ms/winget-manifest.<type>.1.12.0.schema.json (mirrored in
# microsoft/winget-cli under schemas/JSON/manifests/v1.12.0/). The lists encoded
# below are the ones the manifest files' own header comments record as confirmed
# against that schema on 2026-09-28 — this script is a second copy of them, not a
# second authority. When ManifestVersion moves, re-read the schema at that URL and
# update both the headers and the table below together.
#
# The second argument is where the EXPECTED RELEASE ORIGIN is read from, rather
# than a hostname typed into this file — see RELEASE_PREFIX in the program below.
winget_checks() {
  python3 - "$WINGET_ROOT" "$ORIGIN_SOURCE" <<'PY'
import glob
import os
import re
import sys

try:
    import yaml
except ImportError as exc:  # preflight already covered this; belt and braces.
    print("  pyyaml is not importable: %s" % exc)
    sys.exit(2)

root = sys.argv[1]
origin_source = sys.argv[2]
findings = []


def fail(msg):
    findings.append(msg)


# ── The expected release origin ─────────────────────────────────────────────
# DERIVED, the same way the directory layout below is derived from
# PackageIdentifier rather than hardcoded: read the owner/repo that
# `scripts/install.sh` already downloads the payload from. Two reasons for that
# file — it is the shipped installer's own origin, so if these two ever disagree
# one of them is wrong by definition; and it lives OUTSIDE `packaging/`, which is
# what makes the check mean anything. Deriving it from the manifests' own
# PackageUrl, or from the formula's homepage, would let the same edit that
# redirects the InstallerUrls move the goalpost along with them.
#
# Failure to read it is exit 2, not a finding: per the ENFORCEMENT POLICY header a
# check that cannot run has not passed. If install.sh stops declaring the slug
# this way, point ORIGIN_SOURCE at whatever does.
OWNER_RE = re.compile(r'^GITHUB_OWNER="([^"]+)"', re.M)
REPO_RE = re.compile(r'^GITHUB_REPO="([^"]+)"', re.M)

try:
    with open(origin_source, "r", encoding="utf-8") as handle:
        origin_src = handle.read()
except OSError as exc:
    print("  cannot read %s, so the expected release origin cannot be derived "
          "and the InstallerUrl origin check cannot run — %s" % (origin_source, exc))
    sys.exit(2)

owner_match = OWNER_RE.search(origin_src)
repo_match = REPO_RE.search(origin_src)
# The captured values are also VALIDATED as plain GitHub slug segments, the same
# shape `.github/scripts/release/bump-homebrew-formula.sh` validates its --repo
# against. Matching the assignment is not enough: if install.sh ever switched to
# the env-overridable `GITHUB_OWNER="${GITHUB_OWNER:-Dev-Toolbelt}"` spelling, the
# regex would happily capture `${GITHUB_OWNER:-Dev-Toolbelt}` and every
# InstallerUrl would then fail against a nonsense origin — a confusing false
# positive in place of a clear "this gate cannot run" message.
SLUG_RE = re.compile(r"^[A-Za-z0-9._-]+$")
owner = owner_match.group(1) if owner_match else None
repo = repo_match.group(1) if repo_match else None
if (owner is None or repo is None
        or not SLUG_RE.match(owner) or not SLUG_RE.match(repo)):
    print("  %s no longer declares a literal GITHUB_OWNER=\"<owner>\" / "
          "GITHUB_REPO=\"<repo>\" at the start of a line (read owner=%r repo=%r), "
          "so no expected release origin can be derived from it."
          % (origin_source, owner, repo))
    print("  Point ORIGIN_SOURCE in this script at the file that now holds the")
    print("  repository slug. Do NOT hardcode the origin here — deriving it is the")
    print("  whole reason the InstallerUrl origin check means anything.")
    sys.exit(2)

RELEASE_PREFIX = "https://github.com/%s/%s/releases/download/" % (owner, repo)

# Required top-level fields per manifest type, confirmed against the 1.12.0
# schema each file declares (see the comment above this heredoc). The `version`
# manifest's own header records the confirmation trail but does not enumerate the
# list, so its five fields are taken from the same schema it names.
#
# `locale` has no tracked file yet, so no manifest header records its trail: its
# five fields were read on 2026-09-28 from
#   schemas/JSON/manifests/v1.12.0/manifest.locale.1.12.0.json
# in microsoft/winget-cli, the same path the other three were confirmed against.
# It is the SHORT list on purpose — Publisher, PackageName, License and
# ShortDescription are required of `defaultLocale` only, which is exactly why a
# spec-correct extra locale manifest used to report them as missing.
REQUIRED = {
    "version": [
        "PackageIdentifier", "PackageVersion", "DefaultLocale",
        "ManifestType", "ManifestVersion",
    ],
    "installer": [
        "PackageIdentifier", "PackageVersion", "Installers",
        "ManifestType", "ManifestVersion",
    ],
    "defaultLocale": [
        "PackageIdentifier", "PackageVersion", "PackageLocale", "Publisher",
        "PackageName", "License", "ShortDescription",
        "ManifestType", "ManifestVersion",
    ],
    "locale": [
        "PackageIdentifier", "PackageVersion", "PackageLocale",
        "ManifestType", "ManifestVersion",
    ],
}
# Required per entry in `Installers`, same source.
REQUIRED_INSTALLER_ENTRY = ["Architecture", "InstallerUrl", "InstallerSha256"]

# A digest is 64 lowercase hex characters. This is deliberately STRICTER than the
# schema, which accepts either case — one canonical form means a diff of a bumped
# manifest is readable, and the fix for a violation is to lowercase it.
#
# The all-zeros value satisfies that format, so the format rule alone let a
# RELEASED manifest keep it: directory 1.0.0, PackageVersion 1.0.0, InstallerUrl
# at v1.0.0, digest still 64 zeros — "all checks passed". Only the advisory said
# anything, and promoting the advisory was an edit nobody was scheduled to make.
# Zeros are an honest placeholder only while the manifest is still the unreleased
# scaffold; once the version and the URL are real they are a defect, because the
# one thing that then fails is a user's `winget install`. So the zeros exemption
# is CONDITIONED on the scaffold state (see ZERO_DIGEST at its use site) instead
# of being unconditional, and no future manual promotion activates it.
#
# Honest limit: a 64-char lowercase-hex value that is simply WRONG is
# indistinguishable from a right one here. Only hashing the actual artifact
# catches that, which is why packaging/README.md forbids hand-writing digests.
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
ZERO_DIGEST = "0" * 64

# The unreleased-scaffold pair. packaging/README.md documents both halves: the
# version directory and PackageVersion are "0.0.0", and the InstallerUrls carry
# the literal tag vX.Y.Z because no Windows installer has ever been built.
SCAFFOLD_VERSION = "0.0.0"
SCAFFOLD_TAG = "vX.Y.Z"

# The `# yaml-language-server: $schema=` header each manifest declares. That URL is
# the source of truth for this gate's required-field lists, so a ManifestVersion
# bumped without the header following it leaves every list below validating against
# a schema the file no longer claims to follow — and leaves an editor checking the
# file against the old one. Both segments are read: the manifest TYPE and the
# schema VERSION.
SCHEMA_RE = re.compile(
    r"^#\s*yaml-language-server:\s*\$schema=\S*?"
    r"winget-manifest\.(?P<kind>[A-Za-z]+)\.(?P<version>\d+\.\d+\.\d+)\.schema\.json\s*$"
)


# ── Classification: declared type first, filename second ────────────────────
# winget's multi-file form is one `version` manifest, one `installer` manifest,
# one `defaultLocale` manifest, and N additional `locale` manifests. The filename
# CANNOT tell the last two apart — both are `<Identifier>.locale.<tag>.yaml` — so
# a filename-based classifier that mapped every `.locale.` file to
# `defaultLocale` reported a spec-correct extra locale manifest as six findings:
# a duplicate defaultLocale, three defaultLocale-only fields it is not required
# to carry, a ManifestType mismatch and a $schema mismatch. All six were wrong.
#
# So the DECLARED ManifestType classifies the file, and the filename is then
# checked for agreement with it — that half was catching something real and is
# kept below.
FAMILY_BY_KIND = {
    "version": "version",
    "installer": "installer",
    "defaultLocale": "locale",
    "locale": "locale",
}
FAMILY_SHAPE = {
    "version": "<Identifier>.yaml",
    "installer": "<Identifier>.installer.yaml",
    "locale": "<Identifier>.locale.<tag>.yaml",
}

LOCALE_NAME_RE = re.compile(r"\.locale\.([^.]+)\.yaml$")


def family_from_filename(basename):
    """The NAMING family a filename declares — not the kind, which needs the type."""
    if basename.endswith(".installer.yaml"):
        return "installer"
    if LOCALE_NAME_RE.search(basename):
        return "locale"
    return "version"


paths = sorted(glob.glob(os.path.join(root, "**", "*.yaml"), recursive=True))
if not paths:
    print("  no *.yaml found under %s — this gate checked nothing." % root)
    print("  If the winget channel was removed, remove this check with it.")
    sys.exit(1)

docs = {}
schemas = {}
groups = {}
for path in paths:
    groups.setdefault(os.path.dirname(path), []).append(path)
    try:
        with open(path, "r", encoding="utf-8") as handle:
            raw = handle.read()
    except OSError as exc:
        fail("%s: cannot be read — %s" % (path, exc))
        continue

    for line in raw.splitlines():
        match = SCHEMA_RE.match(line)
        if match:
            schemas[path] = (match.group("kind"), match.group("version"))
            break

    try:
        doc = yaml.safe_load(raw)
    except Exception as exc:  # yaml.YAMLError, or anything the parser raises
        fail("%s: does not parse as YAML — %s" % (path, exc))
        continue
    if not isinstance(doc, dict):
        fail("%s: parses, but the top level is %s, not a mapping"
             % (path, type(doc).__name__))
        continue
    docs[path] = doc


def text(path, doc, field):
    """A field that winget requires to be a string, and must stay one.

    An unquoted `PackageVersion: 1.12` is a YAML float, not "1.12", and an
    unquoted 64-zero digest is the integer 0 with its leading zeros gone. Both
    round-trip through str() looking fine, so the type is checked, not coerced.
    """
    value = doc.get(field)
    if value is None:
        return None
    if not isinstance(value, str):
        fail("%s: %s is %r (%s), not a YAML string — quote it"
             % (path, field, value, type(value).__name__))
        return None
    return value


for version_dir in sorted(groups):
    members = sorted(groups[version_dir])
    by_kind = {}
    for path in members:
        doc = docs.get(path)
        declared = doc.get("ManifestType") if doc is not None else None
        if isinstance(declared, str) and declared in REQUIRED:
            kind = declared
        else:
            # No usable ManifestType. Fall back to the filename so the file is
            # still field-checked as *something* rather than silently skipped. A
            # missing ManifestType is already a required-field finding; a present
            # but unrecognised one gets its own, here.
            family = family_from_filename(os.path.basename(path))
            kind = "defaultLocale" if family == "locale" else family
            if declared is not None:
                fail("%s: ManifestType %r is not one of %s — this directory is a "
                     "multi-file manifest set, not a singleton or merged manifest"
                     % (path, declared, ", ".join(sorted(REQUIRED))))
        by_kind.setdefault(kind, []).append(path)

    # Exactly one each of the three SINGULAR types. `locale` is deliberately not
    # in this list: winget allows N additional locale manifests beside the
    # defaultLocale one, so zero of them and five of them are equally valid. What
    # replaces the count for those files is the uniqueness and DefaultLocale
    # checks further down.
    for kind in ("version", "installer", "defaultLocale"):
        found = by_kind.get(kind, [])
        if len(found) == 0:
            fail("%s: no %s manifest" % (version_dir, kind))
        elif len(found) > 1:
            fail("%s: %d %s manifests (%s) — expected exactly one"
                 % (version_dir, len(found), kind,
                    ", ".join(os.path.basename(p) for p in found)))

    for kind, found in sorted(by_kind.items()):
        for path in found:
            doc = docs.get(path)
            if doc is None:
                continue  # already reported as unparseable

            for field in REQUIRED[kind]:
                if field not in doc:
                    fail("%s: missing required %s-manifest field %s"
                         % (path, kind, field))

            # The filename and the declared type must AGREE. Kept from the old
            # filename-based classifier because this half catches something real:
            # a `*.installer.yaml` that declares `defaultLocale`, or a locale
            # manifest saved without `.locale.<tag>.` in its name, is unusable to
            # winget whichever of the two is the mistake. It no longer decides
            # what the file is — it only reports the disagreement.
            declared = doc.get("ManifestType")
            basename = os.path.basename(path)
            if declared is not None:
                want = FAMILY_BY_KIND[kind]
                got = family_from_filename(basename)
                if want != got:
                    fail("%s: ManifestType %r needs a %s filename, but this file "
                         "is named as a %s manifest (%s) — one of the two is wrong"
                         % (path, declared, FAMILY_SHAPE[want],
                            got, FAMILY_SHAPE[got]))

            # For a locale file the filename also encodes WHICH locale, and winget
            # resolves the file by that tag. A mismatch means the manifest winget
            # loads for pt-BR announces itself as en-US.
            if kind in ("defaultLocale", "locale"):
                name_match = LOCALE_NAME_RE.search(basename)
                locale = doc.get("PackageLocale")
                if (name_match is not None and isinstance(locale, str)
                        and name_match.group(1) != locale):
                    fail("%s: the filename says locale %r but PackageLocale is %r"
                         % (path, name_match.group(1), locale))

            manifest_version = text(path, doc, "ManifestVersion")
            text(path, doc, "PackageVersion")

            # The declared $schema must describe THIS file: right manifest type,
            # and the same schema version the file says it conforms to.
            declared_schema = schemas.get(path)
            if declared_schema is None:
                fail("%s: no readable '# yaml-language-server: $schema=…"
                     "winget-manifest.<type>.<x.y.z>.schema.json' header — that URL is "
                     "this gate's source of truth for the required-field lists"
                     % path)
            else:
                schema_kind, schema_version = declared_schema
                if schema_kind != kind:
                    fail("%s: the $schema header describes a %r manifest, but this "
                         "file is a %r manifest" % (path, schema_kind, kind))
                if manifest_version is not None and schema_version != manifest_version:
                    fail("%s: ManifestVersion is %r but the $schema header points at "
                         "%s — bump the header with the field, or the file is validated "
                         "against a schema it no longer claims"
                         % (path, manifest_version, schema_version))

    # What "exactly one" is replaced by for the locale files, now that N of them
    # are allowed. Two manifests claiming the same PackageLocale is ambiguous, and
    # the version manifest's DefaultLocale has to resolve to one of them — winget
    # looks the default up by locale tag, not by which file is called what.
    locale_members = by_kind.get("defaultLocale", []) + by_kind.get("locale", [])
    by_locale = {}
    for path in locale_members:
        doc = docs.get(path)
        if doc is None:
            continue
        value = doc.get("PackageLocale")
        if isinstance(value, str):
            by_locale.setdefault(value, []).append(os.path.basename(path))
    for value, files in sorted(by_locale.items()):
        if len(files) > 1:
            fail("%s: PackageLocale %r is declared by %d manifests (%s) — a locale "
                 "may appear once per version"
                 % (version_dir, value, len(files), ", ".join(sorted(files))))

    for path in by_kind.get("version", []):
        doc = docs.get(path)
        if doc is None or not isinstance(doc.get("DefaultLocale"), str):
            continue
        default_locale = doc["DefaultLocale"]
        for other in by_kind.get("defaultLocale", []):
            other_doc = docs.get(other)
            if other_doc is None:
                continue
            value = other_doc.get("PackageLocale")
            if isinstance(value, str) and value != default_locale:
                fail("%s: the version manifest's DefaultLocale is %r but the "
                     "defaultLocale manifest declares PackageLocale %r — the "
                     "default has to resolve to a locale present here"
                     % (version_dir, default_locale, value))

    # The three fields that must agree, and whose disagreement is the documented
    # failure mode of a hand-coordinated version bump.
    for field in ("PackageIdentifier", "PackageVersion", "ManifestVersion"):
        seen = {}
        for path in members:
            doc = docs.get(path)
            if doc is None or field not in doc:
                continue
            seen.setdefault(str(doc[field]), []).append(os.path.basename(path))
        if len(seen) > 1:
            detail = "; ".join(
                "%r in %s" % (value, ", ".join(files))
                for value, files in sorted(seen.items())
            )
            fail("%s: %s disagrees across the manifests — %s"
                 % (version_dir, field, detail))

    # All three $schema headers in a version directory must name the same schema
    # version, for the same reason the three ManifestVersion fields must: a bump
    # applied to some of the files is the failure mode, not a bump applied to none.
    schema_versions = {}
    for path in members:
        declared_schema = schemas.get(path)
        if declared_schema is None:
            continue
        schema_versions.setdefault(declared_schema[1], []).append(
            os.path.basename(path))
    if len(schema_versions) > 1:
        detail = "; ".join(
            "%s in %s" % (value, ", ".join(files))
            for value, files in sorted(schema_versions.items())
        )
        fail("%s: the $schema headers disagree about the schema version — %s"
             % (version_dir, detail))

    # The directory path is itself data: winget-pkgs partitions `manifests/` by
    # the LOWERCASED FIRST LETTER OF THE PUBLISHER, then one directory per
    # dot-separated part of the PackageIdentifier, then the version. So
    # `DevToolbelt.Devteam` at 0.0.0 must live at `d/DevToolbelt/Devteam/0.0.0`.
    # The expectation is derived from the identifier, never from a hardcoded path,
    # so renaming the package moves the requirement with it instead of pinning the
    # tree to the name it had when this gate was written. Casing is compared
    # exactly: only the partition letter is lowercased, the publisher and package
    # segments keep the identifier's own casing.
    identifiers = set()
    for path in members:
        doc = docs.get(path)
        if doc is not None and isinstance(doc.get("PackageIdentifier"), str):
            identifiers.add(doc["PackageIdentifier"])
    if len(identifiers) == 1:
        identifier = identifiers.pop()
        id_parts = identifier.split(".")
        if len(id_parts) < 2 or not all(id_parts):
            fail("%s: PackageIdentifier %r is not in Publisher.Package form, so no "
                 "directory layout can be derived from it"
                 % (version_dir, identifier))
        else:
            expected = [id_parts[0][0].lower()] + id_parts
            actual = os.path.relpath(version_dir, root).split(os.sep)[:-1]
            if actual != expected:
                fail("%s: directory layout does not encode PackageIdentifier %r — "
                     "expected %s/<version>, found %s/<version>"
                     % (version_dir, identifier,
                        "/".join(expected), "/".join(actual)))

    # The version DIRECTORY name is the fourth place a bump has to land, and the
    # one a `sed` over the files silently misses.
    dir_version = os.path.basename(version_dir)
    for path in members:
        doc = docs.get(path)
        if doc is None:
            continue
        declared = doc.get("PackageVersion")
        if declared is None:
            continue
        if str(declared) != dir_version:
            fail("%s: PackageVersion %r does not match its version directory %r "
                 "— rename the directory and the field together"
                 % (path, str(declared), dir_version))

    # Installer entries: required fields, digest format, and URL/version agreement.
    for path in by_kind.get("installer", []):
        doc = docs.get(path)
        if doc is None:
            continue
        pkg_version = doc.get("PackageVersion")
        pkg_version = str(pkg_version) if pkg_version is not None else None
        installers = doc.get("Installers")
        if not isinstance(installers, list) or not installers:
            fail("%s: Installers must be a non-empty list" % path)
            continue
        for index, entry in enumerate(installers):
            where = "%s: Installers[%d]" % (path, index)
            if not isinstance(entry, dict):
                fail("%s is %s, not a mapping" % (where, type(entry).__name__))
                continue
            for field in REQUIRED_INSTALLER_ENTRY:
                if field not in entry:
                    fail("%s: missing required field %s" % (where, field))

            # ── The URL: where it points, and which tag it names ──
            # ORIGIN IS CHECKED FIRST, AND UNCONDITIONALLY. The old code only ever
            # asked whether the version string appeared somewhere in the URL, so
            # rewriting both InstallerUrls to
            # `https://evil.example.com/vX.Y.Z/devteam-setup-x64.exe` left every
            # check green — every other field stayed self-consistent, and nothing
            # looked at the host or the owner at all. The scaffold placeholder is a
            # placeholder for the TAG; it is not a licence to point the download
            # somewhere else, so this check applies to the scaffold too.
            url = entry.get("InstallerUrl")
            url_tag = None
            if url is not None and not isinstance(url, str):
                fail("%s: InstallerUrl is %s, not a string"
                     % (where, type(url).__name__))
                url = None
            if url is not None:
                if not url.startswith(RELEASE_PREFIX):
                    fail("%s: InstallerUrl is not a release asset of this project "
                         "— expected it to start with %s (derived from %s), got %s"
                         % (where, RELEASE_PREFIX, origin_source, url))
                else:
                    # The first path segment after `…/download/` is the release tag.
                    url_tag = url[len(RELEASE_PREFIX):].split("/")[0]
                    if not url_tag:
                        fail("%s: InstallerUrl has no release tag between %s and "
                             "the asset name — %s" % (where, RELEASE_PREFIX, url))
                        url_tag = None

            # CHOICE (stated, per the two options): the PAIRED placeholder state
            # is valid — PackageVersion "0.0.0" together with the literal vX.Y.Z
            # tag — because that is the honest recorded state of an unreleased
            # scaffold and the tree must pass today. ANY other combination fails,
            # including a half-done bump in either direction, and the paired state
            # is now also what licenses the zeros digest below. So nothing here is
            # trivially green forever and no follow-up edit "activates" it: the
            # moment one half moves off its placeholder, the other two are held to
            # real values.
            version_scaffold = pkg_version == SCAFFOLD_VERSION
            url_scaffold = url_tag == SCAFFOLD_TAG
            scaffold = version_scaffold and url_scaffold
            # "Once the version and the URLs are real." A half-bumped manifest is
            # neither state, and its actionable finding is the half-bump below, so
            # the digest rule waits for both halves to be off the placeholder
            # rather than piling a derivative message on top. This is not an escape
            # hatch: half-bumped is itself a blocking finding, so a zeros digest
            # cannot reach a release through it.
            released = not version_scaffold and not url_scaffold

            digest = entry.get("InstallerSha256")
            if digest is not None:
                if not isinstance(digest, str):
                    fail("%s: InstallerSha256 is %r (%s), not a quoted string — "
                         "an unquoted all-digit digest is parsed as a number and "
                         "loses its leading zeros"
                         % (where, digest, type(digest).__name__))
                elif not SHA256_RE.match(digest):
                    reason = "expected 64 lowercase hex characters, got %d" % len(digest)
                    if len(digest) == 64 and re.match(r"^[0-9A-Fa-f]{64}$", digest):
                        reason = "hex but not lowercase — lowercase it"
                    fail("%s: InstallerSha256 %r is not a valid digest (%s)"
                         % (where, digest, reason))
                elif digest == ZERO_DIGEST and url_tag is not None and released:
                    # Only asked once the tag could actually be read: a URL that
                    # failed the origin check has already been reported, and
                    # guessing at its release state on top would be noise.
                    fail("%s: InstallerSha256 is still 64 zeros, but this manifest "
                         "is no longer the unreleased scaffold (PackageVersion %r, "
                         "tag %s). The zeros placeholder is honest only while the "
                         "version and the URL are both placeholders; past that it "
                         "is a released manifest whose digest matches nothing, and "
                         "the failure lands on a user's `winget install`. Hash the "
                         "artifact that was actually built and write that digest."
                         % (where, pkg_version, url_tag))

            # ── URL ↔ version agreement ──
            if url_tag is None or pkg_version is None:
                continue
            if scaffold:
                continue  # unreleased scaffold, both halves consistent
            if version_scaffold != url_scaffold:
                fail("%s: half-bumped — PackageVersion is %r but the InstallerUrl "
                     "tag %s the %s placeholder (%s). Bump both or neither."
                     % (where, pkg_version,
                        "is still" if url_scaffold else "is no longer",
                        SCAFFOLD_TAG, url))
                continue
            # EXACT tag equality, not "the version appears in the URL somewhere".
            # The substring form accepted `v1.0.0-rc1` for PackageVersion 1.0.0 —
            # winget would then ship the release candidate as the release — and
            # would equally accept `v1.0.0.1` or `v11.0.0`. There is exactly one
            # correct tag for a version, so compare against it.
            if url_tag != "v" + pkg_version:
                fail("%s: the InstallerUrl release tag is %r, but PackageVersion "
                     "%r requires exactly %r — a tag that merely CONTAINS the "
                     "version (v%s-rc1, v%s.1) publishes a different build under "
                     "this version. %s"
                     % (where, url_tag, pkg_version, "v" + pkg_version,
                        pkg_version, pkg_version, url))

if findings:
    for finding in findings:
        print("  %s" % finding)
    print("  %d finding(s)." % len(findings))
    sys.exit(1)

print("  %d manifest(s) in %d version directory/ies — all checks passed"
      % (len(paths), len(groups)))
PY
}

blocking "winget: manifest contract" winget_checks

# ── Advisory ────────────────────────────────────────────────────────────────

# Both advisories below are TRUE on the tree today, and both must stay green:
# they describe the honest, documented state of an unreleased scaffold
# (packaging/README.md, "What is unverified, and exactly why"). Their value is
# for the day someone reads `packaging/` and concludes the channels are live.
#
# PROMOTE WHEN (both): a release has actually gone out through that channel — for
# Homebrew, `release.yml` has run on a real tag and the tap exists; for winget, a
# signed Windows installer has been built and submitted. At that point a
# reappearing placeholder is a regression, not a status report, and each flips to
# blocking by swapping one word on its invocation line.

# The value of the first `<directive> "…"` line in a formula. ANCHORED ON THE
# DIRECTIVE, never a whole-file grep — both formulas name their own placeholder
# strings in their header comments on purpose (devteam.rb explains what
# REPLACE_WITH_SHA256_OF_RELEASE_TARBALL is and why it is not a plausible-looking
# fake; devteam-app.rb documents NO_RELEASE_SHA256_DOES_NOT_EXIST_YET the same
# way), so a `grep -q` over the file matches the prose forever. Reproduced by
# running `.github/scripts/release/bump-homebrew-formula.sh` against a copy: the
# two directives held a real tag and a real digest and the sha256 advisory still
# fired. Under this script's own PROMOTE WHEN instruction, promoting a permanent
# false positive would make the build permanently red.
#
# `packaging/verify-formula-locally.sh` already sidesteps this trap with exactly
# this awk and says why — "Only the sha256 DIRECTIVE matters" — which is knowledge
# that existed before this gate was written and did not reach it. The url half was
# never affected, because `tags/vX.Y.Z.tar.gz` only ever appears on the url line;
# it is anchored here anyway so both halves fail the same way or not at all.
formula_directive() {
  awk -v want="$2" '
    $1 == want { match($0, /"[^"]*"/); print substr($0, RSTART + 1, RLENGTH - 2); exit }
  ' "$1"
}

homebrew_placeholders() {
  local rc=0 value
  value="$(formula_directive "$HOMEBREW_DIR/devteam.rb" sha256)"
  if [ "$value" = "REPLACE_WITH_SHA256_OF_RELEASE_TARBALL" ]; then
    echo "  $HOMEBREW_DIR/devteam.rb sha256 directive is still the placeholder"
    echo "    REPLACE_WITH_SHA256_OF_RELEASE_TARBALL — no release tarball has been hashed."
    rc=1
  fi
  value="$(formula_directive "$HOMEBREW_DIR/devteam.rb" url)"
  case "$value" in
    */tags/vX.Y.Z.tar.gz)
      echo "  $HOMEBREW_DIR/devteam.rb url directive still points at the literal tag vX.Y.Z."
      rc=1
      ;;
  esac
  value="$(formula_directive "$HOMEBREW_DIR/devteam-app.rb" sha256)"
  if [ "$value" = "NO_RELEASE_SHA256_DOES_NOT_EXIST_YET" ]; then
    echo "  $HOMEBREW_DIR/devteam-app.rb has no releasable artifact to describe — the"
    echo "    app exists under app/ (ADR-0015) but no signed, notarised build does, so"
    echo "    its sha256 directive is an explicit non-value."
    rc=1
  fi
  [ "$rc" -eq 0 ] && echo "  no placeholders left in the Homebrew url/sha256 directives."
  return "$rc"
}

winget_scaffold() {
  local rc=0
  if [ -d "$WINGET_ROOT" ] && find "$WINGET_ROOT" -type d -name '0.0.0' | grep -q .; then
    echo "  $WINGET_ROOT still has a 0.0.0 version directory — placeholder version."
    rc=1
  fi
  if [ -d "$WINGET_ROOT" ] && grep -rq 'vX\.Y\.Z' "$WINGET_ROOT"; then
    echo "  InstallerUrl(s) still carry the literal tag vX.Y.Z — no Windows installer exists."
    rc=1
  fi
  # Advisory here because on the scaffold it is a status report, not a defect.
  # The BLOCKING counterpart already covers the case that is a defect: the winget
  # program above fails a zeros digest the moment the manifest stops being the
  # scaffold. This line and that check are not duplicates — they disagree about
  # the scaffold on purpose.
  if [ -d "$WINGET_ROOT" ] && grep -rq '"0\{64\}"' "$WINGET_ROOT"; then
    echo "  InstallerSha256 is still 64 zeros — nothing has been built, signed or hashed."
    rc=1
  fi
  [ "$rc" -eq 0 ] && echo "  winget manifests are off the scaffold placeholders."
  return "$rc"
}

advisory "homebrew: release placeholders" homebrew_placeholders
advisory "winget: unreleased scaffold" winget_scaffold

# ── Summary ─────────────────────────────────────────────────────────────────
if [ ${#ADVISORY_HITS[@]} -gt 0 ]; then
  echo ""
  echo "packaging OK ✓ (with advisory findings: ${ADVISORY_HITS[*]})"
else
  echo ""
  echo "packaging OK ✓"
fi
