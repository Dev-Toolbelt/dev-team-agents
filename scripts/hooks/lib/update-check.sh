#!/usr/bin/env bash
# Shared helpers for pre-tool-use/01-check-updates.sh.
# Sourced, never executed directly. Every function degrades to a silent no-op on
# failure — a PreToolUse hook must never block a tool call.
#
# Not a hook. Sourced by pre-tool-use/01-check-updates.sh only.

# uc_ttl_fresh / uc_interval_hours read and write state.json via
# state_get/state_set. Source defensively in case a caller other than
# session-start.sh (which already sources it) pulls this file in directly.
if ! command -v state_get >/dev/null 2>&1; then
    # shellcheck source=scripts/lib/state.sh
    . "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/state.sh"
fi

UC_DEFAULT_INTERVAL_HOURS=24

# ── Time ──────────────────────────────────────────────────────────────────────
# Current epoch seconds. Uses the bash 4.2+ printf builtin so the hot path (a
# fresh TTL cache) forks nothing at all; falls back to date(1) on bash 3.2,
# which is still the system bash on macOS.
uc_now_epoch() {
    if [ "${BASH_VERSINFO[0]:-0}" -gt 4 ] || \
       { [ "${BASH_VERSINFO[0]:-0}" -eq 4 ] && [ "${BASH_VERSINFO[1]:-0}" -ge 2 ]; }; then
        local now
        printf -v now '%(%s)T' -1
        printf '%s' "$now"
    else
        date +%s
    fi
}

# ── Preferences ───────────────────────────────────────────────────────────────
# uc_read_pref <prefs_file> <key> <python_default>
# Forks python3. Callers must keep this off the hot path.
uc_read_pref() {
    local prefs_file="$1" key="$2" default="$3"
    if [ -f "$prefs_file" ] && command -v python3 >/dev/null 2>&1; then
        python3 -c \
            "import json; d=json.load(open('$prefs_file')); print(d.get('$key',$default))" \
            2>/dev/null && return 0
    fi
    printf '%s' "$default" | tr -d "'"
}

# uc_interval_hours <prefs_file> <state_file>
# Resolves update_check_interval_hours, mirroring the resolved value into
# state.json's "update_check_interval" key for visibility.
#
# This used to cache the resolved value in a standalone sidecar file,
# invalidated via `[ prefs_file -nt cache_file ]` — a bash builtin, zero forks
# on a cache hit. That trick does not survive consolidation into state.json:
# state.json is also touched by session_id/session_head on every session
# start, so its mtime is effectively always "now" and the comparison would
# almost always report the cache as fresh, silently pinning the interval to
# whatever was first resolved. Since this whole block now runs once per
# SessionStart (not once per tool call, which is what the original hot-path
# optimization was guarding against), the extra python3 fork here is
# negligible — so the cache is dropped and the preference is read directly.
uc_interval_hours() {
    local prefs_file="$1" state_file="$2" hours=""

    hours=$(uc_read_pref "$prefs_file" update_check_interval_hours "$UC_DEFAULT_INTERVAL_HOURS")
    case "$hours" in
        ''|*[!0-9]*) hours="$UC_DEFAULT_INTERVAL_HOURS" ;;
    esac
    state_set update_check_interval "$hours" "$state_file" 2>/dev/null || true
    printf '%s' "$hours"
}

# uc_ttl_fresh <state_file> <interval_hours> <now_epoch>
# Returns 0 when the last check (state.json "last_update_check") is still
# inside the TTL window (nothing to do).
uc_ttl_fresh() {
    local state_file="$1" interval_hours="$2" now="$3" last=""
    last="$(state_get last_update_check "$state_file")"
    case "$last" in
        ''|*[!0-9]*) return 1 ;;
    esac
    [ $(( now - last )) -lt $(( interval_hours * 3600 )) ]
}

