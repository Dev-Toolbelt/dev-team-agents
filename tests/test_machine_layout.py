"""M2.1: the portable / machine-local split of the data store (ADR-0013).

The split exists so that a store can be moved, restored or — later — synchronised.
These tests hold the line on the two properties that make that possible: a record
that names an absolute path never sits in the portable subtree, and a portable
subtree opened as a different machine still reads as the user's own work.
"""

from __future__ import annotations

import json
import os
import unittest
from pathlib import Path
from unittest import mock

from devteam_support import StoreTestCase

from devteam import bind, jsonio, paths, project, registry, store
from devteam.errors import EnvError

OTHER_MACHINE = "11111111-2222-3333-4444-555555555555"


class MachineIdentityTest(StoreTestCase):
    def test_the_id_is_created_once_and_reused(self):
        first = paths.machine_id()
        self.assertTrue(paths.machine_id_file().is_file())
        self.assertEqual(first, paths.machine_id())
        # The record is `{"id", "created_on"}`, not a bare UUID: the host that
        # created the id has to be on disk for a travelled store to be detected.
        record = json.loads(paths.machine_id_file().read_text(encoding="utf-8"))
        self.assertEqual(record["id"], first)
        self.assertEqual(record["created_on"], paths.machine_host())

    def test_an_existing_id_is_adopted_rather_than_replaced(self):
        jsonio.ensure_dir(paths.data_dir())
        paths.machine_id_file().write_text(OTHER_MACHINE + "\n", encoding="utf-8")
        paths._MACHINE_ID_CACHE.clear()
        with mock.patch.dict(os.environ, {"DEVTEAM_HOSTNAME": "this-host"}):
            result = paths.machine_id()
        # A bare-UUID record predates host tracking, so a `None` recorded host must
        # be read as "cannot be judged to have travelled" and adopted — a fixed
        # regression had it read as "host does not match" instead, which re-issued a
        # new id and orphaned every record the old one already named. Both halves
        # matter: the id survives unchanged, AND the record is rewritten to include
        # the current host so the *next* open has something to judge against.
        self.assertEqual(result, OTHER_MACHINE)
        record = json.loads(paths.machine_id_file().read_text(encoding="utf-8"))
        self.assertEqual(record["id"], OTHER_MACHINE)
        self.assertEqual(record["created_on"], "this-host")

    def test_a_recorded_id_from_a_different_host_is_reissued(self):
        with mock.patch.dict(os.environ, {"DEVTEAM_HOSTNAME": "laptop-a"}):
            first = paths.machine_id()
        paths.reset_machine_id_cache()
        with mock.patch.dict(os.environ, {"DEVTEAM_HOSTNAME": "laptop-b"}):
            second = paths.machine_id()
        # Unlike the bare-UUID case, a record naming a *different* host is exactly
        # the travelled-store signal the host check exists to catch.
        self.assertNotEqual(first, second)
        record = json.loads(paths.machine_id_file().read_text(encoding="utf-8"))
        self.assertEqual(record["id"], second)
        self.assertEqual(record["created_on"], "laptop-b")

    def test_an_uppercase_override_is_rejected(self):
        # The regex is anchored to lowercase; an uppercase UUID must not slip
        # through as "close enough" and silently pick a different machine subtree.
        # `OTHER_MACHINE` has no hex letters in it, so it round-trips through
        # `.upper()` unchanged — this needs a UUID that actually has a-f digits.
        lettered = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
        with mock.patch.dict(os.environ, {paths.MACHINE_ID_ENV: lettered.upper()}):
            with self.assertRaises(EnvError):
                paths.machine_id()

    def test_a_file_that_is_not_a_uuid_is_reported_not_replaced(self):
        jsonio.ensure_dir(paths.data_dir())
        paths.machine_id_file().write_text("not-an-id\n", encoding="utf-8")
        paths._MACHINE_ID_CACHE.clear()
        with self.assertRaises(EnvError):
            paths.machine_id()
        self.assertEqual(
            paths.machine_id_file().read_text(encoding="utf-8"), "not-an-id\n"
        )

    def test_the_override_wins_and_must_be_a_uuid(self):
        with mock.patch.dict(os.environ, {paths.MACHINE_ID_ENV: OTHER_MACHINE}):
            self.assertEqual(paths.machine_id(), OTHER_MACHINE)
            self.assertIn(OTHER_MACHINE, str(paths.registry_file()))
        with mock.patch.dict(os.environ, {paths.MACHINE_ID_ENV: "laptop"}):
            with self.assertRaises(EnvError):
                paths.machine_id()

    def test_every_machine_local_resolver_agrees_on_the_subtree(self):
        machine = paths.machine_dir()
        for resolved in (
            paths.registry_file(),
            paths.machine_project_dir("pid"),
            paths.locks_dir(),
        ):
            self.assertEqual(Path(resolved).parts[: len(machine.parts)], machine.parts)


