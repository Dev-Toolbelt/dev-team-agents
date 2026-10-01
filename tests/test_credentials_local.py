"""The local credentials file (ADR-0024): relocation, show, init and patch.

Planted secret values are scanned for in every payload: the promise under test is that
`show`, `init` and `patch` never return one.
"""

from __future__ import annotations

import errno
import hashlib
import json
import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from devteam_support import REPO_ROOT, StoreTestCase
from test_provider_ownership import _missing_tools

from devteam import credentials_local as cl
from devteam import bind, doctor, paths, project, providers, upgrade, versions
from devteam.errors import ConflictError, EnvError, UsageError

PLANTED = "pl4nted-S3CR3T-9d2e"
CONTENT = '{"custom": {"password": "%s"}, "app": {"staging": {"appUrl": "u"}}}\n' % PLANTED


def _mode(path):
    return stat.S_IMODE(os.stat(str(path)).st_mode)


class LocalCredsCase(StoreTestCase):
    def setUp(self):
        super().setUp()
        self.install_version("3.0.0", activate=True)
        self.root = self.new_project()
        code, out, err = self.run_cli("bind", str(self.root), "--json")
        self.assertEqual(code, 0, err)
        self.pid = json.loads(out)["project_id"]
        self.target = cl.file_path(self.root)

    def set_layout(self, value):
        project.set_layout(self.root, value)

    def put(self, path, text, mode=0o600):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        os.chmod(str(path), mode)
        return path

    @property
    def user_data(self):
        return self.root / ".dev-team-agents" / "user-data" / cl.FILE_NAME

    @property
    def store_copy(self):
        return paths.machine_project_dir(self.pid) / cl.FILE_NAME

    def blank_text(self):
        return json.dumps(cl.load_template(), indent=4)

    def quarantined(self):
        base = paths.data_dir() / "quarantine"
        return sorted(p for p in base.rglob(cl.FILE_NAME + "*")) if base.exists() else []


class TemplateTest(LocalCredsCase):
    def test_template_has_the_complete_structure(self):
        template = cl.load_template()
        self.assertEqual(
            set(template), {"work_feedback_active", "work_feedback_interval_minutes", "devops", "app"}
        )
        self.assertIs(template["work_feedback_active"], True)
        self.assertEqual(template["work_feedback_interval_minutes"], 5)
        self.assertEqual(set(template["devops"]), {"agents", "staging", "production"})
        self.assertIn("docker", template["devops"]["production"])

    def test_blank_template_detection_ignores_formatting(self):
        self.assertTrue(cl.is_blank_template(self.blank_text().encode()))
        self.assertFalse(cl.is_blank_template(b"not json"))
        self.assertFalse(cl.is_blank_template(CONTENT.encode()))


class RelocateTest(LocalCredsCase):
    def test_nothing_to_do(self):
        report = cl.relocate(self.root)
        self.assertFalse(report["changed"])
        self.assertFalse(self.target.exists())

    def test_row1_moves_layout1_copy_byte_for_byte(self):
        self.put(self.user_data, CONTENT)
        report = cl.relocate(self.root)
        self.assertTrue(report["changed"])
        self.assertEqual(len(report["moved"]), 1)
        self.assertEqual(self.target.read_bytes(), CONTENT.encode())
        self.assertFalse(self.user_data.exists())
        self.assertEqual(_mode(self.target), 0o600)

    def test_row1_moves_layout2_store_copy(self):
        self.set_layout(2)
        self.put(self.store_copy, CONTENT)
        cl.relocate(self.root)
        self.assertEqual(self.target.read_bytes(), CONTENT.encode())
        self.assertFalse(self.store_copy.exists())
        self.assertEqual(_mode(self.target), 0o600)

    def test_move_preserves_non_canonical_bytes(self):
        raw = b'{ "a":   1 ,\r\n "b": "\xc3\xa9"}'
        self.user_data.parent.mkdir(parents=True, exist_ok=True)
        self.user_data.write_bytes(raw)
        cl.relocate(self.root)
        self.assertEqual(self.target.read_bytes(), raw)

    def test_cross_filesystem_fallback_is_verified_and_removes_source(self):
        self.put(self.user_data, CONTENT)
        with mock.patch("os.link", side_effect=OSError(errno.EXDEV, "cross-device")):
            cl.relocate(self.root)
        self.assertEqual(self.target.read_bytes(), CONTENT.encode())
        self.assertFalse(self.user_data.exists())
        self.assertEqual(_mode(self.target), 0o600)

    def test_row2_identical_legacy_is_quarantined(self):
        self.put(self.target, CONTENT)
        self.put(self.user_data, CONTENT)
        report = cl.relocate(self.root)
        self.assertEqual(report["quarantined"][0]["reason"], "duplicate")
        self.assertFalse(self.user_data.exists())
        self.assertEqual(self.target.read_text(), CONTENT)
        self.assertEqual(len(self.quarantined()), 1)

    def test_row3_blank_legacy_is_quarantined(self):
        self.put(self.target, CONTENT)
        self.put(self.user_data, self.blank_text())
        report = cl.relocate(self.root)
        self.assertEqual(report["quarantined"][0]["reason"], "blank-legacy")
        self.assertEqual(self.target.read_text(), CONTENT)

    def test_row4_blank_root_is_replaced_by_legacy_content(self):
        self.put(self.target, self.blank_text())
        self.put(self.user_data, CONTENT)
        report = cl.relocate(self.root)
        self.assertEqual(report["quarantined"][0]["reason"], "blank-root")
        self.assertEqual(self.target.read_bytes(), CONTENT.encode())
        self.assertFalse(self.user_data.exists())
        quarantined = self.quarantined()
        self.assertEqual(len(quarantined), 1)
        self.assertEqual(json.loads(quarantined[0].read_text()), cl.load_template())

    def test_row5_conflict_touches_nothing(self):
        root_text = '{"app": {"staging": {"appUrl": "root"}}}\n'
        self.put(self.target, root_text)
        self.put(self.user_data, CONTENT)
        report = cl.relocate(self.root)
        self.assertFalse(report["changed"])
        self.assertEqual(len(report["conflicts"]), 1)
        self.assertEqual(self.target.read_text(), root_text)
        self.assertEqual(self.user_data.read_text(), CONTENT)
        self.assertEqual(self.quarantined(), [])

    def test_idempotent(self):
        self.put(self.user_data, CONTENT)
        cl.relocate(self.root)
        again = cl.relocate(self.root)
        self.assertFalse(again["changed"])
        self.assertEqual(self.target.read_bytes(), CONTENT.encode())

    def test_both_layout_copies_move_one_and_resolve_the_other(self):
        self.set_layout(2)
        self.put(self.store_copy, CONTENT)
        self.put(self.user_data, CONTENT)
        cl.relocate(self.root)
        self.assertEqual(self.target.read_bytes(), CONTENT.encode())
        self.assertFalse(self.store_copy.exists())
        self.assertFalse(self.user_data.exists())
        self.assertEqual(len(self.quarantined()), 1)

    def test_legacy_paths_follow_the_recorded_layout(self):
        self.set_layout(1)
        self.assertEqual(cl.legacy_paths(self.root)[0], self.user_data)
        self.set_layout(2)
        self.assertEqual(cl.legacy_paths(self.root)[0], self.store_copy)


