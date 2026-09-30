"""The task board (ADR-0018): capture, derived state, the board query and the hooks.

Hooks write one record per session through `devteam tasks record|mark`; `tasks list` and
`tasks watch` derive everything a client shows. These tests pin the payload normalizers of
all four provider tools, the record semantics (owner scoping, removal kept, history), the
derived state, the cross-project aggregation the app codes against, the watch lifecycle,
and the bash hooks — including that a tool that is not a todo tool forks no python.
"""

import json
import os
import shlex
import shutil
import subprocess
import sys
import threading
import time
import unittest
from pathlib import Path

from devteam_support import CLI, REPO_ROOT, StoreTestCase, requires_bash

from unittest import mock

from devteam import bind, hooks, project, tasks

HOOKS = REPO_ROOT / "scripts" / "hooks"
PRE_TOOL_USE = HOOKS / "pre-tool-use" / "04-task-board.sh"
POST_TOOL_USE = HOOKS / "post-tool-use" / "01-task-board.sh"
POST_DISPATCHER = HOOKS / "post-tool-use.sh"
SESSION_END = HOOKS / "session-end.sh"
STOP_SUB = HOOKS / "stop" / "04b-task-board.sh"

T0 = 1_700_000_000


def todo(content, status="pending"):
    return {"content": content, "status": status, "activeForm": content + "ing"}


def todo_write(session, items, agent_id=None, cwd=""):
    payload = {
        "session_id": session,
        "cwd": cwd,
        "hook_event_name": "PostToolUse",
        "tool_name": "TodoWrite",
        "tool_input": {"todos": items},
    }
    if agent_id:
        payload.update(agent_id=agent_id, agent_type="Explore")
    return payload


def task_create(session, subject, response=None, key="tool_response"):
    payload = {
        "session_id": session,
        "tool_name": "TaskCreate",
        "tool_input": {"subject": subject, "description": "d", "activeForm": subject + "ing"},
    }
    if response is not None:
        payload[key] = response
    return payload


def task_update(session, task_id, status=None, subject=None):
    tool_input = {"taskId": task_id}
    if status:
        tool_input["status"] = status
    if subject:
        tool_input["subject"] = subject
    return {"session_id": session, "tool_name": "TaskUpdate", "tool_input": tool_input}


def codex_plan(session, steps):
    return {
        "session_id": session,
        "tool_name": "update_plan",
        "tool_input": {"plan": [{"step": s, "status": st} for s, st in steps]},
    }


def opencode_todos(session, items):
    return {
        "tool": "todowrite",
        "args": {"todos": [dict(id=i, content=c, status=s, priority="medium") for i, c, s in items]},
        "sessionID": session,
    }


class NormalizeTest(unittest.TestCase):
    def test_todowrite_is_a_replace_matched_by_content(self):
        call = tasks.normalize(todo_write("s", [todo("A", "in_progress"), todo("B")]))
        self.assertEqual(call["provider"], "claude")
        self.assertEqual(call["owner"], "main")
        kind, items = call["op"]
        self.assertEqual(kind, "replace")
        self.assertEqual([(i["content"], i["status"], i["id"]) for i in items], [("A", "in_progress", None), ("B", "pending", None)])

    def test_a_subagent_call_carries_its_id_as_owner(self):
        call = tasks.normalize(todo_write("s", [todo("A")], agent_id="ag-1"))
        self.assertEqual((call["owner"], call["agent_type"]), ("ag-1", "Explore"))

    def test_taskcreate_id_from_a_string_response(self):
        call = tasks.normalize(task_create("s", "Write docs", "Task #3 created successfully: Write docs"))
        self.assertEqual(call["op"][1]["id"], "3")

    def test_taskcreate_id_from_an_object_in_tool_output(self):
        call = tasks.normalize(task_create("s", "X", {"task": {"id": "7", "subject": "X"}}, key="tool_output"))
        self.assertEqual(call["op"][1]["id"], "7")

    def test_taskcreate_without_an_id_leaves_it_to_the_record(self):
        self.assertIsNone(tasks.normalize(task_create("s", "X"))["op"][1]["id"])

    def test_taskupdate_incl_deleted_and_rename(self):
        kind, item = tasks.normalize(task_update("s", "2", "deleted"))["op"]
        self.assertEqual((kind, item["id"], item["status"]), ("update", "2", "deleted"))
        _, item = tasks.normalize(task_update("s", "2", subject="New"))["op"]
        self.assertEqual((item["content"], item["status"]), ("New", None))

    def test_codex_update_plan(self):
        call = tasks.normalize(codex_plan("c1", [("Step one", "completed"), ("Step two", "in_progress")]))
        self.assertEqual(call["provider"], "codex")
        self.assertEqual([i["status"] for i in call["op"][1]], ["completed", "in_progress"])

    def test_opencode_todowrite_uses_the_todo_id_and_session_id_key(self):
        call = tasks.normalize(opencode_todos("o1", [("a", "one", "cancelled"), ("b", "two", "pending")]))
        self.assertEqual((call["provider"], call["session_id"]), ("opencode", "o1"))
        self.assertEqual([(i["id"], i["status"]) for i in call["op"][1]], [("a", "cancelled"), ("b", "pending")])

    def test_anything_unreadable_or_foreign_is_none(self):
        for payload in (
            None, [], "x", {}, {"tool_name": "Bash", "session_id": "s"},
            {"tool_name": "TodoWrite", "session_id": "s", "tool_input": {"todos": "nope"}},
            {"tool_name": "TodoWrite", "tool_input": {"todos": []}},  # no session id
            {"tool_name": "TaskUpdate", "session_id": "s", "tool_input": {}},
        ):
            self.assertIsNone(tasks.normalize(payload), payload)

    def test_provider_flag_restricts_detection(self):
        self.assertIsNone(tasks.normalize(codex_plan("c", [("a", "pending")]), provider="claude"))

    def test_session_keys_refuse_path_separators_and_hash_odd_ones(self):
        for hostile in ("../evil", "a/b", "a\\b", "..", ".", "", "x\0y"):
            self.assertIsNone(tasks.session_key(hostile), hostile)
        self.assertEqual(tasks.session_key("3f2a-uuid_1.0"), "3f2a-uuid_1.0")
        odd = tasks.session_key("a b:c")
        self.assertRegex(odd, r"^a_b_c-[0-9a-f]{12}$")
        self.assertNotEqual(odd, tasks.session_key("a b;c"))
        self.assertFalse(tasks.session_key(".hidden").startswith("."))


class BoardCase(StoreTestCase):
    def setUp(self):
        super().setUp()
        self.install_version("3.0.0", activate=True)
        self.root = self.new_project("proj-a")
        self.project_id = bind.bind(self.root, provider_names=["claude"], mode="link")["project_id"]

    def bound(self, name):
        root = self.new_project(name)
        return root, bind.bind(root, provider_names=["claude"], mode="link")["project_id"]

    def rec(self, payload, now=T0, root=None):
        return tasks.record(root or self.root, payload, now=now)

    def load(self, session, root=None, project_id=None):
        path = tasks.record_path(root or self.root, project_id or self.project_id, session)
        return json.loads(path.read_text(encoding="utf-8"))

    def view(self, now=T0 + 10, **kwargs):
        return tasks.collect(now=now, **kwargs)["projects"]


