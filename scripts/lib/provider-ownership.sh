#!/bin/bash
# provider-ownership.sh — which project paths a delegated provider installer may
# write. Sourced by install-opencode.sh and install-codex.sh; never executed.
#
# A target path that already exists is replaced only when it is framework-owned:
#   · listed in the installer's ledger (.dev-team-agents/.provider-owned-<provider>),
#     written after every standalone install, or
#   · listed in the --owned file a caller vouches for (`devteam bind` passes the
#     paths its manifest claims, after running its own preflight), or
#   · a symlink into the framework (the source tree or <project>/.dev-team-agents).
# Anything else belongs to the project. The installer refuses (exit 4) and names
# it, unless --adopt was passed — then the path is MOVED to a dated quarantine
# under .dev-team-agents/quarantine/ before being replaced. Nothing is deleted.

# `python3` resolves to a working Python 3.9+ on Windows Git Bash too (see the file).
_dta_py="$(dirname "${BASH_SOURCE[0]}")/python.sh"
[ -f "$_dta_py" ] && . "$_dta_py"

PO_CONFLICT_EXIT=4

# po_native_path <path>
# The form a native (non-MSYS) python3 can open. Under Git Bash a POSIX path such as
# /c/Users/x names nothing to it and its separators differ from the ones os.path compares
# with, so every path handed to python3 goes through here. Identity everywhere else.
po_native_path() {
  if command -v cygpath >/dev/null 2>&1; then
    cygpath -m "$1" 2>/dev/null || printf '%s\n' "$1"
  else
    printf '%s\n' "$1"
  fi
}

# po_require_inside <provider> <project_root> <project-relative path>...
# Refuses (exit 4) when any listed path resolves, through symlinks, outside the project:
# a committed `.codex -> ~/.codex` would otherwise receive the install in the user's
# global config. A path that does not exist yet is judged by its nearest existing parent.
po_require_inside() {
  local provider="$1" root="$2"
  shift 2
  if ! python3 - "$(po_native_path "$root")" "$@" <<'PY'

import os, sys
root = os.path.realpath(sys.argv[1])
bad = []
for rel in sys.argv[2:]:
    real = os.path.realpath(os.path.join(root, rel))
    if os.path.normcase(real) != os.path.normcase(root) and not os.path.normcase(real).startswith(os.path.normcase(root) + os.sep):
        bad.append((rel, real))
if bad:
    for rel, real in bad:
        sys.stderr.write("  {} resolves to {}, outside the project\n".format(rel, real))
    sys.exit(1)
PY
  then
    echo "install-${provider}: ERROR: a path the installer would write leaves the project (see above)." >&2
    echo "  Replace the symlink with a real directory, or remove it, and re-run." >&2
    exit "$PO_CONFLICT_EXIT"
  fi
}

# po_conflicts <project_root> <source_dir> <provider> <owned_file|""> <targets_file>
# Prints one conflicting project-relative path per line.
po_conflicts() {
  python3 - "$(po_native_path "$1")" "$(po_native_path "$2")" "$3" "$([[ -n "$4" ]] && po_native_path "$4" || true)" "$(po_native_path "$5")" <<'PY'
import os, sys
root, source, provider, owned_arg, targets_file = sys.argv[1:6]
owned = set()
for f in (os.path.join(root, ".dev-team-agents", ".provider-owned-" + provider), owned_arg):
    if f and os.path.isfile(f):
        owned.update(line.strip() for line in open(f) if line.strip())
fw_roots = [os.path.abspath(source), os.path.abspath(os.path.join(root, ".dev-team-agents"))]
real_roots = [os.path.realpath(r) for r in fw_roots]

def inside(path, roots):
    return any(path == r or path.startswith(r + os.sep) for r in roots)

for rel in (l.strip() for l in open(targets_file)):
    if not rel:
        continue
    path = os.path.join(root, rel)
    if not (os.path.lexists(path)):
        continue
    if rel in owned:
        continue
    if os.path.islink(path):
        target = os.readlink(path)
        lexical = os.path.normpath(os.path.join(os.path.dirname(path), target))
        if inside(lexical, fw_roots) or inside(os.path.realpath(path), real_roots):
            continue
    print(rel)
PY
}

# po_guard <project_root> <source_dir> <provider> <owned_file|""> <targets_file> <adopt 0|1> <dry_run 0|1>
# Refuses (exit 4) on a conflict, or quarantines the conflicting paths under --adopt.
po_guard() {
  local root="$1" source="$2" provider="$3" owned="$4" targets="$5" adopt="$6" dry_run="$7"
  local conflicts
  conflicts="$(po_conflicts "$root" "$source" "$provider" "$owned" "$targets")"
  [[ -z "$conflicts" ]] && return 0
  if [[ "$adopt" -ne 1 ]]; then
    echo "install-${provider}: ERROR: these paths already exist and were not created by dev-team-agents:" >&2
    sed 's/^/  /' <<< "$conflicts" >&2
    echo "  Move or rename them and re-run, or pass --adopt to move them into" >&2
    echo "  .dev-team-agents/quarantine/ and install over them." >&2
    exit "$PO_CONFLICT_EXIT"
  fi
  local qdir stamp
  stamp="$(date +%Y%m%d-%H%M%S)"
  qdir="$root/.dev-team-agents/quarantine/${provider}-${stamp}"
  local rel
  while IFS= read -r rel; do
    [[ -z "$rel" ]] && continue
    if [[ "$dry_run" -eq 1 ]]; then
      echo "  ~ would quarantine $rel"
      continue
    fi
    mkdir -p "$qdir/$(dirname "$rel")"
    mv "$root/$rel" "$qdir/$rel"
    echo "  ~ quarantined $rel -> ${qdir#"$root"/}/$rel"
  done <<< "$conflicts"
}

