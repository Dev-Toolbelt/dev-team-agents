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
| devteam_credential_read | design-rule | Every read of a credential value goes through creds.get_value, which resolves the layer, checks scope and audits; no caller loads a reference file and resolves the value itself, and no output path carries a value or anything derived from one. The one named exception is `credentials_local` (ADR-0024): it reads the plaintext local file the user owns, returns it default-deny redacted, and its `hash` is a machine-keyed HMAC, not a plain digest a guess can be tested against | (review-only — no regex; the backend read is legitimate inside the resolver and forbidden everywhere else, which no pattern can tell apart; pinned by tests/test_review_regressions.py::DesignRuleTest) | scripts/lib/devteam/creds.py |
| placeholder_anchor | design-rule | A check for a placeholder value anchors on the directive or assignment that holds it, never a whole-file grep, because a file's own comments name its placeholder on purpose and a whole-file match keeps firing after the value goes real | (review-only — no regex; the anchored check and the whole-file grep both contain the placeholder literal, so any pattern that finds one finds the other) | .github/scripts/ci/04-packaging.sh |
| app_support_copy | design-rule | Support text in the desktop app — alert and dialog descriptions, field hints, tooltips, result notes — is at most two lines at the component's width (about 160 characters): what happens and what the user does next, in plain words. Detail the user acts on goes into a list or a plan the UI already shows; rationale goes into a code comment or the docs, never on screen | (review-only — no regex; JSX splits a sentence across lines and interpolations, so a length check would miss the long ones and flag headings) | app/src/renderer/screens/Projects.tsx |
| hook_message_language | design-rule | Every user-facing hook message is rendered through devteam_msg in scripts/hooks/lib/notify.sh; no hook writes its own language case | (review-only — no regex; a regex on the `pt-BR` case label would fire on the canonical function and on uc_message) | scripts/hooks/lib/notify.sh |
| hook_python_argv | code-pattern | Inline python in hooks and scripts receives paths and values as argv (sys.argv) or stdin, never interpolated into the source | `open\(['"]\$` | scripts/hooks/session-start.sh |
| app_write_result_toast | design-rule | In the desktop app, the result of a write action started from a list or toolbar is reported through `toastResult` / `toastFailure` / `toastPartialFailure` / `toastBatch`—never rendered inside a table row or cell. Failures persist until closed; retries pass a stable `id` so they replace the earlier toast. Results of actions inside a dialog or form stay inline (`Problem` / `Notice`) because they belong to that dialog's task | (review-only — no regex; toasts and inline result components are rendered in different functions and contexts, so a pattern cannot distinguish a violation from an intentional inline result in a dialog) | app/src/renderer/toasts.tsx |
| app_drilldown_back | code-pattern | Every detail screen in the desktop app returns to its list through `BackNav`, and a screen inside a tab that must reset when the tab is left uses `useOnDeactivate(active, callback)` rather than its own wasActive ref/effect | `wasActive\.current\s*&&\s*!active` | app/src/renderer/BackNav.tsx, app/src/renderer/useOnDeactivate.ts |

Nine are `design-rule`, deliberately. The two `code-pattern` rows have a violation that is a visible literal `scripts/reuse-lint.sh` can match: `hook_python_argv` a shell value inside python source, `app_drilldown_back` a hand-rolled leave-the-tab edge (`wasActive.current && !active`) — the activation edge `Projects.tsx` uses to refetch (`active && !wasActive.current`) is deliberately not matched. For the five `devteam_*` rows, each one's violation is the
*absence* of a call, or an ordering across functions, and a regex that tried to catch either would
fire on the legitimate uses in `versions.py` and `lock.py`. A noisy rule gets disabled; a
review-only rule gets read. The
enforcement is the review gate in `skills/shared/reuse-guidelines/SKILL.md`. The first three rows
are each covered by a named test in `tests/test_review_regressions.py`; `devteam_record_class` is
covered by `tests/test_machine_layout.py::test_every_machine_local_resolver_agrees_on_the_subtree`,
which is the same shape of guard — it asserts that the resolvers agree, not that any one caller
spelled the check correctly.

`devteam_credential_read` earns its row on the same test the row above it passed: the violating
variant reads as ordinary correct code, and the tree already contains the shape it forbids. Inside
the package, `creds.load()` followed by `secrets.get(entry["ref"], entry["source"])` is two
unremarkable lines that hand back the value while skipping both the scope check and the audit line —
and `creds.check()` does exactly that, legitimately, because `devteam doctor` has to probe whether a
value is present without disclosing it or filling the trail with reads nobody asked for. So the
sanctioned bypass and the defect are the same two statements, distinguishable only by which function
they are in: the `devteam_quarantine` situation, where `rmtree` is right for a store-owned version and
wrong for a project path and no pattern can tell them apart. The second half of the rule — no value in
any output path — is what `creds._public_view` exists for, and it is in the row because building a
payload by copying an entry and popping fields is the natural way to write it and fails open the day
the schema grows a field. ADR-0010 is the decision; this row is what stops the next caller from
quietly re-deciding it.

`devteam_record_class` earns its row because the re-derivation is what actually shipped twice: an
export filter testing only the first path component let a plaintext `credentials.local.json` inside
a quarantined memory directory into a **default** archive, and the upgrade's own
`_destination_for` classified `env/credentials.local.json` as portable for the same reason. Both
read as correct path handling. Only "did this caller ask `paths`?" separates them.

`placeholder_anchor` earns its row on evidence from one session, in both directions.
`.github/scripts/ci/04-packaging.sh`'s sha256 advisory grepped the whole of
`packaging/homebrew/devteam.rb` for `REPLACE_WITH_SHA256_OF_RELEASE_TARBALL` — a string that
formula's header comment names deliberately, as part of a documented decision to use a loud non-hex
placeholder so an unset or stale digest fails loudly instead of quietly verifying the wrong bytes.
Running the real bump script against a copy left the advisory firing while the directive held a real
tag and a real digest, and under that script's own `PROMOTE WHEN` instruction, promoting a permanent
false positive to blocking would have made the build permanently red. The url half of the same check
was correct by accident: `tags/vX.Y.Z.tar.gz` only ever appears on the url line, so one file held a
correct and an incorrect instance of the same check side by side. `packaging/verify-formula-locally.sh`
had already documented the trap and avoided it with the same awk — knowledge that existed in this
repository, in the same session, and did not reach the other file, which is the argument for a
registry row rather than a comment. The shape recurs: `packaging/homebrew/devteam-app.rb` pairs the
identical header comment with `NO_RELEASE_SHA256_DOES_NOT_EXIST_YET`.

Review-only for the reason the rule itself states. The correct check and the defective one both
contain the placeholder literal, so any regex that finds a whole-file grep also finds the anchored
comparison beside it and the header comment that explains both — the rule's own failure mode,
applied to its detection. Nor are the literals enumerable in advance; each new manifest invents its
own. A pattern aimed at the grep call instead would fire on `winget_scaffold`'s legitimate
`grep -rq 'vX\.Y\.Z'` over `packaging/winget/`, which is safe today only because nothing there names
that string in a comment — so the regex would be noisy exactly where the rule is not violated.

`app_support_copy` earns its row on the v2 notice in the bind dialog: four clauses (quarantine, nothing
deleted, memory kept, git's index) in a notice whose whole job is "this will be migrated — review the
plan", written the same week as a plan view that itemises all four. A notice that restates the screen
below it is read once and skimmed forever after, and the explanation that did matter was lost in it.
The rule is about **support** text; a result or plan the user must check line by line is content, not
support, and stays as long as its facts.
