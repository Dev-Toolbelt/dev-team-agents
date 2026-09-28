# Reuse Guidelines

Mandatory reuse and standardization rules for this repository. Format, column meanings and the
review/lint gates: `skills/shared/reuse-guidelines/SKILL.md`.

A rule belongs here only when it is **not derivable from the code** and **will still be true after
this sprint**. One-off preferences do not.

| name | type | rule | detection | canonical_ref |
|------|------|------|-----------|---------------|
| devteam_containment | design-rule | Every write or removal of a project path in the devteam CLI calls require_inside first, and directories are created component by component so a symlinked ancestor cannot relocate the write | (review-only — no regex; a correct helper that nobody calls is the failure mode, so verify the call site, not the helper) | scripts/lib/devteam/bind.py |
| devteam_quarantine | design-rule | Retired project content is moved with quarantine.move; only a symlink may be unlinked, because sync regenerates it and it holds no content | (review-only — no regex; rmtree is legitimate for store-owned versions and forbidden for project paths, which no pattern can tell apart) | skills/shared/setup-health-check/SKILL.md#no-destruction-rule |
| devteam_store_write | design-rule | Every store mutation goes through jsonio.write_json_atomic inside a store_lock, in registry-then-core order | (review-only — no regex; the lock and the write are in different statements and the order only matters across functions) | scripts/lib/devteam/jsonio.py |
| devteam_record_class | design-rule | Every caller asks paths.is_machine_local_record or paths.path_is_machine_local which subtree a record belongs in; no caller re-derives the classification from a basename, a dot prefix or a first path component | (review-only — no regex; the failure is the absence of a call, and the ad-hoc test that replaces it is indistinguishable from ordinary path handling) | scripts/lib/devteam/paths.py |

All four are `design-rule`, deliberately: each one's violation is the *absence* of a call, or an
ordering across functions, and a regex that tried to catch either would fire on the legitimate uses
in `versions.py` and `lock.py`. A noisy rule gets disabled; a review-only rule gets read. The
enforcement is the review gate in `skills/shared/reuse-guidelines/SKILL.md`. The first three rows
are each covered by a named test in `tests/test_review_regressions.py`; `devteam_record_class` is
covered by `tests/test_machine_layout.py::test_every_machine_local_resolver_agrees_on_the_subtree`,
which is the same shape of guard — it asserts that the resolvers agree, not that any one caller
spelled the check correctly.

`devteam_record_class` earns its row because the re-derivation is what actually shipped twice: an
export filter testing only the first path component let a plaintext `credentials.local.json` inside
a quarantined memory directory into a **default** archive, and the upgrade's own
`_destination_for` classified `env/credentials.local.json` as portable for the same reason. Both
read as correct path handling. Only "did this caller ask `paths`?" separates them.