class ShowTest(LocalCredsCase):
    def test_missing(self):
        state = cl.show(self.root)
        self.assertEqual(
            state,
            {
                "path": str(self.target),
                "exists": False,
                "valid": False,
                "error": None,
                "hash": None,
                "data": None,
                "unknown_paths": [],
            },
        )

    def test_invalid_reports_line_and_column(self):
        self.put(self.target, '{\n  "a": 1,\n  "b": \n}\n')
        state = cl.show(self.root)
        self.assertTrue(state["exists"])
        self.assertFalse(state["valid"])
        self.assertIsNone(state["data"])
        self.assertEqual(state["error"]["line"], 4)
        self.assertGreaterEqual(state["error"]["column"], 1)
        self.assertTrue(state["error"]["message"])
        self.assertIsNotNone(state["hash"])

    def test_non_object_top_level_is_invalid(self):
        self.put(self.target, "[1, 2]")
        self.assertFalse(cl.show(self.root)["valid"])

    def test_hash_is_a_machine_keyed_hmac_of_raw_bytes_not_a_plain_sha256(self):
        import hmac

        self.put(self.target, CONTENT)
        token = cl.show(self.root)["hash"]
        expected = hmac.new(cl._token_key(), CONTENT.encode(), hashlib.sha256).hexdigest()
        self.assertEqual(token, expected)
        self.assertNotEqual(token, hashlib.sha256(CONTENT.encode()).hexdigest())
        key_file = paths.machine_dir() / cl.TOKEN_KEY_FILE
        self.assertEqual(_mode(key_file), 0o600)
        self.assertTrue(paths.is_machine_local_record(key_file.name))

    def test_every_secret_key_is_redacted_case_insensitively_and_nested(self):
        doc = {
            "a": {"Password": PLANTED, "TOKEN": PLANTED, "secret": PLANTED},
            "b": {"apikey": PLANTED, "PrivateKey": PLANTED, "privateKeyPath": "/k/id"},
            "devops": {"staging": {"database": [{"password": PLANTED}, {"password": ""}]}},
        }
        self.put(self.target, json.dumps(doc))
        state = cl.show(self.root)
        self.assertNotIn(PLANTED, json.dumps(state))
        self.assertEqual(state["data"]["a"]["Password"], {"secret": True, "set": True})
        self.assertEqual(state["data"]["a"]["TOKEN"], {"secret": True, "set": True})
        self.assertEqual(state["data"]["b"]["PrivateKey"], {"secret": True, "set": True})
        self.assertEqual(state["data"]["b"]["privateKeyPath"], "/k/id")
        db = state["data"]["devops"]["staging"]["database"]
        self.assertEqual(db[0]["password"], {"secret": True, "set": True})
        self.assertEqual(db[1]["password"], {"secret": True, "set": False})

    def test_template_has_no_unknown_paths(self):
        self.put(self.target, json.dumps(cl.load_template()))
        self.assertEqual(cl.show(self.root)["unknown_paths"], [])

    def test_unknown_paths(self):
        doc = cl.load_template()
        doc["monitoring"] = {"token": PLANTED}
        doc["app"]["qa"] = {"appUrl": "x"}
        doc["app"]["staging"]["extra"] = 1
        doc["devops"]["staging"]["database"].append({"host": "h", "weird": 1})
        doc["devops"]["production"]["docker"] = {"anything": {"goes": True}}
        self.put(self.target, json.dumps(doc))
        state = cl.show(self.root)
        self.assertEqual(
            sorted(state["unknown_paths"]),
            sorted(
                [
                    "/monitoring",
                    "/app/qa",
                    "/app/staging/extra",
                    "/devops/staging/database/1/weird",
                ]
            ),
        )
        self.assertNotIn(PLANTED, json.dumps(state))

    def test_pointer_escaping(self):
        doc = cl.load_template()
        doc["a/b~c"] = 1
        self.put(self.target, json.dumps(doc))
        self.assertIn("/a~1b~0c", cl.show(self.root)["unknown_paths"])


class InitTest(LocalCredsCase):
    def test_creates_the_template_owner_only(self):
        state = cl.init(self.root)
        self.assertTrue(state["valid"])
        self.assertEqual(_mode(self.target), 0o600)
        self.assertEqual(json.loads(self.target.read_text()), cl.load_template())
        self.assertEqual(self.target.read_bytes(), cl.TEMPLATE_FILE.read_bytes())
        self.assertEqual(state["unknown_paths"], [])

    def test_refuses_when_the_file_exists_and_leaves_it_alone(self):
        self.put(self.target, CONTENT)
        with self.assertRaises(ConflictError):
            cl.init(self.root)
        self.assertEqual(self.target.read_text(), CONTENT)

    def test_show_alone_never_creates_the_file(self):
        cl.show(self.root)
        cl.relocate(self.root)
        self.assertFalse(self.target.exists())


