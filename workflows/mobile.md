# Workflow — Mobile Development

Use this workflow for implementing mobile features across React Native, Expo, Flutter, and native iOS/Android projects.

> **Plan Mode**: every agent step below will present a structured plan for your approval before executing anything. You review, adjust if needed, and approve. Nothing runs until you say so.

> **Command shortcut**: `/devteam:mobile` runs this workflow.

---

## Step 0: Load Context

Load `skills/shared/current-context/SKILL.md` to detect the active branch, open worktree session (`.claude/.worktree-session`), and scope. If already loaded by a command wrapper, this step is a no-op.

---

## Step 1: Scope & Design (parallel when visual decisions are needed)

Send both prompts in a single message to run simultaneously if the feature involves UI decisions. Skip `ui-ux-designer` for purely logic-level changes.

| Step | Agent | Par. |
|------|-------|------|
| 1a | software-architect | A |
| 1b | ui-ux-designer (conditional) | A |

```
Prompt: "As the software-architect, define the approach for this mobile feature: [description].
         Identify platform-specific concerns (iOS vs Android), state management approach, and
         any navigation or performance considerations."

Prompt (if UX decisions needed): "As the ui-ux-designer, define the UX flow and component
         specs for this mobile feature: [description]. Apply platform guidelines
         (HIG for iOS, Material Design for Android)."
```

▶ CHECKPOINT — await: architecture decision + design specs (if applicable)

---

## Step 2: Implementation (mobile-developer)

```
Prompt: "As the mobile-developer, implement the mobile feature: [description].
         Follow the approach from the software-architect.
         [Include design specs from ui-ux-designer if Step 1b was run.]"
```

The `mobile-developer` will:
- Ask once about worktree isolation before editing any file
- Present a plan (files to create/modify, platform-specific adaptations, navigation changes)
- Wait for approval before executing
- Handle platform differences inline (iOS vs Android behaviors, permissions)

**Implementation rules:**
- No visual changes without design specs (Step 1b must have run)
- Handle permissions for both platforms (camera, location, push notifications)
- Respect platform UI conventions — do not port iOS patterns blindly to Android and vice versa

---

## Step 3: Testing

```
Prompt: "As the mobile-developer, write E2E tests for the implemented feature using
         [Detox / Maestro / Appium — specify the testing tool your project uses].
         Cover the happy path and the main error states."
```

The `mobile-developer` will:
- Detect the testing framework from the project (`package.json`, `maestro/`, `.detoxrc.*`)
- Present a plan (test file location, scenarios to cover, device targets)
- Wait for approval before writing test files

If no E2E testing framework is configured, the agent will recommend one based on the project stack and ask whether to set it up.

---

## Step 4: Code Review (code-reviewer)

```
Prompt: "As the code-reviewer, review the mobile changes for: platform consistency,
         performance (unnecessary re-renders, bridge calls), accessibility, and
         security (permissions, deep links, local storage)."
```

The `code-reviewer` presents findings as a structured report with severity levels. Any [BLOCKING] finding requires a remediation plan and approval before continuing.

---

## Step 5: Commit & PR

After all findings are resolved and tests pass:

```
Prompt: "/devteam:commit"
```

Then optionally:

```
Prompt: "Please open a PR for these mobile changes."
```

---

## Step 6: Documentation (technical-writer — optional)

If the feature changes public-facing behavior or introduces a new screen/flow:

```
Prompt: "As the technical-writer, update the relevant docs for this mobile feature:
         [description]. Include any new platform permissions in the README."
```

---

## Workflow Closure

☐ Architecture and design decisions documented
☐ Feature implemented and platform-tested (iOS + Android)
☐ E2E tests written and passing
☐ Code review passed (no [BLOCKING] findings)
☐ Permissions declared in both platform manifests
☐ Commit and PR created
☐ Session summary written

**Related workflows:**
- Need backend API for this feature? → `/devteam:backend` + `workflows/fullstack.md`
- Bug in existing mobile feature? → `/devteam:fix`
- Platform security concern? → `/devteam:security`

---

## Recovery Paths

| Failure point | Recovery |
|---------------|----------|
| Platform-specific crash during testing | Spawn `mobile-developer` with crash log; use `--device ios` or `--device android` flag in tests |
| Design spec conflicts with platform guidelines | Re-run `ui-ux-designer` with explicit platform constraint; present options to user |
| E2E tests flaky on CI | Spawn `mobile-developer` to add retry logic or fix timing issues |
| User aborts mid-workflow | Workflow state is in `.claude/user-data/session-summary.md` — resume by reading the last entry |
