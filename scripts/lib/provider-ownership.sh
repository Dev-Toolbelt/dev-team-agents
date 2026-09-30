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

PO_CONFLICT_EXIT=4

# po_conflicts <project_root> <source_dir> <provider> <owned_file|""> <targets_file>
# Prints one conflicting project-relative path per line.
po_conflicts() {
  python3 - "$@" <<'PY'
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
  target="$(python3 - "$root" "$target" "$link" <<'PY'
import os, sys
root, target, link = (os.path.abspath(p) for p in sys.argv[1:4])
if target == root or target.startswith(root + os.sep):
    print(os.path.relpath(target, os.path.dirname(link)))
else:
    print(target)
PY
)"
  if [[ -L "$link" || -e "$link" ]]; then rm -rf "$link"; fi
  mkdir -p "$(dirname "$link")"
  ln -s "$target" "$link"
  echo "  + symlinked $target -> ${link#"$root"/}"
}
