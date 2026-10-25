"""History mining (ADR-0049, docs/specs/history-mining.md): transcript readers, clustering,
review threads, and the read-only `devteam mine` commands. No network beyond a loopback fake."""

import json
import os
import re
import sqlite3
import subprocess
import unittest
import urllib.parse
from pathlib import Path
from unittest import mock

from devteam_support import StoreTestCase
from test_integrations import IntegrationTestCase

from devteam import integrations, mining, providers
from devteam.integrations import github as github_adapter
from devteam.integrations import http as ihttp

CORRECTION = "don't spawn a worktree for this task please"
D1, D2, D3 = "2026-03-10T12:00:00Z", "2026-03-12T12:00:00Z", "2026-03-14T12:00:00Z"
SECRET = "ghp_abcdefghijklmnopqrstuvwxyz0123456789"


def _jsonl(path, objs):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(o) for o in objs) + "\n", encoding="utf-8")


def _epoch_ms(iso):
    import datetime
    return int(datetime.datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp() * 1000)


class Fixtures:
    """One writer per provider: `write(provider, root, home, messages)` where messages are
    (iso, text, kind) and kind is 'typed' or a noise kind the reader must ignore."""

    @staticmethod
    def claude(root, home, msgs):
        slug = re.sub(r"[^A-Za-z0-9]", "-", str(root))
        objs = []
        for iso, text, kind in msgs:
            o = {"type": "user", "timestamp": iso, "cwd": str(root), "message": {"content": text}}
            if kind == "tool_result":
                o["message"] = {"content": [{"type": "tool_result", "content": text}]}
            elif kind == "sidechain":
                o["isSidechain"] = True
            elif kind == "headless":
                o["entrypoint"] = "sdk-cli"
            objs.append(o)
        _jsonl(home / ".claude" / "projects" / slug / "s1.jsonl", objs)

    @staticmethod
    def codex(root, home, msgs, cwd=None, originator="codex_cli_rs"):
        objs = [{"type": "session_meta", "payload": {"cwd": cwd or str(root), "originator": originator}}]
        for iso, text, kind in msgs:
            role = "assistant" if kind == "tool_result" else "user"
            btype = "output_text" if role == "assistant" else "input_text"
            objs.append({"type": "response_item", "timestamp": iso,
                         "payload": {"type": "message", "role": role, "content": [{"type": btype, "text": text}]}})
        _jsonl(Path(os.environ["CODEX_HOME"]) / "sessions" / "2026" / "03" / "rollout-1.jsonl", objs)

    @staticmethod
    def opencode(root, home, msgs, parent=None):
        base = Path(os.environ["XDG_DATA_HOME"]) / "opencode"
        base.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(base / "opencode.db"))
        conn.executescript(
            "CREATE TABLE session(id TEXT, directory TEXT, parent_id TEXT, time_updated INT);"
            "CREATE TABLE message(id TEXT, session_id TEXT, time_created INT, data TEXT);"
            "CREATE TABLE part(id TEXT, message_id TEXT, time_created INT, data TEXT);")
        conn.execute("INSERT INTO session VALUES('ses_1',?,?,1)", (str(root), parent))
        for i, (iso, text, kind) in enumerate(msgs):
            ms = _epoch_ms(iso)
            role = "assistant" if kind == "tool_result" else "user"
            conn.execute("INSERT INTO message VALUES(?,?,?,?)", ("m%d" % i, "ses_1", ms, json.dumps({"role": role})))
            part = {"type": "text", "text": text}
            if kind == "synthetic":
                part["synthetic"] = True
            conn.execute("INSERT INTO part VALUES(?,?,?,?)", ("p%d" % i, "m%d" % i, ms, json.dumps(part)))
        conn.commit()
        conn.close()


#: One writer per provider in ALL_PROVIDERS; the guard below fails when a provider is added without one.
FIXTURES = {"claude": Fixtures.claude, "codex": Fixtures.codex, "opencode": Fixtures.opencode}


