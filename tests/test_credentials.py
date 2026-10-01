"""Credential values and references (ADR-0010): secrets.py, creds.py, the
`devteam cred` CLI surface, and the doctor findings that read them.

The central promise under test is that a secret value never appears in a
reference file, an audit line, a `--json` payload, or an exception message.
Every test that plants a value scans for its absence explicitly rather than
trusting a code review to have caught a leak.

No test touches a real macOS keychain: behavioural tests force the `insecure`
backend explicitly, and the keychain adapter is covered by patching
`subprocess.run` and asserting the argv and stdin it would use, never by
invoking the real thing. The keychain lives in the OS, outside `$DEVTEAM_HOME`,
where no temp directory can undo what a test wrote — a full run once left three
items in a developer's real login keychain, which is why that rule exists.

**dpapi is the one exception, and the asymmetry is the reason.** A DPAPI blob is
written to `paths.secrets_dir()`, which is inside `$DEVTEAM_HOME` and therefore
inside the throwaway store the fixture removes; the OS holds the *key*, not the
data. So the real `CryptProtectData`/`CryptUnprotectData` can be exercised
without leaving anything behind, and `SecretsDpapiRealRoundTripTest` does
exactly that wherever the host provides them. The mocked class above stays: it
runs everywhere and covers the envelope, which is most of the logic.
"""

from __future__ import annotations

import base64
import ctypes
import json
import os
import unittest
from pathlib import Path
from unittest import mock

from devteam_support import StoreTestCase

from devteam import creds, doctor, paths
from devteam import secrets as secrets_module
from devteam.errors import EnvError, UsageError
from devteam.secrets import SecretError

#: A value distinctive enough that a substring match cannot be a coincidence.
PLANTED = "s3cr3t-PLANTED-VALUE-7f1c9a"


def _iter_files(root):
    root = Path(root)
    if not root.exists():
        return
    if root.is_file():
        yield root
        return
    for path in root.rglob("*"):
        if path.is_file():
            yield path


def assert_value_absent_from_tree(testcase, root, value=PLANTED):
    """Scan every file under ``root`` and fail if ``value`` appears anywhere."""
    for path in _iter_files(root):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        testcase.assertNotIn(value, text, "leaked into {}".format(path))


class CredsTestCase(StoreTestCase):
    """Base for creds/secrets tests: forces a platform with no real keychain.

    `_probe_keychain()` short-circuits to "requires macOS" under a non-darwin
    `DEVTEAM_PLATFORM`, so `default_backend()`/`available_backends()` never shell
    out to `security` even when the suite itself runs on a Mac.
    """

    def setUp(self):
        super().setUp()
        os.environ["DEVTEAM_PLATFORM"] = "linux"


# ── secrets.py — validation ─────────────────────────────────────────────────


class SecretsValidationTest(CredsTestCase):
    def test_backends_tuple_is_stable_and_excludes_the_unimplemented_age_backend(self):
        # ADR-0010 lists an age/sops backend; secrets.py deliberately never
        # implements it, so it must never appear as a name callers can pass.
        self.assertEqual(secrets_module.BACKENDS, ("keychain", "dpapi", "insecure"))
        self.assertNotIn("age", secrets_module.BACKENDS)
        self.assertNotIn("sops", secrets_module.BACKENDS)

    def test_unknown_backend_name_is_rejected_by_put_get_and_delete(self):
        for call in (
            lambda: secrets_module.put("devteam/x/k", "v", backend="vault"),
            lambda: secrets_module.get("devteam/x/k", "vault"),
            lambda: secrets_module.delete("devteam/x/k", "vault"),
        ):
            with self.assertRaises(SecretError) as ctx:
                call()
            self.assertIn("vault", str(ctx.exception))

    def test_invalid_ref_shapes_are_rejected(self):
        for bad in ("", "has space", "trailing/", "/leading", "a" * 257, "new\nline"):
            with self.assertRaises(SecretError):
                secrets_module.put(bad, "v", backend="insecure")

    def test_value_must_be_a_string(self):
        with self.assertRaises(SecretError):
            secrets_module.put("devteam/x/k", 12345, backend="insecure")

    def test_value_with_nul_or_newline_is_rejected_before_reaching_any_backend(self):
        for bad_value in ("has\nnewline", "has\rcr", "has\x00nul"):
            with self.assertRaises(SecretError) as ctx:
                secrets_module.put("devteam/x/k", bad_value, backend="insecure")
            # The rejection message must not echo the bad value back.
            self.assertNotIn(bad_value, str(ctx.exception))

    def test_validation_error_messages_never_contain_the_offending_value(self):
        with self.assertRaises(SecretError) as ctx:
            secrets_module.put("devteam/x/k", PLANTED + "\n", backend="insecure")
        self.assertNotIn(PLANTED, str(ctx.exception))


# ── secrets.py — insecure backend (the only one exercised end-to-end) ──────


class SecretsInsecureBackendTest(CredsTestCase):
    def test_put_get_delete_roundtrip(self):
        result = secrets_module.put("devteam/proj/tok", PLANTED, backend="insecure")
        self.assertEqual(result, {"backend": "insecure", "ref": "devteam/proj/tok", "insecure": True})
        self.assertEqual(secrets_module.get("devteam/proj/tok", "insecure"), PLANTED)
        self.assertTrue(secrets_module.delete("devteam/proj/tok", "insecure"))
        self.assertIsNone(secrets_module.get("devteam/proj/tok", "insecure"))

    def test_get_on_a_ref_never_stored_is_none_not_an_error(self):
        self.assertIsNone(secrets_module.get("devteam/proj/missing", "insecure"))

    def test_delete_on_a_ref_never_stored_returns_false(self):
        self.assertFalse(secrets_module.delete("devteam/proj/missing", "insecure"))

    def test_insecure_is_available_and_last_in_backend_order_when_default(self):
        # With keychain probed unavailable (forced linux) and dpapi unavailable
        # (real ctypes has no windll on this interpreter), insecure must still be
        # offered — a platform with no working backend must never be blocked.
        self.assertIn("insecure", secrets_module.available_backends())
        self.assertEqual(secrets_module.default_backend(), "insecure")

    def test_describe_reports_availability_and_a_reason_for_each_unavailable_backend(self):
        payload = secrets_module.describe()
        self.assertEqual(payload["default"], "insecure")
        self.assertIn("insecure", payload["available"])
        self.assertIsNone(payload["probed"]["insecure"])
        self.assertIsNotNone(payload["probed"]["keychain"])