class PatchTest(LocalCredsCase):
    def setUp(self):
        super().setUp()
        cl.init(self.root)
        self.hash = cl.show(self.root)["hash"]

    def patch(self, ops, expect=None):
        return cl.apply_patch(self.root, ops, expect or self.hash)

    def on_disk(self):
        return json.loads(self.target.read_text())

    def test_set_creates_intermediate_objects_and_keeps_format(self):
        state = self.patch([{"op": "set", "pointer": "/app/qa/appUrl", "value": "https://q"}])
        self.assertEqual(self.on_disk()["app"]["qa"], {"appUrl": "https://q"})
        raw = self.target.read_text()
        self.assertTrue(raw.endswith("}\n"))
        self.assertIn('\n  "app": {', raw)
        self.assertEqual(_mode(self.target), 0o600)
        self.assertNotEqual(state["hash"], self.hash)
        self.assertEqual(state["hash"], cl._hash(raw.encode()))

    def test_set_replaces_and_unset_removes(self):
        self.patch(
            [
                {"op": "set", "pointer": "/work_feedback_interval_minutes", "value": 9},
                {"op": "unset", "pointer": "/app/staging/appUrl"},
            ]
        )
        data = self.on_disk()
        self.assertEqual(data["work_feedback_interval_minutes"], 9)
        self.assertNotIn("appUrl", data["app"]["staging"])

    def test_unset_of_a_missing_path_is_a_no_op(self):
        self.patch([{"op": "unset", "pointer": "/nope/deeper"}])
        self.assertEqual(self.on_disk(), cl.load_template())

    def test_array_append_index_set_and_unset(self):
        self.patch([{"op": "set", "pointer": "/devops/agents/-", "value": "qa-specialist"}])
        self.assertEqual(self.on_disk()["devops"]["agents"][-1], "qa-specialist")
        self.patch(
            [{"op": "set", "pointer": "/devops/agents/0", "value": "x"}],
            expect=cl.show(self.root)["hash"],
        )
        self.assertEqual(self.on_disk()["devops"]["agents"][0], "x")
        self.patch(
            [{"op": "unset", "pointer": "/devops/agents/0"}], expect=cl.show(self.root)["hash"]
        )
        self.assertEqual(self.on_disk()["devops"]["agents"][0], "devops-specialist")

    def test_set_into_database_array_item(self):
        self.patch([{"op": "set", "pointer": "/devops/staging/database/0/host", "value": "db"}])
        self.assertEqual(self.on_disk()["devops"]["staging"]["database"][0]["host"], "db")

    def test_secret_pointer_stores_the_value_and_never_returns_it(self):
        state = self.patch(
            [{"op": "set", "pointer": "/app/staging/password", "value": PLANTED}]
        )
        self.assertEqual(self.on_disk()["app"]["staging"]["password"], PLANTED)
        self.assertNotIn(PLANTED, json.dumps(state))
        self.assertEqual(state["data"]["app"]["staging"]["password"], {"secret": True, "set": True})

    def test_unknown_keys_are_preserved(self):
        doc = self.on_disk()
        doc["monitoring"] = {"url": "m", "token": PLANTED}
        doc["app"]["qa"] = {"appUrl": "q"}
        self.target.write_text(json.dumps(doc, indent=2) + "\n")
        fresh = cl.show(self.root)["hash"]
        state = self.patch([{"op": "set", "pointer": "/app/staging/appUrl", "value": "s"}], fresh)
        data = self.on_disk()
        self.assertEqual(data["monitoring"], {"url": "m", "token": PLANTED})
        self.assertEqual(data["app"]["qa"], {"appUrl": "q"})
        self.assertIn("/monitoring", state["unknown_paths"])

    def test_key_order_is_preserved(self):
        before = list(self.on_disk())
        self.patch([{"op": "set", "pointer": "/app/staging/appUrl", "value": "s"}])
        self.assertEqual(list(self.on_disk()), before)

    def test_hash_mismatch_is_refused_and_file_untouched(self):
        before = self.target.read_bytes()
        with self.assertRaises(ConflictError) as ctx:
            self.patch([{"op": "set", "pointer": "/app/staging/appUrl", "value": "s"}], "0" * 64)
        self.assertEqual(ctx.exception.exit_code, 4)
        self.assertEqual(ctx.exception.details["actual_hash"], self.hash)
        self.assertEqual(self.target.read_bytes(), before)

    def test_a_hand_edit_between_read_and_write_is_refused(self):
        self.target.write_text(self.target.read_text() + "\n")
        with self.assertRaises(ConflictError):
            self.patch([{"op": "set", "pointer": "/app/staging/appUrl", "value": "s"}])

    def test_invalid_json_on_disk_is_refused(self):
        self.target.write_text("{ broken")
        bad = cl.show(self.root)["hash"]
        with self.assertRaises(EnvError) as ctx:
            self.patch([{"op": "set", "pointer": "/a", "value": 1}], bad)
        self.assertEqual(ctx.exception.details["error"]["line"], 1)
        self.assertEqual(self.target.read_text(), "{ broken")

    def test_missing_file_is_refused(self):
        self.target.unlink()
        with self.assertRaises(EnvError):
            self.patch([{"op": "set", "pointer": "/a", "value": 1}])
        self.assertFalse(self.target.exists())

    def test_placeholder_values_are_refused(self):
        before = self.target.read_bytes()
        for value in ({"secret": True, "set": True}, {"nested": {"secret": True, "set": False}}):
            with self.assertRaises(UsageError):
                self.patch([{"op": "set", "pointer": "/app/staging/password", "value": value}])
        self.assertEqual(self.target.read_bytes(), before)

    def test_ops_are_all_or_nothing(self):
        before = self.target.read_bytes()
        with self.assertRaises(UsageError):
            self.patch(
                [
                    {"op": "set", "pointer": "/app/staging/appUrl", "value": "s"},
                    {"op": "set", "pointer": "/work_feedback_active/x", "value": 1},
                ]
            )
        self.assertEqual(self.target.read_bytes(), before)

    def test_malformed_ops_are_usage_errors(self):
        for ops in (
            {"op": "set"},
            [{"op": "nuke", "pointer": "/a"}],
            [{"op": "set", "pointer": "a", "value": 1}],
            [{"op": "set", "pointer": "/a"}],
            [{"op": "set", "pointer": "/devops/agents/01", "value": 1}],
            [{"op": "set", "pointer": "/devops/agents/9", "value": 1}],
        ):
            with self.subTest(ops=ops), self.assertRaises(UsageError):
                self.patch(ops)

    def test_tmp_files_do_not_linger(self):
        self.patch([{"op": "set", "pointer": "/app/staging/appUrl", "value": "s"}])
        leftovers = [p.name for p in self.target.parent.iterdir() if p.name.endswith(".tmp")]
        self.assertEqual(leftovers, [])


