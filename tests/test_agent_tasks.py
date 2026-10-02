"""Agent spawns are tasks (docs/specs/task-board.md § Agent spawns are tasks, ADR-0018 amendment).

Every non-built-in, non-review agent a session spawns is a task the hooks record with no agent
cooperation. These tests pin the cycle on every provider (spawn, result, background hand-back,
failure, Codex wait matched by agent id), what is excluded (built-ins, review agents), the
read-side rule that hides them behind a mirrored plan, the additive JSON, and that a call that
is not an agent forks no python.
"""

import datetime
import json
import subprocess
import unittest

from devteam_support import REPO_ROOT, requires_bash

from devteam import providers, review_triggers, tasks

import test_tasks as tt
from test_tasks import POST_TOOL_USE, PRE_TOOL_USE, STOP_SUB, T0, BoardCase, todo, todo_write

AGENT = "backend-developer"


def _claude(session, agent, call, **extra):
    base = {"session_id": session, "cwd": "", "tool_use_id": call, "tool_name": "Agent"}
    base["tool_input"] = {"description": "add the endpoint", "prompt": "p", "subagent_type": agent}
    base["tool_input"].update(extra.pop("input", {}))
    base.update(extra)
    return base


def claude_cycle(session, agent, call, **extra):
    spawn = dict(_claude(session, agent, call, **extra), hook_event_name="PreToolUse")
    end = dict(_claude(session, agent, call, **extra), hook_event_name="PostToolUse",
               tool_response={"content": [{"type": "text", "text": "done"}]})
    return spawn, [end]


def codex_cycle(session, agent, call, **extra):
    spawn = {
        "session_id": session, "cwd": "", "tool_use_id": call, "hook_event_name": "PreToolUse",
        "tool_name": "spawn_agent", "tool_input": {"agent_type": agent, "message": "add the endpoint\nmore"},
    }
    spawn.update(extra)
    ack = dict(spawn, hook_event_name="PostToolUse", tool_response={"agent_id": "ag-" + call, "nickname": None})
    wait = {
        "session_id": session, "cwd": "", "tool_use_id": "w-" + call, "hook_event_name": "PostToolUse",
        "tool_name": "wait_agent", "tool_input": {"targets": ["ag-" + call]},
        "tool_response": {"status": {"ag-" + call: {"completed": "done"}}, "timed_out": False},
    }
    return spawn, [ack, wait]


def opencode_cycle(session, agent, call, **extra):
    spawn = {"tool": "task", "sessionID": session, "tool_use_id": call,
             "args": {"description": "add the endpoint", "prompt": "p", "subagent_type": agent}}
    spawn.update(extra)
    return spawn, [dict(spawn, output="done")]


#: One cycle builder per provider in `providers.ALL_PROVIDERS`: a provider added without a case
#: fails `test_every_provider_has_its_agent_capture_decided` instead of shipping a board that
#: misses its agents.
CYCLES = {"claude": claude_cycle, "codex": codex_cycle, "opencode": opencode_cycle}


class ProviderParityTest(unittest.TestCase):
    def test_every_provider_has_its_agent_capture_decided(self):
        self.assertEqual(set(CYCLES), set(providers.ALL_PROVIDERS))
        self.assertEqual(set(review_triggers.BUILTIN_AGENTS), set(providers.ALL_PROVIDERS))

    def test_every_provider_lists_its_built_in_agents(self):
        for provider in providers.ALL_PROVIDERS:
            names = review_triggers.BUILTIN_AGENTS[provider]
            self.assertTrue(names, provider)
            for name in names:
                self.assertTrue(review_triggers.is_builtin(provider, name), (provider, name))
                self.assertTrue(review_triggers.is_builtin(provider, name.upper()), (provider, name))
            self.assertFalse(review_triggers.is_builtin(provider, AGENT), provider)
        self.assertTrue(review_triggers.is_builtin("claude", "Explore"))
        self.assertTrue(review_triggers.is_builtin("codex", "worker"))
        self.assertFalse(review_triggers.is_builtin("nope", "explore"))

    def test_a_review_agent_is_never_a_built_in(self):
        for provider in providers.ALL_PROVIDERS:
            for name in review_triggers.REVIEW_AGENTS:
                self.assertFalse(review_triggers.is_builtin(provider, name), (provider, name))


