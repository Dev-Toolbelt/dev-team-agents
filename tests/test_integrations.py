"""ADR-0023: the `devteam integration` CLI, its storage layers and its HTTP policy.

A local fake server (``http.server`` on 127.0.0.1 in a thread) emulates the GitHub and
Jira APIs; the loopback-http escape hatch is switched on through the environment for the
tests that need it. Every test runs against a temp store and a temp bound project passed
with ``--path``, so resolution can never walk up into the real repository.

The central promise is that the token never leaves the secret store and the
Authorization header: every test that plants one scans stdout, stderr, the parsed JSON
and every file in the store (except the secret store itself) for its absence.
"""

from __future__ import annotations

import base64
import http.server
import json
import os
import socket
import subprocess
import threading
import time
import unittest
from unittest import mock
import urllib.request

from devteam_support import StoreTestCase

from devteam import bind, paths, project
from devteam import update as update_module
from devteam.errors import EnvError, UsageError
from devteam.integrations import http as ihttp
from devteam import integrations
from devteam.lock import store_lock

TOKEN = "ghp_PLANTED-token-9d2f7c41"
LOOPBACK_ENV = ihttp.LOOPBACK_ENV


class FakeServer:
    """Serves ``routes[path] = (code, headers, body)``; records every request."""

    def __init__(self):
        self.routes = {}
        self.log = []
        outer = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                path = self.path.split("?", 1)[0]
                outer.log.append({"path": path, "query": self.path, "headers": {k.title(): v for k, v in self.headers.items()}})
                code, headers, body = outer.routes.get(path, (404, {}, {"message": "nope"}))
                if not isinstance(body, bytes):
                    body = json.dumps(body).encode("utf-8")
                self.send_response(code)
                for key, value in headers.items():
                    self.send_header(key, value)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        self.httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    @property
    def url(self):
        return "http://127.0.0.1:{}".format(self.httpd.server_address[1])

    def stop(self):
        self.httpd.shutdown()
        self.httpd.server_close()


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class IntegrationTestCase(StoreTestCase):
    def setUp(self):
        super().setUp()
        self._saved_loopback = os.environ.get(LOOPBACK_ENV)
        os.environ[LOOPBACK_ENV] = "1"
        self.addCleanup(self._restore_loopback)
        self.install_version("3.0.0", activate=True)
        self.root = self.new_project()
        self.pid = bind.bind(self.root, provider_names=["claude"])["project_id"]
        self.plain = self.tmp / "plain"
        self.plain.mkdir()
        self.server = FakeServer()
        self.addCleanup(self.server.stop)

    def _restore_loopback(self):
        if self._saved_loopback is None:
            os.environ.pop(LOOPBACK_ENV, None)
        else:
            os.environ[LOOPBACK_ENV] = self._saved_loopback

    def cli(self, *args, input_text=None, path=None):
        """``(code, body, stdout, stderr)`` for ``devteam integration ...`` on a path."""
        target = self.root if path is None else path
        code, out, err = self.run_cli(
            "integration", *args, "--path", str(target), "--json", input_text=input_text
        )
        try:
            body = json.loads(out)
        except ValueError:
            body = None
        if isinstance(body, dict) and body.get("ok") is True:
            body.pop("ok")
        self.outputs.append((out, err))
        return code, body, out, err

    @property
    def outputs(self):
        if not hasattr(self, "_outputs"):
            self._outputs = []
        return self._outputs

    def github_routes(self, login="octocat", scopes="repo, read:org", remaining="4999"):
        self.server.routes["/user"] = (
            200,
            {"X-OAuth-Scopes": scopes, "X-RateLimit-Remaining": remaining, "X-RateLimit-Limit": "5000"},
            {"login": login, "name": "The Octocat"},
        )

    def connect_github(self, token=TOKEN, extra=()):
        self.github_routes()
        return self.cli(
            "connect", "github", "--field", "api_url={}".format(self.server.url), *extra,
            input_text=token + "\n",
        )

    def connect_jira(self, deployment="cloud", token=TOKEN):
        fields = ["--field", "site_url={}".format(self.server.url), "--field", "deployment={}".format(deployment)]
        if deployment == "cloud":
            fields += ["--field", "email=me@example.com"]
        return self.cli("connect", "jira", *fields, input_text=token)

    def assert_token_absent(self, token=TOKEN):
        for out, err in self.outputs:
            self.assertNotIn(token, out)
            self.assertNotIn(token, err)
        secrets_dir = paths.secrets_dir().resolve() if paths.machine_id(create=False) else None
        for base in (self.home, self.root):
            for path in base.rglob("*"):
                if not path.is_file() or ".git" in path.parts:
                    continue
                if secrets_dir is not None and secrets_dir in path.resolve().parents:
                    continue
                text = path.read_text(encoding="utf-8", errors="replace")
                self.assertNotIn(token, text, "token leaked into {}".format(path))


