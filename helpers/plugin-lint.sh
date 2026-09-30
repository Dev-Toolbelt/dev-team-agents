#!/usr/bin/env bash
# Dev-only: validate plugins/*/plugin.json against plugins/_schema/plugin.schema.json rules.
# Usage: helpers/plugin-lint.sh [--verbose] [<plugins-dir>]
set -euo pipefail

VERBOSE=0
ROOT=""
for a in "$@"; do
  case "$a" in
    --verbose) VERBOSE=1 ;;
    --quiet) ;;
    *) ROOT="$a" ;;
  esac
done
[ -n "$ROOT" ] || ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/plugins"
[ -d "$ROOT" ] || { echo "plugin-lint: plugins dir not found: $ROOT"; exit 1; }

exec python3 - "$ROOT" "$VERBOSE" <<'PY'
import json, os, re, subprocess, sys

root, verbose = sys.argv[1], sys.argv[2] == "1"
errors = []
names = {}
TYPES = {"boolean", "string", "integer", "string_list", "enum"}
RUNTIMES = {"bash", "python3"}
OUTPUTS = {"config", "json", "log"}
SCRIPT_RE = re.compile(r"^(?!/)(?!.*(^|/)\.\.(/|$))[A-Za-z0-9._/-]+$")


def is_int(v):
    return isinstance(v, int) and not isinstance(v, bool)


