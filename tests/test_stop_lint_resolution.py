"""Stop sub-scripts run only the lint shipped beside them, never a project's copy.

Each hook is copied into a throwaway shipped tree (`<tree>/scripts/hooks/stop/`) and run
against a throwaway project that plants a same-named lint at every path the hooks used
to fall back to. See scripts/hooks/lib/shipped-lint.sh.
"""

import os
import shutil
import subprocess
import unittest

from devteam_support import REPO_ROOT, StoreTestCase, make_git_project, requires_bash

from devteam import providers

STOP = REPO_ROOT / "scripts" / "hooks" / "stop"

#: hook → (lint it runs, a touched path that passes its gate, project files its gate needs)
HOOKS = {
    "03c-reuse-lint.sh": ("reuse-lint.sh", "src/app.js", {"docs/development/reuse-guidelines.md": "# Rules\n"}),
    "03d-design-token-lint.sh": ("design-token-lint.sh", "src/app.css", {}),
    "03f-spec-lint.sh": ("spec-lint.sh", "docs/specs/checkout.md", {"docs/specs/.keep": ""}),
    "03g-index-lint.sh": ("index-lint.sh", "docs/wiki/a.md", {}),
}

#: Hooks are provider-agnostic (every provider calls the same stop.sh); the map makes
#: adding a provider a decision. Fails when one is added without a case.
RUNS_STOP_DISPATCHER = {"claude": True, "codex": True, "opencode": True}

MARKER_LINT = "#!/usr/bin/env bash\necho ran > \"{marker}\"\n"


@requires_bash()
class ShippedLintResolutionTest(StoreTestCase):
    def setUp(self):
        super().setUp()
        self.repo = make_git_project(self.tmp / "app")
        # A space in the shipped path: the resolver must quote every expansion.
        self.tree = self.tmp / "ship ped" / "scripts"
        # The hooks and the libraries they source — what every bind places beside them.
        for tree in ("hooks", "lib"):
            shutil.copytree(str(REPO_ROOT / "scripts" / tree), str(self.tree / tree))

    def write(self, path, text):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def run_hook(self, hook, touched):
        env = dict(
            os.environ,
            USER_DATA_DIR=str(self.tmp / "state"),
            DEVTEAM_TOUCHED_COMPUTED="1",
            DEVTEAM_TOUCHED_PATHS=touched,
        )
        env.pop("DEVTEAM_NO_CHANGES", None)
        return subprocess.run(["bash", str(self.tree / "hooks" / "stop" / hook)], cwd=str(self.repo), env=env,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def plant(self, lint):
        markers = []
        for rel in ("scripts/" + lint, ".dev-team-agents/scripts/" + lint):
            marker = self.tmp / ("planted-" + rel.replace("/", "_"))
            self.write(self.repo / rel, MARKER_LINT.format(marker=marker))
            markers.append(marker)
        # The old 03c guard: a repository could satisfy it by committing this file.
        self.write(self.repo / "scripts" / "lib" / "tiers.json", "{}\n")
        return markers

    def test_every_provider_has_a_decided_case(self):
        self.assertEqual(set(RUNS_STOP_DISPATCHER), set(providers.ALL_PROVIDERS))

    def test_a_project_copy_never_runs_when_the_shipped_lint_is_absent(self):
        # The hooks receive no provider variable, so each pass runs the same script; the
        # loop keeps the per-provider record honest if that ever stops being true.
        for provider in providers.ALL_PROVIDERS:
            for hook, (lint, touched, needs) in HOOKS.items():
                with self.subTest(provider=provider, hook=hook):
                    self.setUp()
                    for rel, text in needs.items():
                        self.write(self.repo / rel, text)
                    markers = self.plant(lint)
                    result = self.run_hook(hook, touched)
                    self.assertEqual(result.returncode, 0, result.stderr.decode())
                    for marker in markers:
                        self.assertFalse(marker.exists(), "{} ran {}".format(hook, marker.name))

    def test_the_shipped_lint_is_the_one_that_runs(self):
        for hook, (lint, touched, needs) in HOOKS.items():
            with self.subTest(hook=hook):
                self.setUp()
                for rel, text in needs.items():
                    self.write(self.repo / rel, text)
                planted = self.plant(lint)
                shipped = self.tmp / "shipped-ran"
                self.write(self.tree / lint, MARKER_LINT.format(marker=shipped))
                result = self.run_hook(hook, touched)
                self.assertIn(result.returncode, (0, 2), result.stderr.decode())
                self.assertTrue(shipped.exists(), "{} did not run the shipped {}".format(hook, lint))
                for marker in planted:
                    self.assertFalse(marker.exists())

    def test_a_link_bind_layout_resolves_through_the_link(self):
        # Production link bind: `.dev-team-agents/scripts` is a symlink into the store,
        # and the hook runs through that link.
        lint, touched, needs = HOOKS["03g-index-lint.sh"]
        shipped = self.tmp / "shipped-ran"
        self.write(self.tree / lint, MARKER_LINT.format(marker=shipped))
        bound = self.repo / ".dev-team-agents"
        bound.mkdir()
        os.symlink(str(self.tree), str(bound / "scripts"))
        env = dict(os.environ, USER_DATA_DIR=str(self.tmp / "state"), DEVTEAM_TOUCHED_COMPUTED="1",
                   DEVTEAM_TOUCHED_PATHS=touched)
        env.pop("DEVTEAM_NO_CHANGES", None)
        subprocess.run(["bash", ".dev-team-agents/scripts/hooks/stop/03g-index-lint.sh"], cwd=str(self.repo),
                       env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertTrue(shipped.exists())


if __name__ == "__main__":
    unittest.main()
