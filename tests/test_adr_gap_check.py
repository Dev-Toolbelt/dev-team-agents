"""The ADR-gap Stop check warns once per set of signals, not after every reply.

A Stop sub-script that exits 2 is fed back to the agent, and Claude Code answers by
continuing the turn. The check used to exit 2 on every Stop while a new dependency sat
uncommitted, so a warning the user had already declined repeated after every reply.
These tests run the real script against a throwaway git repository and a scratch state
directory — never the developer's own.
"""

import os
import subprocess
import unittest

from devteam_support import REPO_ROOT, StoreTestCase, make_git_project, requires_bash

from devteam import providers

HOOK = REPO_ROOT / "scripts" / "hooks" / "stop" / "03e-adr-gap-check.sh"

#: Whether each provider shows a Stop hook's stderr to the agent. The script and its
#: marker are provider-agnostic (no provider variable reaches the Stop environment), so
#: the behaviour asserted below is the same for all; this map records who sees the
#: warning, and the parity guard fails when a provider is added without deciding it.
SURFACES_WARNING = {"claude": True, "codex": True, "opencode": False}

PACKAGE = '{\n  "name": "app",\n  "dependencies": {}\n}\n'


@requires_bash()
class AdrGapCheckTest(StoreTestCase):
    def setUp(self):
        super().setUp()
        self.repo = make_git_project(self.tmp / "app")
        (self.repo / "package.json").write_text(PACKAGE, encoding="utf-8")
        self.git("add", "package.json")
        self.git("commit", "-qm", "manifest")
        self.state = self.tmp / "state"

    def git(self, *args):
        env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@e", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@e")
        subprocess.run(["git", *args], cwd=str(self.repo), check=True, env=env, stdout=subprocess.DEVNULL)

    def add_dependency(self, name):
        text = (self.repo / "package.json").read_text(encoding="utf-8")
        (self.repo / "package.json").write_text(text.replace('"dependencies": {', '"dependencies": {\n    "%s": "1.0.0",' % name), encoding="utf-8")

    def run_hook(self):
        env = dict(
            os.environ,
            USER_DATA_DIR=str(self.state),
            DEVTEAM_TOUCHED_COMPUTED="1",
            DEVTEAM_TOUCHED_PATHS="package.json",
        )
        env.pop("DEVTEAM_NO_CHANGES", None)
        result = subprocess.run(["bash", str(HOOK)], cwd=str(self.repo), env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return result.returncode, result.stderr.decode()

    def test_every_provider_has_a_decided_case(self):
        self.assertEqual(set(SURFACES_WARNING), set(providers.ALL_PROVIDERS))

    def test_warns_once_then_stays_quiet_for_the_same_change(self):
        for provider in providers.ALL_PROVIDERS:
            with self.subTest(provider=provider):
                self.setUp()
                self.add_dependency("left-pad")
                code, err = self.run_hook()
                self.assertEqual(code, 2)
                self.assertIn("POSSIBLE ADR GAP", err)
                self.assertEqual(self.run_hook(), (0, ""))
                # Staging the same change is not a new signal.
                self.git("add", "package.json")
                self.assertEqual(self.run_hook()[0], 0)

    def test_a_new_dependency_warns_again(self):
        self.add_dependency("left-pad")
        self.assertEqual(self.run_hook()[0], 2)
        self.assertEqual(self.run_hook()[0], 0)
        self.add_dependency("right-pad")
        self.assertEqual(self.run_hook()[0], 2)

    def test_never_writes_through_a_symlinked_marker(self):
        self.state.mkdir(parents=True)
        victim = self.tmp / "victim.txt"
        victim.write_text("mine\n", encoding="utf-8")
        (self.state / ".adr-gap-warned").symlink_to(victim)
        self.add_dependency("left-pad")
        self.assertEqual(self.run_hook()[0], 2)
        self.assertEqual(victim.read_text(encoding="utf-8"), "mine\n")
        # Without a usable marker it keeps warning rather than going silent.
        self.assertEqual(self.run_hook()[0], 2)

    def test_no_signal_no_warning(self):
        self.assertEqual(self.run_hook(), (0, ""))


if __name__ == "__main__":
    unittest.main()
