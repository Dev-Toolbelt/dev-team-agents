"""Atomic JSON, locking, identity and the managed ignore block."""

import json
import os
import unittest

from devteam_support import StoreTestCase

from devteam import gitignore, jsonio, lock, project
from devteam.errors import ConflictError, EnvError


class JsonIoTest(StoreTestCase):
    def test_write_is_atomic_and_leaves_no_temp_file(self):
        target = self.tmp / "nested" / "file.json"
        jsonio.write_json_atomic(target, {"b": 1, "a": 2})
        self.assertEqual(jsonio.read_json(target), {"a": 2, "b": 1})
        leftovers = [p.name for p in target.parent.iterdir() if p.name != "file.json"]
        self.assertEqual(leftovers, [])

    def test_missing_file_returns_default(self):
        self.assertIsNone(jsonio.read_json(self.tmp / "nope.json"))
        self.assertEqual(jsonio.read_json(self.tmp / "nope.json", default={}), {})

    def test_malformed_file_is_reported_not_overwritten(self):
        bad = self.tmp / "bad.json"
        bad.write_text("{not json", encoding="utf-8")
        with self.assertRaises(EnvError):
            jsonio.read_json(bad)
        self.assertEqual(bad.read_text(encoding="utf-8"), "{not json")


class LockTest(StoreTestCase):
    def test_second_holder_times_out(self):
        with lock.store_lock("registry") as held:
            other = lock.Lock(held.path, timeout=0.2)
            with self.assertRaises(ConflictError):
                other.acquire()

    def test_lock_is_released_on_exit(self):
        first = lock.store_lock("registry")
        with first:
            pass
        with lock.Lock(first.path, timeout=0.5):
            pass

    def test_stale_lock_is_reclaimed(self):
        held = lock.store_lock("registry")
        held.acquire()
        # Simulate a process killed while holding the lock.
        owner = held.path / "owner.json"
        owner.write_text(json.dumps({"pid": 1, "acquired_at": 0}), encoding="utf-8")
        taker = lock.Lock(held.path, timeout=1.0, stale_after=1.0)
        with taker:
            self.assertIsNotNone(taker.stolen_from)


class ProjectIdentityTest(StoreTestCase):
    def test_ensure_creates_then_preserves_identity(self):
        root = self.new_project()
        first, created = project.ensure(root)
        self.assertTrue(created)
        second, created_again = project.ensure(root)
        self.assertFalse(created_again)
        self.assertEqual(first["project_id"], second["project_id"])

    def test_context_paths_default_to_docs_and_merge_without_duplicates(self):
        root = self.new_project()
        data, _ = project.ensure(root)
        self.assertEqual(data["context_paths"], ["docs"])
        merged, _ = project.ensure(root, context_paths=["rfcs", "docs"])
        self.assertEqual(merged["context_paths"], ["docs", "rfcs"])

    def test_rejects_absolute_and_escaping_context_paths(self):
        pid = "8f14e45f-ea0c-4c2b-9c1f-2b1f9a7d3e10"
        for bad in (["/etc"], ["../outside"], [""], []):
            with self.assertRaises(EnvError):
                project.validate({"schema": 1, "project_id": pid, "context_paths": bad})

    def test_rejects_a_context_path_absolute_only_on_the_other_platform(self):
        """A `project.json` is committed, so it crosses platforms by design.

        Each shape below is absolute on exactly one flavour and relative on the
        other, which is why the host's own `Path` was not enough to catch them:
        `PurePosixPath("C:\\x").is_absolute()` is False, and
        `PureWindowsPath("/etc").is_absolute()` is False. Asserted here on every
        host — a check that only runs on Windows would not have caught the
        Windows shapes being accepted on macOS either.
        """
        pid = "8f14e45f-ea0c-4c2b-9c1f-2b1f9a7d3e10"
        for bad in ("C:\\Windows", "c:/windows", "\\\\server\\share", "\\etc", "//server/share"):
            with self.assertRaises(EnvError, msg=bad):
                project.validate(
                    {"schema": 1, "project_id": pid, "context_paths": [bad]}
                )

    def test_rejects_a_newer_schema_instead_of_rewriting_it(self):
        pid = "8f14e45f-ea0c-4c2b-9c1f-2b1f9a7d3e10"
        with self.assertRaises(EnvError):
            project.validate({"schema": 99, "project_id": pid, "context_paths": ["docs"]})

    def test_resolve_root_from_a_subdirectory_finds_the_marker(self):
        root = self.new_project()
        project.ensure(root)
        nested = root / "src" / "deep"
        nested.mkdir(parents=True)
        self.assertEqual(project.resolve_root(nested), root.resolve())

    def test_reassign_identity_changes_the_id(self):
        root = self.new_project()
        before, _ = project.ensure(root)
        previous, new = project.reassign_identity(root)
        self.assertEqual(previous, before["project_id"])
        self.assertNotEqual(previous, new)


class ManagedBlockTest(StoreTestCase):
    def test_append_to_file_without_trailing_newline_does_not_join_lines(self):
        target = self.tmp / ".gitignore"
        target.write_text("node_modules\ncredentials.local.json", encoding="utf-8")
        gitignore.apply_managed_block(target, [".claude/agents/dev-team"])
        text = target.read_text(encoding="utf-8")
        self.assertIn("credentials.local.json\n", text)
        self.assertNotIn("credentials.local.json#", text)

    def test_second_apply_is_a_noop(self):
        target = self.tmp / ".gitignore"
        entries = [".claude/agents/dev-team", ".worktrees/"]
        gitignore.apply_managed_block(target, entries)
        changed, action = gitignore.apply_managed_block(target, entries)
        self.assertFalse(changed)
        self.assertEqual(action, "unchanged")

    def test_replacing_the_block_preserves_surrounding_content(self):
        target = self.tmp / ".gitignore"
        target.write_text("first\n", encoding="utf-8")
        gitignore.apply_managed_block(target, ["a"])
        target.write_text(target.read_text(encoding="utf-8") + "last\n", encoding="utf-8")
        gitignore.apply_managed_block(target, ["b"])
        text = target.read_text(encoding="utf-8")
        self.assertIn("first\n", text)
        self.assertIn("last\n", text)
        self.assertEqual(text.count(gitignore.BEGIN), 1)
        self.assertEqual(gitignore.read_managed_entries(target), ["b"])

    def test_empty_entries_clear_the_block(self):
        target = self.tmp / ".gitignore"
        target.write_text("keep\n", encoding="utf-8")
        gitignore.apply_managed_block(target, ["a"])
        gitignore.apply_managed_block(target, [])
        self.assertEqual(gitignore.read_managed_entries(target), [])
        self.assertIn("keep", target.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
