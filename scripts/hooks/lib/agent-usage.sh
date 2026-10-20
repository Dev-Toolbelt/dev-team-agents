#!/usr/bin/env bash
# scripts/hooks/lib/agent-usage.sh — per-agent token/model telemetry.
# Not a hook. Sourced by scripts/hooks/stop/05-telemetry.sh, which calls
# devteam_queue_agent_usage before its existing flush step.
#
# Data source: the Stop hook payload's transcript_path (proven in production
# by stop/_disabled-04-notifier.sh, same incremental byte-offset scan technique
# reused here with a separate cache file so the two never collide).
#
# What is captured, and why, per empirical verification against a real
# session transcript (not documentation):
#   - tool_use entries named "Agent" carry input.subagent_type (the agent name)
#   - their matching toolUseResult carries agentId and resolvedModel (the REAL
#     model that ran, not the tiers.json config); a background launch ack also
#     carries outputFile
#   - the subagent's own transcript is outputFile, else
#     <session transcript minus .jsonl>/subagents/agent-<agentId>.jsonl; its
#     usage is counted by devteam/usage.py (ADR-0041), once per message.id —
#     Claude Code writes several lines per message while it streams
#
# Foreground agents are counted from their result. A background agent's
# completion surfaces as a separate task-notification, not as a second
# toolUseResult, so it is never counted twice: its launch ack is scanned once,
# reading whatever its transcript holds at scan time. Dedup is by transcript
# byte offset, so an agent still running when its ack was scanned is
# undercounted and NOT retried on a later Stop — the execution trace
# (devteam tasks trace) reads it again once it ends. This trades occasional
# undercount for never blocking or slowing the Stop hook.
set -uo pipefail

# shellcheck source=scripts/hooks/lib/file-stat.sh
. "$(dirname "${BASH_SOURCE[0]}")/file-stat.sh"

devteam_queue_agent_usage() {
    local hook_payload="$1"
    local user_data_dir="$2"
    local telemetry_send="$3"

    command -v python3 >/dev/null 2>&1 || return 0
    [ -f "$hook_payload" ] || return 0

    local transcript_path
    transcript_path=$(python3 -c \
        'import json,sys; d=json.load(open(sys.argv[1])); print(d.get("transcript_path",""))' \
        "$hook_payload" 2>/dev/null || echo "")
    [ -n "$transcript_path" ] && [ -f "$transcript_path" ] || return 0

    local cache_file="${user_data_dir}/.agent-usage-cache"
    local cached_path="" cached_offset=0
    if [ -f "$cache_file" ]; then
        IFS=$'\x1f' read -r cached_path cached_offset < "$cache_file" 2>/dev/null || true
    fi

    local file_size
    file_size=$(dt_file_size "$transcript_path")
    local start_offset=0
    if [ "$cached_path" = "$transcript_path" ] \
        && [ "${cached_offset:-0}" -le "${file_size:-0}" ] 2>/dev/null; then
        start_offset="${cached_offset:-0}"
    fi

    # Emits one line per completed agent as agent_name\x1fmodel\x1finput\x1foutput\x1fcache_creation\x1fcache_read
    # followed by a final line "OFFSET\x1f<new_offset>".
    local scan_result
    # The path and offset go in as arguments, never into the program text. Token counting is
    # devteam/usage.py's, shared with the execution trace (ADR-0041): one count per message,
    # read from the subagent's own transcript beside the session's.
    local lib_dir
    lib_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" 2>/dev/null && pwd)"
    [ -n "$lib_dir" ] || return 0
    scan_result=$(python3 -I -c "
import json, sys
sys.path.insert(0, sys.argv[3])
try:
    from devteam import usage
except ImportError:
    # A tree without the CLI package: say so on stderr (the caller discards it) and count nothing,
    # rather than keep the offset and miss these agents forever.
    sys.stderr.write('agent-usage: devteam package not found under ' + sys.argv[3] + '\\n')
    print('OFFSET\\x1f' + sys.argv[2])
    sys.exit(0)

path = sys.argv[1]
start_offset = int(sys.argv[2])
new_offset = start_offset
results = []

try:
    with open(path, 'rb') as f:
        f.seek(start_offset)
        data = f.read()
    newline_idx = data.rfind(b'\\n')
    processed = data[:newline_idx + 1] if newline_idx != -1 else b''
    new_offset = start_offset + len(processed)

    agent_names = {}
    for line in processed.decode('utf-8', errors='ignore').splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except Exception:
            continue
        msg = entry.get('message') or {}
        content = msg.get('content') if isinstance(msg, dict) else None
        if isinstance(content, list):
            for c in content:
                if isinstance(c, dict) and c.get('type') == 'tool_use' and c.get('name') == 'Agent':
                    # toolUseResult.parentUuid references the whole message's
                    # own 'uuid' field, not the tool_use content block's 'id'.
                    name = (c.get('input') or {}).get('subagent_type', 'unknown')
                    if entry.get('uuid'):
                        agent_names[entry['uuid']] = name
        tur = entry.get('toolUseResult')
        if isinstance(tur, dict) and tur.get('agentId'):
            agent_name = agent_names.get(entry.get('parentUuid'), 'unknown')
            model = tur.get('resolvedModel', 'unknown')
            out_path = tur.get('outputFile') or usage.claude_subagent_path(path, str(tur.get('agentId')))
            totals = usage.claude_transcript_usage(out_path)
            if totals is None:
                continue
            results.append((agent_name, model, totals['input'], totals['output'],
                             totals['cache_write'], totals['cache_read']))
except Exception:
    pass

for r in results:
    print('\\x1f'.join(str(x) for x in r))
print(f'OFFSET\\x1f{new_offset}')
" "$transcript_path" "$start_offset" "$lib_dir" 2>/dev/null || printf 'OFFSET\x1f%s' "$start_offset")

    local new_offset="$start_offset"
    while IFS=$'\x1f' read -r f1 f2 f3 f4 f5 f6; do
        [ -n "${f1:-}" ] || continue
        if [ "$f1" = "OFFSET" ]; then
            new_offset="${f2:-$start_offset}"
            continue
        fi
        local props
        props=$(printf '{"agent_name":"%s","model":"%s","input_tokens":%s,"output_tokens":%s,"cache_creation_input_tokens":%s,"cache_read_input_tokens":%s,"provider":"claude"}' \
            "$f1" "$f2" "${f3:-0}" "${f4:-0}" "${f5:-0}" "${f6:-0}")
        bash "$telemetry_send" --queue "agent_completed" "$props" 2>/dev/null || true
    done <<< "$scan_result"

    printf '%s\x1f%s\n' "$transcript_path" "$new_offset" > "$cache_file" 2>/dev/null || true
}
