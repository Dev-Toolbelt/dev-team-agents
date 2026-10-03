"""`devteam auth` security properties: no secret in any output or file, the session store, the
refresh lock, the test seam and the telemetry separation (ADR-0029 SR-8, 9, 16-18, 41, 44)."""

from __future__ import annotations

import argparse
import os
import re
import sys
import threading
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

from auth_support import CODE, EMAIL, NEW_PASSWORD, PASSWORD, AuthTestCase  # noqa: E402
from devteam_support import requires_posix_modes  # noqa: E402

from devteam import auth_gotrue as gotrue  # noqa: E402
from devteam import auth_session  # noqa: E402
from devteam import cli as devteam_cli  # noqa: E402
from devteam import entitlement  # noqa: E402
from devteam import secrets as secrets_module  # noqa: E402
from test_json_contract import discover_commands  # noqa: E402

LIB = Path(__file__).resolve().parent.parent / "scripts" / "lib" / "devteam"
SECRETS = ("SENTINEL-ACCESS", "SENTINEL-REFRESH", PASSWORD, NEW_PASSWORD, "pw-SENTINEL-wrong-one", CODE)


class NoSecretOnTheCommandLineTest(unittest.TestCase):
    def test_no_auth_option_accepts_a_code_a_password_or_a_token(self):
        parser = devteam_cli.build_parser()
        leaves, _ = discover_commands(parser)
        allowed_values = {"--email", "--name", "--new", "--client-schemas"}
        seen = set()

        def node_for(path):
            node = parser
            for word in path:
                action = next(a for a in node._actions if isinstance(a, argparse._SubParsersAction))
                node = action.choices[word]
            return node

        for path in leaves:
            if path[0] != "auth":
                continue
            for action in node_for(path)._actions:
                for flag in action.option_strings:
                    seen.add(flag)
                    if action.nargs != 0 and not isinstance(action, argparse._HelpAction):
                        self.assertIn(flag, allowed_values, "{} {} takes a value".format(" ".join(path), flag))
        self.assertIn("--password", seen)

    def test_password_is_a_switch_not_a_value(self):
        parser = devteam_cli.build_parser()
        with self.assertRaises(Exception):
            parser.parse_args(["auth", "login", "--email", EMAIL, "--password", PASSWORD])


class NoSecretInAnyOutputTest(AuthTestCase):
    def assert_clean(self, text, where):
        for secret in SECRETS:
            self.assertNotIn(secret, text, "{} leaked {!r}".format(where, secret))

    def test_every_auth_subcommand_in_success_and_failure(self):
        self.idp.add_user("known@example.com")
        # success paths
        self.sign_in()
        self.run_auth("auth", "status")
        self.run_auth("auth", "check")
        self.run_auth("auth", "profile")
        self.run_auth("auth", "profile", "update", "--name", "Ada")
        self.run_auth("auth", "profile", "identities")
        self.run_auth("auth", "password", "change", input_text=PASSWORD + "\n" + NEW_PASSWORD + "\n")
        self.run_auth("auth", "logout")
        self.run_auth("auth", "login", "--email", "known@example.com", "--password", input_text=PASSWORD + "\n")
        self.run_auth("auth", "logout")
        self.run_auth("auth", "password", "reset", "--email", "known@example.com", "--send-code")
        self.run_auth("auth", "password", "reset", "--email", "known@example.com", "--finish", input_text=CODE + "\n" + NEW_PASSWORD + "\n")
        self.run_auth("auth", "delete", "--send-code")
        self.run_auth("auth", "delete", "--yes", input_text=CODE + "\n")
        # failure paths
        self.run_auth("auth", "login", "--email", EMAIL, "--password", input_text="pw-SENTINEL-wrong-one\n")
        self.run_auth("auth", "otp", "verify", "--email", EMAIL, input_text="99999999\n")
        self.run_auth("auth", "password", "change", input_text=PASSWORD + "\n" + NEW_PASSWORD + "\n")
        self.idp.limited.add("/auth/v1/otp")
        self.run_auth("auth", "otp", "start", "--email", EMAIL)
        self.idp.limited.clear()
        self.idp.down = True
        for argv in (["auth", "status"], ["auth", "check"], ["auth", "logout"], ["auth", "otp", "start", "--email", EMAIL]):
            self.run_auth(*argv)
            self.run_auth(*argv, "--json")
        self.assertTrue(self.outputs)
        self.assert_clean("\n".join(self.outputs), "an output")

    def test_no_file_in_the_store_holds_a_token_outside_the_secret_backend(self):
        self.sign_in()
        self.run_auth("auth", "password", "change", input_text=PASSWORD + "\n" + NEW_PASSWORD + "\n")
        self.run_auth("auth", "status")
        holders = []
        for rel, raw in self.store_files().items():
            text = raw.decode("utf-8", "replace")
            for secret in SECRETS:
                if secret in text:
                    holders.append((rel, secret))
        self.assertEqual({rel.replace(os.sep, "/").rsplit("/", 1)[-1] for rel, _ in holders}, {"insecure.json"})
        self.assertEqual({secret for _, secret in holders}, {"SENTINEL-REFRESH"})
        self.assertFalse(any("SENTINEL-ACCESS" in raw.decode("utf-8", "replace") for raw in self.store_files().values()))

    def test_the_audit_log_and_notifications_carry_nothing(self):
        self.sign_in()
        for rel, raw in self.store_files().items():
            if rel.endswith("audit.log") or rel.endswith("notifications.jsonl"):
                self.assert_clean(raw.decode("utf-8", "replace"), rel)