# ── secrets.py — keychain adapter, mocked ───────────────────────────────────


class SecretsKeychainAdapterTest(CredsTestCase):
    """Mocks `subprocess.run` and `shutil.which` — never a real keychain."""

    def setUp(self):
        super().setUp()
        os.environ["DEVTEAM_PLATFORM"] = "darwin"

    def test_put_never_places_the_value_on_argv_only_on_stdin(self):
        calls = []

        def fake_run(args, input=None, capture_output=True, timeout=None, start_new_session=False):  # noqa: A002
            # `args` is the full argv `_run_security` builds: ["security", <subcommand>, ...].
            calls.append((list(args), input))
            if args[1] == "-i":
                return mock.Mock(returncode=0, stdout=b"", stderr=b"")
            if args[1] == "find-generic-password":
                return mock.Mock(returncode=0, stdout=(PLANTED + "\n").encode("utf-8"), stderr=b"")
            raise AssertionError("unexpected security invocation: {}".format(args))

        with mock.patch("devteam.secrets.subprocess.run", side_effect=fake_run):
            secrets_module.put("devteam/proj/tok", PLANTED, backend="keychain")

        self.assertEqual(len(calls), 2, "put must write, then read back to verify")
        write_argv, write_stdin = calls[0]
        for token in write_argv:
            self.assertNotIn(PLANTED, token, "the value must never appear in argv")
        # The whole command goes to `security -i` on stdin; a bare `-w` would go
        # through readpassphrase, which cuts a value at 128 characters.
        self.assertEqual(write_argv, ["security", "-i"])
        line = write_stdin.decode("utf-8")
        self.assertTrue(line.startswith("add-generic-password -a devteam/proj/tok -s dev-team-agents -U -w "))
        self.assertTrue(line.endswith("\n"))
        self.assertEqual(line.count("\n"), 1)

    def test_put_quotes_the_value_so_it_reads_back_unchanged(self):
        # `security -i` honours backslash escapes inside double quotes, like a POSIX
        # shell does for `\` and `"`; shlex stands in for it here (the real binary
        # was checked by hand: spaces, quotes, backslashes, `$`, backticks).
        import shlex

        for value in ['plain', 'sp ace', 'q"uo"te', 'back\\slash\\', "it's", "ATATT3x" + "aB9-_=" * 30]:
            word = secrets_module._quote_for_security(value)
            self.assertEqual(shlex.split(word), [value])

    def test_put_refuses_a_value_over_the_keychain_limit_before_calling_security(self):
        with mock.patch("devteam.secrets.subprocess.run") as run:
            with self.assertRaises(SecretError) as ctx:
                secrets_module.put("devteam/proj/tok", "x" * (secrets_module.KEYCHAIN_VALUE_MAX_BYTES + 1), backend="keychain")
        run.assert_not_called()
        self.assertIn("insecure", ctx.exception.hint)
        # A token of a realistic length is well inside it.
        self.assertGreater(secrets_module.KEYCHAIN_VALUE_MAX_BYTES, 1024)

    def test_put_failure_never_echoes_the_value_from_stderr(self):
        failed = mock.Mock(returncode=1, stdout=b"", stderr=("bad: " + PLANTED).encode("utf-8"))
        with mock.patch("devteam.secrets.subprocess.run", return_value=failed):
            with self.assertRaises(SecretError) as ctx:
                secrets_module.put("devteam/proj/tok", PLANTED, backend="keychain")
        self.assertNotIn(PLANTED, str(ctx.exception))
        self.assertIn("<redacted>", str(ctx.exception))

    def test_every_security_call_runs_without_a_controlling_terminal(self):
        # With a controlling tty, `add-generic-password -w` prompts on /dev/tty and
        # ignores stdin, so a CLI started under a terminal hung until the timeout.
        sessions = []

        def fake_run(args, input=None, capture_output=True, timeout=None, start_new_session=False):  # noqa: A002
            sessions.append(start_new_session)
            if args[1] == "find-generic-password":
                return mock.Mock(returncode=0, stdout=(PLANTED + "\n").encode("utf-8"), stderr=b"")
            return mock.Mock(returncode=0, stdout=b"", stderr=b"")

        with mock.patch("devteam.secrets.subprocess.run", side_effect=fake_run):
            secrets_module.put("devteam/proj/tok", PLANTED, backend="keychain")
            secrets_module.get("devteam/proj/tok", backend="keychain")
            secrets_module.delete("devteam/proj/tok", backend="keychain")

        self.assertTrue(sessions)
        self.assertTrue(all(sessions), "a `security` call kept the controlling terminal")

    def test_put_verifies_by_reading_back_and_deletes_on_mismatch(self):
        # A cut or mangled value can still exit 0; put() must not trust the exit
        # code alone.
        calls = []

        def fake_run(args, input=None, capture_output=True, timeout=None, start_new_session=False):  # noqa: A002
            calls.append(list(args))
            if args[1] == "-i":
                return mock.Mock(returncode=0, stdout=b"", stderr=b"")
            if args[1] == "find-generic-password":
                return mock.Mock(returncode=0, stdout=b"\n")  # empty password read back
            if args[1] == "delete-generic-password":
                return mock.Mock(returncode=0, stdout=b"", stderr=b"")
            raise AssertionError(args)

        with mock.patch("devteam.secrets.subprocess.run", side_effect=fake_run):
            with self.assertRaises(SecretError) as ctx:
                secrets_module.put("devteam/proj/tok", PLANTED, backend="keychain")
        self.assertNotIn(PLANTED, str(ctx.exception))
        self.assertIn("delete-generic-password", [c[1] for c in calls])

    def test_get_returncode_44_means_not_found_not_an_error(self):
        with mock.patch(
            "devteam.secrets.subprocess.run",
            return_value=mock.Mock(returncode=44, stdout=b"", stderr=b""),
        ):
            self.assertIsNone(secrets_module.get("devteam/proj/tok", "keychain"))

    def test_get_nonzero_returncode_raises_with_safe_stderr_never_the_value(self):
        with mock.patch(
            "devteam.secrets.subprocess.run",
            return_value=mock.Mock(returncode=51, stdout=b"", stderr=b"SecKeychainSearchCopyNext: locked"),
        ):
            with self.assertRaises(SecretError) as ctx:
                secrets_module.get("devteam/proj/tok", "keychain")
        self.assertIn("locked", str(ctx.exception))

    def test_delete_returncode_44_returns_false(self):
        with mock.patch(
            "devteam.secrets.subprocess.run",
            return_value=mock.Mock(returncode=44, stdout=b"", stderr=b""),
        ):
            self.assertFalse(secrets_module.delete("devteam/proj/tok", "keychain"))

    def test_run_security_binary_missing_raises_actionable_secreterror(self):
        with mock.patch("devteam.secrets.subprocess.run", side_effect=FileNotFoundError()):
            with self.assertRaises(SecretError) as ctx:
                secrets_module.get("devteam/proj/tok", "keychain")
        self.assertIn("hint", ctx.exception.__dict__)
        self.assertTrue(ctx.exception.hint)

    def test_run_security_timeout_raises_actionable_secreterror_not_hang(self):
        import subprocess as real_subprocess

        with mock.patch(
            "devteam.secrets.subprocess.run",
            side_effect=real_subprocess.TimeoutExpired(cmd="security", timeout=10.0),
        ):
            with self.assertRaises(SecretError) as ctx:
                secrets_module.get("devteam/proj/tok", "keychain")
        self.assertIn("locked", ctx.exception.hint or ctx.exception.message)

    def test_probe_keychain_reports_missing_binary_without_shelling_out(self):
        with mock.patch("devteam.secrets.shutil.which", return_value=None):
            self.assertIn("not found", secrets_module.describe()["probed"]["keychain"])

    def test_probe_keychain_none_only_on_darwin_with_working_security(self):
        with mock.patch("devteam.secrets.shutil.which", return_value="/usr/bin/security"):
            with mock.patch(
                "devteam.secrets.subprocess.run", return_value=mock.Mock(returncode=0)
            ):
                self.assertIsNone(secrets_module.describe()["probed"]["keychain"])

    def test_put_requires_darwin_even_if_caller_forces_backend(self):
        os.environ["DEVTEAM_PLATFORM"] = "linux"
        with self.assertRaises(SecretError):
            secrets_module.put("devteam/proj/tok", PLANTED, backend="keychain")


