# Agents and Skills — v2 Carry-Over

**Axis:** `agent-*` + `skill-*` · **Verified against:** `HEAD` = `7f85ed7`

This axis had the **lowest** v1 mortality (41 of 79 survived). `agents/` and `skills/` changed least during the provider port, so most content-level findings reproduce verbatim.

A recurring theme runs through the HIGH and MEDIUM-HIGH entries: `CLAUDE.md` mandates that agents be **stack-agnostic** ("no hardcoded framework, language, or tool references in agent core behavior"), and the detection-table → skill-load pattern exists to honor that. Several agents state the pattern and then violate it a few lines below.

---

## HIGH

### `security-specialist` hardcodes per-ecosystem SAST and dependency-audit commands in the body

- **Fingerprint:** `agent-security-specialist-body-130-153-hardcodes-per-language-sast-and-dep-audit-commands-bandit-composer-npm-trivy-stack-prescriptive`
- **Evidence:** `agents/security-specialist.md:132-158` — "## Tooling & Dependency Audit … `bandit -r . -ll  # Python`", "`npm audit --audit-level=high`", "`composer audit`", "`pip-audit`", "`trivy image myapp:latest`", "`snyk test`".
- **Problem:** An ungated, ecosystem-specific command list in the body of a stack-agnostic agent. It belongs in a skill behind detection.
- **Why it matters at HEAD:** The block is intact and still ungated; the same file also eager-loads 8 security skills (~996 lines) at `:25-32`. *(Re-measured: now lines 132-158, was 130-153.)*

### `backend-developer` "Integration Awareness" re-states provider rules inline for 8 integrations

- **Fingerprint:** `agent-backend-developer-integration-awareness-section-duplicates-provider-specific-critical-rules-inline-for-7-integrations-systemic-stack-prescriptive-body`
- **Evidence:** `agents/backend-developer.md:86-180` — "## Integration Awareness … detect them and load the corresponding skill", with sub-blocks Supabase (`:96`), GoTrue (`:108`), JWT (`:118`), Kong (`:128`), Realtime (`:138`), Jira (`:149`), SonarQube (`:159`), Async Jobs (`:173`). Each has a `Load: skills/…/SKILL.md` line **followed by** an inline "Critical rules:" list.
- **Problem:** The design is lazy (detect → load skill) but the critical rules are copied out of each skill into the agent body, so ~95 lines of vendor-specific text load unconditionally even when the project uses none of the eight platforms. The skill stops being the single source of truth.
- **Why it matters at HEAD:** The count grew from 7 to 8 sub-blocks. Extracting this section alone would take `backend-developer` from 265 lines to ~170 — under the cap.
- **Merged from:** 2 v1 fingerprints (`agent-*` + `token-*`).

### `frontend-test-specialist` embeds React and Vue hook-test recipes with code samples

- **Fingerprint:** `agent-frontend-test-specialist-107-122-hardcodes-react-renderhook-testing-library-and-vue-withsetup-recipes-in-body-stack-agnostic`
- **Evidence:** `agents/frontend-test-specialist.md:113` — "**React** — use `renderHook` from `@testing-library/react`:"; `:116` — `const { result } = renderHook(() => useCartTotal(mockItems));`; `:123` — "**Vue** — call composables directly inside a thin `withSetup` wrapper:".
- **Problem:** Framework-specific recipes in the agent body with no gate. A project uses one framework, so roughly half the block is dead weight on every spawn.
- **Why it matters at HEAD:** Both recipes intact and ungated. *(Re-measured: now lines 109-136.)*
- **Merged from:** 2 v1 fingerprints (`agent-*` + `token-*`).

### `devops-specialist` Decision Framework and Anti-Overengineering Rules remain stack-prescriptive

- **Fingerprint:** `agent-devops-specialist-decision-framework-and-anti-overengineering-still-stack-prescriptive-in-body-after-2026-05-18-fix-on-description-and-identity`
- **Evidence:** `agents/devops-specialist.md:146` — "| < 1k req/day | Single EC2/VPS + Docker Compose |"; `:157` — "Don't use Kubernetes when Docker Compose works"; `:160` — "Don't build a service mesh when Nginx handles the routing"; `:162` — "Don't set up a full observability platform (Datadog, Grafana Cloud) when CloudWatch or a self-hosted Prometheus covers the need".
- **Problem:** An earlier fix corrected only the description and identity paragraph. Both decision sections still name Docker Compose, Kubernetes, Nginx, Datadog, Grafana Cloud, CloudWatch and Prometheus as unconditional guidance.
- **Why it matters at HEAD:** This finding was **reopened three times** across the v1 audit window and never addressed. *(Re-measured: sections now start at 140 and 155.)*