class SessionStorageTest(AuthTestCase):
    def test_the_insecure_backend_is_named_in_text_and_in_json(self):
        body = self.sign_in()
        self.assertEqual(body["secret_backend"], "insecure")
        self.assertTrue(body["secret_backend_insecure"])
        self.assertTrue(any("plain file" in w for w in body["warnings"]))
        code, out, _ = self.run_auth("auth", "status", "--offline")
        self.assertIn("warning: the session is stored in a plain file", out)
        code, body, _ = self.run_json("auth", "status", "--offline")
        self.assertEqual(body["secret_backend"], "insecure")

    @requires_posix_modes
    def test_the_fallback_file_is_mode_0600(self):
        self.sign_in()
        path = next(Path(self.home).rglob("insecure.json"))
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_an_os_keychain_holds_the_token_and_nothing_else_does(self):
        vault = {}
        patches = (
            mock.patch.object(secrets_module, "default_backend", lambda: "keychain"),
            mock.patch.object(secrets_module, "available_backends", lambda: ["keychain", "insecure"]),
            mock.patch.dict(secrets_module._PUT, {"keychain": lambda ref, value: vault.__setitem__(ref, value)}),
            mock.patch.dict(secrets_module._GET, {"keychain": lambda ref: vault.get(ref)}),
            mock.patch.dict(secrets_module._DELETE, {"keychain": lambda ref: vault.pop(ref, None) is not None}),
        )
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)
        code, out, _ = self.run_inproc(["auth", "otp", "start", "--email", EMAIL, "--json"])
        self.assertEqual(code, 0)
        code, out, _ = self.run_inproc(["auth", "otp", "verify", "--email", EMAIL, "--json"], CODE + "\n")
        self.assertEqual(code, 0, out)
        self.assertIn("keychain", out)
        self.assertIn('"secret_backend_insecure": false', out)
        self.assertNotIn("plain file", out)
        self.assertTrue(vault["account.session.refresh_token"].startswith("SENTINEL-REFRESH"))
        self.assertFalse(any(b"SENTINEL-REFRESH" in raw for raw in self.store_files().values()))
        code, out, _ = self.run_inproc(["auth", "logout", "--json"])
        self.assertEqual(code, 0)
        self.assertEqual(vault, {})


class RefreshLockTest(AuthTestCase):
    def test_two_threads_share_one_token_exchange(self):
        self.sign_in()
        identity = entitlement.load_identity()
        client = gotrue.Client(identity)
        self.idp.refresh_delay = 0.4
        results, errors = [], []

        def work():
            try:
                results.append(auth_session.access_token(client))
            except Exception as exc:  # noqa: BLE001
                errors.append(exc)

        threads = [threading.Thread(target=work) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(20)
        self.assertEqual(errors, [])
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0], results[1])
        self.assertEqual(self.idp.refresh_exchanges, 1)
        self.assertEqual(self.idp.reuse_events, 0)

    def test_two_processes_each_succeed_without_presenting_a_rotated_token_twice(self):
        self.sign_in()
        self.idp.refresh_delay = 0.4
        procs = [self.popen("auth", "profile", "show", "--json") for _ in range(2)]
        codes = []
        for proc in procs:
            out, err = proc.communicate(timeout=60)
            codes.append(proc.returncode)
            self.outputs.append(out.decode() + err.decode())
        self.assertEqual(codes, [0, 0])
        self.assertEqual(self.idp.reuse_events, 0, "reuse detection fired: the lock did not serialise the refresh")
        self.assertEqual(self.idp.refresh_exchanges, 2)
        # The second process read the rotated token the first had stored.
        self.assertEqual(len(self.idp.refresh), 3)

    def test_the_session_survives_many_sequential_refreshes(self):
        self.sign_in()
        for _ in range(3):
            code, body, _ = self.run_json("auth", "profile")
            self.assertEqual(code, 0, body)
        self.assertEqual(self.idp.reuse_events, 0)

    def test_the_lock_is_taken_around_the_refresh(self):
        self.sign_in()
        taken = []
        real = auth_session.store_lock

        def spy(name, timeout=15.0):
            taken.append(name)
            return real(name, timeout=timeout)

        client = gotrue.Client(entitlement.load_identity())
        with mock.patch.object(auth_session, "store_lock", spy):
            auth_session.access_token(client)
        self.assertIn(auth_session.LOCK_NAME, taken)


