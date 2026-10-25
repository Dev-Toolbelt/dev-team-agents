"""Repair ledger (ADR-0051, spec docs/specs/repair-ledger.md).

Two layers: `repairs.process` / `repairs.classify` driven directly, and the PostToolUse sub-script
`03-repair-detect.sh` driven as a subprocess with each provider's payload shape. Delivery wiring itself
(`devteam_hints_deliver`) is covered by tests/test_hint_delivery.py; here it is only exercised through
the hook, per provider.
"""

import json
import os
import subprocess
import unittest

from devteam_support import REPO_ROOT, StoreTestCase, make_git_project, requires_bash

from devteam import paths, providers, repairs

HOOK = REPO_ROOT / "scripts" / "hooks" / "post-tool-use" / "03-repair-detect.sh"
CONTEXT_HINTS = REPO_ROOT / "scripts" / "hooks" / "lib" / "context-hints.sh"
SESSION = "sess-1"


def _claude(command, ok, session=SESSION, text=""):
    if ok:
        return {"hook_event_name": "PostToolUse", "session_id": session, "tool_name": "Bash",
                "tool_input": {"command": command}, "tool_response": {"stdout": text or "ok", "stderr": ""}}
    return {"hook_event_name": "PostToolUseFailure", "session_id": session, "tool_name": "Bash",
            "tool_input": {"command": command}, "error": "Exit code 1\n" + (text or "boom")}


def _codex(command, ok, session=SESSION, text=""):
    body = "Process exited with code {}\n{}".format(0 if ok else 1, text or ("ok" if ok else "boom"))
    return {"hook_event_name": "PostToolUse", "session_id": session, "tool_name": "Bash",
            "tool_input": {"command": command}, "tool_response": body}


def _opencode(command, ok, session=SESSION, text=""):
    return {"sessionID": session, "tool": "bash", "args": {"command": command},
            "output": text or ("ok" if ok else "boom"), "exit_code": 0 if ok else 1}


#: Per-provider shell payload builders. Fails when a provider is added without a case.
SHELL_PAYLOADS = {"claude": _claude, "codex": _codex, "opencode": _opencode}
#: How a repair hint reaches the model: immediately as PostToolUse(Failure) context, or queued.
DELIVERY = {"claude": "now", "codex": "now", "opencode": "queued"}


class ProviderMapTest(unittest.TestCase):
    def test_every_provider_has_a_payload_and_delivery_case(self):
        # Assert
        self.assertEqual(set(SHELL_PAYLOADS), set(providers.ALL_PROVIDERS))
        self.assertEqual(set(DELIVERY), set(providers.ALL_PROVIDERS))


class LedgerCase(StoreTestCase):
    def setUp(self):
        super().setUp()
        self.state = self.tmp / "state"
        self.state.mkdir()
        self.tmpdir = self.tmp / "tmpdir"
        self.tmpdir.mkdir()
        saved = os.environ.get("TMPDIR")
        os.environ["TMPDIR"] = str(self.tmpdir)
        self.addCleanup(lambda: os.environ.__setitem__("TMPDIR", saved) if saved is not None
                        else os.environ.pop("TMPDIR", None))

    def run_calls(self, calls, build=_claude, session=SESSION):
        hints = []
        for command, ok in calls:
            hints.extend(repairs.process(str(self.state), session, build(command, ok, session)))
        return hints

    def ledger(self):
        path = self.state / repairs.LEDGER_FILE
        return json.loads(path.read_text())["repairs"] if path.exists() else []


