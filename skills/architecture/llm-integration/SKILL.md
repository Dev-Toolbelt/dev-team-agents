---
name: llm-integration
description: LLM/RAG in product — retrieval, chunking, prompt versioning, eval, cost, failure modes.
---

# LLM Integration

How to put a language model inside a product feature: retrieval, prompting, evaluation, cost, and the failure modes that only appear in production.

## When to Load

Load when the project ships a feature whose output is produced by a language model — semantic search, assistant/chat, summarization, extraction, classification, agentic tool-calling, or "ask your data".

Do **not** load for using an AI coding assistant to write the project's code. That is tooling, not product architecture.

> Model names, providers and API shapes below are **illustrative only**. Detect the provider the project already uses (SDK in the dependency manifest, `*_API_KEY` in env templates, gateway config) and follow its own documentation. Never introduce a provider the project has not chosen.

---

## Step 0 — Choose the Cheapest Mechanism That Works

Escalate only when the tier below fails an evaluation, never by default.

| Tier | Mechanism | Use when | Cost of change |
|---|---|---|---|
| 1 | **No model** (deterministic code, full-text search, rules) | Output is derivable from data | None |
| 2 | **Prompt only** | Task fits in instructions; knowledge is in the model or the request | Edit a string |
| 3 | **Prompt + few-shot examples** | Output shape or tone is hard to describe but easy to demonstrate | Edit a string |
| 4 | **RAG** (retrieval-augmented generation) | Answers depend on private, large, or frequently changing corpora | Ingestion pipeline + store |
| 5 | **Tool / function calling** | The model must read live state or cause effects | Tool contracts + authz per tool |
| 6 | **Fine-tuning** | Style/format is stable and demonstrably unteachable by prompt | Training + retraining treadmill |

Rules:
- RAG fixes **missing knowledge**. Fine-tuning fixes **behavior and format**. Using either for the other's problem is the most common architectural mistake in this space.
- Fine-tuning freezes knowledge into weights — a corpus that changes weekly must be retrieved, not trained.
- Tool calling turns the model into a caller of your API. Every tool must enforce the **caller's** authorization, never the model's intent (see `skills/security/idor/SKILL.md`).

---

## Ingestion and Chunking

The retrieval quality ceiling is set at ingestion time. A chunking mistake cannot be recovered by a better model.

| Decision | Guidance |
|---|---|
| Chunk boundary | Split on **document structure** (heading, section, article, row, function) before falling back to fixed size |
| Chunk size | Small enough that one chunk answers one question; large enough to stand alone without its neighbours |
| Overlap | Modest overlap prevents cutting a fact in half; heavy overlap inflates index size and returns near-duplicates |
| Context header | Prepend document title / section path to each chunk so an isolated chunk remains interpretable |
| Tables and code | Never split a table from its header row or a function from its signature — chunk them whole or summarize |
| Metadata | Store `source_id`, `version`, `updated_at`, tenant/ACL keys, and section path alongside every vector |

Pipeline requirements:
- **Idempotent re-ingestion** — re-processing a document must replace, not duplicate, its chunks. Key on `(source_id, chunk_index)` or delete-then-insert per document.
- **Deletion propagation** — when a source record is deleted or unshared, its vectors must be deleted too. Orphan vectors leak data forever.
- **Re-embed on model change** — an index mixing two embedding models is silently broken. Store the embedding model + version per row and re-index on change.
- Treat ingestion as a background job with retries and dead-letter handling (`skills/architecture/async-jobs/SKILL.md`).

---

## Embeddings

| Property | What to check before choosing |
|---|---|
| Dimensionality | Directly drives index size, memory and query cost — larger is not automatically better |
| Domain fit | General-purpose embeddings underperform on code, legal, medical and non-English corpora |
| Symmetry | Some models expect distinct query vs document prefixes; mismatching them quietly degrades recall |
| Max input | Inputs longer than the limit are truncated, often **silently** |
| Normalization | Cosine similarity assumes normalized vectors; verify the model's convention |

Rules:
- Embed the **same normalized text** at query time and at index time (same casing, same stripping, same prefix).
- Cache embeddings keyed by `hash(text) + model + version`. Re-embedding unchanged content is pure waste.
- Batch embedding calls at ingestion; concurrency at query time is latency, not throughput.

---

## Vector Store Selection

Gate on signals already present in the project. See `skills/database/db-comparison/SKILL.md` for the surrounding database picture.

