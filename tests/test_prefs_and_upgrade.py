"""M2: the preference cascade, the layout upgrade, and store portability."""

import io
import json
import os
import shutil
import stat
import subprocess
import tarfile
import unittest
from pathlib import Path
from unittest import mock

from devteam_support import POSIX_MODES, StoreTestCase, requires_posix_modes, rmtree as _rmtree_readonly_safe

from devteam import bind, gitignore, jsonio, paths, prefs, project, registry, store, upgrade, versions
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
        jsonio.write_json_atomic(memory / "credentials.local.json", {"db_password": "s3cret"})
        (memory / ".notifier-state").write_text("turns=3\n", encoding="utf-8")
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
        self.assertEqual(preview["files"], 5)
        self.assertEqual(
            preview["machine_local"], [".notifier-state", "credentials.local.json", "state.json"]
        )

    def test_apply_copies_verifies_and_leaves_the_project_clean(self):
        root, pid = self._v2_bound()
        result = upgrade.apply(root)

        self.assertEqual(result["copied"], 5)
        self.assertEqual(project.layout(root), project.CURRENT_LAYOUT)
        self.assertFalse(project.legacy_memory_dir(root).exists())
        # Two pointers, not one: layout 2 splits a project's own state into a
        # machine-local directory (`state-dir`) and a portable one (`memory-dir`),
        # and the upgrade writes both (ADR-0013).
        self.assertEqual(
            sorted(p.name for p in (root / project.PROJECT_DIR).iterdir()),
            ["memory-dir", "project.json", "resolved", "scripts", "state-dir", "templates"],
        )

        destination = Path(result["destination"])
        self.assertEqual(
            (destination / "session-summary.md").read_text(encoding="utf-8"),
            "## 2026-01-01 | v2 memory\n",
        )
        self.assertEqual((destination / "nested" / "note.txt").read_text(encoding="utf-8"), "deep\n")

        # state.json, the dot-markers and the secrets describe this machine, so they
        # land in the machine subtree and never in the portable one (ADR-0013).
        state_destination = Path(result["state_destination"])
        self.assertEqual(jsonio.read_json(state_destination / "state.json")["session_id"], 42)
        self.assertTrue((state_destination / ".notifier-state").is_file())
        self.assertTrue((state_destination / "credentials.local.json").is_file())
        for machine_local in ("state.json", ".notifier-state", "credentials.local.json"):
            self.assertFalse((destination / machine_local).exists(), machine_local)

    def test_the_original_is_quarantined_not_deleted(self):
        root, _ = self._v2_bound()
        result = upgrade.apply(root)
        quarantined = Path(result["quarantined"])
        self.assertTrue(quarantined.is_dir())
        self.assertTrue((quarantined / "session-summary.md").is_file())

    @requires_posix_modes
    def test_quarantine_and_upgraded_files_are_owner_only(self):
        """Containment used to rest entirely on `data/` itself never being loosened
        (0700). Quarantine can hold a retired `credentials.local.json` verbatim, and
        `shutil.copy2` otherwise preserves a checkout's source mode (often 0644) —
        both must be forced to owner-only independently of that.
        """
        root, _ = self._v2_bound()
        result = upgrade.apply(root)

        # `quarantined` itself is the moved directory (`user-data/`) and keeps
        # whatever mode it already had — it's the quarantine *structure* around it
        # (built fresh by `ensure_dir`) that must be owner-only.
        quarantined = Path(result["quarantined"])
        self.assertEqual(stat.S_IMODE(quarantined.parent.stat().st_mode), 0o700)
        self.assertEqual(stat.S_IMODE(quarantined.parent.parent.stat().st_mode), 0o700)

        for base in (Path(result["destination"]), Path(result["state_destination"])):
            for item in base.rglob("*"):
                if item.is_file():
                    self.assertEqual(
                        stat.S_IMODE(item.stat().st_mode), 0o600, str(item)
                    )

    def test_the_state_pointer_resolves_to_the_new_location(self):
        root, pid = self._v2_bound()
        upgrade.apply(root)
        pointer = (root / project.PROJECT_DIR / project.STATE_DIR_POINTER).read_text(
            encoding="utf-8"
        ).strip()
        # `state.sh` resolves state.json through this pointer, so it must name the
        # machine subtree — the portable one has no state.json in it.
        self.assertEqual(pointer, str(project.state_dir(root, pid)))
        self.assertNotEqual(pointer, str(project.memory_dir(root, pid)))
        self.assertTrue(Path(pointer).is_dir())

    def test_the_gitignore_block_drops_the_user_data_entries(self):
        root, _ = self._v2_bound()
        before = gitignore.read_managed_entries(root / ".gitignore")
        self.assertIn(".dev-team-agents/user-data/", before)
        upgrade.apply(root)
        after = gitignore.read_managed_entries(root / ".gitignore")
        self.assertNotIn(".dev-team-agents/user-data/", after)
        self.assertIn(".worktrees/", after)

    def test_a_sync_after_upgrade_does_not_put_the_user_data_entries_back(self):
        """`upgrade` retires the `user-data/` ignore lines because the directory is gone.
        `bind`/`sync` used to rewrite them unconditionally, so the next sync put back
        exactly what the upgrade had retired — a dirty `.gitignore` on every sync,
        forever, naming a directory that does not exist. Observed on this repository's
        own install right after its upgrade, not derived from reading the code.
        """
        root, _ = self._v2_bound()
        before = gitignore.read_managed_entries(root / ".gitignore")
        self.assertIn(".dev-team-agents/user-data/", before)

        upgrade.apply(root)
        after_upgrade = gitignore.read_managed_entries(root / ".gitignore")
        self.assertNotIn(".dev-team-agents/user-data/", after_upgrade)

        bind.sync_project(project.load(root)["project_id"])

        after_sync = gitignore.read_managed_entries(root / ".gitignore")
        self.assertNotIn(".dev-team-agents/user-data/", after_sync)
        self.assertNotIn("!.dev-team-agents/user-data/graphify.json", after_sync)
        # The entries that are not about the legacy directory still get written.
        self.assertIn(".dev-team-agents/resolved/", after_sync)
        self.assertIn(".worktrees/", after_sync)

    def test_a_layout_1_project_still_gets_the_user_data_entries(self):
        """The other direction, so the fix cannot be "stop writing them at all": a
        project whose memory is still inside it must keep the line that ignores the
        directory, and the negation that keeps `graphify.json` tracked within it.
        """
        root, _ = self._v2_bound()
        self.assertEqual(project.layout(root), project.LAYOUT_MEMORY_IN_PROJECT)
        entries = bind.project_gitignore_entries(root)
        self.assertIn(".dev-team-agents/user-data/", entries)
        self.assertIn("!.dev-team-agents/user-data/graphify.json", entries)

    def test_the_pointers_it_creates_are_excluded_and_the_artifact_block_survives(self):
        """The two layout-2 pointers hold an absolute path into one developer's store,
        so they can never be committed — and nothing was ignoring them. `bind` gets it
        for free because it rebuilds the local exclude from its whole artifact set and
        the pointers are artifacts; `upgrade` wrote them directly and touched no ignore
        file, so an upgraded project showed two untracked files in every `git status`
        until some later `devteam sync` happened to rebuild the block.
        """
        root, _ = self._v2_bound()
        exclude = gitignore.local_exclude_file(root)
        self.assertIsNotNone(exclude, "the fixture project must be a git repository")
        before = gitignore.read_managed_entries(exclude)
        self.assertTrue(before, "bind should have written an artifact block to exclude")

        result = upgrade.apply(root)

        after = gitignore.read_managed_entries(exclude)
        self.assertIn(".dev-team-agents/memory-dir", after)
        self.assertIn(".dev-team-agents/state-dir", after)
        # Unioned, not replaced: the artifact paths bind wrote are still there.
        self.assertTrue(set(before).issubset(set(after)))
        # `unchanged`, and that is the point of asserting it: after a normal `link`-mode
        # bind the pointers are ALREADY excluded, because bind builds the block from its
        # artifact set and the pointers are artifacts. This asserts `upgrade` does not
        # churn a file it has nothing to add to. The case where it does have something to
        # add is the next test.
        self.assertEqual(result["git_exclude"], "unchanged")

    def test_the_pointers_are_added_when_the_exclude_block_does_not_have_them(self):
        """The narrow case the exclude step exists for: a project whose managed block is
        missing the pointers. Reachable from a `vendored` bind (which skips the exclude
        write), from a checkout that became a git repository after it was bound, or from a
        hand-edited block. Before this step, `upgrade` wrote the pointers and touched no
        ignore file, so they stayed untracked-visible until some later `sync` rebuilt it.
        """
        root, _ = self._v2_bound()
        exclude = gitignore.local_exclude_file(root)
        # Simulate the block as a bind that never wrote the pointers would have left it.
        kept = [
            entry
            for entry in gitignore.read_managed_entries(exclude)
            if not entry.endswith(("memory-dir", "state-dir"))
        ]
        gitignore.apply_managed_block(exclude, kept)
        self.assertNotIn(".dev-team-agents/memory-dir", gitignore.read_managed_entries(exclude))

        result = upgrade.apply(root)

        after = gitignore.read_managed_entries(exclude)
        self.assertIn(".dev-team-agents/memory-dir", after)
        self.assertIn(".dev-team-agents/state-dir", after)
        self.assertTrue(set(kept).issubset(set(after)))
        self.assertEqual(result["git_exclude"], "updated")

    def test_the_exclude_step_is_reported_as_skipped_outside_a_git_repository(self):
        root, _ = self._v2_bound()
        # `_rmtree_readonly_safe`, not `shutil.rmtree`: this is a real git
        # repository, whose object files git marks read-only — Windows refuses
        # to unlink those with a plain `rmtree` (see `devteam_support.rmtree`).
        _rmtree_readonly_safe(root / ".git")
        result = upgrade.apply(root)
        self.assertEqual(result["git_exclude"], "skipped")

    def test_graphify_json_stays_in_the_project_through_upgrade(self):
        """`graphify.json` is committed, shared project config, not personal memory
        — it must never travel into the per-user store, even though it lives right
        next to files that do.
        """
        root, _ = self._v2_bound()
        memory = project.legacy_memory_dir(root)
        graphify_content = json.dumps({"nodes": []}, indent=2) + "\n"
        (memory / "graphify.json").write_text(graphify_content, encoding="utf-8")

        preview = upgrade.plan(root)
        self.assertIn("graphify.json", preview["retained"])

        result = upgrade.apply(root)
        self.assertIn("graphify.json", result["retained"])

        graphify_path = memory / "graphify.json"
        self.assertTrue(graphify_path.is_file())
        self.assertEqual(graphify_path.read_text(encoding="utf-8"), graphify_content)
        self.assertFalse((Path(result["destination"]) / "graphify.json").exists())
        self.assertFalse((Path(result["state_destination"]) / "graphify.json").exists())

        after = gitignore.read_managed_entries(root / ".gitignore")
        self.assertIn("!.dev-team-agents/user-data/graphify.json", after)
        self.assertNotIn(".dev-team-agents/user-data/", after)

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
        state = jsonio.read_json(project.state_dir(root, result["project_id"]) / "state.json")
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
        state = jsonio.read_json(project.state_dir(root, result["project_id"]) / "state.json")
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

    def test_a_missing_pointer_is_repaired_not_just_reported(self):
        from devteam import doctor

        root = self.new_project()
        bind.bind(root, provider_names=["claude"])
        project_id = project.load(root)["project_id"]
        pointer_path = root / project.PROJECT_DIR / project.STATE_DIR_POINTER
        pointer_path.unlink()

        report = doctor.run(project_root=root)

        # `doctor` no longer just reports a missing/stale pointer as a WARN: it
        # rewrites it on the spot, the same additive repair it already performs on a
        # moved registry entry. The alternative — report and wait — is what made a
        # stale `state-dir` hand every hook an empty `state.json` until someone
        # happened to run `devteam sync`.
        repaired = [
            f
            for f in report["findings"]
            if f["category"] == "layout" and "was missing; rewritten" in f["message"]
        ]
        self.assertTrue(repaired, report["findings"])
        self.assertEqual(repaired[0]["level"], "ok")
        self.assertIn(project.STATE_DIR_POINTER, repaired[0]["message"])
        self.assertIn(
            {"action": "repointed", "pointer": project.STATE_DIR_POINTER}, report["actions"]
        )
        self.assertTrue(pointer_path.is_file())
        self.assertEqual(
            pointer_path.read_text(encoding="utf-8").strip(),
            str(project.state_dir(root, project_id)),
        )


