"""Archive hardening, and the parts of the --json contract that were broken."""

import io
import json
import os
import shutil
import tarfile
import unittest
from pathlib import Path

from devteam_support import StoreTestCase

from devteam import bind, doctor, migrate, providers, update, versions
from devteam.errors import EnvError, UsageError


def _archive(path, members):
    with tarfile.open(str(path), "w:gz") as tar:
        for member, data in members:
            if data is None:
                tar.addfile(member)
            else:
                member.size = len(data)
                tar.addfile(member, io.BytesIO(data))
    return path


class ArchiveSafetyTest(StoreTestCase):
    """Every member class that could write outside the extraction directory."""

    def _members(self, archive):
        with tarfile.open(str(archive)) as tar:
            return list(update._safe_members(tar))

    def test_rejects_a_symlink_with_an_absolute_target(self):
        member = tarfile.TarInfo("root/escape")
        member.type = tarfile.SYMTYPE
        member.linkname = "/etc"
        archive = _archive(self.tmp / "a.tar.gz", [(member, None)])
        with self.assertRaises(EnvError):
            self._members(archive)

    def test_rejects_a_symlink_climbing_out_of_the_tree(self):
        member = tarfile.TarInfo("root/up")
        member.type = tarfile.SYMTYPE
        member.linkname = "../../../../tmp"
        archive = _archive(self.tmp / "b.tar.gz", [(member, None)])
        with self.assertRaises(EnvError):
            self._members(archive)

    def test_rejects_a_hardlink_escaping_the_tree(self):
        member = tarfile.TarInfo("root/link")
        member.type = tarfile.LNKTYPE
        member.linkname = "../../outside"
        archive = _archive(self.tmp / "c.tar.gz", [(member, None)])
        with self.assertRaises(EnvError):
            self._members(archive)

    def test_rejects_device_and_fifo_members(self):
        for kind, name in ((tarfile.CHRTYPE, "dev"), (tarfile.FIFOTYPE, "fifo")):
            member = tarfile.TarInfo("root/" + name)
            member.type = kind
            archive = _archive(self.tmp / "{}.tar.gz".format(name), [(member, None)])
            with self.assertRaises(EnvError):
                self._members(archive)

    def test_rejects_traversal_in_a_member_name(self):
        archive = _archive(self.tmp / "d.tar.gz", [(tarfile.TarInfo("../outside"), b"x")])
        with self.assertRaises(EnvError):
            self._members(archive)

    def test_accepts_an_ordinary_member(self):
        archive = _archive(self.tmp / "ok.tar.gz", [(tarfile.TarInfo("root/file.txt"), b"x")])
        self.assertEqual([m.name for m in self._members(archive)], ["root/file.txt"])

    def test_a_relative_symlink_inside_the_tree_is_allowed(self):
        member = tarfile.TarInfo("root/sub/link")
        member.type = tarfile.SYMTYPE
        member.linkname = "../target"
        archive = _archive(self.tmp / "rel.tar.gz", [(member, None)])
        self.assertEqual([m.name for m in self._members(archive)], ["root/sub/link"])


class RefAndDigestTest(StoreTestCase):
    def test_a_ref_that_retargets_the_url_is_refused_before_any_request(self):
        for bad in (
            "../../attacker/evil/archive/refs/heads/main",
            "v1.0.0?x=1",
            "v1.0.0#frag",
            "main",
            "",
        ):
            with self.assertRaises(UsageError):
                update.validate_ref(bad)

    def test_accepts_a_version_tag(self):
        self.assertEqual(update.validate_ref("v3.0.0"), "v3.0.0")
        self.assertEqual(update.validate_ref("3.0.0-rc.1"), "3.0.0-rc.1")

    def test_a_mismatched_digest_stops_the_install(self):
        with self.assertRaises(EnvError):
            update.verify_digest(b"payload", expected="0" * 64)

    def test_a_matching_digest_is_reported_as_verified(self):
        import hashlib

        payload = b"payload"
        digest = hashlib.sha256(payload).hexdigest()
        self.assertTrue(update.verify_digest(payload, expected=digest)["verified"])

    def test_absence_of_a_digest_is_reported_not_hidden(self):
        result = update.verify_digest(b"payload")
        self.assertFalse(result["verified"])
        self.assertEqual(len(result["sha256"]), 64)

    def test_only_github_over_https_is_fetched(self):
        for bad in (
            "http://github.com/x.tar.gz",
            "https://evil.example.com/x.tar.gz",
        ):
            with self.assertRaises(EnvError):
                update._check_url(bad)
        update._check_url("https://codeload.github.com/x.tar.gz")