class CliTest(LocalCredsCase):
    def run_json(self, *args, input_text=None):
        code, out, err = self.run_cli(*args, "--path", str(self.root), "--json", input_text=input_text)
        return code, (json.loads(out) if out.strip() else None), err

    def test_show_init_patch_round_trip(self):
        code, body, _ = self.run_json("cred", "local", "show")
        self.assertEqual((code, body["exists"]), (0, False))
        code, body, _ = self.run_json("cred", "local", "init")
        self.assertEqual(code, 0)
        code, body2, _ = self.run_json("cred", "local", "init")
        self.assertEqual((code, body2["exit_code"]), (4, 4))
        ops = json.dumps([{"op": "set", "pointer": "/app/staging/password", "value": PLANTED}])
        code, patched, err = self.run_json(
            "cred", "local", "patch", "--expect-hash", body["hash"], input_text=ops
        )
        self.assertEqual(code, 0, err)
        self.assertNotIn(PLANTED, json.dumps(patched))
        self.assertEqual(
            set(patched),
            {"ok", "path", "exists", "valid", "error", "hash", "data", "unknown_paths"},
        )
        code, conflict, _ = self.run_json(
            "cred", "local", "patch", "--expect-hash", body["hash"], input_text=ops
        )
        self.assertEqual((code, conflict["ok"], conflict["exit_code"]), (4, False, 4))

    def test_invalid_file_exits_0_on_show_and_3_on_patch(self):
        self.put(self.target, "{ nope")
        code, body, _ = self.run_json("cred", "local", "show")
        self.assertEqual(code, 0)
        self.assertFalse(body["valid"])
        self.assertEqual(set(body["error"]), {"message", "line", "column"})
        code, err_body, _ = self.run_json(
            "cred", "local", "patch", "--expect-hash", body["hash"], input_text="[]"
        )
        self.assertEqual((code, err_body["exit_code"]), (3, 3))

    def test_patch_without_valid_stdin_or_hash_is_a_usage_error(self):
        cl.init(self.root)
        code, body, _ = self.run_json("cred", "local", "patch", "--expect-hash", "x", input_text="nope")
        self.assertEqual((code, body["exit_code"]), (2, 2))
        code, body, _ = self.run_json("cred", "local", "patch", input_text="[]")
        self.assertEqual((code, body["exit_code"]), (2, 2))

    def test_human_output_never_carries_a_secret(self):
        self.put(self.target, CONTENT)
        code, out, _ = self.run_cli("cred", "local", "show", "--path", str(self.root))
        self.assertEqual(code, 0)
        self.assertNotIn(PLANTED, out)


def _sha(path):
    import hashlib

    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class WiredRelocationTest(LocalCredsCase):
    """ADR-0024 relocation is reached from sync, doctor and upgrade, never only by hand."""

    def _sync(self):
        code, out, err = self.run_cli("sync", str(self.root), "--json")
        self.assertEqual(code, 0, err)
        return json.loads(out)

    def test_sync_relocates_from_user_data_and_reports_it(self):
        self.set_layout(1)
        self.put(self.user_data, CONTENT)
        result = self._sync()
        self.assertEqual(self.target.read_bytes(), CONTENT.encode())
        self.assertFalse(self.user_data.exists())
        report = result["credentials_local"]
        self.assertTrue(report["changed"])
        self.assertEqual(len(report["moved"]), 1)

    def test_sync_relocates_regardless_of_the_bound_provider(self):
        # Real installers: the delegated providers' bind runs bash scripts that a stub
        # version does not carry.
        versions.install_from_tree(REPO_ROOT, version="9.9.9", force=True, make_current=True)
        for provider in providers.ALL_PROVIDERS:
            if _missing_tools(provider):
                continue
            with self.subTest(provider=provider):
                root = self.new_project("p-{}".format(provider))
                result = bind.bind(root, provider_names=[provider])
                pid = result["project_id"]
                project.set_layout(root, 1)
                legacy = root / ".dev-team-agents" / "user-data" / cl.FILE_NAME
                self.put(legacy, CONTENT)
                synced = bind.sync_project(pid)
                self.assertEqual(cl.file_path(root).read_bytes(), CONTENT.encode())
                self.assertFalse(legacy.exists())
                self.assertEqual(len(synced["credentials_local"]["moved"]), 1)

    def test_sync_all_reports_per_project_and_survives_a_conflict(self):
        self.put(self.target, '{"app": {"staging": {"appUrl": "root"}}}\n')
        self.put(self.user_data, CONTENT)
        code, out, err = self.run_cli("sync", "--all", "--json")
        self.assertEqual(code, 0, err)
        entry = [r for r in json.loads(out)["synced"] if r["project_id"] == self.pid][0]
        self.assertEqual(len(entry["credentials_local"]["conflicts"]), 1)
        self.assertEqual(self.user_data.read_text(), CONTENT)

    def test_reported_bug_store_has_real_file_and_user_data_has_blank_template(self):
        self.set_layout(2)
        self.put(self.store_copy, CONTENT)
        self.put(self.user_data, self.blank_text())
        result = self._sync()
        self.assertEqual(self.target.read_bytes(), CONTENT.encode())
        self.assertFalse(self.store_copy.exists())
        self.assertFalse(self.user_data.exists())
        reasons = [q["reason"] for q in result["credentials_local"]["quarantined"]]
        self.assertEqual(reasons, ["blank-legacy"])
        self.assertEqual(len(self.quarantined()), 1)

    def test_doctor_reports_a_conflict_without_touching_files(self):
        root_text = '{"app": {"staging": {"appUrl": "root"}}}\n'
        self.put(self.target, root_text)
        self.put(self.user_data, CONTENT)
        report = doctor.run(project_root=self.root)
        findings = [f for f in report["findings"] if f["category"] == "credentials"]
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["level"], doctor.WARN)
        self.assertIn("by hand", findings[0]["hint"])
        self.assertEqual(len(report["credentials_local"]["conflicts"]), 1)
        self.assertEqual(self.target.read_text(), root_text)
        self.assertEqual(self.user_data.read_text(), CONTENT)
        self.assertEqual(self.quarantined(), [])

    def test_doctor_relocates_and_reports_the_move(self):
        self.put(self.user_data, CONTENT)
        report = doctor.run(project_root=self.root)
        self.assertEqual(self.target.read_bytes(), CONTENT.encode())
        self.assertEqual([a["action"] for a in report["actions"] if "credentials" in a["action"]],
                         ["credentials_relocated"])

    def test_upgrade_keeps_the_file_at_the_root_byte_for_byte_and_never_quarantines_it(self):
        root = self.new_project("upg")
        memory = project.legacy_memory_dir(root)
        memory.mkdir(parents=True)
        (memory / "session-summary.md").write_text("## memory\n", encoding="utf-8")
        raw = b'{ "custom":   {"password": "%s"} }\r\n' % PLANTED.encode()
        (memory / cl.FILE_NAME).write_bytes(raw)
        digest = _sha(memory / cl.FILE_NAME)
        pid = bind.bind(root, provider_names=["claude"])["project_id"]
        project.set_layout(root, 1)

        result = upgrade.apply(root)

        target = cl.file_path(root)
        self.assertEqual(_sha(target), digest)
        self.assertEqual(Path(result["credentials_local"]["moved"][0]["to"]).resolve(), target.resolve())
        self.assertEqual(
            [p for p in Path(result["quarantined"]).rglob("*") if p.name == cl.FILE_NAME], []
        )
        self.assertFalse((paths.machine_project_dir(pid) / cl.FILE_NAME).exists())
        self.assertFalse((paths.projects_dir() / pid / cl.FILE_NAME).exists())

    def test_upgrade_picks_up_a_store_copy(self):
        root = self.new_project("upg-store")
        memory = project.legacy_memory_dir(root)
        memory.mkdir(parents=True)
        (memory / "session-summary.md").write_text("## memory\n", encoding="utf-8")
        pid = bind.bind(root, provider_names=["claude"])["project_id"]
        project.set_layout(root, 1)
        stored = paths.machine_project_dir(pid) / cl.FILE_NAME
        self.put(stored, CONTENT)
        upgrade.apply(root)
        self.assertEqual(cl.file_path(root).read_bytes(), CONTENT.encode())
        self.assertFalse(stored.exists())


