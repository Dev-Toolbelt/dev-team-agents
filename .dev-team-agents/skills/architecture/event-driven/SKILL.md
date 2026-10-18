---
name: event-driven
description: Event-driven — sourcing, CQRS, saga, idempotency, schema registry.
---

# Event-Driven Architecture

## When to Load

Load when the project uses message queues (Kafka, RabbitMQ, SQS, Pub/Sub), event stores, or distributed transactions.

## Core Patterns

| Pattern | Use when | Key constraint |
|---------|----------|----------------|
| **Event Sourcing** | Audit log required; time-travel queries needed | Event log is append-only; state derived on read |
| **CQRS** | Read and write models diverge; separate scaling needed | Two models must stay eventually consistent |
| **Saga (Orchestration)** | Central coordinator acceptable; easier debugging | Single point of failure in orchestrator |
| **Saga (Choreography)** | Loose coupling preferred; no central bottleneck | Harder to trace; each service reacts to events |
| **Outbox Pattern** | Atomicity between DB write and event publish required | Requires outbox table + background publisher |

## Event Types

| Type | Scope | Versioning |
|------|-------|------------|
| Domain event | Within a bounded context | Internal; break freely |
| Integration event | Crosses bounded contexts | Public contract; version explicitly |

## Idempotency

Every consumer must handle duplicate events:
- Store processed event IDs (`event_id` column or Redis SET)
- Check before processing: if already processed, return success without side effects
- Use idempotency key in HTTP retries (`Idempotency-Key` header)

## Schema & Versioning

| Strategy | Tooling | Trade-off |
|----------|---------|-----------|
| Schema registry | Confluent Registry, AWS Glue | Enforces contract; requires registry infra |
| Avro / Protobuf | Binary; backward/forward compatible with rules | Requires code generation |
| JSON Schema | Human-readable; no code gen | Weaker enforcement |

**Backward-compatible changes**: add optional fields, add enum values at end.
**Breaking changes**: remove fields, rename fields, change types → require new event version.

## Eventual Consistency Trade-offs

- **Read-your-writes**: client must read from the same replica or cache the write locally
- **Causality**: tag events with a `causation_id` and `correlation_id`
- **Compensating transactions**: for sagas, define a compensating action for every step that can fail

## Failure Modes

| Failure | Mitigation |
|---------|------------|
| Consumer lag | Dead-letter queue (DLQ) + alerting on lag |
| Duplicate delivery | Idempotency (see above) |
| Ordering guarantee lost | Partition by entity ID; use sequence numbers |
| Event store grows unbounded | Snapshots: periodically collapse N events into current state |

## Decision Checklist

- [ ] Does the domain require a full audit log? → consider event sourcing
- [ ] Do read and write patterns differ significantly? → consider CQRS
- [ ] Do you need distributed transactions across services? → choose saga strategy
- [ ] Is your message broker at-least-once? → implement idempotent consumers
- [ ] Are events crossing team/service boundaries? → define integration events with explicit versions