| Signal | Choice |
|---|---|
| Project already runs PostgreSQL, corpus in the low millions of chunks | `pgvector` in the existing database — one backup, one transaction, one ops surface |
| Multi-tenant with row-level isolation already enforced in SQL | Vectors in the same database so the existing policies still apply (`skills/integrations/database-multitenancy/SKILL.md`) |
| Corpus very large, or vector search is the product's core workload | Dedicated vector database |
| Serverless / edge with no persistent database | Managed vector service from the existing cloud provider |
| Corpus small and rebuilt on deploy | In-process index — no service to operate |

Rules:
- Filters (tenant, ACL, date, type) must be applied **inside** the vector query. Post-filtering after top-k returns fewer results than requested, or none.
- Index type (exact vs approximate) is a recall/latency trade-off — measure recall against exact search on a sample before shipping approximate.
- Never store the only copy of source text in the vector store; it is a derived index and must be rebuildable from the system of record.

---

## Retrieval Patterns

| Pattern | What it fixes | Cost |
|---|---|---|
| **Hybrid search** (vector + keyword/BM25, fused) | Vector-only misses exact identifiers, codes, rare names | One extra query |
| **Metadata pre-filter** | Wrong tenant/version/language leaking into results | Requires indexed metadata |
| **Reranking** (cross-encoder over top-N) | Correct chunk retrieved but ranked too low to survive top-k | Extra latency per query |
| **Query rewriting** | Conversational or underspecified queries embed poorly | Extra model call before retrieval |
| **Parent-document retrieval** | Small chunks match well but lack context to answer | Store child→parent mapping |
| **Diversity selection (MMR)** | Top-k saturated by near-duplicate chunks | Slight relevance trade-off |

Rules:
- Retrieve wide, rerank, then pass **few** chunks to the model. Stuffing the context window degrades answer quality and multiplies cost.
- Always pass chunk identifiers into the prompt and require citations in the output — this makes hallucination detectable rather than invisible.
- When retrieval returns nothing above the similarity floor, return "no supporting information found". **Never** let the model answer from parametric memory in a grounded feature.

---

## Prompt Versioning

Prompts are deployable artifacts with behavior, not configuration strings.

| Rule | Implementation |
|---|---|
| Prompts live in version control | Dedicated files/templates in the repo, reviewed like code |
| Every prompt carries a version id | Semantic or incrementing; emitted in logs and traces with every call |
| Inputs are injected, never concatenated ad hoc | A template with named slots; user content clearly delimited |
| Model + parameters are pinned per version | Provider, model id, temperature, max tokens travel **with** the prompt version |
| Changes ship behind a flag | Roll out gradually and compare against the previous version (`skills/architecture/feature-flags/SKILL.md`) |
| Rollback is a config change | Reverting a prompt version must not require a redeploy of the whole service |

An "upgrade" of the underlying model is a **breaking change to the prompt contract**. Re-run the evaluation suite before adopting any new model version, including minor ones.

---

## Evaluation

Without an evaluation set, every prompt change is an unmeasured regression.

**Golden set** — 50–200 real, representative cases with expected outcomes. Include known failures, edge cases, adversarial inputs and out-of-scope questions. Version it with the prompts; grow it from production incidents.

Measure retrieval and generation separately — a bad answer from perfect context is a prompt problem, a bad answer from missing context is a retrieval problem.

| Layer | Metric | Meaning |
|---|---|---|
| Retrieval | Recall@k | Was the correct chunk retrieved at all? (ceiling for everything downstream) |
| Retrieval | Precision@k / MRR | How much noise reaches the prompt; how high the right chunk ranks |
| Generation | Groundedness | Is every claim supported by the retrieved context? |
| Generation | Answer relevance | Does it answer the question that was asked? |
| Generation | Format validity | Does the output parse against the expected schema, every time? |
| Operational | p95 latency, cost/request, refusal rate | Regressions users and finance feel first |

Rules:
- **Deterministic checks first** — schema validity, required citations, forbidden strings, exact-match fields. They are free and catch most regressions.
- **LLM-as-judge** is useful but biased: it favors verbose answers and its own style, and it drifts when the judge model changes. Pin the judge model + judge prompt version, and calibrate it against human labels periodically.
- Run the evaluation suite **in CI** on any change to prompts, chunking, retrieval parameters, or model version. Gate merges on the retrieval and format metrics; report the subjective ones.
- Sample real production traffic into the golden set continuously — synthetic-only suites decay.

---

## Cost and Latency Control