class RecordTest(BoardCase):
    def test_todowrite_creates_a_machine_local_record(self):
        result = self.rec(todo_write("s1", [todo("A"), todo("B", "in_progress")], cwd=str(self.root)))
        self.assertEqual((result["recorded"], result["session"], result["all_done"]), (True, "s1", False))
        record = self.load("s1")
        self.assertEqual(record["schema"], 1)
        self.assertEqual((record["provider"], record["project_id"]), ("claude", self.project_id))
        self.assertIsNotNone(record["branch"])
        self.assertEqual([t["key"] for t in record["tasks"]], ["t1", "t2"])
        path = tasks.record_path(self.root, self.project_id, "s1")
        self.assertEqual(path.parent.name, "task-board")

    def test_history_appends_only_on_status_change_and_drives_durations(self):
        self.rec(todo_write("s1", [todo("A")]), now=T0)
        self.rec(todo_write("s1", [todo("A")]), now=T0 + 50)  # unchanged: no entry
        self.rec(todo_write("s1", [todo("A", "in_progress")]), now=T0 + 120)
        self.rec(todo_write("s1", [todo("A", "completed")]), now=T0 + 420)
        history = self.load("s1")["tasks"][0]["history"]
        self.assertEqual([h["status"] for h in history], ["pending", "in_progress", "completed"])
        session = self.view(now=T0 + 500)[0]["sessions"][0]
        task = session["tasks"][0]
        self.assertEqual(task["durations"], {"pending": 120, "in_progress": 300, "completed": 80, "in_review": 0})
        self.assertEqual((task["column"], task["completed_at"]), ("done", T0 + 420))

    def test_history_is_capped_at_fifty_entries(self):
        for i in range(60):
            status = "in_progress" if i % 2 == 0 else "pending"
            self.rec(todo_write("s1", [todo("A", status)]), now=T0 + i)
        self.assertEqual(len(self.load("s1")["tasks"][0]["history"]), tasks.HISTORY_CAP)

    def test_a_subagent_list_and_the_main_list_do_not_remove_each_other(self):
        self.rec(todo_write("s1", [todo("sub-1"), todo("sub-2")], agent_id="ag-1"), now=T0)
        self.rec(todo_write("s1", [todo("main-1")]), now=T0 + 1)
        self.rec(todo_write("s1", [todo("main-1", "in_progress")]), now=T0 + 2)
        live = {t["content"]: t["removed_at"] for t in self.load("s1")["tasks"]}
        self.assertEqual(live, {"sub-1": None, "sub-2": None, "main-1": None})
        # and the subagent rewriting its own list leaves the main task alone
        self.rec(todo_write("s1", [todo("sub-1", "completed")], agent_id="ag-1"), now=T0 + 3)
        by = {t["content"]: t for t in self.load("s1")["tasks"]}
        self.assertEqual(by["sub-2"]["removed_at"], T0 + 3)
        self.assertIsNone(by["main-1"]["removed_at"])
        self.assertEqual({t["owner"] for t in by.values()}, {"main", "ag-1"})

    def test_an_omitted_task_is_marked_removed_and_kept_and_can_reappear(self):
        self.rec(todo_write("s1", [todo("A"), todo("B")]), now=T0)
        self.rec(todo_write("s1", [todo("A")]), now=T0 + 10)
        by = {t["content"]: t for t in self.load("s1")["tasks"]}
        self.assertEqual(by["B"]["removed_at"], T0 + 10)
        self.assertEqual(len(self.load("s1")["tasks"]), 2)
        # removed and never completed: not on the board
        self.assertEqual([t["content"] for t in self.view()[0]["sessions"][0]["tasks"]], ["A"])
        self.rec(todo_write("s1", [todo("A"), todo("B", "in_progress")]), now=T0 + 20)
        by = {t["content"]: t for t in self.load("s1")["tasks"]}
        self.assertIsNone(by["B"]["removed_at"])
        self.assertEqual(len(by), 2)

    def test_a_removed_completed_task_still_counts_as_done(self):
        self.rec(todo_write("s1", [todo("A", "completed"), todo("B")]), now=T0)
        self.rec(todo_write("s1", [todo("B")]), now=T0 + 10)
        counts = self.view()[0]["counts"]
        self.assertEqual((counts["done"], counts["todo"], counts["total"]), (1, 1, 2))

    def test_duplicate_content_is_paired_in_order(self):
        self.rec(todo_write("s1", [todo("same"), todo("same")]), now=T0)
        self.rec(todo_write("s1", [todo("same", "completed"), todo("same")]), now=T0 + 5)
        statuses = [t["status"] for t in self.load("s1")["tasks"]]
        self.assertEqual(statuses, ["completed", "pending"])

    def test_identity_ignores_case_and_whitespace(self):
        self.rec(todo_write("s1", [todo("Fix  the Bug")]), now=T0)
        self.rec(todo_write("s1", [todo(" fix the bug ", "completed")]), now=T0 + 5)
        self.assertEqual(len(self.load("s1")["tasks"]), 1)

    def test_taskcreate_and_taskupdate_are_incremental_and_keep_identity_on_rename(self):
        self.rec(task_create("s1", "One", "Task #1 created successfully: One"), now=T0)
        self.rec(task_create("s1", "Two", {"id": "2"}, key="tool_output"), now=T0 + 1)
        self.rec(task_create("s1", "Three"), now=T0 + 2)  # no id anywhere: next sequential
        self.rec(task_update("s1", "2", "in_progress", subject="Two renamed"), now=T0 + 3)
        self.rec(task_update("s1", "1", "completed"), now=T0 + 4)
        self.rec(task_update("s1", "3", "deleted"), now=T0 + 5)
        by = {t["id"]: t for t in self.load("s1")["tasks"]}
        self.assertEqual(sorted(by), ["1", "2", "3"])
        self.assertEqual((by["2"]["content"], by["2"]["status"]), ("Two renamed", "in_progress"))
        self.assertEqual(by["1"]["status"], "completed")
        self.assertEqual(by["3"]["removed_at"], T0 + 5)
        shown = [t["content"] for t in self.view()[0]["sessions"][0]["tasks"]]
        self.assertEqual(shown, ["One", "Two renamed"])

    def test_an_update_for_an_unknown_task_is_kept_not_dropped(self):
        self.rec(task_update("s1", "9", "in_progress", subject="Old one"), now=T0)
        self.assertEqual(self.load("s1")["tasks"][0]["content"], "Old one")

    def test_codex_and_opencode_are_recorded_with_their_provider(self):
        self.rec(codex_plan("c1", [("Plan", "in_progress")]))
        self.rec(opencode_todos("o1", [("a", "Thing", "pending")]))
        self.assertEqual(self.load("c1")["provider"], "codex")
        self.assertEqual(self.load("o1")["tasks"][0]["id"], "a")
        commands = {s["provider"]: s["resume_command"] for s in self.view()[0]["sessions"]}
        self.assertEqual(commands["codex"], "cd {} && codex resume c1".format(shlex.quote(str(self.root.resolve()))))
        self.assertTrue(commands["opencode"].endswith("opencode --session o1"))

    def test_became_all_done_is_true_exactly_on_the_transition(self):
        first = self.rec(todo_write("s1", [todo("A"), todo("B")]), now=T0)
        second = self.rec(todo_write("s1", [todo("A", "completed"), todo("B")]), now=T0 + 1)
        third = self.rec(todo_write("s1", [todo("A", "completed"), todo("B", "completed")]), now=T0 + 2)
        fourth = self.rec(todo_write("s1", [todo("A", "completed"), todo("B", "completed")]), now=T0 + 3)
        self.assertEqual([r["became_all_done"] for r in (first, second, third, fourth)], [False, False, True, False])
        self.assertTrue(third["all_done"] and fourth["all_done"])

    def test_dropping_an_unfinished_task_is_not_a_session_done(self):
        self.rec(todo_write("s1", [todo("A", "completed"), todo("B")]), now=T0)
        dropped = self.rec(todo_write("s1", [todo("A", "completed")]), now=T0 + 1)
        self.assertTrue(dropped["all_done"])
        self.assertFalse(dropped["became_all_done"])

    def test_completing_the_last_open_task_fires_once(self):
        self.rec(todo_write("s1", [todo("A", "completed"), todo("B")]), now=T0)
        fired = self.rec(todo_write("s1", [todo("A", "completed"), todo("B", "completed")]), now=T0 + 1)
        again = self.rec(todo_write("s1", [todo("A", "completed"), todo("B", "completed")]), now=T0 + 2)
        self.assertEqual([fired["became_all_done"], again["became_all_done"]], [True, False])

    def test_a_replayed_create_keeps_the_status_of_an_existing_task(self):
        self.rec(task_create("s1", "Do it", "Task #1 created successfully: Do it"), now=T0)
        self.rec(task_update("s1", "1", status="completed"), now=T0 + 1)
        self.rec(task_create("s1", "Do it", "Task #1 created successfully: Do it"), now=T0 + 2)
        task = self.load("s1")["tasks"][0]
        self.assertEqual((len(self.load("s1")["tasks"]), task["status"]), (1, "completed"))

    def test_a_subject_containing_a_hash_is_not_taken_for_the_id(self):
        payload = task_create("s1", "Fix #12", "Task #3 created successfully: Fix #12")
        self.assertEqual(tasks.normalize(payload)["op"][1]["id"], "3")
        payload = task_create("s1", "x", "Created: Fix #12")
        self.assertIsNone(tasks.normalize(payload)["op"][1].get("id"))

    def test_an_option_like_session_id_gets_no_resume_command(self):
        self.assertIsNone(tasks.resume_command(self.root, "claude", "--evil"))
        self.assertIsNone(tasks.resume_command(self.root, "claude", "a b"))
        self.assertTrue(tasks.resume_command(self.root, "claude", "abc-1").endswith("abc-1"))

    def test_a_list_that_starts_all_done_is_not_a_transition(self):
        self.assertFalse(self.rec(todo_write("s1", [todo("A", "completed")]))["became_all_done"])

    def test_hostile_session_ids_write_nothing_outside_the_tasks_directory(self):
        state = Path(tasks.tasks_dir(self.root, self.project_id)).parent
        before = sorted(p for p in state.rglob("*"))
        for hostile in ("../../evil", "a/b", "..", "x\\y"):
            self.assertFalse(self.rec(todo_write(hostile, [todo("A")]))["recorded"], hostile)
        self.assertEqual(sorted(p for p in state.rglob("*")), before)
        self.assertTrue(self.rec(todo_write("odd id: 1", [todo("A")]))["recorded"])
        written = list(tasks.tasks_dir(self.root, self.project_id).glob("*.json"))
        self.assertEqual(len(written), 1)
        self.assertEqual(written[0].parent.name, "task-board")

    def test_malformed_payloads_and_unbound_roots_are_a_quiet_no_op(self):
        for payload in (None, "junk", {"tool_name": "TodoWrite", "session_id": "s", "tool_input": []}, {}):
            self.assertFalse(self.rec(payload)["recorded"])
        unbound = self.new_project("not-bound")
        self.assertFalse(tasks.record(unbound, todo_write("s", [todo("A")]))["recorded"])

    def test_a_corrupt_record_is_never_overwritten(self):
        self.rec(todo_write("s1", [todo("A")]))
        path = tasks.record_path(self.root, self.project_id, "s1")
        path.write_text("{not json", encoding="utf-8")
        self.assertFalse(self.rec(todo_write("s1", [todo("A")]))["recorded"])
        self.assertEqual(path.read_text(encoding="utf-8"), "{not json")

    def test_a_record_after_session_end_revives_the_session(self):
        self.rec(todo_write("s1", [todo("A")]), now=T0)
        tasks.mark(self.root, {"session_id": "s1"}, "ended", now=T0 + 5)
        self.assertIsNotNone(self.load("s1")["ended_at"])
        self.rec(todo_write("s1", [todo("A", "in_progress")]), now=T0 + 9)
        self.assertIsNone(self.load("s1")["ended_at"])


