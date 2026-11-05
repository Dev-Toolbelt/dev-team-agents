"""`devteam tasks graph` — the board joined with the execution trace for the canvas view.

Pins the join on the spawn id on every provider, nesting, the cycle guard, the no-trace fallback,
the caps, persona detection, the `--since` filter, the `last_output` read-back, a corrupt trace,
deterministic order, the emitted keys against the app's pin, and that the board's own `tasks list`
shape is untouched.
"""

import json
import os
import unittest
from unittest import mock

from devteam_support import REPO_ROOT

from devteam import compat, graph, jsonio, providers, tasks, trace

import test_execution_trace as te
from test_tasks import T0, BoardCase, todo, todo_write

AGENT = "backend-developer"


def _nest(provider, session, call, parent_call):
    """A nested spawn ``call`` made by the agent ``parent_call`` started, as each provider sends it."""
    parent_agent = {"claude": "ag-", "codex": "ag-", "opencode": "ses-"}[provider] + parent_call
    spawn, rest = te.CYCLES[provider](session, AGENT, call)
    return [te.NESTED[provider](p, parent_agent, session) for p in [spawn] + rest]


#: One fixture per provider in `providers.ALL_PROVIDERS`: the payloads of one top-level agent cycle
#: and one agent nested under it. A provider added without a case fails
#: `test_every_provider_has_a_graph_fixture` instead of shipping a canvas that misses its agents.
FIXTURES = {
    "claude": lambda session: (te.claude_cycle(session, AGENT, "c1"), _nest("claude", session, "c2", "c1")),
    "codex": lambda session: (te.codex_cycle(session, AGENT, "c1"), _nest("codex", session, "c2", "c1")),
    "opencode": lambda session: (te.opencode_cycle(session, AGENT, "c1"), _nest("opencode", session, "c2", "c1")),
}


class GraphCase(BoardCase):
    def feed(self, payloads, at=T0, board=True, traced=True):
        for offset, payload in enumerate(payloads):
            if board:
                tasks.record(self.root, payload, now=at + offset * 10)
            if traced:
                trace.capture(self.root, payload, now=at + offset * 10)

    def cycle(self, provider, session, at=T0, **kwargs):
        (spawn, rest), nested = FIXTURES[provider](session)
        self.feed([spawn] + rest, at=at, **kwargs)
        return nested

    def write_trace(self, session, spans, provider="claude", updated_at=T0):
        path = trace.trace_path(self.root, self.project_id, session)
        path.parent.mkdir(parents=True, exist_ok=True)
        jsonio.write_json_atomic(path, {
            "schema": 1, "session_id": session, "provider": provider, "created_at": T0,
            "updated_at": updated_at, "spans": spans,
        })

    def graph(self, now=T0 + 100, **kwargs):
        return graph.build(self.root, self.project_id, now=now, **kwargs)

    @staticmethod
    def span(ident, owner="main", agent_id=None, **extra):
        span = {"id": ident, "agent": AGENT, "kind": "agent", "agent_id": agent_id or "ag-" + ident,
                "owner": owner, "status": "completed", "started_at": T0, "ended_at": T0 + 5, "turn_at": T0}
        span.update(extra)
        return span

    @staticmethod
    def nodes(result, kind=None):
        return {n["id"]: n for n in result["nodes"] if kind is None or n["kind"] == kind}

    @staticmethod
    def edges(result):
        return {(e["from"], e["to"]) for e in result["edges"]}


