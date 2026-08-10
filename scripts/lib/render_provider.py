#!/usr/bin/env python3
"""render_provider.py — Render the dev-team-agents canonical source into a
provider-specific output tree.

Reads the single source of truth (`agents/*.md`, `commands/*.md`, plus
`scripts/lib/{tiers,tool-map,command-map,commands}.json`) and emits a fully
formed provider installation into `<target>/.claude/`, `<target>/.opencode/`,
or `<target>/.codex/`.

Design:
  · Agent and command BODIES are emitted verbatim — no token munging.
  · A small "Tool conventions" preamble is prepended to every rendered agent
    body, mapping Claude Code tool names the body uses to that provider's
    native tool names. The mapping source is `scripts/lib/tool-map.json`.
  · Agent frontmatter is reshaped per provider (`opencode` uses
    `description/mode/model/permission/options`; `codex` uses TOML
    `name/description/model/model_reasoning_effort/developer_instructions`;
    `claude` is the identity case).
  · Commands are emitted as:
      - claude:  `<target>/.claude/commands/devteam/<name>.md` (body verbatim)
      - opencode: a JSON snippet at
                  `<target>/.opencode/commands.snippet.jsonc` containing
                  `{ "devteam:plan": {...}, ... }` to be deep-merged into the
                  project's `opencode.json` `command` block by the installer.
      - codex:   `<target>/.codex/skills/devteam-<name>/SKILL.md`

Usage:
  python3 render_provider.py --provider <p> --source-dir <S> --target-dir <T>
                             [--agents-only] [--commands-only] [--dry-run]

Exits non-zero with a clear message on any unknown tier, unknown provider,
or missing `tier:` key in an agent's frontmatter (fail-fast).
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from textwrap import dedent


REQUIRED_AGENT_TIERS = ("reasoning", "backend-exec", "frontend", "repetitive")
VALID_PROVIDERS = ("claude", "opencode", "codex")


# ─── minimal YAML frontmatter parser (handles flat key: value, optional
#     block scalar `key: |` continuation) ─────────────────────────────────
def parse_frontmatter(text):
    """Returns (frontmatter_dict, body_str)."""
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    block = text[3:end].lstrip("\n")
    body = text[end + 4:].lstrip("\n")
    fm = {}
    lines = block.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip() or line.lstrip().startswith("#"):
            i += 1
            continue
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*)\s*:\s*(.*)$", line)
        if not m:
            i += 1
            continue
        key, val = m.group(1), m.group(2).strip()
        if val in ("|", ">"):
            # block scalar — gather following indented lines
            collected = []
            i += 1
            while i < len(lines) and (lines[i].startswith(" ") or lines[i].startswith("\t")):
                collected.append(lines[i].strip())
                i += 1
            fm[key] = "\n".join(collected)
        else:
            fm[key] = val
            i += 1
    return fm, body


# ─── path rewriting ──────────────────────────────────────────────────
def apply_path_rewrites(body, provider, tool_map):
    """Rewrite path references in body text per provider's path_rewrites map.
    
    Replaces prefix patterns like 'docs/development/' with provider-specific
    alternatives like 'docs/' (for codex/opencode). Applied to the body text
    before output.
    """
    prov_entry = tool_map.get("providers", {}).get(provider, {})
    rewrites = prov_entry.get("path_rewrites", {}) or {}
    if not rewrites:
        return body
    result = body
    for old_prefix, new_prefix in rewrites.items():
        result = result.replace(old_prefix, new_prefix)
    return result


# ─── plan gate softening ─────────────────────────────────────────────
def soften_plan_gate(body, provider, plan_gate_setting):
    """Remove or soften the mandatory PLAN GATE section for non-Claude providers.
    
    - Claude: keep verbatim
    - codex/opencode with plan_gate="conditional": strip the mandatory gate,
      replace with a lighter note
    - codex/opencode with plan_gate="opt_out": strip entirely
    - codex/opencode with plan_gate="required": keep verbatim
    """
    if provider == "claude":
        return body
    
    if plan_gate_setting == "required":
        return body
    
    # Pattern: the PLAN GATE section starts with "---" (optional blank line after)
    # followed by "**PLAN GATE" and ends at the next "---" or "Task: $ARGUMENTS".
    plan_gate_pattern = re.compile(
        r"\n---\s*\n\*\*PLAN GATE.*?(?=\n---|\nTask: \$ARGUMENTS)",
        re.DOTALL
    )
    
    if plan_gate_setting == "opt_out":
        result = plan_gate_pattern.sub("", body)
        # Also remove the "Task: $ARGUMENTS" line if it's leftover stand-alone
        result = re.sub(r"\n+Task: \$ARGUMENTS", "", result)
        return result
    
    # plan_gate_setting == "conditional" — soften
    soft_note = (
        "\n\n**Plan mode.** For complex or architecturally significant tasks, "
        "present a brief plan before executing and wait for user approval. "
        "For simple tasks (one-liner fixes, straightforward changes), "
        "execute directly.\n"
    )
    result = plan_gate_pattern.sub(soft_note, body)
    # Keep Task: $ARGUMENTS reference
    return result


# ─── body text replacements for Codex ────────────────────────────────
# Patterns found in agent/command bodies that reference Claude-specific
# tools or idioms. Each is replaced with the Codex equivalent.

_CODEX_BODY_REPLACEMENTS = [
    (r'\bTodoWrite\b', 'update_plan'),
    (r'\bthe Task tool\b', 'spawn_agent'),
    (r'\bthe `Task` tool\b', 'spawn_agent'),
    (r'\bvia the Task tool\b', 'via spawn_agent'),
    (r'\bUse the Task tool\b', 'Use spawn_agent'),
    (r'\bTask tool\b', 'spawn_agent'),
    (r'\b`Task` tool\b', 'spawn_agent'),
    # question tool phrasing (opencode-specific name; Codex uses request_user_input)
    (r'\bthe `question` tool\b', "`request_user_input` (Plan mode)"),
    (r'\b`question` tool\b', "`request_user_input` (Plan mode)"),
    (r'\bquestion tool\b', "`request_user_input` (Plan mode)"),
    # Hook references that are Claude-specific
    (r'\.claude/settings\.json', '.codex/hooks.json'),
]


def codex_question_fallback_clause(interaction_mode):
    if interaction_mode == "required":
        return (
            "if it is unavailable in the current surface, tell the user to "
            "switch this task to `/plan` and retry so Codex can show the "
            "interactive chooser"
        )
    return (
        "if it is unavailable in the current surface, ask the same question "
        "directly in the conversation, preserving the same options and the "
        "same recommended choice"
    )


def codex_question_replacements(interaction_mode):
    fallback = codex_question_fallback_clause(interaction_mode)
    return [
        (r'\buse the `AskUserQuestion` tool with options:\b',
         f"use the `request_user_input` tool (Plan mode) with the same options; {fallback}:"),
        (r'\buse the \*\*`AskUserQuestion`\*\* tool with a single question:\b',
         f"use the **`request_user_input`** tool (Plan mode) for the same single question; {fallback}:"),
        (r'\buse the \*\*`AskUserQuestion`\*\* tool to offer a health check:\b',
         f"use the **`request_user_input`** tool (Plan mode) to offer the same health check; {fallback}:"),
        (r'\buse `AskUserQuestion` for every question with a finite set of answers\b',
         f"use the `request_user_input` tool (Plan mode) for every question with a finite set of answers; {fallback}"),
        (r'\bvia `AskUserQuestion`\b', "via `request_user_input` (Plan mode)"),
        (r'\bwith `AskUserQuestion`\b', "with `request_user_input` (Plan mode)"),
        (r'\bvia AskUserQuestion\b', "via `request_user_input` (Plan mode)"),
        (r'\bwith AskUserQuestion\b', "with `request_user_input` (Plan mode)"),
        (r'\bthe `AskUserQuestion` tool\b', "`request_user_input` (Plan mode)"),
        (r'\b`AskUserQuestion` tool\b', "`request_user_input` (Plan mode)"),
        (r'\bAskUserQuestion\b', "`request_user_input` (Plan mode)"),
        (r'\bthe `question` tool\b', "`request_user_input` (Plan mode)"),
        (r'\b`question` tool\b', "`request_user_input` (Plan mode)"),
        (r'\bquestion tool\b', "`request_user_input` (Plan mode)"),
    ]


def _slugify_identifier(text):
    value = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    return value or "user_choice"


def _convert_codex_question_payload(payload):
    questions = payload.get("questions")
    if not isinstance(questions, list) or not questions:
        return payload

    converted = []
    for index, question in enumerate(questions, start=1):
        if not isinstance(question, dict):
            converted.append(question)
            continue

        header = str(question.get("header") or f"Choice {index}")
        prompt = str(question.get("question") or "Choose one option.")
        base_id = question.get("id") or header or prompt
        qid = _slugify_identifier(str(base_id))

        options = []
        raw_options = question.get("options") or []
        if isinstance(raw_options, list):
            for option in raw_options:
                if not isinstance(option, dict):
                    continue
                label = str(option.get("label") or "").strip()
                if not label or label.lower() == "other":
                    continue
                options.append({
                    "label": label,
                    "description": str(option.get("description") or "").strip(),
                })

        converted.append({
            "header": header,
            "id": qid,
            "question": prompt,
            "options": options[:3],
        })

    return {"questions": converted}


_CODEX_JSON_BLOCK_RE = re.compile(r"```json\s*\n(.*?)\n```", re.DOTALL)


def rewrite_codex_question_blocks(body):
    """Convert AskUserQuestion JSON examples into request_user_input payloads."""

    def _replace(match):
        raw_payload = match.group(1).strip()
        try:
            parsed = json.loads(raw_payload)
        except json.JSONDecodeError:
            return match.group(0)

        if not isinstance(parsed, dict) or "questions" not in parsed:
            return match.group(0)

        converted = _convert_codex_question_payload(parsed)
        rendered = json.dumps(converted, indent=2, ensure_ascii=False)
        return dedent(
            f"""\
            ```json
            {rendered}
            ```
            """
        ).rstrip()

    return _CODEX_JSON_BLOCK_RE.sub(_replace, body)

def apply_codex_body_rewrites(body, interaction_mode="optional"):
    """Apply all Codex-specific text replacements to the body.
    
    Runs BEFORE the preamble is prepended, so the body is self-contained
    and references only Codex-native tools and paths.
    """
    result = body
    replacements = codex_question_replacements(interaction_mode) + _CODEX_BODY_REPLACEMENTS
    for pattern, replacement in replacements:
        flags = re.IGNORECASE
        if r'\n' in pattern:
            flags |= re.DOTALL
        result = re.sub(pattern, replacement, result, flags=flags)
    return rewrite_codex_question_blocks(result)


def apply_codex_command_specialization(name, body):
    """Apply command-specific Codex-only behavior without mutating the source command.

    Keep the canonical command body provider-agnostic; specialize only the
    rendered Codex output where the runtime UX differs.
    """
    if name != "commit":
        return body

    original = dedent(
        """\
        **If there are no staged files but there are unstaged or untracked changes**, do not stop with a plain-text blocker. Use `AskUserQuestion` with a single-select question:

        - `Stage all and commit` — run `git add -A` and continue normally
        - `Just show the commit plan` — continue in preview mode as if `--dry-run` had been passed
        - `Abort` — stop without staging or committing anything
        """
    ).strip()

    replacement = dedent(
        """\
        **If there are no staged files but there are unstaged or untracked changes**, do not stop with a plain-text blocker. First determine today's session files by cross-referencing today's `.dev-team-agents/user-data/session-summary.md` entry (if present) and files touched in this conversation. Then use `AskUserQuestion` with a single-select question:

        - `Stage only today's files and commit` — stage only files that match today's session/context and continue normally; this is the default Codex path
        - `Stage everything and commit` — run `git add -A` and continue normally
        - `Just show the commit plan` — continue in preview mode as if `--dry-run` had been passed
        - `Abort` — stop without staging or committing anything

        If today's session/context cannot be determined confidently, treat `Just show the commit plan` as the recommended fallback instead of staging everything by default.
        """
    ).strip()

    return body.replace(original, replacement)


# ─── tool-map rendering ────────────────────────────────────────────────
def tool_conventions_note(provider, tool_map):
    """Returns a markdown note string prepended to every rendered agent body.

    Two concerns, kept compact:
      1. Per-provider native tool name for the Claude Code tool names the body
         references (tool_rewrites from tool-map.json).
      2. Idiom translation notes — how "Load skills/X/SKILL.md" and
         "spawn the agent at .claude/agents/dev-team/X.md" idioms used in the
         body map to this provider's native mechanism.
    """
    prov_entry = tool_map.get("providers", {}).get(provider, {})
    renames = prov_entry.get("tool_rewrites", {}) or {}
    idioms = prov_entry.get("idiom_notes", []) or []
    note_lines = [
    f"> **Provider: {provider}.** This body uses Claude Code idioms. "
    f"Apply these conventions when interpreting it:"
    ]
    if not renames and not idioms:
        note_lines.append("> · (no renames — tool references are native or "
                          "self-explanatory in this provider.)")
    else:
        for line in idioms:
            note_lines.append(f"> {line}")
    note_lines.append("")
    return "\n".join(note_lines)


# ─── run banner ────────────────────────────────────────────────────────
# The `<!-- run-banner -->` block in an agent body carries the model identity
# table the agent emits before doing anything else (see
# skills/shared/model-identity/SKILL.md). The source copy holds Claude's values
# because Claude is the identity case; every other provider gets its Model and
# Effort cells rewritten here, so the agent never has to resolve them at runtime.
_RUN_BANNER_RE = re.compile(
    r"(<!-- run-banner -->\n"          # anchor comment
    r"\|[^\n]*\|\n"                    # header row
    r"\|[^\n]*\|\n)"                   # separator row
    r"\|([^|\n]*)\|([^|\n]*)\|[^|\n]*\|[^|\n]*\|",  # data row: agent | tier | model | effort
)


def render_run_banner(body, model_id, effort, provider):
    """Rewrite the run-banner data row's Model and Effort cells for `provider`.

    Agent and Tier cells are provider-agnostic and pass through untouched.
    Returns the body unchanged when the agent carries no banner block — a
    missing banner is handled by the agent (per the model-identity skill), not
    by failing the render.
    """
    if provider == "claude":
        return body  # identity case — the source already holds Claude's values

    model_cell = model_id
    if provider == "codex" and model_id.startswith("openai/"):
        # Match what the rendered TOML frontmatter actually declares.
        model_cell = model_id.split("/", 1)[1]

    def _sub(m):
        return (
            f"{m.group(1)}"
            f"|{m.group(2)}|{m.group(3)}| `{model_cell}` | `{effort or 'session-default'}` |"
        )

    return _RUN_BANNER_RE.sub(_sub, body, count=1)


# ─── agent rendering per provider ─────────────────────────────────────
def render_agent_claude(name, fm, body, src_path):
    # Claude is the identity case — return source verbatim.
    return {"path": f".claude/agents/dev-team/{name}.md", "content": src_path.read_text()}


def render_agent_opencode(name, fm, body, model_id, effort, tool_map):
    desc = fm.get("description", "").strip()
    tools_list = [t.strip() for t in (fm.get("tools", "") or "").split(",") if t.strip()]
    permission = _opencode_permission(tools_list)
    fm_lines = ["---", f"description: {desc}", "mode: subagent"]
    if model_id:
        fm_lines.append(f"model: {model_id}")
    if effort:
        fm_lines.append(f"variant: {effort}")
    if permission:
        fm_lines.append("permission:")
        for k, v in permission.items():
            fm_lines.append(f"  {k}: {v}")
    fm_lines.append("---")
    fm_text = "\n".join(fm_lines) + "\n"
    # Apply only opencode-specific path rewrites to the agent body.
    body = apply_path_rewrites(body, "opencode", tool_map)
    # Last, so the banner's resolved values are authoritative over any rewrite.
    body = render_run_banner(body, model_id, effort, "opencode")
    note = tool_conventions_note("opencode", tool_map)
    content = fm_text + "\n" + note + body
    return {"path": f".opencode/agents/{name}.md", "content": content}


def _opencode_permission(tools_list):
    """Maps Claude `tools:` list → opencode `permission:` object.

    Every agent is allowed to spawn subagents via the `task` tool, regardless
    of whether its Claude `tools:` line lists `Task`. Per the framework's
    agent design, any agent may delegate. Without this, opencode would
    prompt before each `task` call.
    """
    perm = {"task": "allow"}
    has_bash = False
    for t in tools_list:
        t = t.strip()
        if t == "Read":
            perm["read"] = "allow"
        elif t in ("Write", "Edit"):
            perm["edit"] = "allow"
        elif t == "Glob":
            perm["glob"] = "allow"
        elif t == "Grep":
            perm["grep"] = "allow"
        elif t == "Bash":
            has_bash = True
            perm["bash"] = "ask"
        elif t == "WebSearch":
            perm["websearch"] = "allow"
        elif t == "WebFetch":
            perm["webfetch"] = "allow"
        elif t == "AskUserQuestion":
            perm["question"] = "allow"
        elif t == "TodoWrite":
            perm["todowrite"] = "allow"
    if not has_bash:
        perm["bash"] = "deny"
    return perm


def render_agent_codex(name, fm, body, model_id, effort, tool_map):
    desc = fm.get("description", "").strip().replace('"', '\\"')
    # Codex strips provider prefix from `openai/gpt-5.6-sol` → `gpt-5.6-sol`.
    if model_id.startswith("openai/"):
        model_id_short = model_id.split("/", 1)[1]
    else:
        model_id_short = model_id
    # Apply path rewrites and Codex body rewrites
    body = apply_path_rewrites(body, "codex", tool_map)
    body = apply_codex_body_rewrites(body, "optional")
    # Last, so the banner's resolved values are authoritative over any rewrite.
    body = render_run_banner(body, model_id, effort, "codex")
    note = tool_conventions_note("codex", tool_map)
    instructions = note + body
    # TOML literal block string (triple-quoted).
    toml_lines = [
        f'name = "{name}"',
        f'description = "{desc}"',
        f'model = "{model_id_short}"',
    ]
    if effort:
        toml_lines.append(f'model_reasoning_effort = "{effort}"')
    toml_lines.append('developer_instructions = """')
    toml_lines.append(instructions)
    toml_lines.append('"""')
    toml = "\n".join(toml_lines) + "\n"
    return {"path": f".codex/agents/{name}.toml", "content": toml}