class ViewShapeTest(IntegrationTestCase):
    def test_list_outside_a_bound_project_has_null_project(self):
        code, body, _o, _e = self.cli("list", path=self.plain)

        self.assertEqual(code, 0)
        self.assertIsNone(body["project_id"])
        self.assertEqual([v["name"] for v in body["integrations"]], ["github", "jira"])
        for view in body["integrations"]:
            self.assertIsNone(view["project"])
            self.assertFalse(view["project_configured"])
            self.assertEqual(view["detected"], {})
            self.assertFalse(view["connected"])
            self.assertEqual(view["status"]["state"], "not_connected")

    def test_show_matches_the_contract_keys(self):
        code, body, _o, _e = self.cli("show", "github")

        self.assertEqual(code, 0)
        view = body["integration"]
        self.assertEqual(
            set(view),
            {"name", "title", "description", "homepage", "auth", "fields", "account", "project",
             "project_problem", "detected", "connected", "project_configured", "status"},
        )
        self.assertEqual(set(view["auth"]), {"kind", "label", "help", "has_token", "stale", "backend"})
        self.assertFalse(view["auth"]["has_token"])
        self.assertFalse(view["auth"]["stale"])
        self.assertEqual(view["account"], {"api_url": "https://api.github.com"})
        self.assertEqual(view["project"], {})
        keys = {"key", "scope", "type", "label", "help", "required", "default", "placeholder",
                "options", "resource", "visible_when", "binds_token"}
        for field in view["fields"]:
            self.assertEqual(set(field), keys)
        self.assertEqual(set(view["status"]), {"state", "checked_at", "summary", "facts"})

    def test_jira_descriptor_carries_enum_and_visibility(self):
        _c, body, _o, _e = self.cli("show", "jira")

        fields = {f["key"]: f for f in body["integration"]["fields"]}
        self.assertEqual(fields["deployment"]["type"], "enum")
        self.assertEqual([o["value"] for o in fields["deployment"]["options"]], ["cloud", "data_center"])
        self.assertEqual(fields["email"]["visible_when"], {"key": "deployment", "equals": "cloud"})
        self.assertEqual(fields["project_key"]["resource"], "projects")

    def test_unknown_integration_is_a_usage_error(self):
        code, _b, _o, _e = self.cli("show", "gitlab")

        self.assertEqual(code, 2)

    def test_detected_repository_from_an_https_remote(self):
        subprocess.run(["git", "remote", "add", "origin", "https://github.com/octo/widgets.git"],
                       cwd=str(self.root), check=True)

        _c, body, _o, _e = self.cli("show", "github")

        self.assertEqual(body["integration"]["detected"], {"repository": "octo/widgets"})
        self.assertIsNotNone(body["integration"]["project"])

    def test_detected_repository_from_an_ssh_remote(self):
        subprocess.run(["git", "remote", "add", "origin", "git@github.com:octo/widgets.git"],
                       cwd=str(self.root), check=True)

        _c, body, _o, _e = self.cli("show", "github")

        self.assertEqual(body["integration"]["detected"], {"repository": "octo/widgets"})

    def test_a_remote_on_another_host_is_not_detected(self):
        subprocess.run(["git", "remote", "add", "origin", "git@gitlab.com:octo/widgets.git"],
                       cwd=str(self.root), check=True)

        _c, body, _o, _e = self.cli("show", "github")

        self.assertEqual(body["integration"]["detected"], {})

    def test_connected_needs_token_and_required_fields(self):
        self.connect_github()
        _c, body, _o, _e = self.cli("show", "github")
        self.assertTrue(body["integration"]["connected"])
        self.assertTrue(body["integration"]["auth"]["has_token"])
        self.assertEqual(body["integration"]["auth"]["backend"], "insecure")

        # jira: token stored but site_url missing is not connected
        self.cli("config", "set", "jira", "deployment", "data_center")
        _c, jira, _o, _e = self.cli("show", "jira")
        self.assertFalse(jira["integration"]["connected"])


class ConnectTest(IntegrationTestCase):
    def test_token_via_stdin_reaches_the_store_and_the_header(self):
        code, body, _o, _e = self.connect_github()

        self.assertEqual(code, 0)
        self.assertTrue(body["test"]["ok"])
        self.assertEqual(body["test"]["state"], "connected")
        self.assertEqual(self.server.log[-1]["headers"]["Authorization"], "Bearer " + TOKEN)
        self.assertEqual(self.server.log[-1]["headers"]["X-Github-Api-Version"], "2022-11-28")
        self.assertEqual(integrations.read_token("github"), TOKEN)
        self.assert_token_absent()

    def test_test_result_facts_and_status_are_persisted(self):
        _c, body, _o, _e = self.connect_github()

        facts = {f["label"]: f for f in body["test"]["facts"]}
        self.assertEqual(facts["Account"]["value"], "octocat")
        self.assertEqual(facts["Token scopes"]["value"], "repo, read:org")
        self.assertIn("4999 / 5000", facts["Rate limit"]["value"])
        self.assertEqual(body["integration"]["status"]["state"], "connected")
        self.assertEqual(body["integration"]["status"]["summary"], "Signed in as octocat")
        self.assertTrue(body["test"]["checked_at"])

    def test_fine_grained_token_has_no_scope_header(self):
        self.server.routes["/user"] = (200, {}, {"login": "octocat"})

        _c, body, _o, _e = self.cli(
            "connect", "github", "--field", "api_url=" + self.server.url, input_text=TOKEN
        )

        facts = {f["label"]: f["value"] for f in body["test"]["facts"]}
        self.assertEqual(facts["Token scopes"], "fine-grained")

    def test_empty_stdin_keeps_the_existing_token(self):
        self.connect_github()

        code, body, _o, _e = self.cli("connect", "github", input_text="\n")

        self.assertEqual(code, 0)
        self.assertTrue(body["test"]["ok"])
        self.assertEqual(self.server.log[-1]["headers"]["Authorization"], "Bearer " + TOKEN)

    def test_empty_stdin_without_a_token_is_a_usage_error(self):
        code, body, _o, _e = self.cli(
            "connect", "github", "--field", "api_url=" + self.server.url, input_text=""
        )

        self.assertEqual(code, 2)
        self.assertFalse(body["ok"])
        self.assertEqual(self.server.log, [])

    def test_field_rejects_project_scope_keys(self):
        code, _b, _o, err = self.cli(
            "connect", "github", "--field", "repository=octo/widgets", input_text=TOKEN
        )

        self.assertEqual(code, 2)
        self.assertIsNone(integrations.token_reference("github"))

    def test_field_without_equals_is_a_usage_error(self):
        code, _b, _o, _e = self.cli("connect", "github", "--field", "api_url", input_text=TOKEN)

        self.assertEqual(code, 2)

    def test_jira_cloud_uses_basic_auth(self):
        self.server.routes["/rest/api/3/myself"] = (
            200, {}, {"displayName": "Jo Doe", "emailAddress": "me@example.com"}
        )

        code, body, _o, _e = self.connect_jira("cloud")

        self.assertEqual(code, 0)
        expected = "Basic " + base64.b64encode(("me@example.com:" + TOKEN).encode()).decode()
        self.assertEqual(self.server.log[-1]["headers"]["Authorization"], expected)
        facts = {f["label"]: f["value"] for f in body["test"]["facts"]}
        self.assertEqual(facts["Account"], "Jo Doe")
        self.assertEqual(facts["Email"], "me@example.com")
        self.assert_token_absent()

    def test_jira_cloud_without_email_is_a_usage_error(self):
        code, _b, _o, _e = self.cli(
            "connect", "jira", "--field", "site_url=" + self.server.url, input_text=TOKEN
        )

        self.assertEqual(code, 2)

    def test_jira_data_center_uses_bearer_and_v2(self):
        self.server.routes["/rest/api/2/myself"] = (200, {}, {"displayName": "Jo Doe", "name": "jdoe"})

        code, body, _o, _e = self.connect_jira("data_center")

        self.assertEqual(code, 0)
        self.assertEqual(self.server.log[-1]["path"], "/rest/api/2/myself")
        self.assertEqual(self.server.log[-1]["headers"]["Authorization"], "Bearer " + TOKEN)
        facts = {f["label"]: f["value"] for f in body["test"]["facts"]}
        self.assertEqual(facts["Name"], "jdoe")


