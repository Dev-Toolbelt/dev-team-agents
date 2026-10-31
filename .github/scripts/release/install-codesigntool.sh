#!/usr/bin/env bash
# Unpacks SSL.com's CodeSignTool for app/build/sign-windows.cjs (ADR-0055).
#
#   install-codesigntool.sh PROD   production eSigner: a real, publicly trusted signature
#   install-codesigntool.sh TEST   the eSigner sandbox: a test certificate, never shippable
#
# The zip is pinned by version and SHA-256 and checked before it is unpacked. The config the
# tool reads, and the hash of the jar inside, are owned by sign-windows.cjs, which checks the
# jar and rewrites the config right before every signing. Exports CODESIGNTOOL_HOME,
# CODESIGNTOOL_JAVA and WIN_ESIGNER_ENVIRONMENT to the following steps through GITHUB_ENV.
set -euo pipefail

ENVIRONMENT="${1:-}"
# SSL.com publishes no checksum for CodeSignTool, so this one was computed from the release
# asset downloaded on 2026-10-31 (its layout and bundled conf checked by hand): it proves the
# file is the one reviewed then, not that SSL.com built it. Repeat both on a version bump, and
# update JAR / JAR_SHA256 in app/build/sign-windows.cjs with it.
VERSION="v1.3.2"
URL="https://github.com/SSLcom/CodeSignTool/releases/download/${VERSION}/CodeSignTool-${VERSION}.zip"
SHA256="f14b1e1ef14bfa1fd00279c363aab0debbf5dcfba0e4bcdce5d22bb771de0e3a"

case "$ENVIRONMENT" in
  PROD | TEST) ;;
  *)
    echo "usage: $0 PROD|TEST" >&2
    exit 2
    ;;
esac

: "${RUNNER_TEMP:?RUNNER_TEMP is not set: this script runs in GitHub Actions}"
: "${GITHUB_ENV:?GITHUB_ENV is not set: this script runs in GitHub Actions}"

ZIP="$RUNNER_TEMP/CodeSignTool-${VERSION}.zip"
HOME_DIR="$RUNNER_TEMP/codesigntool"

curl -fsSL --retry 3 -o "$ZIP" "$URL"
# From stdin: with a file name holding a backslash (every Windows path), GNU sha256sum
# prefixes its output line with '\', which would never match.
actual="$(sha256sum < "$ZIP" | cut -d' ' -f1)"
if [ "$actual" != "$SHA256" ]; then
  echo "::error::CodeSignTool ${VERSION} checksum mismatch: expected $SHA256, got $actual. Refusing to run it."
  exit 1
fi

rm -rf "$HOME_DIR"
mkdir -p "$HOME_DIR"
# Git Bash's tar is GNU tar, which cannot read a zip; python's zipfile can, and every hosted
# image has python.
if command -v unzip >/dev/null 2>&1; then
  unzip -q "$ZIP" -d "$HOME_DIR" -x '__MACOSX/*'
else
  python="$(command -v python3 || command -v python)"
  "$python" -m zipfile -e "$ZIP" "$HOME_DIR"
fi

# CodeSignTool needs Java 11 or newer. The hosted Windows image carries several JDKs and its
# default JAVA_HOME is not guaranteed to be one of those, so 17 is named explicitly.
java="java"
if [ -n "${JAVA_HOME_17_X64:-}" ]; then
  java="${JAVA_HOME_17_X64}/bin/java"
fi

# node reads these on Windows, so they are handed over as Windows paths there.
home_out="$HOME_DIR"
if command -v cygpath >/dev/null 2>&1; then
  home_out="$(cygpath -w "$HOME_DIR")"
  [ "$java" = "java" ] || java="$(cygpath -w "$java")"
fi

{
  echo "CODESIGNTOOL_HOME=$home_out"
  echo "CODESIGNTOOL_JAVA=$java"
  echo "WIN_ESIGNER_ENVIRONMENT=$ENVIRONMENT"
} >> "$GITHUB_ENV"
echo "CodeSignTool ${VERSION} unpacked for the ${ENVIRONMENT} eSigner environment."