class ProviderParityTest(GraphCase):
    def test_every_provider_has_a_graph_fixture(self):
        self.assertEqual(set(FIXTURES), set(providers.ALL_PROVIDERS))

    def test_a_board_agent_joins_its_span_on_every_provider(self):
        for provider in providers.ALL_PROVIDERS:
            with self.subTest(provider=provider):
                session = "j-" + provider
                self.cycle(provider, session)
                result = self.graph()
                node = self.nodes(result)["span:{}:c1".format(session)]
                self.assertEqual((node["kind"], node["agent"], node["status"]), ("agent", AGENT, "completed"))
                self.assertEqual(node["task_key"], "t1")  # from the board
                self.assertTrue(node["description"].startswith(AGENT))
                self.assertEqual(node["group"], "turn:{}:none".format(session))  # from the trace
                self.assertIn(("main:" + session, node["id"]), self.edges(result))
                group = {g["id"]: g for g in result["groups"]}["session:" + session]
                self.assertEqual(group["provider"], provider)
                self.assertNotIn("no_trace:" + session, result["notices"])

    def test_a_nested_agent_hangs_from_its_parent_span_on_every_provider(self):
        """[spec:canvas-view#S2]"""
        for provider in providers.ALL_PROVIDERS:
            with self.subTest(provider=provider):
                session = "n-" + provider
                nested = self.cycle(provider, session)
                self.feed(nested, at=T0 + 50)
                result = self.graph()
                spans = self.nodes(result)
                parent, child = "span:{}:c1".format(session), "span:{}:c2".format(session)
                self.assertIn(child, spans)
                self.assertIn((parent, child), self.edges(result))
                self.assertNotIn(("main:" + session, child), self.edges(result))
                # A child session (opencode) or thread never shows up as a session of its own.
                sessions = [g["id"] for g in result["groups"] if g["kind"] == "session"]
                self.assertEqual(len([s for s in sessions if s == "session:" + session]), 1)
                self.assertEqual(sum(1 for n in result["nodes"] if n["id"] == child), 1)


class ShapeTest(GraphCase):
    NODE_KEYS = {
        "id", "kind", "group", "label", "agent", "description", "persona", "persona_source", "status",
        "model", "started_at", "ended_at", "duration_s", "tokens", "subtree_tokens", "usage_complete",
        "findings", "background", "last_output", "task_key", "worktree", "pr", "todos",
        "session_id", "record_id", "spawn_id",
    }
    GROUP_KEYS = {
        "id", "kind", "parent", "label", "provider", "status", "branch", "command", "at", "started_at",
        "ended_at", "prs", "tokens", "usage_complete", "session_id",
    }

    def test_the_document_carries_the_schema_1_keys(self):
        self.cycle("claude", "s1")
        result = self.graph()
        self.assertEqual(set(result), {"schema", "project_id", "as_of", "truncated", "notices", "groups", "nodes", "edges"})
        self.assertEqual((result["schema"], result["project_id"], result["as_of"]), (1, self.project_id, T0 + 100))
        for node in result["nodes"]:
            self.assertEqual(set(node), self.NODE_KEYS)
        for group in result["groups"]:
            self.assertEqual(set(group), self.GROUP_KEYS)
        for edge in result["edges"]:
            self.assertEqual(set(edge), {"id", "from", "to", "kind"})
            self.assertEqual(edge["id"], "e:{}>{}".format(edge["from"], edge["to"]))

    def test_the_board_list_shape_is_untouched(self):
        self.cycle("claude", "s1")
        (project,) = tasks.collect(now=T0 + 100)["projects"]
        for task in project["sessions"][0]["tasks"]:
            self.assertNotIn("_spawn_id", task)
            self.assertNotIn("id", task)

    def test_the_order_is_deterministic(self):
        """[spec:canvas-view#S11]"""
        self.cycle("claude", "b-sess", at=T0 + 20)
        self.cycle("codex", "a-sess", at=T0)
        first, second = self.graph(), self.graph()
        self.assertEqual(json.dumps(first), json.dumps(second))
        keys = [(n["started_at"] or 0, n["id"]) for n in first["nodes"]]
        self.assertEqual(keys, sorted(keys))
        self.assertEqual([e["id"] for e in first["edges"]], sorted(e["id"] for e in first["edges"]))
        # Untimed turn frames sort at their session's start, never ahead of every session.
        ids = [g["id"] for g in first["groups"]]
        self.assertLess(ids.index("session:a-sess"), ids.index("turn:a-sess:none"))

    def test_todos_land_on_the_span_whose_agent_owns_them_and_on_main(self):
        self.cycle("claude", "s1")
        tasks.record(self.root, todo_write("s1", [todo("sub step", "in_progress")], agent_id="ag-c1"), now=T0 + 30)
        tasks.record(self.root, todo_write("s1", [todo("main step")]), now=T0 + 31)
        nodes = self.nodes(self.graph())
        self.assertEqual([t["content"] for t in nodes["span:s1:c1"]["todos"]], ["sub step"])
        self.assertEqual(nodes["span:s1:c1"]["todos"][0]["status"], "in_progress")
        self.assertEqual([t["content"] for t in nodes["main:s1"]["todos"]], ["main step"])