class TestCommandTest(IntegrationTestCase):
    def setUp(self):
        super().setUp()
        self.connect_github()

    def run_test_with(self, route):
        self.server.routes["/user"] = route
        code, body, _o, _e = self.cli("test", "github")
        return code, body

    def test_ok(self):
        code, body = self.run_test_with((200, {}, {"login": "octocat"}))

        self.assertEqual(code, 0)
        self.assertTrue(body["test"]["ok"])
        self.assertEqual(body["integration"]["status"]["state"], "connected")

    def test_401_is_invalid_token(self):
        code, body = self.run_test_with((401, {}, {"message": "Bad credentials"}))

        self.assertEqual(code, 0)
        self.assertFalse(body["test"]["ok"])
        self.assertEqual(body["test"]["state"], "invalid_token")
        self.assertEqual(body["integration"]["status"]["state"], "invalid_token")

    def test_403_without_rate_limit_signal_is_invalid_token(self):
        _c, body = self.run_test_with((403, {}, {"message": "forbidden"}))

        self.assertEqual(body["test"]["state"], "invalid_token")

    def test_403_with_exhausted_rate_limit_is_rate_limited(self):
        code, body = self.run_test_with((403, {"X-RateLimit-Remaining": "0"}, {"message": "limit"}))

        self.assertEqual(code, 0)
        self.assertEqual(body["test"]["state"], "rate_limited")
        self.assertFalse(body["test"]["ok"])

    def test_429_with_retry_after_is_rate_limited(self):
        _c, body = self.run_test_with((429, {"Retry-After": "30"}, {"message": "slow down"}))

        self.assertEqual(body["test"]["state"], "rate_limited")

    def test_server_error_is_unreachable(self):
        _c, body = self.run_test_with((500, {}, {}))

        self.assertEqual(body["test"]["state"], "unreachable")

    def test_non_json_answer_is_unreachable(self):
        _c, body = self.run_test_with((200, {}, b"<html>not json</html>"))

        self.assertEqual(body["test"]["state"], "unreachable")
        self.assertFalse(body["test"]["ok"])

    def test_server_down_is_unreachable_with_exit_zero(self):
        dead = "http://127.0.0.1:{}".format(free_port())
        self.cli("connect", "github", "--field", "api_url={}".format(dead), input_text=TOKEN)

        code, body, _o, _e = self.cli("test", "github")

        self.assertEqual(code, 0)
        self.assertFalse(body["test"]["ok"])
        self.assertEqual(body["test"]["state"], "unreachable")
        self.assertEqual(body["integration"]["status"]["state"], "unreachable")

    def test_response_over_the_size_cap_fails_cleanly(self):
        big = b'"' + b"a" * (ihttp.MAX_RESPONSE_BYTES + 16) + b'"'

        _c, body = self.run_test_with((200, {}, big))

        self.assertEqual(body["test"]["state"], "unreachable")
        self.assertIn("2 MB", body["test"]["summary"])

    def test_missing_token_is_a_usage_error(self):
        self.cli("disconnect", "github")

        code, _b, _o, _e = self.cli("test", "github")

        self.assertEqual(code, 2)

    def test_token_never_leaks_on_any_failure_path(self):
        for route in ((401, {}, {}), (403, {"Retry-After": "1"}, {}), (500, {}, {}), (200, {}, b"x")):
            self.run_test_with(route)
        self.cli("connect", "github", "--field", "api_url=http://127.0.0.1:{}".format(free_port()),
                 input_text=TOKEN)
        self.cli("test", "github")
        self.cli("resources", "github", "repos")
        self.cli("resources", "github", "nonsense")

        self.assert_token_absent()

    def test_token_read_is_audited_without_the_value(self):
        self.cli("test", "github")

        logs = list(self.home.rglob("audit.log"))
        self.assertTrue(logs)
        for log in logs:
            self.assertNotIn(TOKEN, log.read_text(encoding="utf-8"))


class HttpPolicyTest(IntegrationTestCase):
    def test_http_to_a_non_loopback_host_is_refused(self):
        code, _b, _o, _e = self.cli(
            "connect", "github", "--field", "api_url=http://example.com", input_text=TOKEN
        )

        self.assertEqual(code, 2)
        self.assertIsNone(integrations.token_reference("github"))

    def test_loopback_http_is_refused_without_the_env_var(self):
        os.environ.pop(LOOPBACK_ENV)
        self.github_routes()

        code, _b, _o, _e = self.cli(
            "connect", "github", "--field", "api_url=" + self.server.url, input_text=TOKEN
        )

        self.assertEqual(code, 2)
        self.assertEqual(self.server.log, [])

    def test_loopback_http_needs_the_value_one(self):
        os.environ[LOOPBACK_ENV] = "true"

        code, _b, _o, _e = self.cli(
            "connect", "github", "--field", "api_url=" + self.server.url, input_text=TOKEN
        )

        self.assertEqual(code, 2)

    def test_base_url_with_credentials_or_query_is_refused(self):
        for url in ("https://u:p@api.github.com", "https://api.github.com?x=1", "ftp://api.github.com"):
            code, _b, _o, _e = self.cli("config", "set", "github", "api_url", url)
            self.assertEqual(code, 2, url)

    def test_redirect_to_another_origin_is_refused_and_token_not_sent(self):
        other = FakeServer()
        self.addCleanup(other.stop)
        other.routes["/user"] = (200, {}, {"login": "evil"})
        self.connect_github()
        self.server.routes["/user"] = (302, {"Location": other.url + "/user"}, {})
        self.assertEqual(other.log, [])

        code, body, _o, _e = self.cli("test", "github")

        self.assertEqual(code, 0)
        self.assertEqual(body["test"]["state"], "unreachable")
        self.assertIn("redirect", body["test"]["summary"].lower())
        self.assertEqual(other.log, [])
        self.assert_token_absent()

    def test_redirect_within_the_same_origin_is_followed(self):
        self.server.routes["/user"] = (302, {"Location": self.server.url + "/moved"}, {})
        self.server.routes["/moved"] = (200, {}, {"login": "octocat"})

        code, body, _o, _e = self.cli(
            "connect", "github", "--field", "api_url=" + self.server.url, input_text=TOKEN
        )

        self.assertEqual(code, 0)
        self.assertTrue(body["test"]["ok"])

    def test_origin_compares_scheme_host_and_port(self):
        self.assertEqual(ihttp.origin("https://A.example.com/x"), ("https", "a.example.com", 443))
        self.assertNotEqual(ihttp.origin("https://a.example.com"), ihttp.origin("https://a.example.com:8443"))
        self.assertNotEqual(ihttp.origin("https://a.example.com"), ihttp.origin("http://a.example.com"))

    def test_update_keeps_refusing_redirects_off_the_release_hosts(self):
        handler = update_module._RestrictedRedirects()
        request = urllib.request.Request("https://github.com/x")

        with self.assertRaises(EnvError):
            handler.redirect_request(request, None, 302, "Found", {}, "https://evil.example.com/x")
        with self.assertRaises(EnvError):
            handler.redirect_request(request, None, 302, "Found", {}, "http://github.com/x")
        followed = handler.redirect_request(
            request, None, 302, "Found", {}, "https://objects.githubusercontent.com/x"
        )
        self.assertEqual(followed.full_url, "https://objects.githubusercontent.com/x")