def _git(cwd, *args):
    subprocess.run(
        ["git", "-c", "user.email=a@b.c", "-c", "user.name=t"] + list(args),
        cwd=str(cwd), check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )


class DefaultDenyRedactionTest(LocalCredsCase):
    def shown(self, doc):
        self.put(self.target, json.dumps(doc))
        state = cl.show(self.root)
        self.assertNotIn(PLANTED, json.dumps(state))
        return state["data"]

    def test_free_form_and_hand_added_keys_are_redacted(self):
        doc = {
            "devops": {
                "production": {
                    "docker": {"env": {"DB_PASSWORD": PLANTED, "NAME": PLANTED}},
                    "ssh": {"passphrase": PLANTED, "host": "h"},
                }
            },
            "oauth": {"clientSecret": PLANTED, "accessToken": PLANTED, "api_key": PLANTED},
            "tokens": [PLANTED, PLANTED],
            "objs": [{"x": PLANTED}],
        }
        data = self.shown(doc)
        hidden = {"secret": True, "set": True}
        self.assertEqual(data["devops"]["production"]["docker"]["env"]["DB_PASSWORD"], hidden)
        self.assertEqual(data["devops"]["production"]["docker"]["env"]["NAME"], hidden)
        self.assertEqual(data["devops"]["production"]["ssh"]["passphrase"], hidden)
        self.assertEqual(data["devops"]["production"]["ssh"]["host"], "h")
        self.assertEqual(data["oauth"], {"clientSecret": hidden, "accessToken": hidden, "api_key": hidden})
        self.assertEqual(data["tokens"], [hidden, hidden])
        self.assertEqual(data["objs"], [{"x": hidden}])

    def test_url_userinfo_is_redacted_in_app_url_and_host(self):
        doc = {"app": {"staging": {"appUrl": "https://u:%s@x.test/" % PLANTED, "username": "u"},
                       "production": {"appUrl": "https://x.test/"}},
               "devops": {"staging": {"ssh": {"host": "u:%s@h" % PLANTED, "user": "u"}}}}
        data = self.shown(doc)
        self.assertEqual(data["app"]["staging"]["appUrl"], {"secret": True, "set": True})
        self.assertEqual(data["app"]["staging"]["username"], "u")
        self.assertEqual(data["app"]["production"]["appUrl"], "https://x.test/")
        self.assertEqual(data["devops"]["staging"]["ssh"]["host"], {"secret": True, "set": True})

    def test_known_non_secret_shapes_survive(self):
        data = self.shown(cl.load_template())
        template = cl.load_template()
        self.assertIs(data["work_feedback_active"], True)
        self.assertEqual(data["work_feedback_interval_minutes"], 5)
        self.assertEqual(data["app"]["agents"], template["app"]["agents"])
        self.assertEqual(data["devops"]["staging"]["ssh"]["privateKeyPath"], "")
        self.assertEqual(data["devops"]["production"]["docker"], {})
        db = data["devops"]["staging"]["database"][0]
        self.assertEqual(db["type"], "")
        self.assertEqual(db["password"], {"secret": True, "set": False})

    def test_unknown_agents_key_with_non_strings_is_redacted(self):
        data = self.shown({"x": {"agents": [{"k": PLANTED}]}})
        self.assertEqual(data["x"]["agents"], [{"k": {"secret": True, "set": True}}])

    def test_secretish_key_with_a_safe_name_is_redacted(self):
        data = self.shown({"app": {"staging": {"database": [{"host": "h", "dsn": PLANTED}]}}})
        item = data["app"]["staging"]["database"][0]
        self.assertEqual(item["host"], "h")
        self.assertEqual(item["dsn"], {"secret": True, "set": True})


