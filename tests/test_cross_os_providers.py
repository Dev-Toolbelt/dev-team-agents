"""Cross-OS and per-provider guards: UTF-8 render, containment, doctor, unbind, roots."""

import json
import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

from devteam_support import REPO_ROOT, StoreTestCase, requires_bash

from devteam import bind, doctor, global_skills, providers, tasks, versions
from devteam.errors import ConflictError

#: One entry per provider in `providers.ALL_PROVIDERS`; the parity guard fails when
#: a provider is added without a case. Delegated providers' redirectable directory:
DELEGATED_DIR = {"claude": None, "opencode": ".opencode", "codex": ".codex"}
#: A file that must exist for the provider's hook wiring to be healthy, and the
#: doctor message fragment when it does not (None: covered by the claude branch).
HOOK_WARNING = {"claude": "not registered", "opencode": "plugin missing", "codex": "not wired"}


def _needs(provider):
    need = {"opencode": ("bash", "python3", "jq"), "codex": ("bash", "python3")}.get(provider, ())
    return [t for t in need if shutil.which(t) is None]


class ParityTest(unittest.TestCase):
    def test_every_provider_has_a_case(self):
        self.assertEqual(set(DELEGATED_DIR), set(providers.ALL_PROVIDERS))
        self.assertEqual(set(HOOK_WARNING), set(providers.ALL_PROVIDERS))


class RenderEncodingTest(unittest.TestCase):
    def test_render_under_cp1252_emits_utf8_with_lf(self):
        import tempfile

        out = Path(tempfile.mkdtemp(prefix="devteam-render-"))
        self.addCleanup(shutil.rmtree, str(out), True)
        env = dict(os.environ, PYTHONUTF8="0", PYTHONIOENCODING="cp1252", LC_ALL="C", LANG="C")
        probe = (
            "import locale,sys\n"
            "locale.getpreferredencoding = lambda do_setlocale=True: 'cp1252'\n"
            "sys.argv = ['render_provider.py'] + sys.argv[1:]\n"
            "import runpy; runpy.run_path(%r, run_name='__main__')\n"
            % str(REPO_ROOT / "scripts" / "lib" / "render_provider.py")
        )
        for provider in providers.ALL_PROVIDERS:
            if provider == "claude":
                continue
            with self.subTest(provider=provider):
                target = out / provider
                result = subprocess.run(
                    [sys.executable, "-c", probe, "--provider", provider, "--source", str(REPO_ROOT),
                     "--target", str(target)],
                    env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
                )
                self.assertEqual(result.returncode, 0, result.stderr.decode("utf-8", "replace"))
                files = [f for f in target.rglob("*") if f.is_file()]
                self.assertTrue(files)
                for f in files:
                    raw = f.read_bytes()
                    raw.decode("utf-8")
                    self.assertNotIn(b"\r\n", raw, str(f))


class EnvPassthroughTest(unittest.TestCase):
    def test_windows_variables_are_passed_through(self):
        with mock.patch.dict(os.environ, {"SYSTEMROOT": "C:\\Windows", "TEMP": "C:\\T", "PYTHONUTF8": "1"}):
            env = providers._installer_env()
        for key in ("SYSTEMROOT", "TEMP", "PYTHONUTF8"):
            self.assertIn(key, env)
        self.assertNotIn("SOME_UNRELATED_SECRET", env)


