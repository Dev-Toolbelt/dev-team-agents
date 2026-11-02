# A Held Stop Is Not the Agent's End

**Origin:** Orchestrator persona and supervision gate, ADR-0062 | 2026-11-02
**Tags:** SubagentStop, held stop, supervision gate, block decision, subagent-stop dispatcher, task board, 00-supervision, 01-task-board, settle, codex

> A sub-script that settles work must run only on the stop that ends the agent. A gate that holds a stop prints a block, and every sub-script after it is skipped on that stop, so the task is settled on the stop that follows the hold.

---

## What it is

On Codex, `SubagentStop` fires when a child agent stops. The dispatcher in `scripts/hooks/subagent-stop.sh` runs the sub-scripts in `scripts/hooks/subagent-stop/` in alphabetical order. The supervision gate (`00-supervision.sh`, ADR-0062) runs first. When it holds the stop, it prints a `{"decision":"block",...}` and the child keeps running. The task board (`01-task-board.sh`) must not treat that stop as the end of the work.

## How it works

1. Codex fires `SubagentStop` for the child.
2. `00-supervision.sh` checks whether the agent finished properly, for example that its run banner was returned. If not, it prints a block decision.
3. The dispatcher sees the block (`BLOCK_RE`), keeps that output, and `break`s out of the loop.
4. `01-task-board.sh` does not run on this stop.
5. The child continues. Its next stop, the one that ends the agent, runs the gate again. The gate passes, prints nothing, and the task board runs.

## Gotchas

- **Order is load-bearing.** A sub-script that settles work (task board, review window, trace) must sit after the gate. Otherwise the task is marked `completed` while the agent is still working.
- **A held stop is not an end.** Any new sub-script that ends a task on `SubagentStop` must be checked against this rule. The dispatcher's `break` is what keeps the held stop from reaching it.
- **Dispatcher exit code is always 0.** An exit 2 would keep a Codex child running from a board hook. Only the printed JSON carries the block.
- **Keep the gate at `00-`.** Any sub-script that sorts before it runs on the held stop too, so the gate must stay first.

## References

- ADR-0062 (orchestrator persona and supervision gate)
- `scripts/hooks/subagent-stop.sh` (dispatcher header: a held stop is not the agent's end)
- `scripts/hooks/subagent-stop/00-supervision.sh`, `scripts/hooks/subagent-stop/01-task-board.sh`
- `docs/wiki/hooks/codex-0160-subagent-payloads.md` (`SubagentStop` payload and task dedupe)