# ── secrets.py — dpapi adapter, mocked except where this interpreter is itself
# ── Windows, in which case the probe below is real, not a simulation ──


class SecretsDpapiAdapterTest(CredsTestCase):
    def test_probed_availability_matches_whether_windll_actually_exists(self):
        # `ctypes.windll` does not exist on a non-Windows CPython build — that is
        # what `_probe_dpapi` itself keys on — so dpapi must never be offered
        # there even when `DEVTEAM_PLATFORM` says win32. The suite now also runs
        # on a real Windows interpreter, where `ctypes.windll` genuinely exists
        # and the probe is no longer a simulation: dpapi is expected to be
        # offered there. This asserts whichever of the two is actually true for
        # the interpreter running the test, rather than assuming the first
        # unconditionally — an assumption this repository's CI could not
        # previously check, having never run on Windows.
        os.environ["DEVTEAM_PLATFORM"] = "win32"
        backends = secrets_module.available_backends()
        if hasattr(ctypes, "windll"):
            self.assertIn("dpapi", backends)
        else:
            self.assertNotIn("dpapi", backends)

    def test_put_get_delete_require_windows(self):
        for platform in ("darwin", "linux"):
            os.environ["DEVTEAM_PLATFORM"] = platform
            with self.assertRaises(SecretError):
                secrets_module._dpapi_put("devteam/proj/tok", PLANTED)
            with self.assertRaises(SecretError):
                secrets_module._dpapi_get("devteam/proj/tok")
            with self.assertRaises(SecretError):
                secrets_module._dpapi_delete("devteam/proj/tok")

    def test_put_get_roundtrip_with_a_fake_crypt32(self):
        """Exercises the envelope (base64 + jsonio) around a faked DPAPI call.

        `CryptProtectData`/`CryptUnprotectData` are simulated as a reversible
        transform so the test proves `_dpapi_put`/`_dpapi_get` wire the blob
        through correctly, without touching any real Windows API.
        """
        os.environ["DEVTEAM_PLATFORM"] = "win32"

        marker = b"\x01\x02"

        def fake_crypt_protect_data(in_blob_ptr, *rest):
            in_blob = in_blob_ptr._obj if hasattr(in_blob_ptr, "_obj") else in_blob_ptr
            out_blob_ptr = rest[-1]
            raw = secrets_module.ctypes.string_at(in_blob.pbData, in_blob.cbData)
            protected = marker + raw
            buf = secrets_module.ctypes.create_string_buffer(protected, len(protected))
            out_obj = out_blob_ptr._obj if hasattr(out_blob_ptr, "_obj") else out_blob_ptr
            out_obj.cbData = len(protected)
            out_obj.pbData = secrets_module.ctypes.cast(buf, secrets_module.ctypes.POINTER(secrets_module.ctypes.c_char))
            out_obj._keepalive = buf
            return 1

        def fake_crypt_unprotect_data(in_blob_ptr, *rest):
            in_blob = in_blob_ptr._obj if hasattr(in_blob_ptr, "_obj") else in_blob_ptr
            out_blob_ptr = rest[-1]
            raw = secrets_module.ctypes.string_at(in_blob.pbData, in_blob.cbData)
            self.assertEqual(raw[: len(marker)], marker, "unprotect got something protect never wrote")
            original = raw[len(marker):]
            buf = secrets_module.ctypes.create_string_buffer(original, len(original))
            out_obj = out_blob_ptr._obj if hasattr(out_blob_ptr, "_obj") else out_blob_ptr
            out_obj.cbData = len(original)
            out_obj.pbData = secrets_module.ctypes.cast(buf, secrets_module.ctypes.POINTER(secrets_module.ctypes.c_char))
            out_obj._keepalive = buf
            return 1

        fake_crypt32 = mock.Mock()
        fake_crypt32.CryptProtectData.side_effect = fake_crypt_protect_data
        fake_crypt32.CryptUnprotectData.side_effect = fake_crypt_unprotect_data
        fake_kernel32 = mock.Mock()
        fake_windll = mock.Mock(crypt32=fake_crypt32, kernel32=fake_kernel32)

        with mock.patch.object(secrets_module.ctypes, "windll", fake_windll, create=True):
            secrets_module._dpapi_put("devteam/proj/tok", PLANTED)
            got = secrets_module._dpapi_get("devteam/proj/tok")
        self.assertEqual(got, PLANTED)
        # The on-disk envelope must be base64, never the raw value.
        assert_value_absent_from_tree(self, paths.secrets_dir().parent, value=PLANTED)


