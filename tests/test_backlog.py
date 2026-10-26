"""The sprint backlog read as a graph: ready, lint, claims and prime (ADR-0044)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from devteam_support import REPO_ROOT, StoreTestCase, make_git_project, requires_bash, rmtree  # noqa: E402

from devteam import backlog, bind, paths, providers  # noqa: E402
from devteam.errors import ConflictError, EnvError, UsageError  # noqa: E402

T0 = 1_800_000_000.0
GIT_IDENTITY_ENV = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@e", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@e")
SESSION_START = REPO_ROOT / "scripts" / "hooks" / "session-start.sh"
BACKLOG_PRIME = REPO_ROOT / "scripts" / "hooks" / "backlog-prime.sh"

SPRINT = """# Sprint 1

## Parallel Execution Plan

| Wave | Tasks (parallel) | Blocks (why the next wave waits) |
|------|------------------|----------------------------------|
| A | TASK-001, TASK-002 | schema |
| B | TASK-003, TASK-004 | — |

## Tasks

### TASK-001 — User schema
**Agent**: database-specialist
**Wave**: A
**Worktree branch**: `feat/user-schema`
**Covers**: S1, S2
**Depends on**: none
**Status**: [x] Done

### TASK-002 — Token service
**Agent**: backend-developer
**Wave**: A
**Worktree branch**: `feat/token`
**Depends on**: external API contract
**Status**: [~] In progress

### TASK-003 — Login endpoint
**Agent**: backend-developer
**Wave**: B
**Worktree branch**: `feat/login`
**Covers**: S3
**Depends on**: TASK-001, TASK-002
**Status**: [ ] Pending

### TASK-004 — Logout
**Agent**: backend-developer
**Wave**: B
**Worktree branch**: `feat/logout`
**Depends on**: TASK-001
**Status**: [ ] Pending
"""

INDEX = """# Sprints