# ── HTTP ──────────────────────────────────────────────────────────────────────
# Defines HTTP_GET / HTTP_DL. Returns 1 when neither curl nor wget is available.
# The two are defined conditionally here and called by uc_fetch_latest /
# uc_auto_update after this function has run, which shellcheck cannot follow.
# shellcheck disable=SC2317,SC2329  # invoked by callers after uc_setup_http succeeds
uc_setup_http() {
    if command -v curl >/dev/null 2>&1; then
        HTTP_GET() { curl -fsSL --connect-timeout 5 --max-time 10 "$1"; }
        HTTP_DL()  { curl -fsSL --connect-timeout 5 --max-time 30 -o "$1" "$2"; }
        return 0
    fi
    # wget path: ETag conditional requests are not used; fall through without caching.
    if command -v wget >/dev/null 2>&1; then
        HTTP_GET() { wget -qO- "$1"; }
        HTTP_DL()  { wget -qO "$1" "$2"; }
        return 0
    fi
    return 1
}

# uc_fetch_latest <github_api> <etag_file> <version_cache_file>
# Prints the latest release tag (empty when it cannot be resolved).
# On a 304 the cached version string is reused, so an install that is behind the
# still-latest release is still detected.
uc_fetch_latest() {
    local api="$1" etag_file="$2" version_cache="$3"
    local latest="" api_resp="" http_status="" tmp_headers tmp_body

    tmp_headers=$(mktemp 2>/dev/null) || return 0
    tmp_body=$(mktemp 2>/dev/null) || { rm -f "$tmp_headers"; return 0; }

    if command -v curl >/dev/null 2>&1; then
        local curl_args=(-sS --connect-timeout 5 --max-time 10 \
                         -D "$tmp_headers" -o "$tmp_body" -w "%{http_code}")
        if [ -f "$etag_file" ]; then
            local cached_etag
            cached_etag=$(cat "$etag_file" 2>/dev/null || true)
            [ -n "$cached_etag" ] && curl_args+=(-H "If-None-Match: ${cached_etag}")
        fi
        http_status=$(curl "${curl_args[@]}" "${api}/releases/latest" 2>/dev/null || echo "000")

        if [ "$http_status" = "304" ]; then
            latest=$(cat "$version_cache" 2>/dev/null || true)
        else
            if [ "$http_status" = "200" ]; then
                local new_etag
                new_etag=$(grep -i '^etag:' "$tmp_headers" | head -1 \
                    | sed 's/^[Ee][Tt][Aa][Gg]: *//;s/\r//' || true)
                [ -n "$new_etag" ] && printf '%s' "$new_etag" > "$etag_file"
            fi
            api_resp=$(cat "$tmp_body" 2>/dev/null || true)
        fi
    else
        api_resp=$(HTTP_GET "${api}/releases/latest" 2>/dev/null || true)
    fi
    rm -f "$tmp_headers" "$tmp_body"

    if [ -z "$latest" ]; then
        latest=$(printf '%s' "$api_resp" \
            | grep '"tag_name"' | head -1 \
            | sed 's/.*"tag_name": *"\([^"]*\)".*/\1/' || true)
    fi

    if [ -z "$latest" ]; then
        api_resp=$(HTTP_GET "${api}/tags" 2>/dev/null || true)
        latest=$(printf '%s' "$api_resp" \
            | grep '"name"' | head -1 \
            | sed 's/.*"name": *"\([^"]*\)".*/\1/' || true)
    fi

    [ -n "$latest" ] && printf '%s' "$latest" > "$version_cache" 2>/dev/null
    printf '%s' "$latest"
}

# ── Notifications ─────────────────────────────────────────────────────────────
# uc_is_suppressed <type> — reads the UC_SUPPRESS global ("true"/"false"/csv list)
uc_is_suppressed() {
    local type="$1"
    [ "${UC_SUPPRESS:-false}" = "true" ] && return 0
    case ",${UC_SUPPRESS:-false}," in *,"$type",*) return 0 ;; esac
    return 1
}

