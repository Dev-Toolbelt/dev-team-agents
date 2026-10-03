"""Shared base for the `devteam auth` tests: a fake identity server wired in through the seam."""

from __future__ import annotations

import io
import json
import os
import subprocess
import sys
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

from auth_fakes import NEW_PASSWORD, PASSWORD, FakeIdP  # noqa: E402,F401
from devteam_support import CLI, StoreTestCase  # noqa: E402

from devteam import cli as devteam_cli  # noqa: E402

CODE = "24681357"
EMAIL = "ada@example.com"


class AuthTestCase(StoreTestCase):
    def setUp(self):
        super().setUp()
        from devteam import auth_session

        auth_session._forget_memory()
        self.addCleanup(auth_session._forget_memory)
        self.idp = FakeIdP()
        self.idp.fixed_code = CODE
        self.idp.start()
        self.addCleanup(self.idp.stop)
        os.environ.update(self.idp.env())
        self.outputs = []

    # -- running ---------------------------------------------------------------

    def run_auth(self, *args, input_text=None):
        """The real entry point in a subprocess; returns ``(code, stdout, stderr)``."""
        result = self.run_cli(*args, input_text=input_text)
        self.outputs.append(result[1] + result[2])
        return result

    def run_json(self, *args, input_text=None):
        code, out, err = self.run_auth(*args, "--json", input_text=input_text)
        self.assertTrue(out.strip(), "no JSON on stdout: {!r}".format(err))
        return code, json.loads(out), err

    def run_inproc(self, argv, stdin_text=""):
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(sys, "stdin", io.StringIO(stdin_text)):
            code = devteam_cli.main(list(argv), stdout=out, stderr=err)
        self.outputs.append(out.getvalue() + err.getvalue())
        return code, out.getvalue(), err.getvalue()

    def popen(self, *args, input_text=""):
        return subprocess.Popen(
            [sys.executable, str(CLI), *args],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=dict(os.environ),
        )

    # -- scenarios -------------------------------------------------------------

    def sign_in(self, email=EMAIL, name=None):
        """OTP sign-in in the two-step form the desktop app uses; returns the verify result."""
        start = ["auth", "otp", "start", "--email", email]
        if name:
            start += ["--name", name]
        code, body, _ = self.run_json(*start)
        self.assertEqual(code, 0, body)
        code, body, _ = self.run_json("auth", "otp", "verify", "--email", email, input_text=CODE + "\n")
        self.assertEqual(code, 0, body)
        return body

    def store_files(self):
        """Every file under the store, as ``{relative path: bytes}``."""
        found = {}
        for root, _dirs, files in os.walk(str(self.home)):
            for name in files:
                path = Path(root) / name
                found[str(path.relative_to(self.home))] = path.read_bytes()
        return found

    def session_meta(self):
        for rel, raw in self.store_files().items():
            if rel.endswith("account-session.json"):
                return json.loads(raw)
        return None
