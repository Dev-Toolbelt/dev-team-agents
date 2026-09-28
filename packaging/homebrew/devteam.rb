# devteam.rb — Homebrew formula for the dev-team-agents CLI (ADR-0011).
#
# Packages ONLY the `devteam` CLI (`scripts/cli/devteam` + `scripts/lib/devteam/`) —
# the global core/data-store manager described in CLAUDE-md/cli.md. It does not
# package the agents/skills/commands framework itself; a project still gets that
# via `devteam bind` (or, for now, the curl | bash `scripts/install.sh` flow).
#
# ── PLACEHOLDER VALUES — replace before this formula is published ───────────
#   url    below points at a real git tag, but no such tag has been cut yet.
#   sha256 is the literal string "REPLACE_WITH_SHA256_OF_RELEASE_TARBALL" —
#          not a plausible-looking fake digest, so a stale/unset value fails
#          loudly (`brew install` refuses a wrong-length/non-hex sha256)
#          instead of silently succeeding against the wrong bytes.
#   `.github/workflows/release.yml` computes the real sha256 from the actual
#   release tarball and rewrites both lines — see packaging/README.md.
#
# This formula has never been run through `brew install` or `brew audit` — there
# is no Homebrew tap to install it from yet (see packaging/README.md).
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
  # Homebrew retires old python versions (it was python@3.12 at authoring
  # time, 2026-09) — confirm the current formula name with
  # `brew info python3` before publishing, and update this line and the
  # `python3` constant in `install` together.
  depends_on "python@3.12"

  # The CLI enforces python 3.9+ itself (scripts/cli/devteam checks
  # sys.version_info before importing anything), so the runtime floor here is
  # the dependency above, not a version check this formula duplicates.

  def install
    python3 = Formula["python@3.12"].opt_bin/"python3.12"

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
    refute_predicate testpath/"core", :exist?
    refute_predicate testpath/"data", :exist?
  end
end
