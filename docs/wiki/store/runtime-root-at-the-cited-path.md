# A pointer that resolves "the framework" resolves none of its paths

**Origin:** a user asked why `.dev-team-agents/core` existed beside the `.claude/` links | 2026-09-29
**Tags:** core, pointer, scripts, templates, runtime root, project-relative, new-adr.sh, reuse-lint, design-token-lint, exit 0, silent gate

> Put the link at the path the text names. A pointer one directory up is a different path, and a test that walks through the pointer proves nothing about the text.

---

## What it is

v3 gave each bound project `.dev-team-agents/core` → the resolved store version, documented as what
made the framework's project-relative references work. The references were never rewritten: they say
`.dev-team-agents/scripts/new-adr.sh`, and the pointer produced `.dev-team-agents/core/scripts/…`.
138 references across 39 files resolved nowhere.

## How it works

- The test written for it checked `core/scripts` and `core/templates` existed — a path through the
  pointer, which is exactly what the text does not use, so it passed while every reference was broken.
- Two Stop sub-scripts (`03c-reuse-lint.sh`, `03d-design-token-lint.sh`) look for
  `$REPO_ROOT/.dev-team-agents/scripts/<lint>.sh` and `exit 0` when it is absent — a reasonable
  fallback that turned the missing path into two gates silently off in every v3 project.
- The fix links `scripts/` and `templates/` at the cited paths; nothing shipped reads agents, commands
  or skills through `.dev-team-agents/`, so nothing else needs a link.

## Gotchas

- Once `.dev-team-agents/scripts` resolves, **every v2 tool resolves too** — `update.sh` would have
  re-vendored a v2 tree over the bind, and a health-check `chmod +x` would write through the link into
  the immutable store. They refuse in a bound project (`scripts/lib/bound-project-guard.sh`).
- `ensure-claude-framework.sh` used `-e core` to mean "v3, do not mirror". Without that, its `cp` into
  `.dev-team-agents/scripts/` would write through the new link into the store; it now keys on
  `project.json` or a linked `scripts`.
- The guard test binds this repository's **real** tree (`tests/test_runtime_links.py`); the minimal
  fixture tree only proves the fixture's own paths exist.
