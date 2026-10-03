"""Cloudflare over the v4 REST API, with a scoped API token."""

from __future__ import annotations

import re
import urllib.parse

from ..errors import UsageError
from . import http
from .base import check_token, fact, field

DEFAULT_API_URL = "https://api.cloudflare.com/client/v4"
# Account and zone identifiers are 32 lower-case hex characters.
_ID_RE = re.compile(r"^[0-9a-f]{32}$")
_PAGE_SIZE = "50"
#: The hosts a Cloudflare token may be sent to: the API and its FedRAMP twin. Anything
#: else is a hostile or mistyped `api_url`, and the token must never reach it.
API_HOSTS = ("api.cloudflare.com", "api.fed.cloudflare.com")
API_PATH = "/client/v4"


def _api_url(value):
    url = http.validate_base_url(value, "api_url")
    parsed = urllib.parse.urlsplit(url)
    host = (parsed.hostname or "").lower()
    if parsed.scheme == "http" and host in http.LOOPBACK_HOSTS:
        return url  # the integrations test seam; validate_base_url already gated it
    if host not in API_HOSTS or parsed.path != API_PATH or parsed.port not in (None, 443):
        raise UsageError(
            "api_url must be https://api.cloudflare.com/client/v4",
            hint="Or https://api.fed.cloudflare.com/client/v4 for FedRAMP accounts.",
        )
    return url


def _forbid(pattern, reason):
    return re.compile(pattern, re.IGNORECASE), reason


#: Endpoints whose *response* is a credential: calling them would put a secret in the
#: agent's transcript. Refused by `integration call` even with --allow-write (ADR-0031).
FORBIDDEN_ENDPOINTS = (
    _forbid(r"^/user/tokens(?!/verify$)(/|$)", "it creates, reads or rolls API tokens"),
    _forbid(r"^/accounts/[^/]+/tokens(?!/verify$)(/|$)", "it creates, reads or rolls API tokens"),
    _forbid(r"^/user/api_key$", "it reads the Global API Key"),
    _forbid(r"/cfd_tunnel/[^/]+/token$", "it returns the tunnel's secret"),
    _forbid(r"/warp_connector/[^/]+/token$", "it returns the connector's secret"),
    _forbid(r"/access/service_tokens(/|$)", "it creates or rotates Access service tokens"),
    _forbid(r"/r2/temp-access-credentials$", "it mints R2 access credentials"),
)


def _ok(data):
    """The ``result`` of a v4 envelope, or ``FetchError`` when it is not one."""
    if not isinstance(data, dict) or data.get("success") is not True or "result" not in data:
        raise http.FetchError("unreachable", "The server did not answer like the Cloudflare API")
    return data["result"]


def _truncated(data):
    info = data.get("result_info") if isinstance(data, dict) else None
    if not isinstance(info, dict):
        return False
    page, pages = info.get("page"), info.get("total_pages")
    return isinstance(page, int) and isinstance(pages, int) and page < pages


class Cloudflare:
    name = "cloudflare"
    origin_key = "api_url"
    title = "Cloudflare"
    description = "Call the Cloudflare API (DNS, cache, Workers, R2, KV, WAF) with a scoped API token."
    homepage = "https://www.cloudflare.com"
    #: Opts in to `devteam integration call`: agents run API requests through the CLI,
    #: which holds the token (ADR-0031).
    supports_call = True
    forbidden_endpoints = FORBIDDEN_ENDPOINTS
    auth = {
        "kind": "token",
        "label": "API token",
        "help": "A scoped API token (never the Global API Key), created under My Profile or "
        "the account's API Tokens page. It is stored in the OS secret store.",
    }
    fields = [
        field(
            "api_url", "account", "API URL", required=True, default=DEFAULT_API_URL,
            placeholder=DEFAULT_API_URL,
            help="The Cloudflare v4 API base URL. Leave the default.",
        ),
        field(
            "account_id", "account", "Account ID", placeholder="32 hex characters",
            resource="accounts",
            help="Needed for account-owned tokens and account-level endpoints (Workers, R2, KV).",
        ),
        field(
            "zone_id", "project", "Zone", placeholder="32 hex characters", resource="zones",
            help="The zone (domain) this project serves.",
        ),
    ]

    def normalize(self, key, value):
        value = value.strip()
        if key == "api_url":
            return _api_url(value)
        if key in ("account_id", "zone_id"):
            value = value.lower()
            if not _ID_RE.match(value):
                raise UsageError("{} must be a 32-character hexadecimal Cloudflare ID".format(key))
            return value
        raise UsageError("unknown field {!r}".format(key))

    def headers(self, token):
        return {"Authorization": "Bearer {}".format(check_token(token))}

    def _verify(self, account, token):
        """The token's verify record. A user token answers on ``/user/tokens/verify``; an
        account-owned token only on its account's endpoint, so that is tried second."""
        try:
            data, _headers = http.get_json(account["api_url"], "/user/tokens/verify", self.headers(token))
            return _ok(data), "user"
        except http.FetchError as exc:
            if not account.get("account_id") or exc.state == "rate_limited":
                raise
            first = exc
        try:
            data, _headers = http.get_json(
                account["api_url"],
                "/accounts/{}/tokens/verify".format(account["account_id"]),
                self.headers(token),
            )
        except http.FetchError:
            raise first from None
        return _ok(data), "account"

    def test(self, account, token):
        result, owner = self._verify(account, token)
        if not isinstance(result, dict):
            raise http.FetchError("unreachable", "The server did not answer like the Cloudflare API")
        status = result.get("status")
        if status != "active":
            return {"ok": False, "state": "invalid_token",
                    "summary": "The token is {}".format(status or "not active"), "facts": []}
        facts = [
            fact("Token status", "active", "positive"),
            fact("Token owner", "account" if owner == "account" else "user"),
        ]
        expires = result.get("expires_on")
        facts.append(fact("Expires", expires if expires else "never",
                          "neutral" if expires else "warning"))
        if account.get("account_id"):
            facts.append(fact("Account ID", account["account_id"]))
        return {"ok": True, "state": "connected", "summary": "Token is active", "facts": facts}

    def resources(self, kind, account, token):
        if kind == "zones":
            query = {"per_page": _PAGE_SIZE}
            if account.get("account_id"):
                query["account.id"] = account["account_id"]
            data, _headers = http.get_json(account["api_url"], "/zones", self.headers(token), query=query)
        elif kind == "accounts":
            data, _headers = http.get_json(
                account["api_url"], "/accounts", self.headers(token), query={"per_page": _PAGE_SIZE}
            )
        else:
            raise UsageError("unknown resource kind {!r} for cloudflare".format(kind),
                             hint="Available: zones, accounts")
        result = _ok(data)
        if not isinstance(result, list):
            raise http.FetchError("unreachable", "The server did not answer like the Cloudflare API")
        items = [
            {"value": item["id"], "label": item["name"]}
            for item in result
            if isinstance(item, dict) and isinstance(item.get("id"), str)
            and isinstance(item.get("name"), str)
        ]
        return {"items": items, "truncated": _truncated(data)}

    def describe_error(self, body):
        """Cloudflare's own ``errors[]`` as ``"[code] message; …"``, for the human message."""
        errors = body.get("errors") if isinstance(body, dict) else None
        if not isinstance(errors, list):
            return None
        parts = [
            "[{}] {}".format(e.get("code"), e.get("message"))
            for e in errors[:3]
            if isinstance(e, dict) and isinstance(e.get("message"), str)
        ]
        return "; ".join(parts) or None

    def detect(self, project_root, account):
        return {}
