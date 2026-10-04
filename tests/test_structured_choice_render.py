"""Structured-choice parity: `AskUserQuestion` renders to each provider's native tool.

Source agents and commands say `AskUserQuestion`. Claude keeps it; opencode must
say `question`; Codex must name its structured user-input tool and carry the
fallback that matches the command's `interaction_mode`.
"""

import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from devteam_support import REPO_ROOT

sys.path.insert(0, str(REPO_ROOT / "scripts" / "lib"))

from devteam import providers  # noqa: E402

RENDERER = REPO_ROOT / "scripts" / "lib" / "render_provider.py"
COMPAT = REPO_ROOT / "scripts" / "check-codex-compat.sh"

#: One entry per provider in `providers.ALL_PROVIDERS`; the parity guard below
#: fails the moment a provider is added without its own case.
EXPECTATIONS = {
    "claude": {
        "marker": re.compile(r"AskUserQuestion"),
        "forbidden": (),
    },
    "opencode": {
        "marker": re.compile(r"`question`"),
        "forbidden": ("AskUserQuestion", "``question"),
    },
    "codex": {
        "marker": re.compile(r"request_user_input_async"),
        "forbidden": ("(Plan mode)", "``request_user_input", "AskUserQuestion"),
    },
}

OPTIONAL_FALLBACK = "ask the same question directly in the conversation as a numbered list"
REQUIRED_FALLBACK = "tell the user to switch this task to `/plan`"
MODE_RE = re.compile(r"<!-- codex-interaction-mode: (\w+) -->")


def _sources(sub):
    for path in sorted((REPO_ROOT / sub).glob("*.md")):
        text = path.read_text(encoding="utf-8")
        if "AskUserQuestion" in text:
            yield path.stem


def _render(provider, target):
    subprocess.run(
        [sys.executable, str(RENDERER), "--provider", provider,
         "--source-dir", str(REPO_ROOT), "--target-dir", str(target)],
        check=True, capture_output=True, text=True,
    )
    return {p.relative_to(target).as_posix(): p.read_text(encoding="utf-8")
            for p in target.rglob("*") if p.is_file() and not p.is_symlink()}


class StructuredChoiceRenderTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.dirs, cls.out = {}, {}
        for provider in providers.ALL_PROVIDERS:
            target = Path(cls._tmp.name) / provider
            target.mkdir()
            cls.dirs[provider] = target
            cls.out[provider] = _render(provider, target)
        cls.commands_meta = json.loads(
            (REPO_ROOT / "scripts" / "lib" / "commands.json").read_text(encoding="utf-8"))["commands"]

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def _rendered_for(self, provider, kind, name):
        files = self.out[provider]
        if provider == "claude":
            return [t for p, t in files.items()
                    if p.startswith(".claude/") and p.endswith(f"/{name}.md")
                    and f"/{kind}s/" in p]
        if provider == "opencode":
            if kind == "agent":
                return [files[f".opencode/agents/{name}.md"]]
            return [files[".opencode/commands.snippet.jsonc"]]
        if kind == "agent":
            return [files[f".codex/agents/{name}.toml"]]
        return [t for p, t in files.items() if p.startswith(f".codex/skills/devteam-{name}")]

    def test_every_provider_has_a_parity_case(self):
        self.assertEqual(set(EXPECTATIONS), set(providers.ALL_PROVIDERS))

    def test_ask_user_question_sources_render_to_the_native_marker(self):
        for provider in providers.ALL_PROVIDERS:
            marker = EXPECTATIONS[provider]["marker"]
            for kind in ("agent", "command"):
                for name in _sources(kind + "s"):
                    with self.subTest(provider=provider, kind=kind, name=name):
                        texts = self._rendered_for(provider, kind, name)
                        self.assertTrue(texts, "nothing rendered")
                        if provider == "opencode" and kind == "command":
                            snippet = json.loads(
                                "\n".join(l for l in texts[0].splitlines() if not l.startswith("//")))
                            texts = [snippet[f"devteam:{name}"]["template"]]
                        self.assertTrue(any(marker.search(t) for t in texts))

    def test_forbidden_substrings_are_absent(self):
        for provider in providers.ALL_PROVIDERS:
            for rel, text in self.out[provider].items():
                for bad in EXPECTATIONS[provider]["forbidden"]:
                    with self.subTest(provider=provider, file=rel, bad=bad):
                        self.assertNotIn(bad, text)

    def test_codex_fallback_matches_interaction_mode(self):
        skills = {p: t for p, t in self.out["codex"].items()
                  if p.startswith(".codex/skills/devteam-") and p.endswith("SKILL.md")}
        self.assertTrue(skills)
        asking = set(_sources("commands"))
        for rel, text in skills.items():
            name = rel.split("/")[2][len("devteam-"):]
            mode = self.commands_meta[name]["interaction_mode"]
            with self.subTest(command=name, mode=mode):
                self.assertEqual(MODE_RE.findall(text), [mode])
                if mode == "required":
                    if name in asking:
                        self.assertIn(REQUIRED_FALLBACK, text)
                else:
                    self.assertNotIn(REQUIRED_FALLBACK, text)
                    if name in asking:
                        self.assertIn(OPTIONAL_FALLBACK, text)

    def test_codex_required_commands_that_ask_carry_required_fallback(self):
        for name, meta in self.commands_meta.items():
            if meta.get("interaction_mode") != "required" or name not in set(_sources("commands")):
                continue
            with self.subTest(command=name):
                texts = self._rendered_for("codex", "command", name)
                self.assertTrue(any(REQUIRED_FALLBACK in t for t in texts))

    def test_opencode_agents_allow_questions_and_never_deny_bash(self):
        agents = {p: t for p, t in self.out["opencode"].items() if p.startswith(".opencode/agents/")}
        self.assertTrue(agents)
        for rel, text in agents.items():
            fm = text.split("---")[1]
            with self.subTest(agent=rel):
                self.assertRegex(fm, r"(?m)^mode:\s*all\s*$")
                self.assertRegex(fm, r"(?m)^\s+question:\s*allow\s*$")
                self.assertRegex(fm, r"(?m)^\s+bash:\s*ask\s*$")
                self.assertRegex(fm, r"(?m)^\s+task:\s*allow\s*$")
                self.assertNotRegex(fm, r"(?m)^\s+bash:\s*deny")

    def test_claude_render_is_identity(self):
        for kind, sub in (("agent", "agents"), ("command", "commands")):
            for name in _sources(sub):
                src = (REPO_ROOT / sub / f"{name}.md").read_text(encoding="utf-8")
                with self.subTest(kind=kind, name=name):
                    self.assertIn(src, self._rendered_for("claude", kind, name))

    def test_codex_tree_passes_compat_lint(self):
        result = subprocess.run(["bash", str(COMPAT), str(self.dirs["codex"] / ".codex")],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
