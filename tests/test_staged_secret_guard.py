"""`03b-staged-secret-guard.sh` refuses a commit that carries a secret, for every provider (ADR-0059).

gitleaks is replaced by a shim on PATH, so the suite needs no real scanner and the cases are
exact: the shim reports a finding, reports nothing, or crashes, and records how it was called.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from devteam_support import REPO_ROOT, requires_bash
from devteam.providers import ALL_PROVIDERS

GUARD = REPO_ROOT / "scripts" / "hooks" / "pre-tool-use" / "03b-staged-secret-guard.sh"
SECRET = "FAKE-SECRET-VALUE-NEVER-PRINTED"

SHIM = """#!/bin/sh
echo "${GIT_INDEX_FILE:+[index] }$*" >> "$SHIM_LOG"
case "${SHIM_MODE:-clean}" in
  crash) exit 1 ;;
  clean) exit 0 ;;
esac
report=""
prev=""
for arg in "$@"; do
  [ "$prev" = "--report-path" ] && report="$arg"
  prev="$arg"
done
printf '[{"File":"config/app.py","StartLine":7,"RuleID":"generic-api-key","Secret":"%s"}]' "$SHIM_SECRET" > "$report"
exit 3
"""


def _payload(provider, command):
    """The shell call as each provider's hook (or, for opencode, its plugin) spells it."""
    return {
        "claude": {"session_id": "s1", "tool_name": "Bash", "tool_input": {"command": command, "description": "x"}},
        "codex": {"session_id": "s1", "tool_name": "Bash", "tool_input": {"command": command}},
        "codex-exec": {"session_id": "s1", "tool_name": "exec_command",
                       "tool_input": {"cmd": ["bash", "-lc", command]}},
        "opencode": {"sessionID": "s1", "tool": "bash", "args": {"command": command}},
    }[provider]


#: Payload spellings per provider; a provider added to ALL_PROVIDERS without one fails below.
PROVIDER_PAYLOADS = {"claude": ["claude"], "codex": ["codex", "codex-exec"], "opencode": ["opencode"]}
SHAPES = sorted(shape for shapes in PROVIDER_PAYLOADS.values() for shape in shapes)


