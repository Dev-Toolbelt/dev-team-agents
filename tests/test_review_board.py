"""The In Review column of the task board (ADR-0018 amendment, docs/specs/task-board.md).

A review window is opened by a hook (a review/QA agent spawn, a review command, an explicit
request in a prompt) and closed by the `review-result` marker in the agent's report. These
tests pin the detector, every provider payload shape, which tasks enter, each way out
(passed, findings, unread, fix rule, re-review rule, reopened), the durations, the
notifications and that a call that is not ours forks no python.
"""

import datetime
import json
import os
import re
import subprocess
import sys
import time
import unittest
from pathlib import Path

from devteam_support import CLI, REPO_ROOT, requires_bash

from devteam import hooks, review_triggers, tasks

import test_tasks as tt
from test_tasks import POST_DISPATCHER, POST_TOOL_USE, PRE_TOOL_USE, STOP_SUB, T0, todo, todo_write

HOOKS = REPO_ROOT / "scripts" / "hooks"
PROMPT_SUB = HOOKS / "user-prompt-submit" / "01-task-board.sh"
PROMPT_DISPATCHER = HOOKS / "user-prompt-submit.sh"

MARK0 = "<!-- review-result: findings=0 -->"


def marker(n):
    return "Done.\n<!-- review-result: findings={} -->".format(n)


def claude_spawn(session, agent="qa-specialist", tool="Agent"):
    return {
        "session_id": session, "cwd": "", "hook_event_name": "PreToolUse",
        "tool_name": tool, "tool_input": {"description": "d", "prompt": "p", "subagent_type": agent},
    }


def claude_return(session, text, agent="qa-specialist", tool="Agent", **extra):
    payload = {
        "session_id": session, "hook_event_name": "PostToolUse", "tool_name": tool,
        "tool_input": {"description": "d", "prompt": "p", "subagent_type": agent},
        "tool_response": {"content": [{"type": "text", "text": text}]},
    }
    payload["tool_input"].update(extra)
    return payload


def codex_spawn(session, agent="code-reviewer"):
    return {
        "session_id": session, "turn_id": "t1", "cwd": "", "hook_event_name": "PreToolUse",
        "tool_name": "spawn_agent", "tool_input": {"agent_type": agent, "message": "review"},
    }


def codex_wait(session, *texts, namespace=""):
    return {
        "session_id": session, "turn_id": "t1", "agent_id": None, "agent_type": None, "cwd": "",
        "hook_event_name": "PostToolUse", "tool_name": namespace + "wait_agent",
        "tool_input": {"targets": ["a1"]}, "tool_use_id": "u1",
        "tool_response": {"timed_out": False, "outputs": list(texts)},
    }


def opencode_spawn(session, agent="qa-specialist"):
    return {"tool": "task", "args": {"description": "d", "prompt": "p", "subagent_type": agent}, "sessionID": session}


def opencode_return(session, text, agent="qa-specialist"):
    payload = opencode_spawn(session, agent)
    payload["output"] = text
    return payload


def prompt(session, text, cwd=""):
    return {"session_id": session, "cwd": cwd, "hook_event_name": "UserPromptSubmit", "prompt": text}


class DetectorTest(unittest.TestCase):
    def kind(self, text):
        hit = review_triggers.prompt_trigger(text)
        return hit and hit[0]

    def test_commands_only_at_the_start_of_the_prompt(self):
        for text, source in (
            ("/devteam:review", "/devteam:review"), ("  /devteam:QA now", "/devteam:qa"),
            ("/review backend", "/review"), ("$devteam-review", "$devteam-review"),
        ):
            self.assertEqual(review_triggers.prompt_trigger(text), ("command", source), text)
        self.assertIsNone(review_triggers.prompt_trigger("/devteam:reviews"))
        self.assertIsNone(review_triggers.prompt_trigger("/reviewer"))
        self.assertEqual(review_triggers.prompt_trigger("please run /devteam:qa"), ("prompt", "qa"))  # a keyword, not a command

    def test_every_documented_keyword_matches_case_insensitively(self):
        for word in ("review", "REVISAR", "revisão", "revisao", "Revise", "QA", "testar", "test it"):
            self.assertEqual(self.kind("could you {} the change".format(word)), "prompt", word)
            self.assertEqual(self.kind(word.upper() + " now"), "prompt", word)

    def test_keywords_are_word_bounded(self):
        for text in ("the reviewer is out", "protest it", "aqa", "contest it", "reviews", "attest", "revisited"):
            self.assertIsNone(review_triggers.prompt_trigger(text), text)
        self.assertEqual(self.kind("(review)"), "prompt")
        self.assertEqual(self.kind("review."), "prompt")

    def test_a_negation_directly_governing_the_keyword_skips_the_match(self):
        for text in (
            "não precisa revisar", "sem review por favor", "no review needed", "don't review it",
            "please do not review", "without QA", "Don’t revise it",
            "nao testar agora", "sem nem revisar",
        ):
            self.assertIsNone(review_triggers.prompt_trigger(text), text)

    def test_a_negation_farther_than_two_words_or_across_punctuation_does_not_skip(self):
        self.assertEqual(self.kind("no wait, one more thing before we start, review it"), "prompt")
        self.assertEqual(self.kind("skip a b c review"), "prompt")
        self.assertEqual(self.kind("skip a b review"), "prompt")
        self.assertEqual(self.kind("no problem, review the code"), "prompt")
        self.assertEqual(self.kind("no, review it"), "prompt")
        self.assertEqual(self.kind("não tem problema. revisar o código"), "prompt")

    def test_only_and_just_after_a_negation_keep_it_a_request(self):
        self.assertEqual(self.kind("not only review but fix"), "prompt")
        self.assertEqual(self.kind("não apenas revisar, corrigir também"), "prompt")
        self.assertEqual(self.kind("no just review it"), "prompt")

    def test_a_question_about_a_keyword_is_not_a_request(self):
        for text in (
            "what does the QA agent do?", "How does the review work?", "why is the review slow?",
            "o que faz o agente de QA?", "como funciona o review?", "por que o revisar falhou?",
        ):
            self.assertIsNone(review_triggers.prompt_trigger(text), text)

    def test_a_question_elsewhere_in_the_prompt_does_not_hide_a_request(self):
        for text in (
            "what should I fix? review it", "please review, what do you think?",
            "review this. how long will it take?", "can you review the diff?",
        ):
            self.assertEqual(self.kind(text), "prompt", text)

    def test_the_negation_scan_is_linear_in_the_prompt(self):
        for text in ("no review " * 20000, "what review " * 20000, "a b c review. " * 20000):
            started = time.monotonic()
            review_triggers.prompt_trigger(text)
            self.assertLess(time.monotonic() - started, 2.0, text[:12])

    def test_a_later_match_survives_an_earlier_negated_one(self):
        self.assertEqual(self.kind("don't review that but do revise this"), "prompt")

    def test_unrelated_and_non_strings_do_not_match(self):
        for value in ("implement the login form", "", "   ", None, 5, ["review"]):
            self.assertIsNone(review_triggers.prompt_trigger(value))

    def test_agent_names_including_a_namespace(self):
        for name in review_triggers.REVIEW_AGENTS:
            self.assertEqual(review_triggers.agent_name(name), name)
        self.assertEqual(review_triggers.agent_name("team:QA-Specialist"), "qa-specialist")
        for name in ("Explore", "general-purpose", "qa", "", None, 3):
            self.assertIsNone(review_triggers.agent_name(name))

    def test_markers_are_summed_across_a_structure(self):
        self.assertEqual(review_triggers.markers(marker(2)), [2])
        self.assertEqual(review_triggers.markers({"a": [marker(0), {"b": "x\n<!--review-result:findings = 3-->"}]}), [0, 3])
        self.assertEqual(review_triggers.markers("<!-- review-result: findings=x -->"), [])
        self.assertEqual(review_triggers.markers(None), [])


class ReviewCase(tt.BoardCase):
    """Session `s1` with A (in progress), B (completed) and C (pending) — all created at T0."""

    def start(self, session="s1", items=None, now=T0):
        items = items or [todo("A", "in_progress"), todo("B", "completed"), todo("C")]
        self.rec(todo_write(session, items), now=now)

    def open(self, payload, now=T0 + 10):
        return tasks.review_open(self.root, payload, now=now)

    def result(self, payload, now=T0 + 20):
        return tasks.review_result(self.root, payload, now=now)

    def stop(self, payload, now=T0 + 30):
        return tasks.mark(self.root, payload, "idle", now=now)

    def session(self, now=T0 + 40, sid="s1"):
        for item in self.view(now=now)[0]["sessions"]:
            if item["session_id"] == sid:
                return item

    def columns(self, now=T0 + 40, sid="s1"):
        return {t["content"]: t["column"] for t in self.session(now, sid)["tasks"]}

    def window(self, sid="s1", index=0):
        return self.load(sid)["reviews"][index]

    def save(self, sid, rec):
        path = tasks.record_path(self.root, self.project_id, sid)
        path.write_text(json.dumps(rec), encoding="utf-8")

    def todos(self, session, *items, now):
        self.rec(todo_write(session, list(items)), now=now)


class TriggerAndEntryTest(ReviewCase):
    def test_a_claude_agent_spawn_opens_a_window_with_the_in_progress_and_completed_tasks(self):
        self.start()
        out = self.open(claude_spawn("s1"))
        self.assertEqual((out["recorded"], out["window"], out["joined"], out["session"]), (True, "r1", False, "s1"))
        window = self.window()
        self.assertEqual((window["trigger"], window["source"], window["pending"], window["opened_at"]), ("agent", "qa-specialist", 1, T0 + 10))
        self.assertEqual(window["task_keys"], ["t1", "t2"])
        self.assertEqual(self.columns(), {"A": "in_review", "B": "in_review", "C": "todo"})

    def test_the_older_task_tool_name_and_every_review_agent_trigger(self):
        for i, (agent, tool) in enumerate((("code-reviewer", "Task"), ("backend-reviewer", "Agent"), ("frontend-reviewer", "Agent"))):
            self.start("s{}".format(i))
            self.assertTrue(self.open(claude_spawn("s{}".format(i), agent, tool))["recorded"], agent)

    def test_codex_and_opencode_spawns_open_a_window(self):
        self.start("c1")
        self.start("o1")
        self.assertEqual(self.open(codex_spawn("c1"))["window"], "r1")
        self.assertEqual(self.open(opencode_spawn("o1"))["window"], "r1")
        self.assertEqual(self.load("c1")["reviews"][0]["source"], "code-reviewer")

    def test_other_agents_and_todo_tools_never_open_a_window(self):
        self.start()
        for payload in (
            claude_spawn("s1", "Explore"), claude_spawn("s1", "general-purpose"), codex_spawn("s1", "backend-developer"),
            opencode_spawn("s1", "explore"), todo_write("s1", [todo("A")]), {"session_id": "s1", "tool_name": "Bash"},
            claude_return("s1", "text", agent="Explore"),
        ):
            self.assertFalse(self.open(payload)["recorded"], payload)
        self.assertNotIn("reviews", self.load("s1"))

    def test_a_post_tool_use_payload_is_not_a_trigger(self):
        self.start()
        self.assertFalse(self.open(claude_return("s1", "no marker"))["recorded"])

    def test_a_command_and_an_explicit_request_open_a_window(self):
        self.start("s1")
        self.start("s2")
        self.assertEqual(self.open(prompt("s1", "/devteam:review"))["window"], "r1")
        self.assertEqual(self.open(prompt("s2", "por favor revisar o código"))["window"], "r1")
        self.assertEqual(self.window("s1")["trigger"], "command")
        self.assertEqual(self.window("s2")["trigger"], "prompt")
        self.assertTrue(self.window("s2")["scan"])

    def test_a_prompt_that_is_not_a_review_request_opens_nothing(self):
        self.start()
        for text in ("add a login form", "não revisar isso", "/devteam:backend fix it"):
            self.assertFalse(self.open(prompt("s1", text))["recorded"], text)

    def test_no_record_or_no_eligible_task_opens_nothing(self):
        self.assertFalse(self.open(claude_spawn("ghost"))["recorded"])
        self.start(items=[todo("C")])
        self.assertFalse(self.open(claude_spawn("s1"))["recorded"])
        self.start("s2", items=[todo("A", "in_progress")])
        self.todos("s2", todo("A", "in_progress"), now=T0 + 1)
        self.rec(todo_write("s2", []), now=T0 + 2)  # empty list clears: A removed unfinished
        self.assertFalse(self.open(claude_spawn("s2"))["recorded"])

    def test_tasks_created_after_the_window_opened_do_not_enter_it(self):
        self.start()
        self.open(claude_spawn("s1"))
        self.todos("s1", todo("A", "in_progress"), todo("B", "completed"), todo("C"), todo("D", "in_progress"), now=T0 + 15)
        self.assertEqual(self.window()["task_keys"], ["t1", "t2"])
        self.assertEqual(self.columns()["D"], "in_progress")

    def test_a_second_trigger_joins_the_open_window_and_counts_up(self):
        self.start()
        self.open(claude_spawn("s1"))
        out = self.open(claude_spawn("s1", "backend-reviewer"), now=T0 + 11)
        self.assertEqual((out["window"], out["joined"]), ("r1", True))
        self.open(prompt("s1", "/review"), now=T0 + 12)
        window = self.window()
        self.assertEqual((window["pending"], window["scan"], len(self.load("s1")["reviews"])), (3, True, 1))

    def test_a_later_window_takes_only_tasks_completed_since_the_previous_one_resolved(self):
        self.start()
        self.open(claude_spawn("s1"))
        self.result(claude_return("s1", marker(0)), now=T0 + 20)
        self.assertEqual(self.window()["resolved_at"], T0 + 20)
        self.todos("s1", todo("A", "completed"), todo("B", "completed"), todo("C", "in_progress"), todo("E", "completed"), now=T0 + 30)
        self.open(claude_spawn("s1"), now=T0 + 40)
        # B was done before the first window resolved; A finished after it, C is in progress, E is new.
        self.assertEqual(self.window(index=1)["task_keys"], ["t1", "t3", "t4"])