| Lever | Effect |
|---|---|
| Smaller/cheaper model for narrow subtasks (classification, routing, extraction) | Largest single cost reduction; reserve the strong model for synthesis |
| Provider prompt/context caching for stable prefixes | Put the invariant system prompt first, variable content last |
| Semantic or exact-match response cache for repeated queries | Removes both cost and latency entirely on hits |
| Fewer, better chunks in context | Cost scales with input tokens, latency scales with output tokens |
| Streaming responses | Perceived latency drops even when total time does not |
| `max_tokens` and output schemas | Bounds the expensive half of the bill |
| Batch/offline API for non-interactive work | Significant discount for ingestion, backfills, evaluations |

Guardrails, not suggestions:
- **Per-user and per-tenant quotas** on requests and tokens (`skills/architecture/rate-limiting/SKILL.md`). An unmetered LLM endpoint is an unbounded bill exposed to the internet.
- **Timeouts, retries with backoff, and a circuit breaker** on every provider call; degrade to a non-AI path when the provider is down (`skills/architecture/resilience/SKILL.md`).
- **Token accounting per request** persisted with tenant, feature and prompt version — cost attribution is impossible to reconstruct later.
- Long generations belong in a **background job with a result callback**, not in a synchronous request holding a connection open.

---

## Failure Modes

| Failure | Why it happens | Mitigation |
|---|---|---|
| **Hallucination** | Model completes plausibly when context is missing or contradictory | Require citations to retrieved chunk ids; verify claims map to context; return "not found" below the similarity floor |
| **Prompt injection** | Untrusted text (user input, retrieved documents, web pages, tool output) is read as instructions | Treat all non-system text as data: delimit and label it, keep authority in the system prompt, never let text grant permissions |
| **Indirect injection via RAG** | A poisoned document in the corpus hijacks every answer that retrieves it | Trust-tier the corpus, strip instruction-like patterns at ingestion, restrict which sources may be retrieved per feature |
| **Excessive agency** | Tool calls execute with the service's privileges instead of the user's | Authorize every tool call against the end user; require confirmation for destructive or irreversible actions; allowlist tools per feature |
| **PII in prompts** | User data, secrets, or full records are sent to a third party and may be retained | Minimize fields sent, redact before the call, verify provider retention/training terms, honor data-residency constraints |
| **Secret leakage into context** | Credentials in retrieved documents or env dumps get echoed back | Scan the corpus for secrets at ingestion (`skills/security/secret-management/SKILL.md`) |
| **Output injection** | Model output is rendered as HTML/markdown or executed as SQL/shell | Escape and validate model output exactly like user input — it is untrusted |
| **Silent format drift** | Free-text output parsed with regex breaks after a model update | Constrain to a schema, validate on every response, retry once with the validation error, then fail loudly |
| **Non-determinism in tests** | Same input, different output | Pin model + parameters; assert on invariants and schema, not exact strings; mock the provider in unit tests |
| **Context window overflow** | Conversation or retrieved set grows past the limit | Budget tokens explicitly per section; truncate history by summarization, not by silent tail-drop |
| **Cost blowout** | Retry storms, loops in agentic flows, unmetered endpoints | Hard caps on iterations and tokens per request; alert on cost per tenant, not just totals |

`skills/security/owasp-top-10/SKILL.md` remains fully applicable — an LLM feature is still a web feature.

---

## Observability

Emit one trace per LLM interaction, carrying: `prompt_version`, `model` + parameters, retrieved chunk ids and scores, input/output token counts, latency split (retrieval vs generation), tool calls made, and the outcome (success / schema failure / refusal / no-context).

- Log **references** to prompts and inputs, not full PII payloads; sample full traces under an explicit retention policy.
- Define SLOs on the user-visible metrics — p95 latency, error rate, refusal rate (`skills/architecture/observability-slo/SKILL.md`).
- Capture explicit and implicit user feedback (thumbs, edits, abandonment) and route it back into the golden set.

---

## Decision Checklist

- [ ] Is a model actually required, or is this a search/rules problem?
- [ ] Is the mechanism the cheapest tier that passes evaluation (prompt → few-shot → RAG → tools → fine-tune)?
- [ ] Does chunking follow document structure, and does each chunk stand alone?
- [ ] Is re-ingestion idempotent, and does deletion remove vectors?
- [ ] Is the embedding model + version recorded per row, with a re-index path?
- [ ] Are tenant/ACL filters applied inside the vector query, not after it?
- [ ] Is retrieval hybrid and reranked before hitting the context window?
- [ ] Are prompts versioned, pinned to a model, flagged, and rollback-able without a redeploy?
- [ ] Does a golden set exist, and does CI gate merges on it?
- [ ] Are quotas, timeouts, retries, token caps and cost attribution in place?
- [ ] Is every non-system text treated as data, and every model output treated as untrusted?
- [ ] Do traces carry prompt version, retrieved ids, tokens and outcome?
