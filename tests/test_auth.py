"""`devteam auth`: sign-in flows, passwords, profile, deletion, logout and the license gate answer.

Run against a fake GoTrue and fake Edge Functions on loopback (`auth_fakes.py`) through the
ADR-0029 test seam, with a throwaway Ed25519 key. Browser sign-in, the secret-hygiene sweep and
session concurrency live in `test_auth_oauth.py` and `test_auth_security.py`.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from auth_support import CODE, EMAIL, NEW_PASSWORD, PASSWORD, AuthTestCase  # noqa: E402

from devteam import auth_gotrue as gotrue  # noqa: E402
from devteam.errors import UsageError  # noqa: E402


class OtpSignInTest(AuthTestCase):
    def test_otp_signs_in_and_fetches_the_license(self):
        body = self.sign_in(name="Ada")
        self.assertTrue(body["signed_in"])
        self.assertEqual(body["account"]["email"], EMAIL)
        self.assertEqual(body["method"], "email-otp")
        self.assertTrue(body["entitled"])
        self.assertEqual(body["entitlement"]["status"], "active")
        self.assertEqual(self.idp.entitlement_calls, 1)
        self.assertEqual(self.idp.users[EMAIL]["display_name"], "Ada")

    def test_session_survives_into_an_offline_status(self):
        self.sign_in()
        before = len(self.idp.calls)
        code, body, _ = self.run_json("auth", "status", "--offline")
        self.assertEqual(code, 0)
        self.assertTrue(body["signed_in"] and body["entitled"])
        self.assertEqual(len(self.idp.calls), before, "--offline touched the network")

    def test_login_email_sends_then_reads_the_code_from_stdin(self):
        code, body, _ = self.run_json("auth", "login", "--email", EMAIL, input_text=CODE + "\n")
        self.assertEqual(code, 0, body)
        self.assertEqual(body["account"]["email"], EMAIL)

    def test_start_answers_identically_for_every_kind_of_address(self):
        self.idp.add_user("known@example.com")
        self.idp.add_user("unconfirmed@example.com", confirmed=False)
        self.idp.add_user("banned@example.com", banned=True)
        results = []
        for address in ("known@example.com", "unconfirmed@example.com", "banned@example.com", "nobody@example.com"):
            code, out, _err = self.run_auth("auth", "otp", "start", "--email", address, "--json")
            results.append((code, out))
        self.assertEqual(len(set(results)), 1, results)
        self.assertEqual(results[0][0], 0)

    def test_a_start_the_server_refuses_still_looks_sent(self):
        self.idp.add_user("banned@example.com", banned=True)
        code, body, _ = self.run_json("auth", "otp", "start", "--email", "banned@example.com")
        self.assertEqual(code, 0)
        self.assertTrue(body["sent"])

    def test_wrong_code_is_one_generic_rejection(self):
        self.run_json("auth", "otp", "start", "--email", EMAIL)
        code, body, _ = self.run_json("auth", "otp", "verify", "--email", EMAIL, input_text="11111111\n")
        self.assertEqual(code, 1)
        self.assertEqual(body["error"], "the code is invalid or has expired")
        self.assertEqual(body["details"]["reason"], "invalid_code")
        code, body, _ = self.run_json("auth", "otp", "verify", "--email", "nobody@example.com", input_text="11111111\n")
        self.assertEqual((code, body["error"]), (1, "the code is invalid or has expired"))

    def test_a_code_that_is_not_eight_digits_is_a_usage_error_with_no_request(self):
        before = len(self.idp.calls)
        code, body, _ = self.run_json("auth", "otp", "verify", "--email", EMAIL, input_text="1234567\n")
        self.assertEqual(code, 2)
        self.assertEqual(len(self.idp.calls), before)

    def test_rate_limit_is_its_own_error_and_is_never_retried(self):
        self.idp.limited.add("/auth/v1/otp")
        code, body, _ = self.run_json("auth", "otp", "start", "--email", EMAIL)
        self.assertEqual(code, 3)
        self.assertEqual(body["details"]["reason"], "rate_limited")
        self.assertEqual(body["details"]["retry_after"], 7)
        self.assertEqual(len(self.idp.calls_to("/auth/v1/otp")), 1)

    def test_an_unreachable_server_is_an_environment_error(self):
        self.idp.down = True
        code, body, _ = self.run_json("auth", "otp", "start", "--email", EMAIL)
        self.assertEqual(code, 3)
        self.assertEqual(body["details"]["reason"], "unreachable")

    def test_login_needs_a_method(self):
        code, body, _ = self.run_json("auth", "login")
        self.assertEqual(code, 2)

    def test_an_unconfigured_build_refuses_with_a_clear_reason(self):
        for key in ("DEVTEAM_AUTH_TEST_URL", "DEVTEAM_AUTH_TEST_KID", "DEVTEAM_AUTH_TEST_PUBKEY"):
            import os

            os.environ.pop(key)
        code, body, _ = self.run_json("auth", "otp", "start", "--email", EMAIL)
        self.assertEqual(code, 3)
        self.assertEqual(body["details"]["reason"], "not_configured")
        self.assertEqual(self.idp.calls, [])


class PasswordSignInTest(AuthTestCase):
    def test_sign_up_confirms_with_a_code_then_signs_in(self):
        code, body, _ = self.run_json(
            "auth", "login", "--email", EMAIL, "--password", "--signup", input_text=PASSWORD + "\n" + CODE + "\n"
        )
        self.assertEqual(code, 0, body)
        self.assertEqual(body["method"], "password-signup")
        self.run_json("auth", "logout")
        code, body, _ = self.run_json("auth", "login", "--email", EMAIL, "--password", input_text=PASSWORD + "\n")
        self.assertEqual((code, body["method"]), (0, "password"))

    def test_every_failed_sign_in_is_the_same_generic_answer(self):
        self.idp.add_user("known@example.com")
        self.idp.add_user("unconfirmed@example.com", confirmed=False)
        answers = set()
        for address, secret in (
            ("known@example.com", "pw-SENTINEL-wrong-one"),
            ("unconfirmed@example.com", PASSWORD),
            ("nobody@example.com", PASSWORD),
        ):
            code, out, _err = self.run_auth(
                "auth", "login", "--email", address, "--password", "--json", input_text=secret + "\n"
            )
            self.assertEqual(code, 1)
            answers.add(out)
        self.assertEqual(len(answers), 1)
        self.assertEqual(json.loads(answers.pop())["error"], "invalid credentials")

    def test_password_is_sent_normalised_to_nfc(self):
        decomposed = "e\u0301" * 6 + "-SENTINEL-pw"
        self.run_json("auth", "login", "--email", EMAIL, "--password", "--signup", input_text=decomposed + "\n" + CODE + "\n")
        sent = self.idp.calls_to("/auth/v1/signup")[0]["body"]["password"]
        self.assertEqual(sent, "\u00e9" * 6 + "-SENTINEL-pw")

    def test_a_weak_password_is_refused_before_any_request(self):
        code, body, _ = self.run_json(
            "auth", "login", "--email", EMAIL, "--password", "--signup", input_text="short\n" + CODE + "\n"
        )
        self.assertEqual(code, 2)
        self.assertEqual(self.idp.calls, [])

    def test_signup_flag_needs_password(self):
        code, _body, _ = self.run_json("auth", "login", "--email", EMAIL, "--signup")
        self.assertEqual(code, 2)


class PasswordPolicyTest(unittest.TestCase):
    """SR-15: 10 to 64 characters and at most 72 UTF-8 bytes, after NFC."""

    def accepts(self, text):
        return gotrue.validate_new_password(text)

    def rejects(self, text):
        with self.assertRaises(UsageError):
            gotrue.validate_new_password(text)

    def test_character_boundaries(self):
        self.rejects("a" * 9)
        self.accepts("a" * 10)
        self.accepts("a" * 64)
        self.rejects("a" * 65)

    def test_byte_boundary_with_multibyte_input(self):
        self.accepts("\u00e9" * 36)  # 36 characters, exactly 72 bytes
        self.rejects("\u00e9" * 37)  # 74 bytes
        self.accepts("a" * 34 + "\u00e9" * 19)  # 34 + 38 = 72 bytes
        self.rejects("a" * 35 + "\u00e9" * 19)  # 73 bytes

    def test_length_is_counted_after_normalisation(self):
        self.rejects("e\u0301" * 5)  # ten code points, five once composed
        self.assertEqual(self.accepts("e\u0301" * 10), "\u00e9" * 10)

    def test_no_composition_rules(self):
        self.accepts("aaaaaaaaaa")


class ResetAndChangeTest(AuthTestCase):
    def setUp(self):
        super().setUp()
        self.idp.add_user(EMAIL)

    def test_reset_sends_a_code_then_finishes_and_revokes_the_other_sessions(self):
        code, body, _ = self.run_json("auth", "password", "reset", "--email", EMAIL, "--send-code")
        self.assertEqual((code, body["sent"]), (0, True))
        code, body, _ = self.run_json(
            "auth", "password", "reset", "--email", EMAIL, "--finish", input_text=CODE + "\n" + NEW_PASSWORD + "\n"
        )
        self.assertEqual(code, 0, body)
        self.assertTrue(body["other_sessions_revoked"])
        self.assertIn("others", self.idp.logouts)
        self.assertEqual(self.idp.users[EMAIL]["password"], NEW_PASSWORD)
        self.assertTrue(body["signed_in"])

    def test_reset_answers_identically_whether_or_not_the_address_exists(self):
        outs = {
            self.run_auth("auth", "password", "reset", "--email", address, "--send-code", "--json")
            for address in (EMAIL, "nobody@example.com")
        }
        self.assertEqual(len({(code, out) for code, out, _ in outs}), 1)

    def test_a_weak_new_password_never_reaches_the_server(self):
        self.run_json("auth", "password", "reset", "--email", EMAIL, "--send-code")
        before = len(self.idp.calls)
        code, _body, _ = self.run_json(
            "auth", "password", "reset", "--email", EMAIL, "--finish", input_text=CODE + "\nshort\n"
        )
        self.assertEqual(code, 2)
        self.assertEqual(len(self.idp.calls), before)

    def test_a_wrong_recovery_code_is_the_generic_rejection(self):
        self.run_json("auth", "password", "reset", "--email", EMAIL, "--send-code")
        code, body, _ = self.run_json(
            "auth", "password", "reset", "--email", EMAIL, "--finish", input_text="00000000\n" + NEW_PASSWORD + "\n"
        )
        self.assertEqual((code, body["details"]["reason"]), (1, "invalid_code"))

    def test_change_needs_the_current_password_and_revokes_the_others(self):
        self.sign_in()
        code, body, _ = self.run_json(
            "auth", "password", "change", input_text="pw-SENTINEL-wrong-one\n" + NEW_PASSWORD + "\n"
        )
        self.assertEqual(code, 1)
        code, body, _ = self.run_json(
            "auth", "password", "change", input_text=PASSWORD + "\n" + NEW_PASSWORD + "\n"
        )
        self.assertEqual(code, 0, body)
        self.assertEqual(self.idp.users[EMAIL]["password"], NEW_PASSWORD)
        self.assertIn("others", self.idp.logouts)
        code, body, _ = self.run_json("auth", "status", "--offline")
        self.assertTrue(body["signed_in"])

    def test_change_signed_out_is_refused(self):
        code, body, _ = self.run_json("auth", "password", "change", input_text=PASSWORD + "\n" + NEW_PASSWORD + "\n")
        self.assertEqual((code, body["details"]["reason"]), (1, "not_signed_in"))


class ProfileTest(AuthTestCase):
    def test_show_update_and_identities(self):
        self.sign_in(name="Ada")
        code, body, _ = self.run_json("auth", "profile")
        self.assertEqual(code, 0)
        self.assertEqual(body["account"]["email"], EMAIL)
        self.assertEqual(body["account"]["display_name"], "Ada")
        code, body, _ = self.run_json("auth", "profile", "update", "--name", "Ada Lovelace")
        self.assertEqual(code, 0)
        self.assertEqual(self.idp.users[EMAIL]["display_name"], "Ada Lovelace")
        self.assertEqual(self.session_meta()["display_name"], "Ada Lovelace")
        code, body, _ = self.run_json("auth", "profile", "identities")
        self.assertEqual([i["provider"] for i in body["identities"]], ["email"])

    def test_update_only_writes_the_display_name_column(self):
        self.sign_in()
        self.run_json("auth", "profile", "update", "--name", "Ada")
        patch = [c for c in self.idp.calls if c["method"] == "PATCH"][0]
        self.assertEqual(set(patch["body"]), {"display_name"})

    def test_a_bad_display_name_is_a_usage_error(self):
        self.sign_in()
        code, _body, _ = self.run_json("auth", "profile", "update", "--name", "x" * 81)
        self.assertEqual(code, 2)

    def test_email_change_asks_for_codes_from_both_addresses(self):
        self.sign_in()
        code, body, _ = self.run_json("auth", "profile", "email", "--new", "ada.new@example.com")
        self.assertEqual((code, body["sent"]), (0, True))
        code, body, _ = self.run_json(
            "auth", "profile", "email", "--new", "ada.new@example.com", "--confirm", input_text=CODE + "\n" + CODE + "\n"
        )
        self.assertEqual(code, 0, body)
        self.assertTrue(body["confirmed"])
        self.assertEqual(self.session_meta()["email"], "ada.new@example.com")

    def test_email_change_with_one_code_stays_pending(self):
        self.sign_in()
        self.run_json("auth", "profile", "email", "--new", "ada.new@example.com")
        code, body, _ = self.run_json(
            "auth", "profile", "email", "--new", "ada.new@example.com", "--confirm", input_text=CODE + "\n\n"
        )
        self.assertEqual(code, 0)
        self.assertFalse(body["confirmed"])
        self.assertEqual(self.session_meta()["email"], EMAIL)

    def test_the_last_identity_cannot_be_unlinked(self):
        self.sign_in()
        self.idp.users[EMAIL]["identities"].append({"identity_id": "11111111-aaaa", "provider": "github", "email": EMAIL})
        code, body, _ = self.run_json("auth", "profile", "unlink", "--github")
        self.assertEqual(code, 0, body)
        code, body, _ = self.run_json("auth", "profile", "unlink", "--google")
        self.assertEqual(code, 2)  # google was never linked
        code, body, _ = self.run_json("auth", "profile", "identities")
        self.assertEqual(len(body["identities"]), 1)
        self.idp.users[EMAIL]["identities"][0]["provider"] = "google"
        code, body, _ = self.run_json("auth", "profile", "unlink", "--google")
        self.assertEqual((code, body["details"]["reason"]), (1, "last_identity"))
        self.assertEqual(len(self.idp.users[EMAIL]["identities"]), 1)


class DeleteTest(AuthTestCase):
    def test_delete_reauthenticates_with_a_fresh_code_and_clears_the_session(self):
        self.sign_in()
        login_bearer = self.idp.calls_to("/functions/v1/entitlement")[0]["bearer"]
        code, body, _ = self.run_json("auth", "delete", "--send-code")
        self.assertEqual((code, body["sent"]), (0, True))
        code, body, _ = self.run_json("auth", "delete", "--yes", input_text=CODE + "\n")
        self.assertEqual(code, 0, body)
        self.assertEqual(self.idp.deleted, [EMAIL])
        used = self.idp.calls_to("/functions/v1/account-delete")[0]["bearer"]
        self.assertNotEqual(used, login_bearer, "delete reused the existing session's token")
        self.assertTrue(self.idp.access[used]["fresh"])
        self.assertTrue(body["deleted"] and not body["signed_in"])
        self.assertIsNone(self.session_meta())
        code, body, _ = self.run_json("auth", "status", "--offline")
        self.assertFalse(body["signed_in"])

    def test_delete_with_a_wrong_code_deletes_nothing(self):
        self.sign_in()
        self.run_json("auth", "delete", "--send-code")
        code, body, _ = self.run_json("auth", "delete", "--yes", input_text="00000000\n")
        self.assertEqual(code, 1)
        self.assertEqual(self.idp.deleted, [])
        self.assertIsNotNone(self.session_meta())

    def test_delete_needs_an_explicit_confirmation_without_a_terminal(self):
        self.sign_in()
        code, body, _ = self.run_json("auth", "delete", input_text=CODE + "\n")
        self.assertEqual(code, 2)
        self.assertEqual(self.idp.deleted, [])

    def test_a_non_fresh_token_is_what_the_function_refuses(self):
        # The premise of the CLI's design: a refreshed session cannot delete an account.
        self.sign_in()
        meta_token = next(iter(self.idp.access))
        refreshed = self.idp.new_session(self.idp.users[EMAIL], fresh=False)
        status = self.idp.route("POST", "/functions/v1/account-delete", {}, {}, refreshed["access_token"])[0]
        self.assertEqual(status, 403)
        self.assertTrue(meta_token)


class LogoutTest(AuthTestCase):
    def local_records(self):
        files = self.store_files()
        return {
            "session": any(r.endswith("account-session.json") for r in files),
            "entitlement": any(r.endswith("entitlement.json") for r in files),
            "refresh": any(b"SENTINEL-REFRESH" in raw for raw in files.values()),
        }

    def test_logout_revokes_on_the_server_and_removes_every_local_record(self):
        self.sign_in()
        self.assertEqual(self.local_records(), {"session": True, "entitlement": True, "refresh": True})
        code, body, _ = self.run_json("auth", "logout")
        self.assertEqual(code, 0)
        self.assertTrue(body["server_revoked"])
        self.assertIn("local", self.idp.logouts)
        self.assertEqual(self.local_records(), {"session": False, "entitlement": False, "refresh": False})

    def test_logout_with_the_server_down_still_removes_the_local_session(self):
        self.sign_in()
        self.idp.down = True
        code, body, _ = self.run_json("auth", "logout")
        self.assertEqual(code, 0)
        self.assertFalse(body["server_revoked"])
        self.assertTrue(body["refresh_token_removed"] and body["entitlement_removed"])
        self.assertEqual(self.local_records(), {"session": False, "entitlement": False, "refresh": False})

    def test_logout_when_signed_out_is_a_clean_no_op(self):
        code, body, _ = self.run_json("auth", "logout")
        self.assertEqual((code, body["was_signed_in"]), (0, False))


class StatusAndCheckTest(AuthTestCase):
    def rewrite_cache(self, **changes):
        path = next(Path(self.home).rglob("entitlement.json"))
        record = json.loads(path.read_text())
        record.update(changes)
        path.write_text(json.dumps(record))

    def rewrite_meta(self, **changes):
        path = next(Path(self.home).rglob("account-session.json"))
        record = json.loads(path.read_text())
        record.update(changes)
        path.write_text(json.dumps(record))

    def test_check_passes_when_entitled(self):
        self.sign_in()
        code, body, _ = self.run_json("auth", "check")
        self.assertEqual(code, 0)
        self.assertTrue(body["entitled"])
        self.assertEqual(body["entitlement"]["status"], "active")

    def test_check_signed_out_fails_with_exit_1_and_the_same_shape(self):
        code, body, _ = self.run_json("auth", "check")
        self.assertEqual(code, 1)
        self.assertFalse(body["ok"])
        self.assertFalse(body["entitled"])
        self.assertEqual(body["entitlement"]["status"], "signed_out")
        for key in ("signed_in", "account", "entitlement", "online", "secret_backend", "test_seam", "warnings"):
            self.assertIn(key, body)

    def test_a_blocked_account_fails_check_but_status_still_reports_it(self):
        self.idp.statuses[EMAIL] = "banned"
        self.sign_in()
        code, body, _ = self.run_json("auth", "check", "--offline")
        self.assertEqual((code, body["entitlement"]["status"]), (1, "banned"))
        code, body, _ = self.run_json("auth", "status", "--offline")
        self.assertEqual((code, body["entitlement"]["status"]), (0, "banned"))
        self.idp.statuses[EMAIL] = "trial_expired"
        self.sign_in()
        code, body, _ = self.run_json("auth", "check", "--offline")
        self.assertEqual((code, body["entitlement"]["status"]), (1, "trial_expired"))

    def test_an_expired_window_needs_an_online_check_exit_3_offline(self):
        self.sign_in()
        self.rewrite_cache(skew=9 * 86400)
        code, body, _ = self.run_json("auth", "check", "--offline")
        self.assertEqual(code, 3)
        self.assertEqual(body["entitlement"]["status"], "needs_online_check")
        self.assertFalse(body["entitled"])

    def test_an_expired_window_renews_online(self):
        self.sign_in()
        self.rewrite_cache(skew=9 * 86400)
        code, body, _ = self.run_json("auth", "check")
        self.assertEqual(code, 0, body)
        self.assertEqual(self.idp.entitlement_calls, 2)
        self.assertTrue(body["online"]["ok"])

    def test_an_expired_window_with_the_server_down_is_exit_3(self):
        self.sign_in()
        self.rewrite_cache(skew=9 * 86400)
        self.idp.down = True
        code, body, _ = self.run_json("auth", "check")
        self.assertEqual(code, 3)
        self.assertFalse(body["online"]["ok"])

    def test_a_stale_check_refreshes_and_a_fresh_one_does_not(self):
        self.sign_in()
        self.run_json("auth", "check")
        self.assertEqual(self.idp.entitlement_calls, 1)
        self.rewrite_meta(last_online_check=1, last_online_attempt=1)
        code, body, _ = self.run_json("auth", "check")
        self.assertEqual(code, 0)
        self.assertEqual(self.idp.entitlement_calls, 2)
        self.assertGreater(self.session_meta()["last_online_check"], 1_000_000)

    def test_a_failed_online_attempt_is_not_repeated_on_every_command(self):
        self.sign_in()
        self.rewrite_meta(last_online_check=1, last_online_attempt=1)
        self.idp.down = True
        code, body, _ = self.run_json("auth", "check")
        self.assertEqual(code, 0)  # the cached token is still valid
        self.assertTrue(body["online"]["attempted"])
        self.assertFalse(body["online"]["ok"])
        before = len(self.idp.calls)
        code, body, _ = self.run_json("auth", "check")
        self.assertFalse(body["online"]["attempted"])
        self.assertEqual(len(self.idp.calls), before)

    def test_a_revoked_session_is_cleared_and_reported_signed_out(self):
        self.sign_in()
        self.rewrite_cache(skew=9 * 86400)
        for record in self.idp.sessions.values():
            record["alive"] = False
        code, body, _ = self.run_json("auth", "check")
        self.assertEqual(code, 1)
        self.assertEqual(body["entitlement"]["status"], "signed_out")
        self.assertIsNone(self.session_meta())

    def test_the_account_of_another_user_is_not_accepted(self):
        self.sign_in()
        self.rewrite_meta(account_id="00000000-0000-0000-0000-000000000000")
        code, body, _ = self.run_json("auth", "check", "--offline")
        self.assertEqual(code, 1)
        self.assertEqual(body["entitlement"]["reason"], "wrong_account")

    def test_status_is_exit_0_even_when_signed_out(self):
        code, body, _ = self.run_json("auth", "status")
        self.assertEqual((code, body["signed_in"], body["secret_backend"]), (0, False, None))
        self.assertEqual(self.idp.calls, [])

    def test_human_output_reads_plainly(self):
        self.sign_in()
        code, out, _err = self.run_auth("auth", "status", "--offline")
        self.assertEqual(code, 0)
        self.assertIn("signed in as " + EMAIL, out)
        self.assertIn("license      active", out)


if __name__ == "__main__":
    unittest.main()
