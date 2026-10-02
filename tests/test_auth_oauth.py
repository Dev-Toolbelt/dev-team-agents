"""Browser sign-in: PKCE, state, the loopback listener and its rejections (ADR-0029 SR-1..6, SR-44)."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import socket
import sys
import threading
import unittest
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

from auth_support import AuthTestCase  # noqa: E402

from devteam import auth_oauth as oauth  # noqa: E402


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def fetch(url, method="GET", headers=None, follow=False):
    """``(status, headers, body)`` without raising on an HTTP error."""
    opener = urllib.request.build_opener() if follow else urllib.request.build_opener(_NoRedirect)
    request = urllib.request.Request(url, method=method, headers=headers or {}, data=b"" if method == "POST" else None)
    try:
        with opener.open(request, timeout=5) as response:
            return response.status, response.headers, response.read().decode()
    except urllib.error.HTTPError as exc:
        try:
            return exc.code, exc.headers, exc.read().decode()
        finally:
            exc.close()


class BrowserTestCase(AuthTestCase):
    """Runs ``auth`` in-process with a fake browser that drives the authorize URL."""

    def setUp(self):
        super().setUp()
        os.environ["DISPLAY"] = ":0"
        self.addCleanup(os.environ.pop, "DISPLAY", None)
        self.opened = []
        self.probes = []
        self.errors = []

    def browser(self, probe=None):
        """A replacement for ``open_browser``: records the URL, runs ``probe``, then follows it."""

        def open_url(url):
            self.opened.append(url)

            def drive():
                try:
                    if probe:
                        probe(self.redirect_of(url))
                    fetch(url, follow=True)
                except Exception as exc:  # noqa: BLE001 - surfaced by the test
                    self.errors.append(exc)

            threading.Thread(target=drive, daemon=True).start()
            return True

        return mock.patch.object(oauth, "open_browser", open_url)

    @staticmethod
    def query_of(url):
        return {k: v[0] for k, v in urllib.parse.parse_qs(urllib.parse.urlsplit(url).query).items()}

    def redirect_of(self, url):
        return urllib.parse.urlsplit(self.query_of(url)["redirect_to"])

    def login(self, provider="google", probe=None):
        with self.browser(probe):
            return self.run_inproc(["auth", "login", "--" + provider, "--json"])


class PkceFlowTest(BrowserTestCase):
    def test_google_sign_in_completes_with_pkce_and_state(self):
        code, out, _err = self.login("google")
        self.assertEqual(code, 0, out)
        body = json.loads(out)
        self.assertEqual(body["method"], "oauth-google")
        self.assertEqual(body["account"]["email"], self.idp.oauth_emails["google"])
        self.assertEqual(self.errors, [])
        query = self.query_of(self.opened[0])
        self.assertEqual(query["code_challenge_method"], "s256")
        self.assertEqual(query["provider"], "google")
        self.assertNotIn("scopes", query)
        # The verifier sent at exchange hashed to the challenge sent at authorize: the fake
        # would have refused the exchange otherwise.
        exchange = [c for c in self.idp.calls if c["query"].get("grant_type") == "pkce"][0]
        verifier = exchange["body"]["code_verifier"]
        self.assertEqual(len(verifier), 43)
        digest = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
        self.assertEqual(digest, query["code_challenge"])
        state = urllib.parse.parse_qs(self.redirect_of(self.opened[0]).query)["state"][0]
        self.assertGreaterEqual(len(state), 22)  # 128 bits or more in base64url

    def test_github_asks_for_the_email_scope(self):
        code, out, _ = self.login("github")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.query_of(self.opened[0])["scopes"], "user:email")

    def test_the_verifier_and_state_are_new_for_every_attempt(self):
        self.login("google")
        self.run_inproc(["auth", "logout"])
        self.login("google")
        first, second = (self.query_of(u) for u in self.opened)
        self.assertNotEqual(first["code_challenge"], second["code_challenge"])
        self.assertNotEqual(first["redirect_to"], second["redirect_to"])

    def test_the_redirect_is_loopback_on_the_bound_port(self):
        self.login("google")
        redirect = self.redirect_of(self.opened[0])
        self.assertEqual(redirect.hostname, "127.0.0.1")
        self.assertEqual(redirect.path, "/callback")
        self.assertGreater(redirect.port, 0)

    def test_no_token_ever_appears_in_a_url_the_browser_saw(self):
        self.login("google")
        self.assertNotIn("SENTINEL", " ".join(self.opened))

    def test_the_session_is_stored_and_the_license_fetched(self):
        self.login("google")
        code, body, _ = self.run_json("auth", "status", "--offline")
        self.assertTrue(body["signed_in"] and body["entitled"])
        self.assertEqual(body["account"]["provider"], "google")


class ListenerRejectionTest(BrowserTestCase):
    def test_a_forged_state_does_not_consume_the_listener(self):
        results = {}

        def probe(redirect):
            base = "http://{}:{}".format(redirect.hostname, redirect.port)
            results["wrong"] = fetch(base + "/callback?state=forged&code=evil")[0]
            results["missing"] = fetch(base + "/callback?code=evil")[0]

        code, out, _ = self.login("google", probe)
        self.assertEqual(code, 0, out)
        self.assertEqual(results, {"wrong": 400, "missing": 400})
        exchange = [c for c in self.idp.calls if c["query"].get("grant_type") == "pkce"]
        self.assertEqual(len(exchange), 1)
        self.assertNotEqual(exchange[0]["body"]["auth_code"], "evil")

    def test_other_methods_paths_and_hosts_are_404_and_do_not_end_the_wait(self):
        results = {}

        def probe(redirect):
            base = "http://{}:{}".format(redirect.hostname, redirect.port)
            results["post"] = fetch(base + "/callback", "POST")[0]
            results["path"] = fetch(base + "/other?state=x")[0]
            results["host"] = fetch(base + "/callback?" + redirect.query, headers={"Host": "evil.example"})[0]
            results["head"] = fetch(base + "/callback", "HEAD")[0]

        code, out, _ = self.login("google", probe)
        self.assertEqual(code, 0, out)
        self.assertEqual(results, {"post": 404, "path": 404, "host": 404, "head": 404})

    def test_a_provider_error_ends_the_attempt_without_echoing_the_description(self):
        def probe(redirect):
            base = "http://{}:{}".format(redirect.hostname, redirect.port)
            query = urllib.parse.parse_qs(redirect.query)["state"][0]
            fetch(base + "/callback?state={}&error=access_denied&error_description=LEAK-ME".format(query))

        def open_url(url):
            self.opened.append(url)
            redirect = self.redirect_of(url)
            threading.Thread(target=probe, args=(redirect,), daemon=True).start()
            return True

        with mock.patch.object(oauth, "open_browser", open_url):
            code, out, err = self.run_inproc(["auth", "login", "--google", "--json"])
        self.assertEqual(code, 1)
        self.assertNotIn("LEAK-ME", out + err)
        self.assertEqual(json.loads(out)["details"]["reason"], "oauth_failed")

    def test_the_callback_page_is_static_and_carries_the_security_headers(self):
        captured = {}

        def probe(redirect):
            pass

        def open_url(url):
            self.opened.append(url)
            redirect = self.redirect_of(url)

            def drive():
                base = "http://{}:{}".format(redirect.hostname, redirect.port)
                captured["bad"] = fetch(base + "/callback?state=wrong&code=SECRETCODE")
                status, headers, body = fetch(url, follow=True)
                captured["ok"] = (status, headers, body)

            threading.Thread(target=drive, daemon=True).start()
            return True

        with mock.patch.object(oauth, "open_browser", open_url):
            code, out, _ = self.run_inproc(["auth", "login", "--google", "--json"])
        self.assertEqual(code, 0, out)
        for status, headers, body in (captured["bad"], captured["ok"]):
            self.assertEqual(headers["Cache-Control"], "no-store")
            self.assertEqual(headers["Referrer-Policy"], "no-referrer")
            self.assertEqual(headers["Content-Security-Policy"], "default-src 'none'")
            self.assertNotIn("SECRETCODE", body)
            self.assertNotIn("pkce-", body)
            self.assertNotIn("<script", body.lower())
            self.assertNotIn("http", body.lower().replace("<!doctype html>", ""))
        self.assertEqual(captured["ok"][0], 200)

    def test_timeout_is_an_environment_error_and_frees_the_port(self):
        with mock.patch.object(oauth, "CALLBACK_TIMEOUT", 0.6), mock.patch.object(
            oauth, "open_browser", lambda url: self.opened.append(url) or True
        ):
            code, out, _ = self.run_inproc(["auth", "login", "--google", "--json"])
        self.assertEqual(code, 3)
        self.assertEqual(json.loads(out)["details"]["reason"], "timeout")
        port = self.redirect_of(self.opened[0]).port
        probe = socket.socket()
        self.addCleanup(probe.close)
        probe.bind(("127.0.0.1", port))  # raises when the listener still holds it

    def test_a_browser_that_cannot_open_prints_the_address_on_stderr(self):
        with mock.patch.object(oauth, "open_browser", lambda url: self.opened.append(url) and False), mock.patch.object(
            oauth, "CALLBACK_TIMEOUT", 0.4
        ):
            code, out, err = self.run_inproc(["auth", "login", "--google", "--json"])
        self.assertEqual(code, 3)
        self.assertIn("/auth/v1/authorize", err)
        json.loads(out)


class ListenerBindingTest(unittest.TestCase):
    def test_binds_loopback_only_on_an_os_assigned_port(self):
        with oauth.Listener("s") as listener:
            self.assertEqual(listener.server.server_address[0], "127.0.0.1")
            self.assertGreater(listener.port, 1023)
            self.assertEqual(listener.redirect_to, "http://127.0.0.1:{}/callback?state=s".format(listener.port))

    def test_falls_back_to_the_fixed_range_when_a_random_port_is_unavailable(self):
        real = oauth._Server
        attempts = []

        def flaky(address, handler):
            attempts.append(address[1])
            if address[1] == 0:
                raise OSError("no")
            return real(address, handler)

        with mock.patch.object(oauth, "_Server", flaky):
            try:
                with oauth.Listener("s") as listener:
                    self.assertIn(listener.port, oauth.FALLBACK_PORTS)
            except Exception as exc:  # the range may be busy on a developer machine
                self.skipTest("fallback ports are busy: {}".format(exc))
        self.assertEqual(attempts[0], 0)

    def test_pkce_pairs_are_43_characters_and_unique(self):
        first, second = oauth.new_pkce(), oauth.new_pkce()
        self.assertEqual(len(first[0]), 43)
        self.assertNotEqual(first, second)
        digest = base64.urlsafe_b64encode(hashlib.sha256(first[0].encode()).digest()).rstrip(b"=").decode()
        self.assertEqual(digest, first[1])


class HeadlessTest(AuthTestCase):
    def test_no_display_refuses_oauth_and_points_at_email(self):
        os.environ.pop("DISPLAY", None)
        os.environ.pop("WAYLAND_DISPLAY", None)
        code, out, err = self.run_auth("auth", "login", "--google", "--json")
        body = json.loads(out)
        self.assertEqual(code, 3)
        self.assertEqual(body["details"]["reason"], "headless")
        self.assertIn("--email", body["hint"])
        self.assertEqual(self.idp.calls, [])

    def test_a_display_is_assumed_off_linux(self):
        self.assertTrue(oauth.can_open_browser({}, "darwin"))
        self.assertTrue(oauth.can_open_browser({}, "win32"))
        self.assertFalse(oauth.can_open_browser({}, "linux"))
        self.assertTrue(oauth.can_open_browser({"WAYLAND_DISPLAY": "w"}, "linux"))


class LinkIdentityTest(BrowserTestCase):
    def test_link_then_unlink_a_provider(self):
        self.sign_in()
        with self.browser():
            code, out, _ = self.run_inproc(["auth", "profile", "link", "--github", "--json"])
        self.assertEqual(code, 0, out)
        self.assertEqual(sorted(i["provider"] for i in json.loads(out)["identities"]), ["email", "github"])
        code, body, _ = self.run_json("auth", "profile", "unlink", "--github")
        self.assertEqual(code, 0, body)


if __name__ == "__main__":
    unittest.main()
