"""First-run onboarding (ADR-0030): `detect`, `doctor --machine`, `start` and the launch map."""

import json
import os
import re
import stat
import subprocess
import unittest
from pathlib import Path
from unittest import mock

from devteam_support import StoreTestCase, requires_shebangs

from devteam import detect, doctor, providers

#: One minimal project per row of `stack-signals.json`. The guard below fails the moment a
#: stack is added to the table without its own case.
STACK_FIXTURES = {
    "Python": {"pyproject.toml": "[project]\n", "app.py": "x = 1\n"},
    "TypeScript/Node.js": {"package.json": "{}", "tsconfig.json": "{}", "src/a.ts": "export {}\n"},
    "JavaScript/Node.js": {"package.json": "{}", "src/a.js": "1\n"},
    "Rust": {"Cargo.toml": "[package]\n", "src/main.rs": "fn main(){}\n"},
    "PHP": {"composer.json": "{}", "src/a.php": "<?php\n"},
    "Ruby": {"Gemfile": "source 'x'\n", "app/a.rb": "1\n"},
    "Go": {"go.mod": "module x\n", "main.go": "package main\n"},
    "Java": {"pom.xml": "<project/>\n", "src/A.java": "class A{}\n"},
    "Kotlin": {"build.gradle.kts": "\n", "src/a.kt": "fun a(){}\n"},
    "C#/.NET": {"app.csproj": "<Project/>\n", "Program.cs": "class P{}\n"},
    "Flutter/Dart": {"pubspec.yaml": "name: x\n", "lib/a.dart": "void main(){}\n"},
    "React Native": {"package.json": '{"dependencies":{"react-native":"1"}}', "src/a.tsx": "export {}\n"},
}

_ENV = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@e", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@e"}


def _git(root, *args):
    subprocess.run(
        ["git", *args], cwd=str(root), check=True, stdout=subprocess.DEVNULL,
        env=dict(os.environ, **_ENV),
    )


def _write(root, files):
    for rel, text in files.items():
        target = Path(root) / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")


def _make_repo(root, files, commits=1, tags=0, branch=None):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    _git(root, "init", "-q", "-b", "stem", ".")
    _write(root, files)
    _git(root, "add", "-A")
    _git(root, "commit", "-qm", "c1")
    for number in range(2, commits + 1):
        _git(root, "commit", "-q", "--allow-empty", "-m", "c{}".format(number))
    for number in range(tags):
        _git(root, "tag", "v0.{}.0".format(number))
    if branch:
        _git(root, "checkout", "-q", "-b", branch)
        _git(root, "commit", "-q", "--allow-empty", "-m", "work")
    return root


def _stub_dir(parent, versions):
    """A directory of executables that print a version; None means one that exits non-zero."""
    bin_dir = Path(parent) / "fakebin"
    bin_dir.mkdir()
    for name, version in versions.items():
        path = bin_dir / name
        body = "#!/bin/sh\necho '{}'\n".format(version) if version else "#!/bin/sh\nexit 1\n"
        path.write_text(body, encoding="utf-8")
        path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return bin_dir


class StackFixtureParityTest(unittest.TestCase):
    def test_every_stack_row_has_a_fixture_and_the_reverse(self):
        names = {stack["name"] for stack in json.loads(detect.STACK_SIGNALS_FILE.read_text())["stacks"]}
        self.assertEqual(names, set(STACK_FIXTURES))


