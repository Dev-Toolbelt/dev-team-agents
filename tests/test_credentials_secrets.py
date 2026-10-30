"""Secrets by reference in the local credentials file (ADR-0053).

The OS secret store is replaced by an in-memory fake; the user's real keychain is never read.
"""

from __future__ import annotations

import json
import os
import re
import unittest
from contextlib import contextmanager
from unittest import mock

from test_credentials_local import LocalCredsCase, _git

from devteam import credentials_local as cl
from devteam import doctor, paths
from devteam import secrets as secret_store
from devteam.errors import DevteamError, EnvError, UsageError

PW = "pl4nted-PW-7c1e"
UUID = "0b9f6c1e-4d2a-4f7e-9a31-5c8d2e7b1a40"
BASE = {"app": {"staging": {"appUrl": "https://s.test", "user": "qa"}}}


class FakeStore:
    def __init__(self, backend="keychain"):
        self.values, self.backend = {}, backend
        self.fail_delete = False

    def _put(self, ref, value):
        self.values[ref] = value

    def _delete(self, ref):
        if self.fail_delete:
            raise RuntimeError("delete failed")
        return self.values.pop(ref, None) is not None

    @contextmanager
    def active(self):
        name = self.backend
        with mock.patch.dict(secret_store._PUT, {name: self._put}), \
                mock.patch.dict(secret_store._GET, {name: lambda r: self.values.get(r)}), \
                mock.patch.dict(secret_store._DELETE, {name: self._delete}), \
                mock.patch.object(secret_store, "default_backend", lambda: name):
            yield self


class SecretCase(LocalCredsCase):
    def write(self, doc):
        self.put(self.target, json.dumps(doc, indent=2))
        return cl.show(self.root)["hash"]

    def patch(self, ops, doc=None):
        h = self.write(doc) if doc is not None else cl.show(self.root)["hash"]
        return cl.apply_patch(self.root, ops, h)

    def disk(self):
        return json.loads(self.target.read_text())

    def audit_text(self):
        log = paths.audit_log(self.pid)
        return log.read_text() if log.exists() else ""


class SetSecretTest(SecretCase):
    def test_value_goes_to_the_store_and_a_reference_to_the_file(self):
        with FakeStore().active() as fake:
            state = self.patch([{"op": "set-secret", "pointer": "/app/staging/password", "value": PW}], BASE)
            leaf = self.disk()["app"]["staging"]["password"]
            self.assertEqual(set(leaf), {"$ref", "$backend"})
            self.assertTrue(re.match(r"^devteam/%s/local/[0-9a-f]{32}$" % self.pid, leaf["$ref"]))
            self.assertEqual(leaf["$backend"], "keychain")
            self.assertEqual(fake.values[leaf["$ref"]], PW)
        self.assertNotIn(PW, self.target.read_text())
        self.assertNotIn(PW, json.dumps(state))
        self.assertIn("password", self.disk()["app"]["staging"]["$secrets"])
        shown = state["data"]["app"]["staging"]["password"]
        self.assertEqual(shown, {"secret": True, "set": True, "marked": True, "stored": "keychain"})

    def test_replace_reuses_the_ref(self):
        with FakeStore().active() as fake:
            op = {"op": "set-secret", "pointer": "/app/staging/password", "value": PW}
            self.patch([op], BASE)
            first = self.disk()["app"]["staging"]["password"]["$ref"]
            self.patch([dict(op, value="other-value")])
            self.assertEqual(self.disk()["app"]["staging"]["password"]["$ref"], first)
            self.assertEqual(fake.values, {first: "other-value"})

    def test_unset_deletes_the_stored_value_and_move_keeps_it(self):
        with FakeStore().active() as fake:
            self.patch([{"op": "set-secret", "pointer": "/app/staging/password", "value": PW}], BASE)
            ref = self.disk()["app"]["staging"]["password"]["$ref"]
            self.patch([{"op": "move", "from": "/app/staging/password", "pointer": "/app/staging/pw2"}])
            self.assertEqual(self.disk()["app"]["staging"]["pw2"]["$ref"], ref)
            self.assertEqual(fake.values, {ref: PW})
            self.patch([{"op": "unset", "pointer": "/app/staging/pw2"}])
            self.assertEqual(fake.values, {})

    def test_failed_patch_puts_the_store_back(self):
        with FakeStore().active() as fake:
            ops = [
                {"op": "set-secret", "pointer": "/app/staging/password", "value": PW},
                {"op": "move", "from": "/nope", "pointer": "/x"},
            ]
            with self.assertRaises(UsageError):
                self.patch(ops, BASE)
            self.assertEqual(fake.values, {})
        self.assertNotIn("$ref", self.target.read_text())

    def test_oversized_and_multiline_values_are_refused(self):
        with FakeStore().active():
            for value, reason in (("x" * 4000, "value-too-large"), ("a\nb", "invalid-secret-value")):
                with self.assertRaises(UsageError) as ctx:
                    self.patch([{"op": "set-secret", "pointer": "/a/password", "value": value}], BASE)
                self.assertEqual(ctx.exception.details["reason"], reason)

    def test_an_ancestor_unset_also_deletes(self):
        with FakeStore().active() as fake:
            self.patch([{"op": "set-secret", "pointer": "/app/staging/password", "value": PW}], BASE)
            self.patch([{"op": "unset", "pointer": "/app"}])
            self.assertEqual(fake.values, {})

    def test_a_foreign_project_ref_is_refused(self):
        foreign = {"$ref": "devteam/other-project/local/" + "a" * 32, "$backend": "keychain"}
        with FakeStore().active():
            with self.assertRaises(UsageError):
                self.patch([{"op": "set", "pointer": "/a/password", "value": foreign}], BASE)