class ConfigTest(IntegrationTestCase):
    def project_file(self, name="github"):
        return self.root / project.PROJECT_DIR / integrations.SETTINGS_DIR / "{}.json".format(name)

    def test_account_field_goes_to_the_store(self):
        code, body, _o, _e = self.cli("config", "set", "github", "api_url", "https://ghe.example.com/api/v3/")

        self.assertEqual(code, 0)
        stored = json.loads(integrations.account_path("github").read_text(encoding="utf-8"))
        self.assertEqual(stored, {"schema": 1, "config": {"api_url": "https://ghe.example.com/api/v3"}})
        self.assertFalse(self.project_file().exists())
        self.assertEqual(body["integration"]["account"]["api_url"], "https://ghe.example.com/api/v3")

    def test_project_field_goes_to_the_project_binding(self):
        code, body, _o, _e = self.cli("config", "set", "github", "repository", "octo/widgets")

        self.assertEqual(code, 0)
        self.assertEqual(
            json.loads(self.project_file().read_text(encoding="utf-8")),
            {"schema": 1, "config": {"repository": "octo/widgets"}},
        )
        self.assertFalse(integrations.account_path("github").exists())
        self.assertEqual(body["integration"]["project"], {"repository": "octo/widgets"})
        self.assertTrue(body["integration"]["project_configured"])

    def test_project_field_without_a_bound_project_is_a_usage_error(self):
        code, body, _o, _e = self.cli("config", "set", "github", "repository", "octo/widgets", path=self.plain)

        self.assertEqual(code, 2)
        self.assertFalse(body["ok"])
        self.assertFalse((self.plain / project.PROJECT_DIR).exists())

    def test_invalid_values_are_usage_errors(self):
        for args in (("github", "repository", "not-a-repo"), ("jira", "project_key", "1bad"),
                     ("jira", "deployment", "saas"), ("jira", "email", "nope"),
                     ("github", "repository", "  "), ("github", "nosuchkey", "x")):
            code, _b, _o, _e = self.cli("config", "set", *args)
            self.assertEqual(code, 2, args)

    def test_jira_project_key_is_upper_cased(self):
        self.cli("config", "set", "jira", "project_key", "proj")

        _c, body, _o, _e = self.cli("config", "get", "jira", "project_key")

        self.assertEqual(body, {"key": "project_key", "value": "PROJ", "scope": "project"})

    def test_config_get_all_and_one_key(self):
        self.cli("config", "set", "github", "repository", "octo/widgets")

        _c, everything, _o, _e = self.cli("config", "get", "github")
        _c, one, _o, _e = self.cli("config", "get", "github", "api_url")
        _c, unbound, _o, _e = self.cli("config", "get", "github", path=self.plain)

        self.assertEqual(everything, {"integration": "github", "account": {"api_url": "https://api.github.com"},
                                      "project": {"repository": "octo/widgets"}})
        self.assertEqual(one, {"key": "api_url", "value": "https://api.github.com", "scope": "account"})
        self.assertIsNone(unbound["project"])

    def test_account_change_drops_the_stale_status(self):
        self.connect_github()
        self.assertIsNotNone(integrations.read_status("github"))

        self.cli("config", "set", "github", "api_url", self.server.url + "/")

        self.assertIsNone(integrations.read_status("github"))
        _c, body, _o, _e = self.cli("show", "github")
        self.assertEqual(body["integration"]["status"]["state"], "unknown")

    def test_project_change_keeps_the_status(self):
        self.connect_github()

        self.cli("config", "set", "github", "repository", "octo/widgets")

        self.assertIsNotNone(integrations.read_status("github"))

    def test_unset_account_and_project_fields(self):
        self.cli("config", "set", "github", "repository", "octo/widgets")
        self.cli("config", "set", "github", "api_url", "https://ghe.example.com/api/v3")

        _c, project_result, _o, _e = self.cli("config", "unset", "github", "repository")
        _c, again, _o, _e = self.cli("config", "unset", "github", "repository")
        _c, account_result, _o, _e = self.cli("config", "unset", "github", "api_url")

        self.assertTrue(project_result["removed"])
        self.assertFalse(again["removed"])
        self.assertTrue(account_result["removed"])
        self.assertEqual(account_result["integration"]["account"]["api_url"], "https://api.github.com")
        self.assertEqual(json.loads(self.project_file().read_text())["config"], {})

    def test_unset_project_field_without_a_bound_project_is_a_usage_error(self):
        code, _b, _o, _e = self.cli("config", "unset", "github", "repository", path=self.plain)

        self.assertEqual(code, 2)

    def test_account_config_never_holds_the_token(self):
        self.connect_github()
        self.cli("config", "set", "github", "repository", "octo/widgets")

        self.assert_token_absent()