class DetectionTest(LedgerCase):
    def test_env_var_set_on_retry_is_recorded(self):
        """[spec:repair-ledger#S1]"""
        # Arrange / Act
        self.run_calls([("make build", False), ("DATABASE_URL=sqlite:///x make build", True)])
        # Assert
        entries = self.ledger()
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["sig"], "make build")
        self.assertEqual(entries[0]["kinds"], ["env"])
        self.assertEqual(entries[0]["delta"], ["set DATABASE_URL=sqlite:///x"])

    def test_each_delta_kind_is_recorded(self):
        """[spec:repair-ledger#S1]"""
        cases = {
            "flag": ("npm run build", "npm run build --legacy-peer-deps", "flag"),
            "wrapper": ("pytest tests", "poetry run pytest tests", "wrapper"),
            "step": ("npm run build", "npm install && npm run build", "step"),
        }
        for name, (fail, fix, kind) in cases.items():
            with self.subTest(kind=name):
                # Arrange
                for leftover in self.state.glob("*"):
                    leftover.unlink()
                # Act
                self.run_calls([(fail, False), (fix, True)])
                # Assert
                entries = self.ledger()
                self.assertEqual(len(entries), 1)
                self.assertIn(kind, entries[0]["kinds"])

    def test_an_intermediate_step_between_failure_and_retry_is_recorded(self):
        """[spec:repair-ledger#S1]"""
        # Act
        self.run_calls([("make build", False), ("npm install", True), ("make build", True)])
        # Assert
        entries = self.ledger()
        self.assertEqual([e["sig"] for e in entries], ["make build"])
        self.assertEqual(entries[0]["kinds"], ["step"])
        self.assertIn("npm install", entries[0]["delta"][0])

    def test_the_same_repair_twice_increments_one_entry(self):
        """[spec:repair-ledger#S1]"""
        # Act
        for _ in range(2):
            self.run_calls([("make build", False), ("FOO=1 make build", True)])
        # Assert
        entries = self.ledger()
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["count"], 2)

    def test_every_provider_payload_shape_is_recorded(self):
        """[spec:repair-ledger#S1]"""
        for provider, build in SHELL_PAYLOADS.items():
            with self.subTest(provider=provider):
                # Arrange
                for leftover in self.state.glob("*"):
                    leftover.unlink()
                # Act
                self.run_calls([("make build", False), ("FOO=1 make build", True)], build=build)
                # Assert
                self.assertEqual([e["sig"] for e in self.ledger()], ["make build"])

    def test_an_identical_retry_is_a_flake(self):
        """[spec:repair-ledger#S3]"""
        # Act
        self.run_calls([("make build", False), ("make build", True)])
        # Assert
        self.assertEqual(self.ledger(), [])

    def test_a_retry_within_ten_calls_is_recorded_and_beyond_it_is_not(self):
        """[spec:repair-ledger#S4]"""
        # Arrange: distinct non-look fillers so they are not mistaken for the retry
        def fillers(n):
            return [("touch f{}".format(i), True) for i in range(n)]

        # Act: the retry is the 10th call after the failure
        self.run_calls([("make build", False)] + fillers(9) + [("FOO=1 make build", True)])
        within = [e["sig"] for e in self.ledger()]
        for leftover in self.state.glob("*"):
            leftover.unlink()
        # Act: the retry is the 11th call after the failure
        self.run_calls([("make build", False)] + fillers(10) + [("FOO=1 make build", True)], session="sess-2")
        # Assert
        self.assertEqual(within, ["make build"])
        self.assertEqual(self.ledger(), [])

    def test_ignored_failure_kinds_are_never_recorded(self):
        """[spec:repair-ledger#S5]"""
        denied = _claude("make build", False, text="blocked by PreToolUse hook: not allowed")
        sql = _claude("psql -c 'select 1'", False, text='ERROR:  syntax error at or near "selec"')
        graphql = _claude("curl api", False, text='{"errors":[{"message":"Cannot query field x"}]}')
        look_log = _claude("cat build/test.log", False)
        ci_log = _claude("gh run view 123 --log-failed", False)
        fixes = {
            "make build": "FOO=1 make build",
            "psql -c 'select 1'": "FOO=1 psql -c 'select 1'",
            "curl api": "FOO=1 curl api",
            "cat build/test.log": "FOO=1 cat build/test.log",
            "gh run view 123 --log-failed": "FOO=1 gh run view 123 --log-failed",
        }
        for label, failed in (("hook denial", denied), ("sql", sql), ("graphql", graphql),
                              ("test log read", look_log), ("ci log read", ci_log)):
            with self.subTest(kind=label):
                # Arrange
                for leftover in self.state.glob("*"):
                    leftover.unlink()
                command = failed["tool_input"]["command"]
                # Act
                repairs.process(str(self.state), SESSION, failed)
                repairs.process(str(self.state), SESSION, _claude(fixes[command], True))
                # Assert
                self.assertEqual(self.ledger(), [])

    def test_a_non_shell_or_empty_command_is_skipped(self):
        # Act
        out = repairs.process(str(self.state), SESSION, {"tool_name": "Edit", "tool_input": {"file_path": "x"}})
        # Assert
        self.assertEqual(out, [])
        self.assertEqual(list(self.state.iterdir()), [])