class ProductionTest(SecretCase):
    PROD = {"prod": {"$production": True, "url": "https://p.test"}}

    def test_plain_set_of_a_secret_is_refused(self):
        with self.assertRaises(UsageError) as ctx:
            self.patch([{"op": "set", "pointer": "/prod/password", "value": PW}], self.PROD)
        self.assertEqual(ctx.exception.details["reason"], "plaintext-in-production")
        self.assertNotIn(PW, json.dumps(ctx.exception.payload()))
        self.assertNotIn("password", self.target.read_text())

    def test_a_moved_plaintext_secret_is_refused_too(self):
        doc = {"dev": {"password": PW}, "prod": {"$production": True}}
        with self.assertRaises(UsageError) as ctx:
            self.patch([{"op": "move", "from": "/dev/password", "pointer": "/prod/password"}], doc)
        self.assertEqual(ctx.exception.details["reason"], "plaintext-in-production")

    def test_set_secret_is_accepted(self):
        with FakeStore().active():
            self.patch([{"op": "set-secret", "pointer": "/prod/password", "value": PW}], self.PROD)
        self.assertIn("$ref", self.disk()["prod"]["password"])

    def test_insecure_backend_is_refused_only_in_production(self):
        with FakeStore("insecure").active():
            with self.assertRaises(EnvError) as ctx:
                self.patch([{"op": "set-secret", "pointer": "/prod/password", "value": PW}], self.PROD)
            self.assertEqual(ctx.exception.details["reason"], "insecure-backend-in-production")
            self.patch([{"op": "set-secret", "pointer": "/app/password", "value": PW}], {"app": {}})
        self.assertEqual(self.disk()["app"]["password"]["$backend"], "insecure")

    def test_existing_plaintext_stays_readable_and_untouched(self):
        doc = {"prod": {"$production": True, "password": PW}}
        self.patch([{"op": "set", "pointer": "/prod/url", "value": "u"}], doc)
        self.assertEqual(self.disk()["prod"]["password"], PW)


