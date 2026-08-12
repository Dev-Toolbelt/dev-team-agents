---
name: ingestion-api
description: Ingestion API — inbound data boundary design, validation, backpressure, idempotency, DLQ.
---

# Ingestion API

Design guidance for the boundary that accepts data **into** a system from external producers — webhooks, telemetry/event beacons, bulk file/CSV uploads, IoT/device streams, partner data feeds, log/metrics collectors.

## When to Use

Build a dedicated ingestion API when:
- An external or semi-trusted producer (partner system, device fleet, webhook sender, client SDK) pushes data **in**, as opposed to a client pulling data out
- Volume or burstiness makes synchronous processing risky (spiky webhook fan-in, batch file drops, high-frequency telemetry)
- The producer cannot be forced to slow down, retry correctly, or wait — the boundary must absorb load on the producer's terms, not the consumer's
- Data must be durably accepted before it is fully processed (accept now, validate/enrich/store asynchronously)
- Multiple producers with different trust levels, schemas, or versions feed the same downstream pipeline

## When NOT to Use

Do not stand up a distinct ingestion layer when:
- The write is a normal user-initiated CRUD operation from your own frontend — that's `skills/architecture/api-design/SKILL.md`, not ingestion
- Volume is low and synchronous validate-then-persist is fast enough (~200ms) and the caller is trusted — plain REST/GraphQL endpoint is sufficient
- The data originates internally between your own services with a shared schema and controlled cadence — use `skills/architecture/event-driven/SKILL.md` (pub/sub, sagas) instead
- You only need to *pull* data from a third party on a schedule — that's an outbound integration, not ingestion

Ingestion is defined by the boundary property (uncontrolled external push, must-not-drop) — not by data volume alone.

---

## Detection Signals

- Endpoint names/paths containing `ingest`, `collect`, `events`, `webhook`, `telemetry`, `beacon`, `bulk-upload`
- A queue or buffer sitting directly behind a public HTTP endpoint (SQS/Pub/Sub/Kafka topic fed by an API Gateway route)
- Webhook receivers from third parties (Stripe, GitHub, Twilio, payment/CRM providers)
- Bulk/batch file ingestion (CSV/JSON/Parquet drop, S3 event-triggered processing)
- High-cardinality client-side event/analytics collection endpoints

---

## Core Design Rules

### 1. Accept Fast, Process Later
The HTTP response confirms **receipt**, not **completion**. Validate the envelope (auth, shape, size) synchronously; hand the payload to a queue or durable store and return `202 Accepted` (or `200` with a receipt id). Full processing — enrichment, business validation, side effects — happens as a background job. See `skills/architecture/async-jobs/SKILL.md` for the job-side idempotency and retry rules once payload hands off there.

### 2. Idempotency at the Boundary
Producers retry on timeout or ambiguous response — the same event will arrive more than once.
- Require or generate a de-duplication key (`Idempotency-Key` header, or a producer-supplied event id) and reject/short-circuit duplicates within a bounded window
- For webhooks, verify the provider's signature **and** dedupe on their event id — signature verification alone does not stop replays
- Never let "accept twice, process twice" happen silently — a passed idempotency check must be visible in logs/metrics, not just swallowed

### 3. Validate the Envelope, Defer the Semantics
Two validation passes, not one:
- **Synchronous, at the edge:** authentication/signature, content-type, size limits, required envelope fields (id, timestamp, schema version). Reject immediately — the producer can act on the error now.
- **Asynchronous, in the worker:** business-rule validation, cross-record checks, enrichment. Route failures to a dead-letter queue (DLQ) — do not block the accept path on rules the producer cannot fix in real time.

### 4. Backpressure Is a Feature, Not a Bug
The ingestion boundary must be able to say "slow down" without dropping data:
- Prefer `429` with `Retry-After` over silently discarding a request when downstream is saturated
- Size the buffer (queue depth) explicitly; alert before it fills, not after
- If the producer is yours (your own SDK/agent), implement client-side backpressure/batching instead of hammering the endpoint — see `skills/architecture/rate-limiting/SKILL.md` for algorithms and headers
- Never let an unbounded queue become an unbounded memory/disk leak — cap it and define the overflow behavior (reject new, or shed oldest, per data criticality)

### 5. Schema Evolution and Versioning
Producers you don't control ship on their own schedule.
- Version the payload envelope explicitly (`schema_version` field or versioned path/media type) — never infer version from field presence
- New optional fields must not break existing producers; removing or repurposing a field is a breaking change and needs a migration window
- Reject unknown-but-critical fields loudly in a sandbox/staging producer, but **accept and store unknown fields as opaque data** in production rather than dropping the whole event — a strict schema at the boundary turns a producer's minor addition into full data loss
- Cross-reference `skills/architecture/api-versioning/SKILL.md` for the general versioning contract this specializes

### 6. Batch vs. Streaming Ingestion
| Shape | Use when | Watch for |
|---|---|---|
| Single-event HTTP push (webhook) | Low-to-moderate frequency, one producer event per request | Signature verification, per-event idempotency key |
| Bulk file/batch upload | Producer emits periodic large batches (CSV export, nightly feed) | Partial-failure reporting — never all-or-nothing on a 100k-row file; report per-row/per-chunk status |
| Streaming (Kafka/Kinesis/WebSocket ingest) | Continuous high-frequency telemetry, ordering matters within a partition key | Consumer lag as the primary health signal, not endpoint latency |

### 7. Authentication and Trust Tiering
- Machine-to-machine producers authenticate with API keys, mTLS, or provider-specific signatures (never end-user session cookies)
- Trust-tier producers explicitly (first-party service, verified partner, unauthenticated public collector) and apply validation/rate limits proportional to trust — do not apply one policy to all
- Rotate and scope ingestion credentials per producer so one compromised partner key doesn't grant write access to the whole pipeline

### 8. Observability
Minimum signals for an ingestion boundary:
- Accept rate, reject rate (by reason: auth, validation, rate-limit), and DLQ growth rate
- End-to-end lag: time from accept to fully-processed, not just endpoint response time
- Duplicate/idempotency-hit rate — a sudden spike usually means a producer-side retry storm, not a boundary bug

---

## Related Skills

| Concern | Skill |
|---|---|
| What happens to the payload after it's queued | `skills/architecture/async-jobs/SKILL.md` |
| Producer-facing throttling algorithms and headers | `skills/architecture/rate-limiting/SKILL.md` |
| General REST/GraphQL contract rules | `skills/architecture/api-design/SKILL.md` |
| Internal service-to-service messaging, sagas | `skills/architecture/event-driven/SKILL.md` |
| Payload envelope/version contract | `skills/architecture/api-versioning/SKILL.md` |
| Large file transfer into the system | `skills/architecture/multipart-upload/SKILL.md` |
| Retries/circuit breakers on downstream calls made during processing | `skills/architecture/resilience/SKILL.md` |
| Ingesting documents into a RAG corpus specifically | `skills/architecture/llm-integration/SKILL.md` § Ingestion and Chunking |