class MiningCase(StoreTestCase):
    def setUp(self):
        super().setUp()
        self.fakehome = self.tmp / "home"
        self.fakehome.mkdir()
        self._env = {k: os.environ.get(k) for k in ("HOME", "CODEX_HOME", "XDG_DATA_HOME")}
        os.environ["HOME"] = str(self.fakehome)
        os.environ["CODEX_HOME"] = str(self.fakehome / "codexhome")
        os.environ["XDG_DATA_HOME"] = str(self.fakehome / "xdg")
        self.addCleanup(self._restore)
        self.root = self.new_project().resolve()

    def _restore(self):
        for k, v in self._env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def write(self, provider, msgs, **kw):
        FIXTURES[provider](self.root, self.fakehome, msgs, **kw)

    def candidates(self):
        return mining.sessions(self.root, home=self.fakehome)


class ProviderCoverage(unittest.TestCase):
    def test_every_provider_has_fixture_and_reader(self):  # [spec:history-mining#S4] [spec:history-mining#S5] [spec:history-mining#S6]
        self.assertEqual(set(FIXTURES), set(providers.ALL_PROVIDERS))
        self.assertEqual(set(mining.READERS), set(providers.ALL_PROVIDERS))


class SessionsPerProvider(MiningCase):
    def test_repeated_correction_on_two_days_is_a_candidate(self):  # [spec:history-mining#S1] [spec:history-mining#S4] [spec:history-mining#S5] [spec:history-mining#S6]
        for provider in providers.ALL_PROVIDERS:
            with self.subTest(provider=provider):
                self._reset()
                self.write(provider, [(D1, CORRECTION, "typed"), (D2, CORRECTION, "typed")])
                result = self.candidates()
                self.assertEqual(result["messages_by_provider"][provider], 2)
                self.assertEqual(len(result["candidates"]), 1)
                c = result["candidates"][0]
                self.assertEqual(c["text"], CORRECTION)
                self.assertEqual(len(c["days"]), 2)
                self.assertEqual(c["kind"], "correction")
                self.assertEqual(c["providers"], [provider])

    def _reset(self):
        import shutil
        shutil.rmtree(self.fakehome, ignore_errors=True)
        self.fakehome.mkdir()

    def test_same_day_repeated_is_not_a_candidate(self):  # [spec:history-mining#S2]
        for provider in providers.ALL_PROVIDERS:
            with self.subTest(provider=provider):
                self._reset()
                self.write(provider, [(D1, CORRECTION, "typed"), ("2026-03-10T12:30:00Z", CORRECTION, "typed")] * 2)
                result = self.candidates()
                self.assertEqual(result["messages_by_provider"][provider], 4)
                self.assertEqual(result["candidates"], [])

    def test_non_typed_messages_neither_produce_nor_count(self):  # [spec:history-mining#S3]
        noise = [(D1, CORRECTION, "tool_result"), (D2, CORRECTION, "tool_result")]
        extra = {"claude": [(D1, CORRECTION, "sidechain"), (D2, CORRECTION, "headless")],
                 "opencode": [(D1, CORRECTION, "synthetic")], "codex": []}
        for provider in providers.ALL_PROVIDERS:
            with self.subTest(provider=provider):
                self._reset()
                self.write(provider, noise + extra[provider])
                result = self.candidates()
                self.assertEqual(result["messages_by_provider"][provider], 0)
                self.assertEqual(result["candidates"], [])

    def test_noise_does_not_inflate_a_one_day_correction(self):  # [spec:history-mining#S3]
        for provider in providers.ALL_PROVIDERS:
            with self.subTest(provider=provider):
                self._reset()
                self.write(provider, [(D1, CORRECTION, "typed"), (D2, CORRECTION, "tool_result")])
                self.assertEqual(self.candidates()["candidates"], [])

    def test_pasted_long_and_fenced_text_is_excluded(self):  # [spec:history-mining#S3]
        junk = [
            "x " * 300 + "don't do that",
            "```\ndon't spawn a worktree for this task please\n```",
            "[Pasted text #1] " + CORRECTION,
            "<command-name>" + CORRECTION,
            "a\nb\nc\nd\ne\n" + CORRECTION,
        ]
        for provider in providers.ALL_PROVIDERS:
            with self.subTest(provider=provider):
                self._reset()
                self.write(provider, [(D1 if i % 2 else D2, t, "typed") for i, t in enumerate(junk * 2)])
                result = self.candidates()
                self.assertEqual(result["messages_by_provider"][provider], 0)
                self.assertEqual(result["candidates"], [])

    def test_secret_is_redacted_in_candidate_text(self):  # [spec:history-mining#S11]
        text = "never use this token %s in commits ok" % SECRET
        for provider in providers.ALL_PROVIDERS:
            with self.subTest(provider=provider):
                self._reset()
                self.write(provider, [(D1, text, "typed"), (D2, text, "typed")])
                result = self.candidates()
                self.assertEqual(len(result["candidates"]), 1)
                self.assertNotIn(SECRET, json.dumps(result))
                self.assertIn("[redacted]", result["candidates"][0]["text"])

    def test_preference_kind_and_cross_provider_merge(self):  # [spec:history-mining#S1]
        text = "always run the linter before committing anything"
        self.write("claude", [(D1, text, "typed")])
        self.write("codex", [(D2, text, "typed")])
        c = self.candidates()["candidates"]
        self.assertEqual(len(c), 1)
        self.assertEqual(c[0]["kind"], "preference")
        self.assertEqual(c[0]["providers"], ["claude", "codex"])

    def test_near_duplicate_wordings_merge(self):  # [spec:history-mining#S1]
        self.write("claude", [(D1, CORRECTION, "typed"), (D2, "don't spawn a worktree for this task", "typed")])
        self.assertEqual(len(self.candidates()["candidates"]), 1)

    def test_other_projects_are_not_read(self):  # [spec:history-mining#S4] [spec:history-mining#S5] [spec:history-mining#S6]
        other = self.tmp / "other"
        other.mkdir()
        msgs = [(D1, CORRECTION, "typed"), (D2, CORRECTION, "typed")]
        Fixtures.claude(other, self.fakehome, msgs)
        Fixtures.codex(other, self.fakehome, msgs)
        Fixtures.opencode(other, self.fakehome, msgs)
        result = self.candidates()
        self.assertEqual(sum(result["messages_by_provider"].values()), 0)

    def test_codex_honours_codex_home_and_skips_headless(self):  # [spec:history-mining#S5] [spec:history-mining#S3]
        msgs = [(D1, CORRECTION, "typed"), (D2, CORRECTION, "typed")]
        Fixtures.codex(self.root, self.fakehome, msgs, originator="codex_exec")
        self.assertEqual(self.candidates()["messages_by_provider"]["codex"], 0)
        # without CODEX_HOME the default ~/.codex is used
        os.environ.pop("CODEX_HOME")
        default = self.fakehome / ".codex" / "sessions" / "r"
        _jsonl(default / "rollout-2.jsonl",
               [{"type": "session_meta", "payload": {"cwd": str(self.root)}}] +
               [{"type": "response_item", "timestamp": D1,
                 "payload": {"type": "message", "role": "user", "content": [{"type": "input_text", "text": CORRECTION}]}}])
        self.assertEqual(self.candidates()["messages_by_provider"]["codex"], 1)

    def test_codex_subdirectory_cwd_belongs(self):  # [spec:history-mining#S5]
        sub = str(self.root / "pkg")
        Fixtures.codex(self.root, self.fakehome, [(D1, CORRECTION, "typed")], cwd=sub)
        self.assertEqual(self.candidates()["messages_by_provider"]["codex"], 1)

    def test_opencode_subagent_sessions_excluded(self):  # [spec:history-mining#S3] [spec:history-mining#S6]
        Fixtures.opencode(self.root, self.fakehome, [(D1, CORRECTION, "typed")], parent="ses_0")
        self.assertEqual(self.candidates()["messages_by_provider"]["opencode"], 0)

    def test_opencode_legacy_json_layout(self):  # [spec:history-mining#S6]
        storage = Path(os.environ["XDG_DATA_HOME"]) / "opencode" / "storage"
        (storage / "session" / "g").mkdir(parents=True)
        (storage / "session" / "g" / "ses_1.json").write_text(json.dumps({"id": "ses_1", "directory": str(self.root)}))
        (storage / "message" / "ses_1").mkdir(parents=True)
        for i, iso in enumerate((D1, D2)):
            mid = "msg_%d" % i
            (storage / "message" / "ses_1" / (mid + ".json")).write_text(
                json.dumps({"id": mid, "role": "user", "time": {"created": _epoch_ms(iso)}}))
            (storage / "part" / mid).mkdir(parents=True)
            (storage / "part" / mid / "prt_1.json").write_text(json.dumps({"type": "text", "text": CORRECTION}))
        result = self.candidates()
        self.assertEqual(result["messages_by_provider"]["opencode"], 2)
        self.assertEqual(len(result["candidates"]), 1)

    def test_worktree_transcripts_are_read(self):  # [spec:history-mining#S4]
        wt = Path(str(self.root) + os.sep + ".worktrees" + os.sep + "x")
        slug = re.sub(r"[^A-Za-z0-9]", "-", str(wt))
        _jsonl(self.fakehome / ".claude" / "projects" / slug / "s.jsonl",
               [{"type": "user", "timestamp": D1, "cwd": str(wt), "message": {"content": CORRECTION}}])
        self.assertEqual(self.candidates()["messages_by_provider"]["claude"], 1)

    def test_no_transcripts_is_empty(self):  # [spec:history-mining#S7]
        result = self.candidates()
        self.assertEqual(result["candidates"], [])
        self.assertEqual(set(result["messages_by_provider"]), set(providers.ALL_PROVIDERS))

    def test_malformed_files_are_skipped(self):  # [spec:history-mining#S7]
        slug = re.sub(r"[^A-Za-z0-9]", "-", str(self.root))
        d = self.fakehome / ".claude" / "projects" / slug
        d.mkdir(parents=True)
        (d / "bad.jsonl").write_bytes(b"\xff\xfe not json\n{broken\n[1,2]\n")
        (d / "good.jsonl").write_text(
            "garbage\n" + json.dumps({"type": "user", "timestamp": D1, "cwd": str(self.root), "message": {"content": CORRECTION}}) + "\n")
        (Path(os.environ["XDG_DATA_HOME"]) / "opencode").mkdir(parents=True)
        (Path(os.environ["XDG_DATA_HOME"]) / "opencode" / "opencode.db").write_bytes(b"not a database")
        _jsonl(Path(os.environ["CODEX_HOME"]) / "sessions" / "rollout-9.jsonl", [{"foo": 1}])
        result = self.candidates()
        self.assertEqual(result["messages_by_provider"]["claude"], 1)
        self.assertEqual(result["messages_by_provider"]["opencode"], 0)
        self.assertEqual(result["messages_by_provider"]["codex"], 0)

    def test_claude_slug_collision_is_filtered_by_recorded_cwd(self):  # [spec:history-mining#S4]
        # "/a/b-c" and "/a/b/c" share one slug; only the session recorded under this root counts.
        slug = re.sub(r"[^A-Za-z0-9]", "-", str(self.root))
        d = self.fakehome / ".claude" / "projects" / slug
        foreign = str(self.root) + "x"
        _jsonl(d / "foreign.jsonl", [{"type": "user", "timestamp": D1, "cwd": foreign, "message": {"content": CORRECTION}}])
        _jsonl(d / "nocwd.jsonl", [{"type": "user", "timestamp": D1, "message": {"content": CORRECTION}}])
        self.assertEqual(self.candidates()["messages_by_provider"]["claude"], 0)
        _jsonl(d / "own.jsonl", [{"type": "user", "timestamp": D2, "cwd": str(self.root) + os.sep + "sub",
                                  "message": {"content": CORRECTION}}])
        self.assertEqual(self.candidates()["messages_by_provider"]["claude"], 1)

    def test_message_cap_is_per_provider(self):  # [spec:history-mining#S1]
        many = [(D1, "never touch file number %d please" % i, "typed") for i in range(5)]
        self.write("claude", many)
        self.write("codex", [(D1, CORRECTION, "typed"), (D2, CORRECTION, "typed")])
        with mock.patch.object(mining, "MAX_MESSAGES", 3):
            result = self.candidates()
        self.assertEqual(result["messages_by_provider"]["claude"], 3)
        self.assertEqual(result["messages_by_provider"]["codex"], 2)
        self.assertEqual([c["providers"] for c in result["candidates"]], [["codex"]])

    def test_cluster_cap_is_per_provider(self):  # [spec:history-mining#S1]
        items = [("claude", D1[:10], "never touch file number %d please" % i) for i in range(5)]
        items += [("codex", D1[:10], CORRECTION), ("codex", D2[:10], CORRECTION)]
        with mock.patch.object(mining, "MAX_MESSAGES", 3):
            found = mining.cluster(items)
        self.assertEqual([c["providers"] for c in found], [["codex"]])

    def test_oversize_transcripts_are_counted_per_provider(self):  # [spec:history-mining#S7]
        slug = re.sub(r"[^A-Za-z0-9]", "-", str(self.root))
        _jsonl(self.fakehome / ".claude" / "projects" / slug / "big.jsonl",
               [{"type": "user", "timestamp": D1, "cwd": str(self.root), "message": {"content": CORRECTION}}])
        _jsonl(self.fakehome / ".claude" / "projects" / slug / "ok.jsonl",
               [{"type": "user", "timestamp": D1, "cwd": str(self.root), "message": {"content": CORRECTION}}])
        real = os.path.getsize
        with mock.patch.object(mining.os.path, "getsize",
                               side_effect=lambda p: mining.MAX_FILE_BYTES + 1 if str(p).endswith("big.jsonl") else real(p)):
            result = self.candidates()
        self.assertEqual(result["skipped_oversize_by_provider"],
                         {p: (1 if p == "claude" else 0) for p in providers.ALL_PROVIDERS})
        self.assertEqual(result["messages_by_provider"]["claude"], 1)
        self.assertIn("1 claude transcript(s) skipped", mining.render_sessions(result))

    def test_reader_exception_does_not_fail(self):  # [spec:history-mining#S7]
        with mock.patch.dict(mining.READERS, {"claude": mock.Mock(side_effect=RuntimeError("boom"))}):
            self.assertEqual(self.candidates()["candidates"], [])


