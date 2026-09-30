# A fixture built by the new code cannot test migration from the old

**Origin:** migration tests that passed while migration broke every hook | 2026-09-27
**Tags:** fixture, migration, test design, circular, legacy layout, false confidence

> If the "old system" in a migration test is produced by the new system, the test asserts that the new code can read its own output — which is never the question.

---

## What it is

A migration test needs a starting state. The cheapest way to build one is to call the code you
already have. That works right up to the point where the old layout contained something the new
code never writes — and that is exactly where migrations break.

## How it works

The v2 fixture was built with `bind(mode="vendored")`, which produces the same directory trees a v2
install had. What it does **not** produce: `.claude/settings.json` with v2 hook paths,
`user-data/state.json`, `credentials.local.json`, or the v2 `.gitignore` lines.

So the suite was green while `devteam migrate --apply` moved `.dev-team-agents/scripts/` into
quarantine and left all four hook commands pointing at it — every hook in the migrated project
silently failing from the next session on.

The fix is to hand-build the legacy layout, including the parts the new code has no reason to
create, and to assert on the *consequence* rather than the mechanics:

```python
# not "was the tree moved?" but "does the path the rewritten hook names exist?"
self.assertTrue((root / commands[0].split()[-1]).exists())
```

## Gotchas

- The tell is a fixture helper that imports the module under test. If the arrange step and the act
  step share an implementation, the assert step is measuring one thing twice.
- Recording a real legacy layout once — as a fixture directory or a generator script pinned to the
  old version — costs less than the incident it prevents.
- Assert that a path a config file *names* resolves, not merely that some file moved. The broken
  state here had every file exactly where the migration intended and every reference dangling.

## References

- `tests/test_review_regressions.py` — `LegacyV2MigrationTest`, which builds the v2 layout by hand
- **A fixture built with `bind()` also leaves a manifest behind.** The v2 fixture unbinds with
  `keep_artifacts=True`, which keeps the bind manifest; a later `bind()` prunes everything that manifest
  names — including the vendored trees a real v2 install keeps. The "bind over v2" tests passed against a
  state no user has until the fixture deleted the manifest (`_install_sh_project`), which is what an
  `install.sh` install looks like: no manifest at all.