class DisconnectTest(IntegrationTestCase):
    def test_disconnect_removes_the_token_and_status_but_keeps_config(self):
        self.connect_github()

        code, body, _o, _e = self.cli("disconnect", "github")

        self.assertEqual(code, 0)
        self.assertTrue(body["changed"])
        self.assertIsNone(integrations.token_reference("github"))
        self.assertIsNone(integrations.read_status("github"))
        self.assertFalse(body["integration"]["connected"])
        self.assertEqual(body["integration"]["status"]["state"], "not_connected")
        stored = json.loads(integrations.account_path("github").read_text(encoding="utf-8"))
        self.assertEqual(stored["config"]["api_url"], self.server.url)
        self.assertNotIn(TOKEN, json.dumps(body))

    def test_keep_token_keeps_the_token_and_clears_status(self):
        self.connect_github()

        code, body, _o, _e = self.cli("disconnect", "github", "--keep-token")

        self.assertEqual(code, 0)
        self.assertTrue(body["changed"])
        self.assertIsNotNone(integrations.token_reference("github"))
        self.assertEqual(integrations.read_token("github"), TOKEN)
        self.assertIsNone(integrations.read_status("github"))
        self.assertEqual(body["integration"]["status"]["state"], "unknown")

    def test_disconnect_when_nothing_is_stored_reports_no_change(self):
        code, body, _o, _e = self.cli("disconnect", "github")

        self.assertEqual(code, 0)
        self.assertFalse(body["changed"])


class ResourcesTest(IntegrationTestCase):
    def test_github_repos_truncated_when_a_next_page_exists(self):
        self.connect_github()
        self.server.routes["/user/repos"] = (
            200,
            {"Link": '<https://api.github.com/user/repos?page=2>; rel="next"'},
            [{"full_name": "octo/a"}, {"full_name": "octo/b"}, {"bogus": 1}],
        )

        code, body, _o, _e = self.cli("resources", "github", "repos")

        self.assertEqual(code, 0)
        self.assertEqual(body["items"], [{"value": "octo/a", "label": "octo/a"},
                                         {"value": "octo/b", "label": "octo/b"}])
        self.assertTrue(body["truncated"])
        self.assertIn("per_page=100", self.server.log[-1]["query"])
        self.assertEqual(self.server.log[-1]["headers"]["Authorization"], "Bearer " + TOKEN)

    def test_github_repos_not_truncated_without_a_next_link(self):
        self.connect_github()
        self.server.routes["/user/repos"] = (200, {}, [{"full_name": "octo/a"}])

        _c, body, _o, _e = self.cli("resources", "github", "repos")

        self.assertFalse(body["truncated"])

    def test_jira_cloud_projects_truncated_until_is_last(self):
        self.server.routes["/rest/api/3/myself"] = (200, {}, {"displayName": "Jo"})
        self.connect_jira("cloud")
        self.server.routes["/rest/api/3/project/search"] = (
            200, {}, {"isLast": False, "values": [{"key": "ABC", "name": "Alpha"}, {"key": "XYZ"}]}
        )

        code, body, _o, _e = self.cli("resources", "jira", "projects")

        self.assertEqual(code, 0)
        self.assertEqual(body["items"], [{"value": "ABC", "label": "ABC - Alpha"},
                                         {"value": "XYZ", "label": "XYZ"}])
        self.assertTrue(body["truncated"])

    def test_jira_cloud_projects_complete_page(self):
        self.server.routes["/rest/api/3/myself"] = (200, {}, {"displayName": "Jo"})
        self.connect_jira("cloud")
        self.server.routes["/rest/api/3/project/search"] = (200, {}, {"isLast": True, "values": []})

        _c, body, _o, _e = self.cli("resources", "jira", "projects")

        self.assertEqual(body, {"items": [], "truncated": False})

    def test_jira_data_center_projects(self):
        self.server.routes["/rest/api/2/myself"] = (200, {}, {"displayName": "Jo"})
        self.connect_jira("data_center")
        self.server.routes["/rest/api/2/project"] = (200, {}, [{"key": "DC", "name": "Data"}])

        _c, body, _o, _e = self.cli("resources", "jira", "projects")

        self.assertEqual(body, {"items": [{"value": "DC", "label": "DC - Data"}], "truncated": False})
        self.assertEqual(self.server.log[-1]["headers"]["Authorization"], "Bearer " + TOKEN)

    def test_unknown_kind_is_a_usage_error(self):
        self.connect_github()

        code, _b, _o, _e = self.cli("resources", "github", "projects")

        self.assertEqual(code, 2)

    def test_network_failure_is_an_environment_error_with_a_hint(self):
        self.connect_github()
        self.server.routes["/user/repos"] = (401, {}, {})

        code, body, _o, _e = self.cli("resources", "github", "repos")

        self.assertEqual(code, 3)
        self.assertFalse(body["ok"])
        self.assertTrue(body.get("hint"))
        self.assert_token_absent()

    def test_not_connected_is_a_usage_error(self):
        code, _b, _o, _e = self.cli("resources", "github", "repos")

        self.assertEqual(code, 2)


class StatusRecordTest(IntegrationTestCase):
    def test_status_file_is_a_machine_local_record(self):
        self.assertTrue(paths.is_machine_local_record("integrations-status.json"))
        self.assertTrue(paths.is_machine_local_record("Integrations-Status.json"))

    def test_status_is_written_under_the_machine_dir_not_the_portable_store(self):
        self.connect_github()

        status = integrations.status_path()

        self.assertTrue(status.is_file())
        self.assertEqual(status.parent, paths.machine_dir())
        self.assertFalse((paths.data_dir() / "integrations-status.json").exists())
        self.assertIn("github", json.loads(status.read_text(encoding="utf-8"))["status"])

    def test_account_config_is_portable_and_outside_the_machine_dir(self):
        self.connect_github()

        self.assertEqual(integrations.account_path("github").parent, paths.data_dir() / "integrations")
        self.assertNotIn(paths.machine_dir(), integrations.account_path("github").parents)