@requires_bash()
class StagedSecretGuardTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.repo = self.tmp / "repo"
        self.repo.mkdir()
        self.shim_dir = self.tmp / "shim"
        self.shim_dir.mkdir()
        self.log = self.tmp / "shim.log"
        # git is linked in rather than its directory put on PATH: Homebrew's bin holds a real
        # gitleaks next to git, which would turn the no-gitleaks case into a real scan.
        (self.shim_dir / "git").symlink_to(shutil.which("git"))
        self.env = {
            "PATH": os.pathsep.join([str(self.shim_dir), "/usr/bin", "/bin"]),
            "HOME": str(self.tmp / "home"),
            "TMPDIR": str(self.tmp),
            "SHIM_LOG": str(self.log),
            "SHIM_SECRET": SECRET,
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_SYSTEM": os.devnull,
        }
        subprocess.run(["git", "init", "-q"], cwd=self.repo, env=self.env, check=True)

    def install_shim(self):
        shim = self.shim_dir / "gitleaks"
        shim.write_text(SHIM)
        shim.chmod(0o755)

    def run_guard(self, provider, command, mode="clean"):
        env = dict(self.env, SHIM_MODE=mode)
        return subprocess.run(
            ["bash", str(GUARD)], input=json.dumps(_payload(provider, command)), cwd=self.repo,
            env=env, capture_output=True, text=True, timeout=60,
        )

    def calls(self):
        return self.log.read_text().splitlines() if self.log.exists() else []

    def test_every_provider_has_a_payload(self):
        self.assertEqual(set(PROVIDER_PAYLOADS), set(ALL_PROVIDERS))

    def test_a_finding_refuses_the_commit_without_printing_the_value(self):
        self.install_shim()
        for provider in SHAPES:
            with self.subTest(provider=provider):
                result = self.run_guard(provider, 'git add . && git commit -m "wip"', mode="leak")
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertIn("config/app.py:7", result.stderr)
                self.assertIn("generic-api-key", result.stderr)
                self.assertNotIn(SECRET, result.stderr + result.stdout)
                self.assertEqual(result.stdout, "")

    def test_a_clean_scan_allows_the_commit(self):
        self.install_shim()
        for provider in SHAPES:
            with self.subTest(provider=provider):
                self.assertEqual(self.run_guard(provider, "git commit -m ok").returncode, 0)

    def test_the_scan_is_staged_and_redacted(self):
        self.install_shim()
        self.run_guard("claude", "git commit -m ok")
        (call,) = self.calls()
        for flag in ("git", "--pre-commit", "--staged", "--redact"):
            self.assertIn(flag, call.split())

    def test_commit_all_scans_a_copy_of_the_index_with_the_add_applied(self):
        self.install_shim()
        self.run_guard("claude", "git commit -am ok")
        (call,) = self.calls()
        self.assertTrue(call.startswith("[index] "), call)
        self.assertIn("--staged", call.split())

    def test_a_command_that_is_not_a_commit_never_runs_the_scanner(self):
        self.install_shim()
        for command in ("git status", "echo 'remember to commit'", "git log --grep commit", "gitcommit"):
            with self.subTest(command=command):
                self.assertEqual(self.run_guard("claude", command, mode="leak").returncode, 0)
        self.assertEqual(self.calls(), [])

    def test_git_dash_c_and_a_multiline_command_are_recognised(self):
        self.install_shim()
        self.assertEqual(self.run_guard("codex", "git -C . commit -m x", mode="leak").returncode, 2)
        self.assertEqual(self.run_guard("claude", "git add a\ngit commit -m x", mode="leak").returncode, 2)

    def test_global_git_options_before_commit_are_recognised(self):
        self.install_shim()
        for command in ("git --no-pager commit -m x", "git --git-dir=.git commit -m x", "git --git-dir .git commit -m x",
                        "git -p commit -m x"):
            with self.subTest(command=command):
                self.assertEqual(self.run_guard("claude", command, mode="leak").returncode, 2)

    def test_a_glued_commit_all_flag_still_applies_the_add(self):
        self.install_shim()
        self.run_guard("claude", 'git commit -am"wip"')
        (call,) = self.calls()
        self.assertTrue(call.startswith("[index] "), call)

    def test_a_scanner_crash_allows_the_commit(self):
        self.install_shim()
        self.assertEqual(self.run_guard("claude", "git commit -m ok", mode="crash").returncode, 0)

    def test_without_gitleaks_the_commit_is_allowed(self):
        for provider in SHAPES:
            with self.subTest(provider=provider):
                result = self.run_guard(provider, "git commit -m ok", mode="leak")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, "")

    def test_a_non_shell_tool_is_ignored(self):
        self.install_shim()
        payload = {"tool_name": "Edit", "tool_input": {"file_path": "x", "new_string": "git commit"}}
        result = subprocess.run(
            ["bash", str(GUARD)], input=json.dumps(payload), cwd=self.repo,
            env=dict(self.env, SHIM_MODE="leak"), capture_output=True, text=True, timeout=60,
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(self.calls(), [])


@requires_bash()
@unittest.skipUnless(shutil.which("gitleaks"), "needs the real gitleaks")
class RealGitleaksTest(unittest.TestCase):
    """The cases a shim cannot prove: what gitleaks actually sees before the command runs."""

    def setUp(self):
        self.repo = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.repo, True)
        self.env = dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_SYSTEM=os.devnull,
                        GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@e", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@e")
        for argv in (["git", "init", "-q"], ["git", "commit", "-q", "--allow-empty", "-m", "init"]):
            subprocess.run(argv, cwd=self.repo, env=self.env, check=True)
        # Built at runtime so no real-looking token is ever committed in this file.
        (self.repo / "settings.py").write_text('TOKEN = "ghp_' + "A1b2C3d4E5f6G7h8I9j0" + 'K1l2M3n4O5p6Q7r8"\n')

    def run_guard(self, command):
        return subprocess.run(
            ["bash", str(GUARD)], input=json.dumps(_payload("claude", command)), cwd=self.repo,
            env=self.env, capture_output=True, text=True, timeout=120,
        )

    def test_add_and_commit_in_one_command_is_scanned(self):
        # Nothing is staged yet when the hook runs; the file the add will stage must still count.
        result = self.run_guard("git add settings.py && git commit -m wip")
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("settings.py", result.stderr)

    def test_more_than_a_hundred_new_files_are_all_scanned(self):
        for index in range(120):
            (self.repo / "clean_{}.txt".format(index)).write_text("nothing here\n")
        result = self.run_guard("git add . && git commit -m wip")
        self.assertEqual(result.returncode, 2, result.stderr)

    def test_the_staged_version_is_scanned_when_suppressions_change(self):
        subprocess.run(["git", "add", "settings.py"], cwd=self.repo, env=self.env, check=True)
        (self.repo / ".gitleaksignore").write_text("unrelated\n")
        subprocess.run(["git", "add", ".gitleaksignore"], cwd=self.repo, env=self.env, check=True)
        (self.repo / "settings.py").write_text("TOKEN = None\n")  # clean copy; the secret stays staged
        result = self.run_guard("git commit -m wip")
        self.assertEqual(result.returncode, 2, result.stderr)

    def test_the_real_index_is_untouched(self):
        self.run_guard("git add . && git commit -m wip")
        staged = subprocess.run(["git", "diff", "--cached", "--name-only"], cwd=self.repo, env=self.env,
                                capture_output=True, text=True).stdout
        self.assertEqual(staged, "")

    def test_a_suppression_added_with_the_secret_is_not_honoured(self):
        subprocess.run(["git", "add", "settings.py"], cwd=self.repo, env=self.env, check=True)
        fingerprints = subprocess.run(
            ["gitleaks", "git", "--pre-commit", "--staged", "--redact", "--no-banner",
             "--report-format", "json", "--report-path", "-", "."],
            cwd=self.repo, env=self.env, capture_output=True, text=True,
        ).stdout
        (self.repo / ".gitleaksignore").write_text(
            "\n".join(f["Fingerprint"] for f in json.loads(fingerprints or "[]")) + "\n")
        subprocess.run(["git", "add", ".gitleaksignore"], cwd=self.repo, env=self.env, check=True)
        result = self.run_guard("git commit -m wip")
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("were not applied", result.stderr)
