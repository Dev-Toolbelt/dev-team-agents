---
name: release-prep
description: Guides the pre-release process for the dev-team-agents repository. Runs consistency checks, validates README sync, determines the correct version bump, and creates the git tag. Use before any version tag is created.
---

# Release Prep

This skill guides the release process for this repository. It orchestrates existing scripts and enforces the rules defined in `CLAUDE.md § Versioning`.

Source of truth for versioning rules: `CLAUDE.md § Versioning`.

---

## When to Use

Invoke this skill before creating any `vX.Y.Z` git tag. Do not tag directly — always run through this checklist first.

---

## Step 0 — Present the Release Plan

Before running any checks, present a plan with:
- Proposed version bump (major / minor / patch) and rationale
- List of validation steps to execute
- Any known risks or items that may block the release

State explicitly: **"Awaiting your approval before proceeding."**

---

## Step 1 — Determine the Version Bump

Read the commits since the last tag:

```bash
git log $(git describe --tags --abbrev=0)..HEAD --oneline
```

Apply the rules from `CLAUDE.md § Versioning`:

| Change type | Bump |
|---|---|
| Agent behavior changes, removed skills, breaking install changes | **major** |
| New agents or new skills | **minor** |
| Fixes, clarifications, doc updates, script patches | **patch** |

If commits span multiple categories, apply the highest bump that applies.

Get the current version:

```bash
git describe --tags --abbrev=0
```

Calculate the next version and confirm with the user before proceeding.

---

## Step 2 — Orphan Skill Scan

```bash
bash scripts/orphan-skill-scan.sh
```

- **AUTO-FIXED** lines: verify the affected agent still reads correctly
- **ACTION REQUIRED** lines: resolve before continuing — do not tag with orphaned skills

---

## Step 3 — Agent Compliance Check

For each file in `agents/`, verify:

- [ ] Has `name`, `description`, `model`, `tools` in frontmatter
- [ ] Has `## Foundational Rule` section
- [ ] Has `## Immutability Warning` section
- [ ] Coding agents have `## Worktree Isolation` section
- [ ] File is ≤ 200 lines

Run a quick scan:

```bash
for f in agents/*.md; do
  lines=$(wc -l < "$f")
  echo "$lines $f"
done | sort -rn | head -10
```

Flag any agent over 200 lines for review.

---

## Step 4 — README Sync Check

The rule from `CLAUDE.md`: any change to `README.md` must be reflected in `README.pt-BR.md` in the same commit.

Check if they diverged since the last tag:

```bash
git diff $(git describe --tags --abbrev=0)..HEAD -- README.md README.pt-BR.md
```

If `README.md` changed but `README.pt-BR.md` did not (or vice versa), stop and sync them before continuing.

---

## Step 5 — Verify Package Exclusions

The install script strips `CLAUDE.md`, `scripts/install.sh`, and `scripts/orphan-skill-scan.sh` from the tarball. Confirm all three exclusions are still in place:

```bash
grep -n "CLAUDE.md\|orphan-skill-scan\|install.sh" scripts/install.sh
```

Expected: at least one line per file referencing exclusion from the extracted content.

---

## Step 6 — Validate User-Invocable Skills Table

For each entry in the `§ User-Invocable Skills` table in `CLAUDE.md`, verify the skill file exists:

```bash
# Example for each row in the table:
ls skills/skill-creator/SKILL.md
ls .claude/skills/agent-creator/SKILL.md
```

If any file is missing, stop — do not tag until the table and the filesystem are in sync.

---

## Step 7 — Auto-Docs and Language Check

Review commits since the last tag for:

1. **Observable behavior changes** (new agent/skill, renamed file, changed install flow, new script flag) → `README.md` and `README.pt-BR.md` must be updated. If not, update before tagging.
2. **Language** → scan new/modified `.md` files for non-English content (except intentional exceptions). Flag any violations.

```bash
git diff $(git describe --tags --abbrev=0)..HEAD --name-only | grep "\.md$"
```

---

## Step 9 — Create the Tag

After all checks pass:

```bash
# Stage and commit any last-minute fixes
git add -p   # review what's staged

# Create the annotated tag
git tag -a vX.Y.Z -m "Release vX.Y.Z"

# Push tag to remote
git push origin vX.Y.Z
```

Confirm the tag is visible:

```bash
git describe --tags
```

---

## Rollback Reference

If a tag was pushed incorrectly:

```bash
# Delete local tag
git tag -d vX.Y.Z

# Delete remote tag (confirm with user before running)
git push origin :refs/tags/vX.Y.Z
```

Do not run the remote delete without explicit user confirmation.
