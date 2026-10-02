"""The delegated installers (opencode, Codex) fail loudly and stay inside the project.

Drives the real `install-*.sh` scripts against a throwaway git project, so the guarantees
(refuse an unmergeable config, refuse a symlinked provider dir, ignore the credentials
file, re-render on update/rollback) are checked where they live — in bash.
"""

import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

from devteam_support import REPO_ROOT, StoreTestCase, requires_bash

from devteam import providers

sys.path.insert(0, str(REPO_ROOT / "scripts" / "lib"))
import codex_hooks_merge  # noqa: E402

SCRIPTS = REPO_ROOT / "scripts"
CONFLICT = 4

#: Per provider: the installer, the directory it owns, a file it writes, the tools it needs.
#: `claude` has no delegated installer; its entry says so, and the parity test fails the moment
#: a provider is added to `ALL_PROVIDERS` without a case here.
INSTALLERS = {
    "claude": None,
    "opencode": {
        "script": "install-opencode.sh",
        "dir": ".opencode",
        "written": ".opencode/agents/backend-developer.md",
        "tools": ("bash", "python3", "jq"),
    },
    "codex": {
        "script": "install-codex.sh",
        "dir": ".codex",
        "written": ".codex/agents/backend-developer.toml",
        "tools": ("bash", "python3"),
    },
}


