"""ADR-0032: a write through `devteam integration call` asks the user, on every provider.

Two layers. The unit tests pin the rule text and the merge semantics in
``devteam.permissions``: only our entries are added or removed, a user's own rules stay,
opencode's keep ours last, a shape we cannot merge into is refused. The bind tests run the
real installers, like ``test_provider_ownership``, because the guarantee for opencode and
Codex lives in the bash installers, and a stubbed one would prove only the stub.

Every per-provider map below is keyed by ``providers.ALL_PROVIDERS``; the parity test fails
the moment a provider is added without its own case.
"""

import fnmatch
import json
import os
import shlex
import shutil
import subprocess
import unittest

from devteam_support import REPO_ROOT, StoreTestCase, requires_bash

from devteam import bind, doctor, hooks, integrations, permissions, providers, versions
from devteam.errors import EnvError

RULES_SCRIPT = REPO_ROOT / "scripts" / "lib" / "permission_rules.py"

WRITES = [
    "devteam integration call cloudflare POST /zones/{zone_id}/purge_cache --data-file - --allow-write --json",
    "devteam integration call cloudflare DELETE /zones/abc/dns_records/def --allow-write",
    "devteam integration call cloudflare PATCH /zones/abc/settings/ssl --data '{\"value\":\"full\"}' --allow-write",
    "devteam integration call cloudflare PUT /x --allow-write",
]
READS = [
    "devteam integration call cloudflare GET /zones --json",
    "devteam integration call cloudflare GET /zones/{zone_id}/dns_records --query type=A",
    "devteam integration list --json",
]


def glob_matches(pattern, command):
    """Claude and opencode `*` matches any run of characters, spaces included."""
    return fnmatch.fnmatchcase(command, pattern)


def codex_prefix_matches(command, names):
    """The Codex rule we render: these exact leading tokens, the method as the fourth word."""
    tokens = shlex.split(command)
    return (
        tokens[:3] == ["devteam", "integration", "call"]
        and len(tokens) > 4
        and tokens[3] in names
        and tokens[4] in permissions.WRITE_METHODS
    )


#: Where each provider's rules land in a bound project, and how a test reads them back.
RULE_FILES = {
    "claude": hooks.SETTINGS_FILE.as_posix(),
    "opencode": ".opencode/opencode.json",
    "codex": permissions.CODEX_RULES_FILE,
}
TOOLS = {"claude": (), "opencode": ("bash", "python3", "jq"), "codex": ("bash", "python3")}


def rules_in(provider, root):
    """True when the provider's ask rules are all present in the bound project."""
    path = root / RULE_FILES[provider]
    if not path.is_file():
        return False
    if provider == "codex":
        return permissions.codex_rules_current(root, integrations.callable_names())
    data = json.loads(path.read_text(encoding="utf-8"))
    if provider == "claude":
        return not permissions.claude_rules_present(data)
    return not permissions.opencode_findings(data)


#: A rule the user wrote themselves, in each provider's own file, that must survive.
USER_RULE = {
    "claude": ("{\"permissions\": {\"ask\": [\"Bash(rm *)\"], \"allow\": [\"Bash(devteam *)\"]}}\n",
               lambda d: d["permissions"]["ask"] == ["Bash(rm *)"] and d["permissions"]["allow"] == ["Bash(devteam *)"]),
    "opencode": ("{\"permission\": {\"bash\": {\"devteam *\": \"allow\"}}}\n",
                 lambda d: d["permission"]["bash"] == {"devteam *": "allow"}),
    "codex": None,  # the rules file is wholly ours; Codex reads the user's from other files
}