---

## MEDIUM-HIGH

### `code-reviewer` carries 10 full structural review categories, contradicting its documented router role

- **Fingerprint:** `agent-code-reviewer-router-has-ten-structural-review-categories-contradicting-claude-md-183-router-does-not-duplicate-specialist-checks`
- **Evidence:** `agents/code-reviewer.md:60-143` — "## Review Categories" → "### 1. Correctness" … "### 10. Type Safety". Contradicted by `CLAUDE.md:180` — "The router does not duplicate the structural checks of the specialists — it coordinates and synthesizes their outputs."
- **Problem:** The contract says coordinate; the implementation ships all 10 categories inline, duplicating `backend-reviewer` / `frontend-reviewer` work on every `/devteam:review`.
- **Why it matters at HEAD:** Related to but distinct from the `CLAUDE.md:180` factual error in [01](01-referencias-e-consistencia.md) — that entry is about *which agents* are named; this one is about the router doing work it is documented not to do.

### `backend-test-specialist` hardcodes a five-language coverage command matrix

- **Fingerprint:** `agent-backend-test-specialist-body-114-120-hardcodes-per-language-coverage-command-matrix-clover-pytest-jacoco-go-simplecov-stack-prescriptive`
- **Evidence:** `agents/backend-test-specialist.md:118-123` — "| PHP | `--coverage-clover coverage/clover.xml` |", "| Python | `pytest --cov --cov-report=xml` |", "| Java | JaCoCo plugin |", "| Go | `go test -coverprofile=coverage.out ./...` |", "| Ruby | SimpleCov |".
- **Problem:** The block declares its own detection at `:108` and a `Load: skills/devops/sonarqube/SKILL.md` at `:110`, yet the 24-line body sits in the agent and loads regardless.
- **Why it matters at HEAD:** ~15% of the agent, unmoved. It belongs in the SonarQube skill the agent already loads by detection.

### `shared/architecture-awareness` is a behavioral skill that hardcodes framework names, eager-loaded by 3 coding agents

- **Fingerprint:** `skill-architecture-awareness-shared-behavioral-skill-enumerates-react-vue-svelte-angular-blade-twig-erb-jinja-laravel-django-rails-eager-loaded-by-three-coding-agents`
- **Evidence:** `skills/shared/architecture-awareness/SKILL.md:10` — "**Decoupled SPA**: React, Vue, Svelte, Angular consuming an API."; `:14` — "run `vite-bundle-visualizer`, `webpack-bundle-analyzer`"; `:17` — "**Server-rendered templates**: Blade, Twig, ERB, Jinja, Handlebars"; `:27` — "(Laravel+Blade, Django+Templates, Rails+ERB)". Loaded unconditionally at `agents/backend-developer.md:42`, `frontend-developer.md:69`, `mobile-developer.md:56`.
- **Problem:** A `shared/` skill meant to encode *behavior* (layer boundaries, API contracts) instead enumerates a fixed framework and bundler list — and there is no section gate, so `backend-developer` receives SPA bundle advice and `mobile-developer` receives two browser-oriented sections that do not apply to native/RN.
- **Why it matters at HEAD:** It contradicts the stack-agnostic core rule at the one place every coding agent reads on every spawn.
- **Merged from:** 2 v1 fingerprints (`skill-*` + `token-*`).

---

## MEDIUM

### `setup-assistant` embeds an inline Docker Compose detection bash block

