"""The PR/MR Created column and the issue references of the task board (ADR-0018 amendment).

A PR/MR mark is recorded only when a tool RESULT confirms the creation, its tasks are fixed at the
next Stop, and the column is derived on read (never stored): In Review beats PR/MR Created beats
Done, a merge seen in any session of the project moves the tasks to Done. Links are stored as
validated parts and rebuilt (and re-validated against the current remotes and integration config)
on every read. These tests drive the record/mark/collect path, the bash gates and every provider's
hook wiring.
"""

import contextlib
import json
import os
import re
import shutil
import subprocess
import time
import sys
import unittest
from pathlib import Path
from unittest import mock

from devteam_support import CLI, REPO_ROOT, StoreTestCase, make_git_project, requires_bash

from devteam import hooks, pr_refs, providers, tasks

import test_tasks as tt
from test_review_board import PROMPT_DISPATCHER, ReviewCase, claude_return, claude_spawn, marker
from test_tasks import POST_DISPATCHER, POST_TOOL_USE, STOP_SUB, T0, codex_plan, opencode_todos, todo, todo_write

HOOKS = REPO_ROOT / "scripts" / "hooks"
PR_SUB = HOOKS / "post-tool-use" / "02-pr-created.sh"
ISSUE_SUB = HOOKS / "user-prompt-submit" / "02-issue-refs.sh"
PR = "https://github.com/o/r/pull/12"
MR = "https://gitlab.example.com/grp/sub/repo/-/merge_requests/4"
JIRA_CFG = {"account": {"site_url": "https://acme.atlassian.net"}, "project": {"project_key": "PROJ"}}
GITHUB_CFG = {"account": {"api_url": "https://api.github.com"}, "project": {"repository": "o/r"}}


def claude_bash(session, command, stdout="", cwd="", event="PostToolUse", error=None):
    payload = {
        "session_id": session, "cwd": cwd, "hook_event_name": event, "tool_name": "Bash",
        "tool_input": {"command": command},
    }
    if error is not None:
        payload["error"] = error
    else:
        payload["tool_response"] = {"stdout": stdout, "stderr": "", "interrupted": False}
    return payload


def codex_bash(session, command, stdout="", cwd=""):
    # Codex `exec_command`: `tool_name: "Bash"`, the command in `tool_input`, `tool_response` a JSON STRING.
    return {
        "session_id": session, "turn_id": "t1", "cwd": cwd, "hook_event_name": "PostToolUse", "tool_name": "Bash",
        "tool_input": {"command": command}, "tool_use_id": "u1", "tool_response": json.dumps(stdout),
    }


def opencode_bash(session, command, stdout="", cwd=""):
    return {"sessionID": session, "tool": "bash", "tool_use_id": "c1", "cwd": cwd, "args": {"command": command}, "output": stdout}


def mcp_create(number=5, repo="o/r", **extra):
    body = {"number": number, "html_url": "https://github.com/{}/pull/{}".format(repo, number), "head": {"ref": "feat/mcp"}}
    body.update(extra)
    return body


def git(root, *args):
    return subprocess.run(
        ["git", *args], cwd=str(root), check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        env=dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@e", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@e"),
    ).stdout.decode().strip()


@contextlib.contextmanager
def integrations(jira=None, github=None):
    def fake(root, name):
        return {"jira": jira, "github": github}[name]

    with mock.patch("devteam.integrations.link_config", side_effect=fake):
        yield


class PrCase(ReviewCase):
    """Session ``s1``: A completed at T0+10, B pending; the project's origin is github.com/o/r."""

    def setUp(self):
        super().setUp()
        git(self.root, "remote", "add", "origin", "https://github.com/o/r.git")

    def begin(self, session="s1", now=T0):
        self.rec(todo_write(session, [todo("A", "in_progress"), todo("B")]), now=now)
        self.rec(todo_write(session, [todo("A", "completed"), todo("B")]), now=now + 10)

    def create(self, session="s1", url=PR, now=T0 + 20, command="gh pr create --fill", cwd=""):
        return self.rec(claude_bash(session, command, url + "\n", cwd=cwd), now=now)

    def stop_idle(self, session="s1", now=T0 + 30):
        return tasks.mark(self.root, {"session_id": session}, "idle", now=now)

    def prs(self, session="s1"):
        return self.load(session).get("prs", [])

    def task(self, content="A", now=T0 + 40, session="s1"):
        return {t["content"]: t for t in self.session(now, session)["tasks"]}[content]

    def edit(self, session, fn):
        rec = self.load(session)
        fn(rec)
        self.save(session, rec)


class CreationTest(PrCase):
    def test_gh_pr_create_records_a_mark_of_parts_never_a_url(self):
        self.begin()
        out = self.create(command="gh pr create --head feat/x --fill")
        self.assertEqual((out["recorded"], out["event"], out["session"]), (True, "pr_created", "s1"))
        (mark,) = self.prs()
        self.assertEqual(
            {k: mark[k] for k in ("id", "kind", "host", "repo", "number", "head", "source", "seen_at", "fixed_at", "task_keys")},
            {"id": "p1", "kind": "pr", "host": "github.com", "repo": "o/r", "number": 12, "head": "feat/x", "source": "gh",
             "seen_at": T0 + 20, "fixed_at": None, "task_keys": []},
        )
        self.assertNotIn("url", mark)
        self.assertNotIn("https://", json.dumps(self.prs()))

    def test_the_url_comes_only_from_the_result_never_from_the_command(self):
        self.begin()
        self.rec(claude_bash("s1", "gh pr create --body https://github.com/o/r/pull/99", "no url printed\n"), now=T0 + 20)
        self.assertEqual(self.prs(), [])
        self.rec(claude_bash("s1", "echo " + PR + " # gh pr create", PR + "\n"), now=T0 + 21)
        self.assertEqual(self.prs(), [])

    def test_the_head_is_the_branch_of_the_project_checkout_when_no_flag_names_it(self):
        self.begin()
        git(self.root, "checkout", "-q", "-b", "feature/mine")
        self.create(cwd=str(self.root))
        self.assertEqual(self.prs()[0]["head"], "feature/mine")

    def test_a_cwd_outside_the_project_root_is_not_trusted(self):
        self.begin()
        other = make_git_project(self.tmp / "other")
        git(other, "checkout", "-q", "-b", "evil/branch")
        self.create(cwd=str(other))
        self.assertIsNone(self.prs()[0]["head"])

    def test_a_linked_worktree_of_the_project_is_trusted_and_a_detached_head_is_not_a_branch(self):
        self.begin()
        wt = self.tmp / "wt"
        git(self.root, "worktree", "add", "-q", "-b", "wt-branch", str(wt))
        self.create(cwd=str(wt))
        self.assertEqual(self.prs()[0]["head"], "wt-branch")
        git(self.root, "checkout", "-q", "--detach")
        self.create(url="https://github.com/o/r/pull/13", cwd=str(self.root), now=T0 + 25)
        self.assertIsNone(self.prs()[1]["head"])

    def test_the_same_url_twice_is_one_mark(self):
        self.begin()
        self.create()
        again = self.create(now=T0 + 25)
        self.assertEqual((again["recorded"], again["event"]), (False, None))
        self.assertEqual(len(self.prs()), 1)

    def test_exactly_one_distinct_url_is_required(self):
        self.begin()
        text = "{}\nhttps://github.com/o/r/pull/13\n".format(PR)
        self.rec(claude_bash("s1", "gh pr create", text), now=T0 + 20)
        self.assertEqual(self.prs(), [])
        self.rec(claude_bash("s1", "gh pr create", "see {} for details\n".format(PR)), now=T0 + 21)
        self.assertEqual(self.prs(), [])

    def test_a_url_whose_repository_is_not_a_remote_is_ignored(self):
        self.begin()
        for url in ("https://github.com/evil/repo/pull/1", "https://gitlab.com/o/r/-/merge_requests/1", "https://evil.example/o/r/pull/1"):
            self.assertFalse(self.create(url=url)["recorded"], url)
        self.assertEqual(self.prs(), [])

    def test_every_remote_url_form_matches(self):
        self.begin()
        for n, remote in enumerate((
            "git@github.com:O/R.git", "ssh://git@github.com/o/r.git", "https://GitHub.com/O/R", "https://tok@github.com/o/R.git/",
        ), start=20):
            git(self.root, "remote", "set-url", "origin", remote)
            out = self.create(url="https://github.com/o/r/pull/{}".format(n), now=T0 + n)
            self.assertEqual(out["event"], "pr_created", remote)

    def test_any_remote_of_the_project_matches_not_only_origin(self):
        self.begin()
        git(self.root, "remote", "add", "upstream", "git@github.com:up/stream.git")
        self.assertTrue(self.create(url="https://github.com/up/stream/pull/3")["recorded"])

    def test_a_command_that_aims_the_tool_elsewhere_never_marks(self):
        self.begin()
        for command in ("PATH=/tmp gh pr create", "GH_HOST=evil.example gh pr create", "gh(){ :; }; gh pr create", "alias gh=true; gh pr create"):
            self.assertFalse(self.create(command=command)["recorded"], command)
        self.assertEqual(self.prs(), [])

    def test_the_already_exists_failure_links_the_existing_pr(self):
        self.begin()
        error = 'Exit code 1\na pull request for branch "feat/x" into branch "main" already exists:\n{}\n'.format(PR)
        out = self.rec(claude_bash("s1", "gh pr create --fill", error=error, event="PostToolUseFailure"), now=T0 + 20)
        self.assertEqual(out["event"], "pr_created")
        self.assertEqual((self.prs()[0]["number"], self.prs()[0]["source"]), (12, "gh"))

    def test_a_failed_create_without_a_url_records_nothing(self):
        self.begin()
        out = self.rec(claude_bash("s1", "gh pr create", error="Exit code 1\nHTTP 422: Validation Failed", event="PostToolUseFailure"), now=T0 + 20)
        self.assertFalse(out["recorded"])
        self.assertEqual(self.prs(), [])

    def test_glab_mr_create_with_subgroups_and_a_self_hosted_remote(self):
        self.begin()
        git(self.root, "remote", "set-url", "origin", "git@gitlab.example.com:grp/sub/repo.git")
        out = self.rec(claude_bash("s1", "glab mr create --source-branch feat/m --fill", MR + "\n"), now=T0 + 20)
        self.assertEqual(out["event"], "pr_created")
        (mark,) = self.prs()
        self.assertEqual((mark["kind"], mark["host"], mark["repo"], mark["number"], mark["head"], mark["source"]),
                         ("mr", "gitlab.example.com", "grp/sub/repo", 4, "feat/m", "glab"))

    def test_a_gh_command_that_printed_an_mr_url_is_not_a_mark(self):
        self.begin()
        git(self.root, "remote", "set-url", "origin", "git@gitlab.example.com:grp/sub/repo.git")
        self.assertFalse(self.rec(claude_bash("s1", "gh pr create", MR + "\n"), now=T0 + 20)["recorded"])

    def test_mcp_create_pull_request_in_every_response_shape(self):
        self.begin()
        body = mcp_create(number=5)
        shapes = (
            body,
            {"content": [{"type": "text", "text": json.dumps(mcp_create(number=6))}]},
            {"structuredContent": mcp_create(number=7), "content": []},
        )
        for n, response in enumerate(shapes):
            out = self.rec({"session_id": "s1", "tool_name": "mcp__github__create_pull_request", "tool_input": {"head": "feat/in"}, "tool_response": response}, now=T0 + 20 + n)
            self.assertEqual(out["event"], "pr_created", n)
        marks = self.prs()
        self.assertEqual([(m["number"], m["source"], m["head"]) for m in marks], [(5, "mcp", "feat/mcp"), (6, "mcp", "feat/mcp"), (7, "mcp", "feat/mcp")])

    def test_mcp_error_mismatch_and_free_text_are_ignored(self):
        self.begin()
        for response in (
            dict(mcp_create(), isError=True),
            mcp_create(html_url="https://github.com/o/r/pull/9"),
            mcp_create(repo="evil/repo"),
            {"content": [{"type": "text", "text": "Created " + PR}]},
        ):
            out = self.rec({"session_id": "s1", "tool_name": "mcp__github__create_pull_request", "tool_input": {}, "tool_response": response}, now=T0 + 20)
            self.assertFalse(out["recorded"], response)
        self.assertEqual(self.prs(), [])

    def test_no_record_for_the_session_means_no_file_and_no_mark(self):
        out = self.create(session="ghost")
        self.assertFalse(out["recorded"])
        self.assertFalse(tasks.record_path(self.root, self.project_id, "ghost").exists())

    def test_the_cap_of_twenty_marks(self):
        self.begin()
        for n in range(1, 26):
            self.create(url="https://github.com/o/r/pull/{}".format(n), now=T0 + 20 + n)
        self.assertEqual(len(self.prs()), tasks.MAX_PRS)
        self.assertEqual(tasks.MAX_PRS, 20)
        self.assertEqual([p["number"] for p in self.prs()][-1], 20)