class TestSeamTest(AuthTestCase):
    def test_a_seam_with_a_remote_url_is_refused(self):
        # Refused means never used: the seam is ignored (with a warning) and the compiled
        # identity stays in force, so a stray variable can neither redirect the CLI nor make
        # every command fail.
        for url in ("https://evil.example.com", "http://evil.example.com", "http://192.168.0.5:9"):
            os.environ["DEVTEAM_AUTH_TEST_URL"] = url
            code, body, err = self.run_json("auth", "status")
            self.assertEqual(code, 0, url)
            self.assertFalse(body["test_seam"], url)
            self.assertIn("test seam ignored", err)
            self.assertEqual(self.idp.calls, [])

    def test_a_seam_key_must_carry_the_test_prefix(self):
        os.environ["DEVTEAM_AUTH_TEST_KID"] = "prod-1"
        code, body, err = self.run_json("auth", "status")
        self.assertEqual(code, 0)
        self.assertFalse(body["test_seam"])
        self.assertIn("test seam ignored", err)
        self.assertEqual(self.idp.calls, [])

    def test_an_active_seam_warns_on_stderr_and_reports_itself(self):
        code, body, err = self.run_json("auth", "status")
        self.assertEqual(code, 0)
        self.assertTrue(body["test_seam"])
        self.assertIn("test seam active", err)
        self.assertEqual(len([line for line in err.splitlines() if "test seam" in line]), 1)

    def test_without_the_seam_nothing_points_the_cli_at_another_server(self):
        for key in ("DEVTEAM_AUTH_TEST_URL", "DEVTEAM_AUTH_TEST_KID", "DEVTEAM_AUTH_TEST_PUBKEY"):
            os.environ.pop(key)
        remote = {
            "SUPABASE_URL": self.idp.url,
            "DEVTEAM_SUPABASE_URL": self.idp.url,
            "DEVTEAM_AUTH_URL": self.idp.url,
            "DEVTEAM_AUTH_ENVIRONMENT": "dev",
        }
        self.addCleanup(lambda: [os.environ.pop(k, None) for k in remote])
        os.environ.update(remote)
        code, body, err = self.run_json("auth", "otp", "start", "--email", EMAIL)
        self.assertEqual(code, 3)
        self.assertEqual(body["details"]["reason"], "not_configured")
        self.assertNotIn("test seam", err)
        self.assertEqual(self.idp.calls, [])


class TelemetrySeparationTest(AuthTestCase):
    def test_no_auth_module_touches_telemetry_and_no_module_imports_auth_but_the_cli(self):
        auth_files = sorted(LIB.glob("auth*.py")) + [LIB / "entitlement.py", LIB / "ed25519.py"]
        self.assertGreaterEqual(len(auth_files), 6)
        for path in auth_files:
            code = "\n".join(
                line for line in path.read_text().splitlines() if line.lstrip().startswith(("import ", "from "))
            )
            self.assertNotIn("telemetry", code.lower(), path.name)
        pattern = re.compile(r"^\s*(from \. import .*\bauth\w*\b|from \.auth\w* import|import auth)", re.M)
        for path in LIB.glob("*.py"):
            if path.name == "cli.py" or path.name.startswith("auth"):
                continue
            self.assertIsNone(pattern.search(path.read_text()), "{} imports the auth modules".format(path.name))

    def test_the_telemetry_payload_has_no_account_field(self):
        # SR-41 from the other side: the event the telemetry sender builds, and every call
        # that feeds it properties, name nothing that identifies an account.
        root = LIB.parent.parent.parent
        sender = (root / "scripts" / "helpers" / "telemetry-send.sh").read_text(encoding="utf-8")
        forbidden = ("account", "email", "entitlement", "auth-session", '"sub"', "user_id")
        for word in forbidden:
            self.assertNotIn(word, sender.lower(), word)
        callers = [p for p in (root / "scripts").rglob("*.sh") if p.name != "telemetry-send.sh"]
        call = re.compile(r"telemetry-send\.sh[^\n]*")
        for path in callers:
            for line in call.findall(path.read_text(encoding="utf-8", errors="replace")):
                for word in forbidden:
                    self.assertNotIn(word, line.lower(), "{}: {}".format(path.name, line))

    def test_requests_carry_no_identifier_beyond_the_project_key(self):
        self.sign_in()
        allowed = {
            "accept", "accept-encoding", "authorization", "apikey", "connection", "content-length",
            "content-type", "host", "user-agent",
        }
        for call in self.idp.calls:
            self.assertLessEqual(set(call["header_names"]), allowed, call["path"])
            self.assertEqual(call["user_agent"], "devteam-cli")


if __name__ == "__main__":
    unittest.main()