class AgentTaskTest(BoardCase):
    def agents(self, session="s1"):
        return [t for t in self.load(session)["tasks"] if t.get("kind") == "agent"]

    def play(self, provider, session="s1", agent=AGENT, call="c1", now=T0, **extra):
        spawn, rest = CYCLES[provider](session, agent, call, **extra)
        return spawn, rest, tasks.record(self.root, spawn, now=now)

    def test_a_spawn_is_an_in_progress_agent_task_and_the_result_completes_it(self):
        for provider in providers.ALL_PROVIDERS:
            with self.subTest(provider=provider):
                session = "s-" + provider
                spawn, rest, result = self.play(provider, session)
                self.assertTrue(result["recorded"])
                (task,) = self.agents(session)
                self.assertEqual((task["status"], task["owner"], task["agent_type"]), ("in_progress", "main", AGENT))
                self.assertEqual(self.load(session)["provider"], provider)
                self.assertEqual(task["content"], AGENT + ": add the endpoint")
                self.assertEqual(task["id"], "c1")
                for step, payload in enumerate(rest, start=1):
                    tasks.record(self.root, payload, now=T0 + 10 * step)
                (task,) = self.agents(session)
                self.assertEqual((task["status"], task["failed"]), ("completed", False))
                self.assertEqual([h["status"] for h in task["history"]], ["in_progress", "completed"])

    def test_the_text_falls_back_to_the_agent_name(self):
        spawn, _ = claude_cycle("s1", AGENT, "c1")
        spawn["tool_input"].pop("description")
        tasks.record(self.root, spawn, now=T0)
        self.assertEqual(self.agents()[0]["content"], AGENT)

    def test_a_replayed_spawn_never_duplicates_a_task(self):
        spawn, _ = claude_cycle("s1", AGENT, "c1")
        tasks.record(self.root, spawn, now=T0)
        tasks.record(self.root, spawn, now=T0 + 1)
        self.assertEqual(len(self.agents()), 1)

    def test_two_agents_side_by_side_are_settled_by_their_own_id(self):
        for call in ("a", "b"):
            tasks.record(self.root, claude_cycle("s1", AGENT, call)[0], now=T0)
        tasks.record(self.root, claude_cycle("s1", AGENT, "b")[1][0], now=T0 + 5)
        self.assertEqual({t["id"]: t["status"] for t in self.agents()}, {"a": "in_progress", "b": "completed"})

    def test_a_result_with_no_spawn_on_record_starts_no_record(self):
        for provider in providers.ALL_PROVIDERS:
            _, rest = CYCLES[provider]("ghost-" + provider, AGENT, "c1")
            for payload in rest:
                self.assertFalse(tasks.record(self.root, payload, now=T0)["recorded"], provider)
            self.assertFalse(tasks.record_path(self.root, self.project_id, "ghost-" + provider).exists())

    def test_an_unmatched_result_leaves_the_record_untouched(self):
        tasks.record(self.root, claude_cycle("s1", AGENT, "a")[0], now=T0)
        before = self.load("s1")
        self.assertFalse(tasks.record(self.root, claude_cycle("s1", AGENT, "zzz")[1][0], now=T0 + 99)["recorded"])
        self.assertEqual(self.load("s1"), before)

    def test_an_async_ack_stays_in_progress_and_the_transcript_hand_back_completes_it(self):
        transcript = self.tmp / "t.jsonl"
        transcript.write_text("", encoding="utf-8")
        spawn, (end,) = claude_cycle("s1", AGENT, "toolu_bg", input={"run_in_background": True}, transcript_path=str(transcript))
        tasks.record(self.root, spawn, now=T0)
        tasks.record(self.root, dict(end, tool_response={"isAsync": True, "status": "async_launched"}), now=T0 + 1)
        self.assertEqual((self.agents()[0]["status"], self.agents()[0]["background"]), ("in_progress", True))
        stamp = "2023-11-14T22:14:30Z"  # after T0 (2023-11-14T22:13:20Z)
        line = {"type": "queue-operation", "timestamp": stamp,
                "content": "<task-notification><tool-use-id>toolu_bg</tool-use-id><task-id>x</task-id>"
                           "<result>all done</result></task-notification>"}
        other = {"type": "queue-operation", "timestamp": stamp,
                 "content": "<task-notification><tool-use-id>toolu_other</tool-use-id><result>no</result></task-notification>"}
        transcript.write_text(json.dumps(other) + "\n" + json.dumps(line) + "\n", encoding="utf-8")
        marked = tasks.mark(self.root, {"session_id": "s1", "transcript_path": str(transcript)}, "idle", now=T0 + 100)
        self.assertTrue(marked["marked"])
        self.assertEqual(self.agents()[0]["status"], "completed")
        self.assertTrue(marked["became_all_done"])
        # The hand-back is read once.
        self.assertEqual(len(self.agents()[0]["history"]), 2)

    def test_a_foreground_launch_the_harness_backgrounded_is_settled_by_its_hand_back(self):
        spawn, (end,) = claude_cycle("s1", AGENT, "toolu_x")
        tasks.record(self.root, spawn, now=T0)
        tasks.record(self.root, dict(end, tool_response={"status": "async_launched"}), now=T0 + 1)
        self.assertEqual(self.agents()[0]["status"], "in_progress")
        self.assertTrue(self.agents()[0]["background"])

    def test_a_claude_failure_cancels_the_task_and_marks_it_failed(self):
        spawn, (end,) = claude_cycle("s1", AGENT, "c1")
        tasks.record(self.root, spawn, now=T0)
        tasks.record(self.root, dict(end, hook_event_name="PostToolUseFailure", tool_response=None, error="boom"), now=T0 + 3)
        (task,) = self.agents()
        self.assertEqual((task["status"], task["failed"]), ("cancelled", True))
        view = self.view()[0]["sessions"][0]["tasks"][0]
        self.assertEqual((view["kind"], view["failed"], view["column"]), ("agent", True, "done"))

    def test_built_in_agents_are_not_tasks_on_any_provider(self):
        for provider in providers.ALL_PROVIDERS:
            name = review_triggers.BUILTIN_AGENTS[provider][0]
            for variant in (name, name.capitalize()):
                spawn, rest = CYCLES[provider]("b-" + provider, variant, "c1")
                for payload in [spawn] + rest:
                    self.assertFalse(tasks.record(self.root, payload, now=T0)["recorded"], (provider, variant))
            self.assertFalse(tasks.record_path(self.root, self.project_id, "b-" + provider).exists())

    def test_an_agent_with_no_type_is_the_default_agent_and_no_task(self):
        spawn, _ = claude_cycle("s1", AGENT, "c1")
        spawn["tool_input"].pop("subagent_type")
        self.assertFalse(tasks.record(self.root, spawn, now=T0)["recorded"])

    def test_review_agents_are_no_tasks_and_still_open_in_review(self):
        for provider in providers.ALL_PROVIDERS:
            with self.subTest(provider=provider):
                session = "r-" + provider
                tasks.record(self.root, todo_write(session, [todo("Build it", "in_progress")]), now=T0)
                spawn, rest = CYCLES[provider](session, "qa-specialist", "q1")
                self.assertFalse(tasks.record(self.root, spawn, now=T0 + 1)["recorded"])
                opened = tasks.review_open(self.root, spawn, now=T0 + 2)
                self.assertTrue(opened["recorded"], provider)
                self.assertEqual(self.agents(session), [])
                view = self.view(now=T0 + 3)[0]["sessions"]
                mine = [s for s in view if s["session_id"] == session][0]
                self.assertEqual([t["column"] for t in mine["tasks"]], ["in_review"])

    def test_a_nested_spawn_is_owned_by_the_subagent(self):
        spawn, _ = claude_cycle("s1", AGENT, "inner", agent_id="sub-1", agent_type="frontend-developer")
        tasks.record(self.root, spawn, now=T0)
        self.assertEqual(self.agents()[0]["owner"], "sub-1")

    def test_a_todo_list_never_touches_an_agent_task_of_the_same_owner(self):
        tasks.record(self.root, claude_cycle("s1", AGENT, "c1")[0], now=T0)
        tasks.record(self.root, todo_write("s1", [todo("Plan A")]), now=T0 + 1)
        tasks.record(self.root, todo_write("s1", []), now=T0 + 2)
        (task,) = self.agents()
        self.assertIsNone(task["removed_at"])
        self.assertEqual(task["status"], "in_progress")

    def test_agent_tasks_are_hidden_when_their_owner_keeps_a_mirrored_plan(self):
        tasks.record(self.root, claude_cycle("s1", AGENT, "c1")[0], now=T0)
        shown = self.view()[0]["sessions"][0]
        self.assertEqual((shown["counts"]["total"], shown["tasks"][0]["kind"]), (1, "agent"))
        tasks.record(self.root, todo_write("s1", [todo("Step 1: do it", "in_progress"), todo("Step 2: ship")]), now=T0 + 1)
        session = self.view()[0]["sessions"][0]
        self.assertEqual([t["content"] for t in session["tasks"]], ["Step 1: do it", "Step 2: ship"])
        self.assertEqual(session["counts"]["total"], 2)
        self.assertEqual(self.view()[0]["counts"]["total"], 2)
        # Kept in the record, just not shown.
        self.assertEqual(len(self.agents()), 1)

    def test_a_hidden_agent_task_does_not_hold_all_done_back(self):
        tasks.record(self.root, claude_cycle("s1", AGENT, "c1")[0], now=T0)
        tasks.record(self.root, todo_write("s1", [todo("Step 1: do it", "in_progress")]), now=T0 + 1)
        done = tasks.record(self.root, todo_write("s1", [todo("Step 1: do it", "completed")]), now=T0 + 2)
        self.assertEqual((done["all_done"], done["became_all_done"]), (True, True))

    def test_another_owners_plan_does_not_hide_an_agent_task(self):
        tasks.record(self.root, claude_cycle("s1", AGENT, "c1")[0], now=T0)
        tasks.record(self.root, todo_write("s1", [todo("Step 1: x")], agent_id="sub-9"), now=T0 + 1)
        kinds = sorted(t["kind"] for t in self.view()[0]["sessions"][0]["tasks"])
        self.assertEqual(kinds, ["agent", "todo"])

    def test_a_task_without_a_kind_reads_as_a_todo(self):
        tasks.record(self.root, todo_write("s1", [todo("A")]), now=T0)
        record = self.load("s1")
        self.assertNotIn("kind", record["tasks"][0])
        self.assertEqual(self.view()[0]["sessions"][0]["tasks"][0]["kind"], "todo")
        self.assertFalse(self.view()[0]["sessions"][0]["tasks"][0]["failed"])

    def test_a_spawn_with_no_result_is_abandoned_when_its_session_ends(self):
        tasks.record(self.root, claude_cycle("s1", AGENT, "c1")[0], now=T0)
        tasks.mark(self.root, {"session_id": "s1"}, "ended", now=T0 + 5)
        view = self.view(now=T0 + 10)[0]
        self.assertEqual(view["abandoned"], 1)

    def test_the_agent_task_enters_the_next_review_as_finished_work(self):
        spawn, (end,) = claude_cycle("s1", AGENT, "c1")
        tasks.record(self.root, spawn, now=T0)
        tasks.record(self.root, end, now=T0 + 1)
        qa, _ = claude_cycle("s1", "qa-specialist", "q1")
        self.assertTrue(tasks.review_open(self.root, qa, now=T0 + 2)["recorded"])
        self.assertEqual(self.view(now=T0 + 3)[0]["sessions"][0]["tasks"][0]["column"], "in_review")


