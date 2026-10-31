#!/usr/bin/env bash
# Security gate (ADR-0059): gitleaks over the whole git history, semgrep at ERROR severity.
#
# gitleaks: findings already reviewed are listed in .gitleaksignore and .gitleaks.toml; any
# other finding fails the job. The scan needs the full history (checkout fetch-depth: 0).
#
# semgrep: explicit rulesets with --metrics=off. `--config auto` would report repository
# context to semgrep.dev, and `p/bash` does not exist (the shell ruleset is `r/bash`) — a run
# naming it fails the config load and can look like a clean pass. A false positive is
# suppressed where it occurs, with `# nosemgrep: <rule> -- <reason>`.
set -euo pipefail

PIN=.github/security-tools.pin
pin() { sed -n "s/^$1=//p" "$PIN"; }

GL_VERSION="$(pin gitleaks_version)"
ARCH="$(uname -m)"
GL_SHA="$(pin "gitleaks_sha256_${ARCH}")"
case "$ARCH" in x86_64) GL_ARCH=x64 ;; aarch64) GL_ARCH=arm64 ;; *) GL_ARCH="" ;; esac
if [ -z "$GL_VERSION" ] || [ -z "$GL_SHA" ] || [ -z "$GL_ARCH" ]; then
  echo "::error::$PIN has no gitleaks version or no sha256 for arch '$ARCH'"
  exit 1
fi

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
curl -fsSL --retry 3 --retry-delay 2 -o "$WORK/gitleaks.tar.gz" \
  "https://github.com/gitleaks/gitleaks/releases/download/v${GL_VERSION}/gitleaks_${GL_VERSION}_linux_${GL_ARCH}.tar.gz"
echo "${GL_SHA}  $WORK/gitleaks.tar.gz" | sha256sum --check --strict
tar -xzf "$WORK/gitleaks.tar.gz" -C "$WORK" gitleaks

echo "── gitleaks ${GL_VERSION}: full history"
"$WORK/gitleaks" git --redact --no-banner --log-level warn --exit-code 1 .

echo "── semgrep $(pin semgrep_version)"
python3 -m pip install --quiet --disable-pip-version-check "semgrep==$(pin semgrep_version)"
semgrep scan --metrics=off --quiet --error --severity ERROR \
  --config p/python --config p/typescript --config p/secrets --config p/github-actions \
  --config r/bash --config p/command-injection \
  --exclude node_modules --exclude dist --exclude release \
  scripts app/src app/test .github helpers tests