class EnteringBoundTest(ReviewCase):
    def test_a_resumed_session_takes_only_what_completed_since_it_resumed(self):
        self.start()  # A in progress, B completed at T0
        tasks.mark(self.root, {"session_id": "s1"}, "ended", now=T0 + 5)
        self.todos("s1", todo("A", "in_progress"), todo("B", "completed"), todo("C"), todo("D", "completed"), now=T0 + 100)
        self.assertEqual(self.load("s1")["resumed_at"], T0 + 100)
        self.open(claude_spawn("s1"), now=T0 + 110)
        self.assertEqual(self.window()["task_keys"], ["t1", "t4"])

    def test_a_session_that_never_ended_has_no_resume_bound(self):
        self.start()
        self.open(claude_spawn("s1"))
        self.assertNotIn("resumed_at", self.load("s1"))
        self.assertEqual(self.window()["task_keys"], ["t1", "t2"])

    def test_a_previous_resolution_bounds_it_even_after_a_resume(self):
        self.start()
        self.open(claude_spawn("s1"))
        self.result(claude_return("s1", marker(0)), now=T0 + 20)
        tasks.mark(self.root, {"session_id": "s1"}, "ended", now=T0 + 25)
        self.todos("s1", todo("A", "completed"), todo("B", "completed"), todo("C"), now=T0 + 30)
        self.open(claude_spawn("s1"), now=T0 + 40)
        self.assertEqual(self.window(index=1)["task_keys"], ["t1"])  # A completed after the resolution; B before it


class ResultTest(ReviewCase):
    def test_zero_findings_resolves_the_window_and_releases_the_tasks(self):
        self.start()
        self.open(claude_spawn("s1"))
        out = self.result(claude_return("s1", marker(0)))
        self.assertEqual((out["recorded"], out["result"], out["findings"], out["resolved"]), (True, True, 0, True))
        window = self.window()
        self.assertEqual((window["resolution"], window["result_at"], window["resolved_at"], window["pending"]), ("passed", T0 + 20, T0 + 20, 0))
        # B was completed -> Done; A was in progress -> back to In progress.
        self.assertEqual(self.columns(), {"A": "in_progress", "B": "done", "C": "todo"})

    def test_findings_keep_the_tasks_in_review_and_start_the_fix_clock(self):
        self.start()
        self.open(claude_spawn("s1"))
        out = self.result(claude_return("s1", marker(3)))
        self.assertEqual((out["findings"], out["resolved"]), (3, False))
        window = self.window()
        self.assertEqual((window["findings"], window["fix_after"], window["resolved_at"]), (3, T0 + 20, None))
        project = self.view()[0]
        self.assertEqual(self.columns(), {"A": "in_review", "B": "in_review", "C": "todo"})
        self.assertEqual(self.session()["tasks"][0]["review"], {"state": "findings", "findings": 3, "since": T0 + 10})
        self.assertEqual(project["with_findings"], 2)
        self.assertEqual((project["counts"]["in_review"], project["sessions"][0]["counts"]["in_review"]), (2, 2))

    def test_a_pending_window_shows_the_pending_state(self):
        self.start()
        self.open(claude_spawn("s1"))
        self.assertEqual(self.session()["tasks"][0]["review"]["state"], "pending")
        self.assertEqual(self.view()[0]["with_findings"], 0)

    def test_parallel_reviewers_are_summed_and_the_result_waits_for_the_last(self):
        self.start()
        self.open(claude_spawn("s1", "backend-reviewer"))
        self.open(claude_spawn("s1", "frontend-reviewer"))
        first = self.result(claude_return("s1", marker(1), agent="backend-reviewer"), now=T0 + 20)
        self.assertEqual((first["recorded"], first["result"], first["findings"]), (True, False, None))
        self.assertIsNone(self.window()["result_at"])
        second = self.result(claude_return("s1", marker(2), agent="frontend-reviewer"), now=T0 + 25)
        self.assertEqual((second["result"], second["findings"]), (True, 3))
        self.assertEqual(self.window()["result_at"], T0 + 25)

    def test_one_report_is_one_slot_and_its_last_marker_counts(self):
        self.start()
        self.open(dict(claude_spawn("s1", "code-reviewer"), tool_use_id="u1"))
        self.open(dict(claude_spawn("s1", "code-reviewer"), tool_use_id="u2"))
        first = claude_return("s1", marker(0) + "\n" + marker(4), agent="code-reviewer")
        first["tool_use_id"] = "u1"
        out = self.result(first)
        self.assertEqual((out["result"], self.window()["pending"], self.window()["found"]), (False, 1, 4))
        second = claude_return("s1", marker(2), agent="code-reviewer")
        second["tool_use_id"] = "u2"
        out = self.result(second)
        self.assertEqual((out["result"], out["findings"]), (True, 6))

    def test_a_marker_in_the_echoed_prompt_of_the_response_is_not_read(self):
        self.start()
        self.open(claude_spawn("s1"))
        payload = claude_return("s1", "no marker here")
        payload["tool_response"]["prompt"] = "end with " + marker(7)
        self.assertEqual(self.result(payload)["findings"], None)

    def test_codex_reads_the_result_from_wait_agent_even_when_namespaced(self):
        self.start("c1")
        self.start("c2")
        self.open(codex_spawn("c1"))
        self.open(codex_spawn("c2"))
        self.assertEqual(self.result(codex_wait("c1", marker(2)))["findings"], 2)
        self.assertEqual(self.result(codex_wait("c2", marker(0), namespace="agents."))["findings"], 0)

    def test_codex_spawn_agent_output_and_a_wait_without_a_marker_are_ignored(self):
        self.start("c1")
        self.open(codex_spawn("c1"))
        spawned = dict(codex_spawn("c1"), hook_event_name="PostToolUse", tool_response={"agent_id": "a1"})
        self.assertFalse(self.result(spawned)["recorded"])
        self.assertFalse(self.result(codex_wait("c1", "just some text"))["recorded"])
        self.assertEqual(self.window("c1")["pending"], 1)

    def test_a_codex_wait_returning_several_agents_takes_one_slot_and_one_marker_each(self):
        self.start("c1")
        self.open(dict(codex_spawn("c1"), tool_use_id="cs1"))
        self.open(dict(codex_spawn("c1", "qa-specialist"), tool_use_id="cs2"))
        self.assertEqual(self.window("c1")["fg"], ["cs1", "cs2"])
        out = self.result(codex_wait("c1", marker(1), marker(2)))
        self.assertEqual((out["result"], out["findings"]), (True, 3))
        window = self.window("c1")
        self.assertEqual((window["fg"], window["pending"], window["markers"], window["found"]), ([], 0, 2, 3))

    def test_a_codex_wait_with_fewer_markers_than_launches_leaves_the_rest_pending(self):
        self.start("c1")
        for launch in ("cs1", "cs2"):
            self.open(dict(codex_spawn("c1"), tool_use_id=launch))
        out = self.result(codex_wait("c1", marker(0)))
        self.assertEqual((out["result"], self.window("c1")["fg"]), (False, ["cs2"]))

    def test_opencode_reads_the_result_from_the_task_output(self):
        self.start("o1")
        self.open(opencode_spawn("o1"))
        self.assertEqual(self.result(opencode_return("o1", marker(5)))["findings"], 5)

    def test_a_review_agent_that_returns_no_marker_leaves_the_result_unread(self):
        self.start()
        self.open(claude_spawn("s1"))
        out = self.result(claude_return("s1", "I looked and it seems fine."))
        self.assertEqual((out["result"], out["findings"], out["resolved"]), (True, None, False))
        self.assertEqual(self.session()["tasks"][0]["review"], {"state": "unread", "findings": None, "since": T0 + 10})
        self.assertEqual(self.columns()["B"], "in_review")

    def test_one_unread_reviewer_never_turns_the_others_zero_into_a_pass(self):
        self.start()
        self.open(claude_spawn("s1", "backend-reviewer"))
        self.open(claude_spawn("s1", "frontend-reviewer"))
        self.result(claude_return("s1", marker(0), agent="backend-reviewer"))
        out = self.result(claude_return("s1", "no marker", agent="frontend-reviewer"))
        self.assertEqual((out["findings"], out["resolved"]), (None, False))

    def test_a_background_agent_launch_and_a_foreign_agent_are_not_results(self):
        self.start()
        self.open(claude_spawn("s1"))
        self.assertFalse(self.result(claude_return("s1", "started", run_in_background=True))["recorded"])
        self.assertFalse(self.result(claude_return("s1", "x", agent="Explore"))["recorded"])
        self.assertEqual(self.window()["pending"], 1)

    def test_a_result_with_no_open_window_is_ignored(self):
        self.start()
        self.assertFalse(self.result(claude_return("s1", marker(0)))["recorded"])
        self.open(claude_spawn("s1"))
        self.result(claude_return("s1", marker(2)))
        again = self.result(claude_return("s1", marker(0)))
        self.assertFalse(again["recorded"])
        self.assertEqual(self.window()["findings"], 2)

    def test_the_prompt_or_input_of_an_agent_is_never_read_as_its_result(self):
        self.start()
        self.open(claude_spawn("s1"))
        payload = claude_return("s1", "no marker here")
        payload["tool_input"]["prompt"] = "end with " + MARK0
        self.assertEqual(self.result(payload)["findings"], None)


