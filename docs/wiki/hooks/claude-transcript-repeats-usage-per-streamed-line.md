# A Claude transcript repeats each message's usage while it streams

**Origin:** /devteam:learn consolidation, execution trace and usage accounting (ADR-0042) | 2026-10-19
**Tags:** claude transcript, usage, message.id, subagent, jsonl, streaming, token count, overcount, final count

> A Claude subagent transcript writes several JSONL lines per `message.id`. Summing every line overcounts tokens. Count only the last line per `message.id`.

---

## What it is

While a message streams, the transcript gets a new line each time it grows. Each line repeats the usage known so far, so the same message's tokens appear more than once.

## How it works

1. Group the transcript's assistant lines by `message.id`.
2. Keep the last line of each group. It carries the final usage.
3. Sum the kept lines.

## Gotchas

- Summing every line overcounts, often by several times for a long streamed reply.
- The first line of a message can show a partial count, so do not take the first line either.

## References

- `scripts/lib/devteam/usage.py` — `claude_transcript_usage`