STAMP = "2023-11-14T22:30:00Z"  # T0 + 1000s: after every spawn these tests make


def hand_back(call, status=None, stamp=STAMP):
    body = "<tool-use-id>{}</tool-use-id>".format(call)
    if status:
        body += "<status>{}</status>".format(status)
    return json.dumps({
        "type": "queue-operation", "timestamp": stamp,
        "content": "<task-notification>{}<result>report</result></task-notification>".format(body),
    }) + "\n"


class SettlementTest(BoardCase):
    """Finding rounds: how an agent task ends when its end is not a plain success."""

    def agents(self, session="s1"):
        return {t["id"]: t for t in self.load(session)["tasks"] if t.get("kind") == "agent"}

    def background(self, call, transcript, now=T0):
        spawn, (end,) = claude_cycle("s1", AGENT, call, input={"run_in_background": True},
                                     transcript_path=str(transcript))
        tasks.record(self.root, spawn, now=now)
        tasks.record(self.root, dict(end, tool_response={"isAsync": True, "status": "async_launched"}), now=now + 1)

    def stop(self, transcript=None, now=T0 + 2000):
        payload = {"session_id": "s1"}
        if transcript is not None:
            payload["transcript_path"] = str(transcript)
        return tasks.mark(self.root, payload, "idle", now=now)

    def test_a_background_hand_back_status_decides_completed_or_failed(self):
        cases = {"completed": ("completed", False), "failed": ("cancelled", True), "killed": ("cancelled", True),
                 "error": ("cancelled", True), "FAILED": ("cancelled", True), "stopped": ("completed", False),
                 "": ("completed", False)}
        for status, expected in cases.items():
            with self.subTest(status=status):
                transcript = self.tmp / "t-{}.jsonl".format(status or "none")
                transcript.write_text("", encoding="utf-8")
                self.background("bg-" + (status or "none"), transcript)
                transcript.write_text(hand_back("bg-" + (status or "none"), status or None), encoding="utf-8")
                self.stop(transcript)
                task = self.agents()["bg-" + (status or "none")]
                self.assertEqual((task["status"], bool(task.get("failed"))), expected)

    def test_a_background_agent_ends_at_its_hand_back_not_at_a_late_stop(self):
        transcript = self.tmp / "late.jsonl"
        transcript.write_text("", encoding="utf-8")
        self.background("bg-late", transcript)
        transcript.write_text(hand_back("bg-late"), encoding="utf-8")  # stamped T0 + 1000
        self.stop(transcript, now=T0 + 11 * 3600)
        task = self.agents()["bg-late"]
        self.assertEqual((task["status"], task["history"][-1]["at"]), ("completed", T0 + 1000))

    def test_a_backdated_end_never_lands_before_the_tasks_last_event(self):
        transcript = self.tmp / "order.jsonl"
        transcript.write_text("", encoding="utf-8")
        # An earlier background agent keeps the scan open from T0, so a hand-back stamped before this
        # task's own spawn (clock skew between hooks) is still read for it.
        self.background("bg-first", transcript, now=T0)
        self.background("bg-order", transcript, now=T0 + 1500)  # spawned after the T0 + 1000 stamp
        transcript.write_text(hand_back("bg-order"), encoding="utf-8")
        self.stop(transcript, now=T0 + 3000)
        task = self.agents()["bg-order"]
        self.assertEqual(task["status"], "completed")
        self.assertEqual([h["at"] for h in task["history"]], [T0 + 1500, T0 + 1500])

    def test_the_cursor_restarts_at_the_transcript_end_when_no_other_background_agent_runs(self):
        transcript = self.tmp / "t.jsonl"
        transcript.write_text("", encoding="utf-8")
        self.background("bg-a", transcript)
        transcript.write_text(hand_back("bg-a"), encoding="utf-8")
        self.stop(transcript)
        self.assertEqual(self.agents()["bg-a"]["status"], "completed")
        # A long stretch with no background agent running passes the stale cursor by far more than one read.
        with transcript.open("a", encoding="utf-8") as handle:
            for _ in range(3 * 1024):
                handle.write(json.dumps({"type": "assistant", "text": "x" * 1000}) + "\n")
        self.background("bg-b", transcript, now=T0 + 100)
        with transcript.open("a", encoding="utf-8") as handle:
            handle.write(hand_back("bg-b"))
        self.stop(transcript)
        self.assertEqual(self.agents()["bg-b"]["status"], "completed")

    def test_one_stop_catches_up_across_a_gap_wider_than_one_read(self):
        transcript = self.tmp / "t.jsonl"
        transcript.write_text("", encoding="utf-8")
        self.background("bg-a", transcript)
        self.background("bg-b", transcript, now=T0 + 10)  # b runs, so the cursor keeps its place
        with transcript.open("a", encoding="utf-8") as handle:
            for _ in range(5 * 1024):  # > 2 MiB
                handle.write(json.dumps({"type": "assistant", "text": "x" * 1000}) + "\n")
            handle.write(hand_back("bg-a"))
        self.stop(transcript)
        self.assertEqual(self.agents()["bg-a"]["status"], "completed")
        self.assertEqual(self.agents()["bg-b"]["status"], "in_progress")

    def test_a_foreground_agent_left_open_at_stop_is_cancelled_as_interrupted(self):
        for provider in ("claude", "opencode"):
            with self.subTest(provider=provider):
                session = "i-" + provider
                spawn, _ = CYCLES[provider](session, AGENT, "c1")
                tasks.record(self.root, spawn, now=T0)
                marked = tasks.mark(self.root, {"session_id": session}, "idle", now=T0 + 9)
                (task,) = [t for t in self.load(session)["tasks"] if t.get("kind") == "agent"]
                self.assertEqual((task["status"], task["interrupted"], bool(task.get("failed"))), ("cancelled", True, False))
                shown = self.view(now=T0 + 10)
                mine = [s for s in shown[0]["sessions"] if s["session_id"] == session][0]["tasks"][0]
                self.assertEqual((mine["interrupted"], mine["column"]), (True, "done"))
                self.assertFalse(marked["became_all_done"])

    def test_a_background_agent_and_an_acknowledged_codex_agent_survive_stop(self):
        transcript = self.tmp / "t.jsonl"
        transcript.write_text("", encoding="utf-8")
        self.background("bg-a", transcript)
        spawn, (ack, _) = codex_cycle("s1", AGENT, "cx")
        tasks.record(self.root, spawn, now=T0 + 5)
        tasks.record(self.root, ack, now=T0 + 6)
        unacked, _ = codex_cycle("s1", AGENT, "cy")
        tasks.record(self.root, unacked, now=T0 + 7)
        self.stop(transcript)
        got = {k: (v["status"], bool(v.get("interrupted"))) for k, v in self.agents().items()}
        self.assertEqual(got, {"bg-a": ("in_progress", False), "cx": ("in_progress", False), "cy": ("cancelled", True)})

    def test_a_codex_spawn_that_answers_with_no_agent_id_fails(self):
        spawn, (ack, _) = codex_cycle("s1", AGENT, "c1")
        tasks.record(self.root, spawn, now=T0)
        tasks.record(self.root, dict(ack, tool_response={"error": "no capacity"}), now=T0 + 1)
        task = self.agents()["c1"]
        self.assertEqual((task["status"], task["failed"]), ("cancelled", True))

    def test_a_codex_close_agent_cancels_the_agent_without_failing_it(self):
        spawn, (ack, _) = codex_cycle("s1", AGENT, "c1")
        tasks.record(self.root, spawn, now=T0)
        tasks.record(self.root, ack, now=T0 + 1)
        for namespaced in ("close_agent", "agents.close_agent"):
            self.assertIsNone(tasks.normalize({"tool_name": namespaced, "session_id": "s1", "tool_input": {}}, "codex"))
        close = {"session_id": "s1", "tool_use_id": "k1", "hook_event_name": "PostToolUse", "tool_name": "close_agent",
                 "tool_input": {"target": "ag-c1"}, "tool_response": {"previous_status": "running"}}
        self.assertTrue(tasks.record(self.root, close, now=T0 + 5)["recorded"])
        task = self.agents()["c1"]
        self.assertEqual((task["status"], task["failed"]), ("cancelled", False))

    def test_an_agent_end_never_raises_session_done_mid_turn_but_the_stop_does(self):
        spawn, (end,) = claude_cycle("s1", AGENT, "c1")
        tasks.record(self.root, spawn, now=T0)
        done = tasks.record(self.root, end, now=T0 + 1)
        self.assertEqual((done["all_done"], done["became_all_done"]), (True, False))
        self.assertTrue(self.stop(now=T0 + 2)["became_all_done"])
        self.assertFalse(self.stop(now=T0 + 3)["became_all_done"])  # paid once

    def test_a_failed_agent_task_never_raises_session_done(self):
        spawn, (end,) = claude_cycle("s1", AGENT, "c1")
        tasks.record(self.root, spawn, now=T0)
        failed = dict(end, hook_event_name="PostToolUseFailure", tool_response=None, error="boom")
        self.assertFalse(tasks.record(self.root, failed, now=T0 + 1)["became_all_done"])
        self.assertFalse(self.stop(now=T0 + 2)["became_all_done"])
        # A todo that completes beside a failed agent task is not a finished session either.
        tasks.record(self.root, todo_write("s1", [todo("Plan", "in_progress")]), now=T0 + 3)
        self.assertFalse(tasks.record(self.root, todo_write("s1", [todo("Plan", "completed")]), now=T0 + 4)["became_all_done"])

    def test_a_replayed_spawn_with_no_id_does_not_duplicate_while_the_first_is_open(self):
        spawn, _ = claude_cycle("s1", AGENT, "")
        tasks.record(self.root, spawn, now=T0)
        tasks.record(self.root, spawn, now=T0 + 1)
        self.assertEqual(len(self.load("s1")["tasks"]), 1)
        tasks.record(self.root, dict(spawn, tool_input=dict(spawn["tool_input"], description="other")), now=T0 + 2)
        self.assertEqual(len(self.load("s1")["tasks"]), 2)

    def test_the_claude_catch_all_agent_is_a_built_in(self):
        self.assertTrue(review_triggers.is_builtin("claude", "claude"))
        spawn, _ = claude_cycle("s1", "claude", "c1")
        self.assertFalse(tasks.record(self.root, spawn, now=T0)["recorded"])