class StopScanTest(ReviewCase):
    def transcript(self, entries):
        path = self.tmp / "t.jsonl"
        path.write_text("\n".join(json.dumps(e) for e in entries) + "\n", encoding="utf-8")
        return str(path)

    def assistant(self, text):
        return {"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": text}]}}

    def test_the_transcript_marker_is_read_at_stop_for_a_command_window(self):
        self.start()
        self.open(prompt("s1", "/devteam:review"))
        path = self.transcript([
            {"type": "user", "message": {"role": "user", "content": "/devteam:review"}},
            self.assistant("looking"),
            {"type": "assistant", "message": {"role": "assistant", "content": [{"type": "tool_use", "name": "Read"}]}},
            self.assistant("Report.\n" + marker(2)),
        ])
        out = self.stop({"session_id": "s1", "transcript_path": path})
        self.assertEqual((out["review_result"], out["review_window"], out["review_findings"]), (True, "r1", 2))
        self.assertEqual(self.window()["findings"], 2)
        self.assertEqual(self.columns()["A"], "in_review")

    def test_a_zero_marker_at_stop_resolves_the_window(self):
        self.start()
        self.open(prompt("s1", "please QA this"))
        out = self.stop({"session_id": "s1", "last_assistant_message": marker(0)})
        self.assertEqual((out["review_result"], out["review_findings"]), (True, 0))
        self.assertEqual(self.window()["resolution"], "passed")

    def test_no_marker_anywhere_records_findings_null(self):
        self.start()
        self.open(prompt("s1", "/review"))
        path = self.transcript([self.assistant("all good")])
        out = self.stop({"session_id": "s1", "transcript_path": path})
        self.assertEqual((out["review_result"], out["review_findings"]), (True, None))
        self.assertEqual(self.session()["tasks"][0]["review"]["state"], "unread")

    def test_a_marker_from_a_previous_turn_is_not_read(self):
        self.start()
        self.open(prompt("s1", "/review"))
        path = self.transcript([
            self.assistant("old\n" + marker(9)),
            {"type": "user", "message": {"role": "user", "content": [{"type": "text", "text": "/review"}]}},
            self.assistant("nothing to report"),
        ])
        self.assertIsNone(self.stop({"session_id": "s1", "transcript_path": path})["review_findings"])

    def test_the_agents_own_markers_win_over_the_final_message(self):
        self.start()
        self.open(prompt("s1", "/devteam:review"))
        self.open(claude_spawn("s1", "code-reviewer"), now=T0 + 11)
        self.result(claude_return("s1", marker(2), agent="code-reviewer"))
        self.assertIsNone(self.window()["result_at"])
        out = self.stop({"session_id": "s1", "last_assistant_message": "Summary\n" + marker(2)})
        self.assertEqual((out["review_result"], out["review_findings"]), (True, 2))

    def test_a_command_window_waits_at_stop_for_a_background_agent_still_running(self):
        self.start()
        self.open(prompt("s1", "/devteam:qa"))
        spawn = claude_spawn("s1")
        spawn["tool_input"]["run_in_background"] = True
        self.open(dict(spawn, tool_use_id="bg1"), now=T0 + 11)
        out = self.stop({"session_id": "s1", "last_assistant_message": "launched"})
        self.assertFalse(out["review_result"])
        window = self.window()
        self.assertEqual((window["pending"], window["scan"], window["bg"], window["fg"]), (1, False, ["bg1"], []))
        self.assertEqual(self.result(dict(claude_return("s1", marker(1)), tool_use_id="bg1"))["findings"], 1)

    def test_a_keyword_only_window_that_closes_unread_holds_nothing(self):
        self.start(items=[todo("A", "in_progress"), todo("Old", "completed")])
        self.open(prompt("s1", "please review it"))
        self.assertEqual(self.columns(now=T0 + 15), {"A": "in_review", "Old": "in_review"})
        out = self.stop({"session_id": "s1", "last_assistant_message": "sure, looks fine"})
        self.assertEqual((out["review_result"], out["review_findings"]), (True, None))
        window = self.window()
        self.assertEqual((window["resolution"], window["resolved_at"]), ("unread-dismissed", T0 + 30))
        self.assertEqual(self.columns(), {"A": "in_progress", "Old": "done"})
        self.assertIsNone(self.session()["tasks"][0]["review"])

    def test_a_keyword_window_with_a_marker_is_read_normally(self):
        self.start()
        self.open(prompt("s1", "revisar isso"))
        self.stop({"session_id": "s1", "last_assistant_message": marker(2)})
        self.assertIsNone(self.window()["resolved_at"])
        self.assertEqual(self.session()["tasks"][0]["review"]["state"], "findings")

    def test_command_and_agent_windows_keep_holding_when_they_close_unread(self):
        self.start()
        self.open(prompt("s1", "/devteam:review"))
        self.stop({"session_id": "s1", "last_assistant_message": "done"})
        self.assertIsNone(self.window()["resolved_at"])
        self.assertEqual(self.session()["tasks"][0]["review"]["state"], "unread")
        self.start("s2")
        self.open(prompt("s2", "review it"))
        self.open(dict(claude_spawn("s2"), tool_use_id="f1"), now=T0 + 11)  # an agent joins: no longer keyword-only
        self.stop({"session_id": "s2", "last_assistant_message": "done"})
        self.assertIsNone(self.window("s2")["resolved_at"])
        self.assertEqual(self.session(sid="s2")["tasks"][0]["review"]["state"], "unread")

    def test_a_keyword_window_joined_by_a_command_is_strong(self):
        self.start()
        self.open(prompt("s1", "review it"))
        self.open(prompt("s1", "/review"), now=T0 + 11)
        self.stop({"session_id": "s1", "last_assistant_message": "done"})
        self.assertIsNone(self.window()["resolved_at"])

    def test_an_expired_keyword_window_is_dismissed(self):
        self.start()
        self.open(prompt("s1", "review it"))
        late = T0 + 10 + tasks.PENDING_MAX_AGE + 5
        self.stop({"session_id": "s1", "last_assistant_message": "x"}, now=late)
        self.assertEqual(self.window()["resolution"], "unread-dismissed")

    def test_a_foreground_launch_still_outstanding_at_stop_is_retired_as_unread(self):
        self.start()
        self.open(dict(claude_spawn("s1"), tool_use_id="fg1"))
        out = self.stop({"session_id": "s1", "last_assistant_message": marker(0)})
        # The final message is not read for an agent window; the lost launch settles unread.
        self.assertEqual((out["review_result"], out["review_findings"]), (True, None))
        window = self.window()
        self.assertEqual((window["pending"], window["fg"], window["unread"]), (0, [], 1))
        self.assertEqual(self.session()["tasks"][0]["review"]["state"], "unread")

    def test_a_failed_foreground_agent_never_wedges_the_window(self):
        self.start()
        self.open(dict(claude_spawn("s1"), tool_use_id="fg1"))
        self.open(prompt("s1", "/review"), now=T0 + 11)
        # No PostToolUse ever arrives (Esc, a crash): the turn ends and both tokens retire.
        out = self.stop({"session_id": "s1", "last_assistant_message": "interrupted"})
        self.assertTrue(out["review_result"])
        self.assertEqual(self.window()["pending"], 0)

    def test_a_codex_spawn_with_a_wait_that_returns_no_marker_settles_at_stop(self):
        self.start("c1")
        self.open(codex_spawn("c1"))
        self.assertFalse(self.result(codex_wait("c1", "timed out, nothing yet"))["recorded"])
        out = self.stop({"session_id": "c1", "last_assistant_message": "done"})
        self.assertEqual((out["review_result"], out["review_findings"]), (True, None))

    def test_a_failed_launch_is_retired_as_unread_at_once(self):
        self.start()
        self.open(dict(claude_spawn("s1"), tool_use_id="fg1"))
        failure = claude_spawn("s1")
        failure.update(tool_use_id="fg1", hook_event_name="PostToolUseFailure", error="interrupted")
        out = self.result(failure)
        self.assertEqual((out["recorded"], out["result"], out["findings"]), (True, True, None))
        self.assertEqual((self.window()["unread"], self.window()["pending"]), (1, 0))

    def test_a_failed_background_launch_is_retired_by_its_id(self):
        self.start()
        spawn = claude_spawn("s1")
        spawn["tool_input"]["run_in_background"] = True
        self.open(dict(spawn, tool_use_id="bg1"))
        self.assertEqual(self.window()["bg"], ["bg1"])
        failure = dict(spawn, tool_use_id="bg1", hook_event_name="PostToolUseFailure", error="x")
        self.assertTrue(self.result(failure)["result"])

    def test_a_failure_of_a_foreign_tool_or_agent_is_not_ours(self):
        self.start()
        self.open(claude_spawn("s1"))
        other = claude_spawn("s1", "Explore")
        other.update(hook_event_name="PostToolUseFailure", error="x")
        self.assertFalse(self.result(other)["recorded"])
        self.assertEqual(self.window()["pending"], 1)

    def test_an_old_pending_window_is_settled_as_unread_instead_of_joined(self):
        self.start()
        self.open(dict(claude_spawn("s1"), tool_use_id="lost"), now=T0 + 10)
        late = T0 + 10 + tasks.PENDING_MAX_AGE + 1
        out = self.open(claude_spawn("s1"), now=late)
        self.assertEqual((out["window"], out["joined"]), ("r2", False))
        first = self.window(index=0)
        self.assertEqual((first["result_at"], first["findings"], first["pending"]), (late, None, 0))
        self.assertEqual(self.window(index=1)["pending"], 1)

    def test_a_recent_pending_window_is_still_joined(self):
        self.start()
        self.open(claude_spawn("s1"), now=T0 + 10)
        out = self.open(claude_spawn("s1"), now=T0 + 10 + tasks.PENDING_MAX_AGE - 1)
        self.assertEqual((out["window"], out["joined"]), ("r1", True))

    def test_the_view_and_stop_settle_a_window_that_waited_too_long(self):
        self.start()
        self.open(dict(claude_spawn("s1"), tool_use_id="lost"), now=T0 + 10)
        late = T0 + 10 + tasks.PENDING_MAX_AGE + 1
        self.assertEqual(self.session(now=late)["tasks"][0]["review"]["state"], "unread")
        self.assertEqual(self.window()["result_at"], None)  # a view never writes
        self.assertTrue(self.stop({"session_id": "s1"}, now=late)["review_result"])
        self.assertEqual(self.window()["findings"], None)

    def test_an_expired_window_takes_the_fix_rule_like_any_unread_result(self):
        self.start(items=[todo("A", "completed")])
        self.open(dict(claude_spawn("s1"), tool_use_id="lost"), now=T0 + 10)
        late = T0 + 10 + tasks.PENDING_MAX_AGE + 1
        self.stop({"session_id": "s1"}, now=late)
        self.assertEqual(self.columns(now=late + 1)["A"], "in_review")
        self.todos("s1", todo("A", "completed"), todo("Fix", "completed"), now=late + 5)
        self.assertEqual(self.window()["resolution"], "fixed")
        self.assertEqual(self.columns(now=late + 6)["A"], "done")

    def test_a_result_that_arrives_late_is_still_folded_in(self):
        self.start()
        self.open(dict(claude_spawn("s1"), tool_use_id="slow"), now=T0 + 10)
        done = dict(claude_return("s1", marker(2)), tool_use_id="slow")
        out = self.result(done, now=T0 + 10 + tasks.PENDING_MAX_AGE + 5)
        self.assertEqual((out["result"], out["findings"]), (True, 2))

    def test_a_second_prompt_joins_with_one_scan_flag_not_two_tokens(self):
        self.start()
        self.open(prompt("s1", "/review"))
        self.open(prompt("s1", "please QA it"), now=T0 + 11)
        self.assertEqual((self.window()["pending"], self.window()["scan"]), (1, True))
        out = self.stop({"session_id": "s1", "last_assistant_message": marker(0)})
        self.assertEqual((out["review_result"], out["review_findings"]), (True, 0))

    def test_an_agent_marker_never_consumes_the_scan_flag(self):
        self.start()
        self.open(prompt("s1", "/review"))
        self.result(claude_return("s1", marker(3)))
        self.assertEqual((self.window()["pending"], self.window()["scan"], self.window()["found"]), (1, True, 3))
        out = self.stop({"session_id": "s1", "last_assistant_message": marker(9)})
        self.assertEqual(out["review_findings"], 3)

    def test_a_record_written_with_a_pending_count_only_still_settles_at_stop(self):
        self.start()
        self.open(prompt("s1", "/review"))
        rec = self.load("s1")
        window = rec["reviews"][0]
        for key in ("fg", "bg", "last_at"):
            window.pop(key, None)
        window.update(scan=False, pending=2)
        self.save("s1", rec)
        out = self.stop({"session_id": "s1", "last_assistant_message": "x"})
        self.assertEqual((out["review_result"], self.window()["pending"], self.window()["unread"]), (True, 0, 2))

    def test_stop_without_a_review_window_reads_no_transcript(self):
        self.start()
        out = self.stop({"session_id": "s1", "transcript_path": str(self.tmp / "missing.jsonl")})
        self.assertEqual((out["marked"], out["review_result"]), (True, False))

    def test_a_fenced_marker_in_the_final_message_is_not_read(self):
        self.start()
        self.open(prompt("s1", "/devteam:review"))
        path = self.transcript([
            {"type": "user", "message": {"role": "user", "content": "/devteam:review"}},
            self.assistant("The marker looks like this:\n```\n" + MARK0 + "\n```\nNothing else."),
        ])
        out = self.stop({"session_id": "s1", "transcript_path": path})
        self.assertEqual((out["review_result"], out["review_findings"]), (True, None))

    def test_a_marker_that_is_not_the_last_line_is_not_read(self):
        self.start()
        self.open(prompt("s1", "/devteam:review"))
        out = self.stop({"session_id": "s1", "last_assistant_message": MARK0 + "\nOne more thing."})
        self.assertEqual((out["review_result"], out["review_findings"]), (True, None))


