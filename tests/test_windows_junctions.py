"""Link mode on Windows without symlink privilege: NTFS junctions.

Windows without Developer Mode refuses `os.symlink` but lets any user create a junction to a
directory. Python sees a junction as a directory, not a symlink, so every place that asks
"is this a link?" goes through `paths.is_link`. The danger these tests pin is the store's
files being moved or deleted through a junction taken for real content.

The junction cases run only on Windows; the CI matrix has a windows-latest job. Runners there
hold the symlink privilege, so `os.symlink` is patched to fail and force the junction path.
"""

import os
import shutil
import unittest
from pathlib import Path
from unittest import mock

from devteam_support import REPO_ROOT, StoreTestCase, requires_bash

from devteam import bind, doctor, paths, providers, quarantine, versions
from test_windows_link_stubs import TOOLS

ON_WINDOWS = os.name == "nt"


def _refuse_symlink(*_args, **_kwargs):
    raise OSError(1314, "A required privilege is not held by the client")


class LinkHelpersEverywhereTest(StoreTestCase):
    """What holds on every platform: a real directory is never treated as a link."""

    def test_a_real_directory_is_not_a_link_and_is_never_removed_as_one(self):
        real = self.tmp / "real"
        real.mkdir()
        (real / "keep.txt").write_text("keep\n", encoding="utf-8")
        self.assertFalse(paths.is_link(real))
        self.assertFalse(paths.is_junction(real))
        with self.assertRaises(OSError):
            paths.remove_link(real)
        self.assertEqual((real / "keep.txt").read_text(encoding="utf-8"), "keep\n")

    def test_a_symlink_is_a_link_and_removing_it_keeps_the_target(self):
        target = self.tmp / "target"
        target.mkdir()
        (target / "keep.txt").write_text("keep\n", encoding="utf-8")
        link = self.tmp / "link"
        try:
            os.symlink(str(target), str(link), target_is_directory=True)
        except OSError:
            self.skipTest("no symlink privilege here")
        self.assertTrue(paths.is_link(link))
        paths.remove_link(link)
        self.assertFalse(os.path.lexists(str(link)))
        self.assertTrue((target / "keep.txt").is_file())

    def test_every_provider_has_a_junction_parity_case(self):
        # Runs everywhere, so adding a provider fails on every OS until it gets a case.
        self.assertEqual(set(JunctionProviderParityTest.LINKS), set(providers.ALL_PROVIDERS))

    def test_make_dir_link_raises_off_windows_when_symlinks_fail(self):
        if ON_WINDOWS:
            self.skipTest("on Windows the junction fallback runs instead")
        target = self.tmp / "t"
        target.mkdir()
        with mock.patch("os.symlink", _refuse_symlink):
            with self.assertRaises(OSError):
                paths.make_dir_link(target, self.tmp / "l")


@unittest.skipUnless(ON_WINDOWS, "NTFS junctions exist only on Windows")
class JunctionHelpersTest(StoreTestCase):
    def _junction(self):
        target = self.tmp / "store-tree"
        target.mkdir()
        (target / "agent.md").write_text("# agent\n", encoding="utf-8")
        link = self.tmp / "junction"
        paths.create_junction(target, link)
        return target, link

    def test_a_junction_is_a_link_not_a_symlink(self):
        _target, link = self._junction()
        self.assertTrue(paths.is_junction(link))
        self.assertTrue(paths.is_link(link))
        self.assertFalse(link.is_symlink())
        self.assertTrue(paths.read_link(link))

    def test_removing_a_junction_keeps_every_file_it_pointed_to(self):
        target, link = self._junction()
        paths.remove_link(link)
        self.assertFalse(os.path.lexists(str(link)))
        self.assertEqual((target / "agent.md").read_text(encoding="utf-8"), "# agent\n")

    def test_make_dir_link_falls_back_to_a_junction(self):
        target = self.tmp / "t"
        target.mkdir()
        with mock.patch("os.symlink", _refuse_symlink):
            kind = paths.make_dir_link(target, self.tmp / "l")
        self.assertEqual(kind, "junction")
        self.assertTrue(paths.is_junction(self.tmp / "l"))

    def test_quarantine_refuses_a_junction(self):
        target, link = self._junction()
        with self.assertRaises(OSError):
            quarantine.move(link, "p", group="pruned")
        self.assertTrue((target / "agent.md").is_file())