class ReferenceLeafTest(SecretCase):
    def test_op_and_bw_refs_are_hidden_and_labelled(self):
        doc = {"a": {"password": {"$ref": "op://Vault/Item/password"}, "token": {"$ref": "bw://%s/api key" % UUID}}}
        self.write(doc)
        data = cl.show(self.root)["data"]["a"]
        self.assertEqual(data["password"]["stored"], "op")
        self.assertEqual(data["token"]["stored"], "bw")
        self.assertTrue(data["password"]["secret"])

    def test_malformed_refs_are_rejected_on_write_and_hidden_on_read(self):
        for bad in ({"$ref": "nope"}, {"$ref": "op://v/i/f", "extra": 1}, {"$ref": 5}):
            with self.assertRaises(UsageError) as ctx:
                self.patch([{"op": "set", "pointer": "/a/password", "value": bad}], BASE)
            self.assertEqual(ctx.exception.details["reason"], "invalid-ref")
        self.write({"a": {"password": {"$ref": "nope"}}})
        self.assertEqual(cl.show(self.root)["data"]["a"]["password"]["stored"], "invalid")

    def test_copy_value_resolves_each_kind_and_the_ref_never_leaks_a_value(self):
        with FakeStore().active() as fake:
            self.patch([{"op": "set-secret", "pointer": "/a/password", "value": PW}], BASE)
            self.patch([
                {"op": "set", "pointer": "/a/opw", "value": {"$ref": "op://V/I/f"}},
                {"op": "set", "pointer": "/a/bwt", "value": {"$ref": "bw://%s/password" % UUID}},
            ])
            h = cl.show(self.root)["hash"]
            item = {"login": {"password": "bw-value"}}
            with mock.patch.object(cl, "_vendor", side_effect=lambda argv: "op-value\n" if argv[0] == "op" else json.dumps(item)):
                self.assertEqual(cl.copy_value(self.root, "/a/password", h)["value"], PW)
                self.assertEqual(cl.copy_value(self.root, "/a/opw", h)["value"], "op-value")
                self.assertEqual(cl.copy_value(self.root, "/a/bwt", h)["value"], "bw-value")

    def test_a_missing_vendor_cli_fails_loudly(self):
        with mock.patch.object(cl.shutil, "which", return_value=None):
            with self.assertRaises(EnvError) as ctx:
                cl.resolve_leaf({"$ref": "op://V/I/f"}, self.pid, "t", "/p", root=self.root)
        self.assertEqual(ctx.exception.details["reason"], "cli-missing")

    def test_resolution_is_audited_without_the_value(self):
        with FakeStore().active():
            self.patch([{"op": "set-secret", "pointer": "/a/password", "value": PW}], BASE)
            leaf = self.disk()["a"]["password"]
            cl.resolve_leaf(leaf, self.pid, "local-exec", "/a/password", root=self.root)
        lines = [json.loads(x) for x in self.audit_text().splitlines()]
        self.assertTrue(any(x["action"] == "local-exec" and x["key"] == "/a/password" for x in lines))
        self.assertNotIn(PW, self.audit_text())


class SecureTest(SecretCase):
    DOC = {"a": {"password": PW, "url": "u"}, "prod": {"$production": True, "token": "tok-9"}}

    def test_list_changes_nothing(self):
        self.write(self.DOC)
        before = self.target.read_bytes()
        result = cl.secure(self.root)
        self.assertEqual(
            sorted((x["pointer"], x["production"]) for x in result["secrets"]),
            [("/a/password", False), ("/prod/token", True)],
        )
        self.assertEqual(set(result), {"path", "secrets", "hash"})
        self.assertEqual(self.target.read_bytes(), before)

    def test_apply_moves_selected_values(self):
        self.write(self.DOC)
        with FakeStore().active() as fake:
            result = cl.secure(self.root, apply=True, pointers=["/a/password"])
            self.assertEqual([x["pointer"] for x in result["secrets"]], ["/prod/token"])
            self.assertEqual(list(fake.values.values()), [PW])
        text = self.target.read_text()
        self.assertNotIn(PW, text)
        self.assertIn("tok-9", text)
        self.assertEqual(result["hash"], cl.show(self.root)["hash"])

    def test_apply_is_all_or_nothing(self):
        self.write({"a": {"password": PW, "token": "x" * 4000}})
        before = self.target.read_bytes()
        with FakeStore().active() as fake:
            with self.assertRaises(UsageError) as ctx:
                cl.secure(self.root, apply=True)
            self.assertEqual(fake.values, {})
        self.assertEqual(ctx.exception.details["reason"], "value-too-large")
        self.assertEqual(self.target.read_bytes(), before)

    def test_unknown_pointer_is_refused(self):
        self.write(self.DOC)
        with FakeStore().active():
            with self.assertRaises(UsageError):
                cl.secure(self.root, apply=True, pointers=["/a/url"])

    def test_cli_list_json(self):
        self.write(self.DOC)
        code, out, err = self.run_cli("cred", "local", "secure", "--path", str(self.root), "--json")
        self.assertEqual(code, 0, err)
        body = json.loads(out)
        self.assertEqual(set(body), {"ok", "path", "secrets", "hash"})
        self.assertNotIn(PW, out)


