#!/usr/bin/env python3
"""Contract validator per provider.

Reads the rendered output of `scripts/render-provider.sh --provider <p>` in
<staging> and verifies it conforms to the provider's published schema (the
shape opencode / Codex / Claude Code expect at runtime). Sources of truth:

  - opencode JSON schema: https://opencode.ai/config.json
  - Codex agent TOML + hooks.json: developers.openai.com/codex
  - Claude (identity): rendered agents must equal source byte-for-byte

Each violation prints one line and increments the non-zero exit code count.

Usage:
  python3 _contract.py --provider <claude|opencode|codex> --staging <dir>
                      [--source <repo-root>]
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path


VALID_PROVIDERS = ("claude", "opencode", "codex")
VALID_TIERS = ("reasoning", "backend-exec", "frontend", "repetitive")

# Permission keys allowed by the opencode schema (PermissionConfig.tool keys).
OPENCODE_PERM_KEYS = {
    "read", "edit", "glob", "grep", "list", "bash", "task",
    "external_directory", "todowrite", "question", "webfetch",
    "websearch", "lsp", "doom_loop", "skill",
}
OPENCODE_PERM_ACTIONS = {"allow", "ask", "deny"}
OPENCODE_MODES = {"subagent", "primary", "all"}

CODEX_EFFORTS = {"low", "medium", "high", "xhigh", "max", "ultra"}


def fail(msg):
    sys.stderr.write(f"contract: FAIL — {msg}\n")
    return 1


def parse_frontmatter(text):
    """Minimal YAML frontmatter; flat key: value (no block scalars)."""
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    block = text[3:end].lstrip("\n")
    body = text[end + 4:].lstrip("\n")
    fm = {}
    i = 0
    lines = block.splitlines()
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
        # handle indented sub-keys (e.g. options: { effort: high }, permission: { read: allow })
        if not val and i + 1 < len(lines) and (lines[i + 1].startswith(" ") or lines[i + 1].startswith("\t")):
            sub = {}
            i += 1
            while i < len(lines) and (lines[i].startswith(" ") or lines[i].startswith("\t")):
                sub_line = lines[i].strip()
                m2 = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*)\s*:\s*(.*)$", sub_line)
                if m2:
                    sub[m2.group(1)] = m2.group(2).strip()
                i += 1
            fm[key] = sub
        else:
            fm[key] = val
            i += 1
    return fm, body


def load_toml_minimal(text):
    """Tiny TOML reader for our agent shape:
    name = "..."
    description = "..."
    model = "..."
    model_reasoning_effort = "..."
    developer_instructions = \"\"\" ... \"\"\"
    No other constructs needed.
    """
    out = {}
    # extract triple-quoted developer_instructions first
    instr_re = re.compile(r'developer_instructions\s*=\s*"""(.*?)"""', re.S)
    m = instr_re.search(text)
    if m:
        out["developer_instructions"] = m.group(1)
        text = text[:m.start()] + text[m.end():]

    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#") or s.startswith("["):
            continue
        m = re.match(r'^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*"(.*)"\s*$', s)
        if not m:
            continue
        out[m.group(1)] = m.group(2)
    return out


# ─── claude contract (identity) ──────────────────────────────────────
def check_claude(staging, source):
    errs = 0
    agents_src = sorted((Path(source) / "agents").glob("*.md"))
    cmds_src = sorted((Path(source) / "commands").glob("*.md"))
    out_a = Path(staging) / ".claude" / "agents" / "dev-team"
    out_c = Path(staging) / ".claude" / "commands" / "devteam"

    for src in agents_src:
        rendered = out_a / src.name
        if not rendered.exists():
            errs += fail(f"claude: agent {src.name} missing from staging")
            continue
        if rendered.read_text() != src.read_text():
            errs += fail(f"claude: agent {src.name} not byte-identical to source")
    for src in cmds_src:
        rendered = out_c / src.name
        if not rendered.exists():
            errs += fail(f"claude: command {src.name} missing from staging")
            continue
        if rendered.read_text() != src.read_text():
            errs += fail(f"claude: command {src.name} not byte-identical to source")
    return errs


# ─── opencode contract ───────────────────────────────────────────────
def check_opencode(staging, source):
    errs = 0
    agents_dir = Path(staging) / ".opencode" / "agents"
    agents = sorted(agents_dir.glob("*.md"))
    if not agents:
        return fail("opencode: no rendered agents found")

    # Source-of-truth agent names (for cross-check against commands.json)
    src_agents = {p.stem for p in (Path(source) / "agents").glob("*.md")}

    for f in agents:
        text = f.read_text()
        fm, body = parse_frontmatter(text)
        name = f.stem

        if not fm.get("description"):
            errs += fail(f"opencode/{name}.md: missing or empty 'description'")
        mode = fm.get("mode")
        if mode not in OPENCODE_MODES:
            errs += fail(f"opencode/{name}.md: 'mode' must be one of {sorted(OPENCODE_MODES)}, got '{mode}'")
        model = fm.get("model", "")
        if not re.match(r"^[a-z][a-z0-9_-]*/.+$", model):
            errs += fail(f"opencode/{name}.md: 'model' must be 'provider/model-id', got '{model}'")
        # options.effort optional; when present must be one of known efforts
        opts = fm.get("options") or {}
        if isinstance(opts, str):
            # parse "effort: high" if present inline
            m = re.match(r"effort:\s*([a-z]+)", opts)
            if m and m.group(1) not in {"default", "high", "low", "medium"}:
                errs += fail(f"opencode/{name}.md: unknown effort '{m.group(1)}'")
        elif isinstance(opts, dict):
            if "effort" in opts and opts["effort"] not in {"default", "high", "low", "medium"}:
                errs += fail(f"opencode/{name}.md: unknown effort '{opts['effort']}'")
        # permission object validation
        perm = fm.get("permission") or {}
        if isinstance(perm, dict):
            for k, v in perm.items():
                if k not in OPENCODE_PERM_KEYS:
                    errs += fail(f"opencode/{name}.md: unknown permission key '{k}'")
                if v not in OPENCODE_PERM_ACTIONS:
                    errs += fail(f"opencode/{name}.md: permission '{k}' has invalid action '{v}'")
        if not body.strip():
            errs += fail(f"opencode/{name}.md: empty body")
        if name not in src_agents:
            errs += fail(f"opencode/{name}.md: rendered agent name does not match any source agent")

    # commands snippet
    snippet_path = Path(staging) / ".opencode" / "commands.snippet.jsonc"
    if not snippet_path.exists():
        return errs + fail("opencode: commands.snippet.jsonc missing")
    snip_text = snippet_path.read_text()
    snip_clean = "\n".join(l for l in snip_text.splitlines() if not l.lstrip().startswith("//"))
    try:
        snip = json.loads(snip_clean)
    except json.JSONDecodeError as e:
        return errs + fail(f"opencode: commands snippet is not valid JSON: {e}")

    rendered_agent_names = {p.stem for p in agents}
    for key, entry in snip.items():
        if not re.match(r"^devteam:[a-z][a-z0-9-]*$", key):
            errs += fail(f"opencode: command key '{key}' does not match devteam:<name>")
        for req in ("description", "agent", "model", "template"):
            v = entry.get(req)
            if not v or (isinstance(v, str) and not v.strip()):
                errs += fail(f"opencode/{key}: missing or empty '{req}'")
        m_entry = entry.get("model", "")
        if not re.match(r"^[a-z][a-z0-9_-]*/.+$", m_entry):
            errs += fail(f"opencode/{key}: 'model' must be 'provider/model-id', got '{m_entry}'")
        agent_ref = entry.get("agent", "")
        if agent_ref and agent_ref not in rendered_agent_names:
            errs += fail(f"opencode/{key}: agent '{agent_ref}' not found among rendered agents")
    return errs


# ─── codex contract ──────────────────────────────────────────────────
def check_codex(staging, source):
    errs = 0
    agents_dir = Path(staging) / ".codex" / "agents"
    agents = sorted(agents_dir.glob("*.toml"))
    if not agents:
        return fail("codex: no rendered agents found")

    src_agents = {p.stem for p in (Path(source) / "agents").glob("*.md")}

    for f in agents:
        try:
            data = load_toml_minimal(f.read_text())
        except Exception as e:
            errs += fail(f"codex/{f.name}: TOML parse error: {e}")
            continue
        name = f.stem
        for req in ("name", "description", "model", "developer_instructions"):
            if not data.get(req):
                errs += fail(f"codex/{f.name}: missing or empty '{req}'")
        if data.get("name") and data.get("name") != name:
            errs += fail(f"codex/{f.name}: 'name' field '{data.get('name')}' does not match filename")
        if data.get("model") and "/" in data.get("model"):
            errs += fail(f"codex/{f.name}: 'model' must NOT carry provider prefix (got '{data.get('model')}')")
        effort = data.get("model_reasoning_effort")
        if effort and effort not in CODEX_EFFORTS:
            errs += fail(f"codex/{f.name}: 'model_reasoning_effort' '{effort}' not in {sorted(CODEX_EFFORTS)}")
        if name not in src_agents:
            errs += fail(f"codex/{f.name}: rendered agent name does not match any source agent")

    # prompts at .codex/prompts/devteam-<name>.md non-empty with description header
    prompts_dir = Path(staging) / ".codex" / "prompts"
    prompts = sorted(prompts_dir.glob("devteam-*.md"))
    if not prompts:
        errs += fail("codex: no rendered prompts found")
    for p in prompts:
        text = p.read_text()
        if not text.strip():
            errs += fail(f"codex/{p.name}: empty prompt body")
        if "<!-- description:" not in text:
            errs += fail(f"codex/{p.name}: missing '<!-- description: ... -->' header")
        # name should match devteam-<cmd-name>
        m = re.match(r"^devteam-(.+)\.md$", p.name)
        if not m:
            errs += fail(f"codex/{p.name}: filename must match 'devteam-<name>.md'")
    return errs


# ─── shared: tier × provider completeness ────────────────────────────
def check_tiers_completeness(source):
    """Every tier has a column for every provider in tiers.json."""
    errs = 0
    tiers = json.load(open(Path(source) / "scripts/lib/tiers.json"))
    tier_providers = set()
    for tier, entry in tiers.get("tiers", {}).items():
        if tier not in VALID_TIERS:
            errs += fail(f"tiers.json: unknown tier '{tier}' (allowed: {VALID_TIERS})")
            continue
        provs = {k for k in entry.keys() if not k.startswith("_")}
        tier_providers |= provs
    # require at least the 3 canonical providers present in every tier
    for tier in VALID_TIERS:
        entry = tiers.get("tiers", {}).get(tier, {})
        provs = {k for k in entry.keys() if not k.startswith("_")}
        missing = {"claude", "opencode", "codex"} - provs
        if missing:
            errs += fail(f"tiers.json: tier '{tier}' missing column(s) for {sorted(missing)}")
    return errs


# ─── shared: commands.json cross-ref ────────────────────────────────
def check_commands_json(source):
    """Each entry in scripts/lib/commands.json has a valid agent reference
    and a tier present in tiers.json."""
    errs = 0
    cmds = json.load(open(Path(source) / "scripts/lib/commands.json"))
    src_agents = {p.stem for p in (Path(source) / "agents").glob("*.md")}
    src_cmds = {p.stem for p in (Path(source) / "commands").glob("*.md")}
    for name, meta in cmds.get("commands", {}).items():
        if name not in src_cmds:
            errs += fail(f"commands.json: '{name}' has no matching commands/<name>.md source file")
        tier = meta.get("tier")
        if tier not in VALID_TIERS:
            errs += fail(f"commands.json/{name}: invalid tier '{tier}'")
        agent = meta.get("agent")
        if agent and agent not in src_agents:
            errs += fail(f"commands.json/{name}: agent '{agent}' not found in agents/")
    return errs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider", required=True, choices=VALID_PROVIDERS)
    ap.add_argument("--staging", required=True)
    ap.add_argument("--source", required=True)
    args = ap.parse_args()

    staging = Path(args.staging).resolve()
    source = Path(args.source).resolve()
    if not staging.is_dir():
        return fail(f"staging dir not found: {staging}")

    errs = 0
    # Shared contracts (always checked, regardless of provider)
    errs += check_tiers_completeness(source)
    errs += check_commands_json(source)

    # Per-provider contract
    if args.provider == "claude":
        errs += check_claude(staging, source)
    elif args.provider == "opencode":
        errs += check_opencode(staging, source)
    elif args.provider == "codex":
        errs += check_codex(staging, source)

    if errs:
        sys.stderr.write(f"\ncontract: {errs} violation(s) for provider '{args.provider}'\n")
        sys.exit(1)
    print(f"contract OK ✓  ({args.provider})  shared+tiers+commands+per-provider")


if __name__ == "__main__":
    main()