class ProviderPayloadTest(PrCase):
    """Every provider's own payload shape reaches the same mark (iterates ALL_PROVIDERS)."""

    SESSIONS = {"claude": "pc", "codex": "px", "opencode": "po"}
    RECORDS = {
        "claude": lambda s: todo_write(s, [todo("A", "in_progress")]),
        "codex": lambda s: codex_plan(s, [("A", "in_progress")]),
        "opencode": lambda s: opencode_todos(s, [("a", "A", "in_progress")]),
    }
    BASH = {"claude": claude_bash, "codex": codex_bash, "opencode": opencode_bash}

    def test_every_provider_has_a_case(self):
        for table in (self.SESSIONS, self.RECORDS, self.BASH):
            self.assertEqual(set(table), set(providers.ALL_PROVIDERS))

    def test_a_confirmed_creation_and_a_merge_are_recorded_for_each_provider(self):
        for provider in providers.ALL_PROVIDERS:
            session = self.SESSIONS[provider]
            self.rec(self.RECORDS[provider](session), now=T0)
            bash = self.BASH[provider]
            out = self.rec(bash(session, "gh pr create --fill", PR + "\n", cwd=str(self.root)), now=T0 + 20)
            self.assertEqual(out["event"], "pr_created", provider)
            self.assertEqual(self.load(session)["prs"][0]["number"], 12, provider)
            out = self.rec(bash(session, "gh pr merge 12 --squash", "✓ Squashed and merged pull request #12 (t)\n", cwd=str(self.root)), now=T0 + 40)
            self.assertEqual(out["event"], "pr_merged", provider)
            self.assertEqual(self.load(session)["merges"][0]["number"], 12, provider)

    def test_an_unrelated_command_is_not_recorded_by_any_provider(self):
        for provider in providers.ALL_PROVIDERS:
            session = self.SESSIONS[provider]
            self.rec(self.RECORDS[provider](session), now=T0)
            out = self.rec(self.BASH[provider](session, "echo " + PR, PR + "\n"), now=T0 + 20)
            self.assertFalse(out["recorded"], provider)
            self.assertNotIn("prs", self.load(session), provider)

    def test_opencode_mcp_create_uses_args_and_output_and_a_stringified_result(self):
        self.rec(self.RECORDS["opencode"]("po"), now=T0)
        out = self.rec({"sessionID": "po", "tool": "github_create_pull_request", "args": {"head": "feat/oc"}, "output": json.dumps(mcp_create(number=8))}, now=T0 + 20)
        self.assertEqual(out["event"], "pr_created")
        self.assertEqual(self.load("po")["prs"][0]["head"], "feat/mcp")

    def test_codex_mcp_create_uses_a_serialized_call_tool_result(self):
        self.rec(self.RECORDS["codex"]("px"), now=T0)
        response = {"content": [{"type": "text", "text": json.dumps(mcp_create(number=9))}], "isError": False}
        out = self.rec({"session_id": "px", "tool_name": "mcp__github__create_pull_request", "tool_input": {}, "tool_response": json.dumps(response)}, now=T0 + 20)
        self.assertEqual((out["event"], self.load("px")["prs"][0]["number"]), ("pr_created", 9))


class MembershipTest(PrCase):
    def test_membership_is_fixed_at_the_next_stop(self):
        self.begin()
        self.create()
        self.assertEqual(self.task(now=T0 + 25)["column"], "done")
        self.assertEqual(self.prs()[0]["task_keys"], [])
        out = self.stop_idle()
        self.assertEqual(out["pr_marks"], [{"kind": "pr", "number": 12, "url": PR}])
        (mark,) = self.prs()
        self.assertEqual((mark["fixed_at"], mark["task_keys"]), (T0 + 30, ["t1"]))
        view = self.task()
        self.assertEqual(view["column"], "pr_created")
        self.assertEqual(view["pr"], {"kind": "pr", "number": 12, "url": PR, "state": "open"})
        self.assertEqual(self.task("B")["column"], "todo")
        self.assertIsNone(self.task("B")["pr"])

    def test_a_task_completed_after_the_stop_goes_to_done_not_to_the_pr(self):
        self.begin()
        self.create()
        self.stop_idle()
        self.rec(todo_write("s1", [todo("A", "completed"), todo("B", "completed")]), now=T0 + 40)
        self.assertEqual((self.task("A", now=T0 + 50)["column"], self.task("B", now=T0 + 50)["column"]), ("pr_created", "done"))

    def test_the_first_mark_wins_each_task_belongs_to_at_most_one_pr(self):
        self.begin()
        self.create()
        self.stop_idle()
        self.rec(todo_write("s1", [todo("A", "completed"), todo("B", "completed")]), now=T0 + 40)
        self.create(url="https://github.com/o/r/pull/13", now=T0 + 50)
        self.stop_idle(now=T0 + 60)
        first, second = self.prs()
        self.assertEqual((first["task_keys"], second["task_keys"]), (["t1"], ["t2"]))

    def test_two_marks_in_one_stop_the_first_takes_the_tasks(self):
        self.begin()
        self.create()
        self.create(url="https://github.com/o/r/pull/13", now=T0 + 21)
        out = self.stop_idle()
        self.assertEqual([m["number"] for m in out["pr_marks"]], [12, 13])
        first, second = self.prs()
        self.assertEqual((first["task_keys"], second["task_keys"]), (["t1"], []))

    def test_tasks_completed_before_the_previous_mark_are_not_taken_again(self):
        self.begin()
        self.create()
        self.stop_idle()
        self.create(url="https://github.com/o/r/pull/13", now=T0 + 50)
        self.stop_idle(now=T0 + 60)
        self.assertEqual(self.prs()[1]["task_keys"], [])

    def test_cancelled_removed_and_failed_tasks_never_join(self):
        self.rec(todo_write("s1", [todo("A", "completed"), todo("B", "cancelled"), todo("C", "pending")]), now=T0)
        self.rec(todo_write("s1", [todo("A", "completed"), todo("C", "pending")]), now=T0 + 5)
        self.create()
        self.stop_idle()
        self.assertEqual(self.prs()[0]["task_keys"], ["t1"])

    def test_a_session_without_a_completed_task_fixes_an_empty_mark(self):
        self.rec(todo_write("s1", [todo("A", "in_progress")]), now=T0)
        self.create()
        out = self.stop_idle()
        self.assertEqual(out["pr_marks"][0]["number"], 12)
        self.assertEqual(self.prs()[0]["task_keys"], [])
        self.assertEqual(self.session()["prs"][0]["number"], 12)

    def test_a_stop_with_nothing_unfixed_reports_no_marks_and_a_second_stop_none(self):
        self.begin()
        self.assertEqual(self.stop_idle(now=T0 + 15)["pr_marks"], [])
        self.create()
        self.assertEqual(len(self.stop_idle()["pr_marks"]), 1)
        self.assertEqual(self.stop_idle(now=T0 + 35)["pr_marks"], [])

    def test_a_mark_that_no_longer_validates_at_the_stop_is_fixed_but_not_reported(self):
        self.begin()
        self.create()
        git(self.root, "remote", "remove", "origin")
        out = self.stop_idle()
        self.assertEqual(out["pr_marks"], [])
        self.assertEqual(self.prs()[0]["fixed_at"], T0 + 30)

    def test_the_session_end_does_not_fix_marks(self):
        self.begin()
        self.create()
        out = tasks.mark(self.root, {"session_id": "s1"}, "ended", now=T0 + 30)
        self.assertEqual(out["pr_marks"], [])
        self.assertIsNone(self.prs()[0]["fixed_at"])