class LeavingTest(ReviewCase):
    def with_findings(self):
        self.start(items=[todo("A", "completed"), todo("B", "in_progress")])
        self.open(claude_spawn("s1"))
        self.result(claude_return("s1", marker(2)), now=T0 + 20)

    def all_items(self, *extra, a="completed", b="completed"):
        return [todo("A", a), todo("B", b)] + list(extra)

    def test_the_fix_rule_resolves_when_every_task_created_after_the_result_is_done(self):
        self.with_findings()
        self.todos("s1", *self.all_items(todo("Fix 1"), todo("Fix 2")), now=T0 + 30)
        self.assertEqual(self.window()["resolved_at"], None)
        self.todos("s1", *self.all_items(todo("Fix 1", "completed"), todo("Fix 2")), now=T0 + 40)
        self.assertEqual(self.window()["resolved_at"], None)
        self.todos("s1", *self.all_items(todo("Fix 1", "completed"), todo("Fix 2", "completed")), now=T0 + 50)
        window = self.window()
        self.assertEqual((window["resolved_at"], window["resolution"]), (T0 + 50, "fixed"))
        self.assertEqual(set(self.columns(now=T0 + 60).values()), {"done"})

    def test_a_cancelled_fix_counts_as_done(self):
        self.with_findings()
        self.todos("s1", *self.all_items(todo("Fix", "cancelled")), now=T0 + 30)
        self.assertEqual(self.window()["resolution"], "fixed")

    def test_without_a_fix_list_the_window_stays_open(self):
        self.with_findings()
        self.todos("s1", *self.all_items(), now=T0 + 30)
        self.assertIsNone(self.window()["resolved_at"])
        self.assertEqual(self.session(now=T0 + 40)["tasks"][0]["column"], "in_review")

    def test_a_fix_task_created_before_the_result_is_not_a_fix(self):
        self.start(items=[todo("A", "completed"), todo("B", "in_progress")])
        self.open(claude_spawn("s1"))
        self.todos("s1", todo("A", "completed"), todo("B", "in_progress"), todo("Early", "completed"), now=T0 + 15)
        self.result(claude_return("s1", marker(1)), now=T0 + 20)
        self.assertIsNone(self.window()["resolved_at"])

    def test_a_fix_task_created_in_the_same_second_as_the_result_counts(self):
        self.with_findings()  # the result lands at T0 + 20
        self.todos("s1", *self.all_items(todo("Fix", "completed")), now=T0 + 20)
        self.assertEqual(self.window()["resolution"], "fixed")

    def test_a_task_that_existed_when_the_result_arrived_is_never_a_fix_even_in_the_same_second(self):
        self.start(items=[todo("A", "completed"), todo("B", "in_progress")])
        self.open(claude_spawn("s1"), now=T0 + 10)
        self.todos("s1", *self.all_items(todo("Early", "completed"), b="in_progress"), now=T0 + 20)
        self.result(claude_return("s1", marker(1)), now=T0 + 20)
        self.assertIsNone(self.window()["resolved_at"])

    def test_the_windows_own_members_are_never_the_fix_list(self):
        self.start(items=[todo("A", "completed"), todo("B", "in_progress")])
        self.open(claude_spawn("s1"), now=T0)
        self.result(claude_return("s1", marker(2)), now=T0)  # members were created in this very second
        self.todos("s1", *self.all_items(b="completed"), now=T0 + 5)
        self.assertIsNone(self.window()["resolved_at"])

    def test_a_removed_fix_task_is_not_part_of_the_fix_list(self):
        self.with_findings()
        self.todos("s1", *self.all_items(todo("Fix 1"), todo("Fix 2")), now=T0 + 30)
        self.todos("s1", *self.all_items(todo("Fix 1", "completed")), now=T0 + 40)  # Fix 2 dropped
        self.assertEqual(self.window()["resolution"], "fixed")

    def test_the_view_applies_the_fix_rule_to_a_record_written_before_it_held(self):
        self.with_findings()
        path = tasks.record_path(self.root, self.project_id, "s1")
        data = json.loads(path.read_text())
        data["tasks"].append({
            "key": "t9", "id": None, "owner": "main", "agent_type": None, "content": "Fix", "status": "completed",
            "created_at": T0 + 30, "removed_at": None, "history": [{"status": "completed", "at": T0 + 30}],
        })
        path.write_text(json.dumps(data))
        self.assertEqual(self.columns(), {"A": "done", "B": "in_progress", "Fix": "done"})

    def test_a_later_window_with_zero_findings_resolves_the_earlier_unresolved_ones(self):
        self.with_findings()
        self.open(claude_spawn("s1"), now=T0 + 60)
        self.result(claude_return("s1", marker(0)), now=T0 + 70)
        first, second = self.load("s1")["reviews"]
        self.assertEqual((first["resolution"], first["resolved_at"]), ("fixed", T0 + 70))
        self.assertEqual((second["resolution"], second["findings"]), ("passed", 0))

    def test_a_later_zero_window_releases_an_earlier_unread_one(self):
        self.start(items=[todo("A", "completed")])
        self.open(claude_spawn("s1"))
        self.result(claude_return("s1", "no marker"))
        self.assertEqual(self.columns()["A"], "in_review")
        self.open(claude_spawn("s1"), now=T0 + 30)
        self.result(claude_return("s1", marker(0)), now=T0 + 40)
        self.assertEqual([w["resolution"] for w in self.load("s1")["reviews"]], ["fixed", "passed"])
        self.assertEqual(self.columns()["A"], "done")

    def test_a_later_window_with_findings_leaves_the_earlier_one_alone(self):
        self.with_findings()
        self.open(claude_spawn("s1"), now=T0 + 60)
        self.result(claude_return("s1", marker(1)), now=T0 + 70)
        first, second = self.load("s1")["reviews"]
        self.assertIsNone(first["resolved_at"])
        self.assertEqual(second["findings"], 1)

    def test_an_unread_result_is_released_by_the_fix_rule(self):
        self.start(items=[todo("A", "completed")])
        self.open(prompt("s1", "/review"))
        self.stop({"session_id": "s1", "last_assistant_message": "fine"})
        self.assertEqual(self.session()["tasks"][0]["review"]["state"], "unread")
        self.todos("s1", todo("A", "completed"), todo("Fix", "completed"), now=T0 + 50)
        self.assertEqual(self.window()["resolution"], "fixed")

    def test_a_reopened_task_leaves_the_window_at_once(self):
        self.start()
        self.open(claude_spawn("s1"))
        self.todos("s1", todo("A", "in_progress"), todo("B", "in_progress"), todo("C"), now=T0 + 15)
        window = self.window()
        self.assertEqual(window["left"], {"t2": T0 + 15})
        self.assertEqual(self.columns(now=T0 + 16), {"A": "in_review", "B": "in_progress", "C": "todo"})
        self.assertIsNone(self.window()["resolved_at"])

    def test_any_transition_out_of_the_review_states_leaves_the_window_and_stops_accruing(self):
        self.start()
        self.open(claude_spawn("s1"), now=T0 + 10)
        # A: in_progress -> pending; B: completed -> cancelled; both leave.
        self.todos("s1", todo("A"), todo("B", "cancelled"), todo("C"), now=T0 + 15)
        self.assertEqual(self.window()["left"], {"t1": T0 + 15, "t2": T0 + 15})
        view = {t["content"]: t for t in self.session(now=T0 + 500)["tasks"]}
        self.assertEqual(view["A"]["durations"]["in_review"], 5)
        self.assertEqual(view["A"]["column"], "todo")
        self.assertEqual(view["B"]["durations"]["in_review"], 5)

    def test_a_task_dropped_while_unfinished_leaves_the_window(self):
        self.start()
        self.open(claude_spawn("s1"), now=T0 + 10)
        self.todos("s1", todo("B", "completed"), todo("C"), now=T0 + 15)  # A omitted: removed
        self.assertEqual(self.window()["left"], {"t1": T0 + 15})

    def test_a_task_that_is_in_progress_when_the_window_opens_stays_in_it(self):
        self.start()
        self.open(claude_spawn("s1"))
        self.todos("s1", todo("A", "in_progress"), todo("B", "completed"), todo("C"), now=T0 + 15)
        self.assertEqual(self.window()["left"], {})

    def test_a_task_completed_while_in_review_stays_until_the_review_ends(self):
        self.start()
        self.open(claude_spawn("s1"))
        self.todos("s1", todo("A", "completed"), todo("B", "completed"), todo("C"), now=T0 + 15)
        self.assertEqual(self.columns(now=T0 + 16)["A"], "in_review")


class DurationAndDoneTest(ReviewCase):
    def test_in_review_time_runs_from_the_window_opening_to_its_resolution(self):
        self.start()
        self.open(claude_spawn("s1"), now=T0 + 100)
        during = {t["content"]: t["durations"]["in_review"] for t in self.session(now=T0 + 160)["tasks"]}
        self.assertEqual(during, {"A": 60, "B": 60, "C": 0})
        self.result(claude_return("s1", marker(0)), now=T0 + 190)
        after = {t["content"]: t["durations"]["in_review"] for t in self.session(now=T0 + 900)["tasks"]}
        self.assertEqual(after, {"A": 90, "B": 90, "C": 0})

    def test_a_reopened_task_stops_accruing_and_overlapping_windows_are_not_double_counted(self):
        self.start(items=[todo("A", "completed")])
        self.open(claude_spawn("s1"), now=T0 + 100)
        self.result(claude_return("s1", marker(1)), now=T0 + 110)
        self.open(claude_spawn("s1"), now=T0 + 120)
        self.todos("s1", todo("A", "completed"), now=T0 + 130)
        seconds = self.session(now=T0 + 200)["tasks"][0]["durations"]["in_review"]
        self.assertEqual(seconds, 100)  # one merged span from T0+100 to now, not 100 + 80
        self.todos("s1", todo("A", "in_progress"), now=T0 + 150)
        self.assertEqual(self.session(now=T0 + 400)["tasks"][0]["durations"]["in_review"], 50)

    def test_review_seconds_with_a_controlled_clock_are_non_zero_and_merged(self):
        rec = {
            "tasks": [],
            "reviews": [
                {"opened_at": 100, "resolved_at": 160, "task_keys": ["t1", "t2"], "left": {"t2": 130}},
                {"opened_at": 150, "resolved_at": None, "task_keys": ["t1"], "left": {}},
            ],
        }
        self.assertEqual(tasks._review_seconds(rec, until=200), {"t1": 100, "t2": 30})
        self.assertEqual(tasks._review_spans(rec, 200), {"t1": [(100, 200)], "t2": [(100, 130)]})
        self.assertEqual(tasks._review_seconds(rec, until=100), {})

    def test_durations_partition_time_while_a_task_is_in_review(self):
        self.start(items=[todo("A", "in_progress"), todo("B", "completed")])
        self.open(claude_spawn("s1"), now=T0 + 100)
        self.result(claude_return("s1", marker(1)), now=T0 + 160)
        for content, status in (("A", "in_progress"), ("B", "completed")):
            task = {t["content"]: t for t in self.session(now=T0 + 400)["tasks"]}[content]
            d = task["durations"]
            self.assertEqual(d["in_review"], 300)
            # 400 seconds of life: 300 in review, the remaining 100 under the provider status.
            self.assertEqual(d[status], 100, content)
            self.assertEqual(d["pending"] + d["in_progress"] + d["completed"] + d["in_review"], 400)

    def test_a_task_that_leaves_the_window_resumes_counting_under_its_status(self):
        self.start(items=[todo("A", "completed")])
        self.open(claude_spawn("s1"), now=T0 + 100)
        self.result(claude_return("s1", marker(1)), now=T0 + 110)
        self.todos("s1", todo("A", "in_progress"), now=T0 + 150)
        d = self.session(now=T0 + 400)["tasks"][0]["durations"]
        self.assertEqual((d["in_review"], d["completed"], d["in_progress"]), (50, 100, 250))

    def test_session_done_is_not_reached_while_a_task_is_in_review_and_fires_on_the_pass(self):
        self.start(items=[todo("A", "in_progress")])
        self.open(claude_spawn("s1"), now=T0 + 10)
        out = self.rec(todo_write("s1", [todo("A", "completed")]), now=T0 + 20)
        self.assertEqual((out["all_done"], out["became_all_done"]), (False, False))
        passed = self.result(claude_return("s1", marker(0)), now=T0 + 30)
        self.assertEqual((passed["all_done"], passed["became_all_done"]), (True, True))

    def test_findings_keep_the_session_open_until_the_fix_completes_it(self):
        self.start(items=[todo("A", "completed")])
        self.open(claude_spawn("s1"), now=T0 + 10)
        found = self.result(claude_return("s1", marker(1)), now=T0 + 20)
        self.assertEqual((found["all_done"], found["became_all_done"]), (False, False))
        out = self.rec(todo_write("s1", [todo("A", "completed"), todo("Fix", "completed")]), now=T0 + 30)
        self.assertEqual((out["all_done"], out["became_all_done"]), (True, True))

    def test_a_session_that_ends_in_review_flags_its_tasks_abandoned(self):
        self.start(items=[todo("A", "completed")])
        self.open(claude_spawn("s1"), now=T0 + 10)
        self.assertEqual(tasks.mark(self.root, {"session_id": "s1"}, "ended", now=T0 + 20)["open"], 1)
        task = self.session(now=T0 + 30)["tasks"][0]
        self.assertEqual((task["column"], task["abandoned"], task["stale"]), ("in_review", True, False))

    def test_a_task_in_review_is_never_stale(self):
        self.start(items=[todo("A", "in_progress")])
        self.open(claude_spawn("s1"), now=T0 + 10)
        task = self.session(now=T0 + 10 + 7200)["tasks"][0]
        self.assertFalse(task["stale"])