# ─── command rendering per provider ──────────────────────────────────
def render_command_claude(name, body, src_path):
    return {"path": f".claude/commands/devteam/{name}.md", "content": src_path.read_text()}


def render_command_opencode(name, meta, body, model_id, effort, tool_map):
    body = apply_path_rewrites(body, "opencode", tool_map)
    body = soften_plan_gate(body, "opencode", meta.get("plan_gate", "conditional"))
    snippet_entry = {
        "description": meta.get("description", ""),
        "agent": meta.get("agent", ""),
        "model": model_id,
        "template": tool_conventions_note("opencode", tool_map) + body,
    }
    if effort:
        snippet_entry["variant"] = effort
    return {
        "snippet_key": f"devteam:{name}",
        "snippet_entry": snippet_entry,
    }


def render_command_codex(name, meta, body, model_id, effort, tool_map):
    note = tool_conventions_note("codex", tool_map)
    interaction_mode = meta.get("interaction_mode", "optional")
    # Apply path rewrites, Codex body rewrites, and plan gate softening
    body = apply_path_rewrites(body, "codex", tool_map)
    body = apply_codex_command_specialization(name, body)
    body = apply_codex_body_rewrites(body, interaction_mode)
    body = soften_plan_gate(body, "codex", meta.get("plan_gate", "conditional"))
    desc = meta.get("description", "")
    skill_content = (
        "---\n"
        f'name: "devteam-{name}"\n'
        f'description: "{desc}"\n'
        "---\n\n"
        f"<!-- codex-plan-gate: {meta.get('plan_gate', 'conditional')} -->\n"
        f"<!-- codex-interaction-mode: {interaction_mode} -->\n\n"
        + note + body
    )
    return {"path": f".codex/skills/devteam-{name}/SKILL.md", "content": skill_content}


