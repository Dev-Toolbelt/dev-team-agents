"""The CLI contract the desktop app and CI scripts depend on (ADR-0011).

Every assertion here is about the interface, not the implementation: one JSON
document on stdout, an ``ok`` field, and a stable exit code per failure class.
"""

import json
import unittest

from devteam_support import StoreTestCase

from devteam import errors


class JsonContractTest(StoreTestCase):
    def assert_json(self, args, expected_code=0):
        code, out, err = self.run_cli(*args)
        self.assertEqual(code, expected_code, "stderr: {}".format(err))
        body = json.loads(out)  # raises if stdout is not exactly one document
        self.assertIn("ok", body)
        return body

    def test_flag_works_before_and_after_the_subcommand(self):
        before = self.assert_json(["--json", "path"])
        after = self.assert_json(["path", "--json"])
        self.assertEqual(before["core"], after["core"])

    def test_path_reports_every_store_location(self):
        body = self.assert_json(["path", "--json"])
        for key in ("core", "data", "cache", "versions", "registry", "current_file"):
            self.assertIn(key, body)
        self.assertTrue(body["core"].startswith(str(self.home)))

    def test_usage_error_exits_two(self):
        code, out, _ = self.run_cli("--json")
        self.assertEqual(code, errors.EXIT_USAGE)
        self.assertFalse(json.loads(out)["ok"])

    def test_unknown_subcommand_exits_two(self):
        code, _, _ = self.run_cli("teleport")
        self.assertEqual(code, errors.EXIT_USAGE)

    def test_environment_error_exits_three_with_a_hint(self):
        body_code, out, _ = self.run_cli("bind", str(self.new_project()), "--json")
        self.assertEqual(body_code, errors.EXIT_ENVIRONMENT)
        body = json.loads(out)
        self.assertFalse(body["ok"])
        self.assertIn("hint", body)

    def test_conflict_exits_four(self):
        self.run_cli("store", "install", "--from", str(self.source), "--version", "3.0.0")
        code, out, _ = self.run_cli(
            "store", "install", "--from", str(self.source), "--version", "3.0.0", "--json"
        )
        self.assertEqual(code, errors.EXIT_CONFLICT)
        self.assertFalse(json.loads(out)["ok"])

    def test_human_mode_writes_no_json_and_json_mode_writes_no_prose(self):
        self.run_cli("store", "install", "--from", str(self.source), "--version", "3.0.0")
        _, human, _ = self.run_cli("version")
        with self.assertRaises(ValueError):
            json.loads(human)
        _, machine, _ = self.run_cli("version", "--json")
        self.assertEqual(json.loads(machine)["current"], "3.0.0")

    def test_warnings_go_to_stderr_so_json_stdout_stays_parseable(self):
        self.run_cli("store", "install", "--from", str(self.source), "--version", "3.0.0")
        project_root = self.new_project()
        import shutil

        code, out, _ = self.run_cli("bind", str(project_root), "--json")
        self.assertEqual(code, 0)
        json.loads(out)
        shutil.rmtree(str(project_root))
        code, out, err = self.run_cli("sync", "--all", "--json")
        json.loads(out)  # still a single valid document
        self.assertEqual(code, errors.EXIT_FINDINGS)

    def test_full_lifecycle_through_the_cli_only(self):
        self.run_cli("store", "install", "--from", str(self.source), "--version", "3.0.0")
        project_root = self.new_project("lifecycle")

        bound = self.assert_json(["bind", str(project_root), "--json"])
        self.assertEqual(bound["version"], "3.0.0")

        listed = self.assert_json(["list", "--json"])
        self.assertEqual(len(listed["projects"]), 1)
        self.assertEqual(listed["projects"][0]["resolves_to"], "3.0.0")

        from devteam_support import make_source_tree

        make_source_tree(self.tmp / "source", version="3.1.0")
        self.run_cli("store", "install", "--from", str(self.source), "--version", "3.1.0")
        self.run_cli("store", "use", "3.1.0")
        synced = self.assert_json(["sync", "--all", "--json"])
        self.assertEqual(synced["synced"][0]["version"], "3.1.0")

        pinned = self.assert_json(["pin", "3.0.0", "--path", str(project_root), "--json"])
        self.assertEqual(pinned["pin"], "3.0.0")
        self.assert_json(["sync", str(project_root), "--json"])
        after_pin = self.assert_json(["list", "--json"])
        self.assertEqual(after_pin["projects"][0]["resolves_to"], "3.0.0")

        gc_preview = self.assert_json(["store", "gc", "--json"])
        self.assertEqual(gc_preview["would_remove"], [])

        report = self.assert_json(["doctor", str(project_root), "--json"])
        self.assertEqual(report["status"], "ok")

        unbound = self.assert_json(["unbind", str(project_root), "--json"])
        self.assertIn("project.json", unbound["kept"])


if __name__ == "__main__":
    unittest.main()
