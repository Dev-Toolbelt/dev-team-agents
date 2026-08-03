#!/usr/bin/env bash
# Usage: bash helpers/agent-lint.sh
# Validates YAML frontmatter on all agents/*.md files and skills/**/SKILL.md files.
# Checks for required fields, valid model values, and canonical skill frontmatter.
# Also validates skill identity (name == directory basename, names unique) and
# warns on over-budget skill descriptions.
# Exits 0 if all pass, 1 if any errors found. Warnings never affect the exit code.
# Flags:
#   --quiet   suppress success output when clean

set -euo pipefail

QUIET=false
for arg in "$@"; do
  case "$arg" in
    --quiet) QUIET=true ;;
  esac
done

REQUIRED_FIELDS=("name" "description" "tier" "model")
VALID_TIERS=("reasoning" "backend-exec" "frontend" "repetitive")

# scripts/lib/tiers.json stays canonical for the tier → model mapping. Each
# agent mirrors its tier's `claude` value in two places the renderer cannot
# derive at install time: the `model:` frontmatter key (Claude Code reads it to
# pick the subagent model) and the `<!-- run-banner -->` row (the model-identity
# table the agent prints). Three copies drift silently, so the mapping is
# re-derived here on every lint run and any mismatch is an error.
TIERS_JSON="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/scripts/lib/tiers.json"