class DoctorTest(SecretCase):
    def test_plaintext_secret_findings(self):
        self.write({"a": {"password": PW}, "prod": {"$production": True, "token": "t"}})
        findings, _a, _r = doctor.check_credentials_local(self.root)
        mine = {f["message"].split(" ")[0]: f["level"] for f in findings if f["category"] == "plaintext-secret"}
        self.assertEqual(mine, {"/a/password": "info", "/prod/token": "fail"})
        self.assertNotIn(PW, json.dumps(findings))


class ExecTest(SecretCase):
    def test_env_names(self):
        self.assertEqual(cl.env_name("appUrl"), "APP_URL")
        self.assertEqual(cl.env_name("totp-secret"), "TOTP_SECRET")
        self.assertIsNone(cl.env_name("$$"))

    def test_environment_resolves_refs_and_skips_containers(self):
        with FakeStore().active():
            self.patch([{"op": "set-secret", "pointer": "/g/password", "value": PW}], {"g": {"appUrl": "u", "n": 3, "on": True, "sub": {"x": 1}, "z": None}})
            env = cl.group_environment(self.root, "/g", self.pid)
        self.assertEqual(env, {"DEVTEAM_APP_URL": "u", "DEVTEAM_N": "3", "DEVTEAM_ON": "true", "DEVTEAM_PASSWORD": PW})

    def test_collisions_are_refused(self):
        self.write({"g": {"appUrl": "a", "app_url": "b"}})
        with self.assertRaises(UsageError):
            cl.group_environment(self.root, "/g", self.pid)

    def test_cli_runs_the_child_with_the_environment_and_its_exit_code(self):
        self.write({"g": {"appUrl": "https://x.test"}})
        code, out, err = self.run_cli(
            "cred", "local", "exec", "--path", str(self.root), "/g", "--", "sh", "-c", 'echo "$DEVTEAM_APP_URL"; exit 7'
        )
        self.assertEqual(code, 7, err)
        self.assertEqual(out.strip(), "https://x.test")

    def test_cli_refuses_json_and_missing_command(self):
        self.write({"g": {"appUrl": "u"}})
        code, out, _ = self.run_cli("cred", "local", "exec", "--path", str(self.root), "/g", "--json", "--", "true")
        self.assertEqual(code, 2)
        self.assertFalse(json.loads(out)["ok"])
        code, _, _ = self.run_cli("cred", "local", "exec", "--path", str(self.root), "/g")
        self.assertEqual(code, 2)