class RedactionTest(LedgerCase):
    def test_secret_values_never_reach_the_ledger_or_the_hint(self):
        """[spec:repair-ledger#S6]"""
        secret = "hunter2-very-secret-9f8e7d"
        token = "ghp_" + "a1B2c3D4e5F6g7H8i9J0k1L2m3N4o5P6q7R8"
        # Act
        self.run_calls([("deploy.sh", False), ("API_TOKEN={} PLAIN={} deploy.sh".format(secret, token), True)])
        hints = self.run_calls([("deploy.sh", False)])
        # Assert
        raw = (self.state / repairs.LEDGER_FILE).read_text()
        for value in (secret, token):
            self.assertNotIn(value, raw)
            self.assertFalse(any(value in h for h in hints))
        self.assertIn("API_TOKEN=[redacted]", raw)
        self.assertEqual(len(hints), 1)


class FlagSecretTest(LedgerCase):
    def test_secrets_typed_as_flags_are_never_stored(self):
        """Single-dash flags with an attached value keep the option name only; `--x=v` drops the value."""
        cases = {
            "-pS3cretPw": "-p",
            "-tghp_a1B2c3D4e5F6g7H8i9J0k1L2m3N4o5P6q7R8": "-t",
            "-uadmin:hunter2": "-u",
            "--api-token=zzTopSecretValue99": "--api-token",
        }
        for flag, name in cases.items():
            with self.subTest(flag=flag):
                state = self.tmp / ("state-" + name.strip("-"))
                state.mkdir()
                secret = flag.split("=", 1)[-1] if "=" in flag else flag[2:]
                # Act
                for command, ok in (("mytool login {}".format(flag), False), ("mytool login", False),
                                    ("mytool login {}".format(flag), True)):
                    repairs.process(str(state), SESSION, _claude(command, ok))
                hints = repairs.process(str(state), SESSION, _claude("mytool login", False))
                # Assert
                for path in state.iterdir():
                    if path.is_file():
                        self.assertNotIn(secret, path.read_text(), path.name)
                self.assertTrue(any(name in h for h in hints), hints)
                self.assertFalse(any(secret in h for h in hints))

    def test_the_window_file_holds_no_flag_value_while_a_failure_waits(self):
        # Act
        repairs.process(str(self.state), SESSION, _claude("mytool login -pS3cretPw", False))
        # Assert
        window = (self.state / (repairs.WINDOW_PREFIX + SESSION + ".json")).read_text()
        self.assertNotIn("S3cretPw", window)
        self.assertIn("-p", window)

    def test_hint_line_redacts_as_a_final_net(self):
        # Act
        line = repairs.hint_line({"sig": "x", "delta": ["set TOKEN=ghp_" + "a1B2c3D4e5F6g7H8i9J0k1L2m3N4o5P6q7R8"]})
        # Assert
        self.assertNotIn("a1B2c3D4", line)