def check(plugin, d):
    def err(msg):
        errors.append(f"plugin-lint: {plugin}: {msg}")

    if not isinstance(d, dict):
        return err("manifest must be a JSON object")
    allowed = {"schema", "name", "title", "description", "homepage", "requires", "config", "actions", "status", "hooks"}
    for k in d:
        if k not in allowed:
            err(f"unknown top-level key '{k}'")
    for k in ("schema", "name", "title", "description"):
        if k not in d:
            err(f"missing required key '{k}'")
    if "schema" in d and not (is_int(d["schema"]) and d["schema"] == 1):
        err("schema must be 1")
    name = d.get("name")
    if "name" in d:
        if not isinstance(name, str) or not re.fullmatch(r"[a-z][a-z0-9-]{1,31}", name):
            err("name must match ^[a-z][a-z0-9-]{1,31}$")
        else:
            if name != plugin:
                err(f"name '{name}' does not match directory '{plugin}'")
            if name in names:
                err(f"duplicate name '{name}' (also in {names[name]})")
            names.setdefault(name, plugin)
    for k, mx in (("title", 40), ("description", 200)):
        if k in d and not (isinstance(d[k], str) and 1 <= len(d[k]) <= mx):
            err(f"{k} must be a string of 1-{mx} chars")
    if "homepage" in d and not (isinstance(d["homepage"], str) and d["homepage"].startswith("https://")):
        err("homepage must start with https://")

    scripts = []

    def script(path, runtime, where):
        if not isinstance(path, str) or not SCRIPT_RE.match(path):
            return err(f"{where}: script path must be relative, without '..': {path!r}")
        if runtime is not None and runtime not in RUNTIMES:
            err(f"{where}: runtime must be one of {sorted(RUNTIMES)}")
        scripts.append((path, runtime, where))

    reqs = d.get("requires", [])
    if not isinstance(reqs, list):
        err("requires must be an array")
        reqs = []
    for i, r in enumerate(reqs):
        w = f"requires[{i}]"
        if not isinstance(r, dict) or set(r) - {"binary", "install_hint"}:
            err(f"{w}: must be an object with binary, install_hint only")
            continue
        if not (isinstance(r.get("binary"), str) and re.fullmatch(r"[A-Za-z0-9._-]+", r["binary"])):
            err(f"{w}: invalid binary")
        if not (isinstance(r.get("install_hint"), str) and r["install_hint"]):
            err(f"{w}: install_hint required")

    cfg = d.get("config", [])
    if not isinstance(cfg, list):
        err("config must be an array")
        cfg = []
    keys = set()
    cfg_allowed = {"key", "type", "label", "help", "required", "default", "placeholder", "min", "max", "options"}
    for i, c in enumerate(cfg):
        w = f"config[{i}]"
        if not isinstance(c, dict):
            err(f"{w}: must be an object")
            continue
        for k in c:
            if k not in cfg_allowed:
                err(f"{w}: unknown key '{k}'")
        for k in ("key", "type", "label", "help", "default"):
            if k not in c:
                err(f"{w}: missing required key '{k}'")
        key = c.get("key")
        if "key" in c:
            if not (isinstance(key, str) and re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,63}", key)):
                err(f"{w}: invalid key {key!r}")
            elif key in keys:
                err(f"{w}: duplicate config key '{key}'")
            else:
                keys.add(key)
        for k in ("label", "help"):
            if k in c and not (isinstance(c[k], str) and c[k]):
                err(f"{w}: {k} must be a non-empty string")
        if "required" in c and not isinstance(c["required"], bool):
            err(f"{w}: required must be boolean")
        if "placeholder" in c and not isinstance(c["placeholder"], str):
            err(f"{w}: placeholder must be a string")
        for k in ("min", "max"):
            if k in c and not is_int(c[k]):
                err(f"{w}: {k} must be an integer")
        t = c.get("type")
        if "type" in c and t not in TYPES:
            err(f"{w}: type must be one of {sorted(TYPES)}")
            continue
        opts = c.get("options")
        if t == "enum":
            if not isinstance(opts, list) or not opts:
                err(f"{w}: enum requires non-empty options")
                opts = None
        elif "options" in c:
            err(f"{w}: options only allowed for type enum")
            opts = None
        values = []
        if opts:
            for j, o in enumerate(opts):
                if not (isinstance(o, dict) and set(o) == {"value", "label"}
                        and isinstance(o["value"], str) and isinstance(o["label"], str)):
                    err(f"{w}: options[{j}] must be {{value, label}} strings")
                else:
                    values.append(o["value"])
        if "default" in c:
            v = c["default"]
            if t == "string_list":
                ok = isinstance(v, list) and all(isinstance(x, str) for x in v)
            elif t == "boolean":
                ok = isinstance(v, bool)
            elif t == "integer":
                ok = is_int(v)
                if ok and is_int(c.get("min")) and v < c["min"]:
                    ok = False
                if ok and is_int(c.get("max")) and v > c["max"]:
                    ok = False
            elif t == "enum":
                ok = isinstance(v, str) and v in values
            elif t == "string":
                ok = isinstance(v, str)
            else:
                ok = True
            if not ok:
                err(f"{w}: default {v!r} does not match type '{t}'")

    acts = d.get("actions", [])
    if not isinstance(acts, list):
        err("actions must be an array")
        acts = []
    ids = set()
    act_allowed = {"id", "label", "help", "runtime", "script", "output", "requires_enabled", "timeout_seconds"}
    for i, a in enumerate(acts):
        w = f"actions[{i}]"
        if not isinstance(a, dict):
            err(f"{w}: must be an object")
            continue
        for k in a:
            if k not in act_allowed:
                err(f"{w}: unknown key '{k}'")
        for k in ("id", "label", "help", "runtime", "script", "output"):
            if k not in a:
                err(f"{w}: missing required key '{k}'")
        aid = a.get("id")
        if "id" in a:
            if not (isinstance(aid, str) and re.fullmatch(r"[a-z][a-z0-9-]{0,31}", aid)):
                err(f"{w}: invalid id {aid!r}")
            elif aid in ids:
                err(f"{w}: duplicate action id '{aid}'")
            else:
                ids.add(aid)
        if "output" in a and a["output"] not in OUTPUTS:
            err(f"{w}: output must be one of {sorted(OUTPUTS)}")
        if "requires_enabled" in a and not isinstance(a["requires_enabled"], bool):
            err(f"{w}: requires_enabled must be boolean")
        ts = a.get("timeout_seconds")
        if "timeout_seconds" in a and not (is_int(ts) and 1 <= ts <= 3600):
            err(f"{w}: timeout_seconds must be an integer 1-3600")
        if "script" in a:
            script(a["script"], a.get("runtime"), w)
        elif "runtime" in a and a["runtime"] not in RUNTIMES:
            err(f"{w}: runtime must be one of {sorted(RUNTIMES)}")

    st = d.get("status")
    if st is not None:
        if not isinstance(st, dict) or set(st) - {"runtime", "script", "timeout_seconds"}:
            err("status: must be an object with runtime, script, timeout_seconds only")
        else:
            for k in ("runtime", "script"):
                if k not in st:
                    err(f"status: missing required key '{k}'")
            ts = st.get("timeout_seconds")
            if "timeout_seconds" in st and not (is_int(ts) and 1 <= ts <= 30):
                err("status: timeout_seconds must be an integer 1-30")
            if "script" in st:
                script(st["script"], st.get("runtime"), "status")

    hk = d.get("hooks")
    if hk is not None:
        if not isinstance(hk, dict) or set(hk) - {"pre_tool_use", "stop"}:
            err("hooks: must be an object with pre_tool_use, stop only")
        else:
            for k, v in hk.items():
                script(v, "bash", f"hooks.{k}")

    pdir = os.path.join(root, plugin)
    real_root = os.path.realpath(pdir)
    for path, runtime, where in scripts:
        full = os.path.realpath(os.path.join(pdir, path))
        if not (full == real_root or full.startswith(real_root + os.sep)):
            err(f"{where}: script escapes plugin dir: {path}")
            continue
        if not os.path.isfile(full):
            err(f"{where}: script not found: {path}")
            continue
        if runtime == "python3" or (runtime is None and path.endswith(".py")):
            r = subprocess.run([sys.executable, "-c",
                                "import sys;compile(open(sys.argv[1]).read(),sys.argv[1],'exec')", full],
                               capture_output=True, text=True)
            if r.returncode:
                err(f"{where}: python syntax error in {path}: {r.stderr.strip().splitlines()[-1] if r.stderr.strip() else ''}")
        else:
            r = subprocess.run(["bash", "-n", full], capture_output=True, text=True)
            if r.returncode:
                err(f"{where}: bash syntax error in {path}: {r.stderr.strip().splitlines()[0] if r.stderr.strip() else ''}")
        if runtime != "python3" and not os.access(full, os.X_OK):
            print(f"plugin-lint: {plugin}: warning: {path} is not executable (CLI invokes via interpreter)", file=sys.stderr)


count = 0
for entry in sorted(os.listdir(root)):
    if entry == "_schema" or entry.startswith("."):
        continue
    pdir = os.path.join(root, entry)
    if not os.path.isdir(pdir):
        continue
    mf = os.path.join(pdir, "plugin.json")
    if not os.path.isfile(mf):
        errors.append(f"plugin-lint: {entry}: missing plugin.json")
        continue
    count += 1
    try:
        with open(mf) as f:
            data = json.load(f)
    except (ValueError, OSError) as e:
        errors.append(f"plugin-lint: {entry}: invalid JSON: {e}")
        continue
    check(entry, data)

for e in errors:
    print(e)
if errors:
    sys.exit(1)
if verbose:
    print(f"plugin-lint: {count} plugin(s) OK")
PY