- **Fingerprint:** `agent-setup-assistant-lines-60-70-docker-compose-version-detection-inline-bash-block-stack-prescriptive-in-agent-body-while-mobile-detection-and-stack-detection-already-extracted-to-skills`
- **Evidence:** `agents/setup-assistant.md:63-73` — "**Docker Compose version detection:** …" followed by `if docker compose version >/dev/null 2>&1; then DOCKER_COMPOSE="docker compose" … elif command -v docker-compose …`.
- **Problem:** A 10-line Docker-specific block in the body of the agent spawned on 100% of onboardings. On projects without Docker it is pure waste; on projects with Docker it duplicates `skills/devops/docker-dev/SKILL.md` (151 lines).
- **Why it matters at HEAD:** `skills/shared/stack-detection/SKILL.md` exists **and is already loaded by this very agent at line 20**, so the canonical home is available and unused. Sibling agents (mobile, database, devops) use the detection-table pattern instead.
- **Merged from:** 2 v1 fingerprints (`agent-*` + `token-*`).

### `frontend-developer` Data Fetching rules hardcode React/TanStack identifiers outside the detection table

- **Fingerprint:** `agent-frontend-developer-body-92-102-data-fetching-section-hardcodes-usestate-useeffect-tanstack-query-swr-stack-prescriptive`
- **Evidence:** `agents/frontend-developer.md:102` — "**Never duplicate server state in `useState`**"; `:103` — "call `queryClient.invalidateQueries` or `mutate()` (SWR)"; `:106` — "recommend adopting TanStack Query or SWR".
- **Problem:** The Rules block (101-106) sits *below* the detection table (94-99) and states React/TanStack/SWR concretes as unconditional principles.

### `frontend-developer` Security section hardcodes framework and build-tool APIs

- **Fingerprint:** `agent-frontend-developer-security-section-134-139-hardcodes-dangerouslysetinnerhtml-vhtml-vite-next-public-framework-apis-in-agent-body`
- **Evidence:** `agents/frontend-developer.md:140` — "**`dangerouslySetInnerHTML` / `v-html` / `innerHTML`**"; `:142` — "only expose vars prefixed for the build tool (`VITE_*`, `NEXT_PUBLIC_*`)".
- **Problem:** Valid security principles written entirely in React/Vue/Vite/Next identifiers, in the body rather than behind detection.

### `frontend-reviewer` type-safety criteria are written in React+TypeScript identifiers

- **Fingerprint:** `agent-frontend-reviewer-body-type-safety-and-code-quality-hardcodes-react-ts-identifiers-proptypes-react-changeevent-hocs`
- **Evidence:** `agents/frontend-reviewer.md:110-116` — "Component props without declared types (PropTypes, TypeScript interfaces)", "Event handler types missing (`React.ChangeEvent<HTMLInputElement>` vs generic `Event`)", "HOCs wrapping HOCs".
- **Problem:** Generically valid criteria phrased so they read as inapplicable on Vue/Svelte/Angular projects.

### `database-specialist` description pins a closed list of engines

- **Fingerprint:** `agent-database-specialist-description-frontmatter-enumerates-12-engines-and-three-cloud-managed-db-families-stack-prescriptive-identity-surface`
- **Evidence:** `agents/database-specialist.md:3` — "Covers MySQL, PostgreSQL, SQL Server, MongoDB, Redis, Cassandra, SQLite and managed cloud services (AWS RDS/Aurora/DynamoDB, GCP Cloud SQL/Firestore/Spanner, Azure SQL/Cosmos DB)."
- **Problem:** The concrete list belongs only in the detection→skill table at `:63-72`, not on the identity surface the router matches against. *(Re-measured: 7 engines + 9 managed services, not the ~12 the v1 finding claimed.)*

### `mobile/ios` and `mobile/android` are thin wrappers, and platform loading is gated only by prose

- **Fingerprint:** `skill-mobile-ios-and-android-wrapper-pattern-first-instruction-is-load-ios-hig-or-material-design-doubling-token-cost-251-and-256-lines-total-instead-of-218-and-221-net-loss-vs-loading-the-large-skill-directly`
- **Evidence:** `skills/mobile/ios/SKILL.md:7` — "Load `skills/mobile/ios-hig/SKILL.md` for the full reference…"; `skills/mobile/android/SKILL.md:7` — the equivalent for `material-design`. The routing table at `agents/mobile-developer.md:76-77` **already loads both halves**. Detection at `agents/mobile-developer.md:78-82` is prose in a table cell — "| **Cross-platform (both platforms)** | React Native, Flutter, or Expo … | Load **both** platform skill pairs above |" — not a bash gate like the blocks above it.
- **Problem:** Two compounding defects. The wrapper's opening line duplicates a load the agent already performs, so the wrapper adds its body *on top of* the full reference instead of replacing it; and the narrative gate lets a model pessimistically load all four platform skills.
- **Why it matters at HEAD:** iOS costs 33 + 218 = **251** lines, Android 35 + 221 = **256**, cross-platform **507** — for a project that may have one active target. Byte-for-byte unchanged.
- **Merged from:** 3 v1 fingerprints (2 × `agent-*` + 1 × `skill-*`).

