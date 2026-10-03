"""Featured commands and progressive reveal (ADR-0030 section 5).

Covers the metadata in `scripts/lib/commands.json`, what the render engine does with it on
every provider, the machine-local usage record, the reveal ordering, the hook that records use,
the session-start banner and the `devteam catalog` surface.
"""

import io
import json
import os
import re
import subprocess
import sys
import unittest
from pathlib import Path

from devteam_support import CLI, REPO_ROOT, StoreTestCase, requires_bash

sys.path.insert(0, str(REPO_ROOT / "scripts" / "lib"))

import render_provider  # noqa: E402

from devteam import command_usage, paths, providers  # noqa: E402

LIB = REPO_ROOT / "scripts" / "lib"
ADR = next((REPO_ROOT / "docs" / "development" / "adrs").glob("0030-*.md"))
HOOK = REPO_ROOT / "scripts" / "hooks" / "user-prompt-submit" / "03-command-usage.sh"
SESSION_START = REPO_ROOT / "scripts" / "hooks" / "session-start.sh"

FEATURED = ["plan", "fix", "review", "commit", "pr"]

#: One entry per provider in ALL_PROVIDERS: how a featured command is spelled to the user.
EXPOSED = {
    "claude": "/devteam:plan",
    "opencode": "/devteam:plan",
    "codex": "$devteam-plan",
}

#: What the render engine writes for a featured command, per provider. `None` means the provider's
#: command format has nowhere to carry the flag, so nothing is invented (see featured_marker).
RENDERED_MARKER = {
    "claude": None,
    "opencode": None,
    "codex": "<!-- codex-featured: true -->",
}

#: The prompt a user types to run `plan` on each provider.
PROMPTS = {
    "claude": "/devteam:plan add a login page",
    "opencode": "/devteam:plan add a login page",
    "codex": "$devteam-plan add a login page",
}


class ProviderFixturesTest(unittest.TestCase):
    def test_every_provider_has_a_case_in_every_fixture_map(self):
        for name, fixture in (("EXPOSED", EXPOSED), ("RENDERED_MARKER", RENDERED_MARKER), ("PROMPTS", PROMPTS)):
            with self.subTest(fixture=name):
                self.assertEqual(set(fixture), set(providers.ALL_PROVIDERS))
        self.assertEqual(set(command_usage._INSTALLED_MARKERS), set(providers.ALL_PROVIDERS))


class CommandMetadataTest(unittest.TestCase):
    def setUp(self):
        self.commands = command_usage.load_commands(LIB)
        self.on_disk = {p.stem for p in (REPO_ROOT / "commands").glob("*.md")}

    def test_exactly_five_commands_are_featured_and_they_are_the_ones_in_the_adr(self):
        self.assertEqual(sorted(command_usage.featured(self.commands)), sorted(FEATURED))
        section = ADR.read_text(encoding="utf-8").split("### 5.", 1)[1].split("### 6.", 1)[0]
        named = re.findall(r"`(\w+)`", section.split("carry", 1)[0])
        self.assertEqual(sorted(named), sorted(FEATURED))

    def test_the_flag_is_true_or_absent_never_false(self):
        for name, meta in self.commands.items():
            with self.subTest(command=name):
                self.assertIn(meta.get("featured", True), (True,))

    def test_every_command_on_disk_has_metadata_and_a_related_list(self):
        self.assertEqual(set(self.commands), self.on_disk)
        for name, meta in self.commands.items():
            with self.subTest(command=name):
                self.assertIsInstance(meta.get("related"), list)

    def test_every_related_target_exists_and_is_not_the_command_itself(self):
        for name in self.commands:
            for target in command_usage.related(self.commands, name):
                with self.subTest(command=name, target=target):
                    self.assertIn(target, self.on_disk)
                    self.assertNotEqual(target, name)

    def test_the_adr_examples_hold(self):
        self.assertEqual(command_usage.related(self.commands, "commit"), ["push", "merge"])