# "<tier><TAB><claude model>" lines, resolved once. A missing python3 or an
# absent tiers.json legitimately skips the check (this helper also runs from a
# Stop hook), but a tiers.json that is present and unreadable is an error —
# silently skipping there would let the whole mapping drift unnoticed.
# Keep the snippet free of backslashes inside f-string expressions: that is a
# SyntaxError, and it previously turned this check into a silent no-op.
TIER_MODEL_MAP=""
TIER_MAP_BROKEN=false
if [ -f "$TIERS_JSON" ] && command -v python3 >/dev/null 2>&1; then
  if ! TIER_MODEL_MAP=$(python3 -c '
import json, sys
with open(sys.argv[1]) as fh:
    for tier, entry in json.load(fh)["tiers"].items():
        model = entry.get("claude")
        if model:
            print(tier + "\t" + model)
' "$TIERS_JSON" 2>/dev/null) || [ -z "$TIER_MODEL_MAP" ]; then
    TIER_MAP_BROKEN=true
    TIER_MODEL_MAP=""
  fi
fi

# "<tier><TAB><claude effort>" for tiers that set one. Claude Code supports a
# per-subagent `effort:` key; a tier that omits it inherits the session level,
# which is deliberate — see the _claude_note in tiers.json.
# Emits "<tier><TAB><effort>" rows and "@<agent><TAB><effort>" rows, the latter
# from the agent_effort override map, which wins over the tier level.
TIER_EFFORT_MAP=""
if [ "$TIER_MAP_BROKEN" = false ] && [ -f "$TIERS_JSON" ] && command -v python3 >/dev/null 2>&1; then
  TIER_EFFORT_MAP=$(python3 -c '
import json, sys
with open(sys.argv[1]) as fh:
    lib = json.load(fh)
for tier, entry in lib.get("effort", {}).items():
    if isinstance(entry, dict) and entry.get("claude"):
        print(tier + "\t" + entry["claude"])
for agent, entry in lib.get("agent_effort", {}).items():
    if isinstance(entry, dict) and entry.get("claude"):
        print("@" + agent + "\t" + entry["claude"])
' "$TIERS_JSON" 2>/dev/null || true)
fi

claude_model_for_tier() {
  [ -z "$TIER_MODEL_MAP" ] && return 0
  printf '%s\n' "$TIER_MODEL_MAP" | awk -F'\t' -v t="$1" '$1 == t { print $2; exit }'
}

# $1 = tier, $2 = agent name. A per-agent override wins over the tier level.
claude_effort_for() {
  [ -z "$TIER_EFFORT_MAP" ] && return 0
  local hit
  hit=$(printf '%s\n' "$TIER_EFFORT_MAP" | awk -F'\t' -v a="@$2" '$1 == a { print $2; exit }')
  if [ -n "$hit" ]; then
    printf '%s\n' "$hit"
    return 0
  fi
  printf '%s\n' "$TIER_EFFORT_MAP" | awk -F'\t' -v t="$1" '$1 == t { print $2; exit }'
}

# Skill `description` feeds the always-loaded skill index across every skill in
# the repo, so it is the highest-leverage per-character cost in the tree.
SKILL_DESC_LIMIT=95
# Descriptions feed the always-loaded skill index across every skill in the tree,
# so length here is the highest-leverage per-character cost in the repo. All
# violators were trimmed on 2026-07-31, so this is enforced. Keep it `true`:
# cut meta-narrative (which agent loads it, "authoritative", exhaustive lists),
# never the routing signal that tells an agent when to load the skill.
SKILL_DESC_STRICT=true

# Quiz-first Rule (CLAUDE.md): plain-text prompts are forbidden for ANY finite
# answer set — yes/no *and* 2–4 option multiple choice.
#   Pattern 1 — yes/no parentheticals, matched anywhere on the line.
QUIZ_YESNO_RE='\([yY]es[/ ][nN]o\)|\(y[/]n\)|\(yes\|no\)|\( yes / no \)'
#   Pattern 2 — multiple-choice prompts: a question mark immediately followed by
#   a short slash-separated option list. Anchoring on the `?` (rather than on any
#   parenthesised slash) keeps descriptive prose such as the provider list
#   "(Claude / opencode / Codex)" out of the match.
QUIZ_OPT='[A-Za-z0-9][A-Za-z0-9 ._-]{0,19}'
QUIZ_MC_RE="\\?[[:space:]\"'\`*]*\\([[:space:]]*${QUIZ_OPT}([[:space:]]*/[[:space:]]*${QUIZ_OPT})+\\)"

ERRORS=()
WARNINGS=()

# "<name><TAB><file>" entries, scanned for duplicates after all skills are read.
SKILL_NAMES=()

check_agent() {
  local file="$1"

  # Check frontmatter block exists
  local first_line
  first_line=$(head -1 "$file")
  if [ "$first_line" != "---" ]; then
    ERRORS+=("  · ${file}: missing frontmatter (file must start with ---)")
    return
  fi

  # Extract frontmatter (between first and second ---)
  local frontmatter
  frontmatter=$(awk '/^---/{n++; if(n==2) exit} n==1 && !/^---/' "$file")

  if [ -z "$frontmatter" ]; then
    ERRORS+=("  · ${file}: empty or malformed frontmatter block")
    return
  fi

  # Check required fields
  for field in "${REQUIRED_FIELDS[@]}"; do
    if ! echo "$frontmatter" | grep -qE "^${field}:"; then
      ERRORS+=("  · ${file}: missing field: ${field}")
    fi
  done

  # Validate tier value (used by render-provider.sh to pick the model per provider)
  local tier
  tier=$(echo "$frontmatter" | grep -E "^tier:" | sed 's/^tier:[[:space:]]*//' | tr -d '\r')
  if [ -z "$tier" ]; then
    ERRORS+=("  · ${file}: missing field: tier")
  else
    local tier_valid=false
    for t in "${VALID_TIERS[@]}"; do
      [ "$tier" = "$t" ] && tier_valid=true && break
    done
    if [ "$tier_valid" = false ]; then
      local tier_allowed
      tier_allowed=$(IFS=", "; echo "${VALID_TIERS[*]}")
      ERRORS+=("  · ${file}: invalid tier: ${tier} (allowed: ${tier_allowed})")
    fi
  fi

  # ── model: must mirror tiers.json[tier].claude ─────────────────────────────
  local model expected
  model=$(echo "$frontmatter" | grep -E "^model:" | head -1 | sed 's/^model:[[:space:]]*//' | tr -d '\r' | sed 's/[[:space:]]*$//')
  expected=$(claude_model_for_tier "$tier")
  if [ -n "$expected" ] && [ -n "$model" ] && [ "$model" != "$expected" ]; then
    ERRORS+=("  · ${file}: model '${model}' does not match tiers.json for tier '${tier}' (expected '${expected}')")
  fi

  # ── effort: present iff tiers.json defines one, by agent or by tier ────────
  # Setting it overrides the session's effort level, so an agent that resolves
  # to no effort must not carry the key — that is what keeps a user's lowered
  # session effort from being silently undone.
  local effort_fm expected_effort agent_stem
  # Key the override lookup on the filename stem: that is the name the renderer
  # uses, so the two lookups cannot disagree.
  agent_stem=$(basename "$file" .md)
  # `|| true` is load-bearing: effort is absent on most agents, and under
  # `set -o pipefail` a non-matching grep fails the whole substitution and
  # kills the script before a single finding is printed.
  effort_fm=$(echo "$frontmatter" | grep -E "^effort:" | head -1 | sed 's/^effort:[[:space:]]*//' | tr -d '\r' | sed 's/[[:space:]]*$//' || true)
  expected_effort=$(claude_effort_for "$tier" "$agent_stem")
  if [ -n "$expected_effort" ] && [ "$effort_fm" != "$expected_effort" ]; then
    ERRORS+=("  · ${file}: effort '${effort_fm:-<missing>}' does not match tiers.json (expected '${expected_effort}')")
  elif [ -z "$expected_effort" ] && [ -n "$effort_fm" ]; then
    ERRORS+=("  · ${file}: effort '${effort_fm}' set, but neither tier '${tier}' nor agent_effort defines a claude effort in tiers.json (omit it to inherit the session)")
  fi

  # ── run-banner row must agree with the frontmatter ─────────────────────────
  # The row is `| \`agent\` | \`tier\` | \`model\` | \`effort\` |` on the third
  # line of the block. Claude is the identity case, so the source copy carries
  # Claude's values; the renderer rewrites Model/Effort for other providers.
  local name_fm banner
  name_fm=$(echo "$frontmatter" | grep -E "^name:" | head -1 | sed 's/^name:[[:space:]]*//' | tr -d '\r' | sed 's/[[:space:]]*$//')
  # The closing-banner section must sit at the END of the body: it exists
  # purely for recency, so that the requirement is the last thing the agent
  # reads before it composes the summary it hands back. Observed compliance
  # with the top-of-file instruction alone was 0 of 6 multi-message runs.
  if ! grep -q '^## Before You Finish$' "$file"; then
    ERRORS+=("  · ${file}: missing '## Before You Finish' section (closing run banner — see skills/shared/model-identity/SKILL.md)")
  elif [ "$(grep -c '^## ' "$file")" -gt 0 ] && [ "$(grep -n '^## ' "$file" | tail -1 | cut -d: -f2-)" != "## Before You Finish" ]; then
    ERRORS+=("  · ${file}: '## Before You Finish' must be the last section — it works by recency")
  fi

  # Same `|| true` reason: without it, an agent missing the banner exits the
  # script instead of reporting the very thing this check looks for.
  banner=$(grep -A 3 '^<!-- run-banner -->$' "$file" | tail -1 || true)
  if [ -z "$banner" ]; then
    ERRORS+=("  · ${file}: missing <!-- run-banner --> block (see skills/shared/model-identity/SKILL.md)")
  else
    local b_agent b_tier b_model b_effort
    b_agent=$(echo "$banner" | awk -F'|' '{gsub(/[ `]/, "", $2); print $2}')
    b_tier=$(echo "$banner" | awk -F'|' '{gsub(/[ `]/, "", $3); print $3}')
    b_model=$(echo "$banner" | awk -F'|' '{gsub(/[ `]/, "", $4); print $4}')
    b_effort=$(echo "$banner" | awk -F'|' '{gsub(/[ `]/, "", $5); print $5}')
    [ -n "$name_fm" ] && [ "$b_agent" != "$name_fm" ] && \
      ERRORS+=("  · ${file}: run-banner agent '${b_agent}' does not match frontmatter name '${name_fm}'")
    [ -n "$tier" ] && [ "$b_tier" != "$tier" ] && \
      ERRORS+=("  · ${file}: run-banner tier '${b_tier}' does not match frontmatter tier '${tier}'")
    [ -n "$model" ] && [ "$b_model" != "$model" ] && \
      ERRORS+=("  · ${file}: run-banner model '${b_model}' does not match frontmatter model '${model}'")
    # Effort: the banner shows the tier's value, or `session-default` when the
    # tier sets none — which is what the agent actually runs at without the key.
    # The label is hyphenated on purpose: b_effort is compared after spaces are
    # stripped above, so a two-word label would have to be matched here as
    # "sessiondefault" and read like a typo.
    if [ -n "$expected_effort" ]; then
      [ "$b_effort" != "$expected_effort" ] && \
        ERRORS+=("  · ${file}: run-banner effort '${b_effort}' does not match tiers.json (expected '${expected_effort}')")
    elif [ -n "$TIER_EFFORT_MAP" ] || [ "$TIER_MAP_BROKEN" = false ]; then
      [ "$b_effort" != "session-default" ] && \
        ERRORS+=("  · ${file}: run-banner effort '${b_effort}' should be 'session-default' — this agent resolves to no claude effort in tiers.json")
    fi
  fi

  # Check for quiz-first compliance (AskUserQuestion required for finite-answer prompts)
  check_quiz_first "$file" "$QUIZ_YESNO_RE" "plain-text yes/no prompt found"
  check_quiz_first "$file" "$QUIZ_MC_RE" "plain-text multiple-choice prompt found"

  # Every agent must load project-context/SKILL.md (the Foundational Rule) —
  # it is the only place preferences.json, the Contradiction Guard, and the
  # Memory Layers routing actually get read. An agent that skips this load
  # silently ignores every user preference instead of failing loudly.
  if ! grep -q 'project-context/SKILL\.md' "$file"; then
    ERRORS+=("  · ${file}: does not reference skills/shared/project-context/SKILL.md (Foundational Rule) — user preferences.json would go unread")
  fi
}

# Flags plain-text prompts that should be an AskUserQuestion call.
# Lines inside fenced blocks or containing inline code are skipped, matching the
# original yes/no check: those are documentation of the pattern, not a live prompt.
check_quiz_first() {
  local file="$1" regex="$2" label="$3"

  local violations
  violations=$(grep -nE "$regex" "$file" 2>/dev/null | grep -v "^[0-9]*:[[:space:]]*\`\`\`" | grep -cv "^[0-9]*:.*\`" || true)
  [ -z "$violations" ] && violations=0

  if [ "$violations" -gt 0 ]; then
    ERRORS+=("  · ${file}: ${label} — use AskUserQuestion tool instead (see skills/shared/interaction-patterns/SKILL.md)")
  fi
}

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# ── Validate skill frontmatter (name + description only) ─────────────────────
check_skill() {
  local file="$1"

  local first_line
  first_line=$(head -1 "$file")
  if [ "$first_line" != "---" ]; then
    return  # No frontmatter — acceptable for some skills
  fi

  local frontmatter
  frontmatter=$(awk '/^---/{n++; if(n==2) exit} n==1 && !/^---/' "$file")
  [ -z "$frontmatter" ] && return

  # Check required skill fields
  for field in name description; do
    if ! echo "$frontmatter" | grep -qE "^${field}:"; then
      ERRORS+=("  · ${file}: missing skill field: ${field}")
    fi
  done

  # Check for non-canonical keys (only name and description allowed at top level)
  while IFS= read -r line; do
    [ -z "$line" ] && continue
    key=$(echo "$line" | grep -oE '^[a-zA-Z_-]+:' | tr -d ':' || true)
    [ -z "$key" ] && continue
    case "$key" in
      name|description) ;;  # canonical
      *) ERRORS+=("  · ${file}: non-canonical frontmatter key: ${key} (only name/description allowed)") ;;
    esac
  done <<< "$frontmatter"

  local rel="${file#"$REPO_ROOT"/}"

  # ── name must equal the directory basename ─────────────────────────────────
  # The render engine resolves opencode skills by frontmatter `name`, while the
  # installers symlink by directory. If the two disagree, the skill is
  # unreachable under one of the two providers.
  local name dir_name
  name=$(echo "$frontmatter" | grep -E "^name:" | head -1 | sed 's/^name:[[:space:]]*//' | tr -d '\r' | sed 's/^["'"'"']//; s/["'"'"']$//; s/[[:space:]]*$//')
  dir_name=$(basename "$(dirname "$file")")
  if [ -n "$name" ]; then
    if [ "$name" != "$dir_name" ]; then
      ERRORS+=("  · ${rel}: name '${name}' does not match directory '${dir_name}' (they must be identical)")
    fi
    SKILL_NAMES+=("${name}"$'\t'"${rel}")
  fi

  # ── description budget (warning — see SKILL_DESC_STRICT) ───────────────────
  local desc
  desc=$(echo "$frontmatter" | grep -E "^description:" | head -1 | sed 's/^description:[[:space:]]*//' | tr -d '\r' | sed 's/^["'"'"']//; s/["'"'"']$//; s/[[:space:]]*$//')
  if [ -n "$desc" ] && [ "${#desc}" -gt "$SKILL_DESC_LIMIT" ]; then
    if [ "$SKILL_DESC_STRICT" = true ]; then
      ERRORS+=("  · ${rel}: description is ${#desc} chars (budget: ${SKILL_DESC_LIMIT})")
    else
      # "<length><TAB><path>" so the report can rank worst offenders first.
      WARNINGS+=("${#desc}"$'\t'"${rel}")
    fi
  fi
}

