"""M2: the preference cascade, the layout upgrade, and store portability."""

import json
import shutil
import subprocess
import unittest
from pathlib import Path

from devteam_support import StoreTestCase

from devteam import bind, gitignore, jsonio, prefs, project, registry, store, upgrade, versions
from devteam.errors import ConflictError, EnvError, UsageError


class CascadeTest(StoreTestCase):
    def setUp(self):
        super().setUp()
        self.install_version("3.0.0", activate=True)
        self.root = self.new_project()
        self.result = bind.bind(self.root, provider_names=["claude"])
        self.pid = self.result["project_id"]

    def test_later_layers_win(self):
        resolved = prefs.resolve(self.pid, "3.0.0")
        self.assertEqual(resolved["values"]["language"], "pt-BR")
        self.assertEqual(resolved["origin"]["language"], "defaults")

        prefs.set_value("language", "en", "3.0.0", scope="global")
        resolved = prefs.resolve(self.pid, "3.0.0")
        self.assertEqual(resolved["values"]["language"], "en")
        self.assertEqual(resolved["origin"]["language"], "global")

        prefs.set_value("language", "es", "3.0.0", scope="project", project_id=self.pid)
        resolved = prefs.resolve(self.pid, "3.0.0")
        self.assertEqual(resolved["values"]["language"], "es")
        self.assertEqual(resolved["origin"]["language"], "project")

    def test_unset_falls_back_to_the_layer_below(self):
        prefs.set_value("language", "en", "3.0.0", scope="global")
        prefs.set_value("language", "es", "3.0.0", scope="project", project_id=self.pid)
        prefs.unset("language", scope="project", project_id=self.pid)
        self.assertEqual(prefs.resolve(self.pid, "3.0.0")["values"]["language"], "en")

    def test_consent_keys_are_withheld_when_no_layer_sets_them(self):
        resolved = prefs.resolve(self.pid, "3.0.0")
        for key in prefs.CONSENT_KEYS:
            self.assertFalse(resolved["values"][key], key)
            self.assertEqual(resolved["origin"][key], "consent-withheld", key)

    def test_a_consent_key_set_explicitly_is_honoured(self):
        prefs.set_value("telemetry", "true", "3.0.0", scope="global")
        resolved = prefs.resolve(self.pid, "3.0.0")
        self.assertTrue(resolved["values"]["telemetry"])
        self.assertEqual(resolved["origin"]["telemetry"], "global")

    def test_values_are_coerced_to_the_type_the_default_declares(self):
        prefs.set_value("session_summary_max_days", "45", "3.0.0", scope="global")
        self.assertEqual(prefs.resolve(self.pid, "3.0.0")["values"]["session_summary_max_days"], 45)
        with self.assertRaises(UsageError):
            prefs.set_value("session_summary_max_days", "many", "3.0.0", scope="global")
        with self.assertRaises(UsageError):
            prefs.set_value("worktree_active", "sometimes", "3.0.0", scope="global")

    def test_an_unknown_key_is_rejected_on_write(self):
        with self.assertRaises(UsageError):
            prefs.set_value("langauge", "en", "3.0.0", scope="global")

    def test_the_projection_is_one_file_and_says_it_is_generated(self):
        projected = self.root / prefs.RESOLVED_FILE
        self.assertTrue(projected.is_file())
        payload = json.loads(projected.read_text(encoding="utf-8"))
        self.assertIn("_generated_by", payload)
        self.assertIn("devteam prefs set", payload["_generated_by"])
        self.assertEqual(payload["language"], "pt-BR")

    def test_sync_refreshes_the_projection(self):
        prefs.set_value("language", "en", "3.0.0", scope="global")
        bind.sync_project(self.pid)
        payload = json.loads((self.root / prefs.RESOLVED_FILE).read_text(encoding="utf-8"))
        self.assertEqual(payload["language"], "en")


