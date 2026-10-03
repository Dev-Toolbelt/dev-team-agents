#!/usr/bin/env bash
# Local account service for development (ADR-0029): the Supabase stack in Docker, with the
# CLI pointed at it through the loopback test seam (SR-44). Dev-only; never shipped.
#
#   bash infra/supabase/dev-local.sh up       # start (first run pulls the images)
#   eval "$(bash infra/supabase/dev-local.sh env)"
#   devteam auth login --email you@example.test   # codes arrive in Mailpit, http://127.0.0.1:54324
#   bash infra/supabase/dev-local.sh down     # stop, keeping the database
#   bash infra/supabase/dev-local.sh reset    # stop and drop the local database
#
# The stack runs from a generated copy under .local/ (gitignored): config.toml with SMTP,
# Google and GitHub switched off, so mail goes to Mailpit and no OAuth app is needed. The
# committed config.toml is never edited, so a `supabase config push` cannot inherit a local
# setting. Secrets made here (signing key, ban pepper) are local-only and never leave .local/.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOCAL="$HERE/.local"
UNUSED_SERVICES="realtime,storage-api,imgproxy,studio"
WORKDIR="$LOCAL"           # the CLI reads $WORKDIR/supabase/config.toml
PROJECT="$LOCAL/supabase"
SECRETS="$LOCAL/secrets"
KID="test-local"           # the seam accepts only kids with the test- prefix
API_URL="http://127.0.0.1:54321"   # [api] port in config.toml

die() { printf 'dev-local: %s\n' "$*" >&2; exit 1; }

need() {
    command -v supabase >/dev/null 2>&1 || die "supabase CLI not found (brew install supabase/tap/supabase)"
    command -v openssl >/dev/null 2>&1 || die "openssl not found"
    docker info >/dev/null 2>&1 || die "Docker is not running"
}

sb() { supabase --workdir "$WORKDIR" "$@"; }

sync_project() {
    mkdir -p "$PROJECT"
    # The CLI resolves symlinks and refuses paths outside the project, so these are copies,
    # refreshed on every `up` so an edited migration or function is picked up.
    for dir in migrations templates tests functions; do
        rm -rf "${PROJECT:?}/$dir"
        cp -R "$HERE/$dir" "$PROJECT/$dir"
    done
    cp "$HERE/seed.sql" "$PROJECT/seed.sql"
    python3 - "$HERE/config.toml" "$PROJECT/config.toml" <<'PY'
import re, sys
src = open(sys.argv[1], encoding="utf-8").read()
for section in ("auth.email.smtp", "auth.external.google", "auth.external.github"):
    src, count = re.subn(r"(\[%s\]\n)enabled = true" % re.escape(section), r"\1enabled = false", src)
    if count != 1:
        sys.exit("dev-local: cannot switch off [%s] in config.toml" % section)
open(sys.argv[2], "w", encoding="utf-8").write(src)
PY
}

make_secrets() {
    mkdir -p "$SECRETS"
    chmod 700 "$SECRETS"
    if [ ! -f "$SECRETS/entitlement.pem" ]; then
        (umask 077; openssl genpkey -algorithm ed25519 -out "$SECRETS/entitlement.pem")
    fi
    if [ ! -f "$SECRETS/ban-hmac-key" ]; then
        (umask 077; openssl rand -base64 48 | tr -d '\n' > "$SECRETS/ban-hmac-key")
    fi
    # Read by the edge runtime at start. Written after sync_project, which replaces functions/.
    local private
    private="$(openssl pkcs8 -topk8 -nocrypt -in "$SECRETS/entitlement.pem" -outform DER | base64 | tr -d '\n')"
    # ENTITLEMENT_ISSUER: inside the stack SUPABASE_URL is the gateway's internal address,
    # while the CLI checks `iss` against the URL it calls.
    (umask 077; printf 'ENTITLEMENT_ED25519_PRIVATE_KEY=%s\nENTITLEMENT_KID=%s\nBAN_HMAC_KEY=%s\nENTITLEMENT_ISSUER=%s\n' \
        "$private" "$KID" "$(cat "$SECRETS/ban-hmac-key")" "$API_URL" > "$PROJECT/functions/.env")
}

public_key() {
    # base64url without padding, the only encoding the CLI accepts.
    openssl pkey -in "$SECRETS/entitlement.pem" -pubout -outform DER | tail -c 32 | base64 | tr '+/' '-_' | tr -d '=\n'
}

status_value() {
    sb status -o env 2>/dev/null | sed -n "s/^$1=\"\{0,1\}\([^\"]*\)\"\{0,1\}$/\1/p"
}

cmd_up() {
    need
    sync_project
    make_secrets
    sb stop >/dev/null 2>&1 || true
    # The account service needs only auth, the database, the gateway, edge functions and
    # Mailpit; the others are unused here and can fail the start's health check.
    sb start --exclude "$UNUSED_SERVICES"
    # shellcheck disable=SC2016  # the eval line is printed for the user to run, unexpanded.
    printf '\nReady. Next:\n  eval "$(bash %s env)"\n  devteam auth login --email you@example.test\n' "${BASH_SOURCE[0]}"
    printf 'Mail (sign-in and reset codes): http://127.0.0.1:54324\n'
}

cmd_env() {
    [ -f "$SECRETS/entitlement.pem" ] || die "run '$0 up' first"
    local url anon
    url="$(status_value API_URL)"
    anon="$(status_value ANON_KEY)"
    [ -n "$url" ] && [ -n "$anon" ] || die "the local stack is not running ('$0 up')"
    printf 'export DEVTEAM_AUTH_TEST_URL=%s\n' "$url"
    printf 'export DEVTEAM_AUTH_TEST_KID=%s\n' "$KID"
    printf 'export DEVTEAM_AUTH_TEST_PUBKEY=%s\n' "$(public_key)"
    printf 'export DEVTEAM_AUTH_TEST_ANON_KEY=%s\n' "$anon"
    # A throwaway store, so the local account never mixes with your real one.
    printf 'export DEVTEAM_HOME=%s\n' "$LOCAL/devteam-home"
}

cmd_down() { need; sb stop; }

cmd_reset() { need; sb stop --no-backup; rm -rf "$LOCAL/devteam-home"; }

case "${1:-}" in
    up) cmd_up ;;
    env) cmd_env ;;
    down) cmd_down ;;
    reset) cmd_reset ;;
    *) printf 'usage: %s up|env|down|reset\n' "$0" >&2; exit 2 ;;
esac