class RecordPlacementTest(StoreTestCase):
    def setUp(self):
        super().setUp()
        self.install_version("3.0.0", activate=True)
        self.root = self.new_project()
        self.pid = bind.bind(self.root, provider_names=["claude"])["project_id"]

    def test_the_absolute_path_records_live_in_the_machine_subtree(self):
        machine = paths.machine_dir()
        self.assertEqual(paths.registry_file().parent, machine)
        self.assertTrue(paths.registry_file().is_file())

        manifest = bind.manifest_file(self.pid)
        self.assertTrue(manifest.is_file())
        self.assertEqual(manifest.parent, paths.machine_project_dir(self.pid))

        # The two records the inventory found to carry absolute paths, and the only
        # two: whatever else a bind writes must be readable on another machine.
        self.assertIn(str(self.root.resolve()), paths.registry_file().read_text(encoding="utf-8"))
        self.assertIn(str(self.root.resolve()), manifest.read_text(encoding="utf-8"))

    def test_no_portable_record_names_an_absolute_path(self):
        portable = paths.projects_dir()
        offenders = []
        for path in list(portable.rglob("*")) + [paths.global_preferences_file()]:
            if not path.is_file():
                continue
            if str(self.root.resolve()) in path.read_text(encoding="utf-8", errors="replace"):
                offenders.append(str(path.relative_to(paths.data_dir())))
        self.assertEqual(offenders, [])

    def test_state_json_is_machine_local_and_the_pointer_names_it(self):
        state_dir = project.state_dir(self.root, self.pid)
        self.assertEqual(state_dir, paths.machine_project_dir(self.pid))
        self.assertTrue((state_dir / "state.json").is_file())
        self.assertFalse((paths.project_data_dir(self.pid) / "state.json").exists())

        pointer = (self.root / project.PROJECT_DIR / project.STATE_DIR_POINTER).read_text(
            encoding="utf-8"
        ).strip()
        self.assertEqual(pointer, str(state_dir))

    def test_a_second_machine_reads_the_same_store_without_its_records(self):
        with mock.patch.dict(os.environ, {paths.MACHINE_ID_ENV: OTHER_MACHINE}):
            self.assertEqual(registry.entries(), {})
            self.assertFalse(bind.manifest_file(self.pid).exists())
            self.assertFalse((project.state_dir(self.root, self.pid) / "state.json").exists())
            # ...while everything the user authored is exactly where it was.
            self.assertEqual(paths.project_data_dir(self.pid), paths.projects_dir() / self.pid)


class FreshMachineRestoreTest(StoreTestCase):
    """The documented restore flow: install the core, then import a portable archive."""

    def test_installing_the_core_does_not_make_the_store_look_populated(self):
        self.install_version("3.0.0", activate=True)
        # `store install` writes machine-id and the machine subtree. Counting those as
        # user records made `devteam import` refuse on exactly the fresh machine the
        # restore flow targets.
        self.assertTrue(paths.machine_id_file().is_file())
        self.assertEqual(store.portable_entries(), [])

    def test_a_portable_archive_restores_onto_a_freshly_installed_machine(self):
        self.install_version("3.0.0", activate=True)
        root = self.new_project()
        pid = bind.bind(root, provider_names=["claude"])["project_id"]
        summary = paths.project_data_dir(pid) / "session-summary.md"
        summary.parent.mkdir(parents=True, exist_ok=True)
        summary.write_text("## authored\n", encoding="utf-8")
        archive = self.tmp / "portable.tar.gz"
        store.export(archive)

        # A second machine that has only installed the core: no --force needed.
        for path in (paths.projects_dir(), paths.global_preferences_file()):
            if path.is_dir():
                __import__("shutil").rmtree(str(path))
            elif path.exists():
                path.unlink()
        self.assertEqual(store.portable_entries(), [])
        store.import_archive(archive)
        self.assertEqual(summary.read_text(encoding="utf-8"), "## authored\n")