class CodexWaitTest(BoardCase):
    def wait(self, statuses, call="w1"):
        return {
            "session_id": "s1", "cwd": "", "tool_use_id": call, "hook_event_name": "PostToolUse",
            "tool_name": "wait_agent", "tool_input": {"targets": list(statuses)},
            "tool_response": {"status": statuses, "timed_out": not statuses},
        }

    def spawn(self, call):
        spawn, (ack, _) = codex_cycle("s1", AGENT, call)
        tasks.record(self.root, spawn, now=T0)
        tasks.record(self.root, ack, now=T0 + 1)

    def statuses(self):
        return {t["id"]: (t["status"], t["failed"]) for t in self.load("s1")["tasks"] if t.get("kind") == "agent"}

    def test_the_agent_id_from_the_spawn_response_is_kept_on_the_task(self):
        self.spawn("c1")
        self.assertEqual(self.load("s1")["tasks"][0]["agent_ref"], "ag-c1")

    def test_a_wait_completes_each_agent_it_reports_and_only_those(self):
        for call in ("c1", "c2", "c3"):
            self.spawn(call)
        tasks.record(self.root, self.wait({"ag-c1": {"completed": "a"}, "ag-c2": {"completed": None}}), now=T0 + 5)
        self.assertEqual(self.statuses(), {
            "c1": ("completed", False), "c2": ("completed", False), "c3": ("in_progress", False),
        })

    def test_a_wait_that_timed_out_or_reports_a_running_agent_changes_nothing(self):
        self.spawn("c1")
        before = self.load("s1")
        self.assertFalse(tasks.record(self.root, self.wait({}), now=T0 + 5)["recorded"])
        self.assertFalse(tasks.record(self.root, self.wait({"ag-c1": "running"}), now=T0 + 5)["recorded"])
        self.assertEqual(self.load("s1"), before)

    def test_an_errored_or_missing_agent_is_cancelled_and_failed_a_closed_one_only_cancelled(self):
        for call in ("c1", "c2", "c3"):
            self.spawn(call)
        tasks.record(self.root, self.wait({"ag-c1": {"errored": "x"}, "ag-c2": "not_found", "ag-c3": "shutdown"}), now=T0 + 5)
        self.assertEqual(self.statuses(), {
            "c1": ("cancelled", True), "c2": ("cancelled", True), "c3": ("cancelled", False),
        })

    def test_the_wait_response_may_arrive_as_json_text(self):
        self.spawn("c1")
        wait = self.wait({"ag-c1": {"completed": "a"}})
        wait["tool_response"] = json.dumps(wait["tool_response"])
        tasks.record(self.root, wait, now=T0 + 5)
        self.assertEqual(self.statuses(), {"c1": ("completed", False)})

    def test_a_namespaced_wait_is_read_too(self):
        self.spawn("c1")
        wait = self.wait({"ag-c1": {"completed": "a"}})
        wait["tool_name"] = "agents.wait_agent"
        tasks.record(self.root, wait, now=T0 + 5)
        self.assertEqual(self.statuses(), {"c1": ("completed", False)})


