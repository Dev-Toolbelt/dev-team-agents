"""`post_json` keeps the integrations HTTP policy (ADR-0029 SR-44)."""

from __future__ import annotations

import json
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts" / "lib"))

from devteam.errors import UsageError  # noqa: E402
from devteam.integrations import http as policy  # noqa: E402


class Handler(BaseHTTPRequestHandler):
    seen = []

    def log_message(self, *args):
        pass

    def _send(self, code, body, extra=None):
        raw = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        for key, value in (extra or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(raw)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        body = json.loads(self.rfile.read(length) or b"{}")
        Handler.seen.append((self.path, dict(self.headers), body))
        if self.path == "/ok":
            self._send(200, {"echo": body})
        elif self.path == "/bad":
            self._send(400, {"error_code": "otp_expired"})
        elif self.path == "/limited":
            self._send(429, {"error_code": "over_request_rate_limit"}, {"Retry-After": "5"})
        elif self.path == "/moved":
            self._send(307, {}, {"Location": "http://127.0.0.1:1/elsewhere"})


class PostJsonTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = HTTPServer(("127.0.0.1", 0), Handler)
        cls.url = "http://127.0.0.1:{}".format(cls.server.server_address[1])
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self):
        Handler.seen.clear()

    def test_plain_http_is_refused_unless_loopback_is_allowed(self):
        with self.assertRaises(UsageError):
            policy.post_json(self.url, "/ok", {}, {"a": 1})

    def test_non_loopback_http_is_refused_even_with_the_flag(self):
        with self.assertRaises(UsageError):
            policy.post_json("http://example.com", "/ok", {}, {}, allow_loopback_http=True)
        with self.assertRaises(UsageError):
            policy.post_json("http://127.0.0.1.evil.com", "/ok", {}, {}, allow_loopback_http=True)

    def test_posts_json_to_loopback_when_allowed(self):
        data, _headers = policy.post_json(
            self.url, "/ok", {"apikey": "anon"}, {"email": "a@b.c"}, allow_loopback_http=True
        )
        self.assertEqual(data, {"echo": {"email": "a@b.c"}})
        _path, headers, _body = Handler.seen[0]
        self.assertEqual(headers["Content-Type"], "application/json")
        self.assertEqual(headers["Apikey"], "anon")

    def test_error_carries_status_and_parsed_body_not_the_request(self):
        with self.assertRaises(policy.FetchError) as ctx:
            policy.post_json(self.url, "/bad", {"Authorization": "Bearer secret-token"}, {"code": "1"},
                             allow_loopback_http=True)
        err = ctx.exception
        self.assertEqual((err.http_status, err.body), (400, {"error_code": "otp_expired"}))
        self.assertNotIn("secret-token", err.summary)

    def test_rate_limit_is_classified(self):
        with self.assertRaises(policy.FetchError) as ctx:
            policy.post_json(self.url, "/limited", {}, {}, allow_loopback_http=True)
        self.assertEqual((ctx.exception.state, ctx.exception.http_status), ("rate_limited", 429))

    def test_redirects_are_not_followed(self):
        with self.assertRaises(policy.FetchError):
            policy.post_json(self.url, "/moved", {}, {}, allow_loopback_http=True)
        self.assertEqual(len(Handler.seen), 1)

    def test_get_json_policy_is_unchanged(self):
        with self.assertRaises(UsageError):
            policy.get_json(self.url, "/ok", {})


if __name__ == "__main__":
    unittest.main()