# ── Skill names must be globally unique ───────────────────────────────────────
# Agent bodies and helpers/orphan-skill-scan.sh reference skills by bare name,
# so two skills in different categories sharing a name make both references
# ambiguous.
check_skill_name_uniqueness() {
  [ ${#SKILL_NAMES[@]} -eq 0 ] && return

  local dup files
  while IFS= read -r dup; do
    [ -z "$dup" ] && continue
    files=$(printf '%s\n' "${SKILL_NAMES[@]}" | awk -F'\t' -v n="$dup" '$1 == n { printf "%s%s", sep, $2; sep = ", " }')
    ERRORS+=("  · duplicate skill name '${dup}' declared in: ${files}")
  done < <(printf '%s\n' "${SKILL_NAMES[@]}" | cut -f1 | sort | uniq -d)
}

# ── Orchestration roster must match agents/ ───────────────────────────────────
# skills/architecture/orchestration/SKILL.md carries the roster an orchestrator
# reads to choose a subagent_type. It was hand-maintained and unvalidated, and it
# drifted: backend-test-specialist was listed as `repetitive` while its own
# frontmatter said `backend-exec`. A wrong NAME there is worse than a wrong tier
# — the orchestrator passes it straight to the Task tool, the spawn fails, and a
# failed spawn is trivially narrated as a success (see the skill's Spawn
# Integrity section).
ROSTER_FILE="$REPO_ROOT/skills/architecture/orchestration/SKILL.md"
# Deliberately absent from the roster: the orchestrator itself, and the
# onboarding agent, which the user invokes and no orchestrator delegates to.
ROSTER_EXEMPT=("software-architect" "setup-assistant")

check_orchestration_roster() {
  [ -f "$ROSTER_FILE" ] || return 0

  local rows row name tier agent_file actual seen=" "

  # Rows between the "## Agent Roster" heading and the next H2 only, so the
  # scope-classification table further down is not mistaken for a roster row.
  # Single-quoted on purpose: the backticks are literal markdown table syntax,
  # not command substitution.
  # shellcheck disable=SC2016
  rows=$(awk '/^## Agent Roster/{f=1;next} /^## /{f=0} f' "$ROSTER_FILE" \
         | grep -oE '^\| `[a-z0-9-]+` \| `[a-z0-9-]+` \|' || true)

  while IFS= read -r row; do
    [ -z "$row" ] && continue
    name=$(printf '%s' "$row" | awk -F'`' '{print $2}')
    tier=$(printf '%s' "$row" | awk -F'`' '{print $4}')
    seen="${seen}${name} "

    agent_file="$REPO_ROOT/agents/${name}.md"
    if [ ! -f "$agent_file" ]; then
      ERRORS+=("  · orchestration roster lists '${name}', but agents/${name}.md does not exist — an orchestrator passing that to the Task tool gets a failed spawn")
      continue
    fi

    actual=$(grep -m1 '^tier:' "$agent_file" | sed 's/^tier:[[:space:]]*//' | tr -d '[:space:]' || true)
    if [ -n "$actual" ] && [ "$actual" != "$tier" ]; then
      ERRORS+=("  · orchestration roster: '${name}' listed as tier '${tier}' but agents/${name}.md declares '${actual}'")
    fi
  done <<< "$rows"

  # Reverse direction — an agent no orchestrator can reach.
  local a base
  for a in "$REPO_ROOT"/agents/*.md; do
    [ -f "$a" ] || continue
    base=$(basename "$a" .md)
    case " ${ROSTER_EXEMPT[*]} " in *" $base "*) continue ;; esac
    case "$seen" in *" $base "*) continue ;; esac
    ERRORS+=("  · agents/${base}.md is missing from the orchestration roster — no orchestrator can delegate to it (add a row, or add it to ROSTER_EXEMPT)")
  done
}

# ── commands.json tier must match its lead agent's tier ───────────────────────
# The two fields are not independent knobs. On opencode the snippet's `agent`
# makes the command run AS that agent while `model` is resolved from the
# COMMAND's tier, so a divergence runs an agent on a model that is not its own.
# Unvalidated, two rows drifted: `tester` sat in `repetitive` while
# backend-test-specialist is `backend-exec` (contradicting the CLAUDE.md rule
# against putting a test agent on that tier), and `health-check` sat in
# `backend-exec` while naming `setup-assistant`, a `reasoning` agent. The CI
# contract checker validates the rendered output and only catches a dangling
# ref, so the source-side rule lives here — same reason as the roster check.
COMMANDS_JSON="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/scripts/lib/commands.json"

check_command_roster() {
  [ -f "$COMMANDS_JSON" ] || return 0
  command -v python3 >/dev/null 2>&1 || return 0

  local rows name tier agent agent_file actual cmd_file pin expected_pin
  rows=$(python3 -c '
import json, sys
with open(sys.argv[1]) as fh:
    lib = json.load(fh)
for name, entry in lib.get("commands", {}).items():
    if name.startswith("_") or not isinstance(entry, dict):
        continue
    print(name + "\t" + entry.get("tier", "") + "\t" + entry.get("agent", ""))
' "$COMMANDS_JSON" 2>/dev/null || true)

  if [ -z "$rows" ]; then
    ERRORS+=("  · scripts/lib/commands.json: present but no command rows could be read (command tier check skipped)")
    return 0
  fi

  while IFS=$'\t' read -r name tier agent; do
    [ -z "$name" ] && continue

    if [ -z "$agent" ]; then
      ERRORS+=("  · commands.json: '${name}' has no 'agent' — the renderer needs one even for runner commands that spawn nothing (see _filler_agent_note)")
      continue
    fi

    agent_file="$REPO_ROOT/agents/${agent}.md"
    if [ ! -f "$agent_file" ]; then
      ERRORS+=("  · commands.json: '${name}' names agent '${agent}', but agents/${agent}.md does not exist")
      continue
    fi

    actual=$(grep -m1 '^tier:' "$agent_file" | sed 's/^tier:[[:space:]]*//' | tr -d '[:space:]' || true)
    if [ -n "$actual" ] && [ "$actual" != "$tier" ]; then
      ERRORS+=("  · commands.json: '${name}' is tier '${tier}' but its lead agent '${agent}' declares '${actual}' — on opencode that runs the agent on a model that is not its own (see _tier_rule)")
    fi

    # `model:` frontmatter pin — Claude-only, and the only route by which a
    # command's tier reaches Claude Code at all (it symlinks the body and never
    # renders). The key OVERRIDES the session's model, so it is permitted on the
    # `repetitive` tier alone: a haiku pin can never raise what the user chose,
    # while pinning a `reasoning` command to opus would silently undo someone who
    # lowered the session for cost. Presence is permitted, not required — see
    # _claude_model_pin in commands.json for why `explain` deliberately has none.
    cmd_file="$REPO_ROOT/commands/${name}.md"
    if [ -f "$cmd_file" ] && [ "$(head -1 "$cmd_file")" = "---" ]; then
      pin=$(awk 'NR==1 { next } /^---[[:space:]]*$/ { exit } /^model:/ { sub(/^model:[[:space:]]*/, ""); print; exit }' \
            "$cmd_file" | tr -d '[:space:]')
      if [ -n "$pin" ]; then
        if [ "$tier" != "repetitive" ]; then
          ERRORS+=("  · commands/${name}.md: 'model: ${pin}' on a '${tier}' command — the key overrides the session model, so only 'repetitive' may pin one (see commands.json _claude_model_pin)")
        else
          expected_pin=$(claude_model_for_tier "$tier")
          if [ -n "$expected_pin" ] && [ "$pin" != "$expected_pin" ]; then
            ERRORS+=("  · commands/${name}.md: 'model: ${pin}' does not match tiers.json['${tier}'].claude (expected '${expected_pin}')")
          fi
        fi
      fi
    fi
  done <<< "$rows"
}

SEPARATOR="━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ "$TIER_MAP_BROKEN" = true ]; then
  ERRORS+=("  · scripts/lib/tiers.json: present but no tier → claude model could be read (agent model checks skipped)")
fi

for agent_file in agents/*.md; do
  [ -f "$agent_file" ] || continue
  check_agent "$agent_file"
done

while IFS= read -r skill_file; do
  # Skip references/ subdirectories
  [[ "$skill_file" == *"/references/"* ]] && continue
  check_skill "$skill_file"
done < <(find "$REPO_ROOT/skills" -name "SKILL.md" | sort)

check_skill_name_uniqueness
check_orchestration_roster
check_command_roster

# Warnings are reported only in verbose mode — they are non-blocking and would
# otherwise fire on every Stop-hook run.
SHOW_WARNINGS=false
if [ ${#WARNINGS[@]} -gt 0 ] && [ "$QUIET" = false ]; then
  SHOW_WARNINGS=true
fi

if [ ${#ERRORS[@]} -gt 0 ] || [ "$SHOW_WARNINGS" = true ]; then
  echo "$SEPARATOR"
  echo " AGENT LINT"
  echo "$SEPARATOR"
fi

if [ ${#ERRORS[@]} -gt 0 ]; then
  echo ""
  echo " ERRORS — Fix before merging:"
  for err in "${ERRORS[@]}"; do
    echo "$err"
  done
fi

if [ "$SHOW_WARNINGS" = true ]; then
  echo ""
  echo " WARN — ${#WARNINGS[@]} skill description(s) over the ${SKILL_DESC_LIMIT}-char budget (non-blocking):"
  printf '%s\n' "${WARNINGS[@]}" \
    | sort -rn \
    | head -5 \
    | awk -F'\t' -v lim="$SKILL_DESC_LIMIT" '{ printf "  · %s: description is %s chars (budget: %s)\n", $2, $1, lim }'
  if [ ${#WARNINGS[@]} -gt 5 ]; then
    echo "  … and $(( ${#WARNINGS[@]} - 5 )) more over budget"
  fi
fi

if [ ${#ERRORS[@]} -gt 0 ] || [ "$SHOW_WARNINGS" = true ]; then
  echo ""
  echo "$SEPARATOR"
fi

if [ ${#ERRORS[@]} -gt 0 ]; then
  exit 1
fi

if [ "$QUIET" = false ]; then
  if [ ${#WARNINGS[@]} -gt 0 ]; then
    echo "agent-lint: no errors ✓ (${#WARNINGS[@]} warning(s))"
  else
    echo "agent-lint: clean ✓"
  fi
fi
