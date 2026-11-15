"""`03c-modern-web-guidance-guard.sh` refuses the modern-web-guidance CLI, for every provider (ADR-0047).

The skill is vendored as Markdown only; its upstream SKILL.md tells the agent to fetch and run
an unpinned package. The guard refuses that run and nothing else: a mention of the command in
a quoted argument on one line, or a read of the vendored guides, is not a run.
"""

from __future__ import annotations

import json
import subprocess
import time
import unittest

from devteam_support import REPO_ROOT, requires_bash
from devteam.providers import ALL_PROVIDERS

GUARD = REPO_ROOT / "scripts" / "hooks" / "pre-tool-use" / "03c-modern-web-guidance-guard.sh"


def _payload(shape, command):
    """The shell call as each provider's hook (or, for opencode, its plugin) spells it."""
    return {
        "claude": {"session_id": "s1", "tool_name": "Bash", "tool_input": {"command": command, "description": "x"}},
        "codex": {"session_id": "s1", "tool_name": "Bash", "tool_input": {"command": command}},
        "codex-exec": {"session_id": "s1", "tool_name": "exec_command",
                       "tool_input": {"cmd": ["bash", "-lc", command]}},
        "opencode": {"sessionID": "s1", "tool": "bash", "args": {"command": command}},
    }[shape]


#: Payload spellings per provider; a provider added to ALL_PROVIDERS without one fails below.
PROVIDER_PAYLOADS = {"claude": ["claude"], "codex": ["codex", "codex-exec"], "opencode": ["opencode"]}
SHAPES = sorted(shape for shapes in PROVIDER_PAYLOADS.values() for shape in shapes)

REFUSED = (
    'npx -y modern-web-guidance@latest search "light dismiss dialog" --skill-version 2026_11_09-5bcc021b',
    "npx modern-web-guidance retrieve dialog",
    "pnpx modern-web-guidance@latest list",
    "bunx modern-web-guidance@1.0.0 search tabs",
    "pnpm dlx modern-web-guidance@latest retrieve dialog",
    "yarn dlx modern-web-guidance legacy-scan .",
    "npm exec -- modern-web-guidance search tabs",
    "NPM_CONFIG_CACHE=/tmp/npm-cache npx -y modern-web-guidance@latest install",
    "cd app && npx --offline modern-web-guidance@latest retrieve dialog",
    "npm install -g modern-web-guidance",
    "pnpm add -D modern-web-guidance@latest",
    "modern-web-guidance legacy-scan src --json",
    "npx.cmd -y modern-web-guidance@latest search tabs",
    "npm x modern-web-guidance list",
    "npx --cache /tmp/npm -y modern-web-guidance@latest search tabs",
    "timeout 60 npx -y modern-web-guidance@latest retrieve dialog",
    'npx -y "modern-web-guidance@latest" search tabs',
    "/usr/local/bin/npx -y modern-web-guidance@latest list",
    "sudo -E npx -y modern-web-guidance list",
    "env -i PATH=/usr/bin npx modern-web-guidance list",
    "npx -y npm:modern-web-guidance list",
    "npx -y github:GoogleChrome/modern-web-guidance list",
    "npx --package=modern-web-guidance modern-web search tabs",
    'sh -c "npx -y modern-web-guidance@latest list"',
    "echo $(npx -y modern-web-guidance@latest list)",
    "echo `npx modern-web-guidance list`",
    "if true; then npx modern-web-guidance list; fi",
    "{ npx modern-web-guidance list; }",
    "pnpm --filter web add modern-web-guidance",
    "yarn global add modern-web-guidance",
)

#: Refused although nothing runs: the text is not parsed as shell, so a mention after a
#: newline or a separator inside quotes or a heredoc reads as command position. Documented
#: in the guard's header; the refusal message says how to write such text instead.
REFUSED_MENTIONS = (
    'git commit -m "docs: guard\n\nnpx -y modern-web-guidance@latest search is refused"',
    'echo "a; npx -y modern-web-guidance search x"',
    "cat > notes.md <<EOF\nnpx -y modern-web-guidance@latest list\nEOF",
)