class MarkAndDerivedStateTest(BoardCase):
    def session(self, now, **kwargs):
        return self.view(now=now, **kwargs)[0]["sessions"][0]

    def test_mark_is_a_no_op_without_a_record_and_reports_open_tasks(self):
        def marked(*args, **kwargs):
            result = tasks.mark(*args, **kwargs)
            return {"marked": result["marked"], "open": result["open"]}

        self.assertEqual(marked(self.root, {"session_id": "ghost"}, "idle"), {"marked": False, "open": 0})
        self.rec(todo_write("s1", [todo("A"), todo("B", "completed")]))
        self.assertEqual(marked(self.root, {"session_id": "s1"}, "ended", now=T0 + 1), {"marked": True, "open": 1})
        self.assertEqual(marked(self.root, {"session_id": "s1"}, "bogus"), {"marked": False, "open": 0})

    def test_status_active_then_idle_then_active_again(self):
        self.rec(todo_write("s1", [todo("A")]), now=T0)
        self.assertEqual(self.session(T0 + 1)["status"], "active")
        tasks.mark(self.root, {"session_id": "s1"}, "idle", now=T0 + 5)
        self.assertEqual(self.session(T0 + 6)["status"], "idle")
        self.rec(todo_write("s1", [todo("A", "in_progress")]), now=T0 + 8)
        self.assertEqual(self.session(T0 + 9)["status"], "active")

    def test_a_session_unseen_for_the_ended_threshold_is_ended(self):
        self.rec(todo_write("s1", [todo("A")]), now=T0)
        self.assertEqual(self.session(T0 + 21600)["status"], "active")
        self.assertEqual(self.session(T0 + 21601)["status"], "ended")
        self.assertEqual(self.session(T0 + 100, ended_after=50)["status"], "ended")

    def test_stale_only_when_in_progress_long_enough_in_a_live_session(self):
        self.rec(todo_write("s1", [todo("A", "in_progress"), todo("B")]), now=T0)
        fresh = self.session(T0 + 3600)["tasks"]
        self.assertEqual([t["stale"] for t in fresh], [False, False])
        aged = self.session(T0 + 3601)
        self.assertEqual([t["stale"] for t in aged["tasks"]], [True, False])
        self.assertEqual(self.view(now=T0 + 3601)[0]["stale"], 1)
        self.assertEqual(self.session(T0 + 200, stale_after=100)["tasks"][0]["stale"], True)

    def test_an_ended_session_flags_open_tasks_abandoned_not_stale(self):
        self.rec(todo_write("s1", [todo("A", "in_progress"), todo("B"), todo("C", "completed")]), now=T0)
        tasks.mark(self.root, {"session_id": "s1"}, "ended", now=T0 + 100)
        project = self.view(now=T0 + 99999)[0]
        flags = {t["content"]: (t["stale"], t["abandoned"]) for t in project["sessions"][0]["tasks"]}
        self.assertEqual(flags, {"A": (False, True), "B": (False, True), "C": (False, False)})
        self.assertEqual((project["abandoned"], project["stale"], project["sessions_active"]), (2, 0, 0))
        durations = project["sessions"][0]["tasks"][0]["durations"]
        self.assertEqual(durations["in_progress"], 100)  # stops running when the session ended

    def test_since_drops_sessions_idle_before_it(self):
        self.rec(todo_write("old", [todo("A")]), now=T0)
        self.rec(todo_write("new", [todo("B")]), now=T0 + 1000)
        sessions = self.view(now=T0 + 1001, since=T0 + 500)[0]["sessions"]
        self.assertEqual([s["session_id"] for s in sessions], ["new"])
        self.assertEqual(self.view(now=T0 + 1001, since=T0 + 5000), [])


