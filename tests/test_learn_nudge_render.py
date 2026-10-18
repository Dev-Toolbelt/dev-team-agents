"""Learn-nudge parity: a Yes to the nudge runs `learn --auto` inline on every provider.

The canonical check lives in `commands/merge.md` § Step 4; `pr`, `refactor` and
`audit` delegate to it. Each provider's rendered merge command must name that
provider's own `learn` invocation and must not fall back to a hand-off.
"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from devteam_support import REPO_ROOT

sys.path.insert(0, str(REPO_ROOT / "scripts" / "lib"))

from devteam import providers  # noqa: E402

RENDERER = REPO_ROOT / "scripts" / "lib" / "render_provider.py"

#: One entry per provider in `providers.ALL_PROVIDERS`; the parity guard below
#: fails the moment a provider is added without its own case.
INVOCATIONS = {
    "claude": "/devteam:learn --auto",
    "opencode": "/devteam:learn --auto",
    "codex": "$devteam-learn --auto",
}

INLINE_DIRECTIVE = "with `--auto` inline, in this same turn"
HAND_OFF = "hand off by telling the user to invoke"
DELEGATORS = ("pr", "refactor", "audit")


def _render(provider, target):
    subprocess.run(
        [sys.executable, str(RENDERER), "--provider", provider,
         "--source-dir", str(REPO_ROOT), "--target-dir", str(target)],
        check=True, capture_output=True, text=True,
    )


def _command(provider, target, name):
    if provider == "claude":
        return (target / ".claude/commands/devteam" / f"{name}.md").read_text(encoding="utf-8")
    if provider == "opencode":
        raw = (target / ".opencode/commands.snippet.jsonc").read_text(encoding="utf-8")
        snippet = json.loads("\n".join(l for l in raw.splitlines() if not l.startswith("//")))
        return snippet[f"devteam:{name}"]["template"]
    return (target / ".codex/skills" / f"devteam-{name}" / "SKILL.md").read_text(encoding="utf-8")


class LearnNudgeRenderTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.targets = {}
        for provider in providers.ALL_PROVIDERS:
            target = Path(cls._tmp.name) / provider
            target.mkdir()
            _render(provider, target)
            cls.targets[provider] = target

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def test_every_provider_has_a_parity_case(self):
        self.assertEqual(set(INVOCATIONS), set(providers.ALL_PROVIDERS))

    def test_merge_runs_learn_inline_with_the_provider_invocation(self):
        for provider in providers.ALL_PROVIDERS:
            with self.subTest(provider=provider):
                text = _command(provider, self.targets[provider], "merge")
                self.assertIn(INLINE_DIRECTIVE, text)
                self.assertIn(INVOCATIONS[provider], text)
                self.assertNotIn(HAND_OFF, text)

    def test_closing_commands_delegate_to_the_canonical_check(self):
        for provider in providers.ALL_PROVIDERS:
            for name in DELEGATORS:
                with self.subTest(provider=provider, command=name):
                    text = _command(provider, self.targets[provider], name)
                    self.assertIn("commands/merge.md` § Step 4", text)
                    self.assertNotIn("never spawn `/devteam:learn` inline", text)


if __name__ == "__main__":
    unittest.main()