class UpgradeConflictTest(LocalCredsCase):
    def test_conflict_refuses_before_anything_moves(self):
        root = self.new_project("upg-conflict")
        memory = project.legacy_memory_dir(root)
        memory.mkdir(parents=True)
        (memory / "session-summary.md").write_text("## memory\n", encoding="utf-8")
        legacy = memory / cl.FILE_NAME
        legacy.write_text('{"a": "%s"}' % PLANTED, encoding="utf-8")
        bind.bind(root, provider_names=["claude"])
        project.set_layout(root, 1)
        target = cl.file_path(root)
        self.put(target, '{"b": 1}')
        with self.assertRaises(ConflictError) as ctx:
            upgrade.apply(root)
        self.assertIn("doctor", ctx.exception.hint)
        self.assertEqual(legacy.read_text(encoding="utf-8"), '{"a": "%s"}' % PLANTED)
        self.assertEqual(target.read_text(encoding="utf-8"), '{"b": 1}')
        self.assertTrue((memory / "session-summary.md").exists())
        self.assertEqual(project.layout(root), 1)


class WorktreeTest(LocalCredsCase):
    def setUp(self):
        super().setUp()
        _git(self.root, "init", "-q")
        _git(self.root, "add", "-A")
        _git(self.root, "commit", "-q", "--allow-empty", "-m", "i")
        self.wt = Path(tempfile.mkdtemp(prefix="cl-wt-")) / "wt"
        self.addCleanup(__import__("shutil").rmtree, str(self.wt.parent), True)
        _git(self.root, "worktree", "add", "-q", str(self.wt), "-b", "side")

    def test_path_resolves_to_the_main_checkout_from_a_worktree(self):
        self.assertEqual(cl.file_path(self.wt).resolve(), cl.file_path(self.root).resolve())
        self.assertEqual(cl.file_path(self.root).resolve(), self.target.resolve())

    def test_init_show_patch_from_a_worktree_use_the_shared_file(self):
        cl.init(self.wt)
        self.assertTrue(self.target.is_file())
        self.assertFalse((self.wt / ".dev-team-agents" / cl.FILE_NAME).exists())
        state = cl.show(self.wt)
        self.assertEqual(Path(state["path"]).resolve(), self.target.resolve())
        cl.apply_patch(
            self.wt, [{"op": "set", "pointer": "/app/staging/appUrl", "value": "u"}], state["hash"]
        )
        self.assertEqual(json.loads(self.target.read_text())["app"]["staging"]["appUrl"], "u")

    def test_relocate_from_a_worktree_never_moves_a_copy_into_it(self):
        self.put(self.user_data, CONTENT)
        report = cl.relocate(self.wt)
        self.assertEqual(self.target.read_text(), CONTENT)
        self.assertFalse((self.wt / ".dev-team-agents" / cl.FILE_NAME).exists())
        self.assertEqual(Path(report["path"]).resolve(), self.target.resolve())

    def test_falls_back_to_the_given_root_without_git(self):
        plain = Path(tempfile.mkdtemp(prefix="cl-nogit-"))
        self.addCleanup(__import__("shutil").rmtree, str(plain), True)
        with mock.patch("subprocess.run", side_effect=FileNotFoundError("git")):
            self.assertEqual(cl.file_path(self.wt), self.wt / ".dev-team-agents" / cl.FILE_NAME)
        self.assertEqual(cl.file_path(plain), plain / ".dev-team-agents" / cl.FILE_NAME)


class MoveRaceTest(LocalCredsCase):
    def test_existing_root_is_never_clobbered_by_the_move(self):
        self.put(self.user_data, CONTENT)
        self.put(self.target, '{"other": 1}')
        self.assertFalse(cl._move_file(self.user_data, self.target))
        self.assertEqual(self.target.read_text(), '{"other": 1}')
        self.assertTrue(self.user_data.exists())

    def test_root_appearing_mid_relocate_is_treated_as_present(self):
        self.put(self.user_data, CONTENT)
        real = os.link

        def racing(src, dst, **kwargs):
            self.put(dst, CONTENT)  # someone else wins the race with identical content
            return real(src, dst, **kwargs)

        with mock.patch("os.link", side_effect=racing):
            report = cl.relocate(self.root)
        self.assertEqual(report["moved"], [])
        self.assertEqual([q["reason"] for q in report["quarantined"]], ["duplicate"])
        self.assertEqual(self.target.read_text(), CONTENT)

    def test_link_unsupported_falls_back_to_exclusive_copy(self):
        self.put(self.user_data, CONTENT)
        with mock.patch("os.link", side_effect=PermissionError(1, "no links")):
            cl.relocate(self.root)
        self.assertEqual(self.target.read_text(), CONTENT)
        self.assertFalse(self.user_data.exists())
        self.assertEqual(_mode(self.target), 0o600)

    def test_exclusive_copy_does_not_overwrite(self):
        self.put(self.user_data, CONTENT)
        self.put(self.target, "keep")
        with mock.patch("os.link", side_effect=OSError(errno.EXDEV, "x")):
            self.assertFalse(cl._move_file(self.user_data, self.target))
        self.assertEqual(self.target.read_text(), "keep")

    def test_other_oserrors_propagate_and_keep_the_source(self):
        self.put(self.user_data, CONTENT)
        with mock.patch("os.link", side_effect=OSError(errno.EIO, "io")):
            with self.assertRaises(OSError):
                cl._move_file(self.user_data, self.target)
        self.assertTrue(self.user_data.exists())
        self.assertFalse(self.target.exists())

    def test_a_file_at_the_projects_own_root_is_never_a_candidate(self):
        # v3-credentials spec: nothing scans for it; a project may keep one there on purpose.
        self.assertNotIn(self.root / cl.FILE_NAME, cl.legacy_paths(self.root, self.pid))
        self.put(self.root / cl.FILE_NAME, CONTENT)
        report = cl.relocate(self.root)
        self.assertFalse(report["changed"])
        self.assertFalse(self.target.exists())
        self.assertEqual((self.root / cl.FILE_NAME).read_text(), CONTENT)


