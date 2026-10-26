"""Codex agent spawns reach the task board (ADR-0018), as Codex 0.160 really sends them.

The fixture is a sanitized capture of a real session: the collaboration tools arrive with their
namespace glued to the name (`collaborationspawn_agent`), the spawn's message is encrypted, its
response names a task but no agent id, and the child's id and end arrive as `SubagentStart` /
`SubagentStop`. These tests replay it through the hook scripts and pin the pieces.
"""

import copy
import json
import unittest

from devteam_support import REPO_ROOT, requires_bash

from devteam import hooks, providers, tasks, trace

import test_tasks as tt
from test_agent_tasks import AGENT, PARENT_THREAD, final_answer
from test_tasks import HOOKS, POST_TOOL_USE, PRE_TOOL_USE, T0, BoardCase

import sys

sys.path.insert(0, str(REPO_ROOT / "scripts" / "lib"))
import codex_hooks_merge  # noqa: E402

FIXTURE = REPO_ROOT / "tests" / "fixtures" / "codex-0.160-hook-payloads.json"
SUBAGENT_START = HOOKS / "subagent-start.sh"
SUBAGENT_STOP = HOOKS / "subagent-stop.sh"
REVIEW_MARKER = "all clear\n<!-- review-result: findings=0 -->"


def fixture(cwd=""):
    payloads = json.loads(FIXTURE.read_text(encoding="utf-8"))
    for payload in payloads:
        payload["cwd"] = cwd
    return payloads


def cycle(cwd=""):
    """The fixture's first agent cycle: spawn pre/post, start, the child's own call, stop, wait."""
    by = {}
    for payload in fixture(cwd)[:12]:
        key = (payload["hook_event_name"], payload.get("tool_name"), bool(payload.get("agent_id")))
        by[key] = payload
    return {
        "spawn_pre": by[("PreToolUse", "collaborationspawn_agent", False)],
        "spawn_post": by[("PostToolUse", "collaborationspawn_agent", False)],
        "start": by[("SubagentStart", None, True)],
        "child_bash": by[("PreToolUse", "Bash", True)],
        "stop": by[("SubagentStop", None, True)],
        "wait_post": by[("PostToolUse", "collaborationwait_agent", False)],
    }


def named(payload, tool_name):
    return dict(payload, tool_name=tool_name)


class CodexToolNameTest(unittest.TestCase):
    def test_the_dotted_and_the_glued_namespace_both_name_the_tool(self):
        for name in ("spawn_agent", "collaboration.spawn_agent", "collaborationspawn_agent"):
            self.assertEqual(tasks.codex_tool(name), "spawn_agent", name)
        for name in ("wait_agent", "collaborationwait_agent", "collaborationclose_agent"):
            self.assertIn(tasks.codex_tool(name), ("wait_agent", "close_agent"), name)

    def test_only_the_known_namespace_is_glued(self):
        for name in ("foospawn_agent", "collaborationspawn_agentx", "Xcollaborationspawn_agent", "collaboration", ""):
            self.assertNotIn(tasks.codex_tool(name), tasks._CODEX_AGENT_TOOLS, name)
        self.assertEqual(tasks.codex_tool(None), "")

    def test_a_glued_spawn_is_an_agent_op_and_an_unknown_prefix_is_not(self):
        payload = cycle()["spawn_pre"]
        self.assertEqual(tasks.normalize(payload)["op"][0], "agent_spawn")
        self.assertEqual(tasks.normalize(named(payload, "collaboration.spawn_agent"))["op"][0], "agent_spawn")
        other = tasks.normalize(named(payload, "foospawn_agent"))
        self.assertTrue(other is None or other["op"][0] == "direct")


class CodexAgentTextTest(unittest.TestCase):
    def content(self, **inp):
        payload = dict(cycle()["spawn_pre"], tool_input=dict({"agent_type": "scratch-writer"}, **inp))
        return tasks.normalize(payload)["op"][1]["content"]

    def test_the_text_is_the_agent_type_and_its_task_name_without_the_root(self):
        self.assertEqual(self.content(task_name="/root/scratch_writer", message="gAAAAAB"), "scratch-writer: scratch_writer")
        self.assertEqual(self.content(task_name="scratch_writer"), "scratch-writer: scratch_writer")

    def test_an_opaque_message_is_never_the_text(self):
        self.assertEqual(self.content(message="gAAAAABqwvHMj1Ss2g2DWY3_opaque_encrypted"), "scratch-writer")
        self.assertEqual(self.content(message="A" * 60), "scratch-writer")

    def test_a_readable_message_still_describes_an_agent_without_a_task_name(self):
        self.assertEqual(self.content(message="add the endpoint\nmore"), "scratch-writer: add the endpoint")


