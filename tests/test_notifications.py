"""The notification queue: hooks append, the CLI reads and acknowledges, the app streams.

The framework's notifications used to be boxed stdout that no provider shows the user
(SessionStart stdout is model context; Stop stdout is not displayed). These tests pin
the replacement end to end: the bash writer (`scripts/hooks/lib/notify.sh`), the
record contract it shares with `notifications.RECORD_KEYS`, and the three commands a
client uses — including `watch`, the one command whose `--json` stdout is JSON Lines.
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

from devteam import bind, notifications, project

NOTIFY_LIB = REPO_ROOT / "scripts" / "hooks" / "lib" / "notify.sh"
STATE_LIB = REPO_ROOT / "scripts" / "lib" / "state.sh"
NOTIFIER = REPO_ROOT / "scripts" / "hooks" / "stop" / "04-notifier.sh"
SESSION_START = REPO_ROOT / "scripts" / "hooks" / "session-start.sh"


def record(id_, level="warning", code="test.code", message="m", expires_at=0, ts=None, project_id="p"):
    return {
        "id": id_,
        "ts": int(time.time()) if ts is None else ts,
        "project_id": project_id,
        "session_id": "s1",
        "level": level,
        "code": code,
        "message": message,
        "dedupe_key": "",
        "expires_at": expires_at,
    }


class QueueCase(StoreTestCase):
    def setUp(self):
        super().setUp()
        self.install_version("3.0.0", activate=True)
        self.root = self.new_project("notified")
        self.project_id = bind.bind(self.root, provider_names=["claude"], mode="link")["project_id"]
        self.queue = notifications.queue_path(self.root, self.project_id)
        self.queue.parent.mkdir(parents=True, exist_ok=True)

    def append(self, *records, raw=None):
        with open(str(self.queue), "a", encoding="utf-8") as handle:
            for item in records:
                handle.write(json.dumps(item) + "\n")
            if raw is not None:
                handle.write(raw + "\n")


class CollectAndAckTest(QueueCase):
    def test_a_malformed_line_is_skipped_not_fatal(self):
        self.append(record("a"), raw='{"id": "broken"')
        self.append(record("b"))
        self.assertEqual([r["id"] for r in notifications.collect()], ["a", "b"])

    def test_a_record_with_a_mistyped_field_is_skipped_not_fatal(self):
        # `"ts": null` used to reach the sort in `collect` and raise, taking `list`,
        # `ack` and `watch` down until 200 newer lines trimmed it away.
        bad = [
            dict(record("null-ts"), ts=None),
            dict(record("str-ts"), ts="yesterday"),
            dict(record("bool-ts"), ts=True),
            dict(record("str-expiry"), expires_at="soon"),
            dict(record("int-message"), message=7),
        ]
        self.append(record("a"), *bad)
        self.append(record("b"))
        self.assertEqual([r["id"] for r in notifications.collect()], ["a", "b"])
        self.assertEqual(notifications.ack(all_=True), ["a", "b"])

    def test_an_expired_notification_is_not_reported(self):
        now = time.time()
        self.append(record("old", expires_at=int(now) - 1), record("live", expires_at=int(now) + 60))
        self.assertEqual([r["id"] for r in notifications.collect(now=now)], ["live"])

    def test_ack_marks_seen_and_unseen_hides_it(self):
        self.append(record("a"), record("b"))
        self.assertEqual(notifications.ack(["a"]), ["a"])
        self.assertEqual([r["id"] for r in notifications.collect(unseen_only=True)], ["b"])
        seen = {r["id"]: r["seen"] for r in notifications.collect()}
        self.assertEqual(seen, {"a": True, "b": False})

    def test_ack_is_idempotent_and_all_takes_the_rest(self):
        self.append(record("a"), record("b"))
        notifications.ack(["a"])
        self.assertEqual(notifications.ack(["a"]), [])
        self.assertEqual(notifications.ack(all_=True), ["b"])

    def test_ack_never_rewrites_the_queue(self):
        # A rewrite racing a hook's append would drop the line being written.
        self.append(record("a"))
        before = self.queue.read_bytes()
        notifications.ack(all_=True)
        self.assertEqual(self.queue.read_bytes(), before)

    def test_ack_drops_old_marks_for_records_already_trimmed(self):
        self.append(record("live"))
        seen_file = notifications.seen_path(self.root, self.project_id)
        old = time.time() - notifications.SEEN_RETENTION_SECONDS - 10
        seen_file.write_text(json.dumps({"schema": 1, "seen": {"gone": old}}), encoding="utf-8")
        notifications.ack(["live"])
        seen = json.loads(seen_file.read_text(encoding="utf-8"))["seen"]
        self.assertEqual(sorted(seen), ["live"])

    def test_ack_with_nothing_named_is_a_usage_error(self):
        code, out, _ = self.run_cli("--json", "notifications", "ack")
        self.assertEqual(code, 2)
        self.assertIn("--all", json.loads(out)["hint"])

    def test_list_and_ack_json_shapes_are_exact(self):
        self.append(record("a"))
        code, out, err = self.run_cli("--json", "notifications", "list")
        self.assertEqual(code, 0, err)
        payload = json.loads(out)
        self.assertEqual(set(payload), {"notifications", "count", "ok"})
        self.assertEqual(
            set(payload["notifications"][0]), set(notifications.RECORD_KEYS) | {"seen"}
        )
        code, out, err = self.run_cli("--json", "notifications", "ack", "a")
        self.assertEqual(code, 0, err)
        self.assertEqual(set(json.loads(out)), {"acknowledged", "count", "ok"})


class WatchTest(QueueCase):
    def test_backlog_then_ready_then_each_new_record_then_end(self):
        self.append(record("backlog"))
        events = []
        stop = notifications._Stop()

        def run():
            notifications.watch(events.append, interval=0.05, stop=stop, watch_stdin=False)

        thread = threading.Thread(target=run)
        thread.start()
        deadline = time.time() + 5
        while not any(e["event"] == "ready" for e in events) and time.time() < deadline:
            time.sleep(0.02)
        time.sleep(0.05)  # a distinct mtime for the append below
        self.append(record("fresh"))
        while not any(e.get("notification", {}).get("id") == "fresh" for e in events) and time.time() < deadline:
            time.sleep(0.02)
        stop.set("test")
        thread.join(5)

        kinds = [e["event"] if e["event"] != "notification" else e["notification"]["id"] for e in events]
        self.assertEqual(kinds, ["backlog", "ready", "fresh", "end"])
        self.assertEqual(events[-1]["reason"], "test")

    def test_an_already_seen_record_is_not_streamed(self):
        self.append(record("seen"), record("unseen"))
        notifications.ack(["seen"])
        events = []
        stop = notifications._Stop()
        stop.set("once")  # one pass, then end
        notifications.watch(events.append, interval=0.01, stop=stop, watch_stdin=False)
        # `stop` is already set, so the loop body never runs: nothing but `end`.
        self.assertEqual([e["event"] for e in events], ["end"])
        events.clear()
        stop = notifications._Stop()
        thread = threading.Thread(
            target=notifications.watch, args=(events.append,),
            kwargs={"interval": 0.02, "stop": stop, "watch_stdin": False},
        )
        thread.start()
        deadline = time.time() + 5
        while not any(e["event"] == "ready" for e in events) and time.time() < deadline:
            time.sleep(0.02)
        stop.set("done")
        thread.join(5)
        streamed = [e["notification"]["id"] for e in events if e["event"] == "notification"]
        self.assertEqual(streamed, ["unseen"])

    def test_the_cli_streams_json_lines_and_exits_when_stdin_closes(self):
        self.append(record("x"))
        proc = subprocess.Popen(
            [sys.executable, str(CLI), "--json", "notifications", "watch", "--interval", "0.05"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=dict(os.environ),
        )
        lines = []
        for _ in range(2):
            lines.append(json.loads(proc.stdout.readline()))
        proc.stdin.close()
        rest = proc.stdout.read().decode().splitlines()
        code = proc.wait(timeout=10)
        stderr = proc.stderr.read()
        proc.stdout.close()
        proc.stderr.close()
        lines.extend(json.loads(line) for line in rest if line.strip())
        self.assertEqual(code, 0, stderr)
        self.assertEqual(lines[0]["event"], "notification")
        self.assertEqual(lines[0]["notification"]["id"], "x")
        self.assertEqual(lines[1]["event"], "ready")
        self.assertEqual(lines[-1], {"event": "end", "reason": "stdin-closed", "ok": True})
        self.assertTrue(all(l["ok"] is True for l in lines))

    def run_watch_failure(self, *argv):
        proc = subprocess.run(
            [sys.executable, str(CLI), *argv],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=dict(os.environ),
            timeout=30,
        )
        return proc.returncode, proc.stdout.decode().splitlines()

    def test_a_failure_is_one_compact_json_line_before_and_after_parsing(self):
        # An indented error document made the app read `{` as a protocol error, so
        # the exit code that explains the failure (e.g. 3, a layout it may not
        # migrate) was never looked at and the stream retried forever.
        corrupt = self.tmp / "declaration.json"
        corrupt.write_text("{not json", encoding="utf-8")
        cases = {
            "parse": ("--json", "notifications", "watch", "--interval", "0"),
            "gate": ("--json", "--client-schemas", str(corrupt), "notifications", "watch"),
        }
        for name, argv in cases.items():
            with self.subTest(name):
                code, lines = self.run_watch_failure(*argv)
                self.assertEqual(code, 2)
                self.assertEqual(len(lines), 1, lines)
                body = json.loads(lines[0])
                self.assertEqual(body["event"], "error")
                self.assertIs(body["ok"], False)
                self.assertEqual(body["exit_code"], 2)

    def test_another_commands_failure_keeps_its_indented_document(self):
        code, lines = self.run_watch_failure("--json", "notifications", "ack")
        self.assertEqual(code, 2)
        self.assertGreater(len(lines), 1)
        self.assertNotIn("event", json.loads("\n".join(lines)))

    def test_forgetting_acknowledged_ids_neither_replays_nor_drops(self):
        # `emitted` forgets ids a queue no longer reports as unseen, so it is bounded
        # by the queues rather than by how long `watch` has run. Forgetting must not
        # turn into a replay of the acknowledged record, nor hide the next one.
        self.append(record("one"), record("two"))
        events = []
        stop = notifications._Stop()

        def emit(event):
            events.append(event)
            if event["event"] == "ready":
                notifications.ack(["one"])
                time.sleep(0.05)
                self.append(record("three"))

        thread = threading.Thread(
            target=notifications.watch, args=(emit,),
            kwargs={"interval": 0.02, "stop": stop, "watch_stdin": False},
        )
        thread.start()
        deadline = time.time() + 5
        while not any(e.get("notification", {}).get("id") == "three" for e in events) and time.time() < deadline:
            time.sleep(0.02)
        stop.set("done")
        thread.join(5)
        streamed = [e["notification"]["id"] for e in events if e["event"] == "notification"]
        self.assertEqual(streamed, ["one", "two", "three"])

    @unittest.skipIf(os.name != "posix", "SIGTERM is TerminateProcess on Windows")
    def test_the_cli_ends_cleanly_on_sigterm(self):
        proc = subprocess.Popen(
            [sys.executable, str(CLI), "--json", "notifications", "watch", "--interval", "0.05"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            env=dict(os.environ),
        )
        self.assertEqual(json.loads(proc.stdout.readline())["event"], "ready")
        proc.terminate()
        last = [json.loads(l) for l in proc.stdout.read().decode().splitlines() if l.strip()][-1]
        self.assertEqual(proc.wait(timeout=10), 0)
        self.assertEqual(last["reason"], "sigterm")
        proc.stdin.close()
        proc.stdout.close()


@requires_bash()
class NotifyShTest(StoreTestCase):
    """The writer half of the record contract."""

    def notify(self, state_dir, *calls, suppress="false", max_lines=None):
        script = ['source "$1"', 'source "$2"', 'devteam_notify_init "$3" "$4" "$5" "sess"']
        for level, code, message, ttl, dedupe in calls:
            script.append(
                "devteam_notify {} {} {} {} {}".format(
                    *(shlex.quote(v) for v in (level, code, message, str(ttl), dedupe))
                )
            )
        env = dict(os.environ)
        if max_lines is not None:
            env["DEVTEAM_NOTIFY_MAX_LINES"] = str(max_lines)
        root = self.tmp / "proj"
        (root / ".dev-team-agents").mkdir(parents=True, exist_ok=True)
        (root / ".dev-team-agents" / "project.json").write_text(
            json.dumps({"schema": 1, "project_id": "pid-1"}), encoding="utf-8"
        )
        subprocess.run(
            ["bash", "-c", "\n".join(script), "_", str(STATE_LIB), str(NOTIFY_LIB),
             str(root), str(state_dir), suppress],
            check=True, env=env,
        )
        path = Path(state_dir) / notifications.QUEUE_FILE
        if not path.is_file():
            return []
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]

    def test_the_record_has_exactly_the_contract_keys_and_survives_hostile_text(self):
        state = self.tmp / "state"
        message = 'a "quoted" \\ back\nslash\tand tab'
        rows = self.notify(state, ("critical", "context.critical", message, 60, "k1"))
        self.assertEqual(len(rows), 1)
        self.assertEqual(set(rows[0]), set(notifications.RECORD_KEYS))
        self.assertEqual(rows[0]["message"], 'a "quoted" \\ back\nslash and tab')
        self.assertEqual(rows[0]["project_id"], "pid-1")
        self.assertEqual(rows[0]["session_id"], "sess")
        self.assertGreater(rows[0]["expires_at"], rows[0]["ts"])
        self.assertTrue(notifications._valid(rows[0]))

    def test_a_dedupe_key_already_queued_is_not_written_again(self):
        state = self.tmp / "state"
        rows = self.notify(state, ("warning", "c", "one", 0, "same"), ("warning", "c", "two", 0, "same"))
        self.assertEqual([r["message"] for r in rows], ["one"])

    def test_suppression_all_and_by_level(self):
        state = self.tmp / "all"
        self.assertEqual(self.notify(state, ("critical", "c", "m", 0, ""), suppress="true"), [])
        state = self.tmp / "info"
        rows = self.notify(
            state, ("info", "tip", "t", 0, ""), ("warning", "w", "w", 0, ""), suppress="['info']"
        )
        self.assertEqual([r["level"] for r in rows], ["warning"])

    def test_control_characters_never_make_an_invalid_line(self):
        # An ANSI escape or a \b made the line invalid JSON; the reader skips those,
        # so the notification vanished without a trace.
        state = self.tmp / "ctrl"
        rows = self.notify(state, ("warning", "update.available", "a\x1b[31mb\x08c\x7fd", 0, ""))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["message"], "a[31mbcd")
        self.assertTrue(notifications._valid(rows[0]))

    def test_concurrent_writers_trimming_leave_whole_lines_and_no_lock(self):
        state = self.tmp / "race"
        state.mkdir()
        root = self.tmp / "proj"
        (root / ".dev-team-agents").mkdir(parents=True, exist_ok=True)
        script = (
            'source "$1"; source "$2"; devteam_notify_init "$3" "$4" false s; '
            'for i in $(seq 1 25); do devteam_notify info c "w$5-$i" 0 ""; done'
        )
        env = dict(os.environ, DEVTEAM_NOTIFY_MAX_LINES="30")
        procs = [
            subprocess.Popen(
                ["bash", "-c", script, "_", str(STATE_LIB), str(NOTIFY_LIB), str(root), str(state), str(n)],
                env=env,
            )
            for n in range(3)
        ]
        for proc in procs:
            self.assertEqual(proc.wait(timeout=60), 0)
        lines = (state / notifications.QUEUE_FILE).read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 30)
        self.assertTrue(all(notifications._valid(json.loads(line)) for line in lines))
        self.assertEqual(sorted(p.name for p in state.iterdir()), [notifications.QUEUE_FILE])

    def test_the_writer_keeps_only_the_newest_lines(self):
        state = self.tmp / "trim"
        calls = [("info", "c", "n{}".format(i), 0, "") for i in range(7)]
        rows = self.notify(state, *calls, max_lines=5)
        self.assertEqual([r["message"] for r in rows], ["n2", "n3", "n4", "n5", "n6"])


@requires_bash()
class NotifierHookTest(StoreTestCase):
    """`stop/04-notifier.sh`: once per session, silent on stdout, one python fork."""

    def setUp(self):
        super().setUp()
        self.root = self.new_project("hooked")
        self.state = self.root / ".dev-team-agents" / "user-data"
        self.state.mkdir(parents=True)
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=str(self.root), stdout=subprocess.PIPE, check=True
        ).stdout.decode().strip()
        (self.state / "state.json").write_text(
            json.dumps({"session_id": "s1", "session_head": head}), encoding="utf-8"
        )
        transcript = self.root / "transcript.jsonl"
        transcript.write_text(
            json.dumps({"message": {"usage": {"input_tokens": 10, "cache_read_input_tokens": 150000}}})
            + "\n",
            encoding="utf-8",
        )
        self.payload = self.root / "payload.json"
        self.payload.write_text(json.dumps({"transcript_path": str(transcript)}), encoding="utf-8")

    def run_hook(self, extra_env=None):
        env = dict(os.environ, DEVTEAM_HOOK_PAYLOAD=str(self.payload))
        env.update(extra_env or {})
        return subprocess.run(
            ["bash", str(NOTIFIER)], cwd=str(self.root), env=env,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True,
        )

    def queued(self):
        path = self.state / notifications.QUEUE_FILE
        return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines()] if path.is_file() else []

    def test_nothing_reaches_stdout(self):
        # Stop stdout is not shown to the user; anything printed there is noise.
        self.assertEqual(self.run_hook().stdout, b"")

    def test_context_critical_and_the_tip_fire_once_across_stops(self):
        for _ in range(3):
            self.run_hook()
        codes = [r["code"] for r in self.queued()]
        self.assertEqual(codes.count("context.critical"), 1)
        self.assertEqual(codes.count("tip.daily"), 1)

    def test_without_a_session_id_once_per_session_becomes_once_per_day(self):
        # A fixed `0` fallback made the notice fire once and then never again.
        (self.state / "state.json").write_text(json.dumps({}), encoding="utf-8")
        for _ in range(2):
            self.run_hook()
        keys = [r["dedupe_key"] for r in self.queued() if r["code"] == "context.critical"]
        self.assertEqual(keys, ["context.critical:day-{}".format(time.strftime("%Y-%m-%d"))])

    def test_at_most_one_python_fork_per_stop(self):
        # Wall-clock budgets are noise on a shared CI runner; the fork count is the cost.
        shim = self.tmp / "shim"
        shim.mkdir()
        log = self.tmp / "python-calls"
        real = shutil.which("python3")
        (shim / "python3").write_text(
            '#!/bin/sh\necho x >> "{}"\nexec "{}" "$@"\n'.format(log, real), encoding="utf-8"
        )
        (shim / "python3").chmod(0o755)
        self.run_hook({"PATH": "{}{}{}".format(shim, os.pathsep, os.environ["PATH"])})
        self.assertEqual(len(log.read_text().splitlines()), 1)


@requires_bash()
class SessionStartTest(StoreTestCase):
    def test_no_boxed_banner_is_printed_any_more(self):
        root = self.new_project("started")
        (root / "docs" / "project.md").write_text("# p\n", encoding="utf-8")
        old = time.time() - 90 * 86400
        os.utime(str(root / "docs" / "project.md"), (old, old))
        result = subprocess.run(
            ["bash", str(SESSION_START)], cwd=str(root), stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, env=dict(os.environ), check=True,
        )
        self.assertNotIn("DEV TEAM AGENTS", result.stdout.decode())
        queue = root / ".dev-team-agents" / "user-data" / notifications.QUEUE_FILE
        codes = [json.loads(l)["code"] for l in queue.read_text(encoding="utf-8").splitlines()]
        self.assertIn("docs.project_stale", codes)


if __name__ == "__main__":
    unittest.main()