uc_notify() {
    local type="$1" msg="$2" icon
    uc_is_suppressed "$type" && return 0
    case "$type" in
        warning)  icon="⚠️" ;;
        critical) icon="🚨" ;;
        *)        icon="ℹ️" ;;
    esac
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo " $icon  DEV TEAM AGENTS  $icon"
    echo " $msg"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
}

# uc_message <updated|available> <lang> <current> <latest>
uc_message() {
    local kind="$1" lang="$2" current="$3" latest="$4"
    if [ "$kind" = "updated" ]; then
        case "$lang" in
            pt-BR|pt*) printf '%s' "dev-team-agents atualizado para $latest. Execute um health check para verificar: \"Faça um health check neste projeto\"." ;;
            es*)       printf '%s' "dev-team-agents actualizado a $latest. Ejecuta un health check para verificar: \"Haz un health check en este proyecto\"." ;;
            *)         printf '%s' "dev-team-agents updated to $latest. Run a health check to verify: \"Run a health check on this project\"." ;;
        esac
        return 0
    fi
    case "$lang" in
        pt-BR|pt*) printf '%s' "Atualização disponível: $current → $latest
 Execute: .dev-team-agents/scripts/update.sh
 Auto-update: update.sh --enable-auto" ;;
        es*)       printf '%s' "Actualización disponible: $current → $latest
 Ejecuta: .dev-team-agents/scripts/update.sh
 Auto-update: update.sh --enable-auto" ;;
        *)         printf '%s' "Update available: $current → $latest
 Run: .dev-team-agents/scripts/update.sh
 Auto-update: update.sh --enable-auto" ;;
    esac
}

# ── Auto-update ───────────────────────────────────────────────────────────────
# uc_auto_update_enabled <prefs_file> <user_data_dir>
uc_auto_update_enabled() {
    local prefs_file="$1" user_data_dir="$2" auto="false"
    if [ -f "$prefs_file" ] && command -v python3 >/dev/null 2>&1; then
        auto=$(python3 -c \
            "import json; d=json.load(open('$prefs_file')); print(str(d.get('auto_update',False)).lower())" \
            2>/dev/null || echo false)
    fi
    # Legacy flag file support (migration period)
    [ -f "${user_data_dir}/.auto-update" ] && auto=true
    [ "$auto" = "true" ]
}

# uc_perform_auto_update <current> <latest> [install_dir]
#
# Runs the same fetch-and-verify path as the manual `update.sh`. Auto-update is
# the *less* supervised of the two — nobody is watching it — so it must not be
# the one that pipes an unverified download into bash. It delegates to
# scripts/lib/installer-fetch.sh, which pins the ref, checks the payload is a
# parseable installer for this project, and honours a published SHA-256.
#
# If that library is missing (partial install, trimmed tree), auto-update is
# skipped rather than falling back to an unverified fetch: a silently skipped
# upgrade is recoverable, a tampered one is not.
uc_perform_auto_update() {
    local current="$1" latest="$2" install_dir="${3:-}"
    local fetch_lib tmp_installer rc=0

    if [ -z "$install_dir" ]; then
        install_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." 2>/dev/null && pwd)" || return 1
    fi
    fetch_lib="$install_dir/scripts/lib/installer-fetch.sh"

    if [ ! -f "$fetch_lib" ]; then
        echo ""
        echo "→ Update available ($current → $latest), but the installer"
        echo "  verification library is missing. Skipping the automatic update."
        echo "  Run /devteam:update to upgrade with verification."
        return 1
    fi

    echo ""
    echo "→ Auto-updating dev-team-agents: $current → $latest"

    # shellcheck source=/dev/null
    . "$fetch_lib" || return 1

    tmp_installer=$(mktemp 2>/dev/null) || return 1
    trap 'rm -f "$tmp_installer"' RETURN

    dta_fetch_installer "$tmp_installer" "$latest" || rc=$?
    if [ "$rc" -ne 0 ]; then
        echo "→ Automatic update aborted: the installer failed verification." >&2
        return 1
    fi

    bash "$tmp_installer" "$latest"
}