@requires_bash()
class DelegatedInstallerTest(StoreTestCase):
    def setUp(self):
        super().setUp()
        self.fake_home = self.tmp / "fake-home"
        self.fake_home.mkdir()

    def _installers(self):
        for provider in providers.ALL_PROVIDERS:
            case = INSTALLERS[provider]
            if case is None:
                continue
            missing = [t for t in case["tools"] if shutil.which(t) is None]
            if missing:
                self.skipTest("{} needs {}".format(provider, ", ".join(missing)))
            yield provider, case

    def _install(self, root, case, *extra):
        env = dict(os.environ, HOME=str(self.fake_home))
        return subprocess.run(
            ["bash", str(SCRIPTS / case["script"]), "--source", str(REPO_ROOT), *extra],
            cwd=str(root), env=env, capture_output=True, text=True, timeout=300,
        )

    def test_every_provider_has_a_case(self):
        self.assertEqual(set(INSTALLERS), set(providers.ALL_PROVIDERS))

    def test_a_malformed_codex_hooks_file_is_refused_and_preserved(self):
        if shutil.which("python3") is None:
            self.skipTest("needs python3")
        for label, body in (
            ("not json", b'{"hooks": {broken'),
            ("array", b"[]"),
            ("hooks not an object", b'{"hooks": []}'),
            ("event not an array", b'{"hooks": {"Stop": {}}}'),
        ):
            with self.subTest(label):
                root = self.new_project("hooks-" + label.replace(" ", "-"))
                hooks = root / ".codex" / "hooks.json"
                hooks.parent.mkdir()
                hooks.write_bytes(body)

                result = self._install(root, INSTALLERS["codex"])

                self.assertEqual(result.returncode, CONFLICT, result.stderr)
                self.assertIn("hooks.json", result.stderr)
                self.assertEqual(hooks.read_bytes(), body)
                self.assertFalse((root / ".codex" / "agents").exists())

    def test_a_wrong_shape_codex_hooks_file_keeps_unrelated_keys_on_success(self):
        if shutil.which("python3") is None:
            self.skipTest("needs python3")
        root = self.new_project("hooks-keep")
        hooks = root / ".codex" / "hooks.json"
        hooks.parent.mkdir()
        hooks.write_text('{"note": "mine"}', encoding="utf-8")

        result = self._install(root, INSTALLERS["codex"])

        self.assertEqual(result.returncode, 0, result.stderr)
        import json

        merged = json.loads(hooks.read_text(encoding="utf-8"))
        self.assertEqual(merged["note"], "mine")
        self.assertIn("Stop", merged["hooks"])

    def test_the_windows_hook_command_walks_to_the_root_through_an_absolute_bash(self):
        bash = "C:\\Program Files\\Git\\bin\\bash.exe"
        windows = codex_hooks_merge.command_for(
            ".dev-team-agents/scripts/hooks", "stop.sh", windows=True, bash_path=bash
        )
        unix = codex_hooks_merge.command_for(".dev-team-agents/scripts/hooks", "stop.sh", windows=False)

        # The outer pair is the one `cmd /C` strips from a line holding more than two quotes.
        self.assertTrue(windows.startswith('""{}" -c "'.format(bash)), windows)
        self.assertTrue(windows.endswith('""'))
        body = windows[len('""{}" -c "'.format(bash)):-2]
        self.assertIn('while [ -n \\"$d\\" ]', body)
        self.assertIn("exec bash .dev-team-agents/scripts/hooks/stop.sh", body)
        self.assertNotIn("'", windows)
        # Same walk as the Unix form once the cmd.exe escaping is undone.
        walk = unix[len("env -u BASH_ENV -u ENV bash -c '"):-1]
        self.assertEqual(body.replace('\\"', '"'), walk)

    def test_the_unix_hook_command_strips_the_shell_startup_variables(self):
        command = codex_hooks_merge.command_for(".dev-team-agents/scripts/hooks", "stop.sh", windows=False)
        self.assertTrue(command.startswith("env -u BASH_ENV -u ENV bash -c '"))

    def test_git_bash_discovery_never_picks_the_wsl_launcher(self):
        def which(_):
            return "C:\\Windows\\System32\\bash.exe"

        found = codex_hooks_merge.find_git_bash(
            which=which,
            environ={"ProgramFiles": "C:\\Program Files"},
            isfile=lambda p: p.endswith("Git\\bin\\bash.exe") or p.endswith("Git/bin/bash.exe"),
        )
        self.assertIsNotNone(found)
        self.assertNotIn("System32", found)
        self.assertIsNone(
            codex_hooks_merge.find_git_bash(
                which=lambda _: "C:\\Users\\x\\AppData\\Local\\Microsoft\\WindowsApps\\bash.exe",
                environ={},
                isfile=lambda p: False,
            )
        )

    def test_a_jsonc_opencode_config_is_refused_and_untouched(self):
        case = INSTALLERS["opencode"]
        if any(shutil.which(t) is None for t in case["tools"]):
            self.skipTest("opencode needs bash, python3 and jq")
        root = self.new_project("jsonc")
        cfg = root / ".opencode" / "opencode.json"
        cfg.parent.mkdir()
        body = b'{\n  // my comment\n  "command": {},\n}\n'
        cfg.write_bytes(body)

        result = self._install(root, case)

        self.assertEqual(result.returncode, CONFLICT, result.stderr)
        self.assertIn("opencode.json", result.stderr)
        self.assertEqual(cfg.read_bytes(), body)
        self.assertNotIn("merged", result.stdout)

    def test_a_provider_dir_that_leaves_the_project_is_refused(self):
        for provider, case in self._installers():
            with self.subTest(provider=provider):
                root = self.new_project("escape-" + provider)
                outside = self.tmp / ("global-" + provider)
                outside.mkdir()
                try:
                    (root / case["dir"]).symlink_to(outside, target_is_directory=True)
                except (OSError, NotImplementedError):
                    self.skipTest("cannot create symlinks here")

                result = self._install(root, case)

                self.assertEqual(result.returncode, CONFLICT, result.stderr)
                self.assertIn("outside the project", result.stderr)
                self.assertEqual(list(outside.iterdir()), [])

    def test_a_standalone_install_ignores_the_credentials_file(self):
        for provider, case in self._installers():
            with self.subTest(provider=provider):
                root = self.new_project("creds-" + provider)

                result = self._install(root, case)
                self.assertEqual(result.returncode, 0, result.stderr)

                for name in ("credentials.local.json", "credentials.local.json.bak"):
                    target = root / ".dev-team-agents" / name
                    target.write_text("{}", encoding="utf-8")
                    ignored = subprocess.run(
                        ["git", "check-ignore", "-q", "--no-index", str(target)], cwd=str(root)
                    )
                    self.assertEqual(ignored.returncode, 0, name)

    def test_update_and_rollback_re_render_every_provider_and_survive_a_failure(self):
        for name in ("update.sh", "rollback.sh"):
            text = (SCRIPTS / name).read_text(encoding="utf-8")
            self.assertIn("po_rerender_providers", text, name)

        root = self.tmp / "rerender"
        scripts = root / ".dev-team-agents" / "scripts"
        scripts.mkdir(parents=True)
        (root / ".dev-team-agents" / "opencode" / "plugin").mkdir(parents=True)
        (root / ".dev-team-agents" / "agents").mkdir()
        (root / ".dev-team-agents" / "opencode" / "plugin" / "dev-team-agents.ts").write_text("", encoding="utf-8")
        (root / ".dev-team-agents" / "agents" / "product-analyst.md").write_text("", encoding="utf-8")
        (scripts / "render-provider.sh").write_text("", encoding="utf-8")
        (scripts / "install-opencode.sh").write_text("echo opencode >> \"$LOG\"; exit 1\n", encoding="utf-8")
        (scripts / "install-codex.sh").write_text("echo codex >> \"$LOG\"\n", encoding="utf-8")
        (root / ".opencode").mkdir()
        (root / ".codex").mkdir()
        log = self.tmp / "rerender.log"

        result = subprocess.run(
            ["bash", "-c", 'set -euo pipefail; source "$1"; po_rerender_providers; echo reached', "x",
             str(SCRIPTS / "lib" / "provider-ownership.sh")],
            cwd=str(root), env=dict(os.environ, LOG=str(log)), capture_output=True, text=True,
        )

        self.assertEqual(log.read_text(encoding="utf-8").split(), ["opencode", "codex"])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("install-opencode.sh failed", result.stderr)


if __name__ == "__main__":
    unittest.main()