class DetectStackTest(StoreTestCase):
    def test_each_stack_is_detected_from_its_signals(self):
        for name, files in STACK_FIXTURES.items():
            with self.subTest(stack=name):
                root = self.tmp / "stack-{}".format(re.sub(r"\W", "", name))
                _write(root, files)
                result = detect.detect_stack(root)
                self.assertIn(name, result["all"])
                self.assertTrue(result["signals"])

    def test_primary_is_the_stack_with_most_source_files(self):
        root = self.tmp / "multi"
        _write(root, {"package.json": "{}", "go.mod": "module x\n", "svc/a.go": "p\n", "svc/b.go": "p\n", "web/a.js": "1\n"})
        by_ext, _top, _tests = detect.scan_tree(root, {".go", ".js"})
        result = detect.detect_stack(root, by_ext=by_ext)
        self.assertEqual(result["primary"], "Go")
        self.assertEqual(set(result["all"]), {"Go", "JavaScript/Node.js"})

    def test_unknown_folder_has_no_stack(self):
        root = self.tmp / "plain"
        _write(root, {"notes.txt": "hi\n"})
        self.assertEqual(detect.detect_stack(root), {"primary": None, "all": [], "signals": []})


class DetectProjectTypeTest(StoreTestCase):
    def _run(self, **repo):
        root = _make_repo(self.tmp / "p", **repo)
        return detect.run(str(root))["project_type"]

    def test_empty_repository_is_new(self):
        root = self.tmp / "empty"
        root.mkdir()
        _git(root, "init", "-q", ".")
        kind = detect.run(str(root))["project_type"]
        self.assertEqual((kind["suggested"], kind["confidence"]), ("new", "high"))

    def test_few_commits_and_little_code_is_new(self):
        kind = self._run(files={"app.py": "x=1\n"}, commits=2)
        self.assertEqual((kind["suggested"], kind["confidence"]), ("new", "high"))

    def test_history_without_tests_ci_or_tags_is_unfinished(self):
        kind = self._run(files={"app.py": "x=1\n"}, commits=6)
        self.assertEqual((kind["suggested"], kind["confidence"]), ("unfinished", "high"))

    def test_history_with_tests_and_tags_is_maintenance(self):
        kind = self._run(files={"app.py": "x=1\n", "tests/test_a.py": "1\n"}, commits=12, tags=2)
        self.assertEqual((kind["suggested"], kind["confidence"]), ("maintenance", "high"))

    def test_conflicting_signals_lower_confidence(self):
        many = {"src/f{}.py".format(n): "x=1\n" for n in range(20)}
        kind = self._run(files=many, commits=2)
        self.assertEqual((kind["suggested"], kind["confidence"]), ("maintenance", "low"))

    def test_unsure_defaults_to_maintenance(self):
        kind = self._run(files={"app.py": "x=1\n", ".github/workflows/ci.yml": "on: push\n"}, commits=5)
        self.assertEqual((kind["suggested"], kind["confidence"]), ("maintenance", "low"))

    def test_override_wins_with_high_confidence(self):
        root = _make_repo(self.tmp / "o", files={"app.py": "x\n"}, commits=6)
        kind = detect.run(str(root), project_type="new")["project_type"]
        self.assertEqual((kind["suggested"], kind["confidence"]), ("new", "high"))


class DetectFirstTaskTest(StoreTestCase):
    def test_branch_ahead_of_base_suggests_review_of_that_branch(self):
        root = _make_repo(self.tmp / "r", files={"src/a.py": "x\n"}, commits=1, branch="feat/x")
        with mock.patch.object(detect, "default_branch", return_value="stem"):
            task = detect.run(str(root))["first_task"]
        self.assertEqual((task["kind"], task["target"]), ("review", "feat/x"))
        self.assertEqual(task["label"], "Review your last changes on feat/x")
        self.assertTrue(task["read_only"])

    def test_base_branch_is_detected_never_assumed(self):
        root = _make_repo(self.tmp / "b", files={"src/a.py": "x\n"})
        self.assertEqual(detect.default_branch(root), None)  # `stem` is not a conventional name
        _git(root, "config", "init.defaultBranch", "stem")
        self.assertEqual(detect.default_branch(root), "stem")

    def test_on_the_base_branch_audits_the_largest_source_directory(self):
        files = {"src/a.py": "x\n", "src/b.py": "x\n", "lib/c.py": "x\n", "node_modules/z/d.js": "x\n",
                 "docs/e.py": "x\n", "tests/test_a.py": "x\n"}
        root = _make_repo(self.tmp / "a", files=files)
        _git(root, "config", "init.defaultBranch", "stem")
        task = detect.run(str(root))["first_task"]
        self.assertEqual((task["kind"], task["target"], task["label"]), ("audit", "src", "Audit src/"))
        self.assertTrue(task["read_only"])

    def test_no_source_means_no_first_task(self):
        root = self.tmp / "none"
        _write(root, {"notes.txt": "x\n"})
        self.assertIsNone(detect.run(str(root))["first_task"])

    def test_launch_comes_from_the_suggested_provider(self):
        root = _make_repo(self.tmp / "l", files={"src/a.py": "x\n"})
        task = detect.run(str(root), provider="codex")["first_task"]
        self.assertEqual(task["launch"]["provider"], "codex")
        self.assertEqual(task["launch"]["argv"][:3], ["codex", "--sandbox", "read-only"])
        self.assertIn("--report-only", task["launch"]["argv"][-1])