### `setup-assistant` bundles three distinct roles in one 244-line agent

- **Fingerprint:** `agent-setup-assistant-three-roles-bundled-extractable-health-checker-update-manager`
- **Evidence:** `agents/setup-assistant.md:42` "## Role 1 — Project Setup", `:196` "## Role 2 — Health Check", `:212` "## Role 3 — Update Manager".
- **Problem:** Three roles with different triggers and different skill needs share one file that loads fully on every spawn.
- **Why it matters at HEAD:** Extracting Roles 2 and 3 would drop the agent to ~195 lines — under the cap. The remedy the v1 finding proposed (extracting the tracker MCP table) **is already done**; the bundled roles are what remains.

### `frontend-test-specialist` inlines reference blocks its backend twin keeps in skills

- **Fingerprint:** `agent-frontend-test-specialist-262-vs-backend-160-asymmetric-decoupled-frontend-block-inlined`
- **Evidence:** `agents/frontend-test-specialist.md:151-189` — "## Decoupled Frontend — Extra Practices" (MSW handler samples, state-coverage table, factories); `:190-199` — "## Selector Priority (Testing Library convention)". `agents/backend-test-specialist.md` has no equivalent inline blocks.
- **Problem:** ~49 lines of inline reference material make the frontend test agent 100 lines heavier than its backend twin for the same role. No extraction target exists — `skills/testing/` holds only contract-testing, mutation-testing, snapshot-testing, test-pyramid, test-strategy, visual-regression.
- **Why it matters at HEAD:** 266 vs 164 lines. *(Note: it is **no longer the largest agent** — `software-architect` at 372 is.)*
- **Merged from:** 2 v1 fingerprints (`agent-*` + `token-*`).

---

## LOW-MEDIUM

### `backend-developer` description enumerates paradigms four lines above a stack-neutrality claim

- **Fingerprint:** `agent-backend-developer-description-enumerates-rest-graphql-mvc-server-rendered-paradigms-on-identity-surface-last-coding-agent-desc-while-body-claims-stack-agnostic`
- **Evidence:** `agents/backend-developer.md:3` — "Works in both decoupled (REST API, GraphQL) and monolithic (MVC, server-rendered templates) architectures." vs `:7` — "You are not attached to any specific stack."
- **Note:** These are paradigms, not products, so this is an honest LOW-MEDIUM — but the description is what the router matches on.

### `mobile-developer` description pins five concrete stacks

- **Fingerprint:** `agent-mobile-developer-description-frontmatter-enumerates-five-stacks-swift-kotlin-react-native-expo-flutter-on-identity-surface`
- **Evidence:** `agents/mobile-developer.md:3` — "native (Swift/Kotlin) and cross-platform (React Native, Expo, Flutter)".
- **Note:** The counter-argument (mobile *is* iOS/Android by nature) stands, so the recommendation is to soften, not delete. The body already has correct detection-gated loading at `:58-82`.

### `setup-assistant` contains two `## Immutability Warning` headers

- **Fingerprint:** `agent-setup-assistant-immutability-section-225-238-redundant-with-warning-line-24-duplicate-md-headers`
- **Evidence:** `agents/setup-assistant.md:28` — "## Immutability Warning / **Never modify files inside `.dev-team-agents/`**" (5 lines) and `:231` — "## Immutability Warning / If the user asks to modify…" (14 lines).
- **Problem:** Duplicate markdown section IDs in one file — breaks anchors and states one rule in two voices. Verified by counting `^## Immutability Warning` per agent: every other agent has exactly 1.
- **Merged from:** 2 v1 fingerprints (`agent-*` + `token-*`).

### `code-reviewer` mixes five conditional loads into a 15-item mandatory Foundational Rule