class SessionsCommand(MiningCase):
    def snapshot(self):
        snap = {}
        for base in (self.root, self.home, self.fakehome):
            for dirpath, dirs, files in os.walk(base):
                if ".git" in dirs and Path(dirpath) == self.root:
                    pass
                for f in files:
                    p = Path(dirpath) / f
                    if "/.git/" in str(p):
                        continue
                    st = p.stat()
                    snap[str(p)] = (st.st_size, st.st_mtime_ns)
        return snap

    def test_json_shape_and_writes_nothing(self):  # [spec:history-mining#S15] [spec:history-mining#S1]
        for provider in providers.ALL_PROVIDERS:
            FIXTURES[provider](self.root, self.fakehome, [(D1, CORRECTION, "typed"), (D2, CORRECTION, "typed")])
        before = self.snapshot()
        code, out, err = self.run_cli("mine", "sessions", "--path", str(self.root), "--json")
        self.assertEqual(code, 0, err)
        body = json.loads(out)
        self.assertTrue(body["ok"])
        self.assertEqual(body["min_days"], 2)
        self.assertEqual(set(body["messages_by_provider"]), set(providers.ALL_PROVIDERS))
        self.assertEqual(set(body["skipped_oversize_by_provider"]), set(providers.ALL_PROVIDERS))
        self.assertEqual(len(body["candidates"]), 1)
        self.assertEqual(set(body["candidates"][0]), {"text", "kind", "days", "occurrences", "providers"})
        self.assertEqual(body["candidates"][0]["providers"], sorted(providers.ALL_PROVIDERS))
        self.assertEqual(self.snapshot(), before)

    def test_empty_history_exits_zero(self):  # [spec:history-mining#S7]
        code, out, _e = self.run_cli("mine", "sessions", "--path", str(self.root), "--json")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["candidates"], [])

    def test_sessions_make_no_network_call(self):  # [spec:history-mining#S15]
        with mock.patch.object(ihttp, "request_json", side_effect=AssertionError("network")), \
                mock.patch.object(integrations, "ready", side_effect=AssertionError("network")):
            self.write("claude", [(D1, CORRECTION, "typed"), (D2, CORRECTION, "typed")])
            self.assertEqual(len(self.candidates()["candidates"]), 1)