@requires_shebangs
class DetectProvidersTest(StoreTestCase):
    def _providers(self, stubs, project_dirs=()):
        root = self.tmp / "proj"
        for rel in project_dirs:
            (root / rel).mkdir(parents=True)
        root.mkdir(exist_ok=True)
        bin_dir = _stub_dir(self.tmp, stubs)
        with mock.patch.dict(os.environ, {"PATH": str(bin_dir)}):
            return detect.detect_providers(root)

    def test_installed_providers_report_binary_and_version_in_all_providers_order(self):
        info = self._providers({"codex": "codex 9.1", "claude": "claude 2.0"})
        self.assertEqual([p["name"] for p in info["installed"]], ["claude", "codex"])
        self.assertEqual(info["installed"][0], {"name": "claude", "binary": "claude", "version": "claude 2.0"})

    def test_a_binary_that_does_not_answer_has_a_null_version(self):
        info = self._providers({"opencode": None})
        self.assertEqual(info["installed"], [{"name": "opencode", "binary": "opencode", "version": None}])

    def test_suggested_prefers_a_provider_both_installed_and_in_the_project(self):
        info = self._providers({"claude": "1", "codex": "2"}, project_dirs=[".codex"])
        self.assertEqual((info["in_project"], info["suggested"]), (["codex"], "codex"))

    def test_suggested_falls_back_to_the_first_installed(self):
        info = self._providers({"opencode": "1", "codex": "2"}, project_dirs=[".claude"])
        self.assertEqual((info["in_project"], info["suggested"]), (["claude"], "opencode"))

    def test_nothing_installed_suggests_nothing_and_has_no_claude_fallback(self):
        info = self._providers({})
        self.assertEqual(info, {"installed": [], "in_project": [], "suggested": None})

    def test_in_project_has_no_claude_fallback_but_detect_keeps_it(self):
        root = self.tmp / "bare"
        root.mkdir()
        self.assertEqual(providers.detect_in_project(root), [])
        self.assertEqual(providers.detect(root), ["claude"])


