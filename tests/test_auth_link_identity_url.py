"""link_identity_url accepts the provider's authorize URL, and only that host."""

from __future__ import annotations

import sys
import types
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts" / "lib"))

from devteam import auth_gotrue  # noqa: E402
from devteam.errors import EnvError  # noqa: E402

BASE = "https://proj.example.test"


def _client():
    identity = types.SimpleNamespace(supabase_url=BASE, anon_key="anon")
    return auth_gotrue.Client(identity)


class LinkIdentityUrlTest(unittest.TestCase):
    def _link(self, provider, response):
        client = _client()
        with mock.patch.object(client, "_call", return_value=response):
            return client.link_identity_url("tok", provider, "http://127.0.0.1:1/cb", "chal")

    def _assert_rejected(self, provider, response):
        with self.assertRaises(EnvError) as ctx:
            self._link(provider, response)
        self.assertEqual(ctx.exception.details["reason"], "bad_response")

    def test_github_authorize_url_is_returned_unchanged(self):
        # Arrange
        url = "https://github.com/login/oauth/authorize?client_id=x&state=y"
        # Act
        result = self._link("github", {"url": url})
        # Assert
        self.assertEqual(result, url)

    def test_google_authorize_url_is_returned_unchanged(self):
        # Arrange
        url = "https://accounts.google.com/o/oauth2/v2/auth?client_id=x"
        # Act
        result = self._link("google", {"url": url})
        # Assert
        self.assertEqual(result, url)

    def test_provider_host_is_matched_case_insensitively(self):
        # Arrange
        url = "https://GitHub.com/x"
        # Act
        result = self._link("github", {"url": url})
        # Assert
        self.assertEqual(result, url)

    def test_project_url_stays_accepted(self):
        # Arrange
        url = BASE + "/auth/v1/authorize?provider=github"
        # Act
        result = self._link("github", {"url": url})
        # Assert
        self.assertEqual(result, url)

    def test_unsafe_urls_are_rejected(self):
        cases = [
            ("github", "https://evil.example/login/oauth/authorize"),
            ("github", "https://github.com.evil.example/x"),
            ("github", "https://evil.example/github.com/x"),
            ("github", "https://github.com@evil.example/x"),
            ("github", "http://github.com/login/oauth/authorize"),
            ("github", "https://accounts.google.com/o/oauth2/v2/auth"),
            ("google", "https://github.com/login/oauth/authorize"),
            ("github", "https://evil.example\\@github.com/x"),
            ("github", "https://u@github.com/x"),
            ("github", "https://github.com./x"),
            ("github", "https://github.com:8443/x"),
            ("github", "https://github.com:abc/x"),
            ("github", " https://github.com/x"),
            ("github", "https://github.com/x\r\ny"),
            ("github", "https://github.com/x\x1b"),
            ("google", "https://accounts.google.com@evil.example/x"),
            ("google", "http://accounts.google.com/x"),
            ("gitlab", "https://github.com/x"),
        ]
        for provider, url in cases:
            with self.subTest(provider=provider, url=url):
                # Arrange / Act / Assert
                self._assert_rejected(provider, {"url": url})

    def test_missing_or_non_string_url_is_rejected(self):
        for response in ({}, {"url": None}, {"url": 5}, {"url": ["https://github.com/x"]}, None, "x"):
            with self.subTest(response=response):
                self._assert_rejected("github", response)


if __name__ == "__main__":
    unittest.main()