ALLOWED = (
    "npm view modern-web-guidance version",
    "git clone https://github.com/GoogleChrome/modern-web-guidance",
    'grep -rn "npx -y modern-web-guidance@latest" skills/third-party',
    "ls .claude/skills/modern-web-guidance/guides/forms",
    "cat skills/third-party/modern-web-guidance/guides/ui-components/dialog.md",
    "python3 helpers/third-party-skills.py sync modern-web-guidance",
    "npx -y some-other-tool modern-web-guidance-notes.md",
    "npm install modern-web-guidance-polyfill",
    "npx vitest run",
    'git commit -m "docs: say that npx -y modern-web-guidance@latest is refused"',
    "echo modern-web-guidance search is the upstream command",
    "npx prettier --check modern-web-guidance",
    "cd skills/third-party && npx markdownlint-cli2 modern-web-guidance",
)


@requires_bash()
class ModernWebGuidanceGuardTest(unittest.TestCase):
    def run_guard(self, payload):
        return subprocess.run(["bash", str(GUARD)], input=json.dumps(payload), capture_output=True, text=True)

    def test_every_provider_has_a_payload(self):
        self.assertEqual(set(PROVIDER_PAYLOADS), set(ALL_PROVIDERS))

    def test_running_or_installing_the_tool_is_refused_for_every_provider(self):
        for shape in SHAPES:
            for command in REFUSED:
                with self.subTest(shape=shape, command=command):
                    result = self.run_guard(_payload(shape, command))
                    self.assertEqual(result.returncode, 2, result.stderr)
                    self.assertIn("third-party-web-skills", result.stderr)

    def test_a_codex_argv_array_naming_the_runner_directly_is_refused(self):
        payload = {"session_id": "s1", "tool_name": "exec_command",
                   "tool_input": {"cmd": ["npx", "-y", "modern-web-guidance@latest", "search", "tabs"]}}
        self.assertEqual(self.run_guard(payload).returncode, 2)

    def test_a_mention_at_command_position_inside_quoted_text_is_refused(self):
        for command in REFUSED_MENTIONS:
            with self.subTest(command=command):
                result = self.run_guard(_payload("claude", command))
                self.assertEqual(result.returncode, 2)
                self.assertIn("git commit -F", result.stderr)

    def test_a_large_command_naming_the_package_is_answered_quickly(self):
        # Undoing JSON escapes with bash `${VAR//…}` took 27 s on a 40 KB heredoc (bash 3.2).
        body = "\n".join("line {} mentions modern-web-guidance in passing".format(i) for i in range(4500))
        command = "cat > notes.md <<'EOF'\n{}\nEOF".format(body)
        self.assertGreater(len(command), 200_000)
        started = time.monotonic()
        result = self.run_guard(_payload("claude", command))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertLess(time.monotonic() - started, 5)

    def test_an_invalid_utf8_byte_does_not_let_the_command_through(self):
        payload = json.dumps(_payload("claude", "echo MARK; npx -y modern-web-guidance@latest list")).encode()
        result = subprocess.run(["bash", str(GUARD)], input=payload.replace(b"MARK", b"\xff"), capture_output=True)
        self.assertEqual(result.returncode, 2)

    def test_a_shell_command_that_does_not_name_the_package_passes(self):
        for shape in SHAPES:
            with self.subTest(shape=shape):
                self.assertEqual(self.run_guard(_payload(shape, "npx -y cowsay hello")).returncode, 0)

    def test_mentions_and_reads_pass_for_every_provider(self):
        for shape in SHAPES:
            for command in ALLOWED:
                with self.subTest(shape=shape, command=command):
                    result = self.run_guard(_payload(shape, command))
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(result.stderr, "")

    def test_a_non_shell_tool_naming_the_package_passes(self):
        payloads = (
            {"tool_name": "Read", "tool_input": {"file_path": "skills/third-party/modern-web-guidance/SKILL.md"}},
            {"tool_name": "Write", "tool_input": {"file_path": "notes.md",
                                                   "content": "npx -y modern-web-guidance@latest search x"}},
            {"tool": "edit", "args": {"filePath": "a.md", "newString": "npx modern-web-guidance list"}},
        )
        for payload in payloads:
            with self.subTest(tool=payload.get("tool_name", payload.get("tool"))):
                self.assertEqual(self.run_guard(payload).returncode, 0)

    def test_an_unparseable_payload_fails_open(self):
        result = subprocess.run(
            ["bash", str(GUARD)], input='{"tool_name":"Bash", modern-web-guidance', capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