class TraceShapesTest(GraphCase):
    def test_an_owner_cycle_draws_every_span_once(self):
        self.write_trace("s1", [
            self.span("a", owner="ag-b"), self.span("b", owner="ag-a"), self.span("c", owner="ag-a"),
        ])
        result = self.graph()
        spans = self.nodes(result, "agent")
        self.assertEqual(set(spans), {"span:s1:a", "span:s1:b", "span:s1:c"})
        self.assertEqual(len(result["nodes"]), 4)  # main + three spans, none twice
        self.assertIn(("span:s1:a", "span:s1:c"), self.edges(result))

    def test_review_and_builtin_spans_are_nodes_with_no_board_task(self):
        self.write_trace("s1", [self.span("r1", agent="code-reviewer", kind="review", findings=2),
                                self.span("b1", agent="Explore", kind="builtin")])
        spans = self.nodes(self.graph())
        self.assertEqual((spans["span:s1:r1"]["kind"], spans["span:s1:r1"]["findings"]), ("review", 2))
        self.assertEqual(spans["span:s1:b1"]["kind"], "builtin")
        self.assertIsNone(spans["span:s1:r1"]["task_key"])

    def test_a_cancelled_span_shows_interrupted(self):
        self.write_trace("s1", [self.span("a", status="cancelled")])
        self.assertEqual(self.nodes(self.graph())["span:s1:a"]["status"], "interrupted")

    def test_last_output_is_read_back_through_the_trace_rule(self):
        """[spec:canvas-view#S13]"""
        self.write_trace("s1", [
            self.span("ok", last_output="Implemented the endpoint and its tests"),
            self.span("multi", last_output="line one\nline two"),
            self.span("long", last_output="x" * 141),
            self.span("number", last_output=42),
            self.span("secret", last_output="token=ghp_abcdefghijklmnopqrstuvwxyz0123456789"),  # gitleaks:allow
            self.span("hidden", last_output="ok\u200b\U000e0041done"),
            self.span("none"),
        ])
        nodes = self.nodes(self.graph())
        self.assertEqual(nodes["span:s1:ok"]["last_output"], "Implemented the endpoint and its tests")
        self.assertEqual(nodes["span:s1:multi"]["last_output"], "line one line two")  # one line
        self.assertLessEqual(len(nodes["span:s1:long"]["last_output"]), trace.LAST_OUTPUT_MAX)
        self.assertEqual(nodes["span:s1:hidden"]["last_output"], "okdone")
        for ident in ("number", "none"):
            self.assertIsNone(nodes["span:s1:" + ident]["last_output"], ident)
        self.assertNotIn("ghp_abcdefghijklmnopqrstuvwxyz0123456789", nodes["span:s1:secret"]["last_output"])
        self.assertFalse(hasattr(graph, "LAST_OUTPUT_MAX"))  # one cap, the trace's

    def test_a_corrupt_trace_falls_back_to_the_board_with_a_notice(self):
        self.cycle("claude", "s1", traced=False)
        self.write_trace("s1", [self.span("c1", started_at="not a time", ended_at=None)])
        result = self.graph()
        self.assertIn("bad_trace:s1", result["notices"])
        self.assertNotIn("no_trace:s1", result["notices"])
        (node,) = [n for n in result["nodes"] if n["kind"] != "main"]
        self.assertEqual((node["id"], node["group"]), ("span:s1:c1", "session:s1"))
        self.assertIn(("main:s1", "span:s1:c1"), self.edges(result))

    def test_clean_deletes_invisible_characters_before_redaction(self):
        text = graph._clean("token=ghp_abcdefghij\u200bklmnopqrstuvwxyz0123456789 done", 100)  # gitleaks:allow
        self.assertNotIn("klmnopqrstuvwxyz", text)
        self.assertEqual(graph._clean("a\u200bb\U000e0041c\ufe0fd", 100), "abcd")
        self.assertEqual(graph._clean("two\t words\n", 100), "two words")

    def test_a_crafted_span_id_is_never_drawn(self):
        self.write_trace("s1", [self.span("$(id)"), self.span("ok")])
        self.assertEqual(set(self.nodes(self.graph(), "agent")), {"span:s1:ok"})