class RuleTextTest(unittest.TestCase):
    def test_the_methods_are_the_clis_write_methods(self):
        self.assertEqual(permissions.WRITE_METHODS, integrations.WRITE_METHODS)

    def test_glob_rules_match_every_write_and_no_read(self):
        for command in WRITES:
            with self.subTest(command=command):
                self.assertTrue(any(glob_matches(p, command) for p in permissions.command_patterns()))
        for command in READS:
            with self.subTest(command=command):
                self.assertFalse(any(glob_matches(p, command) for p in permissions.command_patterns()))

    def test_claude_rules_wrap_the_same_patterns(self):
        self.assertEqual(
            list(permissions.CLAUDE_ASK_RULES), ["Bash({})".format(p) for p in permissions.command_patterns()]
        )

    def test_codex_prefix_matches_every_canonical_write_and_no_read(self):
        names = integrations.callable_names()
        for command in WRITES:
            self.assertTrue(codex_prefix_matches(command, names), command)
        for command in READS:
            self.assertFalse(codex_prefix_matches(command, names), command)

    def test_codex_rules_name_every_callable_integration_and_carry_examples(self):
        text = permissions.codex_rules(["cloudflare", "zeta"])
        self.assertTrue(text.startswith(permissions.CODEX_RULES_MARKER))
        self.assertEqual(text.count("prefix_rule("), 2)
        self.assertIn('decision = "prompt"', text)
        for method in permissions.WRITE_METHODS:
            self.assertIn("devteam integration call zeta {} /example --allow-write".format(method), text)
        self.assertIn('not_match = ["devteam integration call zeta GET /example"]', text)

    @unittest.skipUnless(shutil.which("codex"), "codex is not installed")
    def test_codex_itself_reads_the_rule_as_a_prompt(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            rules = os.path.join(tmp, "devteam.rules")
            with open(rules, "w", encoding="utf-8") as handle:
                handle.write(permissions.codex_rules(integrations.callable_names()))
            result = subprocess.run(
                ["codex", "execpolicy", "check", "--rules", rules, "--",
                 "devteam", "integration", "call", "cloudflare", "POST", "/zones", "--allow-write"],
                capture_output=True, text=True,
            )
            if result.returncode != 0 and "ENOENT" in result.stderr:
                self.skipTest("the codex launcher is installed but its binary is not")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("prompt", result.stdout)


class ClaudeMergeTest(unittest.TestCase):
    def test_merge_is_idempotent_and_keeps_the_users_rules(self):
        data = {"permissions": {"ask": ["Bash(rm *)"], "allow": ["Bash(devteam *)"]}}
        self.assertTrue(permissions.merge_claude(data))
        self.assertFalse(permissions.merge_claude(data))
        self.assertEqual(data["permissions"]["ask"][0], "Bash(rm *)")
        self.assertEqual(data["permissions"]["allow"], ["Bash(devteam *)"])
        self.assertEqual(permissions.claude_rules_present(data), [])

    def test_unmerge_removes_only_ours_and_drops_what_it_emptied(self):
        data = {}
        permissions.merge_claude(data)
        self.assertEqual(permissions.unmerge_claude(data), len(permissions.CLAUDE_ASK_RULES))
        self.assertEqual(data, {})
        data = {"permissions": {"ask": ["Bash(rm *)"]}}
        permissions.merge_claude(data)
        permissions.unmerge_claude(data)
        self.assertEqual(data, {"permissions": {"ask": ["Bash(rm *)"]}})

    def test_shapes_it_cannot_merge_into_are_refused(self):
        for data in ({"permissions": []}, {"permissions": {"ask": "Bash(x)"}}):
            with self.subTest(data=data), self.assertRaises(EnvError):
                permissions.merge_claude(data)


class OpencodeMergeTest(unittest.TestCase):
    def test_ours_are_appended_last_after_a_broader_allow(self):
        data = {"permission": {"bash": {"devteam *": "allow"}}}
        self.assertTrue(permissions.merge_opencode(data))
        keys = list(data["permission"]["bash"])
        self.assertEqual(keys[0], "devteam *")
        self.assertEqual(keys[1:], list(permissions.OPENCODE_ASK_RULES))
        self.assertFalse(permissions.merge_opencode(data))
        self.assertEqual(permissions.opencode_findings(data), [])

    def test_a_rule_added_after_ours_is_reported_and_the_next_merge_moves_ours_last(self):
        data = {}
        permissions.merge_opencode(data)
        data["permission"]["bash"]["devteam *"] = "allow"
        self.assertIn("listed after ours", permissions.opencode_findings(data)[0])
        self.assertTrue(permissions.merge_opencode(data))
        self.assertEqual(list(data["permission"]["bash"])[-1], permissions.OPENCODE_ASK_RULES[-1])

    def test_a_string_action_becomes_its_object_form(self):
        data = {"permission": {"bash": "allow"}}
        permissions.merge_opencode(data)
        self.assertEqual(data["permission"]["bash"]["*"], "allow")

    def test_an_agent_level_bash_permission_is_reported(self):
        data = {"agent": {"build": {"permission": {"bash": {"*": "allow"}}}}}
        permissions.merge_opencode(data)
        self.assertTrue(any("build" in p for p in permissions.opencode_findings(data)))

    def test_unmerge_removes_only_ours(self):
        data = {"permission": {"bash": {"devteam *": "allow"}, "edit": "ask"}}
        permissions.merge_opencode(data)
        self.assertEqual(permissions.unmerge_opencode(data), len(permissions.OPENCODE_ASK_RULES))
        self.assertEqual(data, {"permission": {"bash": {"devteam *": "allow"}, "edit": "ask"}})


class CodexTrustTest(unittest.TestCase):
    def test_trust_is_read_from_the_codex_config(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            home, project = Path(tmp) / "home", Path(tmp) / "proj"
            project.mkdir()
            self.assertIsNone(permissions.codex_project_trusted(project, home=home))
            (home / ".codex").mkdir(parents=True)
            config = home / ".codex" / "config.toml"
            config.write_text('[projects."/elsewhere"]\ntrust_level = "trusted"\n', encoding="utf-8")
            self.assertFalse(permissions.codex_project_trusted(project, home=home))
            config.write_text(
                'model = "x"\n[projects."{}"]\ntrust_level = "trusted"\n[other]\n'.format(project.resolve()),
                encoding="utf-8",
            )
            self.assertTrue(permissions.codex_project_trusted(project, home=home))


class RulesScriptTest(unittest.TestCase):
    """The entry point the installers call."""

    def run_script(self, *args):
        return subprocess.run(["python3", str(RULES_SCRIPT), *args], capture_output=True, text=True)

    def test_a_file_that_is_not_strict_json_is_refused_with_4_and_left_untouched(self):
        import tempfile

        for provider in ("claude", "opencode"):
            with self.subTest(provider=provider), tempfile.TemporaryDirectory() as tmp:
                path = os.path.join(tmp, "cfg.json")
                original = '{\n  // a comment\n  "a": 1,\n}\n'
                with open(path, "w", encoding="utf-8") as handle:
                    handle.write(original)
                result = self.run_script(provider, path)
                self.assertEqual(result.returncode, 4, result.stderr)
                with open(path, encoding="utf-8") as handle:
                    self.assertEqual(handle.read(), original)


def _missing_tools(provider):
    return [tool for tool in TOOLS[provider] if shutil.which(tool) is None]


@requires_bash()
class ProviderAskRulesTest(StoreTestCase):
    """The real bind, per provider: rules written, user rules kept, unbind removes only ours."""

    def setUp(self):
        super().setUp()
        versions.install_from_tree(REPO_ROOT, version="9.9.9", force=True, make_current=True)
        self._home = os.environ.get("HOME")
        self.fake_home = self.tmp / "fake-home"
        self.fake_home.mkdir()
        os.environ["HOME"] = str(self.fake_home)
        self.addCleanup(self._restore_home)

    def _restore_home(self):
        if self._home is None:
            os.environ.pop("HOME", None)
        else:
            os.environ["HOME"] = self._home

    def _providers(self):
        for provider in providers.ALL_PROVIDERS:
            missing = _missing_tools(provider)
            if missing:
                self.skipTest("{} needs {}".format(provider, ", ".join(missing)))
            yield provider

    def test_every_provider_has_a_case(self):
        for table in (RULE_FILES, TOOLS, USER_RULE):
            self.assertEqual(set(table), set(providers.ALL_PROVIDERS))

    def test_bind_writes_the_rules_sync_is_idempotent_and_unbind_removes_only_ours(self):
        for provider in self._providers():
            with self.subTest(provider=provider):
                root = self.new_project("ask-{}".format(provider))
                rule_file = root / RULE_FILES[provider]
                user = USER_RULE[provider]
                if user is not None:
                    rule_file.parent.mkdir(parents=True, exist_ok=True)
                    rule_file.write_text(user[0], encoding="utf-8")

                result = bind.bind(root, provider_names=[provider])
                self.assertTrue(rules_in(provider, root), provider)
                first = rule_file.read_text(encoding="utf-8")

                bind.bind(root, provider_names=[provider])
                self.assertEqual(rule_file.read_text(encoding="utf-8"), first, "a second bind changed the rules")

                bind.unbind(root)
                if user is None:
                    self.assertFalse(rule_file.exists(), "unbind left {}".format(rule_file))
                else:
                    data = json.loads(rule_file.read_text(encoding="utf-8"))
                    self.assertTrue(user[1](data), "unbind did not leave exactly the user's rules: {}".format(data))
                self.assertTrue(result["project_id"])

    def test_doctor_reports_missing_rules(self):
        for provider in self._providers():
            with self.subTest(provider=provider):
                root = self.new_project("doc-{}".format(provider))
                bind.bind(root, provider_names=[provider])
                rule_file = root / RULE_FILES[provider]
                if provider == "codex":
                    rule_file.unlink()
                else:
                    data = json.loads(rule_file.read_text(encoding="utf-8"))
                    if provider == "claude":
                        permissions.unmerge_claude(data)
                    else:
                        permissions.unmerge_opencode(data)
                    rule_file.write_text(json.dumps(data), encoding="utf-8")
                findings, _actions = doctor.check_project(root)
                warned = [f for f in findings if f["category"] == "permissions" and f["level"] == "warn"]
                self.assertTrue(warned, "doctor said nothing for {}".format(provider))


if __name__ == "__main__":
    unittest.main()
