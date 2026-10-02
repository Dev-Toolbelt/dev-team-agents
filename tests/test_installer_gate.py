"""Provider parity for the account gate: the delegated installers enforce it like `bind` does.

`bind` is gated in-process by the central gate; opencode and Codex reach the project through
bash installers that `bind` does not wrap when run standalone, so each one calls
`devteam auth check` before its first write (`scripts/lib/auth-gate.sh`). The per-provider
map below fails the moment a provider is added to `ALL_PROVIDERS` without a case.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

from auth_support import AuthTestCase  # noqa: E402
from devteam_support import REPO_ROOT, requires_bash  # noqa: E402

from devteam import auth_gate as gate
from devteam import providers  # noqa: E402

BLOCKED = 5

#: Per provider: how its write path is gated. `claude` is the identity case — `devteam bind`
#: runs in-process under the central gate — so it has no installer script.
CASES = {
    "claude": None,
    "opencode": {
        "script": "install-opencode.sh",
        "written": ".opencode/agents/backend-developer.md",
        "tools": ("bash", "python3", "jq"),
    },
    "codex": {
        "script": "install-codex.sh",
        "written": ".codex/agents/backend-developer.toml",
        "tools": ("bash", "python3"),
    },
}


@requires_bash()
class InstallerGateTest(AuthTestCase):
    def setUp(self):
        super().setUp()
        self.fake_home = self.tmp / "fake-home"
        self.fake_home.mkdir()

    def _scripts(self, mode, name="scripts-copy", drop_cli=False):
        """A copy of `scripts/` whose compiled config carries ``mode`` (the gate reads its own tree)."""
        target = self.tmp / name
        shutil.copytree(REPO_ROOT / "scripts", target, ignore=shutil.ignore_patterns("__pycache__"))
        config = target / "lib" / "auth-config.json"
        data = json.loads(config.read_text())
        data["gate_mode"] = mode
        config.write_text(json.dumps(data))
        if drop_cli:
            shutil.rmtree(target / "cli")
        return target

    def _cases(self):
        for provider in providers.ALL_PROVIDERS:
            case = CASES[provider]
            if case is None:
                continue
            missing = [t for t in case["tools"] if shutil.which(t) is None]
            if missing:
                self.skipTest("{} needs {}".format(provider, ", ".join(missing)))
            yield provider, case

    def _run(self, scripts, case, project, *extra, env=None):
        merged = dict(os.environ, HOME=str(self.fake_home))
        merged.update(env or {})
        return subprocess.run(
            ["bash", str(scripts / case["script"]), "--source", str(REPO_ROOT), *extra],
            cwd=str(project), env=merged, capture_output=True, text=True, timeout=300,
        )

    def test_every_provider_has_a_case(self):
        self.assertEqual(set(CASES), set(providers.ALL_PROVIDERS))

    def test_enforce_refuses_before_any_write_on_every_delegated_provider(self):
        scripts = self._scripts("enforce")
        for provider, case in self._cases():
            with self.subTest(provider=provider):
                project = self.new_project("enforce-" + provider)
                result = self._run(scripts, case, project)
                self.assertEqual(result.returncode, BLOCKED, result.stderr)
                self.assertIn("blocked", result.stderr)
                self.assertIn("devteam auth login", result.stderr)
                self.assertFalse((project / case["written"]).exists())

    def test_warn_notices_and_installs(self):
        scripts = self._scripts("warn")
        for provider, case in self._cases():
            with self.subTest(provider=provider):
                project = self.new_project("warn-" + provider)
                result = self._run(scripts, case, project)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("upcoming release", result.stderr)
                self.assertTrue((project / case["written"]).exists())

    def test_an_entitled_account_installs_under_enforce(self):
        self.sign_in()
        scripts = self._scripts("enforce")
        for provider, case in self._cases():
            with self.subTest(provider=provider):
                project = self.new_project("entitled-" + provider)
                result = self._run(scripts, case, project)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertTrue((project / case["written"]).exists())

    def test_a_dry_run_and_a_target_listing_are_never_gated(self):
        scripts = self._scripts("enforce")
        for provider, case in self._cases():
            for flag in ("--dry-run", "--list-targets"):
                with self.subTest(provider=provider, flag=flag):
                    project = self.new_project("dry-{}{}".format(provider, flag))
                    result = self._run(scripts, case, project, flag)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertNotIn("blocked", result.stderr)

    def _path_without_devteam(self, extra=None):
        dirs = [d for d in os.environ.get("PATH", "").split(os.pathsep) if not (Path(d) / "devteam").exists()]
        return os.pathsep.join(([str(extra)] if extra else []) + dirs)

    def test_enforce_blocks_when_no_cli_can_be_run(self):
        scripts = self._scripts("enforce", name="no-cli", drop_cli=True)
        for provider, case in self._cases():
            with self.subTest(provider=provider):
                project = self.new_project("nocli-enforce-" + provider)
                result = self._run(scripts, case, project, env={"PATH": self._path_without_devteam()})
                self.assertEqual(result.returncode, BLOCKED, result.stderr)
                self.assertIn("blocked", result.stderr)
                self.assertFalse((project / case["written"]).exists())

    def test_warn_skips_with_a_note_when_no_cli_can_be_run(self):
        scripts = self._scripts("warn", name="no-cli-warn", drop_cli=True)
        for provider, case in self._cases():
            with self.subTest(provider=provider):
                project = self.new_project("nocli-warn-" + provider)
                result = self._run(scripts, case, project, env={"PATH": self._path_without_devteam()})
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("skipped", result.stderr)
                self.assertTrue((project / case["written"]).exists())

    def test_an_unexpected_cli_exit_code_blocks_under_enforce_and_skips_under_warn(self):
        fake = self.tmp / "fake-bin"
        fake.mkdir()
        (fake / "devteam").write_text("#!/bin/sh\nexit 7\n")
        (fake / "devteam").chmod(0o755)
        for mode, expected in (("enforce", BLOCKED), ("warn", 0)):
            scripts = self._scripts(mode, name="odd-" + mode, drop_cli=True)
            for provider, case in self._cases():
                with self.subTest(provider=provider, mode=mode):
                    project = self.new_project("odd-{}-{}".format(mode, provider))
                    result = self._run(
                        scripts, case, project, env={"PATH": self._path_without_devteam(fake)}
                    )
                    self.assertEqual(result.returncode, expected, result.stderr)
                    self.assertFalse((project / case["written"]).exists() and expected == BLOCKED)

    def test_install_provider_gates_before_running_the_installer(self):
        scripts = self._scripts("enforce", name="staging/scripts")
        staging = scripts.parent
        for provider, case in self._cases():
            with self.subTest(provider=provider):
                project = self.new_project("bootstrap-" + provider)
                name = case["script"].replace("install-", "").replace(".sh", "")
                result = subprocess.run(
                    ["bash", str(scripts / "install-provider.sh"), name, "--source", str(staging)],
                    cwd=str(project), env=dict(os.environ, HOME=str(self.fake_home)),
                    capture_output=True, text=True, timeout=120,
                )
                self.assertEqual(result.returncode, BLOCKED, result.stderr)
                self.assertFalse((project / case["written"]).exists())

    def test_update_gates_the_provider_rerender_but_not_the_core_update(self):
        script = (REPO_ROOT / "scripts" / "update.sh").read_text()
        self.assertIn('if ag_gate update "$SCRIPTS_DIR"; then\n    po_rerender_providers', script)
        self.assertLess(script.index('bash "$TMP_INSTALLER"'), script.index("ag_gate update"))
        scripts = self._scripts("enforce", name="update-copy")
        result = subprocess.run(
            ["bash", "-c", '. "$1/lib/auth-gate.sh"; ag_gate update "$1"', "_", str(scripts)],
            env=dict(os.environ, HOME=str(self.fake_home)), capture_output=True, text=True, timeout=60,
        )
        self.assertEqual(result.returncode, BLOCKED, result.stderr)

    def test_bind_is_gated_for_every_provider(self):
        for provider in providers.ALL_PROVIDERS:
            with self.subTest(provider=provider):
                project = self.new_project("bind-" + provider)
                with mock.patch.object(gate, "gate_mode", return_value="enforce"):
                    code, out, _err = self.run_inproc(
                        ["bind", str(project), "--provider", provider, "--json"]
                    )
                self.assertEqual(code, 1, out)
                self.assertFalse(json.loads(out)["ok"])
                self.assertFalse((project / ".dev-team-agents").exists())


@requires_bash()
class UpdateScriptGateTest(AuthTestCase):
    """`scripts/update.sh` end to end, with the download and the re-render stubbed at their seams."""

    def setUp(self):
        super().setUp()
        self.fake_home = self.tmp / "fake-home"
        self.fake_home.mkdir()

    def _install(self, mode, drop_cli=False):
        """A project with a copy of ``scripts/`` as its installed, unbound `.dev-team-agents/`."""
        root = self.tmp / "update-project-{}".format(mode + ("-nocli" if drop_cli else ""))
        scripts = root / ".dev-team-agents" / "scripts"
        shutil.copytree(REPO_ROOT / "scripts", scripts, ignore=shutil.ignore_patterns("__pycache__"))
        (scripts / "helpers" / "telemetry-send.sh").unlink()
        config = scripts / "lib" / "auth-config.json"
        data = json.loads(config.read_text())
        data["gate_mode"] = mode
        config.write_text(json.dumps(data))
        if drop_cli:
            shutil.rmtree(scripts / "cli")
        # The two seams: what the update downloads, and what re-renders the provider trees.
        (scripts / "lib" / "installer-fetch.sh").write_text(
            "dta_have_http_tool() { return 0; }\n"
            "dta_resolve_ref() { echo v9.9.9; }\n"
            "dta_fetch_installer() { printf 'echo CORE-UPDATED >> \"$MARKS\"\\n' > \"$1\"; }\n"
        )
        (scripts / "lib" / "provider-ownership.sh").write_text(
            "po_rerender_providers() { echo RERENDERED >> \"$MARKS\"; }\n"
        )
        return root, scripts

    def _update(self, root, scripts, path=None):
        marks = self.tmp / "marks-{}".format(root.name)
        env = dict(os.environ, HOME=str(self.fake_home), MARKS=str(marks))
        if path is not None:
            env["PATH"] = path
        result = subprocess.run(
            ["bash", str(scripts / "update.sh")], cwd=str(root), env=env,
            capture_output=True, text=True, timeout=120,
        )
        done = marks.read_text().split() if marks.exists() else []
        return result, done

    def test_enforce_updates_the_core_but_withholds_the_provider_re_render(self):
        root, scripts = self._install("enforce")
        result, done = self._update(root, scripts)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(done, ["CORE-UPDATED"])
        self.assertIn("NOT re-rendered", result.stderr)
        self.assertIn("devteam auth login", result.stderr)

    def test_warn_updates_and_re_renders_with_a_notice(self):
        root, scripts = self._install("warn")
        result, done = self._update(root, scripts)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(done, ["CORE-UPDATED", "RERENDERED"])
        self.assertIn("upcoming release", result.stderr)

    def test_an_entitled_account_re_renders_under_enforce(self):
        self.sign_in()
        root, scripts = self._install("enforce")
        result, done = self._update(root, scripts)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(done, ["CORE-UPDATED", "RERENDERED"])

    def test_enforce_with_no_cli_withholds_the_re_render(self):
        root, scripts = self._install("enforce", drop_cli=True)
        path = os.pathsep.join(
            d for d in os.environ.get("PATH", "").split(os.pathsep) if not (Path(d) / "devteam").exists()
        )
        result, done = self._update(root, scripts, path=path)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(done, ["CORE-UPDATED"])
        self.assertIn("NOT re-rendered", result.stderr)

    def test_warn_with_no_cli_notes_the_skip_and_re_renders(self):
        root, scripts = self._install("warn", drop_cli=True)
        path = os.pathsep.join(
            d for d in os.environ.get("PATH", "").split(os.pathsep) if not (Path(d) / "devteam").exists()
        )
        result, done = self._update(root, scripts, path=path)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(done, ["CORE-UPDATED", "RERENDERED"])
        self.assertIn("skipped", result.stderr)


if __name__ == "__main__":
    unittest.main()