class AdoptLayoutTest(StoreTestCase):
    """The one-time relocation for a store written before the split."""

    def _pre_split_store(self, project_id="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"):
        data = paths.data_dir()
        jsonio.ensure_dir(data)
        jsonio.write_json_atomic(
            data / "registry.json",
            {"schema": 1, "projects": {project_id: {"path": "/somewhere/app", "mode": "link"}}},
        )
        legacy_project = paths.projects_dir() / project_id
        jsonio.ensure_dir(legacy_project)
        jsonio.write_json_atomic(legacy_project / "state.json", {"session_id": 9})
        jsonio.write_json_atomic(legacy_project / "bind-manifest.json", {"schema": 1})
        jsonio.write_json_atomic(legacy_project / "preferences.json", {"language": "es"})
        (legacy_project / "session-summary.md").write_text("## old\n", encoding="utf-8")
        (legacy_project / ".notifier-state").write_text("turns=1\n", encoding="utf-8")
        return project_id

    def test_it_relocates_only_the_machine_local_records(self):
        pid = self._pre_split_store()
        self.assertTrue(store.machine_layout_pending())

        result = store.adopt_machine_layout()
        self.assertEqual(
            result["moved"],
            [
                "registry.json",
                "projects/{}/.notifier-state".format(pid),
                "projects/{}/bind-manifest.json".format(pid),
                "projects/{}/state.json".format(pid),
            ],
        )
        self.assertFalse((paths.data_dir() / "registry.json").exists())
        self.assertIn(pid, registry.entries())
        machine_project = paths.machine_project_dir(pid)
        self.assertEqual(jsonio.read_json(machine_project / "state.json")["session_id"], 9)
        self.assertTrue((machine_project / ".notifier-state").is_file())

        portable = paths.project_data_dir(pid)
        self.assertEqual(jsonio.read_json(portable / "preferences.json")["language"], "es")
        self.assertTrue((portable / "session-summary.md").is_file())
        self.assertFalse((portable / "state.json").exists())

    def test_it_is_idempotent(self):
        self._pre_split_store()
        store.adopt_machine_layout()
        self.assertFalse(store.machine_layout_pending())
        again = store.adopt_machine_layout()
        self.assertEqual(again["moved"], [])

    def test_an_occupied_destination_is_never_overwritten(self):
        pid = self._pre_split_store()
        jsonio.write_json_atomic(
            paths.registry_file(), {"schema": 1, "projects": {"already": {"path": "/kept"}}}
        )
        result = store.adopt_machine_layout()
        self.assertEqual(
            [item["path"] for item in result["quarantined"]][0], "registry.json"
        )
        # The record that was already current stays current; the legacy one is kept
        # aside rather than deleted, because only the user can say which is right.
        self.assertIn("already", registry.entries())
        self.assertNotIn(pid, registry.entries())
        quarantined = Path(result["quarantined"][0]["to"])
        self.assertTrue(quarantined.is_file())

    def test_the_cli_relocates_before_a_command_reads_the_registry(self):
        pid = self._pre_split_store()
        code, out, err = self.run_cli("doctor", "--json")
        self.assertIn(code, (0, 1), err)
        payload = json.loads(out)
        self.assertTrue(payload["findings"])
        self.assertTrue(paths.registry_file().is_file())
        self.assertIn(pid, registry.entries())
        self.assertIn("machine-local record", err)

    def test_the_cli_reports_the_relocation_in_the_json_payload(self):
        self._pre_split_store()
        code, out, err = self.run_cli("doctor", "--json")
        self.assertIn(code, (0, 1), err)
        payload = json.loads(out)
        # ADR-0011 makes the desktop app a client of this CLI: a store mutation it
        # cannot see in the JSON document is a contract gap, so the relocation must
        # ride in the payload and not only on stderr.
        self.assertIn("store_relocation", payload)
        self.assertTrue(payload["store_relocation"]["moved"])
        # `_pre_split_store`'s registry entry names a path that was never a real
        # directory, so `_repoint_bound_projects` correctly skips it — `repointed`
        # is a real key in the payload either way, just empty for this fixture.
        self.assertIn("repointed", payload["store_relocation"])

    def test_it_repoints_a_real_bound_projects_pointers(self):
        """`_repoint_bound_projects` against a real, live project directory.

        The existing relocation tests use a fake `path` in the registry entry
        (`/somewhere/app`), which is never a real directory, so
        `_repoint_bound_projects` always skips it and the repair itself has no
        coverage. This builds a project that really was bound, then rolls its
        records back to the pre-split shape by hand.
        """
        self.install_version("3.0.0", activate=True)
        root = self.new_project()
        pid = bind.bind(root, provider_names=["claude"])["project_id"]

        # Move this project's machine-local state.json back to the flat, pre-split
        # location, and the registry back to the flat top-level path.
        state_payload = jsonio.read_json(paths.machine_project_dir(pid) / "state.json")
        legacy_project_dir = paths.projects_dir() / pid
        jsonio.write_json_atomic(legacy_project_dir / "state.json", state_payload)
        (paths.machine_project_dir(pid) / "state.json").unlink()

        registry_payload = jsonio.read_json(paths.registry_file())
        jsonio.write_json_atomic(paths.data_dir() / "registry.json", registry_payload)
        paths.registry_file().unlink()

        # And the state-dir pointer named the single directory a pre-split bind had.
        (root / project.PROJECT_DIR / project.STATE_DIR_POINTER).write_text(
            str(legacy_project_dir) + "\n", encoding="utf-8"
        )

        self.assertTrue(store.machine_layout_pending())
        result = store.adopt_machine_layout()

        entry = registry.get(pid)
        self.assertEqual(result["repointed"], [entry["path"]])
        state_pointer = (
            (root / project.PROJECT_DIR / project.STATE_DIR_POINTER)
            .read_text(encoding="utf-8")
            .strip()
        )
        memory_pointer = (
            (root / project.PROJECT_DIR / project.MEMORY_DIR_POINTER)
            .read_text(encoding="utf-8")
            .strip()
        )
        self.assertEqual(state_pointer, str(project.state_dir(root, pid)))
        self.assertEqual(memory_pointer, str(project.memory_dir(root, pid)))
        self.assertNotEqual(state_pointer, memory_pointer)
        # The machine-local state.json itself resolves correctly through the
        # repointed directory, not just the pointer file's text.
        self.assertEqual(
            jsonio.read_json(Path(state_pointer) / "state.json")["installed_version"],
            state_payload["installed_version"],
        )

    def test_a_stray_file_under_projects_is_skipped_not_raised_on(self):
        """A plain file at `data/projects/<something>` must not crash the scan.

        The relocation loop assumes every entry under `projects/` is a directory
        named after a project id; a stray file there (e.g. an editor swap file, a
        `.DS_Store`) must be skipped, not treated as a project to promote records
        out of.
        """
        pid = self._pre_split_store()
        stray = paths.projects_dir() / "not-a-project-id"
        stray.write_text("noise\n", encoding="utf-8")

        result = store.adopt_machine_layout()

        self.assertIn(pid, registry.entries())
        self.assertTrue(stray.is_file())
        self.assertEqual(stray.read_text(encoding="utf-8"), "noise\n")

    def test_a_per_project_destination_collision_is_quarantined_not_overwritten(self):
        """Mirrors `test_an_occupied_destination_is_never_overwritten`, one level
        deeper: a per-project record (not just the registry) can already exist at
        its machine-subtree destination, and must be quarantined rather than
        clobbered — only the user can say which of the two is current.
        """
        pid = self._pre_split_store()
        jsonio.write_json_atomic(
            paths.machine_project_dir(pid) / "bind-manifest.json",
            {"schema": 1, "already": "current"},
        )

        result = store.adopt_machine_layout()

        quarantined_paths = [item["path"] for item in result["quarantined"]]
        self.assertIn("projects/{}/bind-manifest.json".format(pid), quarantined_paths)
        self.assertEqual(
            jsonio.read_json(paths.machine_project_dir(pid) / "bind-manifest.json")["already"],
            "current",
        )
        # A collision on one record must not stop the others from promoting.
        self.assertEqual(
            jsonio.read_json(paths.machine_project_dir(pid) / "state.json")["session_id"], 9
        )
        self.assertIn(pid, registry.entries())


