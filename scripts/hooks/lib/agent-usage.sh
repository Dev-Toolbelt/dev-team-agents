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
#   - their matching toolUseResult carries agentId, resolvedModel (the REAL
#     model that ran, not the tiers.json config), and outputFile
#   - outputFile is the subagent's own transcript; token usage is the sum of
#     message.usage.{input_tokens,output_tokens,cache_creation_input_tokens,
#     cache_read_input_tokens} across all of its lines
#
# Known imprecision (documented, not hidden): every agent in this harness
# launches async (status starts "async_launched"), and the parent transcript's
# toolUseResult was NOT observed to update in place once the agent finishes —
# completion instead surfaces as a separate task-notification elsewhere in the
# transcript. Rather than build unverified detection for that, this scan reads
# whatever outputFile contains at scan time. Dedup is by transcript byte
# offset (an Agent tool_use/toolUseResult pair is scanned at most once), so an
# agent whose outputFile was still being written when its parent entry was
# scanned is undercounted and NOT retried on a later Stop. This trades
# occasional undercount for simplicity and for never blocking or slowing the
# Stop hook waiting on a background agent to finish.
set -uo pipefail

devteam_queue_agent_usage() {
    local hook_payload="$1"
    local user_data_dir="$2"
    local telemetry_send="$3"

    command -v python3 >/dev/null 2>&1 || return 0
    [ -f "$hook_payload" ] || return 0

    local transcript_path
    transcript_path=$(python3 -c \
        "import json; d=json.load(open('$hook_payload')); print(d.get('transcript_path',''))" \
        2>/dev/null || echo "")
    [ -n "$transcript_path" ] && [ -f "$transcript_path" ] || return 0

    local cache_file="${user_data_dir}/.agent-usage-cache"
    local cached_path="" cached_offset=0
    if [ -f "$cache_file" ]; then
        IFS=$'\x1f' read -r cached_path cached_offset < "$cache_file" 2>/dev/null || true
    fi

    local file_size
    file_size=$(stat -f %z "$transcript_path" 2>/dev/null || stat -c %s "$transcript_path" 2>/dev/null || echo 0)
    local start_offset=0
    if [ "$cached_path" = "$transcript_path" ] \
        && [ "${cached_offset:-0}" -le "${file_size:-0}" ] 2>/dev/null; then
        start_offset="${cached_offset:-0}"
    fi

    # Emits one line per completed agent as agent_name\x1fmodel\x1finput\x1foutput\x1fcache_creation\x1fcache_read
    # followed by a final line "OFFSET\x1f<new_offset>".
    local scan_result
    scan_result=$(python3 -c "
import json

path = '${transcript_path}'
start_offset = ${start_offset}
new_offset = start_offset
results = []

try:
    with open(path, 'rb') as f:
        f.seek(start_offset)
        data = f.read()
    newline_idx = data.rfind(b'\n')
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
        msg = entry.get('message', {})
        content = msg.get('content')
        if isinstance(content, list):
            for c in content:
                if isinstance(c, dict) and c.get('type') == 'tool_use' and c.get('name') == 'Agent':
                    # toolUseResult.parentUuid references the whole message's
                    # own 'uuid' field, not the tool_use content block's 'id'.
                    name = (c.get('input') or {}).get('subagent_type', 'unknown')
                    if entry.get('uuid'):
                        agent_names[entry['uuid']] = name
        tur = entry.get('toolUseResult')
        if isinstance(tur, dict) and tur.get('agentId') and tur.get('outputFile'):
            agent_name = agent_names.get(entry.get('parentUuid'), 'unknown')
            model = tur.get('resolvedModel', 'unknown')
            out_path = tur.get('outputFile')
            totals = {'input_tokens': 0, 'output_tokens': 0,
                      'cache_creation_input_tokens': 0, 'cache_read_input_tokens': 0}
            try:
                with open(out_path, 'r', errors='ignore') as of:
                    for oline in of:
                        oline = oline.strip()
                        if not oline:
                            continue
                        try:
                            oentry = json.loads(oline)
                        except Exception:
                            continue
                        usage = (oentry.get('message') or {}).get('usage') or {}
                        for k in totals:
                            totals[k] += usage.get(k, 0) or 0
            except Exception:
                continue
            results.append((agent_name, model, totals['input_tokens'], totals['output_tokens'],
                             totals['cache_creation_input_tokens'], totals['cache_read_input_tokens']))
except Exception:
    pass

for r in results:
    print('\x1f'.join(str(x) for x in r))
print(f'OFFSET\x1f{new_offset}')
" 2>/dev/null || printf 'OFFSET\x1f%s' "$start_offset")

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
