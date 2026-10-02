"""Renderer parity: tool names and docs paths render consistently on every provider.

Source agents and commands are written with Claude Code tool names and the shipped
`docs/development/...` layout. Each non-Claude provider must (a) rename or replace the
Claude-only tools, never leaving a literal Claude name behind, and (b) keep the docs
paths the shipped scripts hardcode.
"""

import re
import sys
import unittest

from devteam_support import REPO_ROOT

sys.path.insert(0, str(REPO_ROOT / "scripts" / "lib"))

import render_provider  # noqa: E402
from devteam import providers  # noqa: E402

LIB = render_provider.load_lib(REPO_ROOT / "scripts" / "lib")

#: Claude tool names that must not survive a render on a provider that does not own them.
CLAUDE_ONLY = ("AskUserQuestion", "ScheduleWakeup", "TaskList", "TaskGet", "TaskOutput",
               "SendMessage", "TodoWrite", "WebFetch")

SCRIPT_DOC_PATHS = {
    "scripts/new-adr.sh": "docs/development/adrs",
    "scripts/reuse-lint.sh": "docs/development/reuse-guidelines.md",
    "scripts/hooks/stop/03e-adr-gap-check.sh": "docs/development/adrs/",
}


def _render_all(provider):
    """Yield (label, text) for every rendered agent and command on `provider`."""
    tm = LIB["tool_map"]
    for path in sorted((REPO_ROOT / "agents").glob("*.md")):
        fm, body = render_provider.parse_frontmatter(path.read_text())
        if provider == "opencode":
            out = render_provider.render_agent_opencode(path.stem, fm, body, "m", None, tm)
        else:
            out = render_provider.render_agent_codex(path.stem, fm, body, "m", None, tm)
        yield f"agent:{path.stem}", out["content"]
    for path in sorted((REPO_ROOT / "commands").glob("*.md")):
        meta = LIB["commands"]["commands"][path.stem]
        _, body = render_provider.parse_frontmatter(path.read_text())
        if provider == "opencode":
            entry = render_provider.render_command_opencode(path.stem, meta, body, "m", None, tm)
            yield f"command:{path.stem}", entry["snippet_entry"]["template"]
        else:
            out = render_provider.render_command_codex(path.stem, meta, body, "m", None, tm)
            for item in (out if isinstance(out, list) else [out]):
                yield f"command:{path.stem}", item["content"]


class RenderToolMapTest(unittest.TestCase):
    def test_every_provider_has_a_map_entry(self):
        for provider in providers.ALL_PROVIDERS:
            self.assertIn(provider, LIB["tool_map"]["providers"], provider)

    def test_no_claude_only_tool_name_survives(self):
        for provider in providers.ALL_PROVIDERS:
            if provider == "claude":
                continue
            pattern = re.compile(r"\b(%s)\b" % "|".join(CLAUDE_ONLY))
            with self.subTest(provider=provider):
                leaks = [(label, m.group(1)) for label, text in _render_all(provider)
                         for m in pattern.finditer(text)]
                self.assertEqual(leaks, [])

    def test_docs_paths_match_shipped_scripts(self):
        for provider in providers.ALL_PROVIDERS:
            rewrites = LIB["tool_map"]["providers"][provider].get("path_rewrites", {})
            with self.subTest(provider=provider):
                self.assertNotIn("docs/development/", rewrites)
        for script, needle in SCRIPT_DOC_PATHS.items():
            self.assertIn(needle, (REPO_ROOT / script).read_text(), script)
        for provider in providers.ALL_PROVIDERS:
            if provider == "claude":
                continue
            with self.subTest(provider=provider):
                text = "\n".join(t for label, t in _render_all(provider) if label in
                                 ("command:adr", "command:rule"))
                self.assertIn("docs/development/", text)
                self.assertNotRegex(text, r"(?<!development/)docs/(adrs|reuse-guidelines)")

    def test_opencode_commands_use_canonical_question_tool(self):
        for name in ("backend", "frontend", "fullstack", "mobile"):
            body = (REPO_ROOT / "commands" / f"{name}.md").read_text()
            self.assertNotIn("`question` tool", body, name)


if __name__ == "__main__":
    unittest.main()