# ─── validation ───────────────────────────────────────────────────────
def load_lib(lib_dir):
    def _load(name):
        p = lib_dir / name
        if not p.exists():
            die(f"missing required lib file: {p}")
        return json.loads(p.read_text())
    return {
        "tiers": _load("tiers.json"),
        "tool_map": _load("tool-map.json"),
        "command_map": _load("command-map.json"),
        "commands": _load("commands.json"),
    }


def die(msg, code=1):
    sys.stderr.write(f"render-provider: ERROR: {msg}\n")
    sys.exit(code)


def resolve_model(tiers_lib, provider, tier):
    if tier not in tiers_lib["tiers"]:
        die(f"unknown tier '{tier}' (expected one of {REQUIRED_AGENT_TIERS})")
    tier_entry = tiers_lib["tiers"][tier]
    if provider not in tier_entry:
        die(f"tier '{tier}' has no model id for provider '{provider}' "
            f"— add a column to scripts/lib/tiers.json")
    return tier_entry[provider]


def resolve_effort(tiers_lib, provider, tier, agent=None):
    """Effort for `tier` on `provider`, or None when neither level applies.

    A per-agent entry in `agent_effort` wins over the tier-level `effort` map:
    effort tracks how much a role needs to reason, which does not always follow
    the tier that picks its model. Commands pass their lead agent from
    commands.json — they run AS that agent on opencode, so its override applies
    to them too. `agent` is None only when no lead agent is known.
    """
    if agent:
        override = tiers_lib.get("agent_effort", {}).get(agent)
        if isinstance(override, dict) and override.get(provider):
            return override[provider]
    eff = tiers_lib.get("effort", {}).get(tier, {})
    return eff.get(provider)


