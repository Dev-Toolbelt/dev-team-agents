# devteam.rb — Homebrew formula for the dev-team-agents CLI (ADR-0011).
#
# Packages ONLY the `devteam` CLI (`scripts/cli/devteam` + `scripts/lib/devteam/`) —
# the global core/data-store manager described in CLAUDE-md/cli.md. It does not
# package the agents/skills/commands framework itself; a project still gets that
# via `devteam bind` (or, for now, the curl | bash `scripts/install.sh` flow).
#
# ── The two machine-written lines ────────────────────────────────────────────
#   Exactly two directives below are not maintained by hand: the `url` and the
#   digest line under it. `.github/scripts/release/bump-homebrew-formula.sh`,
#   which the release workflow runs once a version tag has been pushed, points
#   the url at that tag and writes the digest of the tarball it actually
#   downloaded. That script rewrites those two lines only and never touches
#   comments — so read the lines themselves, not this block, to know which
#   release the formula currently describes.
#
#   Before that script has ever run they hold placeholders: the tag reads
#   vX.Y.Z and the digest is the literal string
#   REPLACE_WITH_SHA256_OF_RELEASE_TARBALL. That is deliberately not a
#   plausible-looking 64-hex fake — `brew install` refuses a value that is not
#   64 hex characters, and the bump script refuses it on the way in, so an
#   unset or stale digest fails loudly instead of quietly verifying the wrong
#   bytes.
#
# ── What has actually been exercised ─────────────────────────────────────────
#   `packaging/verify-formula-locally.sh` runs this file through a real
#   Homebrew — `brew style`, `brew audit --formula`, `brew audit --strict
#   --online`, `brew install --build-from-source`, `brew test` and a smoke test
#   of the installed binary — via a throwaway
#   local tap, against a tarball built from HEAD. What is still unproven is the
#   published path: no tap hosts this formula, and no release tarball has been
#   installed from one (see packaging/README.md).
class Devteam < Formula
  desc "CLI for the dev-team-agents multi-agent development harness"
  homepage "https://github.com/Dev-Toolbelt/dev-team-agents"
  # GitHub's own auto-generated source archive for the tag — the SAME tarball
  # scripts/install.sh downloads at install time (see
  # scripts/install.sh's TARBALL_URL and scripts/lib/installer-fetch.sh), so
  # there is exactly one artifact shape to keep honest, not two.
  url "https://github.com/Dev-Toolbelt/dev-team-agents/archive/refs/tags/vX.Y.Z.tar.gz"
  sha256 "REPLACE_WITH_SHA256_OF_RELEASE_TARBALL"
  license "MIT"
  head "https://github.com/Dev-Toolbelt/dev-team-agents.git", branch: "main"

  # Homebrew core's currently-bottled python formula. This name drifts as
  # Homebrew retires old python versions, and it already has: the line said
  # python@3.12 when the file was written (2026-09), while homebrew-core's
  # python3 had moved to python@3.14 by the first real `brew install` of it.
  #
  # This line is now the ONLY place the python version appears — `install`
  # reads the version back off this dependency instead of repeating it, so the
  # python Homebrew installs and the interpreter the shebang invokes cannot
  # disagree. Nor is the drift against homebrew-core something a human has to
  # remember to check: packaging/verify-formula-locally.sh parses this line,
  # resolves `brew info python3`, and prints the two side by side on every run.
  depends_on "python@3.14"

  # The CLI enforces python 3.9+ itself (scripts/cli/devteam checks
  # sys.version_info before importing anything) and imports only the stdlib, so
  # the runtime floor here is the dependency above, not a version check this
  # formula duplicates.

  def install
    # The interpreter, derived from the declared dependency rather than named a
    # second time: `python@3.14` → `<opt>/python@3.14/bin/python3.14`. Writing
    # that basename out by hand is exactly how the old python@3.12 dependency
    # and its `python3.12` shebang got to drift apart unnoticed.
    python_dep = deps.find { |dep| dep.name.start_with?("python@") }&.name
    raise "no python@ dependency declared; there is no interpreter to point the shebang at" if python_dep.nil?

    python3 = formula_opt_bin(python_dep)/python_dep.sub("@", "")

    # Preserve the source tree's relative layout: `scripts/cli/devteam` does
    # `Path(__file__).resolve().parent.parent / "lib"` to find the `devteam`
    # package, so `cli` and `lib/devteam` must stay siblings under `scripts/`.
    # `scripts/lib` also carries files unrelated to this CLI (tiers.json,
    # render_provider.py, the provider installers, …) — install only what the
    # CLI package itself needs.
    (libexec/"scripts/cli").install "scripts/cli/devteam"
    (libexec/"scripts/lib/devteam").install Dir["scripts/lib/devteam/*.py"]

    inreplace libexec/"scripts/cli/devteam",
              "#!/usr/bin/env python3",
              "#!#{python3}"

    bin.install_symlink libexec/"scripts/cli/devteam" => "devteam"
  end

  test do
    # `devteam path --json` is read-only by design (CLAUDE-md/cli.md — it
    # reports resolved store locations and creates nothing), so this is a
    # honest smoke test: it proves the interpreter, the package layout and
    # the JSON contract all work, without touching the machine's real store.
    require "json"

    ENV["DEVTEAM_HOME"] = testpath.to_s

    output = shell_output("#{bin}/devteam path --json")
    payload = JSON.parse(output)

    assert payload.key?("ok")
    refute_path_exists testpath/"core"
    refute_path_exists testpath/"data"
  end
end