def _node(number, threads):
    return {"number": number, "url": "https://github.com/octo/widgets/pull/%d" % number,
            "reviewThreads": {"nodes": threads}}


def _thread(path, body, resolved=False, outdated=False):
    return {"isResolved": resolved, "isOutdated": outdated, "path": path, "comments": {"nodes": [{"body": body}]}}


NODES = [
    _node(7, [
        _thread("src/a.py", "Please use the shared helper here", resolved=True),
        _thread("src/b.py", "this is stale now", outdated=True),
        _thread("src/c.py", "still open, nobody answered"),
        _thread(None, "general comment, no path", resolved=True),
        _thread("src/d.py", "leaked %s in config" % SECRET, resolved=True),
    ]),
    _node(8, []),
]


class ReviewThreads(MiningCase):
    def test_only_resolved_or_outdated_with_path(self):  # [spec:history-mining#S8] [spec:history-mining#S9]
        found = mining._threads(NODES)
        self.assertEqual([(t["pr"], t["path"], t["state"]) for t in found],
                         [(7, "src/a.py", "resolved"), (7, "src/b.py", "outdated"), (7, "src/d.py", "resolved")])
        self.assertEqual(found[0]["excerpt"], "Please use the shared helper here")
        self.assertTrue(found[0]["url"].endswith("/pull/7"))

    def test_resolved_and_outdated_state(self):  # [spec:history-mining#S8]
        found = mining._threads([_node(1, [_thread("p.py", "fix this properly", resolved=True, outdated=True)])])
        self.assertEqual(found[0]["state"], "resolved+outdated")

    def test_secret_redacted_in_review_excerpt(self):  # [spec:history-mining#S11]
        found = mining._threads(NODES)
        self.assertNotIn(SECRET, json.dumps(found))

    def test_malformed_nodes_tolerated(self):  # [spec:history-mining#S8]
        self.assertEqual(mining._threads([None, "x", {"reviewThreads": None}, _node(1, [None, {"isResolved": True}])]), [])
        self.assertEqual(mining._threads(None), [])

    def test_adapter_path(self):  # [spec:history-mining#S8]
        adapter = mock.Mock()
        adapter.review_threads.return_value = NODES
        with mock.patch.object(integrations, "ready", return_value=(adapter, {"repository": "octo/widgets"}, "tok")):
            result = mining.reviews(self.root)
        adapter.review_threads.assert_called_once_with({"repository": "octo/widgets"}, "tok", "octo/widgets", mining.MERGED_PRS)
        self.assertTrue(result["available"])
        self.assertEqual(result["source"], "github-adapter")
        self.assertEqual(result["prs_scanned"], 2)
        self.assertEqual(len(result["candidates"]), 3)

    def test_no_access_returns_empty_with_reason(self):  # [spec:history-mining#S10]
        with mock.patch.object(integrations, "ready", side_effect=RuntimeError("not connected")), \
                mock.patch.object(mining.subprocess, "run", side_effect=FileNotFoundError("gh")):
            result = mining.reviews(self.root)
        self.assertFalse(result["available"])
        self.assertEqual(result["candidates"], [])
        self.assertIn("could not be read", result["reason"])
        self.assertIn("could not be read", mining.render_reviews(result))

    def test_gh_fallback_when_adapter_cannot(self):  # [spec:history-mining#S8] [spec:history-mining#S10]
        subprocess.run(["git", "remote", "add", "origin", "https://github.com/octo/widgets.git"], cwd=str(self.root), check=True)
        payload = json.dumps({"data": {"repository": {"pullRequests": {"nodes": NODES}}}}).encode()
        real = subprocess.run

        def fake(cmd, *a, **kw):
            if cmd[0] == "gh":
                return mock.Mock(returncode=0, stdout=payload)
            return real(cmd, *a, **kw)

        with mock.patch.object(integrations, "ready", side_effect=RuntimeError("not connected")), \
                mock.patch.object(mining.subprocess, "run", side_effect=fake):
            result = mining.reviews(self.root)
        self.assertEqual(result["source"], "gh")
        self.assertEqual(len(result["candidates"]), 3)

    def test_gh_passes_owner_and_name_as_strings(self):  # [spec:history-mining#S8]
        subprocess.run(["git", "remote", "add", "origin", "https://github.com/123456/789.git"], cwd=str(self.root), check=True)
        payload = json.dumps({"data": {"repository": {"pullRequests": {"nodes": NODES}}}}).encode()
        real = subprocess.run
        seen = []

        def fake(cmd, *a, **kw):
            if cmd[0] == "gh":
                seen.append(cmd)
                return mock.Mock(returncode=0, stdout=payload)
            return real(cmd, *a, **kw)

        with mock.patch.object(integrations, "ready", side_effect=RuntimeError("x")), \
                mock.patch.object(mining.subprocess, "run", side_effect=fake):
            mining.reviews(self.root)
        cmd = seen[0]
        self.assertEqual(cmd[cmd.index("owner=123456") - 1], "-f")
        self.assertEqual(cmd[cmd.index("name=789") - 1], "-f")

    def test_repository_uses_the_integration_host_for_enterprise(self):  # [spec:history-mining#S8]
        subprocess.run(["git", "remote", "add", "origin", "git@ghe.corp.example:octo/widgets.git"], cwd=str(self.root), check=True)
        ghe = {"api_url": "https://ghe.corp.example/api/v3"}
        self.assertEqual(mining._repository(self.root, ghe), "octo/widgets")
        self.assertIsNone(mining._repository(self.root, {"api_url": "https://api.github.com"}))
        self.assertIsNone(mining._repository(self.root, None))

    def test_gh_failure_means_unavailable(self):  # [spec:history-mining#S10]
        subprocess.run(["git", "remote", "add", "origin", "https://github.com/octo/widgets.git"], cwd=str(self.root), check=True)
        real = subprocess.run

        def fake(cmd, *a, **kw):
            return mock.Mock(returncode=1, stdout=b"") if cmd[0] == "gh" else real(cmd, *a, **kw)

        with mock.patch.object(integrations, "ready", side_effect=RuntimeError("x")), \
                mock.patch.object(mining.subprocess, "run", side_effect=fake):
            self.assertFalse(mining.reviews(self.root)["available"])

    def test_thread_cap(self):  # [spec:history-mining#S8]
        many = [_thread("f%d.py" % i, "change please number %d" % i, resolved=True) for i in range(40)]
        found = mining._threads([_node(1, many), _node(2, many), _node(3, many)])
        self.assertEqual(len(found), mining.MAX_THREADS)