class CompatibilityTest(ReviewCase):
    def test_a_record_without_reviews_reads_and_takes_a_window_later(self):
        self.start()
        data = self.load("s1")
        self.assertNotIn("reviews", data)
        self.assertEqual(self.session()["tasks"][0]["review"], None)
        self.assertEqual(self.view()[0]["with_findings"], 0)
        self.assertTrue(self.open(claude_spawn("s1"))["recorded"])

    def test_a_structurally_bad_window_makes_the_record_unreadable_not_the_board(self):
        self.start()
        self.start("s2")
        path = tasks.record_path(self.root, self.project_id, "s1")
        data = json.loads(path.read_text())
        data["reviews"] = [{"id": 1}]
        path.write_text(json.dumps(data))
        self.assertEqual([s["session_id"] for s in self.view()[0]["sessions"]], ["s2"])

    def test_the_tasks_ended_while_no_review_ran_keep_their_columns(self):
        self.start()
        self.assertEqual(self.columns(), {"A": "in_progress", "B": "done", "C": "todo"})


class CliReviewTest(ReviewCase):
    def call(self, *argv, payload=""):
        code, out, err = self.run_cli(
            "--json", "tasks", *argv, "--project-root", str(self.root),
            input_text=payload if isinstance(payload, str) else json.dumps(payload),
        )
        return code, json.loads(out) if out.strip() else None, err

    def test_review_open_and_result_round_trip_through_the_real_entry_point(self):
        self.start()
        code, opened, err = self.call("review-open", payload=claude_spawn("s1"))
        self.assertEqual((code, opened["window"], opened["recorded"]), (0, "r1", True), err)
        code, done, _ = self.call("review-result", payload=claude_return("s1", marker(2)))
        self.assertEqual((code, done["result"], done["findings"]), (0, True, 2))
        code, out, _ = self.run_cli("--json", "tasks", "list")
        listing = json.loads(out)["projects"][0]
        self.assertEqual((listing["counts"]["in_review"], listing["with_findings"]), (2, 2))

    def test_both_exit_zero_on_garbage_and_report_nothing_recorded(self):
        for sub in ("review-open", "review-result"):
            for payload in ("", "not json", "[]", json.dumps({"session_id": "s"})):
                code, body, _ = self.call(sub, payload=payload)
                self.assertEqual(code, 0, (sub, payload))
                self.assertFalse(body["recorded"])

    def test_list_text_shows_the_review_column_and_badges(self):
        self.start()
        self.open(claude_spawn("s1"))
        self.result(claude_return("s1", marker(2)))
        code, out, _ = self.run_cli("tasks", "list")
        self.assertIn("in review 2", out)
        self.assertIn("[2 findings]", out)


@requires_bash()
class ReviewHookTest(tt.HookTest):
    def start(self, session="s1"):
        self.run_script(POST_TOOL_USE, todo_write(session, [todo("A", "in_progress"), todo("B", "completed")], cwd=str(self.root)))
        return self.python_calls()

    def codes(self):
        return [r["code"] for r in self.queue()]

    def test_the_prompt_gate_forks_no_python_for_an_unrelated_prompt_or_a_path_that_looks_related(self):
        self.start()
        base = self.python_calls()
        for text in ("implement the login form", "add a button", ""):
            result = self.run_script(PROMPT_SUB, prompt("s1", text, cwd=str(self.root) + "/review/test/qa"))
            self.assertEqual((result.stdout, result.stderr), (b"", b""))
        self.run_script(PROMPT_SUB, {"session_id": "s1", "hook_event_name": "UserPromptSubmit"})
        self.assertEqual(self.python_calls(), base)
        self.assertNotIn("reviews", self.load("s1"))

    def test_a_review_prompt_without_a_task_record_forks_no_python(self):
        self.run_script(PROMPT_SUB, prompt("ghost", "/devteam:review"))
        self.assertEqual(self.python_calls(), 0)

    def test_the_gate_is_a_loose_substring_and_the_detector_is_the_authority(self):
        base = self.start()
        self.run_script(PROMPT_SUB, prompt("s1", "the contest is a protest"))  # gate passes on "test", detector refuses
        self.assertEqual(self.python_calls(), base + 1)
        self.assertNotIn("reviews", self.load("s1"))

    def test_a_review_command_and_a_keyword_open_windows_through_the_hook_and_the_dispatcher(self):
        self.start("s1")
        self.start("s2")
        self.run_script(PROMPT_SUB, prompt("s1", "/DevTeam:Review"))
        self.run_script(PROMPT_DISPATCHER, prompt("s2", "por favor REVISAR o que fiz"))
        self.assertEqual(self.window("s1")["source"], "/devteam:review")
        self.assertEqual(self.window("s2")["trigger"], "prompt")

    def test_pre_tool_use_opens_a_window_for_each_provider_shape(self):
        for sid in ("s1", "c1", "o1"):
            self.start(sid)
        for payload in (claude_spawn("s1"), codex_spawn("c1"), opencode_spawn("o1")):
            self.assertEqual(self.run_script(PRE_TOOL_USE, payload).stdout, b"")
        for sid in ("s1", "c1", "o1"):
            self.assertEqual(self.window(sid)["trigger"], "agent")

    def test_pre_tool_use_forks_no_python_for_a_command_that_merely_names_an_agent(self):
        base = self.start()
        for payload in (
            {"tool_name": "Bash", "session_id": "s1", "tool_input": {"command": "echo qa-specialist spawn_agent"}},
            {"tool_name": "Read", "session_id": "s1", "tool_input": {"file_path": "agents/qa-specialist.md"}},
            {"tool_name": "TaskCreate", "session_id": "s1", "tool_input": {"subject": "qa-specialist"}},
        ):
            self.run_script(PRE_TOOL_USE, payload)
        self.assertEqual(self.python_calls(), base)

    def test_a_built_in_agent_opens_no_window_and_is_no_task(self):
        self.start()
        for payload in (claude_spawn("s1", "Explore"), codex_spawn("s1", "worker"), opencode_spawn("s1", "explore")):
            self.run_script(PRE_TOOL_USE, payload)
        self.assertEqual(self.load("s1").get("reviews", []), [])
        self.assertEqual([t for t in self.load("s1")["tasks"] if t.get("kind") == "agent"], [])

    def test_pre_tool_use_forks_no_python_for_a_review_agent_in_a_session_without_a_record(self):
        self.run_script(PRE_TOOL_USE, claude_spawn("ghost"))
        self.assertEqual(self.python_calls(), 0)

    def test_post_tool_use_reads_a_claude_result_and_raises_findings_once(self):
        self.start()
        self.run_script(PRE_TOOL_USE, claude_spawn("s1"))
        self.run_script(POST_TOOL_USE, claude_return("s1", marker(3)))
        self.run_script(POST_TOOL_USE, claude_return("s1", marker(3)))
        self.assertEqual(self.codes(), ["tasks.review_findings"])
        note = self.queue()[0]
        self.assertEqual((note["level"], note["session_id"]), ("warning", "s1"))
        self.assertIn("3", note["message"])
        self.assertEqual(self.window()["findings"], 3)

    def test_each_window_notifies_once_for_its_own_findings(self):
        self.start()
        self.run_script(PRE_TOOL_USE, claude_spawn("s1"))
        self.run_script(POST_TOOL_USE, claude_return("s1", marker(1)))
        self.run_script(PRE_TOOL_USE, claude_spawn("s1"))
        self.run_script(POST_TOOL_USE, claude_return("s1", marker(2)))
        self.assertEqual(self.codes(), ["tasks.review_findings", "tasks.review_findings"])

    def test_a_zero_result_notifies_nothing_while_tasks_remain_open(self):
        self.start()
        self.run_script(PRE_TOOL_USE, claude_spawn("s1"))
        self.run_script(POST_TOOL_USE, claude_return("s1", marker(0)))
        self.assertEqual(self.codes(), [])
        self.assertEqual(self.window()["resolution"], "passed")

    def test_session_done_is_raised_when_the_pass_releases_the_last_open_task(self):
        self.run_script(POST_TOOL_USE, todo_write("s1", [todo("A", "in_progress")], cwd=str(self.root)))
        self.run_script(PRE_TOOL_USE, claude_spawn("s1"))
        self.run_script(POST_TOOL_USE, todo_write("s1", [todo("A", "completed")], cwd=str(self.root)))
        self.assertEqual(self.codes(), [])
        self.run_script(POST_TOOL_USE, claude_return("s1", marker(0)))
        self.assertEqual(self.codes(), ["tasks.session_done"])

    def test_post_tool_use_reads_codex_and_opencode_results(self):
        self.start("c1")
        self.start("o1")
        self.run_script(PRE_TOOL_USE, codex_spawn("c1"))
        self.run_script(PRE_TOOL_USE, opencode_spawn("o1"))
        self.run_script(POST_TOOL_USE, codex_wait("c1", marker(4), namespace="agents."))
        self.run_script(POST_DISPATCHER, opencode_return("o1", marker(0)))
        self.assertEqual(self.window("c1")["findings"], 4)
        self.assertEqual(self.window("o1")["resolution"], "passed")

    def test_post_tool_use_forks_no_python_for_other_tools_without_the_marker_words(self):
        base = self.start()
        for payload in (
            {"tool_name": "Edit", "session_id": "s1", "tool_input": {}},
            {"tool_name": "Bash", "session_id": "s1", "tool_input": {"command": "echo review-result"}},
            {"tool": "bash", "session_id": "s1", "output": "review-result"},
        ):
            self.run_script(POST_TOOL_USE, payload)
        self.assertEqual(self.python_calls(), base)

    def test_a_failed_subagent_launch_is_retired_by_the_failure_event(self):
        self.start()
        self.run_script(PRE_TOOL_USE, dict(claude_spawn("s1"), tool_use_id="fg1"))
        failure = dict(claude_spawn("s1"), tool_use_id="fg1", hook_event_name="PostToolUseFailure", error="Interrupted")
        self.run_script(POST_TOOL_USE, failure)
        window = self.window()
        self.assertEqual((window["pending"], window["unread"], window["findings"]), (0, 1, None))

    def test_a_big_payload_through_the_dispatchers_is_fast_silent_and_forks_nothing(self):
        base = self.start()
        big = {"tool_name": "Bash", "session_id": "s1", "tool_input": {"command": "x" * 1_000_000}}
        started = time.monotonic()
        for script in (PRE_TOOL_USE, POST_DISPATCHER):
            result = self.run_script(script, big)
            self.assertEqual((result.stdout, result.stderr), (b"", b""))
        pasted = prompt("s1", "x" * 1_000_000)
        result = self.run_script(PROMPT_DISPATCHER, pasted)
        self.assertEqual((result.stdout, result.stderr), (b"", b""))
        self.assertLess(time.monotonic() - started, 20)
        self.assertEqual(self.python_calls(), base)

    def test_a_review_request_ahead_of_a_pasted_log_still_opens_a_window(self):
        self.start()
        self.run_script(PROMPT_DISPATCHER, prompt("s1", "please review this log:\n" + "line\n" * 100_000))
        self.assertEqual(self.window()["trigger"], "prompt")

    def test_post_tool_use_forks_no_python_without_a_record(self):
        self.run_script(POST_TOOL_USE, claude_return("ghost", marker(1)))
        self.assertEqual(self.python_calls(), 0)

    def test_stop_settles_a_command_window_and_notifies(self):
        self.start()
        self.run_script(PROMPT_SUB, prompt("s1", "/devteam:review"))
        payload = self.tmp / "stop.json"
        payload.write_text(json.dumps({"session_id": "s1", "last_assistant_message": marker(2)}))
        result = self.run_script(STOP_SUB, "", {"DEVTEAM_HOOK_PAYLOAD": str(payload)})
        self.assertEqual(result.stdout, b"")
        self.assertEqual(self.codes(), ["tasks.review_findings"])

    def test_the_review_notification_follows_the_language_preference(self):
        prefs = Path(self.root) / ".dev-team-agents" / "resolved" / "preferences.json"
        prefs.parent.mkdir(parents=True, exist_ok=True)
        prefs.write_text(json.dumps({"language": "pt-BR"}))
        self.start()
        self.run_script(PRE_TOOL_USE, claude_spawn("s1"))
        self.run_script(POST_TOOL_USE, claude_return("s1", marker(2)))
        self.assertIn("revisão", self.queue()[0]["message"])

    def test_every_new_hook_exits_zero_and_silent_on_garbage(self):
        for script in (PROMPT_SUB, PROMPT_DISPATCHER, PRE_TOOL_USE, POST_TOOL_USE, POST_DISPATCHER):
            result = self.run_script(script, "not json at all review qa test")
            self.assertEqual((result.stdout, result.stderr), (b"", b""), script)

    def window(self, sid="s1", index=0):
        return self.load(sid)["reviews"][index]

    def save(self, sid, rec):
        path = tasks.record_path(self.root, self.project_id, sid)
        path.write_text(json.dumps(rec), encoding="utf-8")