class TrackedFileTest(SecretCase):
    DOC = {"g": {"password": {"$ref": "op://V/I/f"}, "appUrl": "u"}}

    def track(self):
        self.write(self.DOC)
        _git(self.root, "add", "-f", str(self.target))

    def test_no_reference_resolves_from_a_tracked_file(self):
        self.track()
        h = cl.show(self.root)["hash"]
        with mock.patch.object(cl, "_vendor", return_value="v") as vendor:
            with self.assertRaises(EnvError) as ctx:
                cl.copy_value(self.root, "/g/password", h)
            self.assertEqual((ctx.exception.details["reason"], ctx.exception.exit_code), ("tracked-file", 3))
            with self.assertRaises(EnvError) as ctx:
                cl.group_environment(self.root, "/g", self.pid)
            self.assertEqual(ctx.exception.details["reason"], "tracked-file")
            vendor.assert_not_called()

    def test_refusal_is_audited_and_untracked_files_resolve(self):
        self.write(self.DOC)
        h = cl.show(self.root)["hash"]
        with mock.patch.object(cl, "_vendor", return_value="v\n"):
            self.assertEqual(cl.copy_value(self.root, "/g/password", h)["value"], "v")
        self.track()
        code, out, _ = self.run_cli(
            "cred", "local", "copy-value", "--pointer", "/g/password", "--expect-hash", h,
            "--path", str(self.root), "--json",
        )
        self.assertEqual(code, 3)
        self.assertEqual(json.loads(out)["details"]["reason"], "tracked-file")
        self.assertIn("refused", self.audit_text())

    def test_exec_cli_refuses(self):
        self.track()
        code, out, _ = self.run_cli("cred", "local", "exec", "--path", str(self.root), "/g", "--", "true")
        self.assertEqual(code, 3)

    def git_answers(self, *answers):
        return mock.patch.object(cl, "_git_rc", side_effect=list(answers))

    def test_a_non_git_directory_is_allowed(self):
        with self.git_answers((128, "")):
            self.assertEqual(cl.tracked_state(self.root), "not-a-repo")
        with self.git_answers((0, "false")):
            self.assertEqual(cl.tracked_state(self.root), "not-a-repo")

    def test_inside_a_repository_only_exit_one_means_untracked(self):
        for answers, state in (
            (((0, "true"), (1, "")), "untracked"),
            (((0, "true"), (0, "")), "tracked"),
            (((0, "true"), (128, "")), "unknown"),
            (((0, "true"), (None, "")), "unknown"),
            (((None, ""),), "unknown"),
            (((69, ""),), "unknown"),
            (((-1, ""),), "not-a-repo"),
        ):
            with self.git_answers(*answers):
                self.assertEqual(cl.tracked_state(self.root), state, answers)

    def test_unknown_is_refused_and_audited(self):
        self.write(self.DOC)
        h = cl.show(self.root)["hash"]
        with self.git_answers((0, "true"), (128, "")), mock.patch.object(cl, "_vendor", return_value="v") as vendor:
            with self.assertRaises(EnvError) as ctx:
                cl.copy_value(self.root, "/g/password", h)
            vendor.assert_not_called()
        self.assertEqual((ctx.exception.details["reason"], ctx.exception.exit_code), ("tracked-file-unknown", 3))
        with self.git_answers((0, "true"), (128, "")):
            with self.assertRaises(EnvError):
                cl.group_environment(self.root, "/g", self.pid)
        self.assertIn("tracked-file-unknown", self.audit_text())

    def test_git_runs_literal_and_without_dangerous_environment(self):
        env = {"GIT_CEILING_DIRECTORIES": "/", "GIT_GLOB_PATHSPECS": "1", "GIT_CONFIG_COUNT": "1",
               "GIT_CONFIG_KEY_0": "core.worktree", "GIT_DIR": "/x", "GIT_AUTHOR_NAME": "keep", "PATH": os.environ["PATH"]}
        with mock.patch.dict(os.environ, env, clear=True), mock.patch.object(cl.subprocess, "run") as run:
            run.return_value = mock.Mock(returncode=0, stdout=b"true\n")
            cl._git_rc(self.root, "rev-parse", "--is-inside-work-tree")
        args, kwargs = run.call_args
        self.assertEqual(args[0][:3], ["git", "--literal-pathspecs", "-C"])
        self.assertEqual(set(kwargs["env"]), {"GIT_AUTHOR_NAME", "PATH"})


class ProductionExecTest(SecretCase):
    def test_production_group_needs_the_flag(self):
        self.write({"p": {"$production": True, "appUrl": "https://p.test"}})
        with self.assertRaises(UsageError) as ctx:
            cl.group_environment(self.root, "/p", self.pid)
        self.assertEqual(ctx.exception.details["reason"], "production-flag-required")
        self.assertEqual(cl.group_environment(self.root, "/p", self.pid, allow_production=True),
                         {"DEVTEAM_APP_URL": "https://p.test"})

    def test_cli(self):
        self.write({"p": {"$production": True, "appUrl": "u"}})
        code, out, _ = self.run_cli("cred", "local", "exec", "--path", str(self.root), "/p", "--", "true")
        self.assertEqual(code, 2)
        code, out, err = self.run_cli(
            "cred", "local", "exec", "--production", "--path", str(self.root), "/p", "--", "sh", "-c", "exit 5"
        )
        self.assertEqual(code, 5, err)


