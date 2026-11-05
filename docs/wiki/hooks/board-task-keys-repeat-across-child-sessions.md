# Board task keys repeat across child sessions folded into one canvas session

**Origin:** Canvas view (ADR-0063) task graph | 2026-11-05
**Tags:** task board, task key, record_id, child session, trace/aliases.json, opencode, codex, graph.py, openTaskLink, resolveTaskLink

> A board task `key` (`t1`, `t2`…) is unique only within one board record. Anything that resolves a task must send the record it lives in (`record_id`), never the top session id.

---

## What it is

opencode child sessions and Codex child threads write their own board record until `trace/aliases.json` maps them to the top session. `scripts/lib/devteam/graph.py` folds those records under the top session by alias, so the same `t1` can appear twice in one canvas session.

## How it works

- Every graph node carries `record_id`, plus `session_id` and `spawn_id`.
- A board task without a spawn id gets the node id `span:<sid>:<record>:<key>`, so two `t1` tasks in one session do not collide.
- Resolvers look the task up in the record they are given: the PR link path (`openTaskLink` → `resolveTaskLink` in `app/src/main/taskBoard.ts`), "Show on board", and any future node action.

## Gotchas

- Sending the top session id resolves the wrong `t1`, or none, whenever a child record is folded in.
- `tasks.record` stops writing a child's record once its alias exists. The duplicate case therefore appears only when a child wrote before its alias, which makes it rare and easy to miss in tests.

## References

- `scripts/lib/devteam/graph.py`
- `app/src/main/taskBoard.ts` (`resolveTaskLink`)
- `docs/development/adrs/0063-the-canvas-view-reads-a-cli-derived-task-graph-rendered-with-react-flow-and-a-deterministic-own-layout.md`