# The inherited board-hook tests already run in test_tasks; only the review ones run here.
for _name in [n for n in dir(tt.HookTest) if n.startswith("test_")]:
    if _name not in ReviewHookTest.__dict__:
        setattr(ReviewHookTest, _name, None)

    def lib(self, payload):
        script = 'source "$1"; devteam_task_board_session_id "$2"'
        result = subprocess.run(
            ["bash", "-c", script, "x", str(HOOKS / "lib" / "task-board.sh"), payload],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True,
        )
        return result.stdout.decode()

    def test_the_first_session_key_wins_over_one_a_tool_echoes(self):
        self.assertEqual(self.lib('{"session_id": "real", "tool_input": {"session_id": "fake"}}'), "real")
        self.assertEqual(self.lib('{"sessionID": "real", "args": {"sessionID": "fake"}, "output": "\\"session_id\\": \\"x\\""}'), "real")
        self.assertEqual(self.lib('{"tool": "task", "session_id": "a1", "output": "session_id: \\"b2\\""}'), "a1")
        self.assertEqual(self.lib('{"session_id": "../etc"}'), "")
        self.assertEqual(self.lib('{"x": 1}'), "")

    def test_a_stop_closing_several_windows_raises_one_notification_per_findings_window(self):
        self.start()
        self.run_script(PROMPT_SUB, prompt("s1", "/devteam:review"))
        rec = self.load("s1")
        second = json.loads(json.dumps(rec["reviews"][0]))
        second["id"] = "r2"
        rec["reviews"].append(second)
        self.save("s1", rec)
        payload = self.tmp / "stop.json"
        payload.write_text(json.dumps({"session_id": "s1", "last_assistant_message": marker(2)}))
        self.run_script(STOP_SUB, "", {"DEVTEAM_HOOK_PAYLOAD": str(payload)})
        self.assertEqual(self.codes(), ["tasks.review_findings", "tasks.review_findings"])

    def save(self, sid, rec):
        path = tasks.record_path(self.root, self.project_id, sid)
        path.write_text(json.dumps(rec), encoding="utf-8")


class WiringTest(tt.BoardCase):
    def test_bind_wires_user_prompt_submit_and_the_wider_post_tool_use_matcher(self):
        settings = json.loads((self.root / ".claude" / "settings.json").read_text())
        events = dict(hooks.EVENTS)
        self.assertEqual(events["UserPromptSubmit"], "user-prompt-submit.sh")
        (prompt_entry,) = [e for e in settings["hooks"]["UserPromptSubmit"] if hooks._is_devteam_entry(e, "user-prompt-submit.sh")]
        self.assertNotIn("matcher", prompt_entry)
        (post,) = [e for e in settings["hooks"]["PostToolUse"] if hooks._is_devteam_entry(e, "post-tool-use.sh")]
        self.assertEqual(post["matcher"], "TodoWrite|TaskCreate|TaskUpdate|Agent|Task")
        (failure,) = [e for e in settings["hooks"]["PostToolUseFailure"] if hooks._is_devteam_entry(e, "post-tool-use.sh")]
        self.assertEqual(failure["matcher"], "Agent|Task")
        self.assertEqual(set(hooks.registered_events(self.root)), {e for e, _ in hooks.EVENTS})

    def test_the_new_dispatcher_and_sub_script_exist_and_share_the_naming_convention(self):
        self.assertTrue(PROMPT_DISPATCHER.is_file() and PROMPT_SUB.is_file())
        self.assertRegex(PROMPT_SUB.name, r"^[0-9]{2}[a-z]?-[a-z0-9]([a-z0-9-]*[a-z0-9])?\.sh$")

    def test_the_codex_installer_writes_the_new_managed_events(self):
        text = (REPO_ROOT / "scripts" / "install-codex.sh").read_text(encoding="utf-8")
        body = re.search(r"python3 - \"\$HOOKS_FILE\" \"\$HOOKS_DIR_REL\" <<'PY'\n(.*?)\nPY\n", text, re.S).group(1)
        target = self.tmp / "hooks.json"
        target.write_text(json.dumps({"hooks": {"PostToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": "mine"}]}]}}))
        for _ in range(2):
            subprocess.run([sys.executable, "-c", body, str(target), ".dev-team-agents/scripts/hooks"], check=True, stdout=subprocess.PIPE)
        data = json.loads(target.read_text())["hooks"]
        for event, script in (("PostToolUse", "post-tool-use.sh"), ("UserPromptSubmit", "user-prompt-submit.sh"), ("SessionEnd", "session-end.sh")):
            ours = [g for g in data[event] if any("_dev_team_agents_managed" in h.get("statusMessage", "") for h in g["hooks"])]
            self.assertEqual(len(ours), 1, event)
            self.assertIn(script, ours[0]["hooks"][0]["command"])
        self.assertEqual(data["PostToolUse"][0]["hooks"][0]["command"], "mine")
        (post,) = [g for g in data["PostToolUse"] if any("_dev_team_agents_managed" in h.get("statusMessage", "") for h in g["hooks"])]
        self.assertEqual(post["matcher"], ".*(wait_agent|spawn_agent|close_agent)")
        for tool in ("wait_agent", "agents.wait_agent", "spawn_agent", "close_agent"):
            self.assertTrue(re.search(post["matcher"], tool), tool)
        self.assertFalse(re.search(post["matcher"], "update_plan"))
        self.assertFalse(re.search(post["matcher"], "shell") or re.search(post["matcher"], "update_plan"))
        for event in ("UserPromptSubmit", "SessionEnd", "Stop"):
            (group,) = [g for g in data[event] if any("_dev_team_agents_managed" in h.get("statusMessage", "") for h in g["hooks"])]
            self.assertEqual(group["matcher"], "*", event)

    def test_the_opencode_plugin_binds_the_new_events_and_gives_its_hooks_a_real_stdin(self):
        text = (REPO_ROOT / "opencode" / "plugin" / "dev-team-agents.ts").read_text(encoding="utf-8")
        for needle in ('"tool.execute.after"', '"chat.message"', "post-tool-use.sh", "user-prompt-submit.sh", "last_assistant_message"):
            self.assertIn(needle, text)
        self.assertNotIn("execAsync", text)

    def test_the_opencode_plugin_ignores_stderr_kills_the_process_group_and_stops_at_the_last_user_message(self):
        text = (REPO_ROOT / "opencode" / "plugin" / "dev-team-agents.ts").read_text(encoding="utf-8")
        self.assertIn('stdio: ["pipe", "pipe", "ignore"]', text)
        self.assertIn("detached", text)
        self.assertIn("process.kill(-child.pid", text)
        self.assertIn('if (role === "user") break', text)
        self.assertIn("last_assistant_message: lastText", text)
        self.assertEqual(text.count("last_assistant_message"), 2)

    def test_the_dispatchers_pipe_the_payload_with_printf(self):
        for name in ("pre-tool-use.sh", "post-tool-use.sh", "user-prompt-submit.sh"):
            text = (HOOKS / name).read_text(encoding="utf-8")
            self.assertNotIn('echo "$INPUT"', text, name)
            self.assertIn("printf '%s\\n' \"$INPUT\" |", text, name)