class WriteCleanupTest(LocalCredsCase):
    def test_temp_file_is_removed_on_base_exception(self):
        self.put(self.target, CONTENT)
        with mock.patch("os.replace", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                cl._write_bytes(self.target, b"{}")
        self.assertEqual(sorted(p.name for p in self.target.parent.glob(cl.FILE_NAME + ".*")), [])
        self.assertEqual(self.target.read_text(), CONTENT)

    def test_temp_names_match_the_gitignore_pattern(self):
        seen = []
        real = os.replace
        with mock.patch("os.replace", side_effect=lambda a, b: (seen.append(a), real(a, b))[1]):
            cl._write_bytes(self.target, b"{}")
        import fnmatch
        self.assertTrue(fnmatch.fnmatch(os.path.basename(seen[0]), cl.FILE_NAME + ".*"))


class HostileInputTest(LocalCredsCase):
    def test_nan_and_infinity_are_invalid_with_a_position(self):
        for token in ("NaN", "Infinity", "-Infinity", "1e999"):
            self.put(self.target, '{\n  "a": "NaN",\n  "b": %s\n}' % token)
            state = cl.show(self.root)
            self.assertFalse(state["valid"], token)
            self.assertEqual((state["error"]["line"], state["error"]["column"]), (3, 8), token)

    def test_deep_nesting_is_invalid_not_a_crash(self):
        self.put(self.target, "[" * 100000)
        self.assertFalse(cl.show(self.root)["valid"])
        self.put(self.target, '{"a":' * 5000 + "1" + "}" * 5000)
        self.assertFalse(cl.show(self.root)["valid"])

    def test_lone_surrogate_is_invalid_and_never_echoed(self):
        self.put(self.target, '{"a": "\\ud800%s"}' % PLANTED)
        state = cl.show(self.root)
        self.assertFalse(state["valid"])
        self.assertNotIn(PLANTED, json.dumps(state))

    def test_patch_turns_encoding_and_range_failures_into_clean_errors(self):
        self.put(self.target, CONTENT)
        digest = cl.show(self.root)["hash"]
        before = self.target.read_bytes()
        for value in ("\ud800", float("nan")):
            with self.assertRaises(UsageError) as ctx:
                cl.apply_patch(
                    self.root, [{"op": "set", "pointer": "/x", "value": value}], digest
                )
            self.assertNotIn(PLANTED, str(ctx.exception))
        nested = []
        for _ in range(5000):
            nested = [nested]
        with self.assertRaises(UsageError):
            cl.apply_patch(self.root, [{"op": "set", "pointer": "/x", "value": nested}], digest)
        self.assertEqual(self.target.read_bytes(), before)

    def test_cli_patch_with_deep_stdin_is_a_usage_error(self):
        self.put(self.target, CONTENT)
        digest = cl.show(self.root)["hash"]
        code, _out, _err = self.run_cli(
            "cred", "local", "patch", str(self.root), "--expect-hash", digest, "--json",
            input_text="[" * 100000,
        )
        self.assertEqual(code, 2)


class DoctorCredentialsTest(LocalCredsCase):
    def test_busy_lock_is_a_warning_not_a_crash(self):
        self.put(self.user_data, CONTENT)
        with mock.patch.object(cl, "relocate", side_effect=ConflictError("busy")):
            findings, actions, report = doctor.check_credentials_local(self.root)
        self.assertIsNone(report)
        self.assertEqual(findings[0]["level"], "warn")

    def test_loose_mode_warns_with_a_chmod_hint(self):
        self.put(self.target, CONTENT, mode=0o644)
        findings, _actions, _report = doctor.check_credentials_local(self.root)
        warns = [f for f in findings if f["level"] == "warn"]
        self.assertEqual(len(warns), 1)
        self.assertIn("chmod 600", warns[0]["hint"])

    def test_owner_only_mode_is_quiet(self):
        self.put(self.target, CONTENT, mode=0o600)
        findings, _a, _r = doctor.check_credentials_local(self.root)
        self.assertEqual([f for f in findings if f["level"] == "warn"], [])




class ReviewHardeningTest(LocalCredsCase):
    """Second review round: ignore-before-move, symlinks, monorepo worktrees, redaction, init."""

    def git_repo(self):
        _git(self.root, "init", "-q")
        _git(self.root, "add", "-A")
        _git(self.root, "commit", "-q", "--allow-empty", "-m", "i")

    def ignored(self, path):
        return subprocess.run(
            ["git", "-C", str(self.root), "check-ignore", "-q", "--no-index", str(path)]
        ).returncode == 0

    def test_relocate_makes_the_target_ignored_before_moving_even_without_the_gitignore_line(self):
        self.git_repo()
        gi = self.root / ".gitignore"
        gi.write_text(gi.read_text().replace(".dev-team-agents/credentials.local.json", "#gone"))
        self.assertFalse(self.ignored(self.target))
        self.put(self.user_data, CONTENT)
        cl.relocate(self.root)
        self.assertEqual(self.target.read_text(), CONTENT)
        self.assertTrue(self.ignored(self.target))
        self.assertTrue(self.ignored(str(self.target) + ".abc.tmp"))

    def test_relocate_refuses_when_the_target_would_stay_tracked_by_a_negation(self):
        self.git_repo()
        gi = self.root / ".gitignore"
        gi.write_text(gi.read_text() + "\n!.dev-team-agents/credentials.local.json\n")
        self.put(self.user_data, CONTENT)
        with self.assertRaises(EnvError):
            cl.relocate(self.root)
        self.assertEqual(self.user_data.read_text(), CONTENT)
        self.assertFalse(self.target.exists())

    def test_a_symlinked_legacy_copy_is_reported_never_followed(self):
        victim = Path(tempfile.mkdtemp(prefix="cl-victim-")) / "config.json"
        self.addCleanup(__import__("shutil").rmtree, str(victim.parent), True)
        victim.write_text("victim")
        os.chmod(str(victim), 0o644)
        self.user_data.parent.mkdir(parents=True, exist_ok=True)
        os.symlink(str(victim), str(self.user_data))
        report = cl.relocate(self.root)
        self.assertEqual([c["reason"] for c in report["conflicts"]], ["symlink"])
        self.assertFalse(self.target.exists())
        self.assertTrue(self.user_data.is_symlink())
        self.assertEqual(_mode(victim), 0o644)

    def test_a_symlinked_dev_team_agents_dir_is_refused(self):
        outside = Path(tempfile.mkdtemp(prefix="cl-out-"))
        self.addCleanup(__import__("shutil").rmtree, str(outside), True)
        alias = self.root / "alias"
        os.symlink(str(outside), str(alias))
        (alias / ".dev-team-agents").mkdir()
        with mock.patch.object(cl, "main_root", return_value=self.root), mock.patch.object(
            cl, "file_path", return_value=alias / ".dev-team-agents" / cl.FILE_NAME
        ):
            with self.assertRaises(EnvError):
                cl.init(self.root)
        self.assertFalse((outside / ".dev-team-agents" / cl.FILE_NAME).exists())

    def test_init_never_overwrites_a_file_that_appears_meanwhile(self):
        real_link = os.link

        def racing(src, dst, **kwargs):
            if str(dst) == str(self.target):
                self.put(self.target, "hand edit")
            return real_link(src, dst, **kwargs)

        with mock.patch("os.link", side_effect=racing):
            with self.assertRaises(ConflictError) as caught:
                cl.init(self.root)
        self.assertEqual(caught.exception.details["reason"], "exists")
        self.assertEqual(self.target.read_text(), "hand edit")

    def test_conflicts_carry_a_reason_the_app_matches_on(self):
        self.put(self.target, CONTENT)
        with self.assertRaises(ConflictError) as caught:
            cl.init(self.root)
        self.assertEqual(caught.exception.details["reason"], "exists")
        with self.assertRaises(ConflictError) as caught:
            cl.apply_patch(self.root, [{"op": "unset", "pointer": "/x"}], "0" * 64)
        self.assertEqual(caught.exception.details["reason"], "hash-conflict")

    def test_store_copy_is_ignored_unless_the_registry_binds_this_project_here(self):
        self.put(self.store_copy, CONTENT)
        with mock.patch.object(cl.registry, "get", return_value={"path": "/somewhere/else"}):
            self.assertNotIn(self.store_copy, cl.legacy_paths(self.root, self.pid))
        self.assertIn(self.store_copy, cl.legacy_paths(self.root, self.pid))

    def test_safe_leaf_names_are_exactly_the_templates_non_secret_nested_leaves(self):
        names = set()

        def walk(node, depth):
            if isinstance(node, dict):
                for key, item in node.items():
                    if isinstance(item, (dict, list)):
                        walk(item, depth + 1)
                    elif depth > 0 and not cl._secret_ish(key):
                        names.add(key.lower())
            elif isinstance(node, list):
                for item in node:
                    walk(item, depth)

        walk(cl.load_template(), 0)
        self.assertEqual(names, set(cl.SAFE_LEAF_NAMES))

    def test_secret_looking_values_are_hidden_under_safe_names(self):
        self.put(self.target, json.dumps({
            "work_feedback_active": "yes-token",
            "work_feedback_interval_minutes": True,
            "devops": {"staging": {
                "ssh": {"privateKeyPath": "-----BEGIN OPENSSH PRIVATE KEY-----\nAAA"},
                "database": [{"database": "postgres://u:%s@h/db" % PLANTED, "host": "db"}],
            }},
            "app": {"staging": {"appUrl": "https://h/cb?token=%s" % PLANTED}},
        }))
        state = cl.show(self.root)
        dumped = json.dumps(state)
        self.assertNotIn(PLANTED, dumped)
        self.assertNotIn("BEGIN OPENSSH", dumped)
        self.assertNotIn("yes-token", dumped)
        data = state["data"]
        self.assertEqual(data["work_feedback_interval_minutes"], {"secret": True, "set": True})
        self.assertEqual(data["devops"]["staging"]["database"][0]["host"], "db")


class MonorepoWorktreeTest(StoreTestCase):
    def test_a_subproject_opened_from_a_worktree_keeps_its_offset(self):
        self.install_version("3.0.0", activate=True)
        mono = self.new_project()
        sub = mono / "apps" / "x"
        sub.mkdir(parents=True)
        _git(mono, "init", "-q")
        (sub / "keep").write_text("k")
        _git(mono, "add", "-A")
        _git(mono, "commit", "-q", "-m", "i")
        wt = Path(tempfile.mkdtemp(prefix="cl-mono-")) / "wt"
        self.addCleanup(__import__("shutil").rmtree, str(wt.parent), True)
        _git(mono, "worktree", "add", "-q", str(wt), "-b", "side")
        expected = (mono / "apps" / "x" / ".dev-team-agents" / cl.FILE_NAME).resolve()
        self.assertEqual(cl.file_path(wt / "apps" / "x").resolve(), expected)
        self.assertEqual(cl.file_path(sub).resolve(), expected)

    def test_inherited_git_dir_does_not_redirect_the_resolution(self):
        self.install_version("3.0.0", activate=True)
        root = self.new_project()
        other = Path(tempfile.mkdtemp(prefix="cl-other-"))
        self.addCleanup(__import__("shutil").rmtree, str(other), True)
        _git(other, "init", "-q")
        with mock.patch.dict(os.environ, {"GIT_DIR": str(other / ".git")}):
            self.assertEqual(cl.file_path(root), root / ".dev-team-agents" / cl.FILE_NAME)

if __name__ == "__main__":
    unittest.main()


class InstallScriptTest(unittest.TestCase):
    """`install.sh` downloads its payload, so its credentials handling is pinned by structure."""

    def setUp(self):
        self.text = (REPO_ROOT / "scripts" / "install.sh").read_text(encoding="utf-8")

    def test_the_swap_carries_the_root_file_into_the_staged_tree_before_moving_the_old_one(self):
        carry = self.text.index('cp -p "$INSTALL_DIR/credentials.local.json" "$NEW_DIR/credentials.local.json"')
        aside = self.text.index('OLD_DIR="$INSTALL_DIR.old.$$"')
        self.assertLess(carry, aside)

    def test_the_relocation_runs_only_after_the_gitignore_lines_cover_the_target(self):
        ignore = self.text.index('_add_gitignore ".dev-team-agents/credentials.local.json"')
        move = self.text.index('mv "$_CRED_OLD" "$_CRED_NEW"')
        self.assertLess(ignore, move)

    def test_install_never_writes_a_template_and_never_follows_a_symlink(self):
        self.assertNotIn("work_feedback_interval_minutes", self.text)
        self.assertIn('[ ! -L "$_CRED_OLD" ]', self.text)
        self.assertIn('[ ! -L "$_CRED_NEW" ]', self.text)