class SubagentLifecycleTest(BoardCase):
    def agents(self, session):
        return [t for t in self.load(session)["tasks"] if t.get("kind") == "agent"]

    def test_spawn_start_stop_is_one_done_agent_task(self):
        steps = cycle()
        session = steps["spawn_pre"]["session_id"]
        tasks.record(self.root, steps["spawn_pre"], now=T0)
        tasks.record(self.root, steps["spawn_post"], now=T0 + 1)
        (task,) = self.agents(session)
        # A response naming a task path is a running agent (the v2 path); its text is the task name.
        self.assertEqual((task["status"], task["failed"], task["content"]), ("in_progress", False, "scratch-writer: scratch_writer"))
        self.assertEqual(task["agent_ref"], "/root/scratch_writer")
        tasks.record(self.root, steps["start"], now=T0 + 2)
        (task,) = self.agents(session)
        self.assertEqual((task["agent_id"], task["agent_ref"]), (steps["start"]["agent_id"], "/root/scratch_writer"))
        self.assertEqual(task["status"], "in_progress")
        tasks.record(self.root, steps["stop"], now=T0 + 3)
        (task,) = self.agents(session)
        self.assertEqual((task["status"], task["failed"], task["history"][-1]["at"]), ("completed", False, T0 + 3))
        # An uninformative wait settles nothing and adds nothing.
        tasks.record(self.root, steps["wait_post"], now=T0 + 4)
        self.assertEqual(len(self.agents(session)), 1)

    def test_a_start_before_the_spawns_answer_links_the_same_task(self):
        steps = cycle()
        session = steps["spawn_pre"]["session_id"]
        tasks.record(self.root, steps["spawn_pre"], now=T0)
        tasks.record(self.root, steps["start"], now=T0 + 1)
        tasks.record(self.root, steps["spawn_post"], now=T0 + 2)
        (task,) = self.agents(session)
        self.assertEqual((task["agent_id"], task["agent_ref"]), (steps["start"]["agent_id"], "/root/scratch_writer"))
        tasks.record(self.root, steps["stop"], now=T0 + 3)
        self.assertEqual(self.agents(session)[0]["status"], "completed")

    def test_a_v1_agent_holding_its_id_is_settled_by_its_stop_and_not_linked_to_another(self):
        steps = cycle()
        session = steps["spawn_pre"]["session_id"]
        agent = steps["start"]["agent_id"]
        tasks.record(self.root, steps["spawn_pre"], now=T0)
        tasks.record(self.root, dict(steps["spawn_post"], tool_response=json.dumps({"agent_id": agent})), now=T0 + 1)
        other = dict(steps["spawn_pre"], tool_use_id="call_other")
        tasks.record(self.root, other, now=T0 + 2)
        tasks.record(self.root, steps["start"], now=T0 + 3)  # already the first task's id: links nothing
        by = {t["id"]: t for t in self.agents(session)}
        self.assertNotIn("agent_id", by["call_other"])
        tasks.record(self.root, steps["stop"], now=T0 + 4)
        by = {t["id"]: t["status"] for t in self.agents(session)}
        self.assertEqual(by, {steps["spawn_pre"]["tool_use_id"]: "completed", "call_other": "in_progress"})

    def v1_stopped(self):
        steps = cycle()
        session = steps["spawn_pre"]["session_id"]
        agent = steps["start"]["agent_id"]
        tasks.record(self.root, steps["spawn_pre"], now=T0)
        tasks.record(self.root, dict(steps["spawn_post"], tool_response=json.dumps({"agent_id": agent})), now=T0 + 1)
        tasks.record(self.root, steps["stop"], now=T0 + 4)
        return steps, session, agent

    def test_a_wait_reporting_an_errored_agent_a_stop_already_ended_marks_it_failed_without_ending_it_again(self):
        steps, session, agent = self.v1_stopped()
        (task,) = self.agents(session)
        self.assertEqual((task["status"], task["failed"], len(task["history"])), ("completed", False, 2))
        wait = dict(steps["wait_post"], tool_response={"status": {agent: "errored"}})
        tasks.record(self.root, wait, now=T0 + 6)
        (task,) = self.agents(session)
        self.assertEqual((task["status"], task["failed"], len(task["history"])), ("completed", True, 2))

    def test_a_wait_reporting_a_completed_agent_a_stop_already_ended_changes_nothing(self):
        steps, session, agent = self.v1_stopped()
        before = json.dumps(self.load(session), sort_keys=True)
        tasks.record(self.root, dict(steps["wait_post"], tool_response={"status": {agent: {"completed": "x"}}}), now=T0 + 6)
        self.assertEqual([t["failed"] for t in self.agents(session)], [False])
        self.assertEqual(json.dumps(self.load(session)["tasks"], sort_keys=True), json.dumps(json.loads(before)["tasks"], sort_keys=True))

    def test_a_spawn_that_never_answered_is_still_cancelled_by_stop(self):
        steps = cycle()
        session = steps["spawn_pre"]["session_id"]
        tasks.record(self.root, steps["spawn_pre"], now=T0)
        tasks.mark(self.root, {"session_id": session}, "idle", now=T0 + 1)
        (task,) = self.agents(session)
        self.assertEqual((task["status"], task["interrupted"]), ("cancelled", True))

    def test_a_replayed_start_or_stop_changes_nothing(self):
        steps = cycle()
        for key in ("spawn_pre", "spawn_post", "start", "start", "stop", "stop"):
            tasks.record(self.root, steps[key], now=T0)
        (task,) = self.agents(steps["spawn_pre"]["session_id"])
        self.assertEqual((task["status"], len(task["history"])), ("completed", 2))

    def test_a_start_or_stop_with_no_spawn_records_nothing(self):
        steps = cycle()
        session = steps["start"]["session_id"]
        for key in ("start", "stop"):
            self.assertFalse(tasks.record(self.root, steps[key], now=T0)["recorded"])
        self.assertFalse(tasks.record_path(self.root, self.project_id, session).exists())
        # Nor does one on a session that has a record but no spawn of that agent.
        self.plan(session)
        tasks.record(self.root, steps["start"], now=T0 + 1)
        tasks.record(self.root, steps["stop"], now=T0 + 2)
        self.assertEqual(self.agents(session), [])

    def test_the_oldest_unlinked_spawn_of_the_type_owns_the_first_start(self):
        steps = cycle()
        session = steps["spawn_pre"]["session_id"]
        second = dict(steps["spawn_pre"], tool_use_id="call_second")
        tasks.record(self.root, steps["spawn_pre"], now=T0)
        tasks.record(self.root, second, now=T0 + 1)
        tasks.record(self.root, steps["start"], now=T0 + 2)
        ids = {t["id"]: t.get("agent_id") for t in self.agents(session)}
        self.assertEqual(ids, {steps["spawn_pre"]["tool_use_id"]: steps["start"]["agent_id"], "call_second": None})

    def test_the_start_of_another_agent_type_claims_no_spawn(self):
        steps = cycle()
        tasks.record(self.root, steps["spawn_pre"], now=T0)
        tasks.record(self.root, dict(steps["start"], agent_type="other-agent", agent_id="ag-2"), now=T0 + 1)
        (task,) = self.agents(steps["spawn_pre"]["session_id"])
        self.assertNotIn("agent_id", task)

    def test_a_built_in_agent_is_no_task(self):
        steps = cycle()
        for agent in ("worker", "default"):
            payload = dict(steps["start"], agent_type=agent)
            self.assertIsNone(tasks.normalize(payload), agent)

    def test_a_finished_child_retires_its_own_open_todo_items(self):
        steps = cycle()
        session = steps["spawn_pre"]["session_id"]
        child = steps["start"]["agent_id"]
        for key in ("spawn_pre", "spawn_post", "start"):
            tasks.record(self.root, steps[key], now=T0)
        plan = {"session_id": session, "cwd": "", "hook_event_name": "PreToolUse", "tool_name": "update_plan",
                "agent_id": child, "tool_input": {"plan": [{"step": "child step", "status": "in_progress"}]}}
        tasks.record(self.root, plan, now=T0 + 1)
        tasks.record(self.root, steps["stop"], now=T0 + 2)
        (owned,) = [t for t in self.load(session)["tasks"] if t["owner"] == child]
        self.assertIsNotNone(owned["removed_at"])

    def test_the_childs_own_calls_stay_the_agents_work(self):
        steps = cycle()
        self.assertIsNone(tasks.normalize(steps["child_bash"]))

    def plan(self, session):
        plan = {"session_id": session, "cwd": "", "hook_event_name": "PreToolUse", "tool_name": "update_plan",
                "tool_input": {"plan": [{"step": "Step 1: build", "status": "in_progress"}]}}
        tasks.record(self.root, plan, now=T0)

    def review_agent(self, agent):
        steps = cycle()
        session = steps["spawn_pre"]["session_id"]
        self.plan(session)
        spawn = copy.deepcopy(steps["spawn_pre"])
        spawn["tool_input"]["agent_type"] = agent
        self.assertTrue(tasks.review_open(self.root, spawn, now=T0 + 1)["recorded"])
        return steps, session, spawn

    def test_a_review_agent_stays_a_window_and_never_becomes_a_task(self):
        steps, session, spawn = self.review_agent("code-reviewer")
        tasks.record(self.root, spawn, now=T0 + 2)
        start = dict(steps["start"], agent_type="code-reviewer")
        self.assertIsNone(tasks.normalize(start))
        tasks.record(self.root, start, now=T0 + 3)
        self.assertEqual(self.agents(session), [])

    def test_a_review_agents_stop_folds_its_marker_into_the_window(self):
        steps, session, _ = self.review_agent("code-reviewer")
        stop = dict(steps["stop"], agent_type="code-reviewer", last_assistant_message=REVIEW_MARKER)
        result = tasks.review_result(self.root, stop, now=T0 + 5)
        self.assertEqual((result["recorded"], result["result"], result["findings"]), (True, True, 0))
        # The same stop again is a replay: the window is already closed.
        self.assertFalse(tasks.review_result(self.root, stop, now=T0 + 6)["result"])

    def test_a_stop_with_no_marker_closes_the_window_unread(self):
        steps, _, _ = self.review_agent("qa-specialist")
        stop = dict(steps["stop"], agent_type="qa-specialist", last_assistant_message="looks fine")
        result = tasks.review_result(self.root, stop, now=T0 + 5)
        self.assertEqual((result["result"], result["findings"]), (True, None))

    def test_a_non_review_agents_stop_with_a_marker_changes_no_window(self):
        steps, _, _ = self.review_agent("code-reviewer")
        stop = dict(steps["stop"], last_assistant_message=REVIEW_MARKER)
        self.assertFalse(tasks.review_result(self.root, stop, now=T0 + 5)["recorded"])

    def twice(self, first, second):
        steps, session, _ = self.review_agent("code-reviewer")
        second_spawn = dict(steps["spawn_pre"], tool_use_id="call_second")
        second_spawn["tool_input"] = dict(second_spawn["tool_input"], agent_type="qa-specialist")
        tasks.review_open(self.root, second_spawn, now=T0 + 2)
        agent = steps["stop"]["agent_id"]
        calls = {
            "stop": dict(steps["stop"], agent_type="code-reviewer", last_assistant_message=REVIEW_MARKER),
            "wait": dict(steps["wait_post"], tool_response={"status": {agent: {"completed": REVIEW_MARKER}}}),
        }
        self.assertTrue(tasks.review_result(self.root, calls[first], now=T0 + 5)["recorded"])
        self.assertFalse(tasks.review_result(self.root, calls[second], now=T0 + 6)["recorded"])
        (window,) = self.load(session)["reviews"]
        # One report, one slot: the second reviewer is still awaited, the first is not counted twice.
        self.assertEqual((window["markers"], window["pending"]), (1, 1))

    def test_a_stop_then_a_wait_naming_the_same_agent_counts_it_once(self):
        self.twice("stop", "wait")

    def test_a_wait_then_a_stop_naming_the_same_agent_counts_it_once(self):
        self.twice("wait", "stop")

    def mixed_wait(self, order):
        """A reviewer a stop already folded, a QA agent still open and a worker, in one wait."""
        steps, session, _ = self.review_agent("code-reviewer")
        second = dict(steps["spawn_pre"], tool_use_id="call_second")
        second["tool_input"] = dict(second["tool_input"], agent_type="qa-specialist")
        tasks.review_open(self.root, second, now=T0 + 2)
        reviewer = steps["stop"]["agent_id"]
        stop = dict(steps["stop"], agent_type="code-reviewer", last_assistant_message=REVIEW_MARKER)
        self.assertTrue(tasks.review_result(self.root, stop, now=T0 + 5)["recorded"])
        reports = {
            "reviewer": {"completed": REVIEW_MARKER},
            "qa-1": {"completed": "found three\n<!-- review-result: findings=3 -->"},
            "worker-1": {"completed": "built it"},
        }
        statuses = {(reviewer if key == "reviewer" else key): reports[key] for key in order}
        wait = dict(steps["wait_post"], tool_response={"status": statuses})
        tasks.review_result(self.root, wait, now=T0 + 6)
        (window,) = self.load(session)["reviews"]
        return window, reviewer

    def test_a_wait_listing_the_folded_reviewer_after_the_open_one_keeps_its_findings(self):
        window, _ = self.mixed_wait(["qa-1", "worker-1", "reviewer"])
        self.assertEqual((window["found"], window["markers"], window["findings"]), (3, 2, 3))
        self.assertNotIn("anon:subagent:worker-1", window["consumed"])

    def test_a_wait_of_the_open_reviewer_then_the_folded_one_keeps_the_open_ones_findings(self):
        window, _ = self.mixed_wait(["qa-1", "reviewer"])
        self.assertEqual((window["found"], window["markers"], window["findings"]), (3, 2, 3))

    def test_the_same_wait_in_the_opposite_order_gives_the_same_result(self):
        window, _ = self.mixed_wait(["reviewer", "worker-1", "qa-1"])
        self.assertEqual((window["found"], window["markers"], window["findings"]), (3, 2, 3))