class JsonContractTest(BoardCase):
    def test_kind_and_failed_are_additive_on_every_task(self):
        tasks.record(self.root, todo_write("s1", [todo("A")]), now=T0)
        tasks.record(self.root, claude_cycle("s1", AGENT, "c1")[0], now=T0 + 1)
        views = self.view()[0]["sessions"][0]["tasks"]
        self.assertEqual(sorted(v["kind"] for v in views), ["agent", "todo"])
        for view in views:
            self.assertIsInstance(view["failed"], bool)
            self.assertTrue({"key", "content", "owner", "agent_type", "status", "column", "review"} <= set(view))
        self.assertEqual(json.loads(json.dumps(self.view())), self.view())


@requires_bash()
class AgentHookTest(tt.HookTest):
    def agents(self, session="s1"):
        return [t for t in self.load(session)["tasks"] if t.get("kind") == "agent"]

    def test_spawn_and_result_flow_through_the_hooks_for_every_provider(self):
        for provider in providers.ALL_PROVIDERS:
            with self.subTest(provider=provider):
                session = "h-" + provider
                spawn, rest = CYCLES[provider](session, AGENT, "c1", cwd=str(self.root)) if provider != "opencode" else CYCLES[provider](session, AGENT, "c1")
                self.assertEqual(self.run_script(PRE_TOOL_USE, spawn).stdout, b"")
                (task,) = self.agents(session)
                self.assertEqual(task["status"], "in_progress")
                for payload in rest:
                    self.assertEqual(self.run_script(POST_TOOL_USE, payload).stdout, b"")
                (task,) = self.agents(session)
                self.assertEqual(task["status"], "completed", provider)

    def test_the_failure_event_cancels_through_the_dispatcher(self):
        spawn, (end,) = claude_cycle("s1", AGENT, "c1", cwd=str(self.root))
        self.run_script(PRE_TOOL_USE, spawn)
        self.run_script(tt.POST_DISPATCHER, dict(end, hook_event_name="PostToolUseFailure", tool_response=None, error="x"))
        (task,) = self.agents()
        self.assertEqual((task["status"], task["failed"]), ("cancelled", True))

    def test_a_background_hand_back_completes_it_at_stop_and_notifies_the_last_task_done(self):
        transcript = self.tmp / "t.jsonl"
        transcript.write_text("", encoding="utf-8")
        spawn, (end,) = claude_cycle("s1", AGENT, "toolu_bg", cwd=str(self.root), input={"run_in_background": True},
                                     transcript_path=str(transcript))
        self.run_script(PRE_TOOL_USE, spawn)
        self.run_script(POST_TOOL_USE, dict(end, tool_response={"isAsync": True, "status": "async_launched"}))
        later = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=60)
        note = {"type": "queue-operation", "timestamp": later.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "content": "<task-notification><tool-use-id>toolu_bg</tool-use-id><result>ok</result></task-notification>"}
        transcript.write_text(json.dumps(note) + "\n", encoding="utf-8")
        payload = {"session_id": "s1", "transcript_path": str(transcript)}
        payload_file = self.tmp / "stop.json"
        payload_file.write_text(json.dumps(payload), encoding="utf-8")
        self.run_script(STOP_SUB, "", extra_env={"DEVTEAM_HOOK_PAYLOAD": str(payload_file)})
        self.assertEqual(self.agents()[0]["status"], "completed")
        self.assertEqual([r["code"] for r in self.queue()], ["tasks.session_done"])

    def test_no_python_for_a_tool_that_is_not_an_agent_call(self):
        for payload in (
            {"tool_name": "Bash", "session_id": "s1", "tool_input": {"command": "echo spawn_agent Agent"}},
            {"tool_name": "Read", "session_id": "s1", "tool_input": {"file_path": "agents/backend-developer.md"}},
            # A subagent's edit is its agent task's work, never direct work (test_direct_work.py).
            {"tool_name": "Edit", "session_id": "s1", "agent_id": "a1", "tool_input": {}},
            {"tool": "bash", "sessionID": "s1", "args": {"command": "task"}},
        ):
            for script in (PRE_TOOL_USE, POST_TOOL_USE):
                result = self.run_script(script, payload)
                self.assertEqual((result.stdout, result.stderr), (b"", b""))
        # `TaskCreate` is a todo tool: only the post hook records it, the pre hook ignores it.
        self.run_script(PRE_TOOL_USE, {"tool_name": "TaskCreate", "session_id": "s1", "tool_input": {"subject": "backend-developer"}})
        # None of them is an agent call; the first is the session's own work (one fork a turn).
        self.assertEqual(self.python_calls(), 1)
        # With no prompt of the user's, that read opens no direct card either, so no record at all.
        self.assertFalse(tasks.record_path(self.root, self.project_id, "s1").exists())

    def test_a_spawn_with_no_agent_type_forks_no_python(self):
        for payload in (
            {"tool_name": "Agent", "session_id": "s1", "tool_use_id": "c1", "tool_input": {"description": "d", "prompt": "p"}},
            {"tool_name": "spawn_agent", "session_id": "s1", "tool_input": {"message": "m"}},
            {"tool": "task", "sessionID": "s1", "args": {"description": "d"}},
        ):
            for script in (PRE_TOOL_USE, POST_TOOL_USE):
                self.assertEqual(self.run_script(script, payload).stdout, b"")
        self.assertEqual(self.python_calls(), 0)

    def test_a_result_forks_no_python_in_a_session_without_a_record(self):
        for provider in providers.ALL_PROVIDERS:
            _, rest = CYCLES[provider]("ghost-" + provider, AGENT, "c1")
            for payload in rest:
                self.run_script(POST_TOOL_USE, payload)
        self.assertEqual(self.python_calls(), 0)

    def test_a_review_agent_spawn_is_no_task_through_the_hooks(self):
        self.run_script(POST_TOOL_USE, todo_write("s1", [todo("A", "in_progress")], cwd=str(self.root)))
        for provider in providers.ALL_PROVIDERS:
            spawn, _ = CYCLES[provider]("s1", "qa-specialist", "q-" + provider)
            self.run_script(PRE_TOOL_USE, spawn)
        self.assertEqual(self.agents(), [])
        self.assertEqual(len(self.load("s1")["reviews"]), 1)