class NoMutationOnReadTest(StoreTestCase):
    """`devteam path` and `devteam doctor` are questions; they must create nothing."""

    def test_describe_creates_no_machine_identity_or_data_dir(self):
        self.assertFalse(paths.data_dir().exists())
        result = paths.describe()
        self.assertEqual(result["machine_id"], "<unassigned>")
        self.assertFalse(paths.machine_id_file().exists())
        self.assertFalse(paths.data_dir().exists())

    def test_doctor_on_an_uninstalled_store_creates_no_machine_identity(self):
        # REGRESSION: `doctor` used to mint the identity it was asked about, so a
        # second run diagnosed a store the first one had created. `check_machine()`
        # resolved read-only, but `check_registry()` reached `registry.entries()` ->
        # `registry_file()` -> `machine_dir()` -> `machine_id(create=True)`. Reads now
        # thread an explicitly read-only id, and no identity means no bound projects.
        from devteam import doctor as doctor_module

        doctor_module.run(project_root=None)
        self.assertFalse(paths.machine_id_file().exists(), "doctor minted a machine id")
        self.assertFalse(paths.data_dir().exists(), "doctor created the data store")


class DoctorMachineReportTest(StoreTestCase):
    def test_another_machines_record_set_is_a_warning_not_ok(self):
        from devteam import doctor as doctor_module

        current = paths.machine_id()
        other = "99999999-8888-7777-6666-555555555555"
        jsonio.ensure_dir(paths.machine_dir(other))

        report = doctor_module.run(project_root=None)

        machine_findings = [f for f in report["findings"] if f["category"] == "machine"]
        self.assertTrue(any(f["level"] == "warn" for f in machine_findings), machine_findings)
        self.assertTrue(any(other in f["message"] for f in machine_findings), machine_findings)
        # This machine's own record set is still reported OK — the two must not be
        # folded into a single finding that hides which set is the active one.
        self.assertTrue(
            any(f["level"] == "ok" and current in f["message"] for f in machine_findings),
            machine_findings,
        )


if __name__ == "__main__":
    unittest.main()