#: What each provider does with the subagent lifecycle events. A provider added to
#: `providers.ALL_PROVIDERS` without a case fails `test_every_provider_has_its_capture_decided`.
#: Claude Code's `Agent`/`Task` calls already reach Pre/PostToolUse and opencode has no such event.
SUBAGENT_EVENTS_WIRED = {"claude": False, "codex": True, "opencode": False}


class ProviderParityTest(unittest.TestCase):
    def wired(self, provider):
        if provider == "claude":
            return {event for event, _ in hooks.EVENTS}
        if provider == "codex":
            return set(providers.CODEX_MANAGED_EVENTS)
        return set()

    def test_every_provider_has_its_capture_decided(self):
        self.assertEqual(set(SUBAGENT_EVENTS_WIRED), set(providers.ALL_PROVIDERS))

    def test_the_events_are_wired_exactly_where_decided(self):
        for provider in providers.ALL_PROVIDERS:
            with self.subTest(provider=provider):
                wired = self.wired(provider)
                for event in ("SubagentStart", "SubagentStop"):
                    self.assertEqual(event in wired, SUBAGENT_EVENTS_WIRED[provider], event)

    def test_only_codex_reads_the_events(self):
        payload = cycle()["start"]
        for provider in providers.ALL_PROVIDERS:
            with self.subTest(provider=provider):
                call = tasks.normalize(payload, provider)
                self.assertEqual(call is not None, SUBAGENT_EVENTS_WIRED[provider])

    def test_the_installer_and_the_provider_registry_list_the_same_codex_events(self):
        self.assertEqual(codex_hooks_merge.MANAGED_EVENTS, providers.CODEX_MANAGED_EVENTS)
        for event in codex_hooks_merge.MANAGED_EVENTS:
            self.assertTrue((HOOKS / codex_hooks_merge.SCRIPTS[event]).is_file(), event)

    def test_the_rendered_codex_hooks_wire_both_events_to_their_dispatchers(self):
        groups = codex_hooks_merge.managed_groups(".dev-team-agents/scripts/hooks", windows=False)
        for event, script in (("SubagentStart", "subagent-start.sh"), ("SubagentStop", "subagent-stop.sh")):
            (group,) = groups[event]
            self.assertIn(script, group["hooks"][0]["command"])
            self.assertIn(codex_hooks_merge.MANAGED_MARKER, group["hooks"][0]["statusMessage"])