@requires_bash()
class WorktreeTest(BoardCase):
    """A task records the linked worktree it was started in, on every provider."""

    def setUp(self):
        super().setUp()
        self.worktree = self.root / ".worktrees" / "feat" / "ping"
        subprocess.run(
            ["git", "-C", str(self.root), "worktree", "add", "-q", str(self.worktree), "-b", "feat/ping"],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        (self.worktree / "apps" / "api").mkdir(parents=True)

    def task_view(self, session):
        for project in self.view(now=T0 + 10):
            for item in project["sessions"]:
                if item["session_id"] == session:
                    return item["tasks"][0]
        return None

    def test_a_task_started_in_a_worktree_names_it_on_every_provider(self):
        for provider in providers.ALL_PROVIDERS:
            with self.subTest(provider=provider):
                session = "wt-" + provider
                spawn, _ = CYCLES[provider](session, AGENT, "c-" + provider, cwd=str(self.worktree / "apps" / "api"))
                tasks.record(self.root, spawn, now=T0)
                self.assertEqual(self.task_view(session)["worktree"], {"path": ".worktrees/feat/ping", "branch": "feat/ping"})

    def test_a_task_started_in_the_main_checkout_has_no_worktree(self):
        for provider in providers.ALL_PROVIDERS:
            with self.subTest(provider=provider):
                session = "main-" + provider
                spawn, _ = CYCLES[provider](session, AGENT, "m-" + provider, cwd=str(self.root))
                tasks.record(self.root, spawn, now=T0)
                self.assertIsNone(self.task_view(session)["worktree"])

    def test_the_worktree_is_fixed_when_the_task_is_created(self):
        spawn, (end,) = claude_cycle("s1", AGENT, "c1", cwd=str(self.worktree))
        tasks.record(self.root, spawn, now=T0)
        # The session moves back to the main checkout; the task still says where it started.
        tasks.record(self.root, dict(end, cwd=str(self.root)), now=T0 + 5)
        self.assertEqual(self.task_view("s1")["worktree"]["path"], ".worktrees/feat/ping")

    def test_a_detached_worktree_has_no_branch(self):
        detached = self.root / ".worktrees" / "detached"
        subprocess.run(["git", "-C", str(self.root), "worktree", "add", "-q", "--detach", str(detached)],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.assertEqual(tasks._git_location(str(detached))[1], {"path": ".worktrees/detached", "branch": None})

    def test_no_work_tree_and_no_commit_yet_degrade_without_a_worktree(self):
        bare = self.tmp / "bare.git"
        subprocess.run(["git", "init", "-q", "--bare", str(bare)], check=True)
        self.assertEqual(tasks._git_location(str(bare))[1], None)
        # Inside `.git` there is no work tree, but HEAD still names the branch, as it always did.
        self.assertEqual(tasks._git_location(str(self.root / ".git")), (tasks._git_location(str(self.root))[0], None))
        unborn = self.tmp / "unborn"
        subprocess.run(["git", "init", "-q", str(unborn)], check=True)
        self.assertEqual(tasks._git_location(str(unborn)), (None, None))
        # The main checkout still names its branch.
        self.assertIsNotNone(tasks._git_location(str(self.root))[0])

    def test_the_opencode_plugin_sends_its_directory_as_cwd(self):
        source = (REPO_ROOT / "opencode" / "plugin" / "dev-team-agents.ts").read_text(encoding="utf-8")
        for hook in ('"tool.execute.before"', '"tool.execute.after"'):
            body = source[source.index(hook):]
            body = body[: body.index("runHook(")]
            self.assertIn("cwd: directory,", body, hook)

    def test_a_malformed_stored_worktree_reads_as_null(self):
        for stored in ("x", {"path": ""}, {"path": 3}, None):
            self.assertIsNone(tasks._worktree_view(stored))
        self.assertEqual(tasks._worktree_view({"path": "/abs/wt", "branch": ""}), {"path": "/abs/wt", "branch": None})


if __name__ == "__main__":
    unittest.main()