# ─── main ─────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider", required=True, choices=VALID_PROVIDERS)
    ap.add_argument("--source-dir", required=True)
    ap.add_argument("--target-dir", required=True)
    ap.add_argument("--agents-only", action="store_true")
    ap.add_argument("--commands-only", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    src = Path(args.source_dir).resolve()
    tgt = Path(args.target_dir).resolve()
    if not src.is_dir():
        die(f"source dir not found: {src}")
    if not tgt.exists():
        tgt.mkdir(parents=True, exist_ok=True)

    lib = load_lib(src / "scripts" / "lib")
    rendered = []  # list of (path, content | snippet-instruction)

    do_agents = not args.commands_only
    do_commands = not args.agents_only

    if do_agents:
        agents_dir = src / "agents"
        for agent_path in sorted(agents_dir.glob("*.md")):
            name = agent_path.stem
            text = agent_path.read_text()
            fm, body = parse_frontmatter(text)
            tier = fm.get("tier")
            if not tier:
                die(f"agent '{name}' has no `tier:` key in frontmatter — "
                    f"add one of {REQUIRED_AGENT_TIERS}")
            model_id = resolve_model(lib["tiers"], args.provider, tier)
            effort = resolve_effort(lib["tiers"], args.provider, tier, agent=name)
            if args.provider == "claude":
                rendered.append(render_agent_claude(name, fm, body, agent_path))
            elif args.provider == "opencode":
                rendered.append(render_agent_opencode(name, fm, body, model_id, effort, lib["tool_map"]))
            elif args.provider == "codex":
                rendered.append(render_agent_codex(name, fm, body, model_id, effort, lib["tool_map"]))

    if do_commands:
        commands_dir = src / "commands"
        commands_meta = lib["commands"].get("commands", {})
        opencode_snippet = {}
        for cmd_path in sorted(commands_dir.glob("*.md")):
            name = cmd_path.stem
            # Command frontmatter is Claude-only: a `model:` key pins that
            # command's body to a fixed model instead of the session's. The
            # other providers resolve the model from commands.json `tier`, so
            # the block is stripped here — left in, it would be emitted as
            # literal YAML at the head of the opencode `template` string and of
            # the Codex prompt. render_command_claude re-reads the source file,
            # so Claude still receives it byte-identical (the contract checker
            # enforces exactly that).
            _cmd_fm, body = parse_frontmatter(cmd_path.read_text())
            meta = commands_meta.get(name)
            if not meta:
                die(f"command '{name}' has no metadata entry in scripts/lib/commands.json — add one")
            tier = meta["tier"]
            model_id = resolve_model(lib["tiers"], args.provider, tier)
            # The lead agent is passed on purpose: on opencode the snippet's
            # `agent` makes the command run AS that agent, so an agent_effort
            # override has to reach the command too. Without it, `devteam:qa`
            # ran qa-specialist at the tier's effort while spawning the same
            # agent directly gave it `low` — the effort-axis twin of the model
            # mismatch that commands.json `_tier_rule` now prevents.
            effort = resolve_effort(lib["tiers"], args.provider, tier, meta.get("agent"))
            if args.provider == "claude":
                rendered.append(render_command_claude(name, body, cmd_path))
            elif args.provider == "opencode":
                entry = render_command_opencode(name, meta, body, model_id, effort, lib["tool_map"])
                opencode_snippet[entry["snippet_key"]] = entry["snippet_entry"]
            elif args.provider == "codex":
                codex_outputs = render_command_codex(name, meta, body, model_id, effort, lib["tool_map"])
                if isinstance(codex_outputs, list):
                    rendered.extend(codex_outputs)
                else:
                    rendered.append(codex_outputs)

        if args.provider == "opencode" and opencode_snippet:
            snippet_path = tgt / ".opencode" / "commands.snippet.jsonc"
            rendered.append({
                "path": str(snippet_path.relative_to(tgt)),
                "content": "// Auto-generated by scripts/render-provider.sh.\n"
                           "// Deep-merge the keys below into the `command` object of your\n"
                           "// project's opencode.json(.jsonc). Each key is exposed as\n"
                           "// `/devteam:<name>`.\n" + json.dumps(opencode_snippet, indent=2, ensure_ascii=False),
            })

    # ─── write outputs ───────────────────────────────────────────────
    if args.dry_run:
        print(f"[dry-run] provider={args.provider} emit_count={len(rendered)}")
        for r in rendered:
            print(f"  would write: {r['path']}")
        return

    for r in rendered:
        p = tgt / r["path"]
        p.parent.mkdir(parents=True, exist_ok=True)
        if p.exists() and args.provider == "claude":
            # Claude installation will symlink over these, so skip overwrite.
            continue
        p.write_text(r["content"])
        print(f"  + {r['path']}")

    print(f"render-provider: emitted {len(rendered)} files for provider '{args.provider}' "
          f"into {tgt}")


if __name__ == "__main__":
    main()