# po_record_ledger <project_root> <provider> <targets_file>
po_record_ledger() {
  local root="$1" provider="$2" targets="$3"
  mkdir -p "$root/.dev-team-agents"
  cp -f "$targets" "$root/.dev-team-agents/.provider-owned-$provider"
}

# po_link_skills <project_root> <source_dir> <link_path>
# Links the framework skills at <link_path>. The target is the project's own
# vendored copy (<project>/.dev-team-agents/skills) when one exists — a v2
# install or a vendored bind — and the source's skills/ otherwise, which is the
# store version under a v3 link or copy bind, where the project has no copy.
# A target inside the project is linked RELATIVELY, so a committed tree resolves
# on every clone; an absolute link into one machine's store is only ever written
# where bind keeps it out of git.
po_link_skills() {
  local root="$1" source="$2" link="$3" target
  if [[ -d "$root/.dev-team-agents/skills" ]]; then
    target="$root/.dev-team-agents/skills"
  else
    target="$source/skills"
  fi
  local rel
  rel="$(python3 - "$(po_native_path "$root")" "$(po_native_path "$target")" "$(po_native_path "$link")" <<'PY'
import os, sys
root, target, link = (os.path.abspath(p) for p in sys.argv[1:4])
if target == root or target.startswith(root + os.sep):
    print(os.path.relpath(target, os.path.dirname(link)).replace(os.sep, "/"))
PY
)"
  [[ -n "$rel" ]] && target="$rel"
  if [[ -L "$link" || -e "$link" ]]; then rm -rf "$link"; fi
  mkdir -p "$(dirname "$link")"
  # Git Bash's `ln -s` silently COPIES unless native symlinks are requested, and a copy
  # recorded as a link goes stale on the next update. Native or nothing.
  case "$(uname -s 2>/dev/null)" in
    MINGW*|MSYS*) export MSYS=winsymlinks:nativestrict ;;
  esac
  if ! ln -s "$target" "$link" || [[ ! -L "$link" ]]; then
    echo "install: ERROR: could not create the symlink ${link#"$root"/} -> $target." >&2
    echo "  On Windows, enable Developer Mode (or run as administrator) so Git Bash can create symlinks." >&2
    return 1
  fi
  echo "  + symlinked $target -> ${link#"$root"/}"
}

# po_rerender_providers
# Re-runs the opencode / Codex installers for the provider trees in the current directory
# (a project root with an installed .dev-team-agents/). Shared by update.sh and rollback.sh.
# Slim Claude installs don't bundle the cross-CLI plumbing (stripped by
# scripts/lib/strip-tarball.sh), so the installer would abort with exit 3: check for the
# plumbing first and degrade to guidance. A provider that fails is reported and the next one
# still runs; returns non-zero when any failed, so the caller's exit reflects it.
po_rerender_providers() {
  local failed=0
  if [ -f ".opencode/opencode.json" ] || [ -d ".opencode" ]; then
    if [ -f ".dev-team-agents/scripts/render-provider.sh" ] && [ -f ".dev-team-agents/opencode/plugin/dev-team-agents.ts" ]; then
      echo "→ opencode config detected, re-running install-opencode.sh..."
      # --adopt: an install from before the ownership ledger has no record of the
      # files its own earlier runs wrote. They are moved to .dev-team-agents/quarantine/
      # once, never deleted, and the ledger claims the fresh copies from then on.
      if ! bash .dev-team-agents/scripts/install-opencode.sh --adopt; then
        echo "⚠ install-opencode.sh failed; opencode support was NOT refreshed." >&2
        failed=1
      fi
    else
      echo "⚠ opencode config detected, but this is a slim install (cross-CLI plumbing not bundled)." >&2
      echo "  Skipping automatic opencode re-render. To refresh opencode support, run:" >&2
      echo "    bash <(curl -sSL https://raw.githubusercontent.com/Dev-Toolbelt/dev-team-agents/main/scripts/install-provider.sh) opencode" >&2
    fi
  fi
  if [ -f ".codex/hooks.json" ] || [ -d ".codex" ]; then
    if [ -f ".dev-team-agents/scripts/render-provider.sh" ] && [ -f ".dev-team-agents/agents/product-analyst.md" ]; then
      echo "→ Codex config detected, re-running install-codex.sh..."
      if ! bash .dev-team-agents/scripts/install-codex.sh --adopt; then
        echo "⚠ install-codex.sh failed; Codex support was NOT refreshed." >&2
        failed=1
      fi
    else
      echo "⚠ Codex config detected, but this is a slim install (cross-CLI plumbing not bundled)." >&2
      echo "  Skipping automatic Codex re-render. To refresh Codex support, run:" >&2
      echo "    bash <(curl -sSL https://raw.githubusercontent.com/Dev-Toolbelt/dev-team-agents/main/scripts/install-provider.sh) codex" >&2
    fi
  fi
  return "$failed"
}