class DerivedStateTest(PrCase):
    def held(self):
        """A completed under a findings review (held In Review), a PR created and fixed meanwhile."""
        self.start(items=[todo("A", "completed")])
        self.open(claude_spawn("s1"), now=T0 + 10)
        self.result(claude_return("s1", marker(1)), now=T0 + 15)
        self.create(now=T0 + 20)
        self.stop_idle()

    def release(self, now=T0 + 50):
        self.todos("s1", todo("A", "completed"), todo("Fix", "completed"), now=now)
        self.assertEqual(self.window()["resolution"], "fixed")

    def test_review_beats_pr_created_and_a_released_task_shows_pr_created(self):
        self.held()
        self.assertEqual(self.prs()[0]["task_keys"], ["t1"])
        view = self.task(now=T0 + 40)
        self.assertEqual((view["column"], view["pr"]["state"]), ("in_review", "open"))
        self.release()
        self.assertEqual(self.task(now=T0 + 60)["column"], "pr_created")
        self.assertEqual(self.task("Fix", now=T0 + 60)["column"], "done")

    def test_a_released_task_whose_pr_was_merged_meanwhile_shows_done(self):
        self.held()
        self.rec(claude_bash("s1", "gh pr merge 12", "\u2713 Merged pull request #12\n"), now=T0 + 40)
        self.assertEqual(self.task(now=T0 + 45)["column"], "in_review")
        self.release()
        view = self.task(now=T0 + 60)
        self.assertEqual((view["column"], view["pr"]["state"]), ("done", "merged"))

    def test_durations_are_a_partition_and_in_review_wins_over_pr_created(self):
        self.held()
        self.release()
        d = self.task(now=T0 + 100)["durations"]
        self.assertEqual((d["in_review"], d["pr_created"]), (40, 50))
        self.assertEqual(d["pending"] + d["in_progress"] + d["completed"] + d["in_review"] + d["pr_created"], 100)

    def test_all_done_and_session_done_count_a_pr_task_as_finished(self):
        self.begin()
        self.create()
        self.stop_idle()
        out = self.rec(todo_write("s1", [todo("A", "completed"), todo("B", "completed")]), now=T0 + 40)
        self.assertEqual((out["all_done"], out["became_all_done"]), (True, True))
        listing = self.view(now=T0 + 50)[0]
        self.assertEqual(listing["counts"]["pr_created"], 1)
        self.assertEqual(listing["counts"]["done"], 1)
        self.assertEqual(listing["sessions"][0]["counts"], {"todo": 0, "in_progress": 0, "done": 1, "in_review": 0, "pr_created": 1, "total": 2})

    def test_a_session_that_ends_with_a_pr_task_has_nothing_abandoned_unless_work_is_open(self):
        self.rec(todo_write("s1", [todo("A", "completed")]), now=T0)
        self.create()
        self.stop_idle()
        tasks.mark(self.root, {"session_id": "s1"}, "ended", now=T0 + 40)
        view = self.task(now=T0 + 50)
        self.assertEqual((view["column"], view["abandoned"], view["stale"]), ("pr_created", False, False))
        self.begin("s2")
        self.create("s2", url="https://github.com/o/r/pull/13", now=T0 + 20)
        self.stop_idle("s2")
        tasks.mark(self.root, {"session_id": "s2"}, "ended", now=T0 + 40)
        states = {t["content"]: (t["column"], t["abandoned"]) for t in self.session(T0 + 50, "s2")["tasks"]}
        self.assertEqual(states, {"A": ("pr_created", False), "B": ("todo", True)})

    def test_project_and_session_views_carry_the_additive_fields(self):
        self.begin()
        self.create(command="gh pr create --head feat/x")
        self.stop_idle()
        project = self.view()[0]
        session = project["sessions"][0]
        self.assertEqual(session["prs"], [{"kind": "pr", "number": 12, "url": PR, "state": "open", "head": "feat/x"}])
        self.assertEqual(project["counts"]["pr_created"], 1)
        self.assertEqual({h["host"] for h in project["link_hosts"]}, {"github.com", "gitlab.com"})
        self.assertTrue(all("base_path" not in h for h in project["link_hosts"]))
        self.assertEqual(self.task()["refs"], [])