class OriginBindingTest(IntegrationTestCase):
    def account_file(self, name="github"):
        return json.loads(integrations.account_path(name).read_text(encoding="utf-8"))["config"]

    def other_server(self):
        other = FakeServer()
        self.addCleanup(other.stop)
        other.routes["/user"] = (200, {}, {"login": "thief"})
        return other

    def test_connect_records_the_origin_but_never_exposes_it(self):
        _c, body, out, _e = self.connect_github()

        port = self.server.httpd.server_address[1]
        self.assertEqual(self.account_file()["token_origin"], "http://127.0.0.1:{}".format(port))
        view = body["integration"]
        self.assertNotIn("token_origin", out)
        self.assertEqual(view["account"], {"api_url": self.server.url})
        self.assertFalse(view["auth"]["stale"])
        self.assertTrue(view["connected"])
        _c, got, _o, _e = self.cli("config", "get", "github")
        self.assertNotIn("token_origin", json.dumps(got))

    def test_changing_the_origin_makes_the_token_stale_and_sends_nothing(self):
        self.connect_github()
        other = self.other_server()

        self.cli("config", "set", "github", "api_url", other.url)
        _c, shown, _o, _e = self.cli("show", "github")
        code, _b, _o, err = self.cli("test", "github")
        res_code, _b, _o, _e = self.cli("resources", "github", "repos")

        view = shown["integration"]
        self.assertTrue(view["auth"]["has_token"])
        self.assertTrue(view["auth"]["stale"])
        self.assertFalse(view["connected"])
        self.assertEqual(view["status"]["state"], "not_connected")
        self.assertIn("new token", view["status"]["summary"])
        self.assertEqual((code, res_code), (2, 2))
        self.assertIn("api_url changed since the token was stored", err + _o)
        self.assertEqual(other.log, [])
        self.assertEqual(integrations.read_token("github"), TOKEN)

    def test_reconnecting_with_a_new_token_clears_the_stale_state(self):
        self.connect_github()
        other = self.other_server()
        self.cli("config", "set", "github", "api_url", other.url)

        _c, body, _o, _e = self.cli("connect", "github", input_text="ghp_new-token\n")

        self.assertTrue(body["test"]["ok"])
        self.assertFalse(body["integration"]["auth"]["stale"])
        self.assertEqual(other.log[-1]["headers"]["Authorization"], "Bearer ghp_new-token")

    def test_connect_with_a_new_origin_and_no_new_token_sends_nothing(self):
        self.connect_github()
        other = self.other_server()

        code, body, _o, _e = self.cli("connect", "github", "--field", "api_url={}".format(other.url))

        self.assertEqual(code, 0)
        self.assertFalse(body["test"]["ok"])
        self.assertEqual(body["test"]["state"], "not_connected")
        self.assertTrue(body["integration"]["auth"]["stale"])
        self.assertEqual(other.log, [])

    def test_a_token_without_a_recorded_origin_is_stale(self):
        self.connect_github()
        path = integrations.account_path("github")
        data = json.loads(path.read_text(encoding="utf-8"))
        del data["config"]["token_origin"]
        path.write_text(json.dumps(data), encoding="utf-8")
        before = len(self.server.log)

        _c, shown, _o, _e = self.cli("show", "github")
        code, _b, _o, _e = self.cli("test", "github")

        self.assertTrue(shown["integration"]["auth"]["stale"])
        self.assertEqual(code, 2)
        self.assertEqual(len(self.server.log), before)

    def test_unsetting_the_url_back_to_the_default_is_a_change_of_origin(self):
        self.connect_github()

        self.cli("config", "unset", "github", "api_url")
        _c, shown, _o, _e = self.cli("show", "github")

        self.assertTrue(shown["integration"]["auth"]["stale"])

    def test_jira_site_url_is_bound_too_but_email_is_not(self):
        self.server.routes["/rest/api/3/myself"] = (200, {}, {"displayName": "Me"})
        self.connect_jira()
        self.cli("config", "set", "jira", "email", "other@example.com")
        _c, same, _o, _e = self.cli("show", "jira")
        other = self.other_server()

        self.cli("config", "set", "jira", "site_url", other.url)
        _c, moved, _o, _e = self.cli("show", "jira")

        self.assertFalse(same["integration"]["auth"]["stale"])
        self.assertTrue(moved["integration"]["auth"]["stale"])

    def test_a_stale_token_is_never_used_for_resources_either(self):
        self.connect_github()
        other = self.other_server()
        self.cli("config", "set", "github", "api_url", other.url)

        with self.assertRaises(integrations.UsageError):
            integrations.resources("github", "repos")
        self.assertEqual(other.log, [])