class RenderTest(unittest.TestCase):
    def setUp(self):
        self.lib = render_provider.load_lib(LIB)
        self.meta = self.lib["commands"]["commands"]

    def render(self, provider, name):
        meta = self.meta[name]
        path = REPO_ROOT / "commands" / (name + ".md")
        _fm, body = render_provider.parse_frontmatter(path.read_text(encoding="utf-8"))
        tier = meta["tier"]
        model = render_provider.resolve_model(self.lib["tiers"], provider, tier)
        effort = render_provider.resolve_effort(self.lib["tiers"], provider, tier, meta.get("agent"))
        if provider == "claude":
            return render_provider.render_command_claude(name, body, path)["content"]
        if provider == "opencode":
            return render_provider.render_command_opencode(name, meta, body, model, effort, self.lib["tool_map"])
        return render_provider.render_command_codex(name, meta, body, model, effort, self.lib["tool_map"])["content"]

    def test_the_marker_per_provider(self):
        for provider in providers.ALL_PROVIDERS:
            with self.subTest(provider=provider):
                expected = RENDERED_MARKER[provider]
                self.assertEqual(render_provider.featured_marker(self.meta["plan"], provider).strip() or None, expected)
                self.assertEqual(render_provider.featured_marker(self.meta["status"], provider), "")

    def test_rendered_output_carries_the_flag_only_where_the_format_can_and_never_edits_descriptions(self):
        for provider in providers.ALL_PROVIDERS:
            for name in ("plan", "status"):
                with self.subTest(provider=provider, command=name):
                    out = self.render(provider, name)
                    text = json.dumps(out) if isinstance(out, dict) else out
                    marker = RENDERED_MARKER[provider]
                    if marker and name == "plan":
                        self.assertIn(marker, text)
                    elif marker:
                        self.assertNotIn("codex-featured", text)
                    self.assertNotIn("featured", json.dumps(out["snippet_entry"]) if provider == "opencode" else "")
                    if provider == "opencode":
                        self.assertEqual(out["snippet_entry"]["description"], self.meta[name]["description"])
                    if provider == "codex":
                        self.assertIn('description: "{}"'.format(self.meta[name]["description"]), out)

    def test_the_exposed_name_follows_the_providers_syntax(self):
        for provider in providers.ALL_PROVIDERS:
            with self.subTest(provider=provider):
                self.assertEqual(command_usage.exposed_name(provider, "plan"), EXPOSED[provider])


class UsageRecordTest(StoreTestCase):
    def setUp(self):
        super().setUp()
        self.state = self.tmp / "state"
        self.commands = command_usage.load_commands(LIB)

    def test_record_counts_and_stamps_atomically(self):
        self.assertTrue(command_usage.record(self.state, "commit", now="2026-10-02T10:00:00Z"))
        self.assertTrue(command_usage.record(self.state, "commit", now="2026-10-02T11:00:00Z"))
        self.assertTrue(command_usage.record(self.state, "plan", now="2026-10-02T12:00:00Z"))
        data = json.loads((self.state / "command-usage.json").read_text(encoding="utf-8"))
        self.assertEqual(
            data,
            {
                "commit": {"count": 2, "last_used": "2026-10-02T11:00:00Z"},
                "plan": {"count": 1, "last_used": "2026-10-02T12:00:00Z"},
            },
        )
        self.assertEqual(command_usage.read_usage(self.state)["commit"]["count"], 2)
        self.assertEqual([p.name for p in self.state.iterdir() if p.name.endswith(".tmp")], [])

    def test_a_malformed_record_is_left_alone_and_reads_as_empty(self):
        self.state.mkdir()
        target = self.state / "command-usage.json"
        target.write_text("{not json", encoding="utf-8")
        self.assertFalse(command_usage.record(self.state, "plan"))
        self.assertEqual(target.read_text(encoding="utf-8"), "{not json")
        self.assertEqual(command_usage.read_usage(self.state), {})

    def test_the_record_is_classified_machine_local(self):
        self.assertTrue(paths.is_machine_local_record("command-usage.json"))
        self.assertTrue(paths.path_is_machine_local("projects/x/command-usage.json"))

    def test_command_in_prompt_per_provider_and_only_real_commands(self):
        for provider, prompt in PROMPTS.items():
            with self.subTest(provider=provider):
                self.assertEqual(command_usage.command_in_prompt(prompt, self.commands), "plan")
        for text in ("please /devteam:plan", "/devteam:nope", "$devteam-nope x", "plan", "", None, "/review"):
            with self.subTest(prompt=text):
                self.assertIsNone(command_usage.command_in_prompt(text, self.commands))

    def test_hook_main_records_from_a_payload_and_swallows_garbage(self):
        payload = json.dumps({"session_id": "s", "prompt": "/devteam:fix the bug"})
        command_usage.hook_main(self.state, io.StringIO(payload))
        command_usage.hook_main(self.state, io.StringIO("not json"))
        self.assertEqual(list(command_usage.read_usage(self.state)), ["fix"])