class DoctorMachineTest(unittest.TestCase):
    def _findings(self, platform, present=(), versions=None, python=(3, 12, 0)):
        versions = versions if versions is not None else {name: "v1" for name in present}
        return doctor.check_prerequisites(
            platform=platform,
            which=lambda name: "/bin/" + name if name in present else None,
            version_of=lambda name: versions.get(name),
            python_version=python,
        )

    def _by(self, findings, category, contains=""):
        return next(f for f in findings if f["category"] == category and contains in f["message"])

    def test_every_finding_carries_fix_and_auto_fixable(self):
        for item in self._findings("linux"):
            self.assertIn("fix", item)
            self.assertIsInstance(item["auto_fixable"], bool)

    def test_healthy_machine_is_ok_without_fixes(self):
        result = self._findings("darwin", present=("git", "claude"))
        self.assertEqual(self._by(result, "git")["level"], "ok")
        self.assertEqual(self._by(result, "python")["level"], "ok")
        self.assertEqual(self._by(result, "provider", "claude")["level"], "ok")

    def test_missing_git_fix_per_os(self):
        cases = {
            "darwin": ((), "xcode-select --install", True),
            "win32": (("winget",), "winget install Git.Git", True),
            "linux": (("apt-get",), "sudo apt-get install -y git", False),
        }
        for platform, (present, fix, auto) in cases.items():
            with self.subTest(platform=platform):
                item = self._by(self._findings(platform, present=present), "git")
                self.assertEqual((item["level"], item["fix"], item["auto_fixable"]), ("fail", fix, auto))
        brew = self._by(self._findings("darwin", present=("brew",)), "git")
        self.assertEqual((brew["fix"], brew["auto_fixable"]), ("brew install git", True))

    def test_old_python_fails_with_a_fix(self):
        item = self._by(self._findings("win32", present=("git", "winget"), python=(3, 8, 10)), "python")
        self.assertEqual((item["level"], item["fix"], item["auto_fixable"]), ("fail", "winget install Python.Python.3.12", True))

    def test_providers_are_never_auto_fixable_and_carry_their_install_command(self):
        result = self._findings("darwin", present=("git", "brew"))
        for name in providers.ALL_PROVIDERS:
            item = self._by(result, "provider", name)
            self.assertEqual(item["level"], "warn")
            self.assertFalse(item["auto_fixable"])
            self.assertEqual(item["fix"], doctor.PROVIDER_INSTALL[name])

    def test_no_provider_at_all_fails(self):
        result = self._findings("linux", present=("git",))
        self.assertTrue(any(f["level"] == "fail" and f["category"] == "provider" for f in result))

    def test_provider_without_a_version_is_a_warning(self):
        result = self._findings("linux", present=("git", "codex"), versions={"git": "g"})
        self.assertEqual(self._by(result, "provider", "codex")["level"], "warn")

    def test_provider_install_commands_cover_all_providers(self):
        self.assertEqual(set(doctor.PROVIDER_INSTALL), set(providers.ALL_PROVIDERS))

    def test_run_machine_document_shape(self):
        document = doctor.run_machine(
            platform="linux", which=lambda n: None, version_of=lambda n: None, python_version=(3, 12, 0)
        )
        self.assertEqual(set(document), {"status", "findings", "actions", "credentials_local"})
        self.assertEqual(document["status"], "fail")


class DoctorMachineCliTest(StoreTestCase):
    def test_machine_flag_reports_prerequisites_without_a_store(self):
        code, out, _err = self.run_cli("doctor", "--machine", "--json")
        payload = json.loads(out)
        self.assertIn(code, (0, 1))
        self.assertEqual({f["category"] for f in payload["findings"]} - {"provider"}, {"git", "python"})
        self.assertTrue(all("fix" in f and "auto_fixable" in f for f in payload["findings"]))
        self.assertEqual(payload["actions"], [])