class FallbackTest(GraphCase):
    def test_a_session_with_no_trace_shows_its_board_agents_flat_with_a_notice(self):
        """[spec:canvas-view#S3]"""
        for provider in providers.ALL_PROVIDERS:
            with self.subTest(provider=provider):
                session = "nt-" + provider
                self.cycle(provider, session, traced=False)
                result = self.graph()
                self.assertIn("no_trace:" + session, result["notices"])
                (node,) = [n for n in result["nodes"] if n["group"] == "session:" + session and n["kind"] != "main"]
                self.assertEqual(node["id"], "span:{}:c1".format(session))
                self.assertEqual((node["model"], node["tokens"], node["usage_complete"]), (None, 0, False))
                self.assertEqual(node["status"], "completed")
                self.assertIn(("main:" + session, node["id"]), self.edges(result))
                self.assertFalse([g for g in result["groups"] if g["parent"] == "session:" + session])


    def test_a_board_task_with_no_spawn_id_is_named_by_its_record(self):
        spawn, _ = te.claude_cycle("s1", AGENT, "c1")
        tasks.record(self.root, spawn, now=T0)
        path = tasks.record_path(self.root, self.project_id, "s1")
        data = json.loads(path.read_text(encoding="utf-8"))
        for task in data["tasks"]:
            task["id"] = None
        jsonio.write_json_atomic(path, data)
        ids = set(self.nodes(self.graph(), "agent"))
        self.assertEqual(ids, {"span:s1:s1:t1"})


