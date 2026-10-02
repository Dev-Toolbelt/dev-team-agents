"""Entitlement token verification, evaluation and cache (ADR-0029 SR-8, 21-27, 44)."""

from __future__ import annotations

import base64
import json
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import ed25519_signer  # noqa: E402
from devteam_support import StoreTestCase  # noqa: E402
from devteam import entitlement as ent  # noqa: E402
from devteam import paths  # noqa: E402
from devteam.errors import UsageError  # noqa: E402

DAY = 86400
SEED = bytes(range(32))
OTHER_SEED = bytes(range(1, 33))
KID = "test-1"
ISSUER = "https://acct.example.supabase.co"
ACCOUNT = "11111111-2222-3333-4444-555555555555"
T0 = 1_800_000_000


def b64(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def compact(obj):
    return json.dumps(obj, separators=(",", ":")).encode("utf-8")


def make_token(overrides=None, seed=SEED, header=None, version="v1", raw_payload=None, drop=()):
    payload = {
        "sub": ACCOUNT,
        "status": "active",
        "features": [],
        "iss": ISSUER,
        "aud": "devteam-cli",
        "v": 1,
        "iat": T0,
        "exp": T0 + 7 * DAY,
    }
    payload.update(overrides or {})
    for key in drop:
        payload.pop(key, None)
    head = b64(compact(header if header is not None else {"kid": KID}))
    body = b64(raw_payload if raw_payload is not None else compact(payload))
    signed = "{}.{}.{}".format(version, head, body).encode("ascii")
    return "{}.{}".format(signed.decode("ascii"), b64(ed25519_signer.sign(seed, signed)))


def identity(**changes):
    values = dict(
        environment="prod",
        supabase_url=ISSUER,
        anon_key="anon",
        audience="devteam-cli",
        keys={KID: ed25519_signer.public_key(SEED)},
    )
    values.update(changes)
    return ent.Identity(**values)


def cache_for(token, skew=0, max_seen_at=T0):
    return {"schema": 1, "token": token, "skew": skew, "max_seen_at": max_seen_at}


class VerifyTokenTest(unittest.TestCase):
    def reason(self, token):
        with self.assertRaises(ent.TokenError) as ctx:
            ent.verify_token(token, identity())
        return ctx.exception.reason

    def test_valid_token(self):
        claims = ent.verify_token(make_token(), identity())
        self.assertEqual((claims.sub, claims.status, claims.kid, claims.iat), (ACCOUNT, "active", KID, T0))

    def test_header_with_alg_is_rejected(self):
        self.assertEqual(self.reason(make_token(header={"kid": KID, "alg": "EdDSA"})), "bad_header")
        self.assertEqual(self.reason(make_token(header={"kid": KID, "alg": "none"})), "bad_header")

    def test_header_without_kid_is_rejected(self):
        self.assertEqual(self.reason(make_token(header={})), "bad_header")

    def test_wrong_version_prefix(self):
        self.assertEqual(self.reason(make_token(version="v2")), "bad_version")

    def test_oversized_token(self):
        self.assertEqual(self.reason(make_token({"features": ["x" * 5000]})), "bad_format")

    def test_non_base64url_character_and_padding(self):
        token = make_token()
        head, body, sig = token.split(".")[1:]
        self.assertEqual(self.reason("v1.{}+.{}.{}".format(head, body, sig)), "bad_encoding")
        self.assertEqual(self.reason("v1.{}=.{}.{}".format(head, body, sig)), "bad_encoding")
        self.assertEqual(self.reason("v1.{}.{}.{}!".format(head, body, sig)), "bad_encoding")

    def test_wrong_part_count(self):
        token = make_token()
        self.assertEqual(self.reason(token + ".extra"), "bad_format")
        self.assertEqual(self.reason(".".join(token.split(".")[:3])), "bad_format")
        self.assertEqual(self.reason(""), "bad_format")

    def test_unknown_kid(self):
        self.assertEqual(self.reason(make_token(header={"kid": "test-2"})), "unknown_kid")

    def test_signature_from_another_key(self):
        self.assertEqual(self.reason(make_token(seed=OTHER_SEED)), "bad_signature")

    def test_tampered_payload(self):
        head, body, sig = make_token().split(".")[1:]
        forged = b64(compact({"sub": ACCOUNT, "status": "active", "iss": ISSUER, "aud": "devteam-cli",
                              "v": 1, "iat": T0, "exp": T0 + 29 * DAY}))
        self.assertEqual(self.reason("v1.{}.{}.{}".format(head, forged, sig)), "bad_signature")

    def test_signature_is_checked_before_the_payload_is_parsed(self):
        head, _body, sig = make_token().split(".")[1:]
        self.assertEqual(self.reason("v1.{}.{}.{}".format(head, b64(b"{not json"), sig)), "bad_signature")

    def test_signed_duplicate_key_is_rejected(self):
        raw = (b'{"sub":"%s","status":"active","status":"banned","iss":"%s","aud":"devteam-cli",'
               b'"v":1,"iat":%d,"exp":%d}') % (ACCOUNT.encode(), ISSUER.encode(), T0, T0 + DAY)
        self.assertEqual(self.reason(make_token(raw_payload=raw)), "duplicate_key")

    def test_signed_non_object_and_nan(self):
        self.assertEqual(self.reason(make_token(raw_payload=b"[1,2]")), "bad_payload")
        self.assertEqual(self.reason(make_token(raw_payload=b'{"iat":NaN}')), "bad_json")

    def test_wrong_types(self):
        for name, value in (("iat", "1"), ("exp", 1.5), ("exp", True), ("v", None), ("sub", 7),
                            ("status", ["active"]), ("features", "all"), ("features", [1])):
            with self.subTest(claim=name, value=value):
                with self.assertRaises(ent.TokenError):
                    ent.verify_token(make_token({name: value}), identity())

    def test_missing_required_claim(self):
        for name in ("sub", "status", "iss", "aud", "v", "iat", "exp"):
            with self.subTest(claim=name):
                with self.assertRaises(ent.TokenError):
                    ent.verify_token(make_token(drop=(name,)), identity())

    def test_unknown_feature_keys_are_never_granted(self):
        claims = ent.verify_token(make_token({"features": ["super-feature"]}), identity())
        self.assertEqual(claims.features, ())


class CheckClaimsTest(unittest.TestCase):
    def reason(self, overrides=None, **identity_changes):
        claims = ent.verify_token(make_token(overrides), identity(**identity_changes))
        with self.assertRaises(ent.TokenError) as ctx:
            ent.check_claims(claims, identity(**identity_changes), ACCOUNT)
        return ctx.exception.reason

    def test_wrong_version(self):
        self.assertEqual(self.reason({"v": 2}), "bad_version")

    def test_dev_token_refused_by_prod_issuer(self):
        self.assertEqual(self.reason({"iss": "https://dev.example.supabase.co"}), "wrong_issuer")

    def test_issuer_trailing_slash_is_equivalent(self):
        claims = ent.verify_token(make_token({"iss": ISSUER + "/"}), identity())
        ent.check_claims(claims, identity(), ACCOUNT)

    def test_wrong_audience(self):
        self.assertEqual(self.reason({"aud": "other"}), "wrong_audience")

    def test_wrong_account(self):
        claims = ent.verify_token(make_token(), identity())
        with self.assertRaises(ent.TokenError) as ctx:
            ent.check_claims(claims, identity(), "someone-else")
        self.assertEqual(ctx.exception.reason, "wrong_account")

    def test_unknown_status(self):
        self.assertEqual(self.reason({"status": "god-mode"}), "unknown_status")

    def test_validity_over_thirty_days(self):
        self.assertEqual(self.reason({"exp": T0 + 30 * DAY + 1}), "validity_too_long")
        claims = ent.verify_token(make_token({"exp": T0 + 30 * DAY}), identity())
        ent.check_claims(claims, identity(), ACCOUNT)

    def test_non_positive_validity(self):
        self.assertEqual(self.reason({"exp": T0}), "bad_validity")

    def test_trial_needs_trial_ends_at(self):
        self.assertEqual(self.reason({"status": "trial"}), "bad_claim_trial_ends_at")


class EvaluateTest(unittest.TestCase):
    def evaluate(self, token=None, now=T0 + 100, skew=0, max_seen_at=T0, account=ACCOUNT, **kw):
        cache = cache_for(token or make_token(), skew, max_seen_at)
        return ent.evaluate(kw.get("cache", cache), identity(), account, now)

    def test_active(self):
        result = self.evaluate()
        self.assertEqual((result.status, result.usable), ("active", True))
        self.assertEqual(result.expires_at, T0 + 7 * DAY)

    def test_premium_is_active_with_its_token_status(self):
        result = self.evaluate(make_token({"status": "premium"}))
        self.assertEqual((result.status, result.token_status), ("active", "premium"))

    def test_trial_and_end_of_trial(self):
        token = make_token({"status": "trial", "trial_ends_at": T0 + 2 * DAY})
        self.assertEqual(self.evaluate(token, now=T0 + DAY).status, "trial")
        ended = self.evaluate(token, now=T0 + 2 * DAY + 1)
        self.assertEqual((ended.status, ended.reason), ("needs_online_check", "trial_period_ended"))

    def test_trial_expires_at_the_earlier_of_trial_and_token(self):
        result = self.evaluate(make_token({"status": "trial", "trial_ends_at": T0 + DAY}))
        self.assertEqual(result.expires_at, T0 + DAY)

    def test_expired_token_needs_online_check(self):
        result = self.evaluate(now=T0 + 7 * DAY)
        self.assertEqual((result.status, result.reason), ("needs_online_check", "expired"))
        self.assertEqual(self.evaluate(now=T0 + 7 * DAY - 1).status, "active")

    def test_max_offline_days_claim_only_shortens(self):
        short = make_token({"max_offline_days": 2})
        self.assertEqual(self.evaluate(short, now=T0 + 2 * DAY - 1).status, "active")
        self.assertEqual(self.evaluate(short, now=T0 + 2 * DAY).status, "needs_online_check")
        longer = make_token({"max_offline_days": 30})
        self.assertEqual(self.evaluate(longer, now=T0 + 7 * DAY).status, "needs_online_check")

    def test_banned_and_trial_expired_are_reported_offline(self):
        for status in ("banned", "trial_expired"):
            with self.subTest(status=status):
                self.assertEqual(self.evaluate(make_token({"status": status})).status, status)

    def test_blocked_token_past_its_window_needs_a_check(self):
        result = self.evaluate(make_token({"status": "banned"}), now=T0 + 8 * DAY)
        self.assertEqual(result.status, "needs_online_check")

    def test_signed_out_and_missing_cache(self):
        self.assertEqual(ent.evaluate(None, identity(), None, T0).status, "signed_out")
        self.assertEqual(self.evaluate(account=None).status, "signed_out")
        missing = ent.evaluate(None, identity(), ACCOUNT, T0)
        self.assertEqual((missing.status, missing.reason), ("needs_online_check", "no_cached_token"))

    def test_invalid_cases(self):
        cases = {
            "wrong account": self.evaluate(account="another"),
            "bad signature": self.evaluate(make_token(seed=OTHER_SEED)),
            "malformed cache": ent.evaluate({}, identity(), ACCOUNT, T0),
            "bad cache types": ent.evaluate({"schema": 1, "token": "x", "skew": "0", "max_seen_at": 0},
                                            identity(), ACCOUNT, T0),
            "unknown status": self.evaluate(make_token({"status": "vip"})),
        }
        for label, result in cases.items():
            with self.subTest(case=label):
                self.assertEqual(result.status, "invalid")

    def test_issued_in_the_future_is_invalid(self):
        result = self.evaluate(make_token({"iat": T0 + 3600, "exp": T0 + 3600 + DAY}), now=T0, max_seen_at=T0)
        self.assertEqual((result.status, result.reason), ("invalid", "issued_in_the_future"))

    def test_iat_within_tolerance_is_accepted(self):
        token = make_token({"iat": T0 + 200, "exp": T0 + 200 + DAY})
        self.assertEqual(self.evaluate(token, now=T0).status, "active")

    def test_clock_slow_by_ten_minutes_still_works_offline(self):
        # Accepted online at true time T0 while the local clock read T0 - 600: skew +600.
        skew = 600
        local = (T0 - 600) + 3 * 3600
        self.assertEqual(self.evaluate(now=local, skew=skew).status, "active")

    def test_clock_rolled_back_a_day_forces_an_online_check(self):
        result = self.evaluate(now=T0 + 3 * 3600 - DAY, max_seen_at=T0 + 3 * 3600)
        self.assertEqual((result.status, result.reason), ("needs_online_check", "clock_rollback"))

    def test_rollback_tolerance_is_five_minutes(self):
        seen = T0 + 3600
        self.assertEqual(self.evaluate(now=seen - 299, max_seen_at=seen).status, "active")
        self.assertEqual(self.evaluate(now=seen - 301, max_seen_at=seen).status, "needs_online_check")

    def test_to_dict_is_json_serialisable(self):
        json.dumps(self.evaluate().to_dict())


class CacheTest(StoreTestCase):
    def setUp(self):
        super().setUp()
        self.path = ent.cache_path()

    def store(self, token, now=T0, account=ACCOUNT):
        return ent.store_token(token, identity(), account, local_now=now)

    def read(self):
        return json.loads(self.path.read_text())

    def test_cache_lives_in_the_machine_local_state_dir(self):
        self.assertEqual(self.path.parent, paths.machine_dir())
        self.assertEqual(self.path.name, "entitlement.json")
        self.assertTrue(paths.is_machine_local_record("entitlement.json"))
        self.assertTrue(paths.path_is_machine_local("projects/x/entitlement.json"))

    def test_store_records_skew_and_resets_max_seen_at(self):
        result = self.store(make_token(), now=T0 - 600)
        self.assertEqual(result.status, "active")
        record = self.read()
        self.assertEqual((record["skew"], record["max_seen_at"], record["schema"]), (600, T0, 1))
        if os.name != "nt":
            self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)

    def test_store_rejects_an_unacceptable_token_and_writes_nothing(self):
        for token, account in ((make_token(seed=OTHER_SEED), ACCOUNT), (make_token(), "someone-else"),
                               (make_token({"exp": T0 + 31 * DAY}), ACCOUNT)):
            self.assertEqual(self.store(token, account=account).status, "invalid")
        self.assertFalse(self.path.exists())

    def test_older_token_never_replaces_a_newer_one(self):
        newer = make_token({"iat": T0 + 1000, "exp": T0 + 1000 + 7 * DAY})
        older = make_token()
        self.store(newer, now=T0 + 1000)
        result = self.store(older, now=T0 + 1001)
        self.assertEqual(self.read()["token"], newer)
        self.assertEqual(result.status, "active")

    def test_newer_token_replaces_and_a_different_account_always_does(self):
        self.store(make_token())
        newer = make_token({"iat": T0 + 500, "exp": T0 + 500 + 7 * DAY})
        self.store(newer, now=T0 + 500)
        self.assertEqual(self.read()["token"], newer)
        other = make_token({"sub": "another", "iat": T0, "exp": T0 + DAY})
        self.store(other, now=T0 + 600, account="another")
        self.assertEqual(self.read()["token"], other)

    def test_check_advances_max_seen_at_only_for_a_token_in_use(self):
        self.store(make_token())
        ent.check(identity(), ACCOUNT, local_now=T0 + 3 * 3600)
        self.assertEqual(self.read()["max_seen_at"], T0 + 3 * 3600)
        ent.check(identity(), ACCOUNT, local_now=T0 + 3 * 3600 + 10)
        self.assertEqual(self.read()["max_seen_at"], T0 + 3 * 3600)  # under the write step
        ent.check(identity(), ACCOUNT, local_now=T0 + 20 * DAY)  # expired: not recorded
        self.assertEqual(self.read()["max_seen_at"], T0 + 3 * 3600)

    def test_clock_jumped_forward_then_back_recovers_after_one_online_check(self):
        self.store(make_token())
        self.assertEqual(ent.check(identity(), ACCOUNT, local_now=T0 + 3 * DAY).status, "active")
        back = ent.check(identity(), ACCOUNT, local_now=T0 + 3600)
        self.assertEqual((back.status, back.reason), ("needs_online_check", "clock_rollback"))
        fresh = make_token({"iat": T0 + 3600, "exp": T0 + 3600 + 7 * DAY})
        self.store(fresh, now=T0 + 3600)
        self.assertEqual(ent.check(identity(), ACCOUNT, local_now=T0 + 3700).status, "active")

    def test_clock_jumped_a_year_forward_and_back_needs_no_extra_step(self):
        self.store(make_token())
        year = ent.check(identity(), ACCOUNT, local_now=T0 + 365 * DAY)
        self.assertEqual(year.status, "needs_online_check")
        self.assertEqual(ent.check(identity(), ACCOUNT, local_now=T0 + DAY).status, "active")

    def test_banned_token_is_cached_and_shown_offline(self):
        self.store(make_token({"status": "banned"}))
        self.assertEqual(ent.check(identity(), ACCOUNT, local_now=T0 + 60).status, "banned")

    def test_corrupt_cache_is_invalid_and_replaced_by_the_next_store(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text("{ not json")
        self.assertEqual(ent.check(identity(), ACCOUNT, local_now=T0).status, "invalid")
        self.assertEqual(self.store(make_token()).status, "active")

    def test_clear_cache(self):
        self.store(make_token())
        ent.clear_cache()
        self.assertFalse(self.path.exists())
        ent.clear_cache()  # idempotent
        self.assertEqual(ent.check(identity(), ACCOUNT, local_now=T0).status, "needs_online_check")


class LoadIdentityTest(unittest.TestCase):
    def config(self, tmp, keys=None, url="https://abc.supabase.co"):
        data = {
            "schema": 1,
            "environment": "prod",
            "audience": "devteam-cli",
            "environments": {"prod": {"supabase_url": url, "anon_key": "anon",
                                      "entitlement_keys": keys if keys is not None else {}}},
        }
        path = Path(tmp) / "auth-config.json"
        path.write_text(json.dumps(data))
        return path

    def setUp(self):
        import tempfile

        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)

    def seam(self, **changes):
        env = {
            ent.SEAM_URL_ENV: "http://127.0.0.1:54321",
            ent.SEAM_KID_ENV: "test-1",
            ent.SEAM_KEY_ENV: b64(ed25519_signer.public_key(SEED)),
        }
        env.update(changes)
        return {k: v for k, v in env.items() if v is not None}

    def test_shipped_config_is_placeholders_and_unconfigured(self):
        loaded = ent.load_identity(environ={})
        self.assertFalse(loaded.configured)
        self.assertEqual(loaded.keys, {})
        self.assertIn("REPLACE-ME", loaded.supabase_url)
        self.assertFalse(loaded.test_seam)
        # An unconfigured build trusts no key, so it rejects every token.
        with self.assertRaises(ent.TokenError):
            ent.verify_token(make_token(), loaded)

    def test_configured_identity(self):
        path = self.config(self.dir.name, {"prod-1": b64(ed25519_signer.public_key(SEED))})
        loaded = ent.load_identity(environ={}, config_path=path)
        self.assertTrue(loaded.configured)
        self.assertEqual(loaded.issuer, "https://abc.supabase.co")
        self.assertEqual(list(loaded.keys), ["prod-1"])

    def test_other_sources_do_not_move_the_endpoint(self):
        path = self.config(self.dir.name, {"prod-1": b64(ed25519_signer.public_key(SEED))})
        env = {
            "SUPABASE_URL": "https://evil.example",
            "DEVTEAM_SUPABASE_URL": "https://evil.example",
            "DEVTEAM_AUTH_URL": "https://evil.example",
            "DEVTEAM_AUTH_ISSUER": "https://evil.example",
        }
        self.assertEqual(ent.load_identity(environ=env, config_path=path).issuer, "https://abc.supabase.co")

    def test_seam_accepts_loopback_and_adds_a_test_key(self):
        path = self.config(self.dir.name)
        loaded = ent.load_identity(environ=self.seam(), config_path=path)
        self.assertTrue(loaded.test_seam)
        self.assertEqual(loaded.issuer, "http://127.0.0.1:54321")
        self.assertIn("test-1", loaded.keys)
        self.assertIn("test seam", ent.seam_warning(loaded))
        self.assertIsNone(ent.seam_warning(ent.load_identity(environ={})))

    def test_seam_refuses_non_loopback_host(self):
        path = self.config(self.dir.name)
        for url in ("https://acct.example.com", "http://example.com:80", "http://127.0.0.1.evil.com",
                    "ftp://127.0.0.1"):
            with self.subTest(url=url):
                with self.assertRaises(UsageError):
                    ent.load_identity(environ=self.seam(**{ent.SEAM_URL_ENV: url}), config_path=path)

    def test_seam_refuses_a_kid_without_the_test_prefix_and_partial_seams(self):
        path = self.config(self.dir.name)
        with self.assertRaises(UsageError):
            ent.load_identity(environ=self.seam(**{ent.SEAM_KID_ENV: "prod-1"}), config_path=path)
        with self.assertRaises(UsageError):
            ent.load_identity(environ=self.seam(**{ent.SEAM_KEY_ENV: None}), config_path=path)
        with self.assertRaises(UsageError):
            ent.load_identity(environ=self.seam(**{ent.SEAM_KEY_ENV: "AAAA"}), config_path=path)


if __name__ == "__main__":
    unittest.main()