class SweepTest(unittest.TestCase):
    def test_stale_session_transients_are_swept_and_fresh_ones_kept(self):
        import tempfile
        import time
        from pathlib import Path

        from devteam import tasks

        with tempfile.TemporaryDirectory() as raw:
            state, tmpdir = Path(raw, "state"), Path(raw, "tmp")
            state.mkdir()
            tmpdir.mkdir()
            old = time.time() - 48 * 3600
            stale = [state / ".context-shown-s1", state / ".context-hints-s1", state / ".repair-window-s1.json",
                     state / ".repair-window-s1.lock", tmpdir / "devteam-repair-open-s1"]
            for path in stale:
                path.write_text("x")
                os.utime(path, (old, old))
            lock_dir = state / ".context-hints-s1.lock"
            lock_dir.mkdir()
            os.utime(lock_dir, (old, old))
            overlap = tmpdir / "devteam-branch-overlap"
            overlap.mkdir()
            stale.append(overlap / "0cdba6f9edbe2fd00e94")
            stale[-1].write_text("")
            os.utime(stale[-1], (old, old))
            fresh_overlap = overlap / "72ed1136a9448363f7ec"
            fresh_overlap.write_text("")
            fresh = state / ".context-shown-s2"
            fresh.write_text("x")
            other = state / ".repair-ledger.lock"
            other.write_text("x")
            os.utime(other, (old, old))
            saved = os.environ.get("TMPDIR")
            os.environ["TMPDIR"] = str(tmpdir)
            try:
                # Act
                tasks._sweep_session_transients(state, time.time())
            finally:
                if saved is None:
                    os.environ.pop("TMPDIR", None)
                else:
                    os.environ["TMPDIR"] = saved
            # Assert
            for path in stale + [lock_dir]:
                self.assertFalse(path.exists(), path.name)
            self.assertTrue(fresh.exists())
            self.assertTrue(fresh_overlap.exists())
            self.assertTrue(other.exists())


    def test_a_symlinked_sentinel_directory_is_not_followed(self):
        import tempfile
        import time
        from pathlib import Path

        from devteam import tasks

        with tempfile.TemporaryDirectory() as raw:
            state, tmpdir, victim = Path(raw, "state"), Path(raw, "tmp"), Path(raw, "victim")
            for d in (state, tmpdir, victim):
                d.mkdir()
            old = time.time() - 48 * 3600
            precious = victim / "id_rsa"
            precious.write_text("x")
            os.utime(precious, (old, old))
            (tmpdir / "devteam-branch-overlap").symlink_to(victim)
            saved = os.environ.get("TMPDIR")
            os.environ["TMPDIR"] = str(tmpdir)
            try:
                # Act
                tasks._sweep_session_transients(state, time.time())
            finally:
                if saved is None:
                    os.environ.pop("TMPDIR", None)
                else:
                    os.environ["TMPDIR"] = saved
            # Assert
            self.assertTrue(precious.exists())