class CollectTest(BoardCase):
    def fill(self, root, sessions):
        for index, (provider_tool, count) in enumerate(sessions):
            session = "s{}-{}".format(index, root.name)
            items = [todo("task {}".format(n), ("completed", "in_progress", "pending")[n % 3]) for n in range(count)]
            if provider_tool == "codex":
                payload = codex_plan(session, [(i["content"], i["status"]) for i in items])
            else:
                payload = todo_write(session, items)
            tasks.record(root, payload, now=T0 + index)

    def test_two_projects_aggregate_and_a_project_without_tasks_is_absent(self):
        root_b, id_b = self.bound("proj-b")
        self.bound("proj-empty")
        self.fill(self.root, [("claude", 3), ("codex", 5), ("claude", 2)])
        self.fill(root_b, [("claude", 3), ("claude", 2)])
        board = tasks.collect(now=T0 + 60)
        self.assertEqual({p["root"] for p in board["projects"]}, {str(self.root.resolve()), str(root_b.resolve())})
        by_root = {p["root"]: p for p in board["projects"]}
        a, b = by_root[str(self.root.resolve())], by_root[str(root_b.resolve())]
        self.assertEqual((a["counts"]["total"], b["counts"]["total"]), (10, 5))
        self.assertEqual((a["sessions_total"], b["sessions_total"]), (3, 2))
        self.assertEqual(a["providers"], ["claude", "codex"])
        self.assertEqual(b["providers"], ["claude"])
        for project in (a, b):
            counts = project["counts"]
            self.assertEqual(counts["todo"] + counts["in_progress"] + counts["done"], counts["total"])
            self.assertEqual(counts["total"], sum(s["counts"]["total"] for s in project["sessions"]))
        # 3 tasks: statuses cycle completed, in_progress, pending -> 1/1/1
        self.assertEqual(
            [(s["counts"]["done"], s["counts"]["in_progress"], s["counts"]["todo"]) for s in b["sessions"] if s["counts"]["total"] == 3],
            [(1, 1, 1)],
        )
        self.assertEqual({p["project_id"] for p in board["projects"]}, {self.project_id, id_b})

    def test_shape_matches_the_documented_contract(self):
        self.fill(self.root, [("claude", 2)])
        board = tasks.collect(now=T0 + 60)
        self.assertEqual(set(board), {"generated_at", "stale_after", "ended_after", "projects"})
        project = board["projects"][0]
        self.assertEqual(
            set(project),
            {"project_id", "root", "providers", "sessions_total", "sessions_active", "counts", "stale",
             "abandoned", "last_activity_at", "sessions", "with_findings", "as_of"},
        )
        session = project["sessions"][0]
        self.assertEqual(
            set(session),
            {"session_id", "provider", "branch", "cwd", "status", "created_at", "last_activity_at", "ended_at",
             "resume_command", "counts", "tasks"},
        )
        self.assertEqual(
            set(session["tasks"][0]),
            {"key", "content", "owner", "agent_type", "status", "column", "created_at", "status_since",
             "completed_at", "durations", "stale", "abandoned", "review"},
        )
        self.assertEqual(set(session["counts"]), {"todo", "in_progress", "done", "in_review", "total"})
        self.assertTrue(session["resume_command"].startswith("cd "))
        self.assertIn("claude --resume", session["resume_command"])

    def test_projects_and_sessions_sort_by_recent_activity_and_the_project_filter_applies(self):
        root_b, id_b = self.bound("proj-b")
        tasks.record(self.root, todo_write("old", [todo("A")]), now=T0)
        tasks.record(root_b, todo_write("new", [todo("B")]), now=T0 + 500)
        self.assertEqual([p["project_id"] for p in tasks.collect(now=T0 + 600)["projects"]], [id_b, self.project_id])
        only = tasks.collect(project_ids=[self.project_id], now=T0 + 600)["projects"]
        self.assertEqual([p["project_id"] for p in only], [self.project_id])

    def test_a_malformed_record_file_is_skipped_not_fatal(self):
        self.fill(self.root, [("claude", 2)])
        (tasks.tasks_dir(self.root, self.project_id) / "junk.json").write_text("{", encoding="utf-8")
        self.assertEqual(tasks.collect(now=T0 + 60)["projects"][0]["counts"]["total"], 2)


class WatchTest(BoardCase):
    def run_watch(self, act, until, **kwargs):
        events = []
        stop = tasks._Stop()
        thread = threading.Thread(
            target=tasks.watch,
            args=(events.append,),
            kwargs=dict(interval=0.02, stop=stop, watch_stdin=False, **kwargs),
        )
        thread.start()
        deadline = time.time() + 5
        while not any(e["event"] == "ready" for e in events) and time.time() < deadline:
            time.sleep(0.02)
        act()
        while not until(events) and time.time() < deadline:
            time.sleep(0.02)
        stop.set("test")
        thread.join(5)
        return events

    def test_backlog_then_ready_then_a_snapshot_per_change_then_end(self):
        tasks.record(self.root, todo_write("s1", [todo("A")]))
        time.sleep(0.05)

        def act():
            tasks.record(self.root, todo_write("s1", [todo("A", "in_progress")]))

        def changed(events):
            return any(
                e["event"] == "snapshot" and e["project"]["counts"]["in_progress"] == 1 for e in events
            )

        events = self.run_watch(act, changed)
        kinds = [e["event"] for e in events]
        self.assertEqual(kinds[0], "snapshot")
        self.assertEqual(kinds[1], "ready")
        self.assertEqual(kinds[-1], "end")
        self.assertEqual(events[-1]["reason"], "test")
        self.assertEqual(events[0]["project"]["project_id"], self.project_id)
        self.assertEqual(events[0]["project"]["counts"]["todo"], 1)
        self.assertTrue(changed(events))

    def test_a_project_without_tasks_emits_nothing_until_it_has_one(self):
        events = self.run_watch(
            lambda: tasks.record(self.root, todo_write("s1", [todo("A")])),
            lambda ev: any(e["event"] == "snapshot" for e in ev),
        )
        kinds = [e["event"] for e in events]
        self.assertLess(kinds.index("ready"), kinds.index("snapshot"))

    def test_time_alone_can_flip_a_task_to_stale_and_is_re_emitted(self):
        tasks.record(self.root, todo_write("s1", [todo("A", "in_progress")]), now=int(time.time()) - 100)
        events = self.run_watch(
            lambda: None,
            lambda ev: any(e["event"] == "snapshot" and e["project"]["stale"] == 1 for e in ev),
            stale_after=100, refresh=0.05,
        )
        self.assertTrue(any(e["event"] == "snapshot" and e["project"]["stale"] == 1 for e in events))

    def test_heartbeat_is_emitted(self):
        events = self.run_watch(lambda: time.sleep(0.15), lambda ev: any(e["event"] == "heartbeat" for e in ev), heartbeat=0.05)
        self.assertTrue(any(e["event"] == "heartbeat" for e in events))