- **Fingerprint:** `agent-code-reviewer-15-item-foundational-rule-longest-in-repo-5-conditional-loads-eager-listed`
- **Evidence:** `agents/code-reviewer.md:32-59` — items 11-15 are all conditional: `:42` SonarQube "if `sonar-project.properties` … is present", `:44` performance-budgets "If the diff touches frontend assets", `:45` api-versioning, `:46` diataxis-framework.
- **Problem:** Conditional loads sit inside the mandatory "load context first" numbered list instead of a separate section, so they read as unconditional.
- **Why it matters at HEAD:** 28 lines — the **second**-longest Foundational Rule, not the longest as v1 claimed (median across 17 agents = 23).

### `product-analyst` has no gate for Asana / ClickUp / Monday / GitHub Issues / Trello

- **Fingerprint:** `agent-product-analyst-other-trackers-still-asana-clickup-monday-ungated`
- **Evidence:** `agents/product-analyst.md:160-162` — "## Jira / Linear Integration" is the only tracker mention in the file. But `agents/setup-assistant.md:3` advertises "GitHub Issues, Jira, Linear, ClickUp, Trello, etc."
- **Problem:** The installer promises five-plus trackers; the agent that actually writes issues handles two. `skills/integrations/` contains only `jira` and `linear`.

### `software-architect` has the largest Foundational Rule in the repo, and it regrew

- **Fingerprint:** `agent-software-architect-foundational-rule-51-lines-2x-avg`
- **Evidence:** `agents/software-architect.md:13-49` — 37 lines, vs the 17-agent median of 23 (+61%).
- **Why it matters at HEAD:** An earlier partial fix took it 51 → 33; it has since grown back to 37. `software-architect` is spawned by most `/devteam:*` commands.

### The three reviewers still duplicate their Foundational Rule almost verbatim

- **Fingerprint:** `agent-three-reviewers-overlap`
- **Evidence:** `agents/backend-reviewer.md:17-41` vs `frontend-reviewer.md:17-40` — a line-level diff shows only 9 differing lines (doc paths and linter configs). `code-reviewer.md:32-59` repeats the same spine. Combined: 233 + 209 + 197 = 639 lines sharing the same section skeleton, review categories, and output format.
- **Why it matters at HEAD:** **Reduced scope** — two of the three overlaps the v1 finding named are now fixed (`reviewer-mindset` is a one-line load in all three; routing lives in `skills/shared/review-router/SKILL.md`). Only the Foundational Rule duplication and the report skeleton remain, at ~65% verbatim overlap rather than the ~80% originally claimed.
- **Merged from:** 2 v1 fingerprints (`agent-*` + `token-*`).

### `architecture/graphql` — 235 lines, no `references/` extraction, narrative load gate

- **Fingerprint:** `skill-architecture-graphql-235-lines-third-largest-no-references-extraction-loaded-by-narrative-gate-not-detection-signal`
- **Evidence:** `skills/architecture/graphql/` contains only `SKILL.md`. Loaded by a sentence at `agents/backend-developer.md:50`, not a `## Detection Signals` table like `devops/sonarqube/SKILL.md:8` uses.
- **Why it matters at HEAD:** 18 skills now have `references/` dirs; this is the largest un-split skill in `architecture/`. *(Re-measured: still 235 lines but now the 5th largest, not 3rd.)*

### `integrations/gotrue` — 225 lines, largest in its domain, no `references/` extraction

- **Fingerprint:** `skill-integrations-gotrue-225-lines-largest-integration-skill-fourth-largest-overall-no-references-extraction-narrative-load-gate`
- **Evidence:** `skills/integrations/gotrue/` contains only `SKILL.md`; loaded by a bare "Load:" line at `agents/backend-developer.md:106`.
- **Why it matters at HEAD:** Sibling integrations (`jira`, `kong`, `realtime`, `push-notifications`, `database-multitenancy`) all received `references/` splits; `gotrue` was skipped and is the biggest one left. *(Now 6th largest repo-wide, not 4th.)*

### `security-checklist` is loaded by two agents with the overlap asserted rather than partitioned