class InsecureInProductionTest(SecretCase):
    def leaf(self, backend="insecure"):
        return {"$ref": "devteam/%s/local/%s" % (self.pid, "ab" * 16), "$backend": backend}

    def refused(self, ops, doc):
        with self.assertRaises(EnvError) as ctx:
            self.patch(ops, doc)
        self.assertEqual(ctx.exception.details["reason"], "insecure-backend-in-production")
        return ctx.exception

    def test_move_set_and_marking_a_group_production_are_refused(self):
        doc = {"dev": {"password": self.leaf()}, "prod": {"$production": True}, "grp": {"password": self.leaf()}}
        self.refused([{"op": "move", "from": "/dev/password", "pointer": "/prod/password"}], doc)
        self.refused([{"op": "set", "pointer": "/prod/password", "value": self.leaf()}], doc)
        self.refused([{"op": "set", "pointer": "/grp/$production", "value": True}], doc)
        self.assertNotIn("password", self.disk()["prod"])

    def test_other_backends_and_existing_ones_are_untouched(self):
        doc = {"prod": {"$production": True, "password": self.leaf()}}
        self.patch([{"op": "set", "pointer": "/prod/url", "value": "u"}], doc)
        self.patch([{"op": "set", "pointer": "/prod/pw2", "value": self.leaf("keychain")}])

    def test_doctor_fails_an_existing_one(self):
        self.write({"prod": {"$production": True, "password": self.leaf()}})
        findings, _a, _r = doctor.check_credentials_local(self.root)
        bad = [f for f in findings if f["category"] == "insecure-backend"]
        self.assertEqual([f["level"] for f in bad], ["fail"])


class FullMatchTest(SecretCase):
    def test_a_trailing_newline_is_not_a_reference(self):
        pid = self.pid
        for ref, backend in (
            ("op://V/I/f\n", None),
            ("bw://%s/password\n" % UUID, None),
            ("devteam/%s/local/%s\n" % (pid, "ab" * 16), "keychain"),
        ):
            leaf = {"$ref": ref}
            if backend:
                leaf["$backend"] = backend
            self.assertIsNone(cl.ref_kind(leaf), ref)


class BitwardenIdTest(SecretCase):
    def test_item_id_must_be_a_uuid(self):
        for bad in ("bw://item-1/password", "bw://--help/password", "bw://" + UUID + "x/password"):
            with self.assertRaises(UsageError) as ctx:
                self.patch([{"op": "set", "pointer": "/a/password", "value": {"$ref": bad}}], BASE)
            self.assertEqual(ctx.exception.details["reason"], "invalid-ref")
        self.patch([{"op": "set", "pointer": "/a/password", "value": {"$ref": "bw://%s/password" % UUID}}])