@requires_bash()
class SubagentHookReplayTest(tt.HookTest):
    SCRIPTS = {
        "PreToolUse": PRE_TOOL_USE, "PostToolUse": POST_TOOL_USE,
        "SubagentStart": SUBAGENT_START, "SubagentStop": SUBAGENT_STOP,
    }

    def agents(self, session):
        return [t for t in self.load(session)["tasks"] if t.get("kind") == "agent"]

    def feed(self, payload):
        proc = self.run_script(self.SCRIPTS[payload["hook_event_name"]], payload)
        self.assertEqual((proc.stdout, proc.stderr), (b"", b""))

    def test_the_captured_session_replays_to_one_done_agent_task(self):
        for payload in fixture(str(self.root))[:12]:
            if payload["hook_event_name"] in self.SCRIPTS:
                self.feed(payload)
        session = fixture()[2]["session_id"]
        (task,) = self.agents(session)
        self.assertEqual(task["status"], "completed")
        self.assertEqual((task["failed"], task["content"]), (False, "scratch-writer: scratch_writer"))
        self.assertEqual((task["agent_ref"], task["agent_id"]), ("/root/scratch_writer", cycle()["start"]["agent_id"]))
        self.assertEqual(self.load(session)["provider"], "codex")

    def test_a_dotted_name_works_through_the_hooks_too(self):
        steps = cycle(str(self.root))
        for key in ("spawn_pre", "spawn_post"):
            self.feed(named(steps[key], "collaboration.spawn_agent"))
        self.feed(steps["start"])
        self.feed(steps["stop"])
        (task,) = self.agents(steps["spawn_pre"]["session_id"])
        self.assertEqual(task["status"], "completed")

    def test_an_unknown_prefix_records_no_agent_task(self):
        steps = cycle(str(self.root))
        self.feed(named(steps["spawn_pre"], "foospawn_agent"))
        # It is just another tool of the session's own: never an agent task.
        path = tasks.record_path(self.root, self.project_id, steps["spawn_pre"]["session_id"])
        self.assertTrue(not path.exists() or self.agents(steps["spawn_pre"]["session_id"]) == [])

    def test_a_review_agents_start_forks_no_python(self):
        steps = cycle(str(self.root))
        self.feed(dict(steps["start"], agent_type="code-reviewer"))
        self.assertEqual(self.python_calls(), 0)

    def test_a_start_with_no_record_forks_no_python(self):
        steps = cycle(str(self.root))
        self.feed(steps["start"])
        self.assertEqual(self.python_calls(), 0)

    def test_a_built_in_roles_start_and_stop_record_no_task(self):
        steps = cycle(str(self.root))
        session = steps["spawn_pre"]["session_id"]
        self.feed(steps["spawn_pre"])
        before = json.dumps(self.load(session)["tasks"], sort_keys=True)
        for key in ("start", "stop"):
            self.feed(dict(steps[key], agent_type="worker"))
        self.assertEqual(json.dumps(self.load(session)["tasks"], sort_keys=True), before)

    def test_the_dispatchers_fail_open_without_a_temp_directory(self):
        steps = cycle(str(self.root))
        for key, script in (("start", SUBAGENT_START), ("stop", SUBAGENT_STOP)):
            proc = self.run_script(script, steps[key], extra_env={"TMPDIR": "/nonexistent/devteam"})
            self.assertEqual((proc.stdout, proc.stderr), (b"", b""))

    def test_a_stop_sub_script_failure_never_keeps_the_child_running(self):
        steps = cycle(str(self.root))
        hooks_dir = self.tmp / "hooks"
        (hooks_dir / "subagent-stop").mkdir(parents=True)
        (hooks_dir / "lib").mkdir()
        (hooks_dir / "subagent-stop" / "01-fail.sh").write_text("#!/usr/bin/env bash\nexit 2\n", encoding="utf-8")
        (hooks_dir / "lib" / "python.sh").write_text("", encoding="utf-8")
        copy_path = hooks_dir / "subagent-stop.sh"
        copy_path.write_text(SUBAGENT_STOP.read_text(encoding="utf-8"), encoding="utf-8")
        proc = self.run_script(copy_path, steps["stop"])  # check=True: it must exit 0
        self.assertEqual(proc.returncode, 0)

    def test_a_stop_with_no_record_forks_no_python(self):
        steps = cycle(str(self.root))
        self.feed(steps["stop"])
        self.assertEqual(self.python_calls(), 0)

    def test_a_review_agents_stop_settles_its_window_through_the_hook(self):
        steps = cycle(str(self.root))
        session = steps["spawn_pre"]["session_id"]
        tasks.record(self.root, {"session_id": session, "cwd": "", "hook_event_name": "PreToolUse", "tool_name": "update_plan",
                                 "tool_input": {"plan": [{"step": "Step 1: build", "status": "in_progress"}]}}, now=T0)
        self.feed(dict(steps["spawn_pre"], tool_input={"agent_type": "code-reviewer", "message": "x"}))
        self.feed(dict(steps["stop"], agent_type="code-reviewer", last_assistant_message=REVIEW_MARKER))
        (window,) = self.load(session)["reviews"]
        self.assertEqual(window["findings"], 0)



