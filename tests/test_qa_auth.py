"""``devteam qa auth`` (ADR-0054 § 3): TOTP, the session cache and the sign-in cascade.

The Node script is replaced by a fake that writes a storageState; no browser runs.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import shutil
import stat
import tempfile
import time
import unittest
from unittest import mock

from test_credentials_local import LocalCredsCase
from test_credentials_secrets import PW, FakeStore

from devteam import credentials_local as cl
from devteam import qa_auth, paths
from devteam.errors import EnvError, UsageError

RECIPE = {
    "url": "https://s.test/login",
    "username_selector": "#u",
    "password_selector": "#p",
    "submit_selector": "#go",
}
SEED = b"12345678901234567890"


class TotpTest(unittest.TestCase):
    def test_rfc_6238_sha1_vectors(self):
        for at, expected in (
            (59, "94287082"),
            (1111111109, "07081804"),
            (1111111111, "14050471"),
            (1234567890, "89005924"),
            (2000000000, "69279037"),
            (20000000000, "65353130"),
        ):
            self.assertEqual(qa_auth.hotp(SEED, at // 30, 8), expected)
            b32 = base64.b32encode(SEED).decode()
            self.assertEqual(qa_auth.totp(b32, at=at, digits=8), expected)

    def test_rfc_6238_sha256_and_sha512_vectors(self):
        self.assertEqual(qa_auth.hotp(b"12345678901234567890123456789012", 59 // 30, 8, hashlib.sha256), "46119246")
        self.assertEqual(qa_auth.hotp(b"1234567890123456789012345678901234567890123456789012345678901234", 59 // 30, 8, hashlib.sha512), "90693936")

    def test_secret_formatting_and_errors(self):
        spaced = " ".join(base64.b32encode(SEED).decode()[i:i + 4] for i in range(0, 32, 4)).lower()
        self.assertEqual(qa_auth.totp(spaced, at=59), qa_auth.totp(base64.b32encode(SEED).decode(), at=59))
        self.assertEqual(len(qa_auth.totp("JBSWY3DPEHPK3PXP")), 6)
        with self.assertRaises(ValueError):
            qa_auth.totp("not base32 !!1")


class AuthCase(LocalCredsCase):
    def write(self, doc):
        self.put(self.target, json.dumps(doc))

    def group(self, **extra):
        return {"g": dict({"login": dict(RECIPE), "username": "qa", "password": PW}, **extra)}

    def audit(self):
        log = paths.audit_log(self.pid)
        return log.read_text() if log.exists() else ""

    def fake_login(self, cookies=None, ok=True, reason=None, log=None):
        def run(payload, interactive):
            if log is not None:
                log.append((payload, interactive))
            if not ok:
                return {"ok": False, "reason": reason, "message": "nope"}
            state = {"cookies": cookies if cookies is not None else [{"name": "s", "value": "v", "expires": -1}], "origins": []}
            with open(payload["out_path"], "w") as handle:
                json.dump(state, handle)
            return {"ok": True}
        return mock.patch.object(qa_auth, "_run_login", side_effect=run)

    def auth(self, pointer="/g", **kw):
        return qa_auth.authenticate(self.root, self.pid, pointer, **kw)


class CascadeTest(AuthCase):
    def test_recipe_signs_in_and_caches(self):
        self.write(self.group())
        log = []
        with self.fake_login(log=log):
            first = self.auth()
            second = self.auth()
        self.assertEqual((first["source"], second["source"]), ("recipe", "cache"))
        self.assertEqual(len(log), 1)
        payload, interactive = log[0]
        self.assertFalse(interactive)
        self.assertEqual((payload["username"], payload["password"], payload["mode"]), ("qa", PW, "recipe"))
        self.assertEqual(payload["recipe"]["submit_selector"], "#go")
        self.assertEqual(set(first), {"path", "expires_at", "source"})
        self.assertTrue(first["path"].startswith(str(paths.machine_project_dir(self.pid) / "qa-sessions")))
        if os.name == "posix":
            self.assertEqual(stat.S_IMODE(os.stat(first["path"]).st_mode), 0o600)
        self.assertRegex(first["expires_at"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")
        self.assertNotIn(PW, self.audit())
        self.assertIn("qa-auth", self.audit())

    def test_expired_cache_is_replaced(self):
        self.write(self.group())
        with self.fake_login():
            first = self.auth()
            later = time.time() + 9 * 3600
            second = self.auth(now=later)
        self.assertEqual(second["source"], "recipe")
        self.assertEqual(second["path"], first["path"])
        self.assertEqual(len(list(qa_auth.session_dir(self.pid).iterdir())), 1)

    def test_earliest_cookie_expiry_wins(self):
        self.write(self.group())
        soon = time.time() + 600
        with self.fake_login(cookies=[{"name": "a", "value": "1", "expires": soon}, {"name": "b", "value": "2", "expires": soon + 5000}]):
            result = self.auth()
        stamp = time.mktime(time.strptime(result["expires_at"], "%Y-%m-%dT%H:%M:%SZ")) - time.timezone
        self.assertAlmostEqual(stamp, soon, delta=2)

    def test_totp_code_is_computed_here_and_the_secret_is_not_sent(self):
        secret = base64.b32encode(SEED).decode()
        self.write({"g": dict(self.group()["g"], totp_secret=secret, login=dict(RECIPE, totp_selector="#otp"))})
        log = []
        with self.fake_login(log=log):
            self.auth()
        payload = log[0][0]
        self.assertRegex(payload["totp"], r"^\d{6}$")
        self.assertNotIn(secret, json.dumps(payload))

    def test_references_are_resolved_for_the_script(self):
        with FakeStore().active():
            self.write({"g": {"login": dict(RECIPE), "username": "qa"}})
            cl.apply_patch(self.root, [{"op": "set-secret", "pointer": "/g/password", "value": PW}], cl.show(self.root)["hash"])
            log = []
            with self.fake_login(log=log):
                self.auth()
        self.assertEqual(log[0][0]["password"], PW)

    def test_no_credentials(self):
        self.write({"g": {"login": dict(RECIPE), "username": "qa"}})
        with self.assertRaises(EnvError) as ctx:
            self.auth()
        self.assertEqual(ctx.exception.details["reason"], "no-credentials")
        self.assertEqual(ctx.exception.details["missing"], ["password"])
        self.assertEqual(ctx.exception.exit_code, 3)

    def test_interactive_runs_when_there_is_no_recipe(self):
        self.write({"g": {"login": {"url": "https://s.test/login"}}})
        log = []
        with self.fake_login(log=log):
            result = self.auth(interactive=True)
        self.assertEqual((result["source"], log[0][1], log[0][0]["mode"]), ("interactive", True, "interactive"))

    def test_failed_recipe_falls_back_only_when_interactive(self):
        self.write(self.group())
        with self.fake_login(ok=False, reason="login-failed"):
            with self.assertRaises(EnvError) as ctx:
                self.auth()
        self.assertEqual(ctx.exception.details["reason"], "login-failed")
        calls = []

        def run(payload, interactive):
            calls.append(interactive)
            if not interactive:
                return {"ok": False, "reason": "login-failed", "message": "x"}
            with open(payload["out_path"], "w") as handle:
                json.dump({"cookies": [{"name": "a", "value": "b", "expires": -1}]}, handle)
            return {"ok": True}
        with mock.patch.object(qa_auth, "_run_login", side_effect=run):
            self.assertEqual(self.auth(interactive=True)["source"], "interactive")
        self.assertEqual(calls, [False, True])

    def test_playwright_missing_carries_the_install_hint(self):
        self.write(self.group())
        with self.fake_login(ok=False, reason="playwright-missing"):
            with self.assertRaises(EnvError) as ctx:
                self.auth()
        self.assertEqual(ctx.exception.details["reason"], "playwright-missing")
        self.assertIn("/devteam:install", ctx.exception.hint)

    def test_no_node_is_playwright_missing(self):
        with mock.patch.object(qa_auth.shutil, "which", return_value=None):
            with self.assertRaises(EnvError) as ctx:
                qa_auth._run_login({}, False)
        self.assertEqual(ctx.exception.details["reason"], "playwright-missing")

    def test_plaintext_password_is_refused_in_production(self):
        self.write({"p": {"$production": True, "login": dict(RECIPE), "username": "qa", "password": PW}})
        with self.fake_login() as run:
            with self.assertRaises(UsageError) as ctx:
                self.auth("/p")
            run.assert_not_called()
        self.assertEqual(ctx.exception.details["reason"], "plaintext-in-production")
        self.assertNotIn(PW, json.dumps(ctx.exception.payload()))

    def test_a_script_that_writes_nothing_is_a_failure(self):
        self.write(self.group())
        with mock.patch.object(qa_auth, "_run_login", return_value={"ok": True}):
            with self.assertRaises(EnvError):
                self.auth()
        base = qa_auth.session_dir(self.pid)
        self.assertEqual([p.name for p in base.iterdir()], [])


class CleanTest(AuthCase):
    def test_clean_removes_only_what_this_command_wrote(self):
        self.write({**self.group(), "h": self.group()["g"]})
        with self.fake_login():
            self.auth("/g")
            self.auth("/h")
        base = qa_auth.session_dir(self.pid)
        mine = next(p for p in base.iterdir() if p.suffix == ".json")
        foreign = base / "notes.txt"
        foreign.write_text("keep")
        self.assertEqual(qa_auth.clean(self.pid), {"removed": 2})
        self.assertFalse(mine.exists())
        self.assertTrue(foreign.exists())
        self.assertEqual(qa_auth.clean(self.pid), {"removed": 0})

    def test_qa_sessions_is_machine_local(self):
        self.assertTrue(paths.is_machine_local_record("qa-sessions"))
        self.assertTrue(paths.path_is_machine_local("projects/x/qa-sessions/a.json"))


class CliTest(AuthCase):
    def test_cli_no_credentials_json(self):
        self.write({"g": {"username": "qa"}})
        code, out, _ = self.run_cli("qa", "auth", "/g", "--path", str(self.root), "--json")
        self.assertEqual(code, 3)
        body = json.loads(out)
        self.assertEqual(body["details"]["reason"], "no-credentials")

    def test_cli_clean_json(self):
        code, out, err = self.run_cli("qa", "auth", "clean", "--path", str(self.root), "--json")
        self.assertEqual(code, 0, err)
        self.assertEqual(json.loads(out), {"ok": True, "removed": 0})


def reasons(case):
    lines = [json.loads(x) for x in case.audit().splitlines()]
    return [(x["action"], x["outcome"], (x.get("detail") or {}).get("reason")) for x in lines]


class LoginUrlTest(AuthCase):
    def run_with(self, login_url, production=False, **group):
        recipe = dict(RECIPE, url=login_url)
        body = {"login": recipe, "username": "qa", "password": {"$ref": "op://V/I/f"}}
        body.update(group)
        if production:
            body["$production"] = True
        self.write({"g": body})
        with self.fake_login() as run, mock.patch.object(cl, "_vendor", return_value="pw"):
            try:
                return self.auth(), run
            except UsageError as exc:
                self.assertEqual(exc.details["reason"], "invalid-login-url")
                self.assertEqual(exc.exit_code, 2)
                run.assert_not_called()
                return None, run

    def test_https_is_accepted_and_plain_http_only_on_loopback(self):
        self.assertIsNotNone(self.run_with("https://s.test/login")[0])
        for url in ("http://localhost:3000/login", "http://127.0.0.1/x", "http://[::1]:8080/x", "http://app.localhost/x"):
            qa_auth.clean(self.pid)
            self.assertIsNotNone(self.run_with(url)[0], url)
        for url in ("http://s.test/login", "ftp://s.test/x", "file:///etc/passwd", "https://u:p@s.test/x", "https:///x"):
            self.assertIsNone(self.run_with(url)[0], url)

    def test_http_is_never_accepted_in_production(self):
        self.assertIsNone(self.run_with("http://localhost/login", production=True)[0])

    def test_login_host_must_match_the_groups_url(self):
        self.assertIsNotNone(self.run_with("https://s.test/login", **{"url": "https://s.test/app"})[0])
        qa_auth.clean(self.pid)
        self.assertIsNone(self.run_with("https://evil.test/login", **{"url": "https://s.test/app"})[0])
        self.assertIn(("qa-auth", "failed", "invalid-login-url"), reasons(self))


class EndpointTest(AuthCase):
    def check(self, login, group_url):
        node = {"url": group_url} if group_url is not None else {}
        qa_auth.check_login_url(login, node, {}, False)

    def test_ports_are_compared_with_scheme_defaults(self):
        self.check("https://s.test/login", "https://s.test:443/app")
        self.check("https://s.test:8443/login", "https://s.test:8443/app")
        for login, group in (
            ("https://s.test/login", "https://s.test:8443/app"),
            ("https://s.test:9000/login", "https://s.test/app"),
        ):
            with self.assertRaises(UsageError) as ctx:
                self.check(login, group)
            self.assertEqual(ctx.exception.details["reason"], "invalid-login-url")

    def test_a_group_url_without_a_host_is_a_clear_error(self):
        with self.assertRaises(UsageError) as ctx:
            self.check("https://s.test/login", "/app")
        self.assertIn("no host", str(ctx.exception))

    def test_the_script_gets_the_rules_and_maps_its_refusal(self):
        self.write({"g": dict(self.group()["g"], **{"url": "https://s.test:8443/app", "login": dict(RECIPE, url="https://s.test:8443/login")})})
        log = []
        with self.fake_login(log=log):
            self.auth()
        self.assertEqual(log[0][0]["url_rules"], {"production": False, "host": "s.test", "port": 8443})
        with self.assertRaises(UsageError) as ctx:
            qa_auth._raise_for({"ok": False, "reason": "invalid-login-url", "message": "m"})
        self.assertEqual((ctx.exception.exit_code, ctx.exception.details["reason"]), (2, "invalid-login-url"))


class StopTest(AuthCase):
    def test_an_interrupted_run_sends_sigterm_then_sigkill(self):
        calls = []

        class Proc:
            args, returncode = [], 0

            def communicate(self, data=None, timeout=None):
                calls.append(("communicate", timeout))
                if data is not None:
                    raise KeyboardInterrupt
                if timeout is None:
                    return b"", b""
                raise qa_auth.subprocess.TimeoutExpired("x", timeout)

            def terminate(self):
                calls.append("terminate")

            def kill(self):
                calls.append("kill")

        with mock.patch.object(qa_auth.shutil, "which", return_value="node"), \
                mock.patch.object(qa_auth.subprocess, "Popen", return_value=Proc()):
            with self.assertRaises(KeyboardInterrupt):
                qa_auth._run_login({}, False)
        names = [c if isinstance(c, str) else "communicate" for c in calls]
        self.assertEqual(names[:3], ["communicate", "terminate", "communicate"])
        self.assertIn("kill", names)
        self.assertLessEqual(calls[2][1], 5.0)


FAKE_PLAYWRIGHT = """
const fs = require("fs");
const log = (x) => fs.appendFileSync(process.env.FAKE_LOG, x + "\\n");
module.exports = { chromium: { launch: async () => ({
  newContext: async () => ({
    storageState: async () => ({ cookies: [{ name: "a", value: "b", expires: -1 }], origins: [] }),
    on() {},
    newPage: async () => { let current = "about:blank"; return {
      setDefaultTimeout() {},
      goto: async (u) => { if (process.env.FAKE_HANG) { log("hanging"); setInterval(() => {}, 1000); await new Promise(() => {}); } current = process.env.FAKE_FINAL_URL || u; },
      url: () => current,
      fill: async () => log("fill"), click: async () => log("click"), press: async () => {},
      waitForLoadState: async () => {}, waitForSelector: async () => {}, waitForURL: async () => {},
      on() {},
    }; },
  }),
  close: async () => log("closed"), on() {},
}) } };
"""


@unittest.skipUnless(shutil.which("node"), "node is not installed")
class ScriptTest(AuthCase):
    def read_log(self):
        if not os.path.exists(self.log):
            return ""
        with open(self.log) as handle:
            return handle.read()

    def setUp(self):
        super().setUp()
        self.tmp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp_dir, True)
        module = os.path.join(self.tmp_dir, "node_modules", "playwright")
        os.makedirs(module)
        with open(os.path.join(module, "index.js"), "w") as handle:
            handle.write(FAKE_PLAYWRIGHT)
        with open(os.path.join(self.tmp_dir, "package.json"), "w") as handle:
            handle.write("{}")
        self.log = os.path.join(self.tmp_dir, "log")
        self.out = os.path.join(self.tmp_dir, "state.json")

    def payload(self, rules=None):
        return {
            "mode": "recipe", "project_root": self.tmp_dir, "out_path": self.out, "timeout_ms": 5000,
            "recipe": dict(RECIPE), "username": "qa", "password": "pw",
            "url_rules": rules or {"production": False, "host": "s.test", "port": 443},
        }

    def spawn(self, **env):
        full = dict(os.environ, FAKE_LOG=self.log, **env)
        return qa_auth.subprocess.Popen(
            ["node", str(qa_auth.LOGIN_SCRIPT)], stdin=qa_auth.subprocess.PIPE,
            stdout=qa_auth.subprocess.PIPE, stderr=qa_auth.subprocess.DEVNULL, env=full,
        )

    def run_script(self, payload, **env):
        proc = self.spawn(**env)
        out, _ = proc.communicate(json.dumps(payload).encode(), timeout=30)
        return proc.returncode, json.loads(out.decode().strip().splitlines()[-1])

    def fills(self):
        return self.read_log().count("fill")

    def test_a_redirect_to_another_host_stops_before_any_fill(self):
        code, answer = self.run_script(self.payload(), FAKE_FINAL_URL="https://evil.test/login")
        self.assertEqual((code, answer["reason"]), (2, "invalid-login-url"))
        self.assertEqual(self.fills(), 0)
        for url in ("http://s.test/login", "https://s.test:8443/login", "https://u:p@s.test/login"):
            code, answer = self.run_script(self.payload(), FAKE_FINAL_URL=url)
            self.assertEqual(answer.get("reason"), "invalid-login-url", url)
        self.assertEqual(self.fills(), 0)

    def test_the_expected_page_signs_in(self):
        code, answer = self.run_script(self.payload(), FAKE_FINAL_URL="https://s.test/login")
        self.assertEqual((code, answer), (0, {"ok": True}))
        self.assertEqual(self.fills(), 2)
        self.assertTrue(os.path.exists(self.out))

    def test_signals_close_the_browser_and_exit_128_plus_the_number(self):
        import signal
        for sig, expected in ((signal.SIGTERM, 143), (signal.SIGINT, 130)):
            if os.path.exists(self.log):
                os.unlink(self.log)
            proc = self.spawn(FAKE_HANG="1")
            proc.stdin.write(json.dumps(self.payload()).encode())
            proc.stdin.close()
            deadline = time.time() + 15
            while time.time() < deadline and "hanging" not in self.read_log():
                time.sleep(0.1)
            proc.send_signal(sig)
            self.assertEqual(proc.wait(timeout=10), expected)
            self.assertIn("closed", self.read_log())
            proc.stdout.close()


class CacheKeyTest(AuthCase):
    def sign_in(self, doc, **kw):
        self.write({"g": doc})
        with self.fake_login() as run:
            return self.auth(**kw), run.call_count

    def base(self, **extra):
        return dict({"login": dict(RECIPE), "username": "qa", "password": PW}, **extra)

    def test_changed_credentials_or_recipe_never_reuse_a_session(self):
        first, _ = self.sign_in(self.base())
        again, calls = self.sign_in(self.base())
        self.assertEqual((again["source"], calls), ("cache", 0))
        for changed in (
            self.base(password="another-pw"),
            self.base(username="other"),
            dict(self.base(), login=dict(RECIPE, submit_selector="#other")),
            self.base(totp_secret="JBSWY3DPEHPK3PXP"),
        ):
            result, calls = self.sign_in(changed)
            self.assertEqual((result["source"], calls), ("recipe", 1), changed)
            self.assertNotEqual(result["path"], first["path"])
        self.assertNotIn("another-pw", json.dumps(os.listdir(str(qa_auth.session_dir(self.pid)))))

    def test_the_production_flag_is_part_of_the_key(self):
        node = self.base()
        self.assertNotEqual(qa_auth.session_key("/g", node, False), qa_auth.session_key("/g", node, True))

    def test_interactive_bypasses_the_cache(self):
        self.sign_in(self.base())
        result, calls = self.sign_in(self.base(), interactive=True)
        self.assertEqual(calls, 1)
        self.assertNotEqual(result["source"], "cache")


class FallbackAndAuditTest(AuthCase):
    def recipe_group(self, **extra):
        self.write({"g": dict(self.group()["g"], **extra)})

    def test_any_recipe_failure_falls_back_to_interactive(self):
        failures = {
            "timeout": EnvError("did not finish", details={"reason": "login-failed"}),
            "store": EnvError("no session", details={"reason": "login-failed"}),
        }
        for name, exc in failures.items():
            qa_auth.clean(self.pid)
            self.recipe_group()
            calls = []

            def run(payload, interactive, exc=exc):
                calls.append(interactive)
                if not interactive:
                    raise exc
                with open(payload["out_path"], "w") as handle:
                    json.dump({"cookies": [{"name": "a", "value": "b", "expires": -1}]}, handle)
                return {"ok": True}
            with mock.patch.object(qa_auth, "_run_login", side_effect=run):
                self.assertEqual(self.auth(interactive=True)["source"], "interactive", name)
            self.assertEqual(calls, [False, True])

    def test_a_missing_store_write_also_falls_back(self):
        self.recipe_group()
        calls = []

        def run(payload, interactive):
            calls.append(interactive)
            if interactive:
                with open(payload["out_path"], "w") as handle:
                    json.dump({"cookies": [{"name": "a", "value": "b", "expires": -1}]}, handle)
            return {"ok": True}
        with mock.patch.object(qa_auth, "_run_login", side_effect=run):
            self.assertEqual(self.auth(interactive=True)["source"], "interactive")
        self.assertEqual(calls, [False, True])

    def test_production_plaintext_refusal_falls_back_when_interactive_only(self):
        self.write({"g": dict(self.group()["g"], **{"$production": True})})
        with self.fake_login(), self.assertRaises(UsageError):
            self.auth()
        with self.fake_login():
            self.assertEqual(self.auth(interactive=True)["source"], "interactive")

    def test_failures_are_audited_with_their_reason(self):
        self.recipe_group()
        with mock.patch.object(qa_auth, "_run_login", side_effect=EnvError("t", details={"reason": "login-failed"})):
            with self.assertRaises(EnvError):
                self.auth()
        self.write({"p": dict(self.group()["g"], **{"$production": True})})
        with self.assertRaises(UsageError):
            self.auth("/p")
        with mock.patch.object(qa_auth, "_run_login", return_value={"ok": True}):
            self.recipe_group(username="store-fail")
            with self.assertRaises(EnvError):
                self.auth()
        got = reasons(self)
        self.assertEqual(got.count(("qa-auth", "failed", "login-failed")), 2)
        self.assertIn(("qa-auth", "failed", "plaintext-in-production"), got)


@unittest.skipUnless(shutil.which("node"), "node is not installed")
class TimeoutTest(AuthCase):
    def test_a_timed_out_script_gets_sigterm_to_close_its_browser(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        marker = os.path.join(tmp, "closed")
        script = os.path.join(tmp, "slow.mjs")
        with open(script, "w") as handle:
            handle.write(
                'import fs from "node:fs";\n'
                'process.on("SIGTERM", () => { fs.writeFileSync(%r, "closed"); process.exit(143); });\n'
                "setInterval(() => {}, 1000);\n" % marker
            )
        with mock.patch.object(qa_auth, "LOGIN_SCRIPT", script), mock.patch.object(qa_auth, "_RECIPE_TIMEOUT", -14.0):
            with self.assertRaises(EnvError) as ctx:
                qa_auth._run_login({}, False)
        self.assertEqual(ctx.exception.details["reason"], "login-failed")
        self.assertTrue(os.path.exists(marker))


if __name__ == "__main__":
    unittest.main()
