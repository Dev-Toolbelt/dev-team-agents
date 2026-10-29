"""The account refresh token is bound to its store and seam (F1).

The macOS login keychain is global to the OS user: it ignores ``DEVTEAM_HOME`` and the
loopback test seam. A shared in-memory dict stands in for it here so no test touches a real
keychain. A session saved, refreshed or cleared in a throwaway store must leave the secret of
the default store's session alone.
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

import devteam_support  # noqa: E402,F401
import ed25519_signer  # noqa: E402
from auth_fakes import SEED, b64  # noqa: E402
from devteam import auth_session, entitlement, paths  # noqa: E402
from devteam import secrets as secrets_module  # noqa: E402
from devteam_support import rmtree  # noqa: E402


def _session(account, refresh):
    return {
        "user": {"id": account, "email": account + "@example.com"},
        "refresh_token": refresh,
        "access_token": "access-" + refresh,
        "expires_in": 3600,
    }


class _DefaultStorePaths:
    """``paths`` as the default store sees it (no ``DEVTEAM_HOME``) but still rooted in the
    test's temp directory, so nothing is written outside it."""

    def __init__(self, real):
        self._real = real

    def devteam_home(self):
        return None

    def __getattr__(self, name):
        return getattr(self._real, name)


class _Client:
    def __init__(self, account):
        self.account = account
        self.presented = []

    def refresh(self, token):
        self.presented.append(token)
        return _session(self.account, "rotated")


