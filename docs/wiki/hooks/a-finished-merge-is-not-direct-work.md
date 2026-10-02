# A Finished Merge Is Not Direct Work

**Origin:** task-board PR/MR Created feature rebase regression | 2026-10-01
**Tags:** task board, merge, direct work, precedence, PreToolUse, PostToolUse, pr_refs.classify, tool output, payload

> A hook payload carrying its tool output is recognized as a PR/MR event first; only payloads without output may be read as direct work, because direct work is captured pre-execution and the output is what confirms a creation or merge.

---

## What it is

The task board reads a main-session shell call in two ways. Direct work (`tasks._normalize_direct`)
takes any write-shaped command (`tasks.writes()`) as the session's own work, from the call before it
runs. The PR/MR path (`pr_refs.classify`) takes a `gh pr` / `glab mr` / `git merge` call only once its
output is in the payload, because the output is the only proof a PR/MR was created or merged.
`git merge` is write-shaped, so its finished PostToolUse payload matches both readers.

## How it works

`tasks.record()` normalizes a payload first and falls through to `_record_event` (PR/MR and merge
events) only when `normalize()` returns `None`. Once direct work existed, `normalize()` returned a
`("direct", {})` op for the finished `git merge`, so the merge was never recorded: the PR stayed
`open`, and the catch-up-merge guard was bypassed. `record()` now routes a direct op to
`_record_event` when `pr_refs.classify(payload)` recognises it. `classify` needs the output, so the
same command's pre-execution payload still becomes direct work.

Only `post-tool-use/02-pr-created.sh` forwards shell payloads after execution; `01-task-board.sh`
exits early on `Bash` and `mcp__*` tools.

## Gotchas

- Direct work is snapshot-captured before execution; the output that confirms a PR/MR event arrives after. Adding a new post-tool reader or write-shaped classifier without this precedence will silently break merge/event recording.
- Neither feature's tests caught this alone; only the two together did. A test for a new reader of shell payloads needs a case where the other reader also matches.

## References

Commit ffbfcb4: "fix(cli): record a finished git merge as a merge, not direct work"
`scripts/lib/devteam/tasks.py` — `record()` function and its call to `pr_refs.classify()`
`tests/test_task_board_pr.py::test_a_git_merge_records_the_branch_it_merged_into` — regression assertion
