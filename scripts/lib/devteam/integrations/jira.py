"""Jira Cloud and Jira Data Center over the REST API."""

from __future__ import annotations

import base64
import re

from ..errors import UsageError
from . import http
from .base import check_token, fact, field

_KEY_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,49}$")


class Jira:
    name = "jira"
    origin_key = "site_url"
    title = "Jira"
    description = "Read Jira projects with an API token (Cloud) or a personal access token (Data Center)."
    homepage = "https://www.atlassian.com/software/jira"
    auth = {
        "kind": "token",
        "label": "API token",
        "help": "Cloud: an Atlassian API token, used with your account email. Data Center: a "
        "personal access token. Stored in the OS secret store.",
    }
    fields = [
        field("site_url", "account", "Site URL", required=True,
              placeholder="https://acme.atlassian.net",
              help="The base URL of your Jira site."),
        field("deployment", "account", "Deployment", type="enum", default="cloud",
              options=[{"value": "cloud", "label": "Cloud"},
                       {"value": "data_center", "label": "Data Center"}],
              help="Cloud signs in with email + API token; Data Center with a bearer token."),
        field("email", "account", "Account email", required=True, placeholder="you@example.com",
              visible_when={"key": "deployment", "equals": "cloud"},
              help="The Atlassian account the API token belongs to."),
        field("project_key", "project", "Project key", placeholder="PROJ", resource="projects",
              help="The Jira project this repository tracks."),
    ]

    def normalize(self, key, value):
        value = value.strip()
        if key == "site_url":
            return http.validate_base_url(value, "site_url")
        if key == "deployment":
            if value not in ("cloud", "data_center"):
                raise UsageError("deployment must be 'cloud' or 'data_center'")
            return value
        if key == "email":
            if "@" not in value or any(c.isspace() for c in value):
                raise UsageError("email must be an email address")
            return value
        if key == "project_key":
            if not _KEY_RE.match(value):
                raise UsageError("project_key must be a Jira project key such as PROJ")
            return value.upper()
        raise UsageError("unknown field {!r}".format(key))

    def _cloud(self, account):
        return account.get("deployment", "cloud") == "cloud"

    def _headers(self, account, token):
        check_token(token)
        if self._cloud(account):
            raw = "{}:{}".format(account.get("email", ""), token).encode("utf-8")
            return {"Authorization": "Basic {}".format(base64.b64encode(raw).decode("ascii"))}
        return {"Authorization": "Bearer {}".format(token)}

    def _api(self, account):
        return "/rest/api/3" if self._cloud(account) else "/rest/api/2"

    def test(self, account, token):
        data, _headers = http.get_json(
            account["site_url"], self._api(account) + "/myself", self._headers(account, token)
        )
        if not isinstance(data, dict) or not data.get("displayName"):
            raise http.FetchError("unreachable", "The server did not answer like the Jira API")
        facts = [fact("Account", data["displayName"], "positive")]
        if self._cloud(account):
            if data.get("emailAddress"):
                facts.append(fact("Email", data["emailAddress"]))
        elif data.get("name"):
            facts.append(fact("Name", data["name"]))
        facts.append(fact("Site", account["site_url"]))
        return {"ok": True, "state": "connected",
                "summary": "Signed in as {}".format(data["displayName"]), "facts": facts}

    def resources(self, kind, account, token):
        if kind != "projects":
            raise UsageError("unknown resource kind {!r} for jira".format(kind),
                             hint="Available: projects")
        headers = self._headers(account, token)
        if self._cloud(account):
            data, _ = http.get_json(account["site_url"], "/rest/api/3/project/search", headers,
                                    query={"maxResults": "100"})
            if not isinstance(data, dict) or not isinstance(data.get("values"), list):
                raise http.FetchError("unreachable", "The server did not answer like the Jira API")
            rows, truncated = data["values"], data.get("isLast") is False
        else:
            data, _ = http.get_json(account["site_url"], "/rest/api/2/project", headers)
            if not isinstance(data, list):
                raise http.FetchError("unreachable", "The server did not answer like the Jira API")
            rows, truncated = data, False
        items = []
        for row in rows:
            if isinstance(row, dict) and isinstance(row.get("key"), str):
                name = row.get("name")
                label = "{} - {}".format(row["key"], name) if isinstance(name, str) and name else row["key"]
                items.append({"value": row["key"], "label": label})
        return {"items": items, "truncated": truncated}

    def detect(self, project_root, account):
        return {}