class SessionIsolationTests(unittest.TestCase):
    def setUp(self):
        self.global_store = {}
        self.tmp = Path(tempfile.mkdtemp(prefix="devteam-iso-"))
        self.addCleanup(rmtree, str(self.tmp), True)
        self.real_home = self.tmp / "real"
        self.other_home = self.tmp / "other"
        keys = (paths.HOME_ENV, paths.MACHINE_ID_ENV, *entitlement.SEAM_ENVS)
        saved = {k: os.environ.get(k) for k in keys}
        self.addCleanup(self._restore, saved)
        for k in (paths.MACHINE_ID_ENV, *entitlement.SEAM_ENVS):
            os.environ.pop(k, None)

        store = self.global_store
        self.reads = []
        fake = {
            "_PUT": {"keychain": lambda ref, value: store.__setitem__(ref, value)},
            "_GET": {"keychain": lambda ref: (self.reads.append(ref), store.get(ref))[1]},
            "_DELETE": {"keychain": lambda ref: store.pop(ref, None) is not None},
        }
        for name, table in fake.items():
            patcher = mock.patch.dict(getattr(secrets_module, name), table, clear=True)
            patcher.start()
            self.addCleanup(patcher.stop)
        for name, value in (
            ("available_backends", lambda: ["keychain"]),
            ("default_backend", lambda: "keychain"),
        ):
            patcher = mock.patch.object(secrets_module, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        auth_session._forget_memory()
        self.addCleanup(auth_session._forget_memory)

    @staticmethod
    def _restore(saved):
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def _use_home(self, home, seam=False):
        os.environ[paths.HOME_ENV] = str(home)
        for key in entitlement.SEAM_ENVS:
            os.environ.pop(key, None)
        if seam:
            os.environ[entitlement.SEAM_URL_ENV] = "http://127.0.0.1:1"
            os.environ[entitlement.SEAM_KID_ENV] = "test-iso-1"
            os.environ[entitlement.SEAM_KEY_ENV] = b64(ed25519_signer.public_key(SEED))
            self.assertIsNotNone(entitlement._seam(os.environ, {})[0])
        auth_session._forget_memory()

    def _use_default_store(self, home, seam=False):
        """The default store (``devteam_home()`` is ``None``), kept inside ``home``."""
        self._use_home(home, seam)
        patcher = mock.patch.object(auth_session, "paths", _DefaultStorePaths(paths))
        patcher.start()
        self.addCleanup(patcher.stop)

    def _stored_token(self):
        return auth_session._stored_refresh_token(auth_session.read_meta())

    def _save_real(self):
        self._use_home(self.real_home)
        auth_session.save_session(_session("real-acct", "token-A"), "google")
        self.assertEqual(self._stored_token(), "token-A")

    def _assert_real_intact(self):
        self._use_home(self.real_home)
        self.assertEqual(self._stored_token(), "token-A")
        self.assertIn("token-A", self.global_store.values())

    def _write_record(self, **fields):
        paths.machine_dir().mkdir(parents=True, exist_ok=True)
        record = {
            "schema": 1, "account_id": "acct", "email": None, "display_name": None,
            "provider": "password", "backend": "keychain", "signed_in_at": 1,
            "last_online_check": None, "last_online_attempt": None,
        }
        record.update(fields)
        auth_session.jsonio.write_json_atomic(auth_session.meta_path(), record)
        auth_session._forget_memory()

    def test_s1_other_home_save_and_logout_keep_the_real_secret(self):
        self._save_real()
        self._use_home(self.other_home)
        auth_session.save_session(_session("other-acct", "token-B"), "password")
        self.assertIn("token-A", self.global_store.values())
        auth_session.clear_local()
        self._assert_real_intact()

    def test_s2_seam_save_and_logout_keep_the_real_secret(self):
        self._save_real()
        self._use_home(self.other_home, seam=True)
        auth_session.save_session(_session("seam-acct", "token-B"), "password")
        self.assertIn("token-A", self.global_store.values())
        auth_session.clear_local()
        self._assert_real_intact()

    def test_s3_clear_in_other_home_with_no_session_keeps_the_real_secret(self):
        self._save_real()
        self._use_home(self.other_home, seam=True)
        paths.machine_dir().mkdir(parents=True, exist_ok=True)
        auth_session.clear_local()
        self._assert_real_intact()

    def test_s4_prefix_record_in_the_default_store_stays_readable(self):
        self._use_default_store(self.real_home)
        self.assertEqual(auth_session.context_ref(), auth_session.REF)
        self.global_store[auth_session.REF] = "token-A"
        self._write_record()
        self.assertEqual(self._stored_token(), "token-A")
        self.assertEqual(auth_session.access_token(_Client("acct")), "access-rotated")
        self.assertEqual(self.global_store[auth_session.REF], "rotated")

    def test_s5_logout_in_the_default_store_removes_its_own_secret(self):
        self._use_default_store(self.real_home)
        auth_session.save_session(_session("real-acct", "token-A"), "google")
        self.assertEqual(self.global_store, {auth_session.REF: "token-A"})
        auth_session.clear_local()
        self.assertEqual(self.global_store, {})
        self.assertIsNone(auth_session.read_meta())

    def test_prefix_record_in_an_isolated_store_never_touches_ref(self):
        self.global_store[auth_session.REF] = "token-A"
        self._use_home(self.other_home)
        self._write_record()
        self.assertIsNone(auth_session.read_meta())
        client = _Client("acct")
        with self.assertRaises(auth_session.Rejected):
            auth_session.access_token(client)
        self.assertEqual(client.presented, [])
        auth_session.clear_local()
        self.assertNotIn(auth_session.REF, self.reads)
        self.assertEqual(self.global_store, {auth_session.REF: "token-A"})
        auth_session.save_session(_session("acct", "token-B"), "password")
        self.assertEqual(self.global_store[auth_session.REF], "token-A")

    def test_seam_in_the_default_store_treats_the_real_record_as_signed_out(self):
        self._use_default_store(self.real_home)
        auth_session.save_session(_session("real-acct", "token-A"), "google")
        self._use_default_store(self.real_home, seam=True)
        self.assertNotEqual(auth_session.context_ref(), auth_session.REF)
        self.assertIsNone(auth_session.read_meta())
        client = _Client("real-acct")
        with self.assertRaises(auth_session.Rejected):
            auth_session.access_token(client)
        self.assertEqual(client.presented, [])
        auth_session.clear_local()
        self.assertNotIn(auth_session.REF, self.reads)
        self.assertEqual(self.global_store, {auth_session.REF: "token-A"})
        self.assertTrue(auth_session.meta_path().exists())

    def test_prefix_record_under_a_seam_in_the_default_store_is_signed_out(self):
        self._use_default_store(self.real_home, seam=True)
        self.global_store[auth_session.REF] = "token-A"
        self._write_record()
        cache = entitlement.cache_path()
        cache.write_text("{}")
        self.assertIsNone(auth_session.read_meta())
        client = _Client("acct")
        with self.assertRaises(auth_session.Rejected):
            auth_session.access_token(client)
        self.assertEqual(client.presented, [])
        auth_session.clear_local()
        self.assertNotIn(auth_session.REF, self.reads)
        self.assertEqual(self.global_store, {auth_session.REF: "token-A"})
        self.assertTrue(auth_session.meta_path().exists())
        self.assertTrue(cache.exists())

    def test_a_tampered_secret_ref_is_never_used(self):
        self.global_store.update({"../x": "x", "account.session.refresh_token.ZZ": "zz"})
        self._use_home(self.other_home)
        other = "{}.{}".format(auth_session.REF, "0" * 16)
        self.assertNotEqual(other, auth_session.context_ref())
        self.global_store[other] = "foreign"
        for ref in ("../x", "account.session.refresh_token.ZZ", other, auth_session.REF, 7):
            self._write_record(secret_ref=ref)
            self.assertIsNone(auth_session.read_meta(), ref)
            client = _Client("acct")
            with self.assertRaises(auth_session.Rejected):
                auth_session.access_token(client)
            auth_session.clear_local()
            self.assertEqual(client.presented, [])
        self.assertEqual(
            self.global_store,
            {"../x": "x", "account.session.refresh_token.ZZ": "zz", other: "foreign"},
        )

    def test_refresh_writes_the_rotated_token_under_the_context_ref(self):
        self._use_home(self.other_home, seam=True)
        auth_session.save_session(_session("acct", "token-B"), "password")
        auth_session._forget_memory()
        ref = auth_session.context_ref()
        self.assertEqual(auth_session.access_token(_Client("acct")), "access-rotated")
        self.assertEqual(self.global_store, {ref: "rotated"})

    def test_schema_follows_the_reference(self):
        self._use_home(self.other_home)
        meta = auth_session.save_session(_session("acct", "t"), "password")
        self.assertEqual((meta["schema"], meta["secret_ref"]), (2, auth_session.context_ref()))
        self.assertIsNotNone(auth_session.read_meta())
        self._use_default_store(self.real_home)
        meta = auth_session.save_session(_session("acct", "t"), "password")
        self.assertEqual((meta["schema"], meta["secret_ref"]), (1, auth_session.REF))
        self.assertIsNotNone(auth_session.read_meta())


if __name__ == "__main__":
    unittest.main()