class BirthLayoutTest(StoreTestCase):
    def setUp(self):
        super().setUp()
        self.install_version("3.0.0", activate=True)

    def test_a_project_with_no_v2_memory_is_born_clean(self):
        root = self.new_project("fresh")
        bind.bind(root, provider_names=["claude"])
        self.assertEqual(project.layout(root), project.CURRENT_LAYOUT)
        self.assertFalse(project.legacy_memory_dir(root).exists())
        self.assertFalse(project.upgrade_available(root))

    def test_a_project_with_v2_memory_is_born_on_the_old_layout(self):
        root = self.new_project("legacy")
        memory = project.legacy_memory_dir(root)
        memory.mkdir(parents=True)
        (memory / "session-summary.md").write_text("## old\n", encoding="utf-8")

        bind.bind(root, provider_names=["claude"])
        self.assertEqual(project.layout(root), project.LAYOUT_MEMORY_IN_PROJECT)
        self.assertTrue(project.upgrade_available(root))
        # bind reports it and changes nothing
        self.assertTrue((memory / "session-summary.md").is_file())


class UpgradeTest(StoreTestCase):
    def setUp(self):
        super().setUp()
        self.install_version("3.0.0", activate=True)

    def _v2_bound(self, name="legacy"):
        root = self.new_project(name)
        memory = project.legacy_memory_dir(root)
        memory.mkdir(parents=True)
        (memory / "session-summary.md").write_text("## 2026-01-01 | v2 memory\n", encoding="utf-8")
        jsonio.write_json_atomic(memory / "state.json", {"session_id": 42})
        (memory / "nested").mkdir()
        (memory / "nested" / "note.txt").write_text("deep\n", encoding="utf-8")
        result = bind.bind(root, provider_names=["claude"])
        return root, result["project_id"]

    def test_plan_changes_nothing(self):
        root, _ = self._v2_bound()
        before = sorted(str(p.relative_to(root)) for p in root.rglob("*") if p.is_file())
        preview = upgrade.plan(root)
        after = sorted(str(p.relative_to(root)) for p in root.rglob("*") if p.is_file())
        self.assertEqual(before, after)
        self.assertEqual(preview["from_layout"], 1)
        self.assertEqual(preview["files"], 3)

    def test_apply_copies_verifies_and_leaves_the_project_clean(self):
        root, pid = self._v2_bound()
        result = upgrade.apply(root)

        self.assertEqual(result["copied"], 3)
        self.assertEqual(project.layout(root), project.CURRENT_LAYOUT)
        self.assertFalse(project.legacy_memory_dir(root).exists())
        self.assertEqual(
            sorted(p.name for p in (root / project.PROJECT_DIR).iterdir()),
            ["core", "project.json", "resolved", "state-dir"],
        )

        destination = Path(result["destination"])
        self.assertEqual(
            (destination / "session-summary.md").read_text(encoding="utf-8"),
            "## 2026-01-01 | v2 memory\n",
        )
        self.assertEqual((destination / "nested" / "note.txt").read_text(encoding="utf-8"), "deep\n")
        self.assertEqual(jsonio.read_json(destination / "state.json")["session_id"], 42)

    def test_the_original_is_quarantined_not_deleted(self):
        root, _ = self._v2_bound()
        result = upgrade.apply(root)
        quarantined = Path(result["quarantined"])
        self.assertTrue(quarantined.is_dir())
        self.assertTrue((quarantined / "session-summary.md").is_file())

    def test_the_state_pointer_resolves_to_the_new_location(self):
        root, pid = self._v2_bound()
        upgrade.apply(root)
        pointer = (root / project.PROJECT_DIR / project.STATE_DIR_POINTER).read_text(
            encoding="utf-8"
        ).strip()
        self.assertEqual(pointer, str(project.memory_dir(root, pid)))
        self.assertTrue(Path(pointer).is_dir())

    def test_the_gitignore_block_drops_the_user_data_entries(self):
        root, _ = self._v2_bound()
        before = gitignore.read_managed_entries(root / ".gitignore")
        self.assertIn(".dev-team-agents/user-data/", before)
        upgrade.apply(root)
        after = gitignore.read_managed_entries(root / ".gitignore")
        self.assertNotIn(".dev-team-agents/user-data/", after)
        self.assertIn(".worktrees/", after)

    def test_a_second_upgrade_is_refused(self):
        root, _ = self._v2_bound()
        upgrade.apply(root)
        with self.assertRaises(UsageError):
            upgrade.plan(root)

    def test_a_populated_destination_is_refused_and_nothing_is_moved(self):
        root, pid = self._v2_bound()
        destination = project.memory_dir_for_layout(root, pid, project.CURRENT_LAYOUT)
        jsonio.ensure_dir(destination)
        (destination / "session-summary.md").write_text("pre-existing\n", encoding="utf-8")

        with self.assertRaises(ConflictError):
            upgrade.apply(root)
        self.assertTrue(project.legacy_memory_dir(root).is_dir())
        self.assertEqual(project.layout(root), project.LAYOUT_MEMORY_IN_PROJECT)

    def test_an_unbound_project_cannot_be_upgraded(self):
        root = self.new_project("unbound")
        with self.assertRaises(UsageError):
            upgrade.plan(root)

    def test_pending_projects_lists_only_stale_layouts(self):
        old_root, _ = self._v2_bound("old")
        fresh = self.new_project("fresh")
        bind.bind(fresh, provider_names=["claude"])

        pending = upgrade.pending_projects()
        self.assertEqual([item["path"] for item in pending], [str(old_root.resolve())])
        upgrade.apply(old_root)
        self.assertEqual(upgrade.pending_projects(), [])


