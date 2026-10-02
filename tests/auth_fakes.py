"""A fake GoTrue and a fake pair of Edge Functions on loopback, for the `devteam auth` tests.

Nothing here is shipped (`tests/` is stripped). The fake issues recognisable sentinel secrets
(``SENTINEL-ACCESS-n``, ``SENTINEL-REFRESH-n``) so a test can grep every output and every file
the CLI wrote for a token, and it signs entitlements with a throwaway Ed25519 test key through
``ed25519_signer``. It models just enough of GoTrue to exercise the CLI: OTP and recovery codes,
sign-up, password and PKCE and refresh grants with rotation and reuse detection, the signed-in
user, logout scopes, identities, the profile table and the two functions.
"""

from __future__ import annotations

import base64
import hashlib
import json
import sys
import threading
import time
import urllib.parse
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import ed25519_signer  # noqa: E402

SEED = bytes(range(40, 72))
KID = "test-auth-1"
PASSWORD = "pw-SENTINEL-correct-horse"
NEW_PASSWORD = "pw-SENTINEL-battery-staple"
DAY = 86400


def b64(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


class FakeIdP:
    def __init__(self):
        self.lock = threading.RLock()
        self.users = {}
        self.codes = {}
        self.sessions = {}
        self.refresh = {}
        self.access = {}
        self.pkce = {}
        self.calls = []
        self.counter = 0
        self.refresh_exchanges = 0
        self.reuse_events = 0
        self.logouts = []
        self.deleted = []
        self.entitlement_calls = 0
        self.down = False
        self.limited = set()
        self.statuses = {}
        self.default_status = "active"
        self.oauth_emails = {"google": "oauth.person@example.com", "github": "oauth.person@example.com"}
        self.refresh_delay = 0.0
        self.fixed_code = None
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), self._handler())
        self.server.daemon_threads = True
        self.url = "http://127.0.0.1:{}".format(self.server.server_address[1])
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    # -- lifecycle -------------------------------------------------------------

    def start(self):
        self.thread.start()
        return self

    def stop(self):
        self.server.shutdown()
        self.server.server_close()

    def env(self):
        return {
            "DEVTEAM_AUTH_TEST_URL": self.url,
            "DEVTEAM_AUTH_TEST_KID": KID,
            "DEVTEAM_AUTH_TEST_PUBKEY": b64(ed25519_signer.public_key(SEED)),
        }

    # -- model -----------------------------------------------------------------

    def next(self):
        with self.lock:
            self.counter += 1
            return self.counter

    def add_user(self, email, password=PASSWORD, confirmed=True, banned=False, name=None, provider="email"):
        user = {
            "id": str(uuid.uuid4()),
            "email": email,
            "password": password,
            "confirmed": confirmed,
            "banned": banned,
            "display_name": name,
            "provider": provider,
            "identities": [{"identity_id": str(uuid.uuid4()), "provider": provider, "email": email}],
            "pending_email": None,
            "change_codes": {},
            "change_ok": set(),
        }
        with self.lock:
            self.users[email] = user
        return user

    def user_by_id(self, uid):
        return next((u for u in self.users.values() if u["id"] == uid), None)

    def code_for(self, email, kind):
        return self.codes.get((email, kind))

    def issue_code(self, email, kind):
        code = self.fixed_code or "{:08d}".format((self.next() * 7919 + 12345678) % 100000000)
        self.codes[(email, kind)] = code
        return code

    def new_session(self, user, fresh):
        with self.lock:
            sid = "s{}".format(self.next())
            n = self.next()
            refresh = "SENTINEL-REFRESH-{}".format(n)
            access = "SENTINEL-ACCESS-{}".format(n)
            self.sessions[sid] = {"user": user["id"], "alive": True}
            self.refresh[refresh] = {"sid": sid, "used": False}
            self.access[access] = {"sid": sid, "fresh": fresh}
            return {
                "access_token": access,
                "refresh_token": refresh,
                "expires_in": 3600,
                "token_type": "bearer",
                "user": self.user_json(user),
            }

    def user_json(self, user):
        return {
            "id": user["id"],
            "email": user["email"],
            "new_email": user["pending_email"],
            "created_at": "2026-10-01T00:00:00Z",
            "user_metadata": {"display_name": user["display_name"]} if user["display_name"] else {},
            "app_metadata": {"provider": user["provider"]},
            "identities": [
                {"identity_id": i["identity_id"], "provider": i["provider"], "identity_data": {"email": i["email"]}}
                for i in user["identities"]
            ],
        }

    def entitlement_token(self, user, **overrides):
        now = int(time.time())
        status = self.statuses.get(user["email"], self.default_status)
        payload = {
            "sub": user["id"],
            "status": status,
            "features": [],
            "iss": self.url,
            "aud": "devteam-cli",
            "v": 1,
            "iat": now,
            "exp": now + 7 * DAY,
        }
        if status == "trial":
            payload["trial_ends_at"] = now + 3 * DAY
        payload.update(overrides)
        head = b64(json.dumps({"kid": KID}, separators=(",", ":")).encode())
        body = b64(json.dumps(payload, separators=(",", ":")).encode())
        signed = "v1.{}.{}".format(head, body).encode("ascii")
        return "{}.{}".format(signed.decode("ascii"), b64(ed25519_signer.sign(SEED, signed)))

    def calls_to(self, path_prefix):
        return [call for call in self.calls if call["path"].startswith(path_prefix)]

    # -- http ------------------------------------------------------------------

    def _handler(self):
        idp = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.0"

            def log_message(self, *args):
                pass

            def _send(self, code, body, headers=None):
                raw = json.dumps(body).encode()
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                for key, value in (headers or {}).items():
                    self.send_header(key, value)
                self.end_headers()
                self.wfile.write(raw)

            def _handle(self, method):
                parsed = urllib.parse.urlsplit(self.path)
                query = {k: v[0] for k, v in urllib.parse.parse_qs(parsed.query, keep_blank_values=True).items()}
                length = int(self.headers.get("Content-Length", "0") or 0)
                raw = self.rfile.read(length) if length else b""
                try:
                    body = json.loads(raw) if raw else {}
                except ValueError:
                    body = {}
                bearer = (self.headers.get("Authorization") or "")[7:] or None
                with idp.lock:
                    idp.calls.append(
                        {
                            "method": method,
                            "path": parsed.path,
                            "query": query,
                            "body": body,
                            "bearer": bearer,
                            "header_names": sorted(k.lower() for k in self.headers.keys()),
                            "user_agent": self.headers.get("User-Agent"),
                        }
                    )
                if idp.down:
                    return self._send(503, {"error": "down"})
                if parsed.path in idp.limited:
                    return self._send(429, {"error_code": "over_request_rate_limit"}, {"Retry-After": "7"})
                try:
                    result = idp.route(method, parsed.path, query, body, bearer, self.headers)
                except Exception as exc:  # noqa: BLE001 - a fake: report, do not crash the thread
                    result = (500, {"error": "fake failure {}".format(type(exc).__name__)}, {})
                code, payload, headers = (result + ({},))[:3] if len(result) == 2 else result
                self._send(code, payload, headers)

            def do_GET(self):
                self._handle("GET")

            def do_POST(self):
                self._handle("POST")

            def do_PUT(self):
                self._handle("PUT")

            def do_PATCH(self):
                self._handle("PATCH")

            def do_DELETE(self):
                self._handle("DELETE")

        return Handler

    def _auth(self, bearer):
        info = self.access.get(bearer or "")
        if not info or not self.sessions[info["sid"]]["alive"]:
            return None, None
        return self.user_by_id(self.sessions[info["sid"]]["user"]), info

    def route(self, method, path, query, body, bearer, headers=None):
        with self.lock:
            return self._route(method, path, query, body, bearer)

    def _route(self, method, path, query, body, bearer):
        bad = lambda code="invalid_credentials": (400, {"error_code": code, "msg": "x"})  # noqa: E731
        if path == "/auth/v1/otp" and method == "POST":
            email = body.get("email")
            user = self.users.get(email)
            if user is None and body.get("create_user"):
                user = self.add_user(email, password=None, confirmed=False, name=(body.get("data") or {}).get("display_name"))
            if user is None:
                return (422, {"error_code": "otp_disabled"})
            if user["banned"]:
                return (400, {"error_code": "user_banned"})
            self.issue_code(email, "email")
            return (200, {})
        if path == "/auth/v1/signup" and method == "POST":
            email = body.get("email")
            existing = self.users.get(email)
            if existing and existing["confirmed"]:
                return (200, {"id": str(uuid.uuid4()), "email": email})
            user = existing or self.add_user(email, confirmed=False, name=(body.get("data") or {}).get("display_name"))
            user["password"] = body.get("password")
            self.issue_code(email, "signup")
            return (200, {"id": user["id"], "email": email})
        if path == "/auth/v1/verify" and method == "POST":
            return self._verify(body)
        if path == "/auth/v1/recover" and method == "POST":
            if body.get("email") in self.users:
                self.issue_code(body["email"], "recovery")
            return (200, {})
        if path == "/auth/v1/token" and method == "POST":
            return self._token(query, body)
        if path == "/auth/v1/logout" and method == "POST":
            user, info = self._auth(bearer)
            if not user:
                return (401, {"error_code": "bad_jwt"})
            self.logouts.append(query.get("scope"))
            for sid, record in self.sessions.items():
                if record["user"] != user["id"]:
                    continue
                if query.get("scope") == "others" and sid != info["sid"]:
                    record["alive"] = False
                if query.get("scope") == "local" and sid == info["sid"]:
                    record["alive"] = False
            return (200, {})
        if path == "/auth/v1/user":
            return self._user(method, body, bearer)
        if path == "/auth/v1/authorize" and method == "GET":
            return self._authorize(query)
        if path == "/auth/v1/user/identities/authorize" and method == "GET":
            user, _info = self._auth(bearer)
            if not user:
                return (401, {"error_code": "bad_jwt"})
            link = dict(query, link=user["id"])
            link.pop("skip_http_redirect", None)
            return (200, {"url": self.url + "/auth/v1/authorize?" + urllib.parse.urlencode(link)})
        if path.startswith("/auth/v1/user/identities/") and method == "DELETE":
            user, _info = self._auth(bearer)
            if not user:
                return (401, {"error_code": "bad_jwt"})
            ident = path.rsplit("/", 1)[1]
            if len(user["identities"]) < 2:
                return (422, {"error_code": "single_identity_not_deletable"})
            user["identities"] = [i for i in user["identities"] if i["identity_id"] != ident]
            return (200, {})
        if path == "/rest/v1/profiles":
            return self._profile(method, query, body, bearer)
        if path == "/functions/v1/entitlement" and method == "POST":
            user, _info = self._auth(bearer)
            if not user:
                return (401, {"error": "unauthorized"})
            self.entitlement_calls += 1
            return (200, {"token": self.entitlement_token(user)})
        if path == "/functions/v1/account-delete" and method == "POST":
            user, info = self._auth(bearer)
            if not user:
                return (401, {"error": "unauthorized"})
            if not info["fresh"]:
                return (403, {"error": "reauth_required"})
            self.deleted.append(user["email"])
            del self.users[user["email"]]
            for record in self.sessions.values():
                if record["user"] == user["id"]:
                    record["alive"] = False
            return (200, {"ok": True})
        return (404, {"error": "no route"})

    def _verify(self, body):
        email, kind, token = body.get("email"), body.get("type"), body.get("token")
        if kind == "email_change":
            return self._verify_change(email, token)
        user = self.users.get(email)
        if not user or self.codes.get((email, kind)) != token or user["banned"]:
            return (403, {"error_code": "otp_expired"})
        del self.codes[(email, kind)]
        user["confirmed"] = True
        return (200, self.new_session(user, fresh=True))

    def _verify_change(self, email, token):
        for user in self.users.values():
            codes = user["change_codes"]
            for which, address in (("new", user["pending_email"]), ("current", user["email"])):
                if address == email and codes.get(which) == token and token:
                    user["change_ok"].add(which)
                    if user["change_ok"] == {"new", "current"}:
                        del self.users[user["email"]]
                        user["email"] = user["pending_email"]
                        user["pending_email"] = None
                        user["change_codes"], user["change_ok"] = {}, set()
                        self.users[user["email"]] = user
                        return (200, self.new_session(user, fresh=True))
                    return (200, {})
        return (403, {"error_code": "otp_expired"})

    def _token(self, query, body):
        grant = query.get("grant_type")
        if grant == "password":
            user = self.users.get(body.get("email"))
            if not user or not user["confirmed"] or user["banned"] or user["password"] != body.get("password"):
                return (400, {"error_code": "invalid_credentials"})
            return (200, self.new_session(user, fresh=True))
        if grant == "refresh_token":
            if self.refresh_delay:
                time.sleep(self.refresh_delay)
            record = self.refresh.get(body.get("refresh_token"))
            if record is None or not self.sessions[record["sid"]]["alive"]:
                return (400, {"error_code": "refresh_token_not_found"})
            if record["used"]:
                self.reuse_events += 1
                self.sessions[record["sid"]]["alive"] = False
                return (400, {"error_code": "refresh_token_already_used"})
            record["used"] = True
            self.refresh_exchanges += 1
            user = self.user_by_id(self.sessions[record["sid"]]["user"])
            self.sessions[record["sid"]]["alive"] = False
            return (200, self.new_session(user, fresh=False))
        if grant == "pkce":
            entry = self.pkce.pop(body.get("auth_code"), None)
            if entry is None:
                return (400, {"error_code": "flow_state_not_found"})
            digest = b64(hashlib.sha256((body.get("code_verifier") or "").encode()).digest())
            if digest != entry["challenge"]:
                return (400, {"error_code": "bad_code_verifier"})
            return (200, self.new_session(entry["user"], fresh=True))
        return (400, {"error_code": "unsupported_grant_type"})

    def _user(self, method, body, bearer):
        user, info = self._auth(bearer)
        if not user:
            return (401, {"error_code": "bad_jwt"})
        if method == "GET":
            return (200, self.user_json(user))
        if method == "PUT":
            if "password" in body:
                if not info["fresh"]:
                    return (400, {"error_code": "reauthentication_needed"})
                user["password"] = body["password"]
            if "email" in body:
                user["pending_email"] = body["email"]
                user["change_codes"] = {"new": self.issue_code(body["email"], "email_change"), "current": self.issue_code(user["email"], "email_change")}
                user["change_ok"] = set()
            return (200, self.user_json(user))
        return (405, {})

    def _authorize(self, query):
        if query.get("code_challenge_method") != "s256" or not query.get("code_challenge"):
            return (400, {"error_code": "validation_failed"})
        provider = query.get("provider")
        redirect = query.get("redirect_to", "")
        if provider not in self.oauth_emails:
            return (400, {"error_code": "validation_failed"})
        if query.get("link"):
            user = self.user_by_id(query["link"])
            if all(i["provider"] != provider for i in user["identities"]):
                user["identities"].append(
                    {"identity_id": str(uuid.uuid4()), "provider": provider, "email": self.oauth_emails[provider]}
                )
        else:
            email = self.oauth_emails[provider]
            user = self.users.get(email) or self.add_user(email, password=None, provider=provider)
        code = "pkce-{}".format(self.next())
        self.pkce[code] = {"challenge": query["code_challenge"], "user": user}
        sep = "&" if "?" in redirect else "?"
        self.authorize_requests = getattr(self, "authorize_requests", []) + [dict(query)]
        return (302, {}, {"Location": "{}{}code={}".format(redirect, sep, code)})

    def _profile(self, method, query, body, bearer):
        user, _info = self._auth(bearer)
        if not user:
            return (401, {"error_code": "bad_jwt"})
        if method == "GET":
            return (200, [{"display_name": user["display_name"], "signup_method": user["provider"], "created_at": "2026-10-01T00:00:00Z"}])
        if method == "PATCH":
            if set(body) != {"display_name"}:
                return (403, {"error_code": "42501"})
            user["display_name"] = body["display_name"]
            return (200, [{"display_name": body["display_name"]}])
        return (405, {})