- **Fingerprint:** `skill-security-checklist-eager-loaded-by-both-security-specialist-and-qa-specialist-no-documented-boundary-overlapping-responsibility`
- **Evidence:** `agents/security-specialist.md:25` — "Load `skills/security/security-checklist/SKILL.md` — OWASP/CWE checklist"; `agents/qa-specialist.md:35` — "…auth flows, input validation, access control … are QA concerns, **not only security-specialist concerns**."
- **Problem:** The qa-specialist line explicitly *asserts* the overlap instead of partitioning it. Both agents cover the same ground with the same 123-line checklist and nothing says which findings belong in which report.
- **Why it matters at HEAD:** Four commands spawn a reviewer plus `qa-specialist`, so the duplicate coverage lands in one consolidated summary.

### `comments-policy` is absent from 9 of 17 agents, including two write-capable coding agents

- **Fingerprint:** `skill-comments-policy-missing-in-non-coding-agents`
- **Evidence:** `grep -rln comments-policy agents/` returns 8 of 17. Absent from `frontend-developer`, `mobile-developer`, `ui-ux-designer`, `software-architect`, `technical-writer`, `security-specialist`, `qa-specialist`, `product-analyst`.
- **Problem:** `frontend-developer` and `mobile-developer` write production code and never load the comments policy, while their reviewers (`frontend-reviewer`, `code-reviewer`) do — so the reviewer enforces a rule the author was never given.
- **Why it matters at HEAD:** Avoidable review churn on the two largest client-side coding agents. *(Re-measured: 9 of 17 lack it, not the 5 the v1 finding claimed.)*
- **Note:** This is the inverse of the duplication finding in [04](04-economia-tokens.md) — the same skill is copy-pasted into 8 agents and missing from 9.

### `discovery-mode` stale-lock handling has an ordering bug and a macOS portability failure

- **Fingerprint:** `skill-discovery-mode-no-stale-lock-cleanup-script-30min-rule-only-documented`
- **Evidence:** `skills/shared/discovery-mode/SKILL.md:129` — "If the lock is stale (older than 30 minutes), remove it and proceed:" with an inline snippet at `:131-136`. The acquire snippet at `:117-121` bails out on `[ -f "$LOCK" ]` **before** the staleness check is ever reached. The staleness check itself uses GNU-only `date -d` with `|| echo 0`.
- **Problem:** Three defects. (a) No cleanup helper exists anywhere in `scripts/`. (b) The two blocks are ordered so a stale lock blocks discovery unless the agent independently reorders them. (c) On macOS, `date -d` fails, `lock_ts=0`, and **every** lock is deleted unconditionally.
- **Why it matters at HEAD:** Parallel-spawn commands (`/devteam:fullstack`, `/devteam:audit`) are exactly the case the lockfile exists for. **Defects (b) and (c) are new — no v1 finding named them.**

---

## LOW

### The `token-efficiency` load line has drifted into nine distinct wordings

- **Fingerprint:** `agent-frontend-developer-and-backend-developer-still-loaded-token-efficiency-inline-line-vs-load-pattern-divergence`
- **Evidence:** `agents/database-specialist.md:24` — "Apply `skills/shared/token-efficiency/SKILL.md` — prefer `grep`/`head` over full reads." vs `software-architect.md:24` — "- Apply `skills/shared/token-efficiency/SKILL.md`" vs `setup-assistant.md:19` — "3. Apply … prefer `grep`/`find`/`head` over full reads".
- **Why it matters at HEAD:** The CHANGELOG announced standardisation to one canonical form; divergence has since **widened from 4 wordings to 9** across the 16 agents that carry the line.

### Composition Root guidance is asymmetric between the two coding agents

- **Fingerprint:** `agent-backend-developer-composition-root-rule-1-line-vs-frontend-developer-12-lines-asymmetric-coverage-of-identical-pattern-no-justification`
- **Evidence:** `agents/backend-developer.md:202` — one sub-bullet pointing at the design-patterns skill; `agents/frontend-developer.md:147-155` — a dedicated 9-line section with four load triggers.
- **Problem:** An identical pattern, originally formalised in a backend/DI context, gets a full section on the frontend agent and one line on the backend agent, with no stated justification.

### `reviewer-base` restates a strict subset of the `sonarqube` skill's own detection signals