class FirstTaskMapTest(unittest.TestCase):
    #: Per provider: the first argv element and the read-only flag the provider enforces.
    EXPECTED = {
        "claude": ("claude", ["--permission-mode", "plan"]),
        "codex": ("codex", ["--sandbox", "read-only"]),
        "opencode": ("opencode", ["--agent", "plan"]),
    }

    def setUp(self):
        self.table = json.loads(detect.FIRST_TASK_FILE.read_text())

    def test_every_provider_has_a_case_and_a_map_entry(self):
        self.assertEqual(set(providers.ALL_PROVIDERS), set(self.EXPECTED))
        self.assertEqual(set(providers.ALL_PROVIDERS), set(self.table["providers"]))

    def test_launch_is_an_argv_array_enforcing_read_only_through_the_provider(self):
        for provider in providers.ALL_PROVIDERS:
            for kind in ("audit", "review"):
                with self.subTest(provider=provider, kind=kind):
                    binary, flags = self.EXPECTED[provider]
                    launch = detect.launch_for(provider, kind, "src", self.table)
                    argv = launch["argv"]
                    self.assertEqual(launch["provider"], provider)
                    self.assertIsInstance(argv, list)
                    self.assertEqual(argv[0], binary)
                    self.assertEqual(argv[1:1 + len(flags)], flags)
                    self.assertNotIn("{prompt}", " ".join(argv))
                    self.assertIn("src", argv[-1])

    def test_audit_requests_report_only_and_review_does_not(self):
        for provider in providers.ALL_PROVIDERS:
            audit = detect.launch_for(provider, "audit", "src", self.table)["argv"][-1]
            review = detect.launch_for(provider, "review", "feat/x", self.table)["argv"][-1]
            self.assertIn("--report-only", audit)
            self.assertNotIn("--report-only", review)

    def test_command_naming_per_provider(self):
        self.assertEqual(
            detect.launch_for("claude", "audit", "src", self.table)["argv"][-1], "/devteam:audit src --report-only"
        )
        self.assertEqual(
            detect.launch_for("codex", "review", "b", self.table)["argv"][-1], "$devteam-review b"
        )

    def test_a_provider_without_a_read_only_mode_has_no_launch(self):
        table = {"kinds": {}, "providers": {"claude": None, "_why": "no read-only mode"}}
        self.assertIsNone(detect.launch_for("claude", "audit", "src", table))

    def test_audit_command_documents_the_flag(self):
        body = (detect.LIB_DIR.parent.parent / "commands" / "audit.md").read_text(encoding="utf-8")
        self.assertIn("--report-only", body)


class StartCliTest(StoreTestCase):
    def setUp(self):
        super().setUp()
        self.install_version("3.0.0", activate=True)

    def test_start_sets_the_project_up_and_returns_the_first_task(self):
        root = _make_repo(self.tmp / "app2", files={"src/a.py": "x\n", "pyproject.toml": "[p]\n"})
        code, out, err = self.run_cli("start", "--path", str(root), "--provider", "claude", "--json")
        self.assertEqual(code, 0, err)
        payload = json.loads(out)
        self.assertTrue(payload["bound"])
        self.assertTrue(payload["project_id"])
        self.assertEqual(payload["detect"]["stack"]["primary"], "Python")
        self.assertEqual(payload["first_task"], payload["detect"]["first_task"])
        self.assertEqual(payload["first_task"]["kind"], "audit")
        self.assertEqual(set(payload["featured_commands"]), {"plan", "fix", "review", "commit", "pr"})
        self.assertTrue((root / ".dev-team-agents" / "project.json").is_file())

    def test_start_human_output_hides_internal_vocabulary(self):
        root = _make_repo(self.tmp / "app3", files={"src/a.py": "x\n"})
        code, out, err = self.run_cli("start", "--path", str(root), "--provider", "claude")
        self.assertEqual(code, 0, err)
        self.assertTrue(out.startswith("Project ready. Start with one of these:"))
        for word in ("bind", "layout", "store", "preference"):
            self.assertNotIn(word, out.lower())

    def test_start_is_idempotent(self):
        root = _make_repo(self.tmp / "app4", files={"src/a.py": "x\n"})
        first = json.loads(self.run_cli("start", "--path", str(root), "--provider", "claude", "--json")[1])
        second = json.loads(self.run_cli("start", "--path", str(root), "--provider", "claude", "--json")[1])
        self.assertEqual(first["project_id"], second["project_id"])

    def test_detect_cli_writes_nothing(self):
        root = _make_repo(self.tmp / "app5", files={"src/a.py": "x\n"})
        before = sorted(p.name for p in root.iterdir())
        code, out, _err = self.run_cli("detect", "--path", str(root), "--json")
        self.assertEqual(code, 0)
        self.assertEqual(
            set(json.loads(out)), {"ok", "path", "providers", "stack", "project_type", "first_task"}
        )
        self.assertEqual(sorted(p.name for p in root.iterdir()), before)


if __name__ == "__main__":
    unittest.main()