class CliTest(BoardCase):
    def hook(self, *argv, payload):
        code, out, err = self.run_cli(*argv, input_text=json.dumps(payload) if not isinstance(payload, str) else payload)
        return code, out, err

    def test_record_mark_list_end_to_end_through_the_real_entry_point(self):
        code, out, err = self.hook(
            "--json", "tasks", "record", "--project-root", str(self.root),
            payload=todo_write("s1", [todo("A", "in_progress"), todo("B")], cwd=str(self.root)),
        )
        self.assertEqual(code, 0, err)
        body = json.loads(out)
        self.assertEqual(
            {k: body[k] for k in ("recorded", "session", "all_done", "became_all_done")},
            {"recorded": True, "session": "s1", "all_done": False, "became_all_done": False},
        )
        code, out, _ = self.hook("--json", "tasks", "mark", "--project-root", str(self.root), "--state", "ended", payload={"session_id": "s1"})
        self.assertEqual((code, json.loads(out)["open"], json.loads(out)["marked"]), (0, 2, True))
        code, out, _ = self.run_cli("--json", "tasks", "list")
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertTrue(data["ok"])
        project = data["projects"][0]
        self.assertEqual((project["counts"]["total"], project["abandoned"], project["sessions"][0]["status"]), (2, 2, "ended"))

    def test_record_and_mark_exit_zero_on_garbage_input(self):
        for stdin in ("", "not json", "[1,2]", "null", json.dumps({"tool_name": "TodoWrite"})):
            code, out, _ = self.run_cli("--json", "tasks", "record", "--project-root", str(self.root), input_text=stdin)
            self.assertEqual(code, 0, stdin)
            self.assertFalse(json.loads(out)["recorded"])
            code, out, _ = self.run_cli("--json", "tasks", "mark", "--project-root", str(self.root), "--state", "idle", input_text=stdin)
            self.assertEqual(code, 0, stdin)
            self.assertFalse(json.loads(out)["marked"])
        code, out, _ = self.run_cli("--json", "tasks", "record", "--project-root", str(self.root / "missing"), input_text="{}")
        self.assertEqual(code, 0)
        self.assertFalse(json.loads(out)["recorded"])

    def test_list_stamps_every_project_with_the_time_its_view_was_computed(self):
        tasks.record(self.root, todo_write("s1", [todo("A", "in_progress")]), now=T0)
        before = int(time.time())
        code, out, _ = self.run_cli("--json", "tasks", "list")
        data = json.loads(out)
        self.assertEqual(code, 0)
        for project in data["projects"]:
            self.assertIsInstance(project["as_of"], int)
            self.assertEqual(project["as_of"], data["generated_at"])
            self.assertGreaterEqual(project["as_of"], before)

    def test_as_of_is_the_view_clock_and_never_makes_an_unchanged_view_differ(self):
        self.rec(todo_write("s1", [todo("A")]), now=T0)
        first = self.view(now=T0 + 10)[0]
        second = self.view(now=T0 + 20)[0]
        self.assertEqual((first["as_of"], second["as_of"]), (T0 + 10, T0 + 20))

    def test_list_accepts_the_documented_filters(self):
        tasks.record(self.root, todo_write("s1", [todo("A", "in_progress")]), now=int(time.time()) - 120)
        code, out, _ = self.run_cli("--json", "tasks", "list", "--project", self.project_id, "--since", "0", "--stale-after", "60", "--ended-after", "99999")
        data = json.loads(out)
        self.assertEqual((code, data["stale_after"], data["ended_after"]), (0, 60, 99999))
        self.assertEqual(data["projects"][0]["stale"], 1)

    def test_watch_streams_json_lines_and_ends_when_stdin_closes(self):
        tasks.record(self.root, todo_write("s1", [todo("A")]))
        proc = subprocess.Popen(
            [sys.executable, str(CLI), "--json", "tasks", "watch", "--interval", "0.05"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=dict(os.environ),
        )
        lines = [json.loads(proc.stdout.readline()) for _ in range(2)]
        proc.stdin.close()
        rest = proc.stdout.read().decode().splitlines()
        code = proc.wait(timeout=10)
        stderr = proc.stderr.read()
        proc.stdout.close()
        proc.stderr.close()
        lines.extend(json.loads(line) for line in rest if line.strip())
        self.assertEqual(code, 0, stderr)
        self.assertEqual([lines[0]["event"], lines[1]["event"]], ["snapshot", "ready"])
        self.assertIsInstance(lines[0]["project"]["as_of"], int)
        self.assertEqual(lines[-1], {"event": "end", "reason": "stdin-closed", "ok": True})
        self.assertTrue(all(l["ok"] is True for l in lines))


@requires_bash()
class HookTest(BoardCase):
    def setUp(self):
        super().setUp()
        # The machine-local state directory the bound project's pointer resolves to.
        self.state = Path(tasks.tasks_dir(self.root, self.project_id)).parent
        self.state.mkdir(parents=True, exist_ok=True)
        self.shim = self.tmp / "shim"
        self.shim.mkdir()
        self.calls = self.tmp / "python-calls"
        real = shutil.which("python3")
        (self.shim / "python3").write_text(
            '#!/bin/sh\necho x >> "{}"\nexec "{}" "$@"\n'.format(self.calls, real), encoding="utf-8"
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

    def test_pre_tool_use_forks_no_python_for_any_other_tool(self):
        for payload in (
            {"tool_name": "Bash", "tool_input": {"command": "ls"}, "session_id": "s"},
            {"tool_name": "Bash", "tool_input": {"command": "echo update_plan todowrite"}, "session_id": "s"},
            {"tool": "bash", "args": {"command": "todowrite"}, "sessionID": "s"},
            {"tool_name": "TodoWrite", "tool_input": {"todos": []}, "session_id": "s"},  # Claude: post hook's job
            {"tool_name": "Read", "tool_input": {"file_path": "/tmp/update_plan"}, "session_id": "s"},
        ):
            result = self.run_script(PRE_TOOL_USE, payload)
            self.assertEqual((result.stdout, result.stderr), (b"", b""))
        self.assertEqual(self.python_calls(), 0)
        self.assertEqual(list((self.state / "task-board").glob("*")) if (self.state / "task-board").exists() else [], [])

    def test_pre_tool_use_records_codex_and_opencode_todo_calls(self):
        self.assertEqual(self.run_script(PRE_TOOL_USE, codex_plan("c1", [("Ship", "in_progress")])).stdout, b"")
        self.run_script(PRE_TOOL_USE, opencode_todos("o1", [("a", "Thing", "pending")]))
        self.assertEqual(self.load("c1")["provider"], "codex")
        self.assertEqual(self.load("o1")["provider"], "opencode")
        self.assertEqual(self.python_calls(), 2)

    def test_the_exact_payload_codex_sends_for_update_plan_is_recorded_through_the_dispatcher(self):
        # Field for field what codex-rs/hooks/src/events/pre_tool_use.rs `command_input_json`
        # serializes (openai/codex @ 92bc601), compact as serde_json writes it: the registry's
        # default `pre_tool_use_payload` hands `update_plan` over with its parsed arguments.
        def payload(plan, **subagent):
            body = dict(
                session_id="0199a0b1-7c3e-7f00-9d1a-4b2c8e6f5a10", turn_id="turn-1", **subagent,
                transcript_path=None, cwd=str(self.root), hook_event_name="PreToolUse",
                model="gpt-5-codex", permission_mode="default", tool_name="update_plan",
                tool_input={"explanation": None, "plan": [{"step": s, "status": st} for s, st in plan]},
                tool_use_id="call_1",
            )
            return json.dumps(body, separators=(",", ":"))

        dispatcher = HOOKS / "pre-tool-use.sh"
        self.run_script(dispatcher, payload([("Read the spec", "completed"), ("Write it", "in_progress")]))
        self.run_script(dispatcher, payload([("Explore", "pending")], agent_id="019a-sub", agent_type="explorer"))
        record = self.load("0199a0b1-7c3e-7f00-9d1a-4b2c8e6f5a10")
        self.assertEqual(record["provider"], "codex")
        by_owner = {(t["owner"], t["content"]): t["status"] for t in record["tasks"]}
        self.assertEqual(by_owner, {
            ("main", "Read the spec"): "completed",
            ("main", "Write it"): "in_progress",
            ("019a-sub", "Explore"): "pending",
        })

    def test_post_tool_use_records_claude_todos_and_raises_session_done_once(self):
        first = todo_write("s1", [todo("A"), todo("B")], cwd=str(self.root))
        done = todo_write("s1", [todo("A", "completed"), todo("B", "completed")], cwd=str(self.root))
        self.assertEqual(self.run_script(POST_TOOL_USE, first).stdout, b"")
        self.run_script(POST_TOOL_USE, done)
        self.run_script(POST_TOOL_USE, first)
        self.run_script(POST_TOOL_USE, done)
        codes = [r["code"] for r in self.queue()]
        self.assertEqual(codes, ["tasks.session_done"])
        self.assertEqual(self.queue()[0]["session_id"], "s1")

    def test_post_tool_use_dispatcher_runs_the_sub_script(self):
        self.run_script(POST_DISPATCHER, todo_write("s1", [todo("A")], cwd=str(self.root)))
        self.assertEqual(len(self.load("s1")["tasks"]), 1)

    def test_post_tool_use_ignores_a_non_todo_tool(self):
        self.run_script(POST_TOOL_USE, {"tool_name": "Edit", "session_id": "s1", "tool_input": {}})
        self.assertEqual(self.python_calls(), 0)

    def test_session_end_marks_ended_and_raises_abandoned_only_with_open_tasks(self):
        self.run_script(POST_TOOL_USE, todo_write("s1", [todo("A"), todo("B", "completed")]))
        self.run_script(SESSION_END, {"session_id": "s1", "hook_event_name": "SessionEnd"})
        self.assertIsNotNone(self.load("s1")["ended_at"])
        self.assertEqual([r["code"] for r in self.queue()], ["tasks.session_abandoned"])
        self.run_script(POST_TOOL_USE, todo_write("s2", [todo("A", "completed")]))
        self.run_script(SESSION_END, {"session_id": "s2"})
        self.assertEqual([r["code"] for r in self.queue()], ["tasks.session_abandoned"])

    def test_session_end_and_stop_fork_no_python_without_a_record(self):
        self.run_script(SESSION_END, {"session_id": "ghost"})
        payload = self.tmp / "stop.json"
        payload.write_text(json.dumps({"session_id": "ghost"}))
        self.run_script(STOP_SUB, "", {"DEVTEAM_HOOK_PAYLOAD": str(payload)})
        self.assertEqual(self.python_calls(), 0)

    def test_stop_marks_a_recorded_session_idle(self):
        self.run_script(POST_TOOL_USE, todo_write("s1", [todo("A")]))
        before = self.python_calls()
        payload = self.tmp / "stop.json"
        payload.write_text(json.dumps({"session_id": "s1"}))
        result = self.run_script(STOP_SUB, "", {"DEVTEAM_HOOK_PAYLOAD": str(payload)})
        self.assertEqual(result.stdout, b"")
        self.assertEqual(self.python_calls(), before + 1)
        self.assertIsNotNone(self.load("s1")["idle_at"])

    def test_a_hook_run_from_a_subdirectory_records_into_the_main_project(self):
        sub = self.root / "pkg"
        sub.mkdir(parents=True)
        # An enclosing repository is what made a relative `--git-common-dir` resolve wrongly.
        subprocess.run(["git", "init", "-q", str(self.tmp)], check=True)
        self.run_script(POST_TOOL_USE, todo_write("s1", [todo("A")], cwd=str(sub)), cwd=sub)
        self.assertEqual(len(self.load("s1")["tasks"]), 1)
        self.run_script(SESSION_END, {"session_id": "s1"}, cwd=sub)
        self.assertIsNotNone(self.load("s1")["ended_at"])

    def test_a_layout_2_project_resolves_the_same_state_dir_in_bash_and_python(self):
        self.assertGreaterEqual(project.layout(self.root), project.LAYOUT_MEMORY_IN_STORE)
        expected = Path(project.state_dir(self.root, self.project_id))
        expected.mkdir(parents=True, exist_ok=True)
        resolved = subprocess.run(
            ["bash", "-c", '. "$1/lib/data-dirs.sh" && devteam_state_dir "$2"', "_", str(HOOKS), str(self.root)],
            stdout=subprocess.PIPE, check=True,
        ).stdout.decode().strip()
        self.assertEqual(Path(resolved).resolve(), expected.resolve())
        self.assertIn("machines", expected.parts)
        self.run_script(POST_TOOL_USE, todo_write("s1", [todo("A")], cwd=str(self.root)))
        self.assertTrue((expected / "task-board" / "s1.json").is_file())
        self.assertEqual(len(self.load("s1")["tasks"]), 1)

    def test_every_hook_exits_zero_and_silent_on_garbage(self):
        for script in (PRE_TOOL_USE, POST_TOOL_USE, POST_DISPATCHER, SESSION_END):
            result = self.run_script(script, "not json at all")
            self.assertEqual((result.stdout, result.stderr), (b"", b""), script)

    def test_a_hostile_session_id_is_skipped_by_the_bash_side(self):
        self.run_script(SESSION_END, {"session_id": "../../etc/passwd"})
        self.assertEqual(self.python_calls(), 0)

    def test_notification_text_follows_the_language_preference(self):
        prefs = self.root / ".dev-team-agents" / "resolved"
        prefs.mkdir(parents=True, exist_ok=True)
        (prefs / "preferences.json").write_text(json.dumps({"language": "pt-BR"}), encoding="utf-8")
        self.run_script(POST_TOOL_USE, todo_write("s1", [todo("A")]))
        self.run_script(POST_TOOL_USE, todo_write("s1", [todo("A", "completed")]))
        self.assertIn("tarefas", self.queue()[0]["message"])

    def test_suppressed_notifications_are_not_queued(self):
        prefs = self.root / ".dev-team-agents" / "resolved"
        prefs.mkdir(parents=True, exist_ok=True)
        (prefs / "preferences.json").write_text(json.dumps({"suppress_notifications": True}), encoding="utf-8")
        self.run_script(POST_TOOL_USE, todo_write("s1", [todo("A")]))
        self.run_script(POST_TOOL_USE, todo_write("s1", [todo("A", "completed")]))
        self.assertEqual(self.queue(), [])


def lots(prefix, n, status="pending"):
    return [todo("{}{}".format(prefix, i), status) for i in range(1, n + 1)]


class ReviewRegressionTest(BoardCase):
    def session(self, now=T0 + 10, **kwargs):
        return self.view(now=now, **kwargs)[0]["sessions"][0]

    def test_more_than_nine_tasks_created_in_one_second_keep_their_creation_order(self):
        self.rec(todo_write("s1", lots("task ", 12)))
        views = self.session()["tasks"]
        self.assertEqual([t["key"] for t in views], ["t{}".format(i) for i in range(1, 13)])
        self.assertEqual(views[9]["content"], "task 10")

    def test_resume_command_uses_the_recorded_cwd_when_it_still_exists(self):
        sub = self.root / "wt dir"
        sub.mkdir()
        self.rec(todo_write("s1", [todo("A")], cwd=str(sub)))
        project = self.view()[0]
        command = self.session()["resume_command"]
        self.assertEqual(command, "cd {} && claude --resume s1".format(shlex.quote(str(sub))))
        self.assertEqual(len(command.splitlines()), 1)
        self.assertNotIn(shlex.quote(project["root"]) + " &&", command)

    def test_resume_command_falls_back_to_the_root_for_a_missing_or_absent_cwd(self):
        self.rec(todo_write("s1", [todo("A")], cwd=str(self.root / "gone")))
        self.rec(todo_write("s2", [todo("A")]), now=T0 + 1)
        root = self.view()[0]["root"]
        for session in self.view()[0]["sessions"]:
            self.assertEqual(session["resume_command"], "cd {} && claude --resume {}".format(shlex.quote(root), session["session_id"]))

    def test_a_non_empty_list_with_nothing_readable_does_not_wipe_the_owners_tasks(self):
        self.rec(todo_write("s1", [todo("A"), todo("B")]))
        result = self.rec(todo_write("s1", [1, "x", {"status": "pending"}, None]), now=T0 + 5)
        self.assertFalse(result["recorded"])
        self.assertEqual([t["removed_at"] for t in self.load("s1")["tasks"]], [None, None])
        self.assertEqual(self.load("s1")["updated_at"], T0)
        self.assertEqual(tasks._items([1, "x"]), None)

    def test_a_genuinely_empty_list_still_clears(self):
        self.rec(todo_write("s1", [todo("A")]))
        self.assertTrue(self.rec(todo_write("s1", []), now=T0 + 5)["recorded"])
        self.assertIsNotNone(self.load("s1")["tasks"][0]["removed_at"])

    def test_an_update_prefers_the_task_of_the_same_owner(self):
        self.rec(task_create("s1", "main one", {"id": "1"}))
        sub = task_create("s1", "sub one", {"id": "1"})
        sub.update(agent_id="ag-1", agent_type="Explore")
        self.rec(sub, now=T0 + 1)
        update = task_update("s1", "1", "completed")
        update.update(agent_id="ag-1", agent_type="Explore")
        self.rec(update, now=T0 + 2)
        by = {t["owner"]: t["status"] for t in self.load("s1")["tasks"]}
        self.assertEqual(by, {"main": "pending", "ag-1": "completed"})

    def test_an_update_falls_back_to_another_owners_task_when_the_owner_has_none(self):
        self.rec(task_create("s1", "main one", {"id": "1"}))
        update = task_update("s1", "1", "in_progress")
        update.update(agent_id="ag-2", agent_type="Explore")
        self.rec(update, now=T0 + 1)
        recorded = self.load("s1")["tasks"]
        self.assertEqual([(t["owner"], t["status"]) for t in recorded], [("main", "in_progress")])

    def test_a_created_task_without_an_id_takes_the_next_session_wide_number(self):
        self.rec(task_create("s1", "main", {"id": "1"}))
        sub = task_create("s1", "sub", {"id": "2"})
        sub.update(agent_id="ag-1", agent_type="Explore")
        self.rec(sub, now=T0 + 1)
        self.rec(task_create("s1", "unnumbered"), now=T0 + 2)
        self.assertEqual([t["id"] for t in self.load("s1")["tasks"]], ["1", "2", "3"])

    def write_raw(self, name, body):
        directory = tasks.tasks_dir(self.root, self.project_id)
        directory.mkdir(parents=True, exist_ok=True)
        (directory / name).write_text(json.dumps(body), encoding="utf-8")

    def test_one_structurally_bad_record_does_not_hide_the_projects_other_sessions(self):
        self.rec(todo_write("good", [todo("A")]))
        bad_task = {"key": "t1", "content": "x", "owner": "main", "created_at": T0}  # no status / removed_at
        self.write_raw("bad1.json", dict(self.load("good"), session_id="bad1", tasks=[bad_task]))
        self.write_raw("bad2.json", dict(self.load("good"), session_id="bad2", last_seen_at=None))
        self.write_raw("bad3.json", dict(self.load("good"), session_id="bad3", tasks=["nope"]))
        sessions = self.view()[0]["sessions"]
        self.assertEqual([s["session_id"] for s in sessions], ["good"])

    def test_a_record_that_passes_validation_but_breaks_the_view_is_skipped_per_record(self):
        self.rec(todo_write("good", [todo("A")]))
        broken = self.load("good")
        broken.update(session_id="odd")
        broken["tasks"][0]["history"] = [{"at": T0}]  # no status: fails only when durations are derived
        self.write_raw("odd.json", broken)
        self.assertEqual([s["session_id"] for s in self.view()[0]["sessions"]], ["good"])
        events = []
        stop = tasks._Stop()
        stop.set("test")
        tasks.watch(events.append, watch_stdin=False, stop=stop)
        self.assertEqual(events[-1]["event"], "end")

    def test_an_unreadable_record_is_never_overwritten_by_record(self):
        self.rec(todo_write("s1", [todo("A")]))
        path = tasks.record_path(self.root, self.project_id, "s1")
        damaged = self.load("s1")
        damaged["last_seen_at"] = None
        path.write_text(json.dumps(damaged), encoding="utf-8")
        self.assertFalse(self.rec(todo_write("s1", [todo("B")]), now=T0 + 5)["recorded"])
        self.assertEqual(json.loads(path.read_text(encoding="utf-8")), damaged)

    def test_git_runs_outside_the_session_lock(self):
        def slow_branch(cwd):
            time.sleep(0.4)
            return "feat/x"

        results = []
        with mock.patch.object(tasks, "_git_branch", slow_branch), mock.patch.object(tasks, "LOCK_TIMEOUT", 0.2):
            threads = [
                threading.Thread(target=lambda n=n: results.append(
                    self.rec(task_create("s1", "task {}".format(n), {"id": str(n)}), now=T0 + n)["recorded"]))
                for n in (1, 2)
            ]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()
        self.assertEqual(results, [True, True])
        self.assertEqual(len(self.load("s1")["tasks"]), 2)
        self.assertEqual(self.load("s1")["branch"], "feat/x")

    def test_racing_records_lose_no_update(self):
        errors = []

        def worker(owner, count):
            for n in range(count):
                payload = task_create("s1", "{} task {}".format(owner, n), {"id": "{}-{}".format(owner, n)})
                if owner != "main":
                    payload.update(agent_id=owner, agent_type="Explore")
                if not self.rec(payload, now=T0 + n)["recorded"]:
                    errors.append((owner, n))

        threads = [threading.Thread(target=worker, args=(owner, 8)) for owner in ("main", "ag-1", "ag-2")]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(errors, [])
        self.assertEqual(len(self.load("s1")["tasks"]), 24)

    def test_a_record_racing_a_mark_loses_neither(self):
        self.rec(todo_write("s1", [todo("seed")]))
        failures = []

        def recorder():
            for n in range(10):
                if not self.rec(task_create("s1", "t{}".format(n), {"id": str(n)}), now=T0 + n)["recorded"]:
                    failures.append(n)

        def marker():
            for _ in range(10):
                if not tasks.mark(self.root, {"session_id": "s1"}, "idle", now=T0 + 3)["marked"]:
                    failures.append("mark")

        threads = [threading.Thread(target=recorder), threading.Thread(target=marker)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(failures, [])
        self.assertEqual(len(self.load("s1")["tasks"]), 11)

    def test_activity_in_the_same_second_as_an_idle_mark_shows_the_session_active(self):
        self.rec(todo_write("s1", [todo("A")]), now=T0)
        tasks.mark(self.root, {"session_id": "s1"}, "idle", now=T0 + 5)
        self.assertEqual(self.session(now=T0 + 6)["status"], "idle")
        self.rec(todo_write("s1", [todo("A", "in_progress")]), now=T0 + 5)
        self.assertIsNone(self.load("s1")["idle_at"])
        self.assertEqual(self.session(now=T0 + 6)["status"], "active")
        tasks.mark(self.root, {"session_id": "s1"}, "idle", now=T0 + 7)
        self.assertEqual(self.session(now=T0 + 8)["status"], "idle")

    def test_a_task_removed_after_completing_is_not_revived_by_an_equal_item(self):
        self.rec(todo_write("s1", [todo("Ship", "completed")]), now=T0)
        self.rec(todo_write("s1", []), now=T0 + 1)
        self.rec(todo_write("s1", [todo("Ship")]), now=T0 + 2)
        recorded = self.load("s1")["tasks"]
        self.assertEqual([(t["status"], t["removed_at"] is None) for t in recorded], [("completed", False), ("pending", True)])

    def test_a_task_removed_before_finishing_is_still_revived(self):
        self.rec(todo_write("s1", [todo("Ship")]), now=T0)
        self.rec(todo_write("s1", []), now=T0 + 1)
        self.rec(todo_write("s1", [todo("Ship", "in_progress")]), now=T0 + 2)
        recorded = self.load("s1")["tasks"]
        self.assertEqual([(t["status"], t["removed_at"]) for t in recorded], [("in_progress", None)])


class HooksWiringTest(StoreTestCase):
    def setUp(self):
        super().setUp()
        self.root = self.tmp / "wired"
        (self.root / ".claude").mkdir(parents=True)
        self.settings = self.root / ".claude" / "settings.json"

    def read(self):
        return json.loads(self.settings.read_text(encoding="utf-8"))

    def ours(self, data, event):
        return [e for e in data["hooks"].get(event, []) if hooks._is_devteam_entry(e, dict(hooks.EVENTS)[event])]

    def test_wire_registers_post_tool_use_narrowed_and_session_end(self):
        hooks.wire(self.root)
        data = self.read()
        (post,) = self.ours(data, "PostToolUse")
        self.assertEqual(post["matcher"], "TodoWrite|TaskCreate|TaskUpdate|Agent|Task")
        self.assertIn("post-tool-use.sh", post["hooks"][0]["command"])
        (end,) = self.ours(data, "SessionEnd")
        self.assertNotIn("matcher", end)
        self.assertIn("session-end.sh", end["hooks"][0]["command"])

    def test_wire_is_idempotent_and_keeps_foreign_entries(self):
        foreign_post = {"matcher": "Bash", "hooks": [{"type": "command", "command": "echo mine"}]}
        foreign_end = {"hooks": [{"type": "command", "command": "notify-me"}]}
        self.settings.write_text(json.dumps({"hooks": {"PostToolUse": [foreign_post], "SessionEnd": [foreign_end]}, "x": 1}))
        hooks.wire(self.root)
        first = self.settings.read_text()
        hooks.wire(self.root)
        self.assertEqual(self.settings.read_text(), first)
        data = self.read()
        self.assertEqual(len(self.ours(data, "PostToolUse")), 1)
        self.assertEqual(len(self.ours(data, "SessionEnd")), 1)
        self.assertIn(foreign_post, data["hooks"]["PostToolUse"])
        self.assertIn(foreign_end, data["hooks"]["SessionEnd"])
        self.assertEqual(data["x"], 1)

    def test_wire_rewrites_a_previously_shipped_post_tool_use_matcher_in_place(self):
        hooks.wire(self.root)
        data = self.read()
        data["hooks"]["PostToolUse"][0]["matcher"] = "TodoWrite|TaskCreate|TaskUpdate"
        self.settings.write_text(json.dumps(data))
        hooks.wire(self.root)
        entries = self.read()["hooks"]["PostToolUse"]
        self.assertEqual([e["matcher"] for e in entries], ["TodoWrite|TaskCreate|TaskUpdate|Agent|Task"])

    def test_wire_keeps_a_matcher_the_user_customized_and_warns(self):
        hooks.wire(self.root)
        data = self.read()
        data["hooks"]["PostToolUse"][0]["matcher"] = "TodoWrite"
        # A stale command path on the same entry is still refreshed; the matcher is not.
        data["hooks"]["PostToolUse"][0]["hooks"][0]["command"] = hooks.command_for("post-tool-use.sh").replace(
            hooks.HOOK_DIR, hooks.CORE_POINTER_HOOK_DIR
        )
        self.settings.write_text(json.dumps(data))
        notes = []

        class Emitter:
            def warn(self, message):
                notes.append(message)

        hooks.wire(self.root, emitter=Emitter())
        (post,) = self.ours(self.read(), "PostToolUse")
        self.assertEqual(post["matcher"], "TodoWrite")
        self.assertEqual(post["hooks"][0]["command"], hooks.command_for("post-tool-use.sh"))
        self.assertTrue(any("PostToolUse" in n and "TodoWrite" in n for n in notes), notes)

    def test_wire_warns_on_stderr_without_an_emitter_and_stays_idempotent(self):
        import contextlib
        import io

        hooks.wire(self.root)
        data = self.read()
        data["hooks"]["PostToolUse"][0]["matcher"] = ".*"
        self.settings.write_text(json.dumps(data))
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            hooks.wire(self.root)
        self.assertIn("PostToolUse", err.getvalue())
        first = self.settings.read_text()
        with contextlib.redirect_stderr(io.StringIO()):
            hooks.wire(self.root)
        self.assertEqual(self.settings.read_text(), first)
        self.assertEqual(self.ours(self.read(), "PostToolUse")[0]["matcher"], ".*")

    def test_unwire_removes_only_our_two_new_events_entries(self):
        foreign_post = {"matcher": "Bash", "hooks": [{"type": "command", "command": "echo mine"}]}
        foreign_end = {"hooks": [{"type": "command", "command": "notify-me"}]}
        self.settings.write_text(json.dumps({"hooks": {"PostToolUse": [foreign_post], "SessionEnd": [foreign_end]}}))
        hooks.wire(self.root)
        removed = hooks.unwire(self.root)
        self.assertIn("PostToolUse", removed)
        self.assertIn("SessionEnd", removed)
        data = self.read()
        self.assertEqual(data["hooks"], {"PostToolUse": [foreign_post], "SessionEnd": [foreign_end]})

    def test_unwire_drops_an_event_that_held_only_our_entry(self):
        hooks.wire(self.root)
        hooks.unwire(self.root)
        self.assertNotIn("hooks", self.read())


@requires_bash()
class InstallInjectHookTest(StoreTestCase):
    """`install.sh`'s `_inject_hook`, extracted verbatim, against an existing settings.json."""

    POST = "env -u BASH_ENV -u ENV .dev-team-agents/scripts/hooks/post-tool-use.sh"
    END = "env -u BASH_ENV -u ENV .dev-team-agents/scripts/hooks/session-end.sh"

    def setUp(self):
        super().setUp()
        text = (REPO_ROOT / "scripts" / "install.sh").read_text(encoding="utf-8")
        start = text.index("    _inject_hook() {")
        end = text.index("\n    }\n", start) + len("\n    }\n")
        self.function = text[start:end]
        self.settings = self.tmp / "settings.json"

    def inject(self):
        script = self.function + (
            '_inject_hook "PostToolUse" "$POST" "hooks/post-tool-use.sh"\n'
            '_inject_hook "SessionEnd" "$END" "hooks/session-end.sh"\n'
        )
        subprocess.run(
            ["bash", "-c", script],
            env=dict(os.environ, SETTINGS_FILE=str(self.settings), POST=self.POST, END=self.END),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True,
        )

    def test_the_two_new_events_are_injected_once_beside_foreign_entries(self):
        foreign = {"hooks": [{"type": "command", "command": "echo keep"}]}
        self.settings.write_text(json.dumps({"hooks": {"PostToolUse": [foreign]}, "other": True}))
        self.inject()
        first = self.settings.read_text()
        self.inject()
        self.assertEqual(self.settings.read_text(), first)
        data = json.loads(first)
        post = data["hooks"]["PostToolUse"]
        self.assertEqual(post[0], foreign)
        self.assertEqual(len(post), 2)
        self.assertEqual(post[1]["matcher"], "TodoWrite|TaskCreate|TaskUpdate|Agent|Task")
        self.assertEqual(post[1]["hooks"][0]["command"], self.POST)
        self.assertEqual(data["hooks"]["SessionEnd"], [{"hooks": [{"type": "command", "command": self.END}]}])
        self.assertTrue(data["other"])

    def widen(self, matcher, command=None):
        entry = {"matcher": matcher, "hooks": [{"type": "command", "command": command or self.POST}]}
        self.settings.write_text(json.dumps({"hooks": {"PostToolUse": [entry]}}))
        result = subprocess.run(
            ["bash", "-c", self.function + '_inject_hook "PostToolUse" "$POST" "hooks/post-tool-use.sh"\n'],
            env=dict(os.environ, SETTINGS_FILE=str(self.settings), POST=self.POST),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True,
        )
        return json.loads(self.settings.read_text())["hooks"]["PostToolUse"], result.stderr.decode()

    def test_our_entry_with_a_matcher_we_shipped_before_is_widened(self):
        post, _ = self.widen("TodoWrite|TaskCreate|TaskUpdate")
        self.assertEqual([e["matcher"] for e in post], ["TodoWrite|TaskCreate|TaskUpdate|Agent|Task"])

    def test_our_entry_with_the_users_own_matcher_is_left_alone_and_warned_about(self):
        for custom in (".*", "TodoWrite", "Bash|Edit"):
            post, warning = self.widen(custom)
            self.assertEqual([e["matcher"] for e in post], [custom], custom)
            self.assertIn("left as is", warning)

    def test_a_foreign_entry_is_never_widened(self):
        post, warning = self.widen("TodoWrite|TaskCreate|TaskUpdate", command="echo mine hooks-elsewhere")
        # Ours is added beside it; the foreign entry keeps its matcher.
        self.assertEqual(post[0]["matcher"], "TodoWrite|TaskCreate|TaskUpdate")
        self.assertEqual(post[0]["hooks"][0]["command"], "echo mine hooks-elsewhere")
        self.assertEqual(warning, "")

    def failure_block(self):
        text = (REPO_ROOT / "scripts" / "install.sh").read_text(encoding="utf-8")
        start = text.index('        python3 - "$SETTINGS_FILE" "$POST_TOOL_USE_HOOK" <<\'PYEOF\'\n') + len(
            '        python3 - "$SETTINGS_FILE" "$POST_TOOL_USE_HOOK" <<\'PYEOF\'\n')
        return text[start:text.index("\nPYEOF\n", start)]

    def test_the_failure_hook_is_injected_once_and_never_duplicated(self):
        self.settings.write_text(json.dumps({"hooks": {"PostToolUseFailure": [{"hooks": [{"type": "command", "command": "echo mine"}]}]}}))
        for _ in range(2):
            subprocess.run([sys.executable, "-c", self.failure_block(), str(self.settings), self.POST], check=True)
        entries = json.loads(self.settings.read_text())["hooks"]["PostToolUseFailure"]
        self.assertEqual(len(entries), 2)
        self.assertEqual((entries[1]["matcher"], entries[1]["hooks"][0]["command"]), ("Agent|Task", self.POST))


if __name__ == "__main__":
    unittest.main()