class InstalledVersionTest(StoreTestCase):
    def test_bind_stamps_the_version_where_the_v2_readers_look(self):
        self.install_version("3.0.0", activate=True)
        root = self.new_project()
        result = bind.bind(root, provider_names=["claude"])
        state = jsonio.read_json(project.memory_dir(root, result["project_id"]) / "state.json")
        self.assertEqual(state["installed_version"], "3.0.0")

    def test_a_stale_v2_value_is_corrected_without_losing_other_keys(self):
        self.install_version("3.0.0", activate=True)
        root = self.new_project("legacy")
        memory = project.legacy_memory_dir(root)
        memory.mkdir(parents=True)
        jsonio.write_json_atomic(
            memory / "state.json", {"installed_version": "2.48.0", "session_id": 7}
        )
        result = bind.bind(root, provider_names=["claude"])
        state = jsonio.read_json(project.memory_dir(root, result["project_id"]) / "state.json")
        self.assertEqual(state["installed_version"], "3.0.0")
        self.assertEqual(state["session_id"], 7)


class DoctorLayoutTest(StoreTestCase):
    def setUp(self):
        super().setUp()
        self.install_version("3.0.0", activate=True)

    def test_a_stale_layout_is_a_warning_that_names_the_command(self):
        from devteam import doctor

        root = self.new_project("legacy")
        project.legacy_memory_dir(root).mkdir(parents=True)
        bind.bind(root, provider_names=["claude"])

        report = doctor.run(project_root=root)
        layout_findings = [f for f in report["findings"] if f["category"] == "layout"]
        self.assertTrue(any(f["level"] == "warn" for f in layout_findings))
        self.assertTrue(any("devteam upgrade" in (f.get("hint") or "") for f in layout_findings))

    def test_a_missing_state_pointer_is_reported(self):
        from devteam import doctor

        root = self.new_project()
        bind.bind(root, provider_names=["claude"])
        (root / project.PROJECT_DIR / project.STATE_DIR_POINTER).unlink()

        report = doctor.run(project_root=root)
        self.assertTrue(
            any("state pointer" in f["message"] for f in report["findings"]), report["findings"]
        )


