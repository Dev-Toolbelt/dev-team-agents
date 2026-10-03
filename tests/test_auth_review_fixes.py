"""Regressions for the accounts review: refresh backoff, error mapping, sign-up and reset edges."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from auth_support import EMAIL, PASSWORD, AuthTestCase  # noqa: E402

from devteam import auth_session as session  # noqa: E402
from devteam import entitlement  # noqa: E402


class RefreshBackoffTest(unittest.TestCase):
    """A failed online attempt backs off whatever the cached status (review: QA MAJOR-1)."""

    META = {"account_id": "u", "last_online_check": 1000}

    def test_a_recent_failed_attempt_suppresses_the_check_for_every_status(self):
        now = 5000.0
        meta = dict(self.META, last_online_attempt=int(now) - 1)
        for status in entitlement.STATUSES:
            with self.subTest(status=status):
                result = entitlement.EntitlementResult(status=status)
                self.assertFalse(session.should_refresh(result, meta, now=now))

    def test_after_the_backoff_a_lapsed_license_is_checked_again(self):
        now = 5000.0 + session.RETRY_AFTER_FAILURE_SECONDS
        meta = dict(self.META, last_online_attempt=5000)
        for status in (entitlement.STATUS_NEEDS_ONLINE_CHECK, entitlement.STATUS_INVALID):
            with self.subTest(status=status):
                result = entitlement.EntitlementResult(status=status)
                self.assertTrue(session.should_refresh(result, meta, now=now))


class ServerRefusalKeepsTheSessionTest(AuthTestCase):
    """Only a dead refresh token or a 401 ends the session (review: code MAJOR-2, security L4)."""

    def _force_online_check(self):
        session.update_meta(last_online_check=0, last_online_attempt=None)

    def test_a_missing_entitlement_function_does_not_sign_the_user_out(self):
        self.sign_in()
        for status in (404, 403, 405, 400):
            with self.subTest(status=status):
                self.idp.forced["/functions/v1/entitlement"] = (status, {"error": "nope"})
                self._force_online_check()
                code, body, _ = self.run_json("auth", "status")
                self.assertEqual(code, 0, body)
                self.assertTrue(body["signed_in"], status)
                self.assertEqual(body["online"]["reason"], "server_refused")

    def test_a_401_from_the_entitlement_function_ends_the_session(self):
        self.sign_in()
        self.idp.forced["/functions/v1/entitlement"] = (401, {"error": "unauthorized"})
        session._forget_memory()
        self._force_online_check()
        code, body, _ = self.run_json("auth", "status")
        self.assertEqual(code, 0, body)
        self.assertFalse(body["signed_in"])


class SignUpAndResetEdgesTest(AuthTestCase):
    def test_a_weak_password_is_reported_not_hidden_behind_code_sent(self):
        self.idp.forced["/auth/v1/signup"] = (422, {"error_code": "weak_password", "msg": "weak"})
        code, body, _ = self.run_json(
            "auth", "login", "--email", EMAIL, "--password", "--signup", "--send-code",
            input_text=PASSWORD + "\n",
        )
        self.assertEqual(code, 1, body)
        self.assertEqual(body["details"]["reason"], "weak_password")
        self.assertNotIn("sent", body)

    def test_a_throttled_recovery_request_answers_like_a_sent_one(self):
        # GoTrue throttles /recover only for registered addresses; a 429 would reveal one.
        self.idp.limited.add("/auth/v1/recover")
        code, body, _ = self.run_json("auth", "password", "reset", "--email", EMAIL, "--send-code")
        self.assertEqual(code, 0, body)
        self.assertTrue(body["sent"])


class LogoutTest(AuthTestCase):
    def test_logout_on_a_fresh_machine_creates_nothing(self):
        before = self.store_files()
        code, body, _ = self.run_json("auth", "logout")
        self.assertEqual(code, 0, body)
        self.assertEqual(self.store_files(), before)

    def test_logout_holds_the_session_lock(self):
        self.sign_in()
        taken = []
        original = session.store_lock

        def spy(name, timeout=None):
            taken.append(name)
            return original(name, timeout=timeout)

        session.store_lock = spy
        try:
            session.clear_local()
        finally:
            session.store_lock = original
        self.assertIn(session.LOCK_NAME, taken)
        self.assertIsNone(session.read_meta())


class NoticeOnlyAtATerminalTest(unittest.TestCase):
    def test_the_warn_notice_is_shown_to_a_terminal_and_never_written_down(self):
        import io

        from devteam import auth_gate as gate
        from devteam.output import Emitter

        class Tty(io.StringIO):
            def isatty(self):
                return True

        captured, terminal = io.StringIO(), Tty()
        gate._notice(Emitter(as_json=True, stdout=io.StringIO(), stderr=captured), "hello")
        gate._notice(Emitter(as_json=True, stdout=io.StringIO(), stderr=terminal), "hello")
        self.assertEqual(captured.getvalue(), "")
        self.assertIn("hello", terminal.getvalue())

class ProfileAndPasswordEdgesTest(AuthTestCase):
    def test_a_rename_that_matched_no_row_is_not_reported_as_done(self):
        from devteam import auth_gotrue as gotrue
        from devteam.auth_gotrue import Rejected

        self.sign_in()
        client = gotrue.Client(entitlement.load_identity())
        access = session.access_token(client)
        with self.assertRaises(Rejected):
            client.profile_set_name(access, "00000000-0000-0000-0000-000000000000", "Someone")

    def test_a_refused_new_password_ends_the_recovery_session(self):
        self.idp.add_user(EMAIL)
        code, body, _ = self.run_json("auth", "password", "reset", "--email", EMAIL, "--send-code")
        self.assertEqual(code, 0, body)
        self.idp.forced["/auth/v1/user"] = (422, {"error_code": "same_password"})
        code, body, _ = self.run_json(
            "auth", "password", "reset", "--email", EMAIL, "--finish",
            input_text="24681357\n" + "a-brand-new-password\n",
        )
        self.assertEqual(code, 1, body)
        self.assertEqual(body["details"]["reason"], "password_rejected")
        self.assertTrue(self.idp.logouts, "the recovery session must be revoked")


if __name__ == "__main__":
    unittest.main()