class BackgroundReviewTest(ReviewCase):
    """A reviewer launched with `run_in_background` reports through a transcript notification."""

    def setUp(self):
        super().setUp()
        self.path = self.tmp / "bg.jsonl"
        self.path.write_text('{"type":"user","message":{"role":"user","content":"go"}}\n', encoding="utf-8")

    def append(self, *entries, raw=""):
        with open(self.path, "a", encoding="utf-8") as handle:
            for entry in entries:
                handle.write(json.dumps(entry) + "\n")
            handle.write(raw)

    def notification(self, text, launch="tu1", status="completed"):
        return (
            "<task-notification>\n<task-id>a1</task-id>\n<tool-use-id>{}</tool-use-id>\n"
            "<status>{}</status>\n<summary>done</summary>\n<result>{}</result>\n</task-notification>"
        ).format(launch, status, text)

    def stamp(self, seconds=15):
        return datetime.datetime.fromtimestamp(T0 + seconds, datetime.timezone.utc).isoformat().replace("+00:00", "Z")

    def hand_back(self, text, launch="tu1", at="default", status="completed"):
        body = self.notification(text, launch, status)
        stamp = {} if at is None else {"timestamp": self.stamp() if at == "default" else at}
        return [
            dict({"type": "queue-operation", "operation": "enqueue", "content": body}, **stamp),
            dict({"type": "user", "message": {"role": "user", "content": body}}, **stamp),
        ]

    def launch(self, launch="tu1"):
        spawn = claude_spawn("s1")
        spawn.update(tool_use_id=launch, transcript_path=str(self.path))
        spawn["tool_input"]["run_in_background"] = True
        self.open(spawn)
        ack = claude_return("s1", "Async agent launched", run_in_background=True)
        ack.update(tool_use_id=launch, tool_response={"isAsync": True, "status": "async_launched"})
        self.assertFalse(self.result(ack)["recorded"])

    def stop_bg(self, now=T0 + 30):
        return self.stop({"session_id": "s1", "transcript_path": str(self.path), "last_assistant_message": "ok"}, now=now)

    def test_a_launch_ack_keeps_the_window_pending_and_is_not_unread(self):
        self.start()
        self.launch()
        self.assertEqual((self.window()["pending"], self.window()["result_at"]), (1, None))
        self.assertFalse(self.stop_bg()["review_result"])
        self.assertEqual(self.session()["tasks"][0]["review"]["state"], "pending")

    def test_a_task_notification_after_the_launch_records_the_result_at_stop(self):
        self.start()
        self.launch()
        self.append(*self.hand_back(marker(2)))
        out = self.stop_bg()
        self.assertEqual((out["review_result"], out["review_window"], out["review_findings"]), (True, "r1", 2))
        self.assertEqual(self.window()["markers"], 1)
        self.assertEqual(self.columns()["A"], "in_review")

    def test_the_queue_entry_and_the_user_entry_are_one_result(self):
        self.start()
        self.launch()
        self.append(*self.hand_back(marker(0)))
        out = self.stop_bg()
        self.assertEqual((out["review_findings"], self.window()["markers"]), (0, 1))
        self.assertEqual(self.window()["resolution"], "passed")

    def test_a_later_stop_does_not_consume_the_same_notification_again(self):
        self.start()
        self.open(prompt("s1", "/devteam:review"), now=T0 + 5)
        self.launch()
        self.stop_bg(now=T0 + 25)
        self.append(*self.hand_back(marker(1)))
        self.stop_bg(now=T0 + 30)
        window = self.window()
        self.assertEqual((window["pending"], window["found"], window["markers"]), (0, 1, 1))
        self.assertEqual(self.stop_bg(now=T0 + 31)["review_result"], False)
        self.assertEqual(self.window()["found"], 1)

    def test_offset_advances_so_only_new_bytes_are_read(self):
        self.start()
        self.launch()
        self.append({"type": "assistant", "message": {"role": "assistant", "content": "x" * 50}})
        self.stop_bg()
        size = self.path.stat().st_size
        self.assertEqual(self.window()["tx_offset"], size)

    def test_a_partial_trailing_line_waits_for_the_next_stop(self):
        self.start()
        self.launch()
        whole = json.dumps(self.hand_back(marker(3))[0])
        self.append(raw=whole[:40])
        self.assertFalse(self.stop_bg()["review_result"])
        self.append(raw=whole[40:] + "\n")
        self.assertEqual(self.stop_bg(now=T0 + 31)["review_findings"], 3)

    def test_a_notification_older_than_the_window_is_ignored(self):
        self.start()
        self.launch()
        self.append(*self.hand_back(marker(5), at="1970-01-01T00:00:00Z"))
        self.assertFalse(self.stop_bg()["review_result"])
        self.assertEqual(self.window()["pending"], 1)

    def test_a_finished_reviewer_without_a_marker_is_unread(self):
        self.start()
        self.launch()
        self.append(*self.hand_back("I reviewed it, all fine."))
        out = self.stop_bg()
        self.assertEqual((out["review_result"], out["review_findings"]), (True, None))
        self.assertEqual(self.session()["tasks"][0]["review"]["state"], "unread")

    def test_a_marker_less_notification_of_an_unknown_agent_is_ignored(self):
        self.start()
        self.launch()
        self.append(*self.hand_back("some other agent", launch="other"))
        self.assertFalse(self.stop_bg()["review_result"])
        self.assertEqual(self.window()["pending"], 1)

    def test_a_foreground_result_is_not_counted_again_from_the_transcript(self):
        self.start()
        spawn = claude_spawn("s1")
        spawn.update(tool_use_id="fg1", transcript_path=str(self.path))
        self.open(spawn)
        done = claude_return("s1", marker(0))
        done["tool_use_id"] = "fg1"
        self.assertTrue(self.result(done)["result"])
        self.assertFalse(self.result(done)["recorded"])
        self.assertEqual(self.window()["markers"], 1)

    def test_a_notification_without_a_timestamp_cannot_bypass_the_window_start(self):
        self.start()
        self.launch()
        self.append(*self.hand_back(marker(5), at=None))
        self.assertFalse(self.stop_bg()["review_result"])
        self.assertEqual(self.window()["pending"], 1)

    def test_only_queue_operation_and_user_entries_are_hand_backs(self):
        self.start()
        self.launch()
        body = self.notification(marker(5))
        self.append(
            {"type": "assistant", "timestamp": self.stamp(), "message": {"role": "assistant", "content": [{"type": "text", "text": body}]}},
            {"type": "system", "timestamp": self.stamp(), "content": body},
            {"type": "user", "timestamp": self.stamp(), "message": {"role": "user", "content": [
                {"type": "tool_result", "tool_use_id": "x", "content": body}]}},
        )
        self.assertFalse(self.stop_bg()["review_result"])
        self.assertEqual(self.window()["pending"], 1)
        self.append({"type": "queue-operation", "timestamp": self.stamp(), "operation": "enqueue", "content": body})
        self.assertEqual(self.stop_bg(now=T0 + 31)["review_findings"], 5)

    def test_a_shrunk_transcript_is_not_replayed_from_the_start(self):
        self.start()
        self.launch()
        self.append({"type": "assistant", "message": {"role": "assistant", "content": "x" * 400}})
        self.stop_bg()
        # Compaction rewrote the file: it is now shorter than the stored offset and still holds
        # an old hand-back, which must not be replayed from byte 0.
        self.path.write_text("\n".join(json.dumps(e) for e in self.hand_back(marker(8))) + "\n", encoding="utf-8")
        rec = self.load("s1")
        rec["reviews"][0]["tx_offset"] = self.path.stat().st_size + 500
        self.save("s1", rec)
        self.assertFalse(self.stop_bg(now=T0 + 31)["review_result"])
        self.assertEqual((self.window()["pending"], self.window()["tx_offset"]), (1, self.path.stat().st_size))
        self.append(*self.hand_back(marker(1), launch="tu1"))
        self.assertEqual(self.stop_bg(now=T0 + 32)["review_findings"], 1)

    def test_a_different_transcript_path_continues_from_its_end(self):
        self.start()
        self.launch()
        other = self.tmp / "other.jsonl"
        other.write_text("\n".join(json.dumps(e) for e in self.hand_back(marker(8))) + "\n", encoding="utf-8")
        out = self.stop({"session_id": "s1", "transcript_path": str(other), "last_assistant_message": "ok"})
        self.assertFalse(out["review_result"])
        self.assertEqual(self.window()["tx_offset"], other.stat().st_size)

    def test_a_real_id_the_window_never_launched_retires_nothing(self):
        window = {"fg": ["a"], "bg": ["b"], "pending": 2}
        self.assertFalse(tasks._take_slot(window, "stranger", "bg"))
        self.assertFalse(tasks._take_slot(window, "stranger", "fg"))
        self.assertEqual((window["fg"], window["bg"]), (["a"], ["b"]))
        self.assertTrue(tasks._take_slot(window, "a", "bg"))  # a known id wins whatever the kind
        self.assertEqual((window["fg"], window["bg"]), ([], ["b"]))

    def test_a_missing_or_synthetic_id_falls_back_to_the_oldest_token_of_its_kind(self):
        window = {"fg": ["a", "c"], "bg": ["b", "d"], "pending": 4}
        self.assertTrue(tasks._take_slot(window, None, "fg"))
        self.assertTrue(tasks._take_slot(window, "anon:3", "bg"))
        self.assertTrue(tasks._take_slot(window, "off:120:2", "bg"))
        self.assertEqual((window["fg"], window["bg"]), (["c"], []))
        self.assertFalse(tasks._take_slot(window, "off:9:9", "bg"))

    def test_a_foreground_agent_backgrounded_after_launch_moves_to_bg_and_resolves_from_the_transcript(self):
        self.start()
        spawn = dict(claude_spawn("s1"), tool_use_id="tu1", transcript_path=str(self.path))
        self.open(spawn)
        self.assertEqual((self.window()["fg"], self.window()["bg"]), (["tu1"], []))
        # The input never said run_in_background; the harness ran it in the background anyway.
        ack = dict(claude_return("s1", "Async agent launched"), tool_use_id="tu1")
        ack["tool_response"] = {"isAsync": True, "status": "async_launched"}
        out = self.result(ack)
        self.assertEqual((out["recorded"], out["result"]), (True, False))
        self.assertEqual((self.window()["fg"], self.window()["bg"], self.window()["pending"]), ([], ["tu1"], 1))
        # Stop does not retire it as unread ...
        self.assertFalse(self.stop_bg()["review_result"])
        self.assertEqual(self.window()["unread"], 0)
        # ... and the later transcript hand-back resolves it.
        self.append(*self.hand_back(marker(3)))
        self.assertEqual(self.stop_bg(now=T0 + 40)["review_findings"], 3)

    def test_a_repeated_or_foreign_async_ack_changes_nothing(self):
        self.start()
        self.open(dict(claude_spawn("s1"), tool_use_id="tu1"))
        ack = dict(claude_return("s1", "x"), tool_use_id="tu1", tool_response={"isAsync": True})
        self.assertTrue(self.result(ack)["recorded"])
        self.assertFalse(self.result(ack)["recorded"])  # already in bg
        other = dict(claude_return("s1", "x", agent="Explore"), tool_use_id="zz", tool_response={"isAsync": True})
        self.assertFalse(self.result(other)["recorded"])
        self.assertEqual(self.window()["bg"], ["tu1"])

    def test_the_bytes_read_per_stop_are_capped_and_resumed(self):
        self.start()
        self.launch()
        filler = {"type": "assistant", "message": {"role": "assistant", "content": "y" * 1000}}
        self.append(*[filler] * 30, *self.hand_back(marker(4)))
        original = tasks.BACKGROUND_SCAN_BYTES
        tasks.BACKGROUND_SCAN_BYTES = 8192
        try:
            for step in range(20):
                out = self.stop_bg(now=T0 + 30 + step)
                if out["review_result"]:
                    break
        finally:
            tasks.BACKGROUND_SCAN_BYTES = original
        self.assertEqual(out["review_findings"], 4)

    def test_a_bash_task_notification_echoing_the_marker_is_ignored(self):
        self.start()
        self.launch()
        body = (
            "<task-notification>\n<task-id>b7</task-id>\n<tool-use-id>bash1</tool-use-id>\n<status>completed</status>\n"
            "<summary>{}</summary>\n</task-notification>"
        ).format(marker(0))
        self.append({"type": "queue-operation", "timestamp": self.stamp(), "operation": "enqueue", "content": body})
        self.assertFalse(self.stop_bg()["review_result"])
        self.assertEqual((self.window()["pending"], self.window()["bg"]), (1, ["tu1"]))

    def test_the_marker_in_the_summary_of_a_known_agent_is_not_read(self):
        self.start()
        self.launch()
        body = "<task-notification>\n<task-id>a1</task-id>\n<tool-use-id>tu1</tool-use-id>\n<summary>{}</summary>\n</task-notification>".format(marker(0))
        self.append({"type": "queue-operation", "timestamp": self.stamp(), "operation": "enqueue", "content": body})
        out = self.stop_bg()
        self.assertEqual((out["review_result"], out["review_findings"]), (True, None))

    def test_a_task_id_only_notification_with_a_marker_is_ignored_unless_known(self):
        self.start()
        self.launch()
        body = "<task-notification>\n<task-id>a9</task-id>\n<result>{}</result>\n</task-notification>".format(marker(0))
        entry = {"type": "queue-operation", "timestamp": self.stamp(), "operation": "enqueue", "content": body}
        self.append(entry)
        self.assertFalse(self.stop_bg()["review_result"])
        self.assertEqual(self.window()["bg"], ["tu1"])
        rec = self.load("s1")
        rec["reviews"][0]["bg"] = ["a9"]
        self.save("s1", rec)
        self.append(dict(entry, timestamp=self.stamp(16)))
        self.assertEqual(self.stop_bg(now=T0 + 31)["review_findings"], 0)

    def test_a_notification_naming_nothing_is_dropped(self):
        window = {"opened_at": T0, "tx_offset": 0, "tx_path": str(self.path)}
        body = "<task-notification>\n<result>{}</result>\n</task-notification>".format(marker(1))
        entry = {"type": "queue-operation", "content": body, "timestamp": self.stamp()}
        self.path.write_text(json.dumps(entry) + "\n", encoding="utf-8")
        self.assertEqual(tasks._background_reports(window, str(self.path)), [])

    def test_a_lone_user_notification_is_not_a_hand_back_but_a_mirroring_one_is(self):
        self.start()
        self.launch()
        _, user_entry = self.hand_back(marker(4))
        queue_entry, _ = self.hand_back(marker(4))
        self.append(user_entry)
        self.assertFalse(self.stop_bg()["review_result"])
        self.assertEqual(self.window()["pending"], 1)
        window = {"opened_at": T0, "tx_offset": 0, "tx_path": str(self.path), "queue_ids": ["a1"]}
        self.assertEqual([r["markers"] for r in tasks._background_reports(window, str(self.path))], [[4]])
        # the queue entry itself is the harness form and needs no mirror
        self.append(queue_entry)
        self.assertEqual(self.stop_bg(now=T0 + 31)["review_findings"], 4)

    def test_a_user_notification_that_does_not_open_the_text_is_ignored(self):
        window = {"opened_at": T0, "tx_offset": 0, "tx_path": str(self.path), "queue_ids": ["a1"]}
        body = "please look at this: " + self.notification(marker(4))
        entry = {"type": "user", "message": {"role": "user", "content": body}, "timestamp": self.stamp()}
        self.path.write_text(json.dumps(entry) + "\n", encoding="utf-8")
        self.assertEqual(tasks._background_reports(window, str(self.path)), [])

    def test_a_fenced_marker_in_a_hand_back_is_not_read(self):
        self.start()
        self.launch()
        self.append(*self.hand_back("The format is:\n```\n" + MARK0 + "\n```"))
        out = self.stop_bg()
        self.assertEqual((out["review_result"], out["review_findings"]), (True, None))

    def test_an_oversize_line_without_a_newline_does_not_wedge_the_scan(self):
        self.start()
        self.launch()
        original = tasks.BACKGROUND_SCAN_BYTES
        tasks.BACKGROUND_SCAN_BYTES = 4096
        try:
            with open(self.path, "a", encoding="utf-8") as handle:
                handle.write('{"type":"assistant","message":{"content":"' + "z" * 10000 + '"}}\n')
            self.append(*self.hand_back(marker(6)))
            out = {"review_result": False}
            for step in range(12):
                out = self.stop_bg(now=T0 + 30 + step)
                if out["review_result"]:
                    break
            self.assertEqual(out["review_findings"], 6)
            self.assertEqual(self.window()["tx_offset"], self.path.stat().st_size)
        finally:
            tasks.BACKGROUND_SCAN_BYTES = original

    def test_a_single_line_over_two_mib_is_skipped_at_the_real_cap(self):
        self.start()
        self.launch()
        with open(self.path, "a", encoding="utf-8") as handle:
            handle.write("x" * (tasks.BACKGROUND_SCAN_BYTES + 5000))  # no newline yet: still being written
        self.stop_bg()
        with open(self.path, "a", encoding="utf-8") as handle:
            handle.write("\n")
        self.append(*self.hand_back(marker(1)))
        out = {"review_result": False}
        for step in range(6):
            out = self.stop_bg(now=T0 + 31 + step)
            if out["review_result"]:
                break
        self.assertEqual(out["review_findings"], 1)