@requires_bash()
class ProviderGuardsTest(StoreTestCase):
    def setUp(self):
        super().setUp()
        versions.install_from_tree(REPO_ROOT, version="9.9.9", force=True, make_current=True)
        self._home = os.environ.get("HOME")
        self.fake_home = self.tmp / "fake-home"
        self.fake_home.mkdir()
        os.environ["HOME"] = str(self.fake_home)
        self.addCleanup(self._restore_home)

    def _restore_home(self):
        if self._home is None:
            os.environ.pop("HOME", None)
        else:
            os.environ["HOME"] = self._home

    def _each(self):
        for provider in providers.ALL_PROVIDERS:
            missing = _needs(provider)
            if missing:
                self.skipTest("{} needs {}".format(provider, ", ".join(missing)))
            yield provider

    def test_bind_refuses_a_symlinked_target_dir_per_delegated_provider(self):
        for provider in self._each():
            dirname = DELEGATED_DIR[provider]
            if dirname is None:
                continue
            with self.subTest(provider=provider):
                root = self.new_project("sym-" + provider)
                outside = self.tmp / ("outside-" + provider)
                outside.mkdir()
                (root / dirname).symlink_to(outside, target_is_directory=True)
                with self.assertRaises(ConflictError):
                    bind.bind(root, provider_names=[provider])
                self.assertEqual(list(outside.iterdir()), [])

    def test_doctor_checks_hook_wiring_for_each_bound_provider(self):
        for provider in self._each():
            with self.subTest(provider=provider):
                root = self.new_project("doc-" + provider)
                bind.bind(root, provider_names=[provider])
                hooks_findings = [f for f in doctor.run(project_root=root)["findings"] if f["category"] == "hooks"]
                self.assertTrue(hooks_findings)
                self.assertTrue(all(f["level"] == "ok" for f in hooks_findings), hooks_findings)
                # Break the wiring, doctor warns; the advertised remedy clears it.
                broken = {
                    "claude": root / ".claude" / "settings.json",
                    "opencode": root / providers.OPENCODE_PLUGIN_FILE,
                    "codex": root / providers.CODEX_HOOKS_FILE,
                }[provider]
                broken.unlink()
                warned = [f for f in doctor.run(project_root=root)["findings"]
                          if f["category"] == "hooks" and f["level"] == "warn"]
                self.assertTrue(warned)
                self.assertIn(HOOK_WARNING[provider], warned[0]["message"])
                bind.sync_project(bind.project.load(root)["project_id"])
                after = [f for f in doctor.run(project_root=root)["findings"]
                         if f["category"] == "hooks" and f["level"] == "warn"]
                self.assertEqual(after, [])

    def test_doctor_is_silent_about_a_provider_that_is_not_bound(self):
        for provider in self._each():
            with self.subTest(provider=provider):
                root = self.new_project("only-" + provider)
                bind.bind(root, provider_names=[provider])
                text = json.dumps(doctor.run(project_root=root)["findings"])
                for other in providers.ALL_PROVIDERS:
                    if other != provider:
                        self.assertNotIn({"opencode": "opencode plugin", "codex": "Codex hook", "claude": "settings.json"}[other], text)

    def test_unbind_removes_only_devteam_command_keys_from_opencode_json(self):
        if _needs("opencode"):
            self.skipTest("opencode needs bash, python3, jq")
        root = self.new_project("oc")
        (root / ".opencode").mkdir()
        cfg = root / ".opencode" / "opencode.json"
        cfg.write_text(json.dumps({"theme": "x", "command": {"mine": {"template": "t"}}}), encoding="utf-8")
        bind.bind(root, provider_names=["opencode"])
        merged = json.loads(cfg.read_text(encoding="utf-8"))
        self.assertTrue(any(k.startswith("devteam:") for k in merged["command"]))
        bind.unbind(root)
        left = json.loads(cfg.read_text(encoding="utf-8"))
        self.assertEqual(left, {"theme": "x", "command": {"mine": {"template": "t"}}})

    def test_unbind_leaves_unparseable_opencode_config_untouched(self):
        root = self.new_project("occ")
        cfg = root / "opencode.json"
        text = '{ // keep\n "command": {"devteam:x": {},}\n}\n'
        cfg.write_text(text, encoding="utf-8")
        removed, untouched = providers.unwire_opencode_commands(root)
        self.assertEqual((removed, untouched), (0, ["opencode.json"]))
        self.assertEqual(cfg.read_text(encoding="utf-8"), text)


class RootsTest(StoreTestCase):
    def setUp(self):
        super().setUp()
        for name in ("CODEX_HOME", "XDG_CONFIG_HOME"):
            saved = os.environ.pop(name, None)
            if saved is not None:
                self.addCleanup(os.environ.__setitem__, name, saved)

    def _paths(self):
        roots, _ = global_skills.load_roots()
        return {r["id"]: r["path"] for r in roots}

    def test_defaults_fall_back_to_home(self):
        found = self._paths()
        self.assertEqual(found["codex"], self.user_home / ".codex" / "skills")
        self.assertEqual(found["opencode"], self.user_home / ".config" / "opencode" / "skills")

    def test_codex_home_and_xdg_config_home_win_over_the_home_directory(self):
        env = {"CODEX_HOME": str(self.tmp / "ch"), "XDG_CONFIG_HOME": str(self.tmp / "xdg")}
        with mock.patch.dict(os.environ, env):
            os.environ.pop(global_skills.USER_HOME_ENV, None)
            found = self._paths()
        self.assertEqual(found["codex"], self.tmp / "ch" / "skills")
        self.assertEqual(found["opencode"], self.tmp / "xdg" / "opencode" / "skills")

    def test_an_explicit_user_home_relocates_every_root(self):
        env = {"CODEX_HOME": str(self.tmp / "ch"), "XDG_CONFIG_HOME": str(self.tmp / "xdg")}
        with mock.patch.dict(os.environ, env):
            found = self._paths()
        self.assertEqual(found["codex"], self.user_home / ".codex" / "skills")
        self.assertEqual(found["opencode"], self.user_home / ".config" / "opencode" / "skills")
        self.assertEqual(found["claude"], self.user_home / ".claude" / "skills")


class ResumeCommandTest(unittest.TestCase):
    def test_windows_form_is_powershell_safe(self):
        with mock.patch.object(tasks.os, "name", "nt"), mock.patch.object(tasks.os.path, "isdir", return_value=True):
            cmd = tasks.resume_command("C:\\a", "claude", "abc-1", cwd="C:\\it's here")
        self.assertEqual(cmd, "Set-Location -LiteralPath 'C:\\it''s here'; claude --resume abc-1")
        self.assertNotIn("&&", cmd)

    def test_posix_form_is_unchanged(self):
        with mock.patch.object(tasks.os, "name", "posix"):
            cmd = tasks.resume_command("/tmp", "claude", "abc-1")
        self.assertTrue(cmd.startswith("cd /tmp && claude --resume "))


if __name__ == "__main__":
    unittest.main()