class MergeTest(PrCase):
    def fixed(self, command="gh pr create --head feat/x"):
        self.begin()
        self.create(command=command)
        self.stop_idle()

    def merge(self, session, command, stdout, now, cwd=None):
        # `git merge` counts only when the checkout it ran in is known and is not the merged branch.
        return self.rec(claude_bash(session, command, stdout, cwd=str(self.root) if cwd is None else cwd), now=now)

    def test_merging_in_the_same_session_moves_the_tasks_to_done_with_a_merged_badge(self):
        self.fixed()
        out = self.merge("s1", "gh pr merge 12 --squash", "✓ Squashed and merged pull request #12 (t)\n", T0 + 60)
        self.assertEqual(out["event"], "pr_merged")
        (entry,) = self.load("s1")["merges"]
        self.assertEqual((entry["kind"], entry["number"], entry["repo"], entry["host"], entry["at"]), ("pr", 12, "o/r", "github.com", T0 + 60))
        view = self.task(now=T0 + 70)
        self.assertEqual((view["column"], view["pr"]["state"]), ("done", "merged"))
        self.assertEqual(self.session(T0 + 70)["prs"][0]["state"], "merged")

    def test_a_merge_in_another_session_joins_by_repo_and_number(self):
        self.fixed()
        self.rec(todo_write("s2", [todo("Other")]), now=T0 + 40)
        self.merge("s2", "gh pr merge 12", "✓ Merged pull request #12\n", T0 + 60)
        self.assertEqual(self.task(now=T0 + 70)["pr"]["state"], "merged")

    def test_a_merge_by_branch_joins_only_at_or_after_the_mark_was_seen(self):
        self.fixed()
        self.rec(todo_write("s2", [todo("Other")]), now=T0)
        self.merge("s2", "git merge feat/x", "Updating a..b\nFast-forward\n", T0 + 5)
        self.assertEqual(self.task(now=T0 + 70)["pr"]["state"], "open")
        self.merge("s2", "git merge origin/feat/x", "Merge made by the 'ort' strategy.\n", T0 + 60)
        self.assertEqual(self.task(now=T0 + 70)["pr"]["state"], "merged")

    def test_catching_a_branch_up_with_its_own_remote_is_not_a_merge(self):
        self.fixed()
        git(self.root, "checkout", "-q", "-b", "feat/x")
        self.assertFalse(self.merge("s1", "git merge origin/feat/x", "Updating a..b\nFast-forward\n", T0 + 60)["recorded"])
        self.assertFalse(self.merge("s1", "git merge feat/x", "Fast-forward\n", T0 + 61, cwd="")["recorded"])
        self.assertNotIn("merges", self.load("s1"))
        self.assertEqual(self.task(now=T0 + 70)["pr"]["state"], "open")

    def test_a_git_merge_records_the_branch_it_merged_into(self):
        self.fixed()
        into = git(self.root, "rev-parse", "--abbrev-ref", "HEAD")
        self.merge("s1", "git merge feat/x", "Fast-forward\n", T0 + 60)
        (entry,) = self.load("s1")["merges"]
        self.assertEqual((entry["branch"], entry["into"]), ("feat/x", into))
        # Write-shaped, but with its output in hand it is a merge, not a turn of direct work.
        self.assertFalse(any(t.get("kind") == "direct" for t in self.load("s1")["tasks"]))
        self.assertEqual(self.task(now=T0 + 70)["pr"]["state"], "merged")

    def test_a_different_number_branch_or_repository_does_not_join(self):
        self.fixed()
        self.merge("s1", "gh pr merge 99", "✓ Merged pull request #99\n", T0 + 60)
        self.merge("s1", "git merge feat/other", "Fast-forward\n", T0 + 61)
        self.merge("s1", "gh pr merge 12 -R o/other", "✓ Merged pull request #12\n", T0 + 62)
        self.assertEqual(self.task(now=T0 + 70)["pr"]["state"], "open")
        self.assertEqual([m["number"] for m in self.load("s1")["merges"] if m["number"]], [99])

    def test_an_ambiguous_remote_set_makes_a_number_only_merge_unjoinable(self):
        self.fixed()
        git(self.root, "remote", "add", "up", "https://github.com/up/stream.git")
        self.merge("s1", "gh pr merge 12", "✓ Merged pull request #12\n", T0 + 60)
        (entry,) = self.load("s1")["merges"]
        self.assertIsNone(entry["repo"])
        self.assertEqual(self.task(now=T0 + 70)["pr"]["state"], "open")

    def test_gh_pr_merge_without_an_argument_uses_the_branch_of_the_checkout(self):
        self.begin()
        git(self.root, "checkout", "-q", "-b", "feat/cur")
        self.create(command="gh pr create --head feat/cur")
        self.stop_idle()
        self.rec(claude_bash("s1", "gh pr merge --squash", "✓ Squashed and merged pull request #12 (t)\n", cwd=str(self.root)), now=T0 + 60)
        self.assertEqual(self.task(now=T0 + 70)["pr"]["state"], "merged")

    def test_glab_mr_merge(self):
        git(self.root, "remote", "set-url", "origin", "https://gitlab.example.com/grp/sub/repo.git")
        self.begin()
        self.rec(claude_bash("s1", "glab mr create --source-branch feat/m", MR + "\n"), now=T0 + 20)
        self.stop_idle()
        self.merge("s1", "glab mr merge 4", "✓ Merged!\n", T0 + 60)
        (entry,) = self.load("s1")["merges"]
        self.assertEqual((entry["kind"], entry["number"], entry["repo"], entry["host"]), ("mr", 4, "grp/sub/repo", "gitlab.example.com"))
        self.assertEqual(self.task(now=T0 + 70)["pr"], {"kind": "mr", "number": 4, "url": MR, "state": "merged"})

    def test_a_merge_of_an_mr_does_not_close_a_pr_with_the_same_number(self):
        self.fixed()
        git(self.root, "remote", "add", "gl", "https://gitlab.example.com/grp/sub/repo.git")
        self.merge("s1", "glab mr merge -R grp/sub/repo 12", "✓ Merged!\n", T0 + 60)
        self.assertEqual(self.task(now=T0 + 70)["pr"]["state"], "open")

    def test_merge_confirmation_rules(self):
        self.fixed()
        for command, stdout in (
            ("gh pr merge 12 --auto", "✓ Pull request #12 will be automatically merged when ready\n"),
            ("gh pr merge 12", "X Pull request #12 is not mergeable\n"),
            ("git merge feat/x", "Already up to date.\n"),
            ("git merge feat/x", "Auto-merging f\nCONFLICT (content): Merge conflict in f\nAutomatic merge failed\n"),
            ("echo gh pr merge 12", "✓ Merged pull request #12\n"),
        ):
            self.assertFalse(self.merge("s1", command, stdout, T0 + 60)["recorded"], command)
        self.assertNotIn("merges", self.load("s1"))

    def test_a_failed_merge_records_nothing(self):
        self.fixed()
        out = self.rec(claude_bash("s1", "gh pr merge 12", error="Exit code 1\n✓ Merged pull request #12\n", event="PostToolUseFailure"), now=T0 + 60)
        self.assertFalse(out["recorded"])
        self.assertNotIn("merges", self.load("s1"))

    def test_mcp_merge_pull_request(self):
        self.fixed()
        payload = {"session_id": "s1", "tool_name": "mcp__github__merge_pull_request", "tool_input": {"owner": "o", "repo": "r", "pullNumber": 12}, "tool_response": {"merged": True}}
        self.assertEqual(self.rec(payload, now=T0 + 60)["event"], "pr_merged")
        self.assertEqual(self.task(now=T0 + 70)["pr"]["state"], "merged")
        failed = dict(payload, tool_response={"merged": False})
        self.assertFalse(self.rec(failed, now=T0 + 61)["recorded"])

    def test_the_cap_of_fifty_merges_keeps_the_latest(self):
        self.fixed()
        for n in range(60):
            self.merge("s1", "git merge branch-{}".format(n), "Fast-forward\n", T0 + 100 + n)
        merges = self.load("s1")["merges"]
        self.assertEqual((len(merges), merges[0]["branch"], merges[-1]["branch"]), (tasks.MAX_MERGES, "branch-10", "branch-59"))
        self.assertEqual(tasks.MAX_MERGES, 50)


class StoredPartsTest(PrCase):
    def setUp(self):
        super().setUp()
        self.begin()
        self.create()
        self.stop_idle()
        self.pristine = self.load("s1")

    def test_a_record_edited_to_a_bad_host_is_omitted_but_kept(self):
        self.edit("s1", lambda r: r["prs"][0].update(host="evil.example"))
        view = self.task()
        self.assertEqual((view["column"], view["pr"]), ("done", None))
        self.assertEqual(self.session()["prs"], [])
        self.assertEqual(self.load("s1")["prs"][0]["host"], "evil.example")

    def test_any_corruption_of_the_parts_is_omitted(self):
        for edit in (
            {"number": "12"}, {"number": 0}, {"number": True}, {"repo": "../x"}, {"repo": "o/r/extra"}, {"kind": "issue"},
            {"host": "github.com/evil"}, {"host": "GitHub.com"}, {"url": "https://evil.example/o/r/pull/12", "repo": "o/other"},
        ):
            self.save("s1", self.pristine)
            self.edit("s1", lambda r, e=edit: r["prs"][0].update(e))
            self.assertIsNone(self.task()["pr"], edit)

    def test_a_stored_url_field_is_never_used(self):
        self.edit("s1", lambda r: r["prs"][0].update(url="https://evil.example/x"))
        self.assertEqual(self.task()["pr"]["url"], PR)

    def test_the_mark_is_revalidated_against_the_current_remotes(self):
        git(self.root, "remote", "set-url", "origin", "https://github.com/someone/else.git")
        self.assertIsNone(self.task()["pr"])
        git(self.root, "remote", "set-url", "origin", "https://github.com/o/r.git")
        self.assertEqual(self.task()["pr"]["number"], 12)

    def test_a_merge_entry_with_a_bad_shape_is_skipped(self):
        self.edit("s1", lambda r: r.update(merges=[{"kind": "x", "at": T0}, "nope", {"kind": "pr", "number": 12, "repo": "o/r", "host": "github.com"}]))
        self.assertEqual(self.task()["pr"]["state"], "open")

    def test_a_record_with_a_non_list_pr_section_is_not_loaded_as_a_task_record(self):
        self.edit("s1", lambda r: r.update(prs="nope"))
        self.assertEqual(self.view(), [])