- **Fingerprint:** `skill-sonarqube-435-lines-overlap-with-reviewer-base-detection-block`
- **Evidence:** `skills/shared/reviewer-base/SKILL.md:16` lists three signals (`sonar-project.properties`, `.sonarcloud.properties`, `SONAR_TOKEN`); `skills/devops/sonarqube/SKILL.md:8-20` lists six.
- **Problem:** A project detected only by a `sonarqube` service in `docker-compose.yml` or a `sonar-scanner` CI step is missed by the reviewer gate even though the skill itself lists those signals.
- **Why it matters at HEAD:** The size half of this finding is **fixed** — `sonarqube/SKILL.md` went 435 → 74 lines with `references/`. Only the detection duplication survives.

### The `When loaded` sub-block pattern exists in exactly one agent

- **Fingerprint:** `agent-when-loaded-pattern-only-qa`
- **Evidence:** `agents/qa-specialist.md:43` — "load `skills/devops/sonarqube/SKILL.md`. When loaded:" — the only occurrence across all 17 agents.
- **Problem:** A useful convention (state what to do once a conditionally-loaded skill is in context) was never propagated to the five other agents that conditionally load the same skill.

### No skill uses the `scripts/` subdirectory the agentskills.io spec allows

- **Fingerprint:** `skill-no-skill-uses-scripts-subdir-pattern-agentskills-io`
- **Evidence:** `find skills -type d -name scripts` returns nothing; `find skills -type d -name references` returns **18** directories.
- **Problem:** Every executable snippet in the corpus is inline bash a model must transcribe, rather than a checked-in script that can be tested.
- **Why it matters at HEAD:** The repo adopted the `references/` half of the spec at scale but never the `scripts/` half — which is precisely why the `discovery-mode` `date -d` portability bug above stayed invisible.

### `shared/adr` is reachable from only one agent

- **Fingerprint:** `skill-adr-coverage-only-architect`
- **Evidence:** `grep -rn "shared/adr" agents/ commands/` → `agents/software-architect.md:30` and `commands/learn.md:171`. No other agent references it.
- **Problem:** `CLAUDE.md`'s ADR Trigger Rule applies to any hard-to-reverse decision (database engine, auth strategy, API design), but `database-specialist`, `backend-developer`, `devops-specialist` and `security-specialist` — the agents that make those calls — have no path to the skill.

### `jQuery` sits in `skills/ui-libraries/` alongside modern component libraries

- **Fingerprint:** `agent-frontend-developer-loads-jquery-skill-orphan-of-modern-stacks`
- **Evidence:** `agents/frontend-developer.md:84` routes to `skills/ui-libraries/jquery/SKILL.md`; the directory holds `antd, bootstrap, chakra-ui, jquery, mui, shadcn`.
- **Note:** A taxonomy call, not a defect — jQuery is a DOM/AJAX library, not a component library in the sense of the others.

### No skill covers LLM / RAG / prompt-engineering integration, and the one pointer is broken

- **Fingerprint:** `skill-missing-prompt-engineering-or-llm-integration`
- **Evidence:** No skill directory matches the topic across 133 skills. The only mention is `skills/database/db-comparison/SKILL.md:37` — "**pgvector** … Semantic search, embeddings, RAG pipelines — load `skills/integrations/database-multitenancy/SKILL.md`" — which routes to a multitenancy skill unrelated to vector search.
- **Why it matters at HEAD:** The gap persisted through 12 new skills in other domains, and **the broken pointer is a fresh defect no v1 finding named**.

### No skill covers load / performance testing

- **Fingerprint:** `skill-add-load-testing`
- **Evidence:** `grep -rli "k6|jmeter|locust|load test|stress test" skills/` returns zero files. `skills/testing/` holds 6 skills, none load-related. The nearest neighbour, `skills/architecture/performance-budgets/SKILL.md:3`, is scoped to client-side budgets (Core Web Vitals, Lighthouse CI).
- **Why it matters at HEAD:** `skills/testing/` grew from 2 → 6 skills and every other gap named in the v1 reports was filled; this one was not.

---

## Cross-references

| Finding | Filed under |
|---|---|
| 11 of 17 agents exceed the 200-line cap, with no enforcement path | [02 — Flows](02-fluxos-e-workflows.md) |
| `security-checklist` eager-loaded by `qa-specialist` (cost dimension) | [04 — Token Economy](04-economia-tokens.md) |
| Foundational Rule duplicated across 17 agents (384 lines) | [04 — Token Economy](04-economia-tokens.md) |
| 20 skill descriptions exceed the 95-char budget | [04 — Token Economy](04-economia-tokens.md) |