class RevealTest(unittest.TestCase):
    def setUp(self):
        self.commands = command_usage.load_commands(LIB)

    @staticmethod
    def used(**counts):
        return {name: {"count": n, "last_used": "2026-10-02T00:00:00Z"} for name, n in counts.items()}

    def test_nothing_used_reveals_nothing(self):
        self.assertEqual(command_usage.revealed(self.commands, {}), [])

    def test_related_minus_featured_minus_used(self):
        # commit -> push, merge; plan -> backend, frontend, fullstack, architect (featured ones never repeat)
        self.assertEqual(command_usage.revealed(self.commands, self.used(commit=1)), ["push", "merge"])
        self.assertEqual(command_usage.revealed(self.commands, self.used(commit=1, push=1)), ["merge"])

    def test_ordered_by_the_usage_count_of_the_source_and_capped_at_three(self):
        usage = self.used(commit=1, plan=5)
        self.assertEqual(command_usage.revealed(self.commands, usage), ["backend", "frontend", "fullstack"])
        self.assertEqual(command_usage.revealed(self.commands, usage, limit=10)[:4], ["backend", "frontend", "fullstack", "architect"])
        self.assertEqual(len(command_usage.revealed(self.commands, usage)), command_usage.ALSO_TRY_LIMIT)

    def test_a_target_related_to_two_sources_takes_the_larger_count(self):
        usage = self.used(commit=1, review=4)  # review -> security, refactor; commit -> push, merge
        self.assertEqual(command_usage.revealed(self.commands, usage), ["security", "refactor", "push"])