class IssueRefsTest(PrCase):
    def prompt(self, text, session="s1", now=T0 + 50):
        return self.rec({"session_id": session, "cwd": str(self.root), "hook_event_name": "UserPromptSubmit", "prompt": text}, now=now)

    def refs(self, content="A", now=T0 + 100, session="s1"):
        with integrations(JIRA_CFG, GITHUB_CFG):
            return self.task(content, now=now, session=session)["refs"]

    def test_no_integration_means_no_reference_stored_or_shown(self):
        self.begin()
        self.assertFalse(self.prompt("fix PROJ-12 and #4")["recorded"])
        self.assertNotIn("refs", self.load("s1"))
        self.assertEqual(self.task()["refs"], [])

    def test_a_prompt_reference_is_a_session_ref_for_tasks_created_at_or_after_it(self):
        self.rec(todo_write("s1", [todo("Early")]), now=T0)
        with integrations(JIRA_CFG, GITHUB_CFG):
            out = self.prompt("please do PROJ-12 now")
        self.assertEqual((out["recorded"], out["event"]), (True, "refs"))
        self.assertEqual(self.load("s1")["refs"], [{"system": "jira", "key": "PROJ-12", "seen_at": T0 + 50}])
        self.rec(todo_write("s1", [todo("Early"), todo("Late")]), now=T0 + 60)
        self.assertEqual(self.refs("Early"), [])
        self.assertEqual(self.refs("Late"), [{"system": "jira", "key": "PROJ-12", "url": "https://acme.atlassian.net/browse/PROJ-12"}])

    def test_the_task_less_first_prompt_creates_a_record_the_first_task_inherits(self):
        with integrations(JIRA_CFG, GITHUB_CFG):
            out = self.prompt("start PROJ-7 please", session="fresh", now=T0)
            self.assertEqual((out["recorded"], out["event"]), (True, "refs"))
            rec = self.load("fresh")
            self.assertEqual((rec["tasks"], rec["refs"][0]["key"], rec["project_id"]), ([], "PROJ-7", self.project_id))
            self.assertEqual([p for p in self.view(now=T0 + 5) if p["project_id"] == self.project_id], [])
            self.rec(todo_write("fresh", [todo("First")]), now=T0 + 10)
            view = self.view(now=T0 + 20)[0]
        (task,) = view["sessions"][0]["tasks"]
        self.assertEqual([r["key"] for r in task["refs"]], ["PROJ-7"])

    def test_a_first_prompt_without_a_valid_reference_creates_nothing(self):
        with integrations(JIRA_CFG, GITHUB_CFG):
            for text in ("hello", "ADR-0018 and UTF-8", "OTHER-5", "see #12", "SHA-256"):
                self.assertFalse(self.prompt(text, session="fresh", now=T0)["recorded"], text)
        self.assertFalse(tasks.record_path(self.root, self.project_id, "fresh").exists())

    def test_github_forms_in_a_prompt(self):
        self.begin()
        git(self.root, "remote", "add", "up", "https://github.com/acme/web.git")
        with integrations(JIRA_CFG, GITHUB_CFG):
            self.prompt("fixes #12 and acme/web#45 and https://github.com/acme/web/issues/46 and see #99 and evil/x#1")
        found = sorted((r["repo"], r["number"]) for r in self.load("s1")["refs"])
        self.assertEqual(found, [("acme/web", 45), ("acme/web", 46), ("o/r", 12)])
        self.rec(todo_write("s1", [todo("A", "completed"), todo("B"), todo("Late")]), now=T0 + 60)
        self.assertEqual(
            sorted(r["key"] for r in self.refs("Late")),
            ["acme/web#45", "acme/web#46", "o/r#12"],
        )
        self.assertEqual(self.refs("A"), [])

    def test_a_reference_is_stored_once_and_shown_once(self):
        self.begin()
        with integrations(JIRA_CFG, GITHUB_CFG):
            self.prompt("PROJ-1 PROJ-1")
            self.assertFalse(self.prompt("again PROJ-1", now=T0 + 55)["recorded"])
        self.assertEqual(len(self.load("s1")["refs"]), 1)

    def test_the_cap_of_fifty_session_references(self):
        self.begin()
        with integrations(JIRA_CFG, GITHUB_CFG):
            for chunk in range(8):
                self.prompt(" ".join("PROJ-{}".format(chunk * 10 + n + 1) for n in range(10)), now=T0 + 50 + chunk)
        self.assertEqual(len(self.load("s1")["refs"]), tasks.MAX_REFS)
        self.assertEqual(tasks.MAX_REFS, 50)

    def test_the_branch_name_is_a_session_ref_when_the_task_is_first_seen_on_it(self):
        git(self.root, "checkout", "-q", "-b", "feature/PROJ-5-login")
        with integrations(JIRA_CFG, GITHUB_CFG):
            self.rec(todo_write("s1", [todo("A")], cwd=str(self.root)), now=T0)
        self.assertEqual([r["key"] for r in self.load("s1")["refs"]], ["PROJ-5"])
        self.assertEqual([r["key"] for r in self.refs(now=T0 + 10)], ["PROJ-5"])

    def test_task_text_references_apply_to_that_task_only_and_owner_repo_is_bound_to_the_remote(self):
        with integrations(JIRA_CFG, GITHUB_CFG):
            self.rec(todo_write("s1", [todo("Do PROJ-7 and o/r#5 and evil/repo#6"), todo("Plain")]), now=T0)
            view = {t["content"]: t["refs"] for t in self.view(now=T0 + 5)[0]["sessions"][0]["tasks"]}
        self.assertEqual([r["key"] for r in view["Do PROJ-7 and o/r#5 and evil/repo#6"]], ["PROJ-7", "o/r#5"])
        self.assertEqual(view["Plain"], [])

    def test_a_task_text_reference_is_not_rewritten_by_a_later_replace(self):
        with integrations(JIRA_CFG, GITHUB_CFG):
            self.rec(todo_write("s1", [todo("Do PROJ-7")]), now=T0)
            self.rec(todo_write("s1", [todo("Do PROJ-7", "in_progress")]), now=T0 + 5)
            self.assertEqual([r["key"] for r in self.refs("Do PROJ-7", now=T0 + 10)], ["PROJ-7"])

    def test_session_and_task_references_are_deduplicated_by_url(self):
        with integrations(JIRA_CFG, GITHUB_CFG):
            self.prompt("PROJ-7", now=T0 - 1)
            self.rec(todo_write("s1", [todo("Do PROJ-7 and PROJ-8")]), now=T0)
            self.assertEqual([r["key"] for r in self.refs("Do PROJ-7 and PROJ-8", now=T0 + 5)], ["PROJ-7", "PROJ-8"])

    def test_edited_or_orphaned_references_are_omitted_and_urls_are_rebuilt(self):
        with integrations(JIRA_CFG, GITHUB_CFG):
            self.prompt("PROJ-7 fixes #3", now=T0 - 1)
            self.rec(todo_write("s1", [todo("A")]), now=T0)
            self.edit("s1", lambda r: r["refs"].extend([
                {"system": "jira", "key": "OTHER-1", "seen_at": T0 - 1},
                {"system": "github", "repo": "../x", "number": 1, "seen_at": T0 - 1},
                {"system": "jira", "key": "PROJ-9", "url": "https://evil.example/x", "seen_at": T0 - 1},
                "junk",
            ]))
            urls = [r["url"] for r in self.task("A", now=T0 + 5)["refs"]]
        self.assertEqual(urls, [
            "https://acme.atlassian.net/browse/PROJ-7", "https://github.com/o/r/issues/3", "https://acme.atlassian.net/browse/PROJ-9",
        ])
        self.assertEqual(self.task("A", now=T0 + 5)["refs"], [])  # integration gone: nothing is shown, the record keeps them
        self.assertEqual(len(self.load("s1")["refs"]), 6)

    def test_a_record_that_cannot_be_read_is_never_overwritten_by_a_prompt(self):
        path = tasks.record_path(self.root, self.project_id, "broken")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{not json", encoding="utf-8")
        with integrations(JIRA_CFG, GITHUB_CFG):
            self.assertFalse(self.prompt("PROJ-1", session="broken", now=T0)["recorded"])
        self.assertEqual(path.read_text(encoding="utf-8"), "{not json")

    def test_a_hostile_committed_binding_matches_nothing(self):
        bad = {"account": {"site_url": "https://acme.atlassian.net"}, "project": {"project_key": "A.*"}}
        with integrations(bad, {"account": {"api_url": "https://api.github.com"}, "project": {"repository": "../x/y"}}):
            self.begin()
            self.assertFalse(self.prompt("AB-12 fixes #3 o/r#4")["recorded"])


class ProviderWiringTest(StoreTestCase):
    """Hook wiring for every provider: the matchers, the in-place upgrade and the plugin forwarding."""

    CASES = {"claude": "claude", "opencode": "opencode", "codex": "codex"}

    def test_every_provider_has_a_case(self):
        self.assertEqual(set(self.CASES), set(providers.ALL_PROVIDERS))

    def test_each_provider_forwards_shell_and_pull_request_mcp_calls(self):
        for provider in providers.ALL_PROVIDERS:
            getattr(self, "check_" + self.CASES[provider])()

    def check_claude(self):
        post, failure = hooks.MATCHERS["PostToolUse"], hooks.MATCHERS["PostToolUseFailure"]
        for tool in ("Bash", "mcp__github__create_pull_request", "mcp__gitlab__merge_pull_request", "TodoWrite", "Agent", "Task", "TaskCreate"):
            self.assertTrue(re.fullmatch(post, tool), tool)
        for tool in ("Read", "Edit", "mcp__github__list_pull_requests", "mcp__github__get_issue"):
            self.assertFalse(re.fullmatch(post, tool), tool)
        for tool in ("Bash", "mcp__github__create_pull_request", "Agent", "Task"):
            self.assertTrue(re.fullmatch(failure, tool), tool)
        for tool in ("TodoWrite", "mcp__github__merge_pull_request", "Read"):
            self.assertFalse(re.fullmatch(failure, tool), tool)
        self.assertIn("TodoWrite|TaskCreate|TaskUpdate|Agent|Task", hooks.PREVIOUS_MATCHERS["PostToolUse"])
        self.assertIn("TodoWrite|TaskCreate|TaskUpdate", hooks.PREVIOUS_MATCHERS["PostToolUse"])
        self.assertIn("Agent|Task", hooks.PREVIOUS_MATCHERS["PostToolUseFailure"])
        for current in hooks.MATCHERS.values():
            for older in hooks.PREVIOUS_MATCHERS.get("PostToolUse", ()) + hooks.PREVIOUS_MATCHERS.get("PostToolUseFailure", ()):
                self.assertNotEqual(current, older)

    def test_claude_wire_upgrades_every_matcher_it_shipped_before_in_place(self):
        root = self.tmp / "wired"
        (root / ".claude").mkdir(parents=True)
        settings = root / ".claude" / "settings.json"
        hooks.wire(root)
        for older in hooks.PREVIOUS_MATCHERS["PostToolUse"]:
            data = json.loads(settings.read_text())
            (entry,) = [e for e in data["hooks"]["PostToolUse"] if hooks._is_devteam_entry(e, "post-tool-use.sh")]
            entry["matcher"] = older
            for e in data["hooks"]["PostToolUseFailure"]:
                if hooks._is_devteam_entry(e, "post-tool-use.sh"):
                    e["matcher"] = "Agent|Task"
            settings.write_text(json.dumps(data))
            hooks.wire(root)
            after = json.loads(settings.read_text())["hooks"]
            self.assertEqual([e["matcher"] for e in after["PostToolUse"] if hooks._is_devteam_entry(e, "post-tool-use.sh")], [hooks.MATCHERS["PostToolUse"]], older)
            self.assertEqual([e["matcher"] for e in after["PostToolUseFailure"] if hooks._is_devteam_entry(e, "post-tool-use.sh")], [hooks.MATCHERS["PostToolUseFailure"]])

    def test_claude_wire_leaves_a_users_own_failure_matcher_alone(self):
        root = self.tmp / "wired2"
        (root / ".claude").mkdir(parents=True)
        settings = root / ".claude" / "settings.json"
        hooks.wire(root)
        data = json.loads(settings.read_text())
        for e in data["hooks"]["PostToolUseFailure"]:
            if hooks._is_devteam_entry(e, "post-tool-use.sh"):
                e["matcher"] = "Bash"
        settings.write_text(json.dumps(data))
        hooks.wire(root)
        kept = [e["matcher"] for e in json.loads(settings.read_text())["hooks"]["PostToolUseFailure"] if hooks._is_devteam_entry(e, "post-tool-use.sh")]
        self.assertEqual(kept, ["Bash"])

    def test_install_sh_mirrors_hooks_py_for_both_events_and_every_previous_matcher(self):
        text = (REPO_ROOT / "scripts" / "install.sh").read_text(encoding="utf-8")
        self.assertGreaterEqual(text.count('"matcher": "{}"'.format(hooks.MATCHERS["PostToolUse"])), 1)
        self.assertGreaterEqual(text.count('"matcher": "{}"'.format(hooks.MATCHERS["PostToolUseFailure"])), 1)
        self.assertIn('wanted = "{}"'.format(hooks.MATCHERS["PostToolUse"]), text)
        self.assertIn('wanted = "{}"'.format(hooks.MATCHERS["PostToolUseFailure"]), text)
        previous = re.search(r"previous = \((.*?)\)\n", text, re.S).group(1)
        for older in hooks.PREVIOUS_MATCHERS["PostToolUse"]:
            self.assertIn('"{}"'.format(older), previous)
        self.assertIn("entry.get('matcher') == \"{}\"".format(hooks.PREVIOUS_MATCHERS["PostToolUseFailure"][0]), text)
        self.assertEqual(text.count('new_entry["matcher"] = "{}"'.format(hooks.MATCHERS["PostToolUse"])), 1)

    def test_install_sh_upgrades_an_entry_with_the_second_generation_matcher(self):
        text = (REPO_ROOT / "scripts" / "install.sh").read_text(encoding="utf-8")
        start = text.index("    _inject_hook() {")
        function = text[start:text.index("\n    }\n", start) + len("\n    }\n")]
        settings = self.tmp / "settings.json"
        post = "env -u BASH_ENV -u ENV .dev-team-agents/scripts/hooks/post-tool-use.sh"
        for older in hooks.PREVIOUS_MATCHERS["PostToolUse"]:
            entry = {"matcher": older, "hooks": [{"type": "command", "command": post}]}
            settings.write_text(json.dumps({"hooks": {"PostToolUse": [entry]}}))
            subprocess.run(
                ["bash", "-c", function + '_inject_hook "PostToolUse" "$POST" "hooks/post-tool-use.sh"\n'],
                env=dict(os.environ, SETTINGS_FILE=str(settings), POST=post), stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True,
            )
            result = json.loads(settings.read_text())["hooks"]["PostToolUse"]
            self.assertEqual([e["matcher"] for e in result], [hooks.MATCHERS["PostToolUse"]], older)

    def test_install_sh_upgrades_the_failure_entry_it_shipped_before(self):
        text = (REPO_ROOT / "scripts" / "install.sh").read_text(encoding="utf-8")
        marker_text = "        python3 - \"$SETTINGS_FILE\" \"$POST_TOOL_USE_HOOK\" <<'PYEOF'\n"
        start = text.index(marker_text) + len(marker_text)
        body = text[start:text.index("\nPYEOF\n", start)]
        settings = self.tmp / "settings-f.json"
        post = "env -u BASH_ENV -u ENV .dev-team-agents/scripts/hooks/post-tool-use.sh"
        for matcher, expected in (("Agent|Task", hooks.MATCHERS["PostToolUseFailure"]), ("Bash", "Bash")):
            entry = {"matcher": matcher, "hooks": [{"type": "command", "command": post}]}
            settings.write_text(json.dumps({"hooks": {"PostToolUseFailure": [entry]}}))
            subprocess.run([sys.executable, "-c", body, str(settings), post], check=True)
            result = json.loads(settings.read_text())["hooks"]["PostToolUseFailure"]
            self.assertEqual([e["matcher"] for e in result], [expected], matcher)

    def check_codex(self):
        text = (REPO_ROOT / "scripts" / "install-codex.sh").read_text(encoding="utf-8")
        matcher = re.search(r'MATCHERS = \{"PostToolUse": "([^"]+)"\}', text).group(1)
        for tool in ("spawn_agent", "agents.wait_agent", "close_agent", "Bash", "mcp__github__create_pull_request", "mcp__x__merge_pull_request"):
            self.assertTrue(re.search(matcher, tool), tool)
        for tool in ("update_plan", "apply_patch", "mcp__github__list_issues", "shell"):
            self.assertFalse(re.search(matcher, tool), tool)

    def test_codex_replaces_its_previously_managed_post_tool_use_group_on_reinstall(self):
        text = (REPO_ROOT / "scripts" / "install-codex.sh").read_text(encoding="utf-8")
        body = re.search(r"python3 - \"\$HOOKS_FILE\" \"\$HOOKS_DIR_REL\" <<'PY'\n(.*?)\nPY\n", text, re.S).group(1)
        target = self.tmp / "hooks.json"
        old = {"matcher": ".*(wait_agent|spawn_agent|close_agent)", "hooks": [
            {"type": "command", "command": "old", "statusMessage": "dev-team-agents posttooluse hook _dev_team_agents_managed"}]}
        mine = {"matcher": "Bash", "hooks": [{"type": "command", "command": "mine"}]}
        target.write_text(json.dumps({"hooks": {"PostToolUse": [mine, old]}}))
        subprocess.run([sys.executable, "-c", body, str(target), ".dev-team-agents/scripts/hooks"], check=True, stdout=subprocess.PIPE)
        groups = json.loads(target.read_text())["hooks"]["PostToolUse"]
        self.assertEqual(groups[0], mine)
        managed = [g for g in groups if any("_dev_team_agents_managed" in h.get("statusMessage", "") for h in g["hooks"])]
        self.assertEqual(len(managed), 1)
        self.assertIn("Bash", managed[0]["matcher"])
        self.assertIn("create_pull_request", managed[0]["matcher"])

    def check_opencode(self):
        text = (REPO_ROOT / "opencode" / "plugin" / "dev-team-agents.ts").read_text(encoding="utf-8")
        command_re = re.search(r"const PR_COMMAND_RE = /(.*)/\n", text).group(1)
        tool_re = re.search(r"const PR_TOOL_RE = /(.*)/\n", text).group(1)
        for command in ("gh pr create --fill", "gh  pr  merge 3", "glab mr create", "glab mr merge 2", "git merge feat/x", "git -C p merge x", "cd x && gh pr create"):
            self.assertTrue(re.search(command_re, command), command)
        for command in ("ls -la", "echo hello", "git status", "gh pr view 3", "git log --oneline", "npm test"):
            self.assertFalse(re.search(command_re, command), command)
        for tool in ("github_create_pull_request", "mcp_github_merge_pull_request", "create_pull_request"):
            self.assertTrue(re.search(tool_re, tool), tool)
        for tool in ("bash", "github_list_pull_requests", "read", "create_pull_request_review"):
            self.assertFalse(re.search(tool_re, tool), tool)
        forward = text[text.index('"tool.execute.after"'):text.index("// Only a subagent's report")]
        for needle in ('input.tool === "bash"', "PR_TOOL_RE.test(input.tool)", "sessionID: input.sessionID,\n          tool: input.tool,", "tool_use_id: callID",
                       "cwd: directory", "args: known", "output: text", "post-tool-use.sh", "return\n"):
            self.assertIn(needle, forward, needle)
        self.assertLess(forward.index("sessionID:"), forward.index("args: known"))
        self.assertLess(forward.index("args: known"), forward.index("output: text"))
        before = text[text.index('"tool.execute.before"'):text.index('"tool.execute.after"')]
        self.assertIn("prArgsByCall.set(before.callID, output.args)", before)

    def test_the_provider_docs_name_the_capture_for_every_provider(self):
        docs = (REPO_ROOT / "docs" / "providers.md").read_text(encoding="utf-8")
        for provider in providers.ALL_PROVIDERS:
            self.assertIn(provider, docs.lower())
        self.assertIn("create_pull_request", docs)


@requires_bash()
class PrHookGateTest(tt.BoardCase):
    """The bash gates: nothing forks python for an unrelated call, the right call reaches the CLI."""

    def setUp(self):
        super().setUp()
        git(self.root, "remote", "add", "origin", "https://github.com/o/r.git")
        self.state = Path(tasks.tasks_dir(self.root, self.project_id)).parent
        self.state.mkdir(parents=True, exist_ok=True)
        self.shim = self.tmp / "shim"
        self.shim.mkdir()
        self.calls = self.tmp / "python-calls"
        (self.shim / "python3").write_text(
            '#!/bin/sh\necho x >> "{}"\nexec "{}" "$@"\n'.format(self.calls, shutil.which("python3")), encoding="utf-8"
        )
        (self.shim / "python3").chmod(0o755)

    def python_calls(self):
        return len(self.calls.read_text().splitlines()) if self.calls.is_file() else 0

    def run_script(self, script, payload, extra_env=None, cwd=None):
        env = dict(os.environ, PATH="{}{}{}".format(self.shim, os.pathsep, os.environ["PATH"]))
        env.update(extra_env or {})
        return subprocess.run(
            ["bash", str(script)], cwd=str(cwd or self.root), env=env,
            input=(payload if isinstance(payload, str) else json.dumps(payload)).encode(),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True,
        )

    def queue(self):
        path = self.state / "notifications.jsonl"
        return [json.loads(l) for l in path.read_text().splitlines()] if path.is_file() else []

    def seed(self, session="s1"):
        self.run_script(POST_TOOL_USE, todo_write(session, [todo("A", "completed"), todo("B")], cwd=str(self.root)))
        self.calls.write_text("")

    def test_unrelated_bash_and_mcp_calls_fork_no_python_in_either_post_tool_use_sub_script(self):
        self.seed()
        for payload in (
            claude_bash("s1", "ls -la", "x", cwd=str(self.root)),
            claude_bash("s1", "echo todowrite TaskUpdate", "x", cwd=str(self.root)),
            claude_bash("s1", "git status && git diff", "x", cwd=str(self.root)),
            claude_bash("s1", "npm test", "x" * 50000, cwd=str(self.root)),
            codex_bash("s1", "rg foo", "x", cwd=str(self.root)),
            opencode_bash("s1", "cat file", "x", cwd=str(self.root)),
            {"session_id": "s1", "tool_name": "mcp__github__list_issues", "tool_input": {}, "tool_response": {}},
        ):
            for script in (PR_SUB, POST_TOOL_USE, POST_DISPATCHER):
                result = self.run_script(script, payload, cwd=self.root)
                self.assertEqual((result.stdout, result.stderr), (b"", b""))
        self.assertEqual(self.python_calls(), 0)

    def test_the_gate_is_a_loose_substring_test_and_the_cli_decides_nothing_is_recorded(self):
        self.seed()
        self.run_script(PR_SUB, {"session_id": "s1", "tool_name": "Read", "tool_input": {"file_path": "/tmp/gh pr create"}})
        self.run_script(PR_SUB, claude_bash("s1", "echo gh pr create", PR + "\n", cwd=str(self.root)))
        self.assertLessEqual(self.python_calls(), 2)
        self.assertNotIn("prs", self.load("s1"))

    def test_the_gate_sees_a_command_whose_words_sit_past_the_old_16k_head(self):
        self.seed()
        command = "echo {} && gh pr create --fill".format("x" * 18000)
        self.run_script(PR_SUB, claude_bash("s1", command, PR + "\n", cwd=str(self.root)))
        self.assertEqual(self.python_calls(), 1)
        self.assertEqual(self.load("s1")["prs"][0]["number"], 12)

    def test_the_gate_is_linear_on_a_large_payload_that_almost_matches(self):
        self.seed()
        payload = claude_bash("s1", "echo hi", "gh pr mer git x pr mr glab " * 30000, cwd=str(self.root))
        started = time.monotonic()
        self.run_script(PR_SUB, payload)
        self.assertLess(time.monotonic() - started, 10)
        self.assertEqual(self.python_calls(), 0)

    def test_the_pr_gate_is_fast_on_a_large_command_and_skips_one_python_would_not_analyse(self):
        self.seed()
        command = "echo {} && gh pr create --fill".format("x " * 100000)
        self.assertGreater(len(command), pr_refs.MAX_COMMAND)
        started = time.monotonic()
        self.run_script(PR_SUB, claude_bash("s1", command, PR + "\n", cwd=str(self.root)))
        self.assertLess(time.monotonic() - started, 1.0)
        self.assertEqual(self.python_calls(), 0)

    def test_the_pr_gate_cap_matches_max_command(self):
        self.assertIn("-le {} ]".format(pr_refs.MAX_COMMAND), PR_SUB.read_text(encoding="utf-8"))

    def test_the_pr_gate_ignores_the_tool_output_and_an_oversize_payload(self):
        self.seed()
        self.run_script(PR_SUB, claude_bash("s1", "echo hi", "gh pr create\n" + PR + "\n", cwd=str(self.root)))
        self.assertEqual(self.python_calls(), 0)
        started = time.monotonic()
        self.run_script(PR_SUB, claude_bash("s1", "gh pr create " + "x" * 1100000, PR + "\n", cwd=str(self.root)))
        self.assertLess(time.monotonic() - started, 1.0)
        self.assertEqual(self.python_calls(), 0)

    def test_the_pr_gate_still_sees_mcp_and_escaped_quote_commands(self):
        self.seed()
        self.run_script(PR_SUB, claude_bash("s1", 'echo "a" && gh pr merge 12', "", cwd=str(self.root)))
        self.assertEqual(self.python_calls(), 1)
        self.run_script(PR_SUB, {"session_id": "s1", "tool_name": "mcp__github__create_pull_request", "tool_input": {}, "tool_response": {}})
        self.assertEqual(self.python_calls(), 2)

    def test_a_later_shell_tool_key_inside_an_agent_payload_does_not_drop_the_agent_call(self):
        self.seed()
        raw = (
            '{"session_id":"s1","tool_name":"Agent","tool_input":{"description":"d","prompt":"p",'
            '"subagent_type":"backend-developer"},"tool_response":{"tool_name":"Bash"}}'
        )
        self.run_script(POST_TOOL_USE, raw)
        self.assertGreaterEqual(self.python_calls(), 1)
        self.calls.write_text("")
        self.run_script(POST_TOOL_USE, claude_bash("s1", "echo TodoWrite", "x", cwd=str(self.root)))
        self.assertEqual(self.python_calls(), 0)

    def test_a_shell_or_mcp_call_never_reaches_the_todo_sub_script_even_when_it_names_a_todo_tool(self):
        self.seed()
        payload = claude_bash("s1", "echo TodoWrite", "x", cwd=str(self.root))
        self.run_script(POST_TOOL_USE, payload)
        self.assertEqual(self.python_calls(), 0)
        self.run_script(POST_TOOL_USE, todo_write("s1", [todo("A", "completed"), todo("B", "completed")], cwd=str(self.root)))
        self.assertEqual(self.python_calls(), 1)

    def test_a_pr_create_without_a_record_forks_nothing(self):
        for session in ("ghost",):
            self.run_script(PR_SUB, claude_bash(session, "gh pr create", PR + "\n", cwd=str(self.root)))
        self.assertEqual(self.python_calls(), 0)

    def test_a_pr_create_with_a_record_reaches_the_cli_once_and_marks(self):
        self.seed()
        result = self.run_script(POST_DISPATCHER, claude_bash("s1", "git push && gh pr create --fill", PR + "\n", cwd=str(self.root)))
        self.assertEqual((result.stdout, result.stderr), (b"", b""))
        self.assertEqual(self.python_calls(), 1)
        self.assertEqual(self.load("s1")["prs"][0]["number"], 12)

    def test_every_provider_payload_reaches_the_same_mark_through_the_dispatcher(self):
        builders = {
            "claude": lambda s: claude_bash(s, "gh pr create", PR + "\n", cwd=str(self.root)),
            "codex": lambda s: codex_bash(s, "gh pr create", PR + "\n", cwd=str(self.root)),
            "opencode": lambda s: opencode_bash(s, "gh pr create", PR + "\n", cwd=str(self.root)),
        }
        self.assertEqual(set(builders), set(providers.ALL_PROVIDERS))
        for provider, build in builders.items():
            session = "h-" + provider
            self.run_script(POST_TOOL_USE, todo_write(session, [todo("A")], cwd=str(self.root)))
            self.run_script(POST_DISPATCHER, build(session))
            self.assertEqual(self.load(session)["prs"][0]["number"], 12, provider)

    def test_the_failure_event_links_an_existing_pr_through_the_dispatcher(self):
        self.seed()
        error = 'Exit code 1\na pull request for branch "x" into branch "main" already exists:\n{}\n'.format(PR)
        self.run_script(POST_DISPATCHER, claude_bash("s1", "gh pr create", error=error, event="PostToolUseFailure", cwd=str(self.root)))
        self.assertEqual(self.load("s1")["prs"][0]["number"], 12)

    def test_the_stop_raises_one_notification_per_fixed_mark_and_never_again(self):
        self.seed()
        self.run_script(POST_DISPATCHER, claude_bash("s1", "gh pr create", PR + "\n", cwd=str(self.root)))
        payload = self.tmp / "stop.json"
        payload.write_text(json.dumps({"session_id": "s1"}))
        self.run_script(STOP_SUB, "", {"DEVTEAM_HOOK_PAYLOAD": str(payload)})
        self.run_script(STOP_SUB, "", {"DEVTEAM_HOOK_PAYLOAD": str(payload)})
        queue = [r for r in self.queue() if r["code"] == "tasks.pr_created"]
        self.assertEqual(len(queue), 1)
        self.assertIn("PR #12", queue[0]["message"])
        self.assertEqual(self.load("s1")["prs"][0]["task_keys"], ["t1"])

    def test_two_marks_fixed_by_one_stop_raise_two_notifications(self):
        self.seed()
        self.run_script(POST_DISPATCHER, claude_bash("s1", "gh pr create", PR + "\n", cwd=str(self.root)))
        self.run_script(POST_DISPATCHER, claude_bash("s1", "gh pr create", "https://github.com/o/r/pull/13\n", cwd=str(self.root)))
        payload = self.tmp / "stop.json"
        payload.write_text(json.dumps({"session_id": "s1"}))
        self.run_script(STOP_SUB, "", {"DEVTEAM_HOOK_PAYLOAD": str(payload)})
        notes = [r for r in self.queue() if r["code"] == "tasks.pr_created"]
        self.assertEqual(sorted("#12" in n["message"] or "#13" in n["message"] for n in notes), [True, True])
        self.assertEqual(len(notes), 2)

    def test_an_mr_notification_uses_the_bang_sign(self):
        git(self.root, "remote", "set-url", "origin", "https://gitlab.example.com/grp/sub/repo.git")
        self.seed()
        self.run_script(POST_DISPATCHER, claude_bash("s1", "glab mr create", MR + "\n", cwd=str(self.root)))
        payload = self.tmp / "stop.json"
        payload.write_text(json.dumps({"session_id": "s1"}))
        self.run_script(STOP_SUB, "", {"DEVTEAM_HOOK_PAYLOAD": str(payload)})
        (note,) = [r for r in self.queue() if r["code"] == "tasks.pr_created"]
        self.assertIn("MR !4", note["message"])

    def test_the_issue_gate_forks_nothing_without_a_reference_shape_or_an_integration_binding(self):
        settings = self.root / ".dev-team-agents" / "integration-settings"
        text = lambda p: {"session_id": "s1", "cwd": str(self.root), "hook_event_name": "UserPromptSubmit", "prompt": p}  # noqa: E731
        for payload in (text("hello there"), text("no digits here"), {"session_id": "s1", "hook_event_name": "UserPromptSubmit"}, text("PROJ-12 no binding")):
            self.run_script(ISSUE_SUB, payload)
            self.run_script(PROMPT_DISPATCHER, payload)
        self.assertEqual(self.python_calls(), 0)
        settings.mkdir(parents=True, exist_ok=True)
        (settings / "jira.json").write_text('{"project_key": "PROJ"}', encoding="utf-8")
        self.run_script(ISSUE_SUB, text("plain words only"))
        self.assertEqual(self.python_calls(), 0)
        self.run_script(ISSUE_SUB, text("work on PROJ-12"))
        self.assertEqual(self.python_calls(), 1)
        self.assertFalse(tasks.record_path(self.root, self.project_id, "s1").exists())

    def test_the_issue_sub_script_prints_nothing_and_exits_zero_on_garbage(self):
        for stdin in ("", "not json", '{"prompt":'):
            result = self.run_script(ISSUE_SUB, stdin)
            self.assertEqual((result.stdout, result.stderr), (b"", b""))


class QualityGateRegressionTest(PrCase):
    def test_a_task_completed_again_after_its_pr_was_fixed_leaves_pr_created(self):
        self.begin()
        self.create()
        self.stop_idle()
        self.assertEqual(self.task(now=T0 + 35)["column"], "pr_created")
        self.rec(todo_write("s1", [todo("A", "in_progress"), todo("B")]), now=T0 + 40)
        self.rec(todo_write("s1", [todo("A", "completed"), todo("B")]), now=T0 + 50)
        view = self.task(now=T0 + 60)
        self.assertEqual((view["column"], view["pr"]["state"]), ("done", "open"))
        self.assertEqual(view["durations"]["pr_created"], 10)

    def test_a_cwd_outside_the_project_root_runs_no_git(self):
        outside = self.tmp / "outside"
        outside.mkdir()
        with mock.patch("devteam.tasks.subprocess.run", wraps=subprocess.run) as run:
            self.assertIsNone(tasks._branch_in_project(str(outside), self.root))
            self.assertIsNone(tasks._branch_in_project(str(self.root.parent), self.root))
        for call in run.call_args_list:
            self.assertNotIn(str(outside), call.args[0])
            self.assertNotIn(str(self.root.parent), call.args[0])
        self.assertIsNotNone(tasks._branch_in_project(str(self.root), self.root))

    def test_a_jira_site_url_with_userinfo_or_a_port_is_refused(self):
        for site in ("https://user@acme.atlassian.net", "https://acme.atlassian.net:8443", "https://u:p@acme.atlassian.net/jira"):
            cfg = {"account": {"site_url": site}, "project": {"project_key": "PROJ"}}
            with integrations(cfg, None):
                self.assertIsNone(pr_refs.load_context(self.root)["jira"], site)
        with integrations(JIRA_CFG, None):
            self.assertEqual(pr_refs.load_context(self.root)["jira"]["host"], "acme.atlassian.net")

    def test_an_exported_tool_aiming_variable_earlier_in_the_line_refuses_the_command(self):
        for command in (
            "export PATH=/tmp/x:$PATH; gh pr create",
            "export GH_HOST=evil.example && gh pr create",
            "GH_REPO=a/b; gh pr merge 3",
            "export GITLAB_HOST=x; glab mr create",
            "export GLAB_TOKEN=x\nglab mr merge 1",
        ):
            self.assertEqual(pr_refs.analyze_command(command), [], command)
        self.assertEqual(len(pr_refs.analyze_command("export FOO=1; gh pr create")), 1)

    def test_remotes_are_read_only_for_a_new_task_text_with_a_connected_integration(self):
        self.begin()
        with mock.patch("devteam.pr_refs.git_remotes", return_value=[]) as remotes:
            with integrations(None, None):
                self.rec(todo_write("s1", [todo("A", "completed"), todo("B"), todo("Do PROJ-5")]), now=T0 + 20)
            remotes.assert_not_called()
            with integrations(JIRA_CFG, None):
                self.rec(todo_write("s1", [todo("A", "completed"), todo("B"), todo("Do PROJ-5"), todo("PROJ-6 too")]), now=T0 + 30)
            remotes.assert_not_called()
            with integrations(None, GITHUB_CFG):
                self.rec(todo_write("s1", [todo("A", "completed"), todo("B"), todo("Do PROJ-5"), todo("PROJ-6 too"), todo("see o/r#7")]), now=T0 + 40)
            self.assertEqual(remotes.call_count, 1)


class JsonContractTest(PrCase):
    def test_the_new_fields_are_additive_through_the_real_cli(self):
        self.begin()
        self.create(command="gh pr create --head feat/x")
        code, out, err = self.run_cli("--json", "tasks", "mark", "--project-root", str(self.root), "--state", "idle", input_text=json.dumps({"session_id": "s1"}))
        self.assertEqual(code, 0, err)
        body = json.loads(out)
        self.assertEqual(body["pr_marks"], [{"kind": "pr", "number": 12, "url": PR}])
        self.assertTrue(body["ok"])
        for key in ("marked", "open", "review_result", "review_window", "review_findings", "review_results", "became_all_done", "title_short"):
            self.assertIn(key, body)
        code, out, _ = self.run_cli("--json", "tasks", "list")
        project = json.loads(out)["projects"][0]
        for key in ("project_id", "root", "counts", "sessions", "with_findings", "as_of", "link_hosts"):
            self.assertIn(key, project)
        self.assertEqual(set(project["counts"]), {"todo", "in_progress", "done", "in_review", "pr_created", "total"})
        self.assertTrue(all(set(h) == {"host", "kinds"} and isinstance(h["kinds"], list) for h in project["link_hosts"]))
        session = project["sessions"][0]
        self.assertEqual(session["prs"][0], {"kind": "pr", "number": 12, "url": PR, "state": "open", "head": "feat/x"})
        task = {t["content"]: t for t in session["tasks"]}["A"]
        self.assertEqual((task["column"], task["pr"]["number"], task["refs"]), ("pr_created", 12, []))
        self.assertIn("pr_created", task["durations"])
        self.assertTrue({"pending", "in_progress", "completed", "in_review"} <= set(task["durations"]))

    def test_record_through_the_cli_reports_the_event(self):
        self.begin()
        code, out, _ = self.run_cli("--json", "tasks", "record", "--project-root", str(self.root), input_text=json.dumps(claude_bash("s1", "gh pr create", PR + "\n")))
        body = json.loads(out)
        self.assertEqual((code, body["recorded"], body["event"]), (0, True, "pr_created"))
        for key in ("recorded", "session", "all_done", "became_all_done", "title_short"):
            self.assertIn(key, body)

    def test_the_human_listing_names_the_new_column(self):
        self.begin()
        code, out, _ = self.run_cli("tasks", "list")
        self.assertEqual(code, 0)
        self.assertIn("pr/mr created 0", out)


if __name__ == "__main__":
    unittest.main()