class RollbackTest(SecretCase):
    def test_reused_ref_gets_its_previous_value_back(self):
        with FakeStore().active() as fake:
            self.patch([{"op": "set-secret", "pointer": "/a/password", "value": PW}], BASE)
            ref = self.disk()["a"]["password"]["$ref"]
            ops = [
                {"op": "set-secret", "pointer": "/a/password", "value": "new-value"},
                {"op": "move", "from": "/nope", "pointer": "/x"},
            ]
            with self.assertRaises(UsageError):
                self.patch(ops)
            self.assertEqual(fake.values, {ref: PW})

    def test_failed_file_write_rolls_back(self):
        self.write(BASE)
        before = self.target.read_bytes()
        with FakeStore().active() as fake:
            with mock.patch.object(cl, "_write_bytes", side_effect=EnvError("disk full")):
                with self.assertRaises(EnvError):
                    cl.apply_patch(self.root, [{"op": "set-secret", "pointer": "/a/password", "value": PW}],
                                   cl.show(self.root)["hash"])
            self.assertEqual(fake.values, {})
        self.assertEqual(self.target.read_bytes(), before)

    def test_a_rollback_that_fails_is_audited_with_the_ref(self):
        with FakeStore().active() as fake:
            fake.fail_delete = True
            with self.assertRaises(UsageError):
                self.patch([
                    {"op": "set-secret", "pointer": "/a/password", "value": PW},
                    {"op": "move", "from": "/nope", "pointer": "/x"},
                ], BASE)
            (ref,) = fake.values
        lines = [json.loads(x) for x in self.audit_text().splitlines()]
        failed = [x for x in lines if x.get("outcome") == "rollback-failed"]
        self.assertEqual([x["detail"]["ref"] for x in failed], [ref])
        self.assertNotIn(PW, self.audit_text())

    def test_a_failed_delete_after_unset_is_audited_with_the_ref(self):
        with FakeStore().active() as fake:
            self.patch([{"op": "set-secret", "pointer": "/a/password", "value": PW}], BASE)
            (ref,) = fake.values
            fake.fail_delete = True
            self.patch([{"op": "unset", "pointer": "/a/password"}])
        lines = [json.loads(x) for x in self.audit_text().splitlines()]
        self.assertEqual([x["detail"]["ref"] for x in lines if x.get("outcome") == "delete-failed"], [ref])

    def test_secure_apply_refuses_production_on_the_insecure_backend(self):
        self.write({"prod": {"$production": True, "token": "tok-9"}, "dev": {"password": PW}})
        before = self.target.read_bytes()
        with FakeStore("insecure").active() as fake:
            with self.assertRaises(EnvError) as ctx:
                cl.secure(self.root, apply=True)
            self.assertEqual(fake.values, {})
        self.assertEqual(ctx.exception.details["reason"], "insecure-backend-in-production")
        self.assertEqual(self.target.read_bytes(), before)


class LockAndReadTest(SecretCase):
    def test_locks_are_taken_in_order(self):
        order = []

        @contextmanager
        def fake_lock(name, *a, **k):
            order.append(name)
            yield

        with FakeStore().active(), mock.patch.object(cl, "store_lock", fake_lock):
            self.patch([{"op": "set-secret", "pointer": "/a/password", "value": PW}], BASE)
            self.assertEqual(order, ["credentials-local", "credentials"])
            del order[:]
            cl.secure(self.root, apply=True)
            self.assertEqual(order, ["credentials-local", "credentials"])

    def test_list_reads_the_file_once(self):
        self.write({"a": {"password": PW}})
        with mock.patch.object(cl, "_read_raw", wraps=cl._read_raw) as read:
            cl.secure(self.root)
        self.assertEqual(read.call_count, 1)

    def test_apply_message_names_the_backend(self):
        import argparse

        from devteam import cli

        self.write({"a": {"password": PW}})
        ns = argparse.Namespace(path=str(self.root), apply=True, pointer=None)
        with FakeStore("insecure").active():
            _result, human = cli.cmd_cred_local_secure(ns, None)
        self.assertIn("INSECURE", human)
        self.write({"a": {"password": PW}})
        with FakeStore("keychain").active():
            _result, human = cli.cmd_cred_local_secure(ns, None)
        self.assertIn("keychain", human)
        self.assertNotIn("INSECURE", human)


class FailureAuditTest(SecretCase):
    def test_a_failed_resolution_is_audited(self):
        leaf = {"$ref": "devteam/%s/local/%s" % (self.pid, "cd" * 16), "$backend": "keychain"}
        self.write({"g": {"password": leaf}})
        with FakeStore().active():
            with self.assertRaises(EnvError):
                cl.group_environment(self.root, "/g", self.pid)
            with self.assertRaises(EnvError):
                cl.resolve_leaf(leaf, self.pid, "local-copy", "/g/password", root=self.root)
        lines = [json.loads(x) for x in self.audit_text().splitlines()]
        self.assertEqual(
            [(x["action"], x["key"], x["outcome"]) for x in lines],
            [("local-exec", "/g/password", "failed"), ("local-copy", "/g/password", "failed")],
        )


if __name__ == "__main__":
    unittest.main()