class DelegatedArtifactTest(StoreTestCase):
    def test_only_paths_that_exist_are_recorded(self):
        root = self.new_project()
        (root / ".codex" / "agents").mkdir(parents=True)
        (root / ".codex" / "hooks.json").write_text("{}", encoding="utf-8")
        records = providers.delegated_artifacts("codex", root)
        paths = [r["path"] for r in records]
        self.assertIn(".codex/agents", paths)
        self.assertIn(".codex/hooks.json", paths)
        self.assertNotIn(".codex/skills", paths)
        self.assertTrue(all(r["kind"] == "delegated" for r in records))


class MigrateGuardTest(StoreTestCase):
    def test_migrate_refuses_a_v3_vendored_bind(self):
        self.install_version("3.0.0", activate=True)
        root = self.new_project()
        bind.bind(root, provider_names=["claude"], mode="vendored")
        with self.assertRaises(UsageError):
            migrate.plan(root)


class DoctorResilienceTest(StoreTestCase):
    def test_a_broken_store_keeps_the_findings_it_already_collected(self):
        self.install_version("3.0.0", activate=True)
        root = self.new_project()
        bind.bind(root, provider_names=["claude"])
        shutil.rmtree(str(self.home / "core"))

        report = doctor.run(project_root=root)
        self.assertEqual(report["status"], "fail")
        categories = {finding["category"] for finding in report["findings"]}
        self.assertIn("store", categories)


class ExitCodeContractTest(StoreTestCase):
    def _json(self, *args):
        code, out, err = self.run_cli(*args)
        return code, json.loads(out), err

    def test_argparse_failures_still_emit_one_json_document(self):
        for args in (
            ["teleport", "--json"],
            ["bind", "--mode", "bogus", "--json"],
            ["bind", "--provider", "bogus", "--json"],
            ["store", "install", "--json"],
        ):
            code, body, _ = self._json(*args)
            self.assertEqual(code, 2, args)
            self.assertFalse(body["ok"], args)
            self.assertIn("error", body)

    def test_doctor_returns_findings_for_a_warn_status(self):
        self.install_version("3.0.0", activate=True)
        root = self.new_project()
        self.run_cli("bind", str(root))
        target = root / ".claude" / "agents" / "dev-team"
        target.unlink()

        code, body, _ = self._json("doctor", str(root), "--json")
        self.assertEqual(code, 1)
        self.assertEqual(body["status"], "warn")
        self.assertFalse(body["ok"], "ok must not contradict status")

    def test_doctor_ok_status_exits_zero_with_ok_true(self):
        self.install_version("3.0.0", activate=True)
        root = self.new_project()
        self.run_cli("bind", str(root))
        code, body, _ = self._json("doctor", str(root), "--json")
        self.assertEqual(code, 0)
        self.assertEqual(body["status"], "ok")
        self.assertTrue(body["ok"])

    def test_sync_all_with_a_missing_project_emits_json_and_exits_one(self):
        self.install_version("3.0.0", activate=True)
        root = self.new_project("gone")
        self.run_cli("bind", str(root))
        shutil.rmtree(str(root))

        code, body, _ = self._json("sync", "--all", "--json")
        self.assertEqual(code, 1)
        self.assertFalse(body["ok"])
        self.assertTrue(body["problems"])

    def test_doctor_on_a_nonexistent_path_is_an_environment_error(self):
        self.install_version("3.0.0", activate=True)
        code, body, _ = self._json("doctor", str(self.tmp / "nope"), "--json")
        self.assertEqual(code, 3)
        self.assertFalse(body["ok"])


if __name__ == "__main__":
    unittest.main()
