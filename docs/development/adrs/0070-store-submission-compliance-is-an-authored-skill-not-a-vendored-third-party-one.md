# ADR-0070: Store submission compliance is an authored skill, not a vendored third-party one

**Date:** 2026-11-25  
**Status:** Accepted  
**Deciders:** dev-team-agents maintainers  
**Applies to:** `skills/mobile/store-submission-compliance/**`, `agents/qa-specialist.md`, `agents/mobile-developer.md`, `agents/ui-ux-designer.md`, `agents/product-analyst.md`, `skills/shared/reviewer-base/SKILL.md`, `skills/shared/release-qa/SKILL.md`, `commands/review.md`, `commands/mobile.md`, `skills/shared/spawn-classifier/SKILL.md`, `skills/mobile/ios/SKILL.md`, `skills/mobile/android/SKILL.md`, `skills/mobile/flutter/SKILL.md`, `skills/mobile/react-native/SKILL.md`, `skills/third-party/sources.json`  
**Relates to:** ADR-0047

## Context

Mobile apps built with the framework are rejected by App Store and Google Play review for a small set of repeat causes: no demo account, a staging backend, a missing purpose string or privacy manifest, no in-app account deletion, digital goods sold outside the store's billing, a Data safety form that does not match the SDKs, a target API below the floor. Nothing in the framework checked for them before submission. The mobile skills (`ios`, `android`, `flutter`, `react-native`) each carried a partial publication checklist, and the four lists had drifted apart.

`mjmirza/app-store-compliance` (v2.5.2) covers this ground well. Its scanner, run on 2026-11-25 against a synthetic iOS and Android project with nine planted problems, reported all nine, and the repository is honest about what a static scan cannot prove. The natural route was ADR-0047: vendor it under `skills/third-party/`.

The repository is licensed under the OpenRoots Agent License 2.3, one licence for code, docs, data and the hook. It is free below USD 20M annual revenue and charges a royalty above it, and it excludes AI training from the grant. Vendoring it would ship those terms to every project that installs dev-team-agents, including companies above the threshold that never chose that dependency.

## Decision

1. Store-submission compliance lives in one authored skill, `skills/mobile/store-submission-compliance/`, written in our own words from Apple's and Google's primary pages. No file, text or data from `mjmirza/app-store-compliance` is copied in. Facts such as guideline numbers, API levels and dates are not owned by anyone; the third-party wording is.
2. `mjmirza/app-store-compliance` is not added to `skills/third-party/sources.json`. A later proposal to vendor it must first show its licence changed to one compatible with redistribution.
3. The skill splits the audit in two halves: signals an agent can find in code and config, and checks only a person can prove on the release build (demo account, live backend, review notes, screenshots, deletion on a device, privacy labels against runtime, reachable purchase). The verdict is `CLEAR`, `BLOCKED` or `NOT CHECKED`, and a critical finding never yields `CLEAR`.
4. Every volatile fact (API levels, SDK minimums, deadlines) carries its source URL and the date it was verified. A fact older than 60 days is re-read at the source before it can block a release.
5. `qa-specialist` loads the skill when the changeset or release targets an iOS or Android app, and a `BLOCKED` verdict becomes a `[BLOCKER]`. `/devteam:release-qa` reports the verdict for each app target. What other roles do before the gate is Decision 6.
6. The rules apply before the gate too. The skill's § Build It Right lists what must ship together with a feature in a store-sensitive area (deletion with sign-up, purpose strings, store billing, consent before third-party AI, …). `product-analyst` records those items as requirements, `ui-ux-designer` designs the reviewed screens to them, and `mobile-developer` loads the skill before writing code. Every reviewer runs the code half on a diff that touches such an area (`reviewer-base`), with `CRITICAL` mapped to `BLOCKING` and `HIGH` to `SUGGESTION` under the `review-result` vocabulary (§ In a Code Review), so a rejection cause is stopped at the pull request rather than at the store. The per-stack mobile skills point at it instead of carrying their own store checklist.

## Consequences

### Positive
- One home for store rules; the four drifting checklists become pointers.
- No licence obligation reaches installed projects.
- The QA gate catches the repeat rejection causes before upload.

### Negative
- The rules are maintained here. Store policy moves several times a year, so the dated facts go stale without a periodic re-check.
- There is no executable scanner; the agent reads the project against the skill's signal tables.

### Neutral
- A team that wants the third-party scanner can still install it on its own under its licence; the skill does not depend on it.

## Alternatives Considered

| Alternative | Why rejected |
|-------------|-------------|
| Vendor the repository under `skills/third-party/` (ADR-0047) | Redistributes ORA 2.3 terms, including a revenue royalty, to every installed project |
| Run the third-party scanner when a project has it installed | Couples the QA gate to an external licence and an unpinned script; may be revisited as an opt-in |
| Keep extending the per-stack mobile checklists | They already drifted; four copies of one rule set contradict the canonical-home rule |
