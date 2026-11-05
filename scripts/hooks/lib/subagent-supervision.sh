#!/usr/bin/env bash
# Shared SubagentStop supervision check (ADR-0062 decision 4), sourced by the Claude Code dispatcher
# (`subagent-supervise.sh`) and the Codex sub-script (`subagent-stop/00-supervision.sh`).
#
#   devteam_subagent_supervise < payload.json
#
# Prints `{"decision":"block","reason":"..."}` when a finished agent from `agents/` ended without its
# closing run banner (or, for a reviewer / QA agent, without the review-result marker); prints nothing
# otherwise. Built-in and namespaced agents are never held, and only a stop whose `stop_hook_active` is
# an explicit `false` is held: a continuation, or a payload without the field, is let go, so it never loops. Fails open: any
# error, a missing python3, a malformed payload prints nothing and returns 0.
#
# Language: the reason is read by the held model, not the user, so it is plain English and does not go
# through devteam_msg (reuse rule `hook_message_language` covers user-facing text only).

devteam_subagent_supervise() {
    local lib agents_dir
    lib="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd)" || return 0
    agents_dir="$lib/../../../agents"
    [ -d "$agents_dir" ] || return 0
    # shellcheck source=scripts/lib/python.sh
    [ -f "$lib/../../lib/python.sh" ] && . "$lib/../../lib/python.sh"
    command -v python3 >/dev/null 2>&1 || return 0
    local input type_re='"agent_type"[[:space:]]*:[[:space:]]*"([a-z0-9][a-z0-9-]*)"'
    input="$(head -c 4194304)"
    # Cheap exit before forking python: an agent type with no definition in agents/ is never held, and
    # neither is a namespaced one (`plugin:name`): devteam agents register under their bare name.
    [[ "$input" =~ $type_re ]] || return 0
    [ -f "$agents_dir/${BASH_REMATCH[1]}.md" ] || return 0
    # shellcheck disable=SC2016  # the program is single-quoted on purpose
    printf '%s' "$input" | python3 -c '
import json, os, re, sys

# Mirrors REVIEW_RESULT_AGENTS in helpers/agent-lint.sh; deliberately broader than the task-board
# review types (review_triggers.REVIEW_AGENTS): seo-specialist emits the marker but opens no window.
REVIEWERS = {"qa-specialist", "code-reviewer", "backend-reviewer", "frontend-reviewer", "seo-specialist"}
MARKER = "<!-- review-result: findings="
try:
    payload = json.loads(sys.stdin.read())
    if not isinstance(payload, dict) or payload.get("stop_hook_active") is not False:
        sys.exit(0)
    agent = payload.get("agent_type")
    message = payload.get("last_assistant_message")
    if not isinstance(agent, str) or not isinstance(message, str):
        sys.exit(0)
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", agent):
        sys.exit(0)
    agents_dir = sys.argv[1]
    definition = os.path.join(agents_dir, agent + ".md")
    if not os.path.isfile(definition):
        sys.exit(0)
    row = re.compile(r"^\s*\|\s*`" + re.escape(agent) + r"`\s*\|", re.M)
    missing = []
    if not row.search(message):
        missing.append("banner")
    if agent in REVIEWERS and MARKER not in message:
        missing.append("marker")
    if not missing:
        sys.exit(0)
    parts = []
    if "banner" in missing:
        table = ""
        with open(definition, encoding="utf-8") as handle:
            lines = handle.read().splitlines()
        for i, line in enumerate(lines):
            if line.strip() == "<!-- run-banner -->":
                block = []
                for nxt in lines[i + 1:]:
                    if not nxt.lstrip().startswith("|"):
                        break
                    block.append(nxt)
                table = "\n".join(block)
                break
        parts.append(
            "Your final message has no closing run banner. Append the table from the `## Model Identity` "
            "block of your agent definition under the heading **Ran on:**, as the last thing in the message."
            + ("\n\n" + table if table else "")
        )
    if "marker" in missing:
        parts.append(
            "Your final message has no review-result marker. End it with `<!-- review-result: findings=N -->` "
            "(N = the number of findings in your Findings Table; 0 when clean), as defined in the review-result skill."
        )
    reason = "Supervision gate: " + " ".join(parts) + "\n\nReply with your complete final report again, including what is missing."
    sys.stdout.write(json.dumps({"decision": "block", "reason": reason}))
except SystemExit:
    raise
except Exception:
    pass
' "$agents_dir" 2>/dev/null
    return 0
}