class HeaderAndDeadlineTest(IntegrationTestCase):
    def test_a_token_with_a_control_character_is_an_invalid_token_not_a_crash(self):
        self.connect_github()
        before = len(self.server.log)

        with mock.patch.object(integrations, "read_token", return_value="abc\ndef"):
            result = integrations.test("github")

        self.assertEqual(result["state"], "invalid_token")
        self.assertIn("cannot be sent in a header", result["summary"])
        self.assertEqual(len(self.server.log), before)

    def test_http_layer_maps_header_value_errors_to_invalid_token(self):
        self.server.routes["/x"] = (200, {}, {})
        for bad in ("Bearer a\nb", "Bearer \u20ac\u4e2d"):
            with self.assertRaises(ihttp.FetchError) as caught:
                ihttp.get_json(self.server.url, "/x", {"Authorization": bad})
            self.assertEqual(caught.exception.state, "invalid_token")
            self.assertNotIn("\u20ac", caught.exception.summary)

    def test_jira_rejects_a_token_with_a_space(self):
        self.server.routes["/rest/api/3/myself"] = (200, {}, {"displayName": "Me"})
        self.connect_jira()
        with mock.patch.object(integrations, "read_token", return_value="two words"):
            result = integrations.test("jira")
        self.assertEqual(result["state"], "invalid_token")

    def test_a_drip_fed_answer_hits_the_total_deadline(self):
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        self.addCleanup(listener.close)

        def serve():
            conn, _ = listener.accept()
            try:
                conn.recv(4096)
                conn.sendall(b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: 200\r\n\r\n")
                for _ in range(40):
                    conn.sendall(b" ")
                    time.sleep(0.15)
            except OSError:
                pass
            finally:
                conn.close()

        threading.Thread(target=serve, daemon=True).start()
        url = "http://127.0.0.1:{}".format(listener.getsockname()[1])
        started = time.monotonic()

        with mock.patch.object(ihttp, "TOTAL_DEADLINE", 0.6), mock.patch.object(ihttp, "CHUNK", 1):
            with self.assertRaises(ihttp.FetchError) as caught:
                ihttp.get_json(url, "/x", {})

        self.assertEqual(caught.exception.state, "unreachable")
        self.assertEqual(caught.exception.summary, "The server did not answer in time")
        self.assertLess(time.monotonic() - started, 3)


class LockAndConsistencyTest(IntegrationTestCase):
    def run_while_locked(self, call):
        """``call`` must not finish while the integrations lock is held elsewhere."""
        done = threading.Event()
        errors = []

        def target():
            try:
                call()
            except Exception as exc:  # noqa: BLE001 - surfaced below
                errors.append(exc)
            done.set()

        with store_lock(integrations.LOCK):
            thread = threading.Thread(target=target, daemon=True)
            thread.start()
            self.assertFalse(done.wait(0.5), "the write did not wait for the lock")
        self.assertTrue(done.wait(10))
        thread.join()
        self.assertEqual(errors, [])

    def test_config_set_and_unset_and_connect_wait_for_the_lock(self):
        self.github_routes()
        self.run_while_locked(lambda: integrations.config_set("github", "api_url", self.server.url))
        self.assertEqual(integrations.read_account("github")["api_url"], self.server.url)

        self.run_while_locked(lambda: integrations.config_unset("github", "api_url"))
        self.assertNotIn("api_url", integrations.read_account("github"))

        self.run_while_locked(lambda: integrations.connect("github", {"api_url": self.server.url}, TOKEN))
        self.assertEqual(integrations.read_token("github"), TOKEN)

    def test_project_binding_write_waits_for_the_lock(self):
        self.run_while_locked(
            lambda: integrations.config_set("github", "repository", "octo/widgets", self.root, self.pid)
        )
        self.assertEqual(
            integrations.read_project(self.root, "github"), {"repository": "octo/widgets"}
        )

    def test_a_test_does_not_record_a_result_for_a_config_that_changed_meanwhile(self):
        self.connect_github()
        with integrations.store_lock(integrations.LOCK):
            integrations._update_status_locked("github", None)

        def changed_during_the_request(adapter, account, token):
            integrations.config_set("github", "api_url", self.server.url + "/v3")
            return {"ok": True, "state": "connected", "summary": "x", "facts": [], "checked_at": "t"}

        with mock.patch.object(integrations, "run_test", changed_during_the_request):
            integrations.test("github")

        self.assertIsNone(integrations.read_status("github"))

    def test_connect_does_not_record_a_result_for_a_config_that_changed_meanwhile(self):
        self.github_routes()

        def changed_during_the_request(adapter, account, token):
            integrations.config_set("github", "api_url", self.server.url + "/v3")
            return {"ok": True, "state": "connected", "summary": "x", "facts": [], "checked_at": "t"}

        with mock.patch.object(integrations, "run_test", changed_during_the_request):
            integrations.connect("github", {"api_url": self.server.url}, TOKEN)

        self.assertIsNone(integrations.read_status("github"))

    def test_connect_reports_where_the_new_token_went(self):
        self.github_routes()
        real = integrations.creds.set_entry

        def insecure(*args, **kwargs):
            entry = real(*args, **kwargs)
            return dict(entry, source="insecure")

        with mock.patch.object(integrations.creds, "set_entry", insecure):
            _result, backend = integrations.connect("github", {"api_url": self.server.url}, TOKEN)
        _result, kept = integrations.connect("github", {}, None)

        self.assertEqual(backend, "insecure")
        self.assertIsNone(kept)


class StatusFileToleranceTest(IntegrationTestCase):
    def quarantined(self):
        return [
            p for p in self.home.rglob("integrations-status.json")
            if "quarantine" in p.parts
        ]

    def test_a_malformed_or_newer_status_file_reads_as_unknown(self):
        self.connect_github()
        for garbage in ("{not json", json.dumps({"schema": 99, "status": {}}), "[1]"):
            integrations.status_path().write_text(garbage, encoding="utf-8")

            code, body, _o, _e = self.cli("show", "github")
            list_code, listed, _o, _e = self.cli("list")

            self.assertEqual((code, list_code), (0, 0))
            self.assertEqual(body["integration"]["status"]["state"], "unknown")
            self.assertEqual(len(listed["integrations"]), 2)

    def test_the_next_write_sets_the_unreadable_file_aside_instead_of_deleting_it(self):
        self.connect_github()
        integrations.status_path().write_text("{not json", encoding="utf-8")

        code, body, _o, _e = self.cli("test", "github")

        self.assertEqual(code, 0)
        self.assertEqual(body["integration"]["status"]["state"], "connected")
        moved = self.quarantined()
        self.assertEqual(len(moved), 1)
        self.assertEqual(moved[0].read_text(encoding="utf-8"), "{not json")


class ProjectBindingSafetyTest(IntegrationTestCase):
    def settings_dir(self):
        return self.root / project.PROJECT_DIR / integrations.SETTINGS_DIR

    def test_a_symlinked_settings_directory_is_refused(self):
        outside = self.tmp / "outside"
        outside.mkdir()
        self.settings_dir().symlink_to(outside, target_is_directory=True)

        code, _b, out, err = self.cli("config", "set", "github", "repository", "octo/widgets")
        unset_code, _b, _o, _e = self.cli("config", "unset", "github", "repository")

        self.assertEqual(code, 2)
        self.assertIn("symbolic link", out + err)
        self.assertEqual(list(outside.iterdir()), [])
        self.assertEqual(unset_code, 0)

    def test_a_symlinked_settings_file_is_refused(self):
        outside = self.tmp / "outside.json"
        outside.write_text('{"schema": 1, "config": {}}', encoding="utf-8")
        self.settings_dir().mkdir(parents=True)
        (self.settings_dir() / "github.json").symlink_to(outside)

        code, _b, _o, _e = self.cli("config", "set", "github", "repository", "octo/widgets")

        self.assertEqual(code, 2)
        self.assertEqual(json.loads(outside.read_text(encoding="utf-8")), {"schema": 1, "config": {}})

    def test_a_symlinked_dev_team_agents_directory_is_refused(self):
        real = self.root / project.PROJECT_DIR
        moved = self.tmp / "moved-dta"
        real.rename(moved)
        real.symlink_to(moved, target_is_directory=True)

        code, _b, _o, _e = self.cli("config", "set", "github", "repository", "octo/widgets")

        self.assertEqual(code, 2)
        self.assertFalse((moved / integrations.SETTINGS_DIR).exists())

    def test_invalid_committed_values_are_treated_as_unset(self):
        self.settings_dir().mkdir(parents=True)
        (self.settings_dir() / "github.json").write_text(
            json.dumps({"schema": 1, "config": {"repository": "not a repo"}}), encoding="utf-8"
        )
        (self.settings_dir() / "jira.json").write_text(
            json.dumps({"schema": 1, "config": {"project_key": "9bad key"}}), encoding="utf-8"
        )

        code, body, _o, _e = self.cli("show", "github")
        jira_code, jira, _o, _e = self.cli("show", "jira")
        get_code, got, _o, _e = self.cli("config", "get", "github", "repository")

        self.assertEqual((code, jira_code, get_code), (0, 0, 0))
        self.assertEqual(body["integration"]["project"], {})
        self.assertFalse(body["integration"]["project_configured"])
        self.assertEqual(jira["integration"]["project"], {})
        self.assertIsNone(got["value"])

    def test_valid_committed_values_are_still_read(self):
        self.settings_dir().mkdir(parents=True)
        (self.settings_dir() / "jira.json").write_text(
            json.dumps({"schema": 1, "config": {"project_key": "proj"}}), encoding="utf-8"
        )

        _c, jira, _o, _e = self.cli("show", "jira")

        self.assertEqual(jira["integration"]["project"], {"project_key": "PROJ"})


if __name__ == "__main__":
    unittest.main()


class TokenRebindingTest(IntegrationTestCase):
    """A new token can never be sent to the origin the previous one was stored for."""

    def other_origin(self):
        other = FakeServer()
        self.addCleanup(other.stop)
        other.routes["/user"] = (200, {}, {"login": "other"})
        return other

    def test_a_failed_config_write_after_storing_the_token_leaves_it_stale(self):
        self.assertEqual(self.connect_github()[0], 0)
        other = self.other_origin()
        real_write = integrations._write_account
        calls = []

        def fail_the_final_write(name, config):
            calls.append(dict(config))
            if integrations.TOKEN_ORIGIN in config:
                raise OSError("disk full")
            real_write(name, config)

        with mock.patch.object(integrations, "_write_account", fail_the_final_write):
            with self.assertRaises(OSError):
                integrations.connect("github", {"api_url": other.url}, "ghp_SECOND-token")

        with self.assertRaises(UsageError):
            integrations.test("github")
        self.assertEqual(self.server.log[-1]["path"], "/user")
        self.assertTrue(all("ghp_SECOND-token" not in str(e["headers"]) for e in self.server.log))
        self.assertEqual(other.log, [])

    def test_a_connect_between_reading_the_config_and_the_token_sends_nothing(self):
        self.assertEqual(self.connect_github()[0], 0)
        other = self.other_origin()
        before = len(self.server.log)
        real_read = integrations.read_token

        def connect_meanwhile(name):
            integrations.connect("github", {"api_url": other.url}, "ghp_SECOND-token")
            return real_read(name)

        with mock.patch.object(integrations, "read_token", connect_meanwhile):
            with self.assertRaises(UsageError):
                integrations.test("github")
        # The only request the old origin saw is none; the new one got the connect's own test.
        self.assertEqual(len(self.server.log), before)
        self.assertTrue(all("ghp_SECOND-token" in e["headers"].get("Authorization", "") for e in other.log))

    def test_replacing_the_token_on_the_same_origin_invalidates_an_in_flight_result(self):
        self.assertEqual(self.connect_github()[0], 0)

        real_run = integrations.run_test
        replaced = []

        def replaced_during_the_request(adapter, account, token):
            if replaced:
                return real_run(adapter, account, token)
            replaced.append(True)
            integrations.connect("github", {}, "ghp_REPLACED-token")
            return {"ok": False, "state": "invalid_token", "summary": "old", "facts": [], "checked_at": "t"}

        with mock.patch.object(integrations, "run_test", replaced_during_the_request):
            integrations.test("github")
        record = integrations.read_status("github")
        self.assertNotEqual((record or {}).get("summary"), "old")

    def test_an_unsendable_token_never_reaches_the_secret_store(self):
        with self.assertRaises(UsageError):
            integrations.connect("github", {"api_url": self.server.url}, "has a space")
        self.assertIsNone(integrations.token_reference("github"))


class TokenNotOnThisMachineTest(IntegrationTestCase):
    def test_test_reports_not_connected_and_resources_explains(self):
        self.assertEqual(self.connect_github()[0], 0)
        entry = integrations.token_reference("github")
        from devteam import secrets as secrets_module
        secrets_module.delete(entry["ref"], entry["source"])

        result = integrations.test("github")
        self.assertFalse(result["ok"])
        self.assertEqual(result["state"], "not_connected")
        self.assertIn("not stored on this machine", result["summary"])
        with self.assertRaises(UsageError) as caught:
            integrations.resources("github", "repos")
        self.assertIn("not stored on this machine", str(caught.exception))


class ProjectBindingToleranceTest(IntegrationTestCase):
    def test_a_malformed_binding_reads_as_unset_with_a_problem(self):
        target = integrations.project_path(self.root, "github")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("{not json", encoding="utf-8")

        code, body, _o, _e = self.cli("list")
        self.assertEqual(code, 0)
        views = {v["name"]: v for v in body["integrations"]}
        self.assertEqual(views["github"]["project"], {})
        self.assertIsInstance(views["github"]["project_problem"], str)
        self.assertIsNone(views["jira"]["project_problem"])

    def test_a_filled_binding_skips_detection(self):
        integrations.config_set("github", "repository", "acme/widgets", self.root, self.pid)
        with mock.patch.object(integrations.get_adapter("github"), "detect") as detect:
            integrations.build_view(integrations.get_adapter("github"), self.root, self.pid)
        detect.assert_not_called()


class DescriptorAndCliTest(IntegrationTestCase):
    def test_only_the_origin_field_binds_the_token(self):
        _c, body, _o, _e = self.cli("show", "jira")
        binds = {f["key"]: f["binds_token"] for f in body["integration"]["fields"]}
        self.assertEqual(binds, {"site_url": True, "deployment": False, "email": False, "project_key": False})

    def test_connect_checks_required_fields_before_reading_the_token(self):
        code, body, _o, err = self.cli("connect", "jira", input_text=TOKEN)
        self.assertEqual(code, 2)
        self.assertIn("site_url", err + json.dumps(body))
        self.assertIsNone(integrations.token_reference("jira"))

    def test_repository_refuses_dot_only_segments(self):
        for value in ("../..", "./x", "acme/.."):
            with self.assertRaises(UsageError):
                integrations.get_adapter("github").normalize("repository", value)
        self.assertEqual(integrations.get_adapter("github").normalize("repository", "a.b/c.d"), "a.b/c.d")

    def test_a_malformed_redirect_target_is_unreachable_not_a_bad_token(self):
        self.server.routes["/user"] = (302, {"Location": "http://127.0.0.1:99999/user"}, {})
        self.assertEqual(
            self.cli("connect", "github", "--field", "api_url={}".format(self.server.url), input_text=TOKEN)[0],
            0,
        )
        result = integrations.test("github")
        self.assertEqual(result["state"], "unreachable")
        self.assertIn("redirect", result["summary"])
