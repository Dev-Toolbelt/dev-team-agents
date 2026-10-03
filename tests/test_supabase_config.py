"""Static checks over the Supabase project files (ADR-0029 SR-7, 11, 12, 14, 31, 32).

No database runs here: these read `infra/supabase/` as text, so a regression in the shipped
configuration or migrations fails in the ordinary suite instead of only in a deployed project.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

INFRA = Path(__file__).resolve().parent.parent / "infra" / "supabase"


def parse_toml(text):
    """``{section: {key: raw value}}`` for the flat tables config.toml uses (py3.9 has no tomllib)."""
    sections, current = {"": {}}, ""
    for raw in text.splitlines():
        line = re.sub(r"^\s*#.*$|\s+#.*$", "", raw).strip()
        if not line:
            continue
        header = re.match(r"^\[(.+)\]$", line)
        if header:
            current = header.group(1)
            sections.setdefault(current, {})
            continue
        key, _, value = line.partition("=")
        sections[current][key.strip()] = value.strip()
    return sections


@unittest.skipUnless(INFRA.is_dir(), "infra/supabase is not part of this tree")
class SupabaseConfigTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = parse_toml((INFRA / "config.toml").read_text(encoding="utf-8"))

    def test_redirect_allow_list_holds_only_the_loopback_callback(self):
        urls = re.findall(r'"([^"]+)"', self.cfg["auth"]["additional_redirect_urls"])
        self.assertEqual(urls, ["http://127.0.0.1:*/callback"])
        for url in urls + [self.cfg["auth"]["site_url"].strip('"')]:
            self.assertNotIn("**", url)
            self.assertNotIn("localhost", url)
            self.assertTrue(url.startswith("http://127.0.0.1"), url)

    def test_codes_are_eight_digits_valid_ten_minutes_and_rate_limited(self):
        email = self.cfg["auth.email"]
        self.assertEqual(email["otp_length"], "8")
        self.assertEqual(email["otp_expiry"], "600")
        self.assertEqual(email["max_frequency"], '"60s"')

    def test_linking_and_sign_in_methods(self):
        auth, email = self.cfg["auth"], self.cfg["auth.email"]
        self.assertEqual(auth["enable_anonymous_sign_ins"], "false")
        self.assertEqual(email["enable_confirmations"], "true")
        self.assertEqual(email["double_confirm_changes"], "true")
        self.assertEqual(self.cfg["auth.sms"]["enable_signup"], "false")

    def test_refresh_token_rotation_and_password_minimum(self):
        self.assertEqual(self.cfg["auth"]["enable_refresh_token_rotation"], "true")
        self.assertGreaterEqual(int(self.cfg["auth"]["minimum_password_length"]), 10)
        self.assertEqual(self.cfg["auth"]["password_requirements"], '""')


    def test_email_templates_resolve_from_the_cli_workdir(self):
        # The Supabase CLI resolves content_path from the directory holding supabase/, not
        # from supabase/ itself, so `./templates/...` fails `supabase start` and `config push`.
        for section, values in self.cfg.items():
            if "content_path" in values:
                with self.subTest(section=section):
                    path = values["content_path"].strip('"')
                    self.assertTrue(path.startswith("./supabase/"), path)
                    self.assertTrue((INFRA.parent / path).resolve() == (INFRA / path[len("./supabase/"):]).resolve())
                    self.assertTrue((INFRA / path[len("./supabase/"):]).is_file(), path)

    def test_the_sections_dev_local_switches_off_are_on_in_the_committed_config(self):
        # dev-local.sh rewrites exactly `enabled = true` on the line after each header and
        # refuses to start otherwise; the committed file keeps all three on for the cloud.
        text = (INFRA / "config.toml").read_text(encoding="utf-8")
        for section in ("auth.email.smtp", "auth.external.google", "auth.external.github"):
            with self.subTest(section=section):
                self.assertIn("[{}]\nenabled = true\n".format(section), text)
        self.assertIn("auth.external.github", (INFRA / "dev-local.sh").read_text(encoding="utf-8"))


@unittest.skipUnless(INFRA.is_dir(), "infra/supabase is not part of this tree")
class MigrationPolicyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        files = sorted((INFRA / "migrations").glob("*.sql"))
        cls.sql = "\n".join(f.read_text(encoding="utf-8") for f in files).lower()

    def test_every_table_in_the_exposed_schema_has_rls_on(self):
        tables = re.findall(r"create table (public\.\w+)", self.sql)
        self.assertTrue(tables)
        for table in tables:
            with self.subTest(table=table):
                self.assertIn("alter table {} enable row level security".format(table), self.sql)

    def test_every_function_pins_search_path_and_is_closed_to_clients(self):
        found = list(re.finditer(r"create (?:or replace )?function (public\.\w+)\((.*?)\)(.*?)(?:\$\$|as \$)", self.sql, re.S))
        self.assertGreaterEqual(len(found), 4)
        for match in found:
            name, _args, head = match.groups()
            with self.subTest(function=name):
                self.assertIn("set search_path = ''", head)
                self.assertRegex(self.sql, r"revoke all on function {}\(.*?\) from public, anon, authenticated".format(re.escape(name)))

    def test_views_are_security_invoker(self):
        for match in re.finditer(r"create (?:or replace )?view\b(.*?);", self.sql, re.S):
            self.assertIn("security_invoker", match.group(1))

    def test_profiles_are_updatable_through_display_name_alone(self):
        self.assertIn("grant update (display_name) on public.profiles to authenticated", self.sql)
        self.assertNotRegex(self.sql, r"grant (?:all|update|insert|delete)\s+on public\.profiles")

    def test_the_server_only_tables_have_no_client_grant(self):
        for table in ("app_config", "banned_identities", "trial_consumed"):
            with self.subTest(table=table):
                self.assertNotRegex(self.sql, r"grant [^;]*on public\.{} to (?:anon|authenticated)".format(table))
        self.assertIn("revoke all on public.profiles, public.licenses, public.app_config", self.sql)

    def test_licenses_have_no_client_write_grant(self):
        self.assertNotRegex(self.sql, r"grant (?:insert|update|delete|all)[^;]*on public\.licenses")

    def test_clients_cannot_read_the_moderation_columns_of_their_license(self):
        grant = re.search(r"grant select \(([^)]*)\)\s+on public\.licenses to authenticated", self.sql)
        self.assertIsNotNone(grant, "licenses must be granted column by column")
        columns = {c.strip() for c in grant.group(1).split(",")}
        self.assertNotIn("ban_reason", columns)
        self.assertNotIn("banned_at", columns)
        self.assertNotIn("grant select on public.licenses to authenticated", self.sql)


if __name__ == "__main__":
    unittest.main()