class SubagentRecoveryTest(BoardCase):
    """What the Subagent events must never do: settle or record a task twice, or the wrong one."""

    def agents(self, session):
        return [t for t in self.load(session)["tasks"] if t.get("kind") == "agent"]

    def test_the_main_sessions_spawn_is_preferred_over_a_nested_one(self):
        record = {"tasks": [
            {"kind": "agent", "status": "in_progress", "agent_type": "w", "owner": "child", "key": "t1"},
            {"kind": "agent", "status": "in_progress", "agent_type": "w", "owner": tasks.MAIN_OWNER, "key": "t2"},
        ]}
        self.assertEqual(tasks._unlinked_spawn(record, "w")["key"], "t2")

    def test_an_agent_type_that_is_no_plain_name_is_dropped(self):
        steps = cycle()
        for bad in ("x" * 129, "a b", "../etc", "w$(id)"):
            self.assertIsNone(tasks.normalize(dict(steps["start"], agent_type=bad)), bad)

    def test_a_child_id_that_is_no_plain_identifier_is_dropped(self):
        steps = cycle()
        for bad in ("a" * 100000 + "\u202e", "x" * 129, "a\u202eb", "../etc", "a b", "-lead"):
            for key in ("start", "stop"):
                self.assertIsNone(tasks.normalize(dict(steps[key], agent_id=bad)), (key, bad[:12]))
        self.assertIsNotNone(tasks.normalize(steps["start"]))
        wait = dict(steps["wait_post"], tool_response={"status": {"a" * 100000 + "\u202e": {"completed": "x"}, "ok-1": "errored"}})
        self.assertEqual([i for i, _, _ in tasks.wait_results(wait["tool_response"])], ["ok-1"])

    def test_spawn_names_accept_a_plain_or_namespaced_name_and_refuse_the_rest(self):
        from devteam import review_triggers
        for good, bare in (("code-reviewer", "code-reviewer"), ("plugin:code-reviewer", "code-reviewer"), (" a.b_c ", "a.b_c"), ("x" * 64, "x" * 64)):
            self.assertEqual(review_triggers.spawn_name(good), bare, good)
        for bad in ("x" * 65, "a b", "../x", "", "a\u202eb", None, 7, "ns:"):
            self.assertIsNone(review_triggers.spawn_name(bad), bad)
        self.assertIs(trace.SAFE_NAME, review_triggers.AGENT_NAME_RE)

    def test_a_subagent_stop_on_a_non_codex_record_folds_no_review_result(self):
        steps = cycle()
        session = steps["spawn_pre"]["session_id"]
        tasks.record(self.root, steps["spawn_pre"], now=T0)
        path = tasks.record_path(self.root, self.project_id, session)
        rec = self.load(session)
        rec["provider"] = "claude"
        path.write_text(json.dumps(rec), encoding="utf-8")
        stop = dict(steps["stop"], last_assistant_message=REVIEW_MARKER)
        self.assertFalse(tasks.review_result(self.root, stop, now=T0 + 1).get("result"))


