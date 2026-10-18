---
description: Scan docs/ for undocumented conventions and catalog them via /devteam:rule
argument-hint: "[--all] [path-under-docs]"
model: haiku
---

Load `skills/shared/reuse-guidelines/SKILL.md` before doing anything — it owns the registry format, the three `type`s, and the classify → propose → confirm → append routine this command drives per candidate.

Load `skills/shared/interaction-patterns/SKILL.md` and use `AskUserQuestion` for every question with a finite set of answers — never a plain-text prompt.

This command is the canonical scan-and-backfill flow. `setup-health-check`'s Category 11 delegates here instead of duplicating the grep — do not fork this logic back into the health-check skill.

---

## Step 1 — Scope

`$ARGUMENTS`, if given, is a path under `docs/` to scan (e.g. `docs/wiki/`). If empty, scan the full default set: `docs/development/code-standards.md`, `docs/design/design-system.md`, `docs/wiki/**`, `docs/project.md`, `docs/development/adrs/**`.

Skip any path that does not exist — do not error on a project that hasn't populated all of them.

---

## Step 2 — Confirm mode

If `$ARGUMENTS` already contains `--all` or `--yes`, skip this step and use all-mode. Otherwise, before scanning, ask the user with `AskUserQuestion`:

- **Apply all automatically (Recommended)** — every surviving candidate is classified and appended without a per-row confirmation
- **Review each one** — one `AskUserQuestion` per candidate, so the user can accept some and decline others

Use the chosen mode for Step 5 exactly as if the corresponding flag had been passed.

---

## Step 3 — Find candidates

Grep the scoped files for mandatory-reuse and standardization language (PT + EN), the same signal vocabulary as `skills/shared/docs-sync/references/update-triggers.md` § Convention / Standardization Signals:

```bash
grep -rniE 'sempre us[ea]|componente (canônico|padrão|central)|padrão obrigatório|nunca (crie|use)|a partir de agora .* sempre|use somente|apenas .* deve|always use|canonical component|mandatory component|must (always )?use|never (create|use) a new|from now on .* always|only use' \
  <scoped paths>
```

For each match, read the surrounding paragraph (not just the matched line) to recover the full rule statement — a grep hit is a location, not the rule itself.

---

## Step 4 — Skip already-registered rules

If `docs/development/reuse-guidelines.md` exists, read it first. Drop any candidate whose `canonical_ref` or subject already has a row — do not propose a duplicate. When a candidate looks like a near-match (same subject, different wording), ask the user with `AskUserQuestion` whether it's the same rule or a distinct one, rather than guessing.

---

## Step 5 — Classify, draft, confirm, append — per candidate

In all-mode (from `--all`/`--yes` or the Step 2 quiz), skip per-candidate confirmation entirely: for each surviving candidate, run the classify/resolve/draft steps of `commands/rule.md` Steps 2–6 (skip its confirm step) and append the row directly. Treat the recovered paragraph from Step 3 as that routine's `$ARGUMENTS`, stripping any flag before passing it through.

In review-mode (the default when the user picks it in Step 2), for each surviving candidate run **the exact routine in `commands/rule.md` Steps 2–6** (classify `type`, resolve `canonical_ref`, draft `detection`, confirm with `AskUserQuestion`, append on confirmation). Treat the recovered paragraph from Step 3 as that routine's `$ARGUMENTS`. Never batch-confirm multiple candidates behind a single question — one `AskUserQuestion` per row, so a user can accept some and decline others.

When a row is confirmed and appended, adapt the source document in place: replace the rule's sentence/paragraph with a one-line reference (`See docs/development/reuse-guidelines.md § <name>`), keeping the same heading and anchor — never delete the heading or the surrounding section. This mirrors the No-Destruction discipline in `setup-health-check/SKILL.md`.

---

## Step 6 — Report

Summarize what happened: rows added, rows declined (omitted in all-mode, since nothing is declined there), candidates skipped as already-registered. If no candidates were found, say so plainly — do not fabricate a finding to justify the scan.

---

## $ARGUMENTS

Optional — `--all` (or `--yes`) to append every surviving candidate without a per-row confirmation, and/or a path under `docs/` to scope the scan.
