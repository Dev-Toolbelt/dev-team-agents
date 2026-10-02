"""PreToolUse dispatcher and the full-suite guard.

Dispatcher: a sub-script that exits without reading stdin must not mask a later
sub-script's exit 2 block, whatever the payload size (a pipe-fed payload larger
than the pipe buffer used to kill the writer with SIGPIPE, exit 141).

Guard: a runner name only counts when it is the command being invoked, and a
scoped run is not a full run.
"""

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from devteam_support import REPO_ROOT, requires_bash

HOOKS = REPO_ROOT / "scripts" / "hooks"
GUARD = HOOKS / "pre-tool-use" / "02c-full-suite-guard.sh"
DISPATCHERS = ("pre-tool-use", "post-tool-use", "user-prompt-submit")


@requires_bash()
class DispatcherExitPrecedenceTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def run_dispatcher(self, name, early_body, payload):
        self.n = getattr(self, "n", 0) + 1
        root = self.tmp / f"{name}-{self.n}"
        (root / name).mkdir(parents=True)
        shutil.copy(HOOKS / f"{name}.sh", root / f"{name}.sh")
        (root / name / "01-early.sh").write_text("#!/usr/bin/env bash\n" + early_body)
        (root / name / "02-block.sh").write_text(
            '#!/usr/bin/env bash\nwc -c > "$0.size"\nexit 2\n'
        )
        result = subprocess.run(
            ["bash", str(root / f"{name}.sh")], input=payload, capture_output=True, text=True
        )
        size = int((root / name / "02-block.sh.size").read_text().strip())
        return result, size

    def test_early_exit_script_does_not_mask_a_block_on_a_large_payload(self):
        payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": "x" * 300_000}})
        for name in DISPATCHERS:
            for early in ("exit 0\n", "exit 1\n"):
                with self.subTest(dispatcher=name, early=early.strip()):
                    result, size = self.run_dispatcher(name, early, payload)
                    self.assertEqual(result.returncode, 2, result.stderr)
                    self.assertGreaterEqual(size, 300_000)

    def test_exit_two_wins_over_an_earlier_other_nonzero_exit(self):
        result, _ = self.run_dispatcher("pre-tool-use", "cat >/dev/null\nexit 3\n", '{"a":1}')
        self.assertEqual(result.returncode, 2)


@requires_bash()
class FullSuiteGuardTest(unittest.TestCase):
    BLOCKED = [
        "npm test",
        "pnpm test",
        "yarn test",
        "bun test",
        "npm run test:unit",
        "pnpm test:run",
        "jest",
        "npx jest --coverage",
        "vitest run",
        "pytest",
        "python -m pytest -q",
        "poetry run pytest",
        "vendor/bin/phpunit",
        "php artisan test",
        "bundle exec rspec",
        "go test ./...",
        "./gradlew test",
        "flutter test",
        "cargo test",
        "make test",
        "make -j4 test-e2e",
        "composer test",
        "composer test:unit",
        "cd app && npm test",
        "cd app && DEVTEAM_FULL_SUITE_CONFIRMED_NOT=1 npm test",
        "FOO=1 npm test",
        "true; pytest",
        "false || jest",
        "docker exec app sh -c 'pnpm test:run'",
        "docker compose exec -T app pnpm test",
        'bash -c "npm test"',
        "exec pytest",
        "echo hi | pytest",
    ]
    ALLOWED = [
        "cat jest.config.js",
        "grep -rn pytest pyproject.toml",
        "git log --grep=jest",
        "ls tests",
        "cmake --build . && ./run_tests",
        "make build",
        "composer test tests/Unit/FooTest.php",
        "composer test -- --filter Foo",
        "composer test:unit --filter Foo",
        "npm test -- foo",
        "npm test src/foo.test.ts",
        "pnpm test --filter web",
        "jest src/foo.test.ts",
        "jest --findRelatedTests src/a.ts",
        "vitest run src/foo.spec.ts",
        "pytest tests/unit/test_foo.py",
        "pytest tests/unit",
        "pytest -k foo",
        "vendor/bin/phpunit --filter Foo",
        "vendor/bin/phpunit tests/Unit/FooTest.php",
        "go test ./pkg/foo/...",
        "go test -run Foo ./...",
        "./gradlew test --tests com.x.FooTest",
        "flutter test test/foo_test.dart",
        "cargo test foo",
        "make test TESTPATH=tests/unit",
        "bundle exec rspec spec/foo_spec.rb:12",
        "echo npm test",
        "cd x && DEVTEAM_FULL_SUITE_CONFIRMED=1 npm test",
        "DEVTEAM_FULL_SUITE_CONFIRMED=1 npm test",
    ]

    def setUp(self):
        # An empty repo: nothing touched, so a full run is blocked, not nudged.
        self.repo = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.repo, ignore_errors=True)
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)

    def run_guard(self, command, **extra):
        payload = json.dumps(
            {"tool_name": "Bash", "tool_input": {"command": command, "description": "run jest"}}
        )
        return subprocess.run(
            ["bash", str(GUARD)], input=payload, capture_output=True, text=True, cwd=self.repo
        )

    def test_full_suite_shapes_are_blocked(self):
        for command in self.BLOCKED:
            with self.subTest(command=command):
                self.assertEqual(self.run_guard(command).returncode, 2, command)

    def test_read_only_and_scoped_commands_pass(self):
        for command in self.ALLOWED:
            with self.subTest(command=command):
                result = self.run_guard(command)
                self.assertEqual(result.returncode, 0, command + "\n" + result.stderr)

    def test_description_key_is_not_absorbed_into_the_command(self):
        payload = '{"tool_input":{"command":"ls","description":"run npm test"}}'
        result = subprocess.run(
            ["bash", str(GUARD)],
            input='{"tool_name":"Bash",' + payload[1:],
            capture_output=True,
            text=True,
            cwd=self.repo,
        )
        self.assertEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