@unittest.skipUnless(ON_WINDOWS, "NTFS junctions exist only on Windows")
class JunctionBindTest(StoreTestCase):
    def setUp(self):
        super().setUp()
        self.install_version("3.0.0", activate=True)
        self.version_dir = versions.require(versions.resolve(None))

    def _bind(self, root, provider="claude"):
        with mock.patch("os.symlink", _refuse_symlink):
            return bind.bind(root, provider_names=[provider], mode="link")

    def test_link_mode_binds_with_junctions_without_symlink_privilege(self):
        root = self.new_project("junctions")
        with mock.patch("os.symlink", _refuse_symlink):
            self.assertTrue(bind.symlink_supported(root))
        result = self._bind(root)
        self.assertEqual(result["mode"], "link")
        for rel, _source in providers.claude_artifacts(self.version_dir):
            self.assertTrue(paths.is_junction(root / rel), rel)
        self.assertTrue(paths.is_junction(root / ".dev-team-agents" / "scripts"))

    def test_a_second_bind_replaces_the_junctions_and_the_store_survives(self):
        root = self.new_project("rebind")
        self._bind(root)
        before = sorted(p.name for p in (self.version_dir / "agents").iterdir())
        result = self._bind(root)
        self.assertEqual(result["retired"], [])  # links are removed, never quarantined
        self.assertEqual(
            paths.realpath_normalized(root / ".claude" / "agents" / "dev-team"),
            paths.realpath_normalized(self.version_dir / "agents"),
        )
        self.assertEqual(sorted(p.name for p in (self.version_dir / "agents").iterdir()), before)
        self.assertTrue(paths.is_junction(root / ".claude" / "agents" / "dev-team"))

    def test_unbind_removes_the_junctions_and_keeps_the_store(self):
        root = self.new_project("unbind")
        self._bind(root)
        files = sorted(str(p.relative_to(self.version_dir)) for p in self.version_dir.rglob("*"))
        bind.unbind(root)
        self.assertFalse(os.path.lexists(str(root / ".claude" / "agents" / "dev-team")))
        self.assertEqual(sorted(str(p.relative_to(self.version_dir)) for p in self.version_dir.rglob("*")), files)

    def test_vendored_mode_vendors_real_trees_when_symlinks_fail(self):
        root = self.new_project("vendored")
        with mock.patch("os.symlink", _refuse_symlink):
            bind.bind(root, provider_names=["claude"], mode="vendored")
        agents = root / ".claude" / "agents" / "dev-team"
        self.assertTrue(agents.is_dir())
        self.assertFalse(paths.is_link(agents))  # a junction is absolute: it would not survive a commit

    def test_doctor_reports_no_broken_link(self):
        root = self.new_project("doctor")
        self._bind(root)
        findings = doctor.check_project(root)
        messages = " ".join(str(f) for f in (findings[0] if isinstance(findings, tuple) else findings))
        self.assertNotIn("broken links", messages)
        self.assertIn("artifact(s) resolve", messages)  # positive: the junctions were checked


@requires_bash()
@unittest.skipUnless(ON_WINDOWS, "NTFS junctions exist only on Windows")
class JunctionProviderParityTest(StoreTestCase):
    """Every provider's link-mode bind succeeds without symlink privilege."""

    #: provider -> the link its own code writes: Python's `_materialize` for Claude, the
    #: installer's `po_link_skills` (bash) for the delegated providers.
    LINKS = {
        "claude": ".claude/agents/dev-team",
        "codex": ".codex/skills/dev-team-agents",
        "opencode": ".opencode/skills/dev-team-agents",
    }

    def setUp(self):
        super().setUp()
        versions.install_from_tree(REPO_ROOT, version="9.9.9", force=True, make_current=True)

    def test_the_installers_junction_survives_a_rerun_and_the_store_too(self):
        for provider in providers.DELEGATED_INSTALLERS:
            with self.subTest(provider=provider):
                missing = [t for t in TOOLS[provider] if shutil.which(t) is None]
                if missing:
                    self.skipTest("{} needs {}".format(provider, ", ".join(missing)))
                root = self.new_project("installer-" + provider)
                link = Path(root) / ".{}/skills/dev-team-agents".format(provider)
                store_skills = versions.require(versions.resolve(None)) / "skills"
                before = sorted(str(p.relative_to(store_skills)) for p in store_skills.rglob("*"))
                with mock.patch.dict(os.environ, {"DEVTEAM_TEST_NO_SYMLINK": "1"}):
                    for _ in range(2):  # the second run removes the first junction
                        bind.bind(root, provider_names=[provider], mode="link")
                self.assertTrue(paths.is_junction(link), link)
                after = sorted(str(p.relative_to(store_skills)) for p in store_skills.rglob("*"))
                self.assertEqual(after, before)

    def test_each_provider_binds_in_link_mode(self):
        for provider in providers.ALL_PROVIDERS:
            with self.subTest(provider=provider):
                missing = [t for t in TOOLS[provider] if shutil.which(t) is None]
                if missing:
                    self.skipTest("{} needs {}".format(provider, ", ".join(missing)))
                root = self.new_project("parity-" + provider)
                # os.symlink for the Python side, the test switch for the installer's `ln -s`.
                with mock.patch("os.symlink", _refuse_symlink), mock.patch.dict(
                    os.environ, {"DEVTEAM_TEST_NO_SYMLINK": "1"}
                ):
                    result = bind.bind(root, provider_names=[provider], mode="link")
                self.assertEqual(result["mode"], "link")
                self.assertTrue(paths.is_junction(Path(root) / self.LINKS[provider]))