class ReplayTest(LedgerCase):
    def test_a_known_signature_failing_again_replays_the_delta(self):
        """[spec:repair-ledger#S2]"""
        # Arrange
        self.run_calls([("make build", False), ("FOO=1 make build", True)])
        # Act: a later session
        hints = self.run_calls([("make build", False)], session="sess-later")
        # Assert
        self.assertEqual(len(hints), 1)
        self.assertIn("`make build` failed before", hints[0])
        self.assertIn("set FOO=1", hints[0])

    def test_an_unknown_signature_gets_no_hint(self):
        # Arrange
        self.run_calls([("make build", False), ("FOO=1 make build", True)])
        # Act / Assert
        self.assertEqual(self.run_calls([("make test", False)]), [])

    def test_the_ledger_is_capped_and_drops_the_oldest(self):
        """[spec:repair-ledger#S9]"""
        # Arrange
        seeded = [{"sig": "cmd{}".format(i), "delta": ["set A=1"], "kinds": ["env"], "count": 1,
                   "first_seen": "2020-01-01T00:00:00Z",
                   "last_seen": "2020-01-01T00:{:02d}:{:02d}Z".format(i // 60, i % 60)} for i in range(200)]
        (self.state / repairs.LEDGER_FILE).write_text(json.dumps({"schema": 1, "repairs": seeded}))
        # Act
        self.run_calls([("make build", False), ("FOO=1 make build", True)])
        # Assert
        sigs = [e["sig"] for e in self.ledger()]
        self.assertEqual(len(sigs), repairs.MAX_LEDGER)
        self.assertIn("make build", sigs)
        self.assertNotIn("cmd0", sigs)


class FailOpenTest(LedgerCase):
    def test_a_ledger_this_release_cannot_read_is_left_untouched(self):
        """[spec:repair-ledger#S11]"""
        for label, content in (("corrupt", "{not json"), ("future schema", json.dumps({"schema": 99, "repairs": []}))):
            with self.subTest(ledger=label):
                # Arrange
                path = self.state / repairs.LEDGER_FILE
                path.write_text(content)
                # Act
                hints = self.run_calls([("make build", False), ("FOO=1 make build", True), ("make build", False)])
                # Assert
                self.assertEqual(path.read_text(), content)
                self.assertEqual(hints, [])

    def test_main_swallows_garbage_input(self):
        """[spec:repair-ledger#S11]"""
        import io
        import sys
        # Arrange
        saved = sys.stdin
        sys.stdin = io.StringIO("not json at all")
        self.addCleanup(setattr, sys, "stdin", saved)
        # Act / Assert
        self.assertEqual(repairs.main(["--state-dir", str(self.state), "--session", SESSION]), 0)
        self.assertEqual(repairs.main([]), 0)


class ExitCodeTest(unittest.TestCase):
    def test_the_payload_field_wins_over_text_markers(self):
        # Arrange
        failed_but_text_says_zero = {"tool": "bash", "args": {"command": "x"}, "exit_code": 1, "output": "Exit code 0"}
        ok_but_text_says_failure = {"tool": "bash", "args": {"command": "x"}, "exit_code": 0, "output": "Exit code: 1"}
        # Assert
        self.assertFalse(repairs.classify(failed_but_text_says_zero)[0])
        self.assertTrue(repairs.classify(ok_but_text_says_failure)[0])

    def test_the_text_marker_is_used_when_there_is_no_field(self):
        # Assert
        self.assertFalse(repairs.classify({"tool_response": "Exit code 2\nboom"})[0])
        self.assertTrue(repairs.classify({"tool_response": "all good"})[0])


class MachineLocalTest(unittest.TestCase):
    def test_the_ledger_is_machine_local_and_documented(self):
        """[spec:repair-ledger#S7]"""
        # Assert
        self.assertTrue(paths.is_machine_local_record("repair-ledger.json"))
        self.assertTrue(paths.is_machine_local_record("/some/dir/Repair-Ledger.json"))
        self.assertIn("repair-ledger.json", paths.MACHINE_LOCAL_RECORDS)
        for doc in ("CLAUDE.md", "CLAUDE-md/cli.md", "CLAUDE-md/user-data.md"):
            text = (REPO_ROOT / doc).read_text(encoding="utf-8")
            self.assertIn("repair-ledger.json", text, doc)

    def test_the_working_file_is_dot_prefixed_and_so_machine_local(self):
        # Assert
        self.assertTrue(paths.is_machine_local_record(repairs.WINDOW_PREFIX + "s1.json"))


@requires_bash()
class HookTest(StoreTestCase):
    """03-repair-detect.sh end to end, per provider, with the real python."""

    def setUp(self):
        super().setUp()
        self.repo = make_git_project(self.tmp / "app")
        self.state = self.tmp / "state"
        self.state.mkdir()
        self.tmpdir = self.tmp / "tmpdir"
        self.tmpdir.mkdir()

    def run_hook(self, payload, raw=None):
        env = {"PATH": os.environ["PATH"], "HOME": str(self.tmp), "USER_DATA_DIR": str(self.state),
               "TMPDIR": str(self.tmpdir)}
        result = subprocess.run(["bash", str(HOOK)], input=raw if raw is not None else json.dumps(payload),
                                cwd=str(self.repo), env=env, capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def learn(self, build, session=SESSION, fail="make build", fix="FOO=1 make build"):
        self.run_hook(build(fail, False, session))
        self.run_hook(build(fix, True, session))

    def queued(self, session=SESSION):
        path = self.state / ".context-hints-{}".format(session)
        return path.read_text().splitlines() if path.exists() else []

    def test_each_provider_records_and_then_gets_its_delivery(self):
        """[spec:repair-ledger#S1] [spec:repair-ledger#S2] [spec:repair-ledger#S12] [spec:repair-ledger#S13] [spec:repair-ledger#S14]"""
        for provider, build in SHELL_PAYLOADS.items():
            with self.subTest(provider=provider):
                # Arrange
                for leftover in self.state.iterdir():
                    leftover.unlink()
                self.learn(build, session="learn-" + provider)
                # Act: a different session hits the known failure
                out = self.run_hook(build("make build", False, "later-" + provider))
                # Assert
                self.assertTrue((self.state / repairs.LEDGER_FILE).exists())
                if DELIVERY[provider] == "now":
                    data = json.loads(out)["hookSpecificOutput"]
                    self.assertIn("[DEVTEAM:HINT]", data["additionalContext"])
                    self.assertIn("set FOO=1", data["additionalContext"])
                    self.assertEqual(self.queued("later-" + provider), [])
                else:
                    self.assertEqual(out, "")
                    queued = self.queued("later-" + provider)
                    self.assertEqual(len(queued), 1)
                    self.assertIn("set FOO=1", queued[0])

    def test_the_hint_is_not_repeated_within_a_session(self):
        """[spec:repair-ledger#S8]"""
        for provider, build in SHELL_PAYLOADS.items():
            with self.subTest(provider=provider):
                # Arrange
                for leftover in self.state.iterdir():
                    leftover.unlink()
                self.learn(build, session="a-" + provider)
                session = "b-" + provider
                # Act
                first = self.run_hook(build("make build", False, session))
                second = self.run_hook(build("make build", False, session))
                # Assert
                if DELIVERY[provider] == "now":
                    self.assertTrue(first)
                    self.assertEqual(second, "")
                else:
                    self.assertEqual(len(self.queued(session)), 1)

    def test_queued_repair_hints_obey_the_shared_five_line_cap(self):
        """[spec:repair-ledger#S9]"""
        # Arrange
        seeded = [{"sig": "tool{} go".format(i), "delta": ["set A=1"], "kinds": ["env"], "count": 1,
                   "first_seen": "2020-01-01T00:00:00Z", "last_seen": "2020-01-01T00:00:00Z"} for i in range(7)]
        (self.state / repairs.LEDGER_FILE).write_text(json.dumps({"schema": 1, "repairs": seeded}))
        for i in range(7):
            self.run_hook(_opencode("tool{} go".format(i), False, "cap"))
        self.assertEqual(len(self.queued("cap")), 7)
        # Act
        script = '. "{}"; devteam_hints_init || exit 9; devteam_hints_drain cap'.format(CONTEXT_HINTS)
        env = {"PATH": os.environ["PATH"], "HOME": str(self.tmp), "USER_DATA_DIR": str(self.state)}
        drained = subprocess.run(["bash", "-c", script], cwd=str(self.repo), env=env, capture_output=True, text=True)
        # Assert
        self.assertEqual(len(drained.stdout.splitlines()), 5)
        self.assertEqual(len(self.queued("cap")), 2)

    def test_the_opt_out_records_and_delivers_nothing(self):
        """[spec:repair-ledger#S10]"""
        # Arrange
        prefs = self.repo / ".dev-team-agents" / "resolved" / "preferences.json"
        prefs.parent.mkdir(parents=True)
        prefs.write_text(json.dumps({"repair_hints_active": False}))
        for provider, build in SHELL_PAYLOADS.items():
            with self.subTest(provider=provider):
                # Act
                self.learn(build, session="off-" + provider)
                out = self.run_hook(build("make build", False, "off2-" + provider))
                # Assert
                self.assertEqual(out, "")
                self.assertFalse((self.state / repairs.LEDGER_FILE).exists())
                self.assertEqual(self.queued("off2-" + provider), [])

    def test_the_opt_out_does_not_stop_a_default_true_project(self):
        """[spec:repair-ledger#S10]"""
        # Arrange
        prefs = self.repo / ".dev-team-agents" / "resolved" / "preferences.json"
        prefs.parent.mkdir(parents=True)
        prefs.write_text(json.dumps({"repair_hints_active": True}))
        # Act
        self.learn(_claude)
        # Assert
        self.assertTrue((self.state / repairs.LEDGER_FILE).exists())

    def test_the_hook_exits_zero_and_stays_silent_on_bad_input(self):
        """[spec:repair-ledger#S11]"""
        # Arrange: a directory where the ledger should be, plus assorted garbage
        (self.state / repairs.LEDGER_FILE).mkdir()
        # Act / Assert
        for raw in ("", "{broken", '{"tool_name": "Bash"}', "x" * 5000):
            self.assertEqual(self.run_hook(None, raw=raw), "")
        self.assertEqual(self.run_hook(_claude("make build", False)), "")
        self.assertEqual(self.run_hook(_claude("make build", True)), "")

    def test_an_unreadable_ledger_is_left_untouched_by_the_hook(self):
        """[spec:repair-ledger#S11]"""
        # Arrange
        path = self.state / repairs.LEDGER_FILE
        path.write_text("{corrupt")
        # Act
        self.learn(_claude)
        out = self.run_hook(_claude("make build", False, "other"))
        # Assert
        self.assertEqual(path.read_text(), "{corrupt")
        self.assertEqual(out, "")


if __name__ == "__main__":
    unittest.main()