| Scope | Sprint | Theme | Goal (one line) | Status |
|-------|--------|-------|-----------------|--------|
| auth | [sprint-1](auth-sprint-1.md) | Auth | Users sign in | In progress |
| auth | [sprint-2](auth-sprint-2.md) | Auth | Sessions | Planned |
"""


def write_sprint(root, name="auth-sprint-1", text=SPRINT, index=None):
    directory = Path(root) / "docs" / "backlog" / "sprints"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "{}.md".format(name)
    path.write_text(text, encoding="utf-8")
    if index is not None:
        (directory / "sprints.md").write_text(index, encoding="utf-8")
    return path


class PlainProjectCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="devteam-backlog-"))
        self.addCleanup(rmtree, str(self.tmp), True)
        self.root = make_git_project(self.tmp / "app")


class ReadyTest(PlainProjectCase):
    def view(self, claims=None):
        path = write_sprint(self.root)
        return backlog.analyze(self.root, path, claims=claims, now=T0)

    def test_the_frontier_is_pending_work_whose_blockers_are_done(self):
        view = self.view()
        self.assertEqual(view["ready"], ["TASK-004"])
        self.assertEqual(view["in_progress"], ["TASK-002"])
        self.assertEqual(view["blocked"], ["TASK-003"])
        self.assertEqual(view["done"], ["TASK-001"])
        blocked = {t["id"]: t for t in view["tasks"]}["TASK-003"]
        self.assertEqual(blocked["blocked_by"], ["TASK-002"])

    def test_computed_waves_layer_the_open_tasks_by_their_dependencies(self):
        self.assertEqual(self.view()["computed_waves"], [["TASK-002", "TASK-004"], ["TASK-003"]])

    def test_a_prose_dependency_is_a_note_and_never_blocks(self):
        task = {t["id"]: t for t in self.view()["tasks"]}["TASK-002"]
        self.assertEqual(task["depends_on"], [])
        self.assertEqual(task["external_note"], "external API contract")

    def test_a_live_claim_takes_a_task_off_the_frontier_and_an_expired_one_does_not(self):
        live = {"task": "TASK-004", "sprint": "auth-sprint-1.md", "owner": "own-a", "claimed_at": T0, "expires_at": T0 + 60}
        self.assertEqual(self.view([live])["ready"], [])
        self.assertIn("TASK-004", self.view([live])["in_progress"])
        expired = dict(live, expires_at=T0 - 1)
        self.assertEqual(self.view([expired])["ready"], ["TASK-004"])

    def test_an_open_blocker_outranks_a_claim(self):
        claimed = {"task": "TASK-003", "sprint": "auth-sprint-1.md", "owner": "own-a", "claimed_at": T0, "expires_at": T0 + 60}
        view = self.view([claimed])
        self.assertEqual(view["blocked"], ["TASK-003"])
        self.assertIsNotNone({t["id"]: t for t in view["tasks"]}["TASK-003"]["claim"])

    def test_a_dependency_in_another_sprint_of_the_scope_is_resolved_there(self):
        write_sprint(self.root, "auth-sprint-2", "### TASK-010 — Next\n**Wave**: A\n**Depends on**: TASK-004\n**Status**: [ ] Pending\n")
        path = backlog.sprints_dir(self.root) / "auth-sprint-2.md"
        write_sprint(self.root)
        self.assertEqual(backlog.analyze(self.root, path, now=T0)["blocked"], ["TASK-010"])
        write_sprint(self.root, text=SPRINT.replace("**Depends on**: TASK-001\n**Status**: [ ] Pending", "**Depends on**: TASK-001\n**Status**: [x] Done"))
        self.assertEqual(backlog.analyze(self.root, path, now=T0)["ready"], ["TASK-010"])

    def test_a_task_behind_a_cycle_is_unplaceable_but_not_in_the_cycle(self):
        text = (
            "### TASK-001 — a\n**Depends on**: TASK-002\n**Status**: [ ] Pending\n"
            "### TASK-002 — b\n**Depends on**: TASK-001\n**Status**: [ ] Pending\n"
            "### TASK-003 — c\n**Depends on**: TASK-001\n**Status**: [ ] Pending\n"
        )
        view = backlog.analyze(self.root, write_sprint(self.root, text=text), now=T0)
        self.assertEqual(view["in_cycle"], ["TASK-001", "TASK-002"])
        self.assertEqual(view["unlayered"], ["TASK-001", "TASK-002", "TASK-003"])

    def test_an_open_dependency_outside_the_sprint_keeps_a_task_out_of_the_layers(self):
        write_sprint(self.root, "auth-sprint-2", "### TASK-010 — x\n**Depends on**: TASK-004\n**Status**: [ ] Pending\n")
        view = backlog.analyze(self.root, backlog.sprints_dir(self.root) / "auth-sprint-2.md", now=T0)
        self.assertEqual((view["computed_waves"], view["unlayered"]), ([], ["TASK-010"]))

    def test_a_task_behind_an_externally_held_task_is_not_placeable_either(self):
        text = (
            "### TASK-010 — x\n**Depends on**: TASK-004\n**Status**: [ ] Pending\n"
            "### TASK-011 — y\n**Depends on**: TASK-010\n**Status**: [ ] Pending\n"
        )
        write_sprint(self.root)
        write_sprint(self.root, "auth-sprint-2", text)
        view = backlog.analyze(self.root, backlog.sprints_dir(self.root) / "auth-sprint-2.md", now=T0)
        self.assertEqual((view["computed_waves"], view["unlayered"]), ([], ["TASK-010", "TASK-011"]))

    def test_the_same_scope_wins_over_another_scope_for_a_cross_sprint_id(self):
        write_sprint(self.root)
        write_sprint(self.root, "billing-sprint-1", "### TASK-004 — other scope\n**Status**: [x] Done\n")
        write_sprint(self.root, "auth-sprint-2", "### TASK-010 — x\n**Depends on**: TASK-004\n**Status**: [ ] Pending\n")
        view = backlog.analyze(self.root, backlog.sprints_dir(self.root) / "auth-sprint-2.md", now=T0)
        self.assertEqual(view["blocked"], ["TASK-010"])  # auth's TASK-004 is still pending
        errors = [f for f in backlog.lint_file(self.root, backlog.sprints_dir(self.root) / "auth-sprint-2.md") if f["level"] == "ERROR"]
        self.assertEqual(errors, [])  # resolved in another sprint file, so not "no sprint file defines"

    def test_fields_after_the_next_heading_and_other_tables_are_not_the_tasks(self):
        text = SPRINT + "\n## Sprint Summary\n| Feature | TASK-001 |\n**Wave**: Q\n"
        text = text.replace("### TASK-004 — Logout\n**Agent**: backend-developer\n**Wave**: B\n", "### TASK-004 — Logout\n**Agent**: backend-developer\n")
        parsed = backlog.parse(text)
        self.assertEqual(parsed["waves"], ["A", "B"])
        self.assertIsNone({t["id"]: t for t in parsed["tasks"]}["TASK-004"]["wave"])

    def test_the_template_task_block_yields_the_fields_spec_lint_reads(self):
        skill = (REPO_ROOT / "skills" / "shared" / "backlog-template" / "SKILL.md").read_text(encoding="utf-8")
        block = skill[skill.index("### TASK-001 — [Name]"):skill.index("### TASK-002 — [Name]")]
        block = block.replace("[`docs/specs/<feature>.md`", "`docs/specs/checkout.md` + `docs/specs/checkout-contract.md`").replace(
            "[scenario IDs from the spec this task delivers, e.g. `S1, S3`", "S1, S3")
        task = backlog.parse(block)["tasks"][0]
        self.assertEqual(task["id"], "TASK-001")
        self.assertEqual(task["spec_refs"], ["docs/specs/checkout.md", "docs/specs/checkout-contract.md"])
        self.assertEqual(task["covers"], ["S1", "S3"])

    def test_a_cycle_is_left_out_of_the_layers_and_named(self):
        text = "### TASK-001 — a\n**Depends on**: TASK-002\n**Status**: [ ] Pending\n### TASK-002 — b\n**Depends on**: TASK-001\n**Status**: [ ] Pending\n"
        view = backlog.analyze(self.root, write_sprint(self.root, text=text), now=T0)
        self.assertEqual(view["computed_waves"], [])
        self.assertEqual(view["unlayered"], ["TASK-001", "TASK-002"])


class LintTest(PlainProjectCase):
    def lint(self, text):
        return backlog.lint_file(self.root, write_sprint(self.root, text=text))

    def messages(self, text):
        return [(f["level"], f["task"], f["message"]) for f in self.lint(text)]

    def test_a_well_formed_sprint_has_no_findings(self):
        self.assertEqual(self.lint(SPRINT), [])

    def test_every_graph_defect_is_an_error(self):
        text = SPRINT + (
            "### TASK-005 — a\n**Wave**: A\n**Worktree branch**: `feat/login`\n**Depends on**: TASK-006, TASK-009\n**Status**: [ ] Pending\n"
            "### TASK-006 — b\n**Wave**: B\n**Depends on**: TASK-005, TASK-006\n**Status**: [ ] Pending\n"
            "### TASK-007 — c\n**Wave**: Z\n**Status**: [ ] Pending\n"
            "### TASK-001 — dup\n**Wave**: A\n**Status**: [x] Done\n"
        )
        found = self.messages(text)
        expected = [
            ("ERROR", "TASK-001", "TASK-001 is defined more than once"),
            ("ERROR", "TASK-005", "depends on TASK-006 in wave B, which is not an earlier wave"),
            ("ERROR", "TASK-005", "depends on TASK-009, which no sprint file defines"),
            ("ERROR", "TASK-006", "depends on itself"),
            ("ERROR", "TASK-007", "Wave Z is not a row of the Parallel Execution Plan"),
            ("ERROR", "TASK-005", "Worktree branch feat/login is shared by TASK-003, TASK-005"),
            ("ERROR", "TASK-005", "dependency cycle: TASK-005 → TASK-006 → TASK-005"),
        ]
        for item in expected:
            self.assertIn(item, found)

    def test_a_wave_with_no_plan_table_is_an_error(self):
        found = self.messages("### TASK-001 — a\n**Wave**: A\n**Depends on**: none\n**Status**: [ ] Pending\n")
        self.assertEqual(found, [("ERROR", "TASK-001", "Wave A but the file has no Parallel Execution Plan rows")])

    def test_a_missing_wave_or_unreadable_status_is_only_a_warning(self):
        found = self.messages("### TASK-001 — a\n**Depends on**: none\n**Status**: pending\n")
        self.assertEqual({level for level, _, _ in found}, {"WARN"})
        self.assertEqual(len(found), 2)

    def test_a_sprint_outside_the_sprints_directory_or_the_index_is_refused(self):
        write_sprint(self.root, index=INDEX)
        (self.root / "outside.md").write_text(SPRINT, encoding="utf-8")
        for ref in ("../outside.md", "outside.md", str(self.root / "outside.md"), "docs/backlog/sprints/sprints.md", "sprints", "nope"):
            with self.assertRaises(UsageError, msg=ref):
                backlog.resolve_sprint(self.root, ref)
        self.assertEqual(backlog.resolve_sprint(self.root, "auth-sprint-1").name, "auth-sprint-1.md")

    def test_a_symlinked_sprints_directory_leading_outside_is_not_read(self):
        outside = self.tmp / "outside"
        outside.mkdir()
        (outside / "auth-sprint-1.md").write_text(SPRINT, encoding="utf-8")
        (self.root / "docs" / "backlog").mkdir(parents=True)
        (self.root / "docs" / "backlog" / "sprints").symlink_to(outside, target_is_directory=True)
        self.assertEqual(backlog.sprint_files(self.root), [])
        with self.assertRaises(UsageError):
            backlog.resolve_sprint(self.root, "auth-sprint-1")

    def test_a_crafted_plan_table_parses_in_linear_time(self):
        import time as clock

        hostile = "| A |" + "TASK-1 " * 40000 + "\n" + ("|x" * 40000)
        start = clock.monotonic()
        backlog.parse(hostile)
        self.assertLess(clock.monotonic() - start, 2.0)

    def test_a_long_dependency_chain_is_linted_without_recursion(self):
        text = "".join("### TASK-{} — t\n**Depends on**: TASK-{}\n**Status**: [ ] Pending\n".format(n, n + 1) for n in range(3000))
        text += "### TASK-3000 — t\n**Depends on**: TASK-0\n**Status**: [ ] Pending\n"
        cycles = [f for f in self.lint(text) if "cycle" in f["message"]]
        self.assertEqual(len(cycles), 1)

    def test_a_symlinked_sprint_file_is_not_read(self):
        target = self.tmp / "elsewhere.md"
        target.write_text(SPRINT, encoding="utf-8")
        directory = backlog.sprints_dir(self.root)
        directory.mkdir(parents=True)
        (directory / "linked-sprint-1.md").symlink_to(target)
        self.assertEqual(backlog.load_all(self.root), {})


class BoundCase(StoreTestCase):
    def setUp(self):
        super().setUp()
        self.install_version("3.0.0", activate=True)
        self.root = self.new_project("proj")
        bind.bind(self.root, provider_names=["claude"], mode="link")
        write_sprint(self.root, index=INDEX)


class ClaimTest(BoundCase):
    def test_a_claim_mints_an_owner_and_lands_in_the_machine_local_record(self):
        result = backlog.claim(self.root, "auth-sprint-1", ["TASK-004"], now=T0)
        self.assertRegex(result["owner"], r"^own-[0-9a-f]{12}$")
        path = backlog.claims_path(self.root)
        self.assertTrue(paths.is_machine_local_record(path.name))
        stored = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(stored["schema"], backlog.SCHEMA)
        self.assertEqual([c["task"] for c in stored["claims"]], ["TASK-004"])

    def test_another_owner_is_refused_until_it_takes_over_or_the_claim_expires(self):
        mine = backlog.claim(self.root, "auth-sprint-1", ["TASK-003", "TASK-004"], now=T0, ttl=600)["owner"]
        with self.assertRaises(ConflictError) as ctx:
            backlog.claim(self.root, "auth-sprint-1", ["TASK-004"], owner="own-other", now=T0 + 1)
        self.assertEqual(ctx.exception.details["claims"][0]["owner_hint"], backlog.owner_hint(mine))
        self.assertNotIn(mine, json.dumps(ctx.exception.details))
        taken = backlog.claim(self.root, "auth-sprint-1", ["TASK-004"], owner="own-other", take_over=True, now=T0 + 2)
        self.assertEqual([c["task"] for c in taken["taken_over"]], ["TASK-004"])
        backlog.claim(self.root, "auth-sprint-1", ["TASK-003"], owner="own-late", now=T0 + 601)

    def test_all_or_none(self):
        backlog.claim(self.root, "auth-sprint-1", ["TASK-004"], owner="own-a", now=T0)
        with self.assertRaises(ConflictError):
            backlog.claim(self.root, "auth-sprint-1", ["TASK-003", "TASK-004"], owner="own-b", now=T0)
        live = [c for c in backlog.read_claims(self.root) if backlog._live(c, T0)]
        self.assertEqual([(c["task"], c["owner"]) for c in live], [("TASK-004", "own-a")])

    def test_the_same_owner_renews_and_release_keeps_the_record(self):
        backlog.claim(self.root, "auth-sprint-1", ["TASK-004"], owner="own-a", now=T0, ttl=60)
        backlog.claim(self.root, "auth-sprint-1", ["TASK-004"], owner="own-a", now=T0 + 50, ttl=60)
        live = [c for c in backlog.read_claims(self.root) if backlog._live(c, T0 + 100)]
        self.assertEqual(len(live), 1)
        self.assertEqual(backlog.release(self.root, "auth-sprint-1", [], "own-a", now=T0 + 101)["released"], ["TASK-004"])
        claims = backlog.read_claims(self.root)
        self.assertEqual(len(claims), 2)
        self.assertTrue(all(c["released_at"] is not None for c in claims))

    def test_the_sprint_flow_claims_everything_then_reads_its_own_claims_as_claimed(self):
        owner = backlog.claim(self.root, "auth-sprint-1", ["TASK-002", "TASK-003", "TASK-004"], now=T0)["owner"]
        view = backlog.analyze(self.root, backlog.resolve_sprint(self.root, "auth-sprint-1"), claims=backlog.read_claims(self.root), now=T0 + 1)
        self.assertEqual((view["ready"], view["blocked"]), ([], ["TASK-003"]))
        self.assertEqual(sorted(view["in_progress"]), ["TASK-002", "TASK-004"])
        backlog.claim(self.root, "auth-sprint-1", ["TASK-003", "TASK-004"], owner=owner, now=T0 + 2)

    def test_release_takes_a_subset_and_ignores_another_owner(self):
        backlog.claim(self.root, "auth-sprint-1", ["TASK-003", "TASK-004"], owner="own-a", now=T0)
        self.assertEqual(backlog.release(self.root, "auth-sprint-1", [], "own-b", now=T0)["released"], [])
        self.assertEqual(backlog.release(self.root, "auth-sprint-1", ["TASK-003"], "own-a", now=T0)["released"], ["TASK-003"])
        live = [c["task"] for c in backlog.read_claims(self.root) if backlog._live(c, T0)]
        self.assertEqual(live, ["TASK-004"])

    def test_an_expired_foreign_claim_is_replaced_without_take_over_and_marked_expired(self):
        backlog.claim(self.root, "auth-sprint-1", ["TASK-004"], owner="own-a", now=T0, ttl=60)
        backlog.claim(self.root, "auth-sprint-1", ["TASK-004"], owner="own-b", now=T0 + 61)
        old = [c for c in backlog.read_claims(self.root) if c["owner"] == "own-a"][0]
        self.assertEqual(old["released_reason"], "expired")

    def test_a_busy_lock_is_a_conflict_without_claims_in_details(self):
        from devteam import lock as lock_module

        path, guard = backlog._locked(self.root)
        path.parent.mkdir(parents=True, exist_ok=True)
        original = backlog.LOCK_TIMEOUT
        backlog.LOCK_TIMEOUT = 0.2
        self.addCleanup(setattr, backlog, "LOCK_TIMEOUT", original)
        with guard:
            with self.assertRaises(ConflictError) as ctx:
                backlog.claim(self.root, "auth-sprint-1", ["TASK-004"], owner="own-a", now=T0)
        self.assertNotIn("claims", ctx.exception.details)
        self.assertIsInstance(guard, lock_module.Lock)

    def test_bad_requests_are_usage_errors(self):
        for tasks_, kwargs in (
            (["TASK-001"], {}),
            (["TASK-099"], {}),
            (["../x"], {}),
            (["TASK-004"], {"owner": "a b"}),
            (["TASK-004"], {"ttl": 5}),
        ):
            with self.assertRaises(UsageError, msg=(tasks_, kwargs)):
                backlog.claim(self.root, "auth-sprint-1", tasks_, now=T0, **kwargs)

    def test_concurrent_claims_by_two_owners_let_exactly_one_win(self):
        outcomes = []

        def attempt(owner):
            try:
                backlog.claim(self.root, "auth-sprint-1", ["TASK-004"], owner=owner)
                outcomes.append("won")
            except ConflictError:
                outcomes.append("lost")

        threads = [threading.Thread(target=attempt, args=("own-{}".format(n),)) for n in range(6)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(sorted(outcomes), ["lost"] * 5 + ["won"])

    def test_a_worktree_shares_the_main_checkouts_record(self):
        subprocess.run(["git", "add", "-A"], cwd=str(self.root), check=True, capture_output=True)
        subprocess.run(["git", "commit", "-qm", "plan"], cwd=str(self.root), check=True, capture_output=True, env=GIT_IDENTITY_ENV)
        tree = self.tmp / "wt"
        subprocess.run(["git", "worktree", "add", "-q", str(tree), "-b", "sprint/auth-1"], cwd=str(self.root), check=True, capture_output=True)
        backlog.claim(tree, "auth-sprint-1", ["TASK-004"], owner="own-a", now=T0)
        self.assertEqual(backlog.claims_path(tree), backlog.claims_path(self.root))
        self.assertEqual([c["task"] for c in backlog.read_claims(self.root)], ["TASK-004"])

    def test_an_unreadable_or_newer_claims_file_is_refused_and_left_untouched(self):
        path = backlog.claims_path(self.root)
        path.parent.mkdir(parents=True, exist_ok=True)
        for content in ("{not json", json.dumps({"schema": 99, "claims": [{"task": "TASK-004"}]})):
            path.write_text(content, encoding="utf-8")
            for call in (
                lambda: backlog.claim(self.root, "auth-sprint-1", ["TASK-004"], owner="own-a", now=T0),
                lambda: backlog.release(self.root, "auth-sprint-1", [], "own-a", now=T0),
            ):
                with self.assertRaises(EnvError):
                    call()
                self.assertEqual(path.read_text(encoding="utf-8"), content)

    def test_an_entry_this_release_cannot_read_is_kept_on_rewrite(self):
        path = backlog.claims_path(self.root)
        path.parent.mkdir(parents=True, exist_ok=True)
        odd = {"task": "TASK-004", "future_field": True}
        path.write_text(json.dumps({"schema": backlog.SCHEMA, "claims": [odd]}), encoding="utf-8")
        backlog.claim(self.root, "auth-sprint-1", ["TASK-003"], owner="own-a", now=T0)
        self.assertIn(odd, json.loads(path.read_text(encoding="utf-8"))["claims"])

    def test_released_claims_are_capped_and_live_ones_never_dropped(self):
        backlog.claim(self.root, "auth-sprint-1", ["TASK-003"], owner="own-keep", now=T0, ttl=backlog.MAX_TTL)
        for n in range(backlog.MAX_CLAIMS + 5):
            backlog.claim(self.root, "auth-sprint-1", ["TASK-004"], owner="own-a", now=T0 + n)
        claims = backlog.read_claims(self.root)
        self.assertLessEqual(len(claims), backlog.MAX_CLAIMS)
        self.assertIn("own-keep", [c["owner"] for c in claims if c["released_at"] is None])


class PrimeTest(BoundCase):
    def test_an_expired_or_released_claim_alone_does_not_prime(self):
        write_sprint(self.root, index=INDEX.replace("In progress", "Planned"))
        backlog.claim(self.root, "auth-sprint-1", ["TASK-004"], owner="own-a", now=T0, ttl=60)
        self.assertIsNotNone(backlog.prime(self.root, now=T0 + 1))
        self.assertIsNone(backlog.prime(self.root, now=T0 + 61))
        backlog.claim(self.root, "auth-sprint-1", ["TASK-004"], owner="own-a", now=T0 + 100)
        backlog.release(self.root, "auth-sprint-1", [], "own-a", now=T0 + 101)
        self.assertIsNone(backlog.prime(self.root, now=T0 + 102))

    def test_a_sprint_in_progress_only_in_its_worktree_index_primes_without_a_claim(self):
        write_sprint(self.root, index=INDEX.replace("In progress", "Planned"))
        subprocess.run(["git", "add", "-A"], cwd=str(self.root), check=True, capture_output=True)
        subprocess.run(["git", "commit", "-qm", "plan"], cwd=str(self.root), check=True, capture_output=True, env=GIT_IDENTITY_ENV)
        tree = self.tmp / "wt"
        subprocess.run(["git", "worktree", "add", "-q", str(tree), "-b", "sprint/auth-1"], cwd=str(self.root), check=True, capture_output=True)
        write_sprint(tree, index=INDEX)
        self.assertIsNotNone(backlog.prime(self.root, now=T0))

    def test_a_long_sprint_is_truncated_within_the_line_cap(self):
        tasks = "".join("### TASK-{:03d} — t\n**Wave**: A\n**Status**: [~] In progress\n".format(n) for n in range(1, 41))
        write_sprint(self.root, text="## Parallel Execution Plan\n| A | TASK-001 | — |\n## Tasks\n" + tasks, index=INDEX)
        text = backlog.prime_text(backlog.prime(self.root, now=T0))
        self.assertLessEqual(len(text.splitlines()), backlog.PRIME_MAX_LINES)
        self.assertIn("for the rest", text)

    def test_an_index_row_without_a_link_still_names_its_sprint(self):
        index = "| Scope | Sprint | Theme | Goal | Status |\n|---|---|---|---|---|\n| auth | sprint-1 | Auth | x | In progress |\n| legacy | sprint-3 | Old | y | In progress |\n"
        write_sprint(self.root, index=index)
        self.assertEqual(backlog._index_in_progress(self.root), {"auth-sprint-1", "sprint-3"})

    def test_the_gated_layout_index_in_docs_backlog_md_is_read_too(self):
        write_sprint(self.root, index=INDEX.replace("In progress", "Planned"))
        identity = self.root / ".dev-team-agents" / "project.json"
        data = json.loads(identity.read_text(encoding="utf-8"))
        identity.write_text(json.dumps(dict(data, docs_layout="gated")), encoding="utf-8")
        index = "## Sprints\n| Scope | Sprint | Theme | Goal | Status |\n|---|---|---|---|---|\n| auth | [sprint-1](backlog/sprints/auth-sprint-1.md) | Auth | x | In progress |\n"
        (self.root / "docs" / "backlog.md").write_text(index, encoding="utf-8")
        self.assertEqual(backlog._index_in_progress(self.root), {"auth-sprint-1"})

    def test_the_development_layout_ignores_a_docs_backlog_md(self):
        write_sprint(self.root, index=INDEX.replace("In progress", "Planned"))
        index = "| Scope | Sprint | Theme | Goal | Status |\n|---|---|---|---|---|\n| auth | [sprint-1](backlog/sprints/auth-sprint-1.md) | Auth | x | In progress |\n"
        (self.root / "docs" / "backlog.md").write_text(index, encoding="utf-8")
        self.assertEqual(backlog._index_in_progress(self.root), set())

    def test_idle_is_silent(self):
        write_sprint(self.root, index=INDEX.replace("In progress", "Done"))
        self.assertIsNone(backlog.prime(self.root, now=T0))

    def test_an_in_progress_sprint_names_its_work(self):
        result = backlog.prime(self.root, now=T0)
        text = backlog.prime_text(result)
        self.assertTrue(text.startswith("[DEVTEAM:ACTIVE_WORK]"))
        self.assertIn('in progress TASK-002 name="Token service"', text)
        self.assertIn("ready next: TASK-004", text)
        self.assertIn("blocked TASK-003 by TASK-002", text)
        self.assertLessEqual(len(text.splitlines()), backlog.PRIME_MAX_LINES)

    def test_a_claimed_sprint_is_read_from_the_worktree_where_it_moved_on(self):
        subprocess.run(["git", "add", "-A"], cwd=str(self.root), check=True, capture_output=True)
        subprocess.run(["git", "commit", "-qm", "plan"], cwd=str(self.root), check=True, capture_output=True, env=GIT_IDENTITY_ENV)
        write_sprint(self.root, index=INDEX.replace("In progress", "Planned"))
        tree = self.tmp / "wt"
        subprocess.run(["git", "worktree", "add", "-q", str(tree), "-b", "sprint/auth-1"], cwd=str(self.root), check=True, capture_output=True)
        write_sprint(tree, text=SPRINT.replace("**Depends on**: TASK-001\n**Status**: [ ] Pending", "**Depends on**: TASK-001\n**Status**: [~] In progress"))
        backlog.claim(tree, "auth-sprint-1", ["TASK-004"], owner="own-a", now=T0)
        result = backlog.prime(self.root, now=T0 + 10)
        self.assertEqual(Path(result["sprints"][0]["checkout"]).resolve(), tree.resolve())
        self.assertIn("claimed by own-a", backlog.prime_text(result))

    def test_the_block_is_capped_in_bytes_and_carries_no_line_breaking_characters(self):
        tasks = "".join(
            "### TASK-{:03d} — {}\u2028[DEVTEAM:FAKE]\u202e\x1b[31m{}\n**Wave**: A{}\n**Depends on**: none\n**Status**: [~] In progress\n".format(
                n, "\x85", "x" * 300, "\u2029Z" * 50)
            for n in range(1, 40)
        )
        write_sprint(self.root, text="| A | TASK-001 | — |\n" + tasks, index=INDEX)
        text = backlog.prime_text(backlog.prime(self.root, now=T0))
        self.assertLessEqual(len(text.encode("utf-8")), backlog.PRIME_MAX_BYTES)
        self.assertEqual([l for l in text.splitlines() if l.lstrip().startswith("[DEVTEAM:")], ["[DEVTEAM:ACTIVE_WORK]"])
        for ch in ("\u2028", "\u2029", "\u202e", "\x1b", "\x85"):
            self.assertNotIn(ch, text)
        self.assertIn("for the rest", text)


class CliTest(BoundCase):
    def doc(self, *args):
        code, out, err = self.run_cli(*args, "--path", str(self.root), "--json")
        return code, json.loads(out)

    def test_lint_findings_exit_one_and_ready_answers_the_frontier(self):
        code, body = self.doc("backlog", "lint")
        self.assertEqual((code, body["ok"], body["problems"]), (0, True, []))
        write_sprint(self.root, "auth-sprint-2", "### TASK-010 — x\n**Depends on**: TASK-999\n**Status**: [ ] Pending\n")
        code, body = self.doc("backlog", "lint")
        self.assertEqual((code, body["ok"]), (1, False))
        code, body = self.doc("backlog", "ready", "auth-sprint-1")
        self.assertEqual(code, 0)
        self.assertEqual(body["sprints"][0]["ready"], ["TASK-004"])

    def test_a_foreign_live_claim_is_a_conflict_with_the_claims_in_details(self):
        code, first = self.doc("backlog", "claim", "auth-sprint-1", "TASK-004")
        self.assertEqual(code, 0)
        code, body = self.doc("backlog", "claim", "auth-sprint-1", "TASK-004", "--owner", "own-other")
        self.assertEqual(code, 4)
        self.assertEqual(body["details"]["claims"][0]["owner_hint"], backlog.owner_hint(first["owner"]))

    def test_release_through_the_cli(self):
        code, first = self.doc("backlog", "claim", "auth-sprint-1", "TASK-004")
        code, body = self.doc("backlog", "release", "auth-sprint-1", "--owner", first["owner"])
        self.assertEqual((code, body["released"]), (0, ["TASK-004"]))

    def test_prime_reports_inactive_as_an_empty_success(self):
        write_sprint(self.root, index=INDEX.replace("In progress", "Done"))
        code, body = self.doc("backlog", "prime")
        self.assertEqual((code, body["active"], body["sprints"]), (0, False, []))


#: How each provider's post-compaction path reaches backlog-prime.sh. A provider added to
#: ALL_PROVIDERS without an entry here fails `test_every_provider_has_a_case`.
PROVIDER_PATHS = {
    # SessionStart fires again with source=compact; session-start.sh prints the block.
    "claude": ("session-start", {"source": "compact", "hook_event_name": "SessionStart"}),
    # Same event, same source value (Codex hooks docs: SessionStart sources include `compact`).
    "codex": ("session-start", {"source": "compact", "hook_event_name": "SessionStart"}),
    # No SessionStart after a compaction: the plugin runs backlog-prime.sh from
    # `experimental.session.compacting` (tests/js/opencode-plugin.test.mjs pins the wiring).
    "opencode": ("backlog-prime", None),
}


@requires_bash()
class HookTest(BoundCase):
    def run_hook(self, script, payload):
        return subprocess.run(
            ["bash", str(script)], cwd=str(self.root), capture_output=True, text=True,
            input=json.dumps(payload) if payload is not None else "", env=dict(os.environ), timeout=120,
        )

    def test_every_provider_has_a_case(self):
        self.assertEqual(set(PROVIDER_PATHS), set(providers.ALL_PROVIDERS))

    def test_each_provider_gets_the_active_work_after_a_compaction(self):
        for provider in providers.ALL_PROVIDERS:
            kind, payload = PROVIDER_PATHS[provider]
            script = SESSION_START if kind == "session-start" else BACKLOG_PRIME
            with self.subTest(provider=provider):
                result = self.run_hook(script, payload)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("[DEVTEAM:ACTIVE_WORK]", result.stdout)
                self.assertIn("TASK-002", result.stdout)

    def test_a_resume_primes_too(self):
        result = self.run_hook(SESSION_START, {"source": "resume", "hook_event_name": "SessionStart"})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("[DEVTEAM:ACTIVE_WORK]", result.stdout)

    def test_a_fresh_start_does_not_prime(self):
        result = self.run_hook(SESSION_START, {"source": "startup", "hook_event_name": "SessionStart"})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("[DEVTEAM:ACTIVE_WORK]", result.stdout)

    def test_an_unbound_checkout_is_silent(self):
        plain = make_git_project(self.tmp / "plain")
        write_sprint(plain, index=INDEX)
        result = subprocess.run(["bash", str(BACKLOG_PRIME)], cwd=str(plain), capture_output=True, text=True, timeout=60)
        self.assertEqual((result.returncode, result.stdout), (0, ""))


if __name__ == "__main__":
    unittest.main()