# ── secrets.py — dpapi adapter, for real, where the host has one ────────────
# Gated on the host itself rather than on `_probe_dpapi()`, deliberately: that
# function reads `paths.platform_key()`, which every test in this file steers
# through `DEVTEAM_PLATFORM`, so using it as the gate would let a leaked env var
# decide whether these tests run. `os.name`/`ctypes.windll` cannot be steered.
# The probe is then asserted *inside* the first test, so it is checked rather
# than trusted.
_HOST_HAS_DPAPI = os.name == "nt" and hasattr(ctypes, "windll")


@unittest.skipUnless(_HOST_HAS_DPAPI, "no real DPAPI on this host")
class SecretsDpapiRealRoundTripTest(CredsTestCase):
    """The real `CryptProtectData`/`CryptUnprotectData`, not a reversible fake.

    `secrets.py` marks its dpapi section UNVERIFIED, and until this repository's
    CI gained a `windows-latest` runner that was the only honest label available:
    the code was written against the documented Win32 pattern and had never once
    executed. The mocked round-trip above proves the envelope (base64 + jsonio)
    and cannot prove anything about DPAPI, because it *is* the part it fakes.

    Four things only a real call can establish, and each has its own test below:

    * the `crypt32` entry points resolve and succeed for this user profile;
    * the stored blob is genuinely ciphertext — the fake's `marker + raw`
      contains the plaintext verbatim, so the assertion below is one the fake
      would fail, which is what makes it worth writing;
    * `_dpapi_bytes_from_blob` copies out of the returned buffer *before*
      `LocalFree` releases it. Reversed, that reads freed memory: garbage, or a
      crash. No fake allocates through `LocalAlloc`, so no fake can test it;
    * a DPAPI blob is integrity-protected, so a tampered one must fail rather
      than decrypt to something else.
    """

    REF = "devteam/proj/real-dpapi"

    def setUp(self):
        super().setUp()
        # `CredsTestCase` pins linux so the keychain probe never shells out. The
        # dpapi adapter refuses any platform but win32, so this test needs it back.
        os.environ["DEVTEAM_PLATFORM"] = "win32"

    def _stored(self):
        return json.loads(secrets_module._dpapi_path(self.REF).read_text(encoding="utf-8"))

    def test_the_probe_agrees_that_this_host_can_use_dpapi(self):
        # If this fails, every skip in this class was hiding a broken probe rather
        # than an absent capability.
        self.assertIsNone(secrets_module._probe_dpapi())
        self.assertIn("dpapi", secrets_module.available_backends())

    def test_a_value_round_trips_through_the_public_put_and_get(self):
        result = secrets_module.put(self.REF, PLANTED, backend="dpapi")
        self.assertEqual(result["backend"], "dpapi")
        self.assertFalse(result["insecure"])
        self.assertTrue(secrets_module._dpapi_path(self.REF).is_file())
        self.assertEqual(secrets_module.get(self.REF, "dpapi"), PLANTED)

    def test_the_stored_blob_is_ciphertext_and_not_the_value(self):
        """The assertion the reversible fake would fail.

        Also the file's own central promise, applied to the one backend that
        keeps a value on disk: nothing under the store may contain it.
        """
        secrets_module.put(self.REF, PLANTED, backend="dpapi")
        blob = base64.b64decode(self._stored()["blob_b64"])
        self.assertNotIn(PLANTED.encode("utf-8"), blob)
        self.assertGreater(len(blob), len(PLANTED), "a DPAPI blob carries a header and a MAC")
        assert_value_absent_from_tree(self, paths.secrets_dir().parent, value=PLANTED)

    def test_a_tampered_blob_is_refused_instead_of_decrypting_to_something_else(self):
        """DPAPI authenticates what it protects; this asserts we surface that.

        The failure must arrive as `SecretError` and must not quote the value —
        an error path is the easiest place for a secret to escape into a log.
        """
        secrets_module.put(self.REF, PLANTED, backend="dpapi")
        path = secrets_module._dpapi_path(self.REF)
        blob = bytearray(base64.b64decode(self._stored()["blob_b64"]))
        # Corrupted in the middle, across several bytes, rather than at one end.
        # The blob's layout is not a documented contract, so a single flip at the
        # tail could land in padding or a length field and fail for the wrong
        # reason — or, worse, not fail at all and make this test vacuous. A run
        # through the middle is inside the ciphertext whatever the layout is.
        middle = len(blob) // 2
        for offset in range(middle, min(middle + 8, len(blob))):
            blob[offset] ^= 0xFF
        path.write_text(
            json.dumps({"blob_b64": base64.b64encode(bytes(blob)).decode("ascii")}),
            encoding="utf-8",
        )
        with self.assertRaises(SecretError) as caught:
            secrets_module.get(self.REF, "dpapi")
        self.assertNotIn(PLANTED, str(caught.exception))

    def test_a_non_ascii_value_survives_the_utf8_encode_decode(self):
        # `_dpapi_put` encodes utf-8 and `_dpapi_get` decodes it; a byte-length
        # assumption anywhere in between shows up here and nowhere else.
        value = "s3cr3t-ação-日本語-ß"
        secrets_module.put(self.REF, value, backend="dpapi")
        self.assertEqual(secrets_module.get(self.REF, "dpapi"), value)

    def test_a_long_value_round_trips(self):
        # One buffer sized from the wrong length would truncate, and a short
        # value can hide that inside DPAPI's own block padding.
        value = "x" * 4096
        secrets_module.put(self.REF, value, backend="dpapi")
        self.assertEqual(secrets_module.get(self.REF, "dpapi"), value)

    def test_two_refs_do_not_share_a_blob(self):
        other = "devteam/proj/real-dpapi-two"
        secrets_module.put(self.REF, PLANTED, backend="dpapi")
        secrets_module.put(other, PLANTED + "-other", backend="dpapi")
        self.assertNotEqual(secrets_module._dpapi_path(self.REF), secrets_module._dpapi_path(other))
        self.assertEqual(secrets_module.get(self.REF, "dpapi"), PLANTED)
        self.assertEqual(secrets_module.get(other, "dpapi"), PLANTED + "-other")

    def test_get_answers_none_for_a_ref_that_was_never_stored(self):
        # Absent is not an error: `get` returning None is what `creds.py` keys on.
        self.assertIsNone(secrets_module.get("devteam/proj/never-stored", "dpapi"))

    def test_delete_removes_the_blob_and_is_false_the_second_time(self):
        secrets_module.put(self.REF, PLANTED, backend="dpapi")
        self.assertTrue(secrets_module.delete(self.REF, "dpapi"))
        self.assertFalse(secrets_module._dpapi_path(self.REF).exists())
        self.assertIsNone(secrets_module.get(self.REF, "dpapi"))
        self.assertFalse(secrets_module.delete(self.REF, "dpapi"))