class V2DedupTest(BoardCase):
    """A task ended by a Subagent event or by the rollout's FINAL_ANSWER is never ended twice, in either order."""

    def setUp(self):
        super().setUp()
        self.rollout = self.tmp / "rollout-2023-11-14T22-13-20-{}.jsonl".format(PARENT_THREAD)
        self.rollout.write_text(json.dumps({"type": "session_meta", "payload": {"id": PARENT_THREAD}}) + "\n", encoding="utf-8")

    def agents(self):
        return {t["id"]: t for t in self.load("s1")["tasks"] if t.get("kind") == "agent"}

    def spawn(self, call, now):
        pre = {"session_id": "s1", "cwd": "", "tool_use_id": call, "hook_event_name": "PreToolUse",
               "tool_name": "collaborationspawn_agent", "transcript_path": str(self.rollout),
               "tool_input": {"task_name": "review", "agent_type": AGENT, "message": "gAAAAAB"}}
        tasks.record(self.root, pre, now=now)
        tasks.record(self.root, dict(pre, hook_event_name="PostToolUse", tool_response='{"task_name":"/root/review"}'), now=now + 1)

    def child(self, event, agent_id, now):
        payload = {"session_id": "s1", "cwd": "", "hook_event_name": event, "agent_id": agent_id, "agent_type": AGENT}
        tasks.record(self.root, payload, now=now)

    def answer(self, stamp):
        with open(str(self.rollout), "a", encoding="utf-8") as handle:
            handle.write(final_answer("/root/review", stamp=stamp))

    def stop(self, now):
        tasks.mark(self.root, {"session_id": "s1", "transcript_path": str(self.rollout)}, "idle", now=now)

    def test_a_stopped_task_does_not_hand_its_answer_to_a_sibling_of_the_same_path(self):
        self.spawn("c1", T0)
        self.spawn("c2", T0 + 2)
        self.child("SubagentStart", "child-1", T0 + 3)
        self.child("SubagentStop", "child-1", T0 + 10)
        by = self.agents()
        self.assertEqual((by["c1"]["status"], by["c2"]["status"]), ("completed", "in_progress"))
        self.answer("2023-11-14T22:30:00Z")  # c1's own answer
        self.stop(T0 + 5000)
        by = self.agents()
        self.assertEqual((by["c1"]["history"][-1]["at"], by["c2"]["status"]), (T0 + 10, "in_progress"))
        self.assertNotIn("answer_claim", by["c1"])
        self.answer("2023-11-14T23:00:00Z")
        self.stop(T0 + 9000)
        self.assertEqual(self.agents()["c2"]["status"], "completed")

    def test_a_task_the_rollout_ended_is_not_ended_again_by_its_stop(self):
        self.spawn("c1", T0)
        self.child("SubagentStart", "child-1", T0 + 2)
        self.answer("2023-11-14T22:30:00Z")
        self.stop(T0 + 5000)
        done = self.agents()["c1"]
        self.assertEqual(done["status"], "completed")
        before = json.dumps(self.load("s1"), sort_keys=True)
        self.child("SubagentStop", "child-1", T0 + 6000)
        self.assertEqual(json.dumps(self.load("s1"), sort_keys=True), before)

    def test_a_stop_ends_a_task_at_its_own_time_before_the_parents_stop(self):
        self.spawn("c1", T0)
        self.child("SubagentStart", "child-1", T0 + 2)
        self.child("SubagentStop", "child-1", T0 + 30)
        self.assertEqual((self.agents()["c1"]["status"], self.agents()["c1"]["history"][-1]["at"]), ("completed", T0 + 30))

    def test_a_claim_with_no_open_task_left_is_cleared_once_it_expires(self):
        self.spawn("c1", T0)
        self.child("SubagentStart", "child-1", T0 + 2)
        self.child("SubagentStop", "child-1", T0 + 10)
        self.assertIn("answer_claim", self.agents()["c1"])
        self.stop(T0 + 100)  # within the age cap: the claim is still held
        self.assertIn("answer_claim", self.agents()["c1"])
        self.stop(T0 + 10 + tasks.PENDING_MAX_AGE + 1)  # nothing is open: only the expiry path runs
        done = self.agents()["c1"]
        self.assertNotIn("answer_claim", done)
        self.assertEqual(done["status"], "completed")

    def test_the_execution_trace_gets_one_span_and_no_subagent_event_touches_it(self):
        pre = {"session_id": "s1", "cwd": "", "tool_use_id": "c1", "hook_event_name": "PreToolUse",
               "tool_name": "collaborationspawn_agent", "transcript_path": str(self.rollout),
               "tool_input": {"task_name": "review", "agent_type": AGENT, "message": "gAAAAAB"}}
        post = dict(pre, hook_event_name="PostToolUse", tool_response='{"task_name":"/root/review"}')
        for payload in (pre, post):
            trace.capture(self.root, payload, now=T0)
        start = {"session_id": "s1", "hook_event_name": "SubagentStart", "agent_id": "child-1", "agent_type": AGENT}
        for payload in (start, dict(start, hook_event_name="SubagentStop")):
            self.assertFalse(trace.capture(self.root, payload, now=T0 + 1)["recorded"])
        spans = json.loads(trace.trace_path(self.root, self.project_id, "s1").read_text(encoding="utf-8"))["spans"]
        self.assertEqual([(s["id"], s["agent_path"]) for s in spans], [("c1", "/root/review")])


class CodexHooksMergeOwnershipTest(unittest.TestCase):
    """Ours are removed hook by hook: a user's hook sharing a group with ours survives (ADR-0022)."""

    def mixed(self):
        ours = {"type": "command", "command": "x", "statusMessage": codex_hooks_merge.MANAGED_MARKER}
        theirs = {"type": "command", "command": "mine", "statusMessage": 7}
        return {"hooks": {"SubagentStart": [{"hooks": [ours, theirs]}]}}, theirs

    def test_merge_keeps_the_users_hook_and_survives_a_non_string_message(self):
        data, theirs = self.mixed()
        merged = codex_hooks_merge.merge(data, {})
        self.assertEqual(merged["hooks"]["SubagentStart"], [{"hooks": [theirs]}])

    def test_unwire_keeps_the_users_hook(self):
        import tempfile
        from pathlib import Path
        data, theirs = self.mixed()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / providers.CODEX_HOOKS_FILE
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps(data), encoding="utf-8")
            self.assertEqual(providers.unwire_codex_hooks(tmp), ["SubagentStart"])
            self.assertEqual(json.loads(path.read_text())["hooks"]["SubagentStart"], [{"hooks": [theirs]}])


if __name__ == "__main__":
    unittest.main()