class RoundThreeDetectorTest(unittest.TestCase):
    def kind(self, text):
        hit = review_triggers.prompt_trigger(text)
        return hit and hit[0]

    def test_skip_is_not_a_negation(self):
        self.assertEqual(self.kind("skip the tests, review it"), "prompt")
        self.assertEqual(self.kind("skip review"), "prompt")

    def test_qa_inside_a_path_or_identifier_is_not_a_request(self):
        for text in ("edit docs/qa/plan.md", "open the qa_report file", "see .qa/config", "run qa-specialist output", "path a/qa"):
            self.assertIsNone(review_triggers.prompt_trigger(text), text)
        for text in ("please do QA", "QA. now", "run the QA, then merge", "qa please"):
            self.assertEqual(self.kind(text), "prompt", text)

    def test_the_marker_counts_only_as_the_last_line_outside_code(self):
        fence = "```\n" + MARK0 + "\n```"
        self.assertEqual(review_triggers.markers(fence), [])
        self.assertEqual(review_triggers.markers("Use `" + MARK0 + "` at the end.\nThanks"), [])
        self.assertEqual(review_triggers.markers(MARK0 + "\nmore text after"), [])
        self.assertEqual(review_triggers.markers("Explained: " + MARK0), [])
        self.assertEqual(review_triggers.markers("```\ncode\n```\nDone\n\n" + MARK0 + "\n\n"), [0])
        self.assertEqual(review_triggers.markers("text\n```\n" + MARK0), [])  # an unterminated fence swallows it


class RoundThreeResultTest(ReviewCase):
    def test_a_general_purpose_agent_quoting_the_marker_changes_nothing(self):
        self.start()
        self.open(dict(claude_spawn("s1"), tool_use_id="q1"))
        before = self.window()
        for payload in (
            claude_return("s1", marker(0), agent="general-purpose"),
            dict(claude_return("s1", marker(0)), tool_input={"description": "d", "prompt": "p"}),
            opencode_return("s1", marker(0), agent="general-purpose"),
        ):
            self.assertFalse(self.result(dict(payload, tool_use_id="x"))["recorded"])
        self.assertEqual(self.window(), before)
        self.assertEqual(self.window()["result_at"], None)

    def test_a_known_review_agent_still_records(self):
        self.start()
        self.open(dict(claude_spawn("s1"), tool_use_id="q1"))
        self.assertEqual(self.result(dict(claude_return("s1", marker(2)), tool_use_id="q1"))["findings"], 2)


class RoundThreeLateResultTest(ReviewCase):
    def settle_unread(self):
        self.start("c1")
        self.open(codex_spawn("c1"))
        out = self.stop({"session_id": "c1", "last_assistant_message": "done"}, now=T0 + 30)
        self.assertEqual((out["review_result"], out["review_findings"]), (True, None))
        return self.window("c1")

    def test_a_late_wait_with_zero_findings_releases_the_tasks(self):
        self.settle_unread()
        self.assertEqual(self.columns(sid="c1")["A"], "in_review")
        out = self.result(codex_wait("c1", marker(0)), now=T0 + 60)
        self.assertEqual((out["recorded"], out["result"], out["findings"], out["resolved"]), (True, True, 0, True))
        self.assertEqual(self.window("c1")["resolution"], "passed")
        self.assertEqual(self.columns(sid="c1")["A"], "in_progress")
        self.assertEqual(self.columns(sid="c1")["B"], "done")

    def test_a_late_wait_with_findings_holds_the_tasks_with_them(self):
        self.settle_unread()
        out = self.result(codex_wait("c1", marker(3)), now=T0 + 60)
        self.assertEqual((out["result"], out["findings"], out["resolved"]), (True, 3, False))
        task = [t for t in self.session(sid="c1")["tasks"] if t["content"] == "A"][0]
        self.assertEqual((task["column"], task["review"]["state"], task["review"]["findings"]), ("in_review", "findings", 3))
        self.assertIsNotNone(self.window("c1")["fix_after"])

    def test_a_late_result_is_bounded_by_the_expiry_age_and_by_the_latest_window(self):
        self.settle_unread()
        old = self.result(codex_wait("c1", marker(0)), now=T0 + 30 + tasks.PENDING_MAX_AGE + 1)
        self.assertFalse(old["recorded"])
        self.assertIsNone(self.window("c1")["resolved_at"])
        # A second unread window: only the latest one takes the late report.
        rec = self.load("c1")
        second = json.loads(json.dumps(rec["reviews"][0]))
        second["id"] = "r2"
        second["result_at"] = T0 + 50
        rec["reviews"].append(second)
        self.save("c1", rec)
        out = self.result(codex_wait("c1", marker(0)), now=T0 + 60)
        self.assertEqual(out["window"], "r2")
        self.assertEqual(self.window("c1", 1)["resolution"], "passed")
        self.assertEqual(self.window("c1", 0)["resolution"], "fixed")  # the re-review rule

    def test_a_late_wait_never_reopens_a_resolved_window(self):
        self.start("c1")
        self.open(codex_spawn("c1"))
        self.result(codex_wait("c1", marker(0)), now=T0 + 20)
        self.assertEqual(self.window("c1")["resolution"], "passed")
        self.assertFalse(self.result(dict(codex_wait("c1", marker(4)), tool_use_id="u2"), now=T0 + 25)["recorded"])


class RoundThreeStateTest(ReviewCase):
    def test_a_task_in_review_never_shows_passed(self):
        self.start()
        self.open(prompt("s1", "/devteam:review"))
        rec = self.load("s1")
        rec["reviews"][0].update(result_at=T0 + 20, findings=0, resolved_at=None, resolution=None, pending=0, scan=False)
        self.save("s1", rec)
        for task in self.session()["tasks"]:
            self.assertNotEqual(task["column"], "in_review")
        self.assertNotEqual(tasks._window_state(rec["reviews"][0]), "passed")

    def test_every_state_the_cli_emits_is_pending_findings_or_unread(self):
        self.start()
        seen = set()
        self.open(dict(claude_spawn("s1"), tool_use_id="a"))
        seen |= {t["review"]["state"] for t in self.session()["tasks"] if t["review"]}
        self.result(dict(claude_return("s1", marker(2)), tool_use_id="a"))
        seen |= {t["review"]["state"] for t in self.session()["tasks"] if t["review"]}
        self.open(prompt("s1", "/review"), now=T0 + 50)
        self.stop({"session_id": "s1", "last_assistant_message": "no marker"}, now=T0 + 60)
        seen |= {t["review"]["state"] for t in self.session(now=T0 + 70)["tasks"] if t["review"]}
        self.assertTrue(seen)
        self.assertLessEqual(seen, {"pending", "findings", "unread"})



class RoundThreeStopOutcomesTest(ReviewCase):
    def two_windows(self):
        self.start()
        self.open(prompt("s1", "/devteam:review"))
        rec = self.load("s1")
        second = json.loads(json.dumps(rec["reviews"][0]))
        second["id"] = "r2"
        rec["reviews"].append(second)
        self.save("s1", rec)

    def test_a_stop_that_closes_several_windows_reports_each(self):
        self.two_windows()
        out = self.stop({"session_id": "s1", "last_assistant_message": marker(2)})
        self.assertEqual(
            out["review_results"], [{"window": "r1", "findings": 2}, {"window": "r2", "findings": 2}]
        )
        self.assertEqual((out["review_window"], out["review_findings"]), ("r2", 2))

    def test_became_all_done_is_computed_after_every_outcome(self):
        self.two_windows()
        self.todos("s1", todo("A", "completed"), todo("B", "completed"), now=T0 + 15)
        out = self.stop({"session_id": "s1", "last_assistant_message": marker(0)})
        self.assertEqual([r["findings"] for r in out["review_results"]], [0, 0])
        self.assertTrue(out["became_all_done"])

    def test_no_window_closed_leaves_review_results_empty(self):
        self.start()
        out = self.stop({"session_id": "s1"})
        self.assertEqual((out["review_results"], out["review_result"]), ([], False))




class RoundThreePluginTest(tt.BoardCase):
    def text(self):
        return (REPO_ROOT / "opencode" / "plugin" / "dev-team-agents.ts").read_text(encoding="utf-8")

    def test_call_ids_are_forwarded_and_the_subagent_type_is_remembered_by_call_id(self):
        text = self.text()
        self.assertEqual(text.count("tool_use_id"), 2)
        self.assertIn("subagentByCall", text)
        self.assertIn("SUBAGENT_CALLS_KEPT", text)
        self.assertIn("args.subagent_type = subagentByCall.get(callID)", text)

    def test_session_id_leads_the_payloads_the_bash_gates_scan(self):
        text = self.text()
        self.assertIn("sessionID: input.sessionID,\n        tool: input.tool,", text)

    def test_task_board_hooks_outlast_the_record_lock(self):
        text = self.text()
        match = re.search(r"TASK_BOARD_HOOK_TIMEOUT_MS = (\d+)", text)
        self.assertGreater(int(match.group(1)) / 1000.0, tasks.LOCK_TIMEOUT)
        self.assertEqual(tasks.LOCK_TIMEOUT, 10.0)
        for script in ("pre-tool-use.sh", "post-tool-use.sh", "user-prompt-submit.sh", "stop.sh"):
            self.assertRegex(text, r"{}`[^)]*TASK_BOARD_HOOK_TIMEOUT_MS".format(re.escape(script)))

    def test_a_command_named_by_opencode_is_rebuilt_as_a_slash_command(self):
        text = self.text()
        self.assertIn("named.command", text)
        self.assertIn("docs/providers.md", text)
        self.assertIn("opencode", (REPO_ROOT / "docs" / "providers.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()


class HookStdinTimeoutTest(unittest.TestCase):
    """A hook-only command must not wait forever on a stdin nobody closes."""

    def test_a_hook_only_command_returns_when_stdin_stays_open_and_silent(self):
        import subprocess
        import sys
        import time as _time
        from pathlib import Path

        cli = Path(__file__).resolve().parent.parent / "scripts" / "cli" / "devteam"
        for command in (["tasks", "record"], ["tasks", "review-open"], ["tasks", "review-result"]):
            started = _time.monotonic()
            proc = subprocess.Popen(
                [sys.executable, str(cli), *command, "--json"],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            )
            try:
                proc.wait(timeout=20)
            finally:
                if proc.poll() is None:
                    proc.kill()
                proc.stdin.close()
                proc.stdout.close()
                proc.stderr.close()
            self.assertIsNotNone(proc.returncode, command)
            self.assertLess(_time.monotonic() - started, 15, command)
