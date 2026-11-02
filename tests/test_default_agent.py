"""ADR-0062 decision 3: `orchestrator_default` makes the persona the Claude Code session default.

Runs the real bind (and so the real installers) for every provider in
`providers.ALL_PROVIDERS`. The key is personal, so it lives in the git-ignored
`.claude/settings.local.json`; opencode and Codex have none and must stay untouched.
"""

import json
import os
import shutil
import subprocess
import sys
import unittest

from devteam_support import REPO_ROOT, StoreTestCase, requires_bash

from devteam import bind, default_agent, prefs, providers, versions

SCRIPT = REPO_ROOT / "scripts" / "lib" / "default_agent.py"

#: provider -> (config file the key lives in, key). None: the provider has no such key.
TARGETS = {
    "claude": (".claude/settings.local.json", "agent"),
    "opencode": None,
    "codex": None,
}

#: Where a key that must never be written would show up, per provider with none.
FORBIDDEN = {
    "opencode": ((".opencode/opencode.json", "default_agent"),),
    "codex": (),
}

TOOLS = {"claude": (), "opencode": ("bash", "python3", "jq"), "codex": ("bash", "python3")}


@requires_bash()
class DefaultAgentTest(StoreTestCase):
    def setUp(self):
        super().setUp()
        versions.install_from_tree(REPO_ROOT, version="9.9.9", force=True, make_current=True)
        self._home = os.environ.get("HOME")
        fake_home = self.tmp / "fake-home"
        fake_home.mkdir()
        os.environ["HOME"] = str(fake_home)
        self.addCleanup(self._restore_home)

    def _restore_home(self):
        if self._home is None:
            os.environ.pop("HOME", None)
        else:
            os.environ["HOME"] = self._home

    def _providers(self):
        for provider in providers.ALL_PROVIDERS:
            missing = [tool for tool in TOOLS[provider] if shutil.which(tool) is None]
            if missing:
                self.skipTest("{} needs {}".format(provider, ", ".join(missing)))
            yield provider

    def _read(self, root, provider):
        path = root / TARGETS[provider][0]
        return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}

    def _set(self, project_id, value):
        prefs.set_value("orchestrator_default", value, "9.9.9", scope="project", project_id=project_id)

    def test_every_provider_has_a_case(self):
        self.assertEqual(set(TARGETS), set(providers.ALL_PROVIDERS))
        self.assertEqual(set(TOOLS), set(providers.ALL_PROVIDERS))
        self.assertEqual(set(default_agent.KEYS), {p for p, t in TARGETS.items() if t})
        self.assertEqual(set(FORBIDDEN), {p for p, t in TARGETS.items() if t is None})

    def test_default_is_off_and_not_written(self):
        for provider in self._providers():
            with self.subTest(provider=provider):
                root = self.new_project("off-" + provider)
                bind.bind(root, provider_names=[provider])
                if TARGETS[provider]:
                    self.assertNotIn(TARGETS[provider][1], self._read(root, provider))

    def test_absent_key_is_written_user_value_is_kept_off_removes_ours(self):
        for provider in self._providers():
            target = TARGETS[provider]
            with self.subTest(provider=provider):
                root = self.new_project("on-" + provider)
                project_id = bind.bind(root, provider_names=[provider])["project_id"]
                if target is None:
                    self._set(project_id, "true")
                    bind.bind(root, provider_names=[provider])
                    self.assertEqual(sorted(p.name for p in root.glob(".codex/config*")), [])
                    for rel, key in FORBIDDEN[provider]:
                        path = root / rel
                        if path.is_file():
                            self.assertNotIn(key, json.loads(path.read_text(encoding="utf-8")))
                    continue
                key = target[1]

                self._set(project_id, "true")
                bind.bind(root, provider_names=[provider])
                self.assertEqual(self._read(root, provider).get(key), "orchestrator")

                self._set(project_id, "false")
                bind.bind(root, provider_names=[provider])
                self.assertNotIn(key, self._read(root, provider))

    def test_a_user_value_is_never_overwritten_or_removed(self):
        for provider in self._providers():
            target = TARGETS[provider]
            if target is None:
                continue
            path_rel, key = target
            with self.subTest(provider=provider):
                root = self.new_project("user-" + provider)
                project_id = bind.bind(root, provider_names=[provider])["project_id"]
                path = root / path_rel
                data = self._read(root, provider)
                data[key] = "mine"
                path.write_text(json.dumps(data), encoding="utf-8")

                self._set(project_id, "true")
                bind.bind(root, provider_names=[provider])
                self.assertEqual(self._read(root, provider)[key], "mine")

                self._set(project_id, "false")
                bind.bind(root, provider_names=[provider])
                self.assertEqual(self._read(root, provider)[key], "mine")

    def test_unbind_removes_only_our_value(self):
        for provider in self._providers():
            target = TARGETS[provider]
            if target is None:
                continue
            key = target[1]
            with self.subTest(provider=provider):
                root = self.new_project("unbind-" + provider)
                project_id = bind.bind(root, provider_names=[provider])["project_id"]
                self._set(project_id, "true")
                bind.bind(root, provider_names=[provider])
                self.assertEqual(self._read(root, provider).get(key), "orchestrator")
                unbound = bind.unbind(root)
                self.assertIn("{} (agent)".format(default_agent.CLAUDE_FILE), unbound["unlinked"])
                self.assertNotIn(key, self._read(root, provider))

    def test_the_committed_settings_file_never_gets_the_key_and_the_file_is_ignored(self):
        root = self.new_project("committed")
        project_id = bind.bind(root, provider_names=["claude"])["project_id"]
        self._set(project_id, "true")
        bind.bind(root, provider_names=["claude"])
        settings = json.loads((root / ".claude" / "settings.json").read_text(encoding="utf-8"))
        self.assertNotIn("agent", settings)
        self.assertIn(".claude/settings.local.json", bind.project_gitignore_entries(root))

    def test_first_bind_of_a_v2_project_honours_its_legacy_preference(self):
        root = self.new_project("v2-first")
        legacy = root / ".dev-team-agents" / "user-data" / "preferences.json"
        legacy.parent.mkdir(parents=True)
        legacy.write_text(json.dumps({"orchestrator_default": True}), encoding="utf-8")
        bind.bind(root, provider_names=["claude"])
        self.assertEqual(self._read(root, "claude").get("agent"), "orchestrator")

    def _run_script(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True)

    def test_script_exit_codes(self):
        self.assertEqual(self._run_script().returncode, 1)
        for provider in providers.ALL_PROVIDERS:
            if TARGETS[provider] is None:
                self.assertEqual(self._run_script(provider, str(self.tmp)).returncode, 1, provider)

        root = self.tmp / "script-nonobject"
        (root / ".claude").mkdir(parents=True)
        (root / ".claude" / "settings.local.json").write_text("[]", encoding="utf-8")
        self.assertEqual(self._run_script("claude", str(root)).returncode, 4)

        outside = self.tmp / "outside"
        outside.mkdir()
        linked = self.tmp / "script-symlink"
        linked.mkdir()
        try:
            os.symlink(str(outside), str(linked / ".claude"))
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable")
        self.assertEqual(self._run_script("claude", str(linked)).returncode, 4)
        self.assertEqual(list(outside.iterdir()), [])

        clean = self.tmp / "script-ok"
        clean.mkdir()
        self.assertEqual(self._run_script("claude", str(clean)).returncode, 0)

    def test_opencode_primary_agents_mirror_the_renderer(self):
        sys.path.insert(0, str(REPO_ROOT / "scripts" / "lib"))
        try:
            import render_provider
        finally:
            sys.path.pop(0)
        self.assertEqual(providers.OPENCODE_PRIMARY_AGENTS, render_provider.OPENCODE_PRIMARY_AGENTS)

    # install.sh Step 7c calls the same script with the same project root; the full installer
    # is not run here (it needs the network and a published tarball), so the script is what is tested.

if __name__ == "__main__":
    unittest.main()