# ── creds.py — schema and validation ────────────────────────────────────────


class CredsSchemaValidationTest(CredsTestCase):
    def test_non_secret_keys_are_exactly_the_documented_two(self):
        self.assertEqual(
            creds.NON_SECRET_KEYS, ("work_feedback_active", "work_feedback_interval_minutes")
        )

    def test_a_newer_schema_is_refused_not_rewritten(self):
        path = paths.credentials_file("proj-1")
        jsonio_write(path, {"schema": 99, "credentials": {}})
        before = path.read_text(encoding="utf-8")
        with self.assertRaises(EnvError) as ctx:
            creds.load("proj-1")
        self.assertIn("newer", str(ctx.exception))
        self.assertEqual(path.read_text(encoding="utf-8"), before, "must not rewrite a newer file")

    def test_a_malformed_file_is_named_in_the_error_not_overwritten(self):
        path = paths.credentials_file("proj-1")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{not json", encoding="utf-8")
        with self.assertRaises(EnvError) as ctx:
            creds.load("proj-1")
        self.assertIn(str(path), str(ctx.exception))
        self.assertEqual(path.read_text(encoding="utf-8"), "{not json")

    def test_entry_with_a_value_looking_field_is_rejected(self):
        for field in ("value", "secret", "password", "token", "api_key"):
            path = paths.credentials_file("proj-{}".format(field))
            jsonio_write(
                path,
                {
                    "schema": 1,
                    "credentials": {
                        "k": {
                            "purpose": "p",
                            "source": "insecure",
                            "ref": "devteam/x/k",
                            "scope": [],
                            field: PLANTED,
                        }
                    },
                },
            )
            with self.assertRaises(EnvError) as ctx:
                creds.load("proj-{}".format(field))
            self.assertIn(field, str(ctx.exception))
            self.assertNotIn(PLANTED, str(ctx.exception))

    def test_entry_with_an_unexpected_but_innocuous_field_is_also_rejected(self):
        path = paths.credentials_file("proj-x")
        jsonio_write(
            path,
            {
                "schema": 1,
                "credentials": {
                    "k": {
                        "purpose": "p",
                        "source": "insecure",
                        "ref": "devteam/x/k",
                        "scope": [],
                        "notes": "unexpected",
                    }
                },
            },
        )
        with self.assertRaises(EnvError):
            creds.load("proj-x")

    def test_require_valid_key_rejects_shapes_a_backend_ref_or_cli_arg_would_choke_on(self):
        for bad in ("", "-leading", " has space", "has/slash"):
            with self.assertRaises(UsageError):
                creds.resolve(bad, "proj-1")


def jsonio_write(path, data):
    from devteam import jsonio

    jsonio.write_json_atomic(path, data)


# ── creds.py — resolution and listing ───────────────────────────────────────


class CredsResolveAndListTest(CredsTestCase):
    def test_project_layer_overrides_global(self):
        creds.set_entry("k", "global purpose", project_id=None, value="global-val", backend="insecure")
        creds.set_entry("k", "project purpose", project_id="proj-1", value="project-val", backend="insecure")
        entry, layer = creds.resolve("k", "proj-1")
        self.assertEqual(layer, "project")
        self.assertEqual(entry["purpose"], "project purpose")

    def test_key_present_only_globally_resolves_from_global(self):
        creds.set_entry("only-global", "p", project_id=None, value="v", backend="insecure")
        entry, layer = creds.resolve("only-global", "proj-1")
        self.assertEqual(layer, "global")

    def test_missing_key_resolves_to_none_none_not_an_error(self):
        entry, layer = creds.resolve("nope", "proj-1")
        self.assertIsNone(entry)
        self.assertIsNone(layer)

    def test_list_entries_merges_layers_project_overriding_global_and_carries_no_value(self):
        creds.set_entry("shared", "purpose A", project_id=None, value="value-global-xyz", backend="insecure")
        creds.set_entry("shared", "purpose B", project_id="proj-1", value="value-project-xyz", backend="insecure")
        creds.set_entry("only-project", "purpose C", project_id="proj-1", value="value-only-xyz", backend="insecure")
        entries = creds.list_entries("proj-1")
        by_key = {e["key"]: e for e in entries}
        self.assertEqual(by_key["shared"]["layer"], "project")
        self.assertEqual(by_key["shared"]["purpose"], "purpose B")
        self.assertEqual(by_key["only-project"]["layer"], "project")
        self.assertEqual(set(by_key["shared"].keys()), {"key", "purpose", "source", "ref", "scope", "layer"})
        serialized = json.dumps(entries)
        for value in ("value-global-xyz", "value-project-xyz", "value-only-xyz"):
            self.assertNotIn(value, serialized)

    def test_list_entries_without_a_project_id_shows_only_global(self):
        creds.set_entry("g1", "p", project_id=None, value="v", backend="insecure")
        creds.set_entry("proj-only", "p", project_id="proj-1", value="v", backend="insecure")
        entries = creds.list_entries(None)
        self.assertEqual([e["key"] for e in entries], ["g1"])


# ── creds.py — get_value: scope, audit, and the leak-scan invariant ─────────


class CredsGetValueTest(CredsTestCase):
    def setUp(self):
        super().setUp()
        creds.set_entry(
            "scoped",
            "needs scope",
            ref_scope=["backend-developer"],
            project_id="proj-1",
            value=PLANTED,
            backend="insecure",
        )
        creds.set_entry(
            "unscoped", "any agent", project_id="proj-1", value=PLANTED, backend="insecure"
        )

    def test_successful_get_returns_the_exact_value_and_audits_ok(self):
        value = creds.get_value("unscoped", "proj-1", agent="backend-developer")
        self.assertEqual(value, PLANTED)
        lines = _read_audit_lines("proj-1")
        self.assertEqual(lines[-1]["outcome"], "ok")
        self.assertEqual(lines[-1]["agent"], "backend-developer")

    def test_agent_in_scope_is_allowed(self):
        value = creds.get_value("scoped", "proj-1", agent="backend-developer")
        self.assertEqual(value, PLANTED)

    def test_agent_not_in_scope_is_refused_and_audited(self):
        with self.assertRaises(EnvError) as ctx:
            creds.get_value("scoped", "proj-1", agent="frontend-developer")
        self.assertNotIn(PLANTED, str(ctx.exception))
        lines = _read_audit_lines("proj-1")
        self.assertEqual(lines[-1]["outcome"], "scope-refused")
        self.assertEqual(lines[-1]["agent"], "frontend-developer")

    def test_scope_is_documented_as_hygiene_not_a_sandbox_in_the_refusal_hint(self):
        with self.assertRaises(EnvError) as ctx:
            creds.get_value("scoped", "proj-1", agent="frontend-developer")
        self.assertIn("not a sandbox", ctx.exception.hint)

    def test_agent_none_is_allowed_even_with_a_nonempty_scope_and_recorded_as_unidentified(self):
        value = creds.get_value("scoped", "proj-1", agent=None)
        self.assertEqual(value, PLANTED)
        lines = _read_audit_lines("proj-1")
        self.assertEqual(lines[-1]["outcome"], "ok")
        self.assertIsNone(lines[-1]["agent"])

    def test_unregistered_key_raises_and_audits_not_registered(self):
        with self.assertRaises(EnvError):
            creds.get_value("never-set", "proj-1")
        lines = _read_audit_lines("proj-1")
        self.assertEqual(lines[-1]["outcome"], "not-registered")

    def test_registered_but_no_value_stored_raises_and_audits_value_missing(self):
        creds.set_entry("no-value-yet", "p", project_id="proj-1")  # no `value=`
        with self.assertRaises(EnvError) as ctx:
            creds.get_value("no-value-yet", "proj-1")
        self.assertNotIn(PLANTED, str(ctx.exception))
        lines = _read_audit_lines("proj-1")
        self.assertEqual(lines[-1]["outcome"], "value-missing")

    def test_audit_log_never_contains_the_value_across_every_outcome_exercised(self):
        creds.get_value("unscoped", "proj-1", agent="x")
        with self.assertRaises(EnvError):
            creds.get_value("scoped", "proj-1", agent="not-allowed")
        with self.assertRaises(EnvError):
            creds.get_value("does-not-exist", "proj-1")
        # Scoped to the audit log itself, never `secrets_dir()` — the `insecure`
        # backend's job there is literally to hold the raw value; the invariant is
        # about the reference layer and the audit trail, not the value store.
        assert_value_absent_from_tree(self, paths.audit_log("proj-1"))

    def test_reference_files_never_contain_the_value(self):
        assert_value_absent_from_tree(self, paths.credentials_dir())


def _read_audit_lines(project_id):
    path = paths.audit_log(project_id)
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


# ── creds.py — unset ─────────────────────────────────────────────────────────


class CredsUnsetTest(CredsTestCase):
    def test_unset_keeps_the_value_by_default(self):
        creds.set_entry("k", "p", project_id="proj-1", value=PLANTED, backend="insecure")
        result = creds.unset("k", project_id="proj-1")
        self.assertEqual(result, {"key": "k", "removed": True, "value_removed": False})
        self.assertEqual(secrets_module.get("devteam/proj-1/k", "insecure"), PLANTED)

    def test_unset_with_forget_value_deletes_the_backend_value_too(self):
        creds.set_entry("k", "p", project_id="proj-1", value=PLANTED, backend="insecure")
        result = creds.unset("k", project_id="proj-1", forget_value=True)
        self.assertTrue(result["value_removed"])
        self.assertIsNone(secrets_module.get("devteam/proj-1/k", "insecure"))

    def test_unset_of_a_key_that_was_never_set_reports_not_removed(self):
        result = creds.unset("ghost", project_id="proj-1")
        self.assertEqual(result, {"key": "ghost", "removed": False, "value_removed": False})


# ── creds.py — import_file: copy -> verify -> retire ────────────────────────


class CredsImportFileTest(CredsTestCase):
    def test_success_moves_original_to_quarantine_and_keeps_non_secret_keys_as_plain_values(self):
        source = self.tmp / "credentials.local.json"
        jsonio_write(
            source,
            {
                "db_password": PLANTED,
                "work_feedback_active": True,
                "work_feedback_interval_minutes": 30,
            },
        )
        result = creds.import_file(source, "proj-1")

        self.assertEqual(result["imported"], ["db_password"])
        self.assertEqual(result["non_secret"], ["work_feedback_active", "work_feedback_interval_minutes"])
        self.assertFalse(source.exists(), "the original must be retired, never left in place")
        self.assertIsNotNone(result["quarantined_to"])
        quarantined_path = Path(result["quarantined_to"])
        self.assertTrue(quarantined_path.exists())
        self.assertEqual(json.loads(quarantined_path.read_text(encoding="utf-8"))["db_password"], PLANTED)

        data = creds.load("proj-1")
        self.assertEqual(data["work_feedback_active"], True)
        self.assertEqual(data["work_feedback_interval_minutes"], 30)
        self.assertNotIn("work_feedback_active", data["credentials"])
        entry = data["credentials"]["db_password"]
        self.assertEqual(set(entry.keys()), {"purpose", "source", "ref", "scope"})

        # The reference file, on disk, must never carry the value.
        assert_value_absent_from_tree(self, paths.credentials_dir())
        self.assertEqual(secrets_module.get(entry["ref"], entry["source"]), PLANTED)

    def test_failure_partway_through_leaves_the_original_untouched_and_nothing_written(self):
        source = self.tmp / "credentials.local.json"
        jsonio_write(source, {"first": "value-one", "second": PLANTED})
        original_bytes = source.read_bytes()

        real_put = secrets_module.put
        calls = {"n": 0}

        def flaky_put(ref, value, backend=None):
            calls["n"] += 1
            if calls["n"] == 2:
                raise SecretError("simulated backend failure")
            return real_put(ref, value, backend=backend)

        with mock.patch("devteam.creds.secrets_module.put", side_effect=flaky_put):
            with self.assertRaises(SecretError):
                creds.import_file(source, "proj-1")

        self.assertTrue(source.exists(), "the original must survive a failed import")
        self.assertEqual(source.read_bytes(), original_bytes)
        # Nothing was quarantined, and the reference file was never touched.
        self.assertFalse(paths.credentials_file("proj-1").exists())
        self.assertEqual(secrets_module.get("devteam/proj-1/first", "insecure"), None)

    def test_import_only_acts_on_the_named_path_never_scans_the_directory(self):
        # ADR-0010's proof case: this repository's own root credentials.local.json
        # is read on purpose by a committed prompt and must never be swept up by
        # an importer that goes looking for candidates on its own.
        target = self.tmp / "wanted.json"
        sibling = self.tmp / "credentials.local.json"
        jsonio_write(target, {"wanted_key": "wanted-value"})
        jsonio_write(sibling, {"untouched_key": PLANTED})

        creds.import_file(target, "proj-1")

        self.assertTrue(sibling.exists(), "a file not named must be left completely alone")
        self.assertEqual(json.loads(sibling.read_text(encoding="utf-8"))["untouched_key"], PLANTED)
        data = creds.load("proj-1")
        self.assertNotIn("untouched_key", data["credentials"])

    def test_import_of_a_non_string_value_is_rejected_before_anything_is_stored(self):
        source = self.tmp / "bad.json"
        jsonio_write(source, {"bad_key": 12345})
        with self.assertRaises(EnvError):
            creds.import_file(source, "proj-1")
        self.assertTrue(source.exists())


# ── creds.py / doctor.py — check and severity mapping ───────────────────────


class CredsCheckAndDoctorTest(CredsTestCase):
    def test_check_flags_missing_value(self):
        # `default_backend()` resolves to `insecure` in this sandbox (keychain and
        # dpapi are both forced unavailable), so an entry with no value stored also
        # trips `insecure-backend` — assert membership, not an exact finding list.
        creds.set_entry("k", "p", project_id="proj-1")  # reference with no value
        issues = {f["issue"] for f in creds.check("proj-1")}
        self.assertIn("missing-value", issues)

    def test_check_flags_insecure_backend_loudly(self):
        creds.set_entry("k", "p", project_id="proj-1", value=PLANTED, backend="insecure")
        findings = creds.check("proj-1")
        issues = {f["issue"] for f in findings}
        self.assertIn("insecure-backend", issues)

    def test_an_unrecognised_source_is_reported_not_fatal(self):
        # REGRESSION: `_validate` used to refuse any `source` outside `BACKENDS`, which
        # made `devteam cred list` and `devteam doctor` fail hard on a file written by a
        # newer CLI or restored from a machine with a backend this build lacks — and it
        # made `check()`'s own `unknown-source` finding unreachable, which is how the
        # dead branch was found. Structure is validated; the set of known backends is a
        # finding, not a parse error.
        path = paths.credentials_file("proj-1")
        jsonio_write(
            path,
            {
                "schema": 1,
                "credentials": {
                    "k": {"purpose": "p", "source": "vault", "ref": "devteam/x/k", "scope": []}
                },
            },
        )
        findings = creds.check("proj-1")
        unknown = [f for f in findings if f["issue"] == "unknown-source"]
        self.assertEqual(len(unknown), 1, findings)
        self.assertEqual(unknown[0]["detail"], "vault")
        # Still describable rather than fatal: the reference is listable.
        self.assertIn("k", {e["key"] for e in creds.list_entries("proj-1")})

    def test_a_source_that_is_not_a_string_is_still_a_parse_error(self):
        # The structural half of the same rule: an absent or empty `source` is not a
        # newer backend, it is a malformed entry.
        path = paths.credentials_file("proj-2")
        jsonio_write(
            path,
            {
                "schema": 1,
                "credentials": {"k": {"purpose": "p", "source": "", "ref": "r", "scope": []}},
            },
        )
        with self.assertRaises(EnvError):
            creds.check("proj-2")

    def test_check_never_raises_it_only_reports(self):
        creds.set_entry("k1", "p", project_id="proj-1", value=PLANTED, backend="insecure")
        creds.set_entry("k2", "p", project_id="proj-1")
        findings = creds.check("proj-1")  # must not raise despite a missing value
        self.assertTrue(any(f["issue"] == "missing-value" for f in findings))

    def test_doctor_maps_missing_value_to_fail_and_insecure_backend_to_warn(self):
        missing = doctor._credential_finding({"key": "k", "layer": "project", "issue": "missing-value"})
        insecure = doctor._credential_finding({"key": "k", "layer": "project", "issue": "insecure-backend"})
        unknown_source = doctor._credential_finding(
            {"key": "k", "layer": "project", "issue": "unknown-source", "detail": "vault"}
        )
        self.assertEqual(missing["level"], doctor.FAIL)
        self.assertEqual(insecure["level"], doctor.WARN)
        # Exercised directly since `creds.check()` can never actually produce this
        # finding shape today (see the SOURCE DEFECT test above) — the mapping
        # table itself is still real code worth pinning.
        self.assertEqual(unknown_source["level"], doctor.FAIL)


# ── CLI: devteam cred ... ────────────────────────────────────────────────────


class CredCliTest(StoreTestCase):
    def setUp(self):
        super().setUp()
        os.environ["DEVTEAM_PLATFORM"] = "linux"  # keep `cred backends` off the real keychain

    def test_cred_get_prints_exactly_the_value_and_a_newline_nothing_else(self):
        creds.set_entry("k", "p", project_id=None, value=PLANTED, backend="insecure")
        code, out, err = self.run_cli("cred", "get", "k", "--global")
        self.assertEqual(code, 0, err)
        self.assertEqual(out, PLANTED + "\n")

    def test_cred_get_with_json_is_refused_as_a_usage_error(self):
        creds.set_entry("k", "p", project_id=None, value=PLANTED, backend="insecure")
        code, out, err = self.run_cli("cred", "get", "k", "--global", "--json")
        self.assertEqual(code, 2)
        body = json.loads(out)
        self.assertFalse(body["ok"])
        self.assertNotIn(PLANTED, out)
        self.assertNotIn(PLANTED, err)

    def test_cred_set_reads_the_value_from_stdin_never_from_argv(self):
        code, out, err = self.run_cli(
            "cred",
            "set",
            "k",
            "--purpose",
            "test",
            "--global",
            "--backend",
            "insecure",
            input_text=PLANTED + "\n",
        )
        self.assertEqual(code, 0, err)
        self.assertEqual(secrets_module.get("devteam/global/k", "insecure"), PLANTED)
        # The value must not have been echoed anywhere on the CLI's own output.
        self.assertNotIn(PLANTED, out)
        self.assertNotIn(PLANTED, err)

    def test_cred_set_with_empty_stdin_is_a_usage_error(self):
        code, out, err = self.run_cli(
            "cred", "set", "k", "--purpose", "test", "--global", "--backend", "insecure",
            input_text="",
        )
        self.assertEqual(code, 2)
        self.assertIn("no value", (out + err).lower())

    def test_cred_list_json_never_contains_a_planted_value(self):
        creds.set_entry("k", "p", project_id=None, value=PLANTED, backend="insecure")
        code, out, err = self.run_cli("cred", "list", "--global", "--json")
        self.assertEqual(code, 0, err)
        self.assertNotIn(PLANTED, out)
        body = json.loads(out)
        self.assertEqual(body["credentials"][0]["key"], "k")

    def test_cred_check_json_never_contains_a_planted_value(self):
        creds.set_entry("k", "p", project_id=None, value=PLANTED, backend="insecure")
        code, out, err = self.run_cli("cred", "check", "--global", "--json")
        # Exit 1: an `insecure-backend` finding is a reported problem (ADR-0010
        # wants it loud), which `main()` maps to the "findings" exit code — not 0.
        self.assertEqual(code, 1, err)
        body = json.loads(out)
        self.assertFalse(body["ok"])
        self.assertTrue(any(f["issue"] == "insecure-backend" for f in body["findings"]))
        self.assertNotIn(PLANTED, out)

    def test_cred_unset_default_keeps_value_forget_flag_removes_it(self):
        creds.set_entry("k", "p", project_id=None, value=PLANTED, backend="insecure")
        code, out, err = self.run_cli("cred", "unset", "k", "--global")
        self.assertEqual(code, 0, err)
        self.assertEqual(secrets_module.get("devteam/global/k", "insecure"), PLANTED)

        creds.set_entry("k2", "p", project_id=None, value=PLANTED, backend="insecure")
        code, out, err = self.run_cli("cred", "unset", "k2", "--global", "--forget-value")
        self.assertEqual(code, 0, err)
        self.assertIsNone(secrets_module.get("devteam/global/k2", "insecure"))

    def test_cred_backends_reports_insecure_available_without_touching_keychain(self):
        code, out, err = self.run_cli("cred", "backends", "--json")
        self.assertEqual(code, 0, err)
        body = json.loads(out)
        self.assertIn("insecure", body["available"])
        self.assertEqual(body["default"], "insecure")

    def test_cred_commands_scoped_to_a_project_via_path_without_a_bind(self):
        # `--path` alone, with no `devteam bind` run, must fail closed: a cred
        # command scoped to a project requires that project to actually be bound.
        project_root = self.new_project()
        code, out, err = self.run_cli("cred", "list", "--path", str(project_root), "--json")
        self.assertEqual(code, 2, err)

    def test_full_project_scoped_lifecycle_through_the_cli(self):
        self.install_version("3.0.0", activate=True)
        project_root = self.new_project("credsapp")
        bound = self.run_cli("bind", str(project_root), "--json")
        self.assertEqual(bound[0], 0, bound[2])

        code, out, err = self.run_cli(
            "cred",
            "set",
            "api_key",
            "--purpose",
            "call the API",
            "--path",
            str(project_root),
            "--backend",
            "insecure",
            input_text=PLANTED + "\n",
        )
        self.assertEqual(code, 0, err)

        code, out, err = self.run_cli("cred", "get", "api_key", "--path", str(project_root))
        self.assertEqual(code, 0, err)
        self.assertEqual(out, PLANTED + "\n")

        code, out, err = self.run_cli("cred", "list", "--path", str(project_root), "--json")
        self.assertEqual(code, 0, err)
        self.assertNotIn(PLANTED, out)
        body = json.loads(out)
        self.assertEqual(body["credentials"][0]["layer"], "project")


if __name__ == "__main__":
    unittest.main()