class IdentityTest(GraphCase):
    """Every node says which session, board record and spawn it stands for, so a link or a future
    node action never parses an id string (ADR-0063 § 7)."""

    def test_a_joined_node_carries_its_session_record_and_spawn_on_every_provider(self):
        for provider in providers.ALL_PROVIDERS:
            with self.subTest(provider=provider):
                session = "id-" + provider
                self.cycle(provider, session)
                result = self.graph()
                node = self.nodes(result)["span:{}:c1".format(session)]
                self.assertEqual((node["session_id"], node["record_id"], node["spawn_id"]), (session, session, "c1"))
                main = self.nodes(result)["main:" + session]
                self.assertEqual((main["session_id"], main["record_id"], main["spawn_id"]), (session, session, None))
                for group in result["groups"]:
                    if group["id"].startswith(("session:" + session, "turn:" + session + ":")):
                        self.assertEqual(group["session_id"], session)

    def test_a_child_session_task_names_its_own_record_not_the_top_session(self):
        """[spec:canvas-view#S6]"""
        spawn, rest = te.claude_cycle("child", AGENT, "c9")
        for offset, payload in enumerate([spawn] + rest):
            tasks.record(self.root, payload, now=T0 + offset)
        path = trace.aliases_path(self.root, self.project_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        jsonio.write_json_atomic(path, {"aliases": {"child": "top"}})
        self.write_trace("top", [self.span("c9")])
        node = self.nodes(self.graph())["span:top:c9"]
        self.assertEqual((node["session_id"], node["record_id"], node["task_key"]), ("top", "child", "t1"))

    def test_an_id_less_board_task_has_no_spawn_id(self):
        spawn, _ = te.claude_cycle("s1", AGENT, "c1")
        tasks.record(self.root, spawn, now=T0)
        path = tasks.record_path(self.root, self.project_id, "s1")
        data = json.loads(path.read_text(encoding="utf-8"))
        for task in data["tasks"]:
            task["id"] = None
        jsonio.write_json_atomic(path, data)
        node = self.nodes(self.graph(), "agent")["span:s1:s1:t1"]
        self.assertEqual((node["session_id"], node["record_id"], node["spawn_id"]), ("s1", "s1", None))

    def test_the_main_node_of_an_idle_session_is_idle_not_unknown(self):
        self.cycle("claude", "s1")
        path = tasks.record_path(self.root, self.project_id, "s1")
        data = json.loads(path.read_text(encoding="utf-8"))
        data["idle_at"] = T0 + 90
        jsonio.write_json_atomic(path, data)
        result = self.graph()
        group = {g["id"]: g for g in result["groups"]}["session:s1"]
        self.assertEqual(group["status"], "idle")
        self.assertEqual(self.nodes(result)["main:s1"]["status"], "idle")


class CapsTest(GraphCase):
    def test_spans_past_max_spans_are_cut_and_truncated_is_set(self):
        self.addCleanup(setattr, trace, "MAX_SPANS", trace.MAX_SPANS)
        trace.MAX_SPANS = 2
        self.write_trace("s1", [self.span("a"), self.span("b"), self.span("c")])
        result = self.graph()
        self.assertTrue(result["truncated"])
        self.assertEqual(len(self.nodes(result, "agent")), 2)

    def test_a_span_cut_by_max_spans_is_not_drawn_again_flat_under_main(self):
        self.addCleanup(setattr, trace, "MAX_SPANS", trace.MAX_SPANS)
        for n, call in enumerate(("c1", "c2")):
            spawn, rest = te.claude_cycle("s1", AGENT, call)
            self.feed([spawn] + rest, at=T0 + n * 100)
        trace.MAX_SPANS = 1
        result = self.graph(now=T0 + 300)
        self.assertTrue(result["truncated"])
        agents = self.nodes(result, "agent")
        self.assertEqual(len(agents), 1)
        self.assertNotIn("no_trace:s1", result["notices"])

    def test_board_fallback_past_max_tasks_is_cut(self):
        self.addCleanup(setattr, tasks, "MAX_TASKS", tasks.MAX_TASKS)
        for n in range(3):
            spawn, _ = te.claude_cycle("s1", AGENT, "c{}".format(n))
            tasks.record(self.root, spawn, now=T0 + n)
        tasks.MAX_TASKS = 2
        result = self.graph()
        self.assertTrue(result["truncated"])
        self.assertEqual(len(self.nodes(result, "agent")), 2)

    def test_an_uncapped_graph_is_not_truncated(self):
        self.cycle("claude", "s1")
        self.assertFalse(self.graph()["truncated"])


class PersonaTest(GraphCase):
    def test_an_orchestrate_turn_makes_main_the_orchestrator(self):
        self.write_trace("s1", [self.span("a", command="orchestrate")])
        result = self.graph()
        main = self.nodes(result)["main:s1"]
        self.assertEqual((main["persona"], main["persona_source"], main["label"]),
                         ("orchestrator", "command", "Orchestrator"))
        turn = {g["id"]: g for g in result["groups"]}["turn:s1:{}".format(T0)]
        self.assertEqual((turn["command"], turn["label"], turn["at"]), ("orchestrate", "/devteam:orchestrate", T0))

    def test_any_other_command_keeps_the_main_session(self):
        self.write_trace("s1", [self.span("a", command="sprint")])
        main = self.nodes(self.graph())["main:s1"]
        self.assertEqual((main["persona"], main["persona_source"], main["label"]), (None, None, "Main session"))


class SinceTest(GraphCase):
    def test_ended_sessions_idle_before_since_are_omitted(self):
        self.write_trace("old", [self.span("a")], updated_at=T0)
        self.write_trace("new", [self.span("b")], updated_at=T0 + 5000)
        now = T0 + 5000 + tasks.DEFAULT_ENDED_AFTER + 1  # both ended
        sessions = {g["id"] for g in self.graph(now=now, since=T0 + 1000)["groups"] if g["kind"] == "session"}
        self.assertEqual(sessions, {"session:new"})

    def test_an_ended_trace_outside_the_window_is_never_loaded(self):
        self.write_trace("old", [self.span("a")], updated_at=T0)
        self.write_trace("new", [self.span("b")], updated_at=T0 + 5000)
        old = trace.trace_path(self.root, self.project_id, "old")
        os.utime(str(old), (T0, T0))
        now = T0 + 5000 + tasks.DEFAULT_ENDED_AFTER + 1
        with mock.patch.object(trace, "load", wraps=trace.load) as load:
            result = self.graph(now=now, since=T0 + 1000)
        self.assertNotIn(old, [call.args[0] for call in load.call_args_list])
        self.assertEqual({g["id"] for g in result["groups"] if g["kind"] == "session"}, {"session:new"})

    def test_an_open_session_stays_whatever_since_says(self):
        self.cycle("claude", "live")
        sessions = {g["id"] for g in self.graph(since=T0 + 1000)["groups"] if g["kind"] == "session"}
        self.assertEqual(sessions, {"session:live"})


class CleanLineTest(unittest.TestCase):
    """`tasks.clean_line` is the one rule a short excerpt goes through (trace `last_output`, canvas text)."""

    def test_it_collapses_deletes_invisible_redacts_and_caps(self):
        self.assertIsNone(tasks.clean_line(None, 10))
        self.assertIsNone(tasks.clean_line(" \n\u200b ", 10))
        self.assertEqual(tasks.clean_line("a\n  b\tc", 50), "a b c")
        self.assertEqual(tasks.clean_line("ok\u200b\U000e0041done", 50), "okdone")
        self.assertEqual(tasks.clean_line("abcdefghij", 5), "abcd\u2026")
        hidden = "ghp_" + "\u200b".join(["abcdefghijklmnopqrst", "uvwxyz0123456789ABCD"])  # gitleaks:allow
        self.assertNotIn("abcdefghijklmnopqrst", tasks.clean_line(hidden, 140))

    def test_the_trace_excerpt_and_the_graph_share_it(self):
        self.assertEqual(graph._clean("x\u200by  z", 10), tasks.clean_line("x\u200by  z", 10))


class CliTest(GraphCase):
    def test_tasks_graph_json(self):
        self.cycle("claude", "s1")
        code, out, err = self.run_cli("--json", "tasks", "graph", "--project", self.project_id)
        self.assertEqual(code, 0, err)
        body = json.loads(out)
        self.assertTrue(body["ok"])
        self.assertEqual(body["schema"], 1)
        self.assertIn("span:s1:c1", {n["id"] for n in body["nodes"]})

    def test_since_rejects_nan_inf_and_negative(self):
        for bad in ("nan", "inf", "-inf", "-1", "soon"):
            with self.subTest(since=bad):
                code, _, err = self.run_cli("--json", "tasks", "graph", "--project", self.project_id, "--since", bad)
                self.assertEqual(code, 2, err)
                self.assertNotIn("Traceback", err)

    def test_an_unknown_project_fails(self):
        code, out, _ = self.run_cli("--json", "tasks", "graph", "--project", "nope")
        self.assertNotEqual(code, 0)
        self.assertFalse(json.loads(out)["ok"])

    def test_it_is_read_only(self):
        self.assertIn(("tasks", "graph"), compat.READ_ONLY)


GRAPH_KEYS = REPO_ROOT / "app" / "test" / "fixtures" / "graph-keys.json"


class GraphJsonKeysPinTest(GraphCase):
    """Pins every key the graph JSON carries, so the app side (``app/test/graphContract.test.ts``)
    has to account for a new one, as ``BoardJsonKeysPinTest`` does for the board."""

    def emitted(self):
        self.cycle("claude", "s1")
        tasks.record(self.root, todo_write("s1", [todo("sub step")], agent_id="ag-c1"), now=T0 + 30)
        result = self.graph()
        found = {"graph": set(result), "group": set(), "node": set(), "edge": set(), "todo": set()}
        for name, items in (("group", "groups"), ("node", "nodes"), ("edge", "edges")):
            for item in result[items]:
                found[name] |= set(item)
        for node in result["nodes"]:
            for item in node["todos"]:
                found["todo"] |= set(item)
        return {name: sorted(keys) for name, keys in found.items()}

    def test_the_keys_the_graph_emits_match_the_committed_contract(self):
        committed = json.loads(GRAPH_KEYS.read_text(encoding="utf-8"))
        self.assertEqual(
            self.emitted(), committed,
            "the graph JSON keys changed: update app/test/fixtures/graph-keys.json, then make "
            "app/test/graphContract.test.ts pass (parse the new key in app/src/cli/operations.ts)",
        )

    def test_the_scenario_reaches_every_kind(self):
        emitted = self.emitted()
        for name in ("group", "node", "edge", "todo"):
            self.assertTrue(emitted[name], name)


if __name__ == "__main__":
    unittest.main()