@requires_bash()
class HookAndBannerTest(StoreTestCase):
    def setUp(self):
        super().setUp()
        self.root = self.new_project("proj")
        self.state = self.root / ".dev-team-agents" / "user-data"
        self.state.mkdir(parents=True)

    def run_hook(self, payload):
        return subprocess.run(
            ["bash", str(HOOK)], cwd=str(self.root), input=payload, capture_output=True, text=True, timeout=60
        )

    def test_the_hook_records_a_command_on_every_provider_and_stays_silent(self):
        for provider in providers.ALL_PROVIDERS:
            with self.subTest(provider=provider):
                payload = json.dumps({"cwd": str(self.root), "session_id": "s-" + provider, "prompt": PROMPTS[provider]})
                result = self.run_hook(payload)
                self.assertEqual((result.returncode, result.stdout, result.stderr), (0, "", ""))
        self.assertEqual(command_usage.read_usage(self.state)["plan"]["count"], len(providers.ALL_PROVIDERS))

    def test_a_prompt_that_is_not_a_command_records_nothing_and_a_path_does_not_fool_the_gate(self):
        for text in ("explain devteam to me", "run /devteam:plan later"):
            self.run_hook(json.dumps({"cwd": "/x/devteam/y", "session_id": "s", "prompt": text}))
        self.assertFalse((self.state / "command-usage.json").exists())

    def banner(self, **env):
        base = {k: v for k, v in os.environ.items() if k not in ("CLAUDECODE", "CLAUDE_PROJECT_DIR", "DEVTEAM_PROVIDER")}
        result = subprocess.run(
            ["bash", str(SESSION_START)], cwd=str(self.root), capture_output=True, text=True,
            env=dict(base, **env), timeout=120,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        block = result.stdout.split("[DEVTEAM:SESSION_BANNER]", 1)[1].split("\n\n", 1)[0]
        return block.splitlines()

    def test_the_banner_lists_only_the_five_featured_commands_in_the_providers_syntax(self):
        for provider in providers.ALL_PROVIDERS:
            with self.subTest(provider=provider):
                lines = self.banner(DEVTEAM_PROVIDER=provider)
                (start,) = [line for line in lines if line.startswith("Start with:")]
                expected = "Start with: " + " ".join(command_usage.exposed_name(provider, n) for n in command_usage.featured(command_usage.load_commands(LIB)))
                self.assertEqual(start, expected)
                self.assertFalse([line for line in lines if line.startswith("Also try:")])

    def test_the_banner_reveals_related_commands_after_use(self):
        command_usage.record(self.state, "commit")
        lines = self.banner(CLAUDECODE="1")
        self.assertIn("Also try: /devteam:push /devteam:merge", lines)

    def test_provider_detection_prefers_the_env_then_the_installed_provider(self):
        (self.root / ".codex").mkdir()
        (self.root / ".codex" / "hooks.json").write_text("{}", encoding="utf-8")
        (self.root / ".claude" / "commands" / "devteam").mkdir(parents=True)
        self.assertEqual(command_usage.detect_provider(self.root, {"CLAUDECODE": "1"}), "claude")
        self.assertEqual(command_usage.detect_provider(self.root, {"DEVTEAM_PROVIDER": "opencode"}), "opencode")
        self.assertEqual(command_usage.detect_provider(self.root, {}), "codex")


class CatalogSurfaceTest(StoreTestCase):
    def setUp(self):
        super().setUp()
        (self.source / "commands" / "plan.md").write_text("---\ndescription: plan it\n---\nBody\n", encoding="utf-8")
        (self.source / "commands" / "status.md").write_text("---\ndescription: status\n---\nBody\n", encoding="utf-8")
        (self.source / "scripts" / "lib" / "commands.json").write_text(
            json.dumps({"commands": {
                "plan": {"featured": True, "related": ["status"]},
                "status": {"related": []},
            }}),
            encoding="utf-8",
        )
        for args in (("store", "install", "--from", str(self.source), "--version", "3.0.0", "--json"), ("store", "use", "3.0.0", "--json")):
            code, _out, err = self.run_cli(*args)
            self.assertEqual(code, 0, err)
        self.cwd = self.tmp / "cwd"
        self.cwd.mkdir()

    def commands(self, *flags):
        result = subprocess.run(
            [sys.executable, str(CLI), "catalog", "commands", "--json", *flags],
            cwd=str(self.cwd), stdin=subprocess.DEVNULL, capture_output=True, text=True, env=dict(os.environ),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def entries(self, payload):
        data = payload.get("data", payload)
        return {entry["name"]: entry for entry in data["commands"]}

    def test_every_entry_carries_featured_and_related_additively(self):
        entries = self.entries(self.commands())
        self.assertEqual(entries["plan"]["featured"], True)
        self.assertEqual(entries["plan"]["related"], ["status"])
        self.assertEqual(entries["status"]["featured"], False)
        self.assertEqual(entries["status"]["related"], [])
        for key in ("name", "description", "path", "version"):
            self.assertIn(key, entries["plan"])

    def test_the_featured_flag_filters(self):
        payload = self.commands("--featured")
        data = payload.get("data", payload)
        self.assertEqual([entry["name"] for entry in data["commands"]], ["plan"])
        self.assertEqual(data["count"], 1)

    def test_a_version_without_commands_json_answers_not_featured(self):
        (self.source / "scripts" / "lib" / "commands.json").unlink()
        code, _out, err = self.run_cli("store", "install", "--from", str(self.source), "--version", "3.0.1", "--json")
        self.assertEqual(code, 0, err)
        code, _out, err = self.run_cli("store", "use", "3.0.1", "--json")
        self.assertEqual(code, 0, err)
        entries = self.entries(self.commands())
        self.assertEqual((entries["plan"]["featured"], entries["plan"]["related"]), (False, []))


if __name__ == "__main__":
    unittest.main()