class ReviewsEndToEnd(IntegrationTestCase):
    """The real adapter, `integrations.ready()` and CLI against a loopback GraphQL server."""

    def setUp(self):
        super().setUp()
        subprocess.run(["git", "remote", "add", "origin", "https://github.com/octo/widgets.git"],
                       cwd=str(self.root), check=True)

    def mine(self):
        code, out, err = self.run_cli("mine", "reviews", "--path", str(self.root), "--json")
        return code, json.loads(out), err

    def test_reviews_via_adapter_and_graphql(self):  # [spec:history-mining#S8] [spec:history-mining#S9] [spec:history-mining#S15]
        code, body, _o, _e = self.connect_github()
        self.assertEqual(code, 0, body)
        # The integration's configured host is the loopback server, so origin must point there.
        host = urllib.parse.urlsplit(self.server.url).hostname
        subprocess.run(["git", "remote", "set-url", "origin", "https://{}/octo/widgets.git".format(host)],
                       cwd=str(self.root), check=True)
        self.server.routes[("POST", "/graphql")] = (
            200, {}, {"data": {"repository": {"pullRequests": {"nodes": NODES}}}})
        code, body, err = self.mine()
        self.assertEqual(code, 0, err)
        self.assertTrue(body["ok"])
        self.assertEqual(body["source"], "github-adapter")
        self.assertEqual(body["repository"], "octo/widgets")
        self.assertEqual(body["prs_scanned"], 2)
        self.assertEqual({c["path"] for c in body["candidates"]}, {"src/a.py", "src/b.py", "src/d.py"})
        self.assertEqual(set(body["candidates"][0]), {"pr", "url", "path", "state", "excerpt"})
        self.assertNotIn(SECRET, json.dumps(body))
        req = [r for r in self.server.log if r["path"] == "/graphql"][0]
        sent = json.loads(req["body"])
        self.assertEqual(sent["variables"], {"owner": "octo", "name": "widgets", "prs": 50})
        self.assertIn("MERGED", sent["query"])
        self.assertTrue(req["headers"]["Authorization"])

    def test_not_connected_no_gh_is_empty_exit_zero(self):  # [spec:history-mining#S10]
        env = dict(os.environ)
        os.environ["PATH"] = str(self.tmp)  # no gh reachable
        try:
            code, body, _e = self.mine()
        finally:
            os.environ["PATH"] = env["PATH"]
        self.assertEqual(code, 0)
        self.assertFalse(body["available"])
        self.assertEqual(body["candidates"], [])
        self.assertTrue(body["reason"])

    def test_server_error_is_empty_exit_zero(self):  # [spec:history-mining#S10]
        self.connect_github()
        self.server.routes[("POST", "/graphql")] = (502, {}, {"message": "bad gateway"})
        os.environ_path = os.environ["PATH"]
        os.environ["PATH"] = str(self.tmp)
        try:
            code, body, _e = self.mine()
        finally:
            os.environ["PATH"] = os.environ_path
        self.assertEqual(code, 0)
        self.assertFalse(body["available"])

    def test_adapter_method_directly(self):  # [spec:history-mining#S8]
        self.server.routes[("POST", "/graphql")] = (
            200, {}, {"data": {"repository": {"pullRequests": {"nodes": NODES}}}})
        nodes = github_adapter.GitHub().review_threads({"api_url": self.server.url}, "tok", "octo/widgets", 3)
        self.assertEqual(len(nodes), 2)
        sent = json.loads(self.server.log[-1]["body"])
        self.assertEqual(sent["variables"]["prs"], 3)

    def test_adapter_rejects_unexpected_shape(self):  # [spec:history-mining#S10]
        self.server.routes[("POST", "/graphql")] = (200, {}, {"errors": [{"message": "x"}]})
        with self.assertRaises(ihttp.FetchError):
            github_adapter.GitHub().review_threads({"api_url": self.server.url}, "tok", "octo/widgets")

    def test_ghe_api_v3_maps_to_api_graphql(self):  # [spec:history-mining#S8]
        with mock.patch.object(ihttp, "post_json", return_value=({"data": {"repository": {"pullRequests": {"nodes": []}}}}, {})) as m:
            github_adapter.GitHub().review_threads({"api_url": "https://ghe.example.com/api/v3"}, "t", "o/n")
        self.assertEqual(m.call_args[0][0], "https://ghe.example.com/api")
        self.assertEqual(m.call_args[0][1], "/graphql")

    def test_ready_raises_when_not_connected(self):  # [spec:history-mining#S10]
        with self.assertRaises(Exception):
            integrations.ready("github", self.root)

    def test_ready_returns_adapter_values_token(self):  # [spec:history-mining#S8]
        self.connect_github()
        adapter, values, token = integrations.ready("github", self.root)
        self.assertEqual(adapter.name, "github")
        self.assertEqual(values["api_url"], self.server.url)
        self.assertTrue(token)


if __name__ == "__main__":
    unittest.main()