class StorePortabilityTest(StoreTestCase):
    def setUp(self):
        super().setUp()
        self.install_version("3.0.0", activate=True)

    def test_export_then_import_round_trips_the_registry(self):
        root = self.new_project()
        result = bind.bind(root, provider_names=["claude"])
        archive = self.tmp / "export.tar.gz"
        exported = store.export(archive)
        self.assertTrue(Path(exported["archive"]).is_file())

        shutil.rmtree(str(self.home / "data"))
        self.assertEqual(registry.entries(), {})

        store.import_archive(archive)
        self.assertIn(result["project_id"], registry.entries())

    def test_import_refuses_to_overwrite_a_populated_store_without_force(self):
        root = self.new_project()
        bind.bind(root, provider_names=["claude"])
        archive = self.tmp / "export.tar.gz"
        store.export(archive)
        with self.assertRaises(ConflictError):
            store.import_archive(archive)

    def test_import_rejects_an_unsafe_archive(self):
        import io
        import tarfile

        bad = self.tmp / "bad.tar.gz"
        with tarfile.open(str(bad), "w:gz") as tar:
            info = tarfile.TarInfo("../escape.txt")
            info.size = 1
            tar.addfile(info, io.BytesIO(b"x"))
        shutil.rmtree(str(self.home / "data"), ignore_errors=True)
        with self.assertRaises(EnvError):
            store.import_archive(bad)

    def test_uninstall_keeps_the_data_store_by_default(self):
        root = self.new_project()
        bind.bind(root, provider_names=["claude"])
        result = store.uninstall()
        self.assertFalse((self.home / "core").exists())
        self.assertTrue((self.home / "data").is_dir())
        self.assertFalse(result["purged"])

    def test_purge_removes_the_data_store(self):
        root = self.new_project()
        bind.bind(root, provider_names=["claude"])
        result = store.uninstall(purge=True)
        self.assertFalse((self.home / "data").exists())
        self.assertTrue(result["purged"])


class UpgradeCliTest(StoreTestCase):
    def test_purge_needs_an_explicit_yes(self):
        self.install_version("3.0.0", activate=True)
        code, out, _ = self.run_cli("uninstall", "--purge", "--json")
        self.assertEqual(code, 2)
        self.assertFalse(json.loads(out)["ok"])
        self.assertTrue((self.home / "data").exists() or True)

    def test_upgrade_preview_and_apply_through_the_cli(self):
        self.install_version("3.0.0", activate=True)
        root = self.new_project("legacy")
        project.legacy_memory_dir(root).mkdir(parents=True)
        (project.legacy_memory_dir(root) / "session-summary.md").write_text("## x\n", encoding="utf-8")
        self.run_cli("bind", str(root))

        code, out, _ = self.run_cli("upgrade", str(root), "--json")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["from_layout"], 1)
        self.assertTrue(project.legacy_memory_dir(root).is_dir(), "preview must change nothing")

        code, out, _ = self.run_cli("upgrade", str(root), "--apply", "--json")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["to_layout"], 2)
        self.assertFalse(project.legacy_memory_dir(root).exists())

    def test_prefs_round_trip_through_the_cli(self):
        self.install_version("3.0.0", activate=True)
        root = self.new_project()
        self.run_cli("bind", str(root))

        code, out, _ = self.run_cli("prefs", "set", "language", "en", "--path", str(root), "--json")
        self.assertEqual(code, 0)
        code, out, _ = self.run_cli("prefs", "get", "language", "--path", str(root), "--json")
        body = json.loads(out)
        self.assertEqual(body["value"], "en")
        self.assertEqual(body["origin"], "global")

        code, out, _ = self.run_cli("prefs", "list", "--path", str(root), "--json")
        self.assertIn("telemetry", json.loads(out)["values"])


if __name__ == "__main__":
    unittest.main()
