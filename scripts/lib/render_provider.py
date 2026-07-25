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
      - codex:   `<target>/.codex/prompts/devteam-<name>.md` (body verbatim)

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
    f"> **Provider: {provider}.** The agent body below was authored for Claude Code. "
    f"Apply the following conventions when interpreting it:"
    ]
    if not renames and not idioms:
        note_lines.append("> · (no renames — tool references are native or "
                          "self-explanatory in this provider.)")
    else:
        for src, dst in renames.items():
            note_lines.append(f"> · `{src}` → `{dst}`")
        for line in idioms:
            note_lines.append(f"> {line}")
        extra = prov_entry.get("_post_render_note")
        if extra:
            note_lines.append("> " + extra)
    note_lines.append("")
    return "\n".join(note_lines)


# ─── agent rendering per provider ─────────────────────────────────────
def render_agent_claude(name, fm, body, src_path):
    # Claude is the identity case — return source verbatim.
    return {"path": f".claude/agents/dev-team/{name}.md", "content": src_path.read_text()}


def render_agent_opencode(name, fm, body, model_id, effort, tool_map):
    desc = fm.get("description", "").strip()
    tools_list = [t.strip() for t in (fm.get("tools", "") or "").split(",") if t.strip()]
    permission = _opencode_permission(tools_list)
    fm_lines = ["---", f"description: {desc}", "mode: subagent"]
    # NOTE: opencode schema has no `effort` field — unknown frontmatter is
    # silently routed into an untyped `options` object, so emitting it was a
    # no-op (see docs/providers.md Known Limitations). Not emitted.
    if permission:
        fm_lines.append("permission:")
        for k, v in permission.items():
            fm_lines.append(f"  {k}: {v}")
    fm_lines.append("---")
    fm_text = "\n".join(fm_lines) + "\n"
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
    snippet_entry = {
        "description": meta.get("description", ""),
        "agent": meta.get("agent", ""),
        "template": tool_conventions_note("opencode", tool_map) + body,
    }
    return {
        "snippet_key": f"devteam:{name}",
        "snippet_entry": snippet_entry,
    }


def render_command_codex(name, meta, body, model_id, effort, tool_map):
    note = tool_conventions_note("codex", tool_map)
    # First paragraph becomes description in a comment header, then body.
    desc = meta.get("description", "")
    content = f"<!-- description: {desc} -->\n<!-- model: {model_id} | agent: {meta.get('agent','')} -->\n\n" + note + body
    return {"path": f".codex/prompts/devteam-{name}.md", "content": content}


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


def resolve_effort(tiers_lib, provider, tier):
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
            effort = resolve_effort(lib["tiers"], args.provider, tier)
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
            body = cmd_path.read_text()
            meta = commands_meta.get(name)
            if not meta:
                die(f"command '{name}' has no metadata entry in scripts/lib/commands.json — add one")
            tier = meta["tier"]
            model_id = resolve_model(lib["tiers"], args.provider, tier)
            effort = resolve_effort(lib["tiers"], args.provider, tier)
            if args.provider == "claude":
                rendered.append(render_command_claude(name, body, cmd_path))
            elif args.provider == "opencode":
                entry = render_command_opencode(name, meta, body, model_id, effort, lib["tool_map"])
                opencode_snippet[entry["snippet_key"]] = entry["snippet_entry"]
            elif args.provider == "codex":
                rendered.append(render_command_codex(name, meta, body, model_id, effort, lib["tool_map"]))

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