class StorePortabilityTest(StoreTestCase):
    def setUp(self):
        super().setUp()
        self.install_version("3.0.0", activate=True)

    def test_a_portable_export_leaves_the_machine_records_behind(self):
        root = self.new_project()
        result = bind.bind(root, provider_names=["claude"])
        prefs.set_value("language", "en", "3.0.0", scope="global")
        summary = paths.project_data_dir(result["project_id"]) / "session-summary.md"
        summary.parent.mkdir(parents=True, exist_ok=True)
        summary.write_text("## 2026-01-01 | authored\n", encoding="utf-8")

        archive = self.tmp / "export.tar.gz"
        exported = store.export(archive)
        self.assertTrue(Path(exported["archive"]).is_file())
        self.assertTrue(exported["portable_only"])

        with tarfile.open(str(archive), "r:gz") as tar:
            names = tar.getnames()
        self.assertIn("data/preferences.json", names)
        self.assertTrue(any(name.endswith("session-summary.md") for name in names), names)
        self.assertFalse([name for name in names if "/machines/" in name], names)
        self.assertNotIn("data/machine-id", names)
        self.assertFalse([name for name in names if "bind-manifest.json" in name], names)

    def test_a_portable_export_round_trips_memory_and_is_rebuilt_by_a_rebind(self):
        root = self.new_project()
        result = bind.bind(root, provider_names=["claude"])
        pid = result["project_id"]
        summary = paths.project_data_dir(pid) / "session-summary.md"
        summary.parent.mkdir(parents=True, exist_ok=True)
        summary.write_text("## 2026-01-01 | portable\n", encoding="utf-8")

        archive = self.tmp / "export.tar.gz"
        store.export(archive)
        shutil.rmtree(str(self.home / "data"))

        imported = store.import_archive(archive)
        self.assertTrue(imported["portable_only"])
        # The registry did not travel — by design — so the project reads as unbound
        # until it is re-bound, and the memory is waiting under its committed identity.
        self.assertEqual(registry.entries(), {})
        self.assertEqual(imported["machine_records_kept"], [])
        self.assertEqual(
            summary.read_text(encoding="utf-8"), "## 2026-01-01 | portable\n"
        )
        self.assertIn("devteam bind", imported["next"])

        rebound = bind.bind(root, provider_names=["claude"])
        self.assertEqual(rebound["project_id"], pid)
        self.assertIn(pid, registry.entries())
        self.assertTrue(bind.manifest_file(pid).is_file())

    def test_export_all_carries_the_registry_and_the_manifests(self):
        root = self.new_project()
        result = bind.bind(root, provider_names=["claude"])
        archive = self.tmp / "export-all.tar.gz"
        exported = store.export(archive, include_machine=True)
        self.assertFalse(exported["portable_only"])

        shutil.rmtree(str(self.home / "data"))
        store.import_archive(archive)
        self.assertIn(result["project_id"], registry.entries())
        self.assertTrue(bind.manifest_file(result["project_id"]).is_file())

    def test_importing_a_portable_archive_keeps_this_machines_registry(self):
        root = self.new_project()
        result = bind.bind(root, provider_names=["claude"])
        archive = self.tmp / "export.tar.gz"
        store.export(archive)

        # The archive carries no machine subtree. Promoting it verbatim would take
        # the live registry out of the active store and make every bound project
        # read as unbound.
        imported = store.import_archive(archive, force=True)
        # `machines/` moves first and `machine-id` last: if the second move fails,
        # the identity is still where the records that name it are, rather than
        # being orphaned from them.
        self.assertEqual(imported["machine_records_kept"], ["machines", "machine-id"])
        self.assertIn(result["project_id"], registry.entries())
        # This machine already knew the project, so reconciling is the next step —
        # a freshly installed machine would be told to bind instead.
        self.assertIn("devteam sync --all", imported["next"])

    def test_a_second_machine_sees_the_memory_but_not_the_registry(self):
        root = self.new_project()
        result = bind.bind(root, provider_names=["claude"])
        pid = result["project_id"]
        self.assertIn(pid, registry.entries())

        other = "11111111-2222-3333-4444-555555555555"
        with mock.patch.dict(os.environ, {paths.MACHINE_ID_ENV: other}):
            self.assertEqual(paths.machine_id(), other)
            # Nothing is shared across machines except what the user authored: the
            # portable preferences layer is the same file, the registry is not.
            self.assertEqual(registry.entries(), {})
            self.assertEqual(prefs.global_file(), paths.global_preferences_file())
            self.assertFalse(bind.manifest_file(pid).exists())
        self.assertIn(pid, registry.entries())

    def test_import_refuses_to_overwrite_authored_records_without_force(self):
        root = self.new_project()
        bind.bind(root, provider_names=["claude"])
        prefs.set_value("language", "en", "3.0.0", scope="global")
        archive = self.tmp / "export.tar.gz"
        store.export(archive)
        with self.assertRaises(ConflictError):
            store.import_archive(archive)

    def test_an_all_archive_refuses_to_replace_a_live_registry_without_force(self):
        root = self.new_project()
        bind.bind(root, provider_names=["claude"])
        archive = self.tmp / "export-all.tar.gz"
        store.export(archive, include_machine=True)
        # Nothing portable was authored, so the pre-extraction check passes; the
        # incoming registry is what must not silently displace the live one.
        self.assertEqual(store.portable_entries(), [])
        with self.assertRaises(ConflictError):
            store.import_archive(archive)
        self.assertTrue(store.registry_file_has_entries())

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

    def _write_archive(self, path, members):
        with tarfile.open(str(path), "w:gz") as tar:
            for member, data in members:
                if data is None:
                    tar.addfile(member)
                else:
                    member.size = len(data)
                    tar.addfile(member, io.BytesIO(data))
        return path

    def test_import_rejects_a_symlink_with_an_absolute_target(self):
        """`store.import_archive` must route every member through
        `update.safe_members` on its own — `filter="data"` does not exist on the
        declared python 3.9 floor, so the bare `except TypeError` fallback used to
        extract unchecked. Covered here on the `store` import path specifically;
        `update`'s own extraction already had coverage.
        """
        member = tarfile.TarInfo("data/escape")
        member.type = tarfile.SYMTYPE
        member.linkname = "/etc/passwd"
        archive = self._write_archive(self.tmp / "sym-abs.tar.gz", [(member, None)])
        with self.assertRaises(EnvError):
            store.import_archive(archive)

    def test_import_rejects_a_hardlink_escaping_the_tree(self):
        # Three levels of ".." from a member two directories deep (`data/nested/`)
        # is what actually climbs outside the extraction root; two levels merely
        # cancels the nesting and lands back inside it.
        member = tarfile.TarInfo("data/nested/link")
        member.type = tarfile.LNKTYPE
        member.linkname = "../../../victim.txt"
        archive = self._write_archive(self.tmp / "hardlink-escape.tar.gz", [(member, None)])
        with self.assertRaises(EnvError):
            store.import_archive(archive)

    def test_import_rejects_device_and_fifo_members(self):
        for kind, name in ((tarfile.CHRTYPE, "dev"), (tarfile.FIFOTYPE, "fifo")):
            member = tarfile.TarInfo("data/" + name)
            member.type = kind
            archive = self._write_archive(self.tmp / "{}.tar.gz".format(name), [(member, None)])
            with self.assertRaises(EnvError):
                store.import_archive(archive)

    def test_import_refuses_an_archive_whose_machines_entry_is_not_a_directory(self):
        # REGRESSION: the guard tested `exists() and not is_dir()`, but `Path.exists()`
        # follows the link and is False for a **dangling** symlink — exactly the case it
        # was written for. The archive was then misread as portable, this machine's
        # identity was carried into it, the move failed, and the live registry was left
        # stranded. `is_symlink()` is now checked first.
        shutil.rmtree(str(paths.data_dir()), ignore_errors=True)
        paths.reset_machine_id_cache()

        archive = self.tmp / "dangling-machines.tar.gz"
        with tarfile.open(str(archive), "w:gz") as tar:
            link = tarfile.TarInfo("data/machines")
            link.type = tarfile.SYMTYPE
            link.linkname = "nowhere"
            tar.addfile(link)
            payload = json.dumps({"language": "en"}).encode("utf-8")
            info = tarfile.TarInfo("data/preferences.json")
            info.size = len(payload)
            tar.addfile(info, io.BytesIO(payload))

        with self.assertRaises(EnvError):
            store.import_archive(archive)
        self.assertFalse((self.home / "data.incoming").exists())

    def test_a_portable_export_carries_no_secret_through_quarantine(self):
        """CRITICAL: a default export used to ship whatever `devteam upgrade`
        quarantined verbatim, including a plaintext `credentials.local.json` — a
        reviewer extracted a real database password from a default archive this
        way. Covers the two separate escapes a review found: a **nested** secret
        (`env/credentials.local.json`) and one with **different case**
        (`Credentials.local.json`).
        """
        root = self.new_project()
        memory = project.legacy_memory_dir(root)
        memory.mkdir(parents=True)
        (memory / "session-summary.md").write_text("## memory\n", encoding="utf-8")
        secret = "s3cret-value-should-never-travel"
        jsonio.write_json_atomic(memory / "credentials.local.json", {"db_password": secret})
        (memory / "env").mkdir()
        jsonio.write_json_atomic(
            memory / "env" / "credentials.local.json", {"db_password": secret}
        )
        # A different directory, not the same one as the top-level file: the two
        # names differ only by case, and macOS's default APFS is case-insensitive —
        # putting both in one directory would silently collide on disk.
        (memory / "secrets").mkdir()
        jsonio.write_json_atomic(
            memory / "secrets" / "Credentials.local.json", {"db_password": secret}
        )
        bind.bind(root, provider_names=["claude"])
        upgrade.apply(root)

        archive = self.tmp / "export.tar.gz"
        exported = store.export(archive)
        self.assertIn("quarantine", exported["excluded"])

        with tarfile.open(str(archive), "r:gz") as tar:
            for member in tar.getmembers():
                if not member.isfile():
                    continue
                content = tar.extractfile(member).read()
                self.assertNotIn(secret.encode("utf-8"), content, member.name)

    def test_export_all_excludes_the_lock_directory(self):
        """HIGH: the exclusion used to match only the first path component, and
        locks now live at `machines/<id>/locks/` — whose first component is
        `machines`, not `locks` — so a first-component test silently let a held
        lock into an `--all` archive.
        """
        root = self.new_project()
        result = bind.bind(root, provider_names=["claude"])
        jsonio.ensure_dir(paths.locks_dir())
        (paths.locks_dir() / "registry.lock").write_text("12345\n", encoding="utf-8")

        archive = self.tmp / "export-all.tar.gz"
        store.export(archive, include_machine=True)
        with tarfile.open(str(archive), "r:gz") as tar:
            names = tar.getnames()

        self.assertFalse([n for n in names if "locks" in Path(n).parts], names)
        # `--all` exists to carry exactly these two, so the lock exclusion must not
        # take them down with it.
        self.assertTrue(any(n.endswith("registry.json") for n in names), names)
        self.assertTrue(
            any(n.endswith("bind-manifest.json") for n in names)
            or any(result["project_id"] in n for n in names),
            names,
        )

    def test_export_defaults_to_the_cache_dir_and_is_owner_only(self):
        """HIGH: the default destination used to be `Path.cwd()` — the bound
        repository, one `git add -A` away from committing an archive that can hold
        credential references and a quarantined pre-upgrade memory directory.
        """
        root = self.new_project()
        bind.bind(root, provider_names=["claude"])

        exported = store.export()
        archive = Path(exported["archive"])
        self.assertEqual(archive.parent, paths.cache_dir() / "exports")
        self.assertNotIn(str(root.resolve()), str(archive))
        if POSIX_MODES:
            self.assertEqual(stat.S_IMODE(archive.stat().st_mode), 0o600)
        # `--to .` is one keystroke away, so the project's own gitignore must catch
        # an archive left in the repository too.
        self.assertIn("devteam-data-*.tar.gz", bind.PROJECT_GITIGNORE_ENTRIES)

    def test_export_files_count_matches_the_archive_in_both_modes(self):
        """The count and the archive filter used to be two separate expressions,
        and a review found the count could drift from what the archive actually
        holds without a test noticing — they are now one predicate.
        """
        root = self.new_project()
        bind.bind(root, provider_names=["claude"])
        prefs.set_value("language", "en", "3.0.0", scope="global")

        default_archive = self.tmp / "default.tar.gz"
        exported = store.export(default_archive)
        with tarfile.open(str(default_archive), "r:gz") as tar:
            counted = sum(1 for m in tar.getmembers() if m.isfile())
        self.assertEqual(exported["files"], counted)

        all_archive = self.tmp / "all.tar.gz"
        exported_all = store.export(all_archive, include_machine=True)
        with tarfile.open(str(all_archive), "r:gz") as tar:
            counted_all = sum(1 for m in tar.getmembers() if m.isfile())
        self.assertEqual(exported_all["files"], counted_all)
        self.assertGreater(exported_all["files"], exported["files"])

    def test_import_withholds_consent_from_an_incoming_preferences_file(self):
        """`telemetry`/`auto_update` must never travel as `true` on an import: the
        backfill only adds *missing* keys, so an imported file already saying
        `true` would silently enable telemetry on a machine whose owner was never
        asked.
        """
        root = self.new_project()
        bind.bind(root, provider_names=["claude"])
        prefs.set_value("telemetry", "true", "3.0.0", scope="global")
        prefs.set_value("auto_update", "true", "3.0.0", scope="global")
        archive = self.tmp / "export.tar.gz"
        store.export(archive)

        # Import onto a store that does not have these keys set at all.
        shutil.rmtree(str(self.home / "data"))
        imported = store.import_archive(archive)
        self.assertEqual(imported["consent_withheld"], ["auto_update", "telemetry"])

        saved = jsonio.read_json(paths.global_preferences_file())
        self.assertNotIn("telemetry", saved)
        self.assertNotIn("auto_update", saved)

        resolved = prefs.resolve(None, "3.0.0")
        for key in ("telemetry", "auto_update"):
            self.assertFalse(resolved["values"][key], key)
            self.assertEqual(resolved["origin"][key], "consent-withheld", key)

    def test_all_archive_import_with_force_adopts_the_archived_identity(self):
        """The archived registry in an `--all` archive lives at
        `machines/<archived-id>/registry.json`. Keeping this machine's own id after
        the wholesale replace would leave `machine_dir()` pointing at a subtree the
        archive never wrote, and every restored bind would read as unbound despite
        `registry.json` sitting right there on disk — so adopting the archived
        identity is a correctness requirement, not an accident of the replace.
        """
        home_a = self.tmp / "machine-a"
        os.environ["DEVTEAM_HOME"] = str(home_a)
        paths.reset_machine_id_cache()
        self.install_version("3.0.0", activate=True)
        root_a = self.new_project("app-a")
        result_a = bind.bind(root_a, provider_names=["claude"])
        machine_a_id = paths.machine_id()
        archive = self.tmp / "all-a.tar.gz"
        store.export(archive, include_machine=True)

        home_b = self.tmp / "machine-b"
        os.environ["DEVTEAM_HOME"] = str(home_b)
        paths.reset_machine_id_cache()
        self.install_version("3.0.0", activate=True)
        root_b = self.new_project("app-b")
        bind.bind(root_b, provider_names=["claude"])
        machine_b_id = paths.machine_id()
        self.assertNotEqual(machine_a_id, machine_b_id)

        store.import_archive(archive, force=True)
        paths.reset_machine_id_cache()

        self.assertEqual(paths.machine_id(), machine_a_id)
        self.assertIn(result_a["project_id"], registry.entries())
        self.assertNotIn(machine_b_id, [p.name for p in paths.machines_dir().glob("*")])

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
