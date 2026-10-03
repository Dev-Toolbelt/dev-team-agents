"""Provider parity: a bind never touches what the project already has, on any provider.

Runs the real installers and render engine — the store version is installed from
this repository — because the guarantee lives in the bash installers as much as
in `bind.py`, and a stubbed installer would prove only the stub.
"""

import json
import os
import shutil
import subprocess
import unittest
from pathlib import Path

from devteam_support import REPO_ROOT, StoreTestCase, requires_bash

from devteam import bind, migrate, project, providers, registry, versions
from devteam.errors import ConflictError, UsageError

#: Files a project authored itself, next to (never on top of) the framework's
#: artifacts. One entry per provider in `providers.ALL_PROVIDERS` — the parity
#: guard below fails the moment a provider is added without its own case.
OWN_FILES = {
    "claude": (
        ".claude/agents/my-agent.md",
        ".claude/commands/my-command.md",
        ".claude/skills/my-skill/SKILL.md",
    ),
    "opencode": (
        ".opencode/agents/my-agent.md",
        ".opencode/skills/my-skill/SKILL.md",
        ".opencode/plugins/my-plugin.ts",
    ),
    "codex": (
        ".codex/agents/my-agent.toml",
        ".codex/skills/my-skill/SKILL.md",
    ),
}

#: A project-owned path at a name the framework writes: the bind must refuse it.
COLLISIONS = {
    "claude": ".claude/skills/project-context/SKILL.md",
    "opencode": ".opencode/agents/backend-developer.md",
    "codex": ".codex/agents/backend-developer.toml",
}

#: A file a v2 installer rendered as real content, with no ledger and no manifest
#: vouching for it: `migrate` must recognise it, quarantine it and reinstall.
V2_OUTPUT = {
    "claude": ".claude/agents/dev-team",
    "opencode": ".opencode/agents/backend-developer.md",
    "codex": ".codex/agents/backend-developer.toml",
}

#: The ledger a standalone installer writes. Claude has none: it has no installer of
#: its own, and its files are links into the store that `_is_managed_path` already
#: recognises — so there is nothing for a bind to trust there.
LEDGERS = {
    "claude": None,
    "opencode": ".dev-team-agents/.provider-owned-opencode",
    "codex": ".dev-team-agents/.provider-owned-codex",
}

TOOLS = {"claude": (), "opencode": ("bash", "python3", "jq"), "codex": ("bash", "python3")}

#: Every bind mode a provider must work in. `copy` shares `link`'s code path for the
#: delegated providers (the installers copy either way), so these two cover both.
MODES = ("link", "vendored")


def _missing_tools(provider):
    return [tool for tool in TOOLS[provider] if shutil.which(tool) is None]


@requires_bash()
class ProviderOwnershipTest(StoreTestCase):
    def setUp(self):
        super().setUp()
        versions.install_from_tree(REPO_ROOT, version="9.9.9", force=True, make_current=True)
        # The Codex installer looks at ~/.codex/prompts; keep it off the real home.
        self._home = os.environ.get("HOME")
        self.fake_home = self.tmp / "fake-home"
        self.fake_home.mkdir()
        os.environ["HOME"] = str(self.fake_home)
        self.addCleanup(self._restore_home)

    def _restore_home(self):
        if self._home is None:
            os.environ.pop("HOME", None)
        else:
            os.environ["HOME"] = self._home

    def _providers(self):
        for provider in providers.ALL_PROVIDERS:
            missing = _missing_tools(provider)
            if missing:
                self.skipTest("{} needs {}".format(provider, ", ".join(missing)))
            yield provider

    def _seed(self, root, rels, text="mine\n"):
        for rel in rels:
            path = root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")

    def _exclude_block(self, root):
        return (root / ".git" / "info" / "exclude").read_text(encoding="utf-8")

    def test_every_provider_has_a_parity_case(self):
        self.assertEqual(set(OWN_FILES), set(providers.ALL_PROVIDERS))
        self.assertEqual(set(COLLISIONS), set(providers.ALL_PROVIDERS))
        self.assertEqual(set(V2_OUTPUT), set(providers.ALL_PROVIDERS))
        self.assertEqual(set(LEDGERS), set(providers.ALL_PROVIDERS))
        self.assertEqual(set(TOOLS), set(providers.ALL_PROVIDERS))

    def _cases(self):
        for provider in self._providers():
            for mode in MODES:
                yield provider, mode

    def test_bind_and_unbind_leave_the_projects_own_files_alone(self):
        for provider, mode in self._cases():
            with self.subTest(provider=provider, mode=mode):
                root = self.new_project("own-{}-{}".format(provider, mode))
                own = OWN_FILES[provider]
                self._seed(root, own)

                result = bind.bind(root, provider_names=[provider], mode=mode)
                manifest = bind.read_manifest(result["project_id"])
                claimed = {item["path"] for item in manifest["artifacts"]}
                exclude = self._exclude_block(root)
                for rel in own:
                    self.assertEqual((root / rel).read_text(encoding="utf-8"), "mine\n", rel)
                    # Neither the file nor any directory holding it is claimed.
                    for part in [rel] + [p.as_posix() for p in Path(rel).parents][:-1]:
                        self.assertNotIn(part, claimed, rel)
                        self.assertNotIn("\n{}\n".format(part), "\n" + exclude, rel)

                unbound = bind.unbind(root)
                moved = {item["path"] for item in unbound["quarantined"]}
                for rel in own:
                    self.assertEqual((root / rel).read_text(encoding="utf-8"), "mine\n", rel)
                    self.assertNotIn(rel, moved)

    def test_migrate_refused_by_any_provider_moves_nothing(self):
        # `migrate` used to quarantine the v2 tree before the bind's checks ran, so a
        # refusal from any provider's preflight left a half-migrated project behind.
        from test_migrate_doctor import materialize_v2_links

        for provider in self._providers():
            with self.subTest(provider=provider):
                root = self.new_project("migrate-clash-{}".format(provider))
                bind.bind(root, provider_names=["claude"], mode="vendored")
                bind.unbind(root, keep_artifacts=True)
                bind.manifest_file(project.load(root)["project_id"]).unlink()
                copied = materialize_v2_links(root)
                rel = COLLISIONS[provider]
                if provider == "claude":
                    shutil.rmtree(str(root / Path(rel).parent))
                self._seed(root, [rel])
                selected = sorted({"claude", provider})

                with self.assertRaises(ConflictError):
                    migrate.apply(root, provider_names=selected, mode="link")
                self.assertEqual((root / rel).read_text(encoding="utf-8"), "mine\n")
                tree = root / project.PROJECT_DIR / "agents"
                self.assertTrue(tree.is_dir() and not tree.is_symlink())
                for path in copied:
                    if not rel.startswith(path + "/"):
                        self.assertFalse((root / path).is_symlink(), path)
                self.assertIsNone(registry.get(project.load(root)["project_id"]))

    def _v2_project(self, name, provider):
        """A v2 install whose provider files are real copies nothing vouches for."""
        from test_migrate_doctor import materialize_v2_links

        root = self.new_project(name)
        selected = sorted({"claude", provider})
        bind.bind(root, provider_names=selected, mode="vendored")
        bind.unbind(root, keep_artifacts=True)
        bind.manifest_file(project.load(root)["project_id"]).unlink()
        materialize_v2_links(root)
        for ledger in (root / project.PROJECT_DIR).glob(".provider-owned-*"):
            ledger.unlink()
        return root, selected

    def test_migrate_takes_over_the_files_a_v2_installer_rendered(self):
        for provider in self._providers():
            with self.subTest(provider=provider):
                root, selected = self._v2_project("v2-output-{}".format(provider), provider)
                rel = V2_OUTPUT[provider]
                self.assertTrue((root / rel).exists() and not (root / rel).is_symlink())
                own = OWN_FILES[provider]
                self._seed(root, own)

                preview = migrate.plan(root, provider_names=selected, mode="link")
                self.assertIn(rel, preview["v2_copies"])
                for path in own:
                    self.assertNotIn(path, preview["v2_copies"])

                result = migrate.apply(root, provider_names=selected, mode="link")
                moved = {item["from"] for item in result["quarantined"]}
                self.assertIn(rel, moved)
                self.assertTrue((root / rel).exists(), rel)
                for path in own:
                    self.assertEqual((root / path).read_text(encoding="utf-8"), "mine\n", path)
                    self.assertNotIn(path, moved)

    def test_a_project_file_at_a_v2_output_path_is_not_taken_for_the_framework(self):
        version_dir = versions.require(versions.resolve(None))
        # Each one names the framework, so only the renderer's structure tells them apart.
        lookalikes = {
            "claude": ("---\nname: dev-team\n---\nsee dev-team-agents\n",),
            "opencode": (
                "---\ndescription: my own backend agent\n---\nsee dev-team-agents\n",
                "---\ndescription: x\nmode: primary\n---\nsee dev-team-agents\n",
            ),
            "codex": (
                'name = "backend-developer"\ndescription = "mine"\n',
                'name = "other"\ndeveloper_instructions = """\ndev-team-agents\n"""\n',
                'description = "x"\ndeveloper_instructions = """\nname = "backend-developer"\n'
                'dev-team-agents\n"""\n',
            ),
        }
        self.assertEqual(set(lookalikes), set(providers.ALL_PROVIDERS))
        for provider in providers.ALL_PROVIDERS:
            for index, text in enumerate(lookalikes[provider]):
                with self.subTest(provider=provider, case=index):
                    root = self.new_project("lookalike-{}-{}".format(provider, index))
                    rel = V2_OUTPUT[provider]
                    self._seed(root, [rel], text=text)
                    self.assertFalse(providers.is_v2_render(rel, root / rel, version_dir))

    def test_every_file_an_installer_renders_is_recognised_as_a_render(self):
        # Not one sample file: every target, so a command whose source never names the
        # framework cannot slip through and bring the original refusal back.
        for provider in self._providers():
            if provider not in providers.DELEGATED_INSTALLERS:
                continue
            with self.subTest(provider=provider):
                root = self.new_project("renders-{}".format(provider))
                result = bind.bind(root, provider_names=[provider], mode="link")
                version_dir = versions.require(versions.resolve(None))
                targets = providers.delegated_targets(provider, version_dir, root)
                real = [rel for rel in targets if not (root / rel).is_symlink()]
                self.assertTrue(real)
                missed = [
                    rel for rel in real if not providers.is_v2_render(rel, root / rel, version_dir)
                ]
                self.assertEqual(missed, [])
                bind.unbind(root)
                self.assertTrue(result["project_id"])

    def test_a_v3_bind_is_not_taken_for_a_v2_install(self):
        # A v3 bind writes the same real files; its manifest claims them.
        for provider, mode in self._cases():
            with self.subTest(provider=provider, mode=mode):
                root = self.new_project("bound-{}-{}".format(provider, mode))
                bind.bind(root, provider_names=[provider], mode=mode)
                if mode == "vendored":
                    continue  # refused by its own guard, covered in test_migrate_doctor
                with self.assertRaises(UsageError):
                    migrate.plan(root, provider_names=[provider], mode=mode)

    def test_bind_points_a_v2_render_at_migrate(self):
        for provider in self._providers():
            if provider not in providers.DELEGATED_INSTALLERS:
                continue
            with self.subTest(provider=provider):
                root, selected = self._v2_project("v2-bind-{}".format(provider), provider)
                # The vendored tree has its own refusal; leave only the provider files.
                for name in migrate.detect(root)["vendored_trees"]:
                    shutil.rmtree(str(root / project.PROJECT_DIR / name))
                identity = project.load(root)["project_id"]
                registry_before = registry.get(identity)
                code, out, _ = self.run_cli(
                    "--json", "bind", str(root), "--provider", provider, "--mode", "link"
                )
                self.assertEqual(code, 4)
                payload = json.loads(out)
                self.assertEqual(payload["details"]["reason"], bind.V2_INSTALL_REASON)
                self.assertIn("/.{}/".format(provider), payload["details"]["path"], payload)
                self.assertEqual(registry.get(identity), registry_before)

    def test_migrate_takes_a_ledgered_file_and_quarantines_the_ledger(self):
        for provider in self._providers():
            if provider not in providers.DELEGATED_INSTALLERS:
                continue
            with self.subTest(provider=provider):
                root, selected = self._v2_project("v2-ledger-{}".format(provider), provider)
                rel = V2_OUTPUT[provider]
                # Edited past recognition, but the installer's own ledger vouches for it.
                (root / rel).write_text("edited\n", encoding="utf-8")
                ledger = "{}/.provider-owned-{}".format(project.PROJECT_DIR, provider)
                (root / ledger).write_text(rel + "\n", encoding="utf-8")

                # No explicit providers: detection must still see the v2 output.
                preview = migrate.plan(root, mode="link")
                self.assertIn(provider, preview["providers"])
                self.assertIn(rel, preview["v2_copies"])
                self.assertIn(ledger, preview["v2_copies"])

                result = migrate.apply(root, mode="link")
                moved = {item["from"] for item in result["quarantined"]}
                self.assertTrue({rel, ledger} <= moved)
                self.assertFalse((root / ledger).exists())

    @unittest.skipUnless(hasattr(os, "mkfifo"), "needs mkfifo")
    def test_a_fifo_in_a_skill_does_not_hang_the_plan(self):
        version_dir = versions.require(versions.resolve(None))
        root = self.new_project("fifo")
        skill = root / ".codex" / "skills" / "devteam-review"
        skill.mkdir(parents=True)
        os.mkfifo(str(skill / "SKILL.md"))
        self.assertFalse(
            providers.is_v2_render(".codex/skills/devteam-review", skill, version_dir)
        )

    def _standalone_install(self, root, provider):
        """`install-<provider>.sh` run by hand in a project bound for Claude only.

        The case the ledger matters for: on an unbound project the installer also
        vendors `.dev-team-agents/scripts`, which bind refuses first and sends to
        `migrate`. Bound, the installer writes only its files and its ledger.
        """
        bind.bind(root, provider_names=["claude"], mode="link")
        version_dir = versions.require(versions.resolve(None))
        script = version_dir / "scripts" / providers.DELEGATED_INSTALLERS[provider]
        subprocess.run(
            ["bash", str(script), "--source", str(version_dir)],
            cwd=str(root),
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        ledger = LEDGERS[provider]
        self.assertTrue((root / ledger).is_file(), ledger)
        return version_dir

    def test_bind_trusts_the_ledger_a_standalone_install_wrote(self):
        for provider in self._providers():
            ledger = LEDGERS[provider]
            if ledger is None:
                continue
            with self.subTest(provider=provider):
                root = self.new_project("ledger-{}".format(provider))
                self._standalone_install(root, provider)
                rel = V2_OUTPUT[provider]
                # Edited past recognition: only the ledger can vouch for it now.
                (root / rel).write_text("edited\n", encoding="utf-8")
                own = OWN_FILES[provider]
                self._seed(root, own)

                result = bind.bind(root, provider_names=["claude", provider], mode="link")
                manifest = bind.read_manifest(result["project_id"])
                claimed = {item["path"] for item in manifest["artifacts"]}
                self.assertIn(rel, claimed)
                self.assertNotEqual((root / rel).read_text(encoding="utf-8"), "edited\n")
                self.assertFalse((root / ledger).exists())
                self.assertIn(ledger, {item["path"] for item in result["retired"]})
                for path in own:
                    self.assertEqual((root / path).read_text(encoding="utf-8"), "mine\n", path)
                    self.assertNotIn(path, claimed)

    def test_a_refused_bind_leaves_the_ledger_and_a_file_outside_it_is_still_foreign(self):
        for provider in self._providers():
            ledger = LEDGERS[provider]
            if ledger is None:
                continue
            with self.subTest(provider=provider):
                root = self.new_project("ledger-clash-{}".format(provider))
                self._standalone_install(root, provider)
                rel = V2_OUTPUT[provider]
                lines = (root / ledger).read_text(encoding="utf-8").splitlines()
                (root / ledger).write_text(
                    "\n".join(line for line in lines if line != rel) + "\n", encoding="utf-8"
                )
                (root / rel).write_text("mine\n", encoding="utf-8")
                before = (root / ledger).read_text(encoding="utf-8")

                manifest_before = bind.read_manifest(project.load(root)["project_id"])
                with self.assertRaises(ConflictError):
                    bind.bind(root, provider_names=["claude", provider], mode="link")
                self.assertEqual((root / rel).read_text(encoding="utf-8"), "mine\n")
                self.assertEqual((root / ledger).read_text(encoding="utf-8"), before)
                self.assertEqual(
                    bind.read_manifest(project.load(root)["project_id"]), manifest_before
                )

    def test_bind_refuses_a_collision_before_writing_anything(self):
        for provider, mode in self._cases():
            with self.subTest(provider=provider, mode=mode):
                root = self.new_project("clash-{}-{}".format(provider, mode))
                rel = COLLISIONS[provider]
                self._seed(root, [rel])

                with self.assertRaises(ConflictError):
                    bind.bind(root, provider_names=[provider], mode=mode)
                self.assertEqual((root / rel).read_text(encoding="utf-8"), "mine\n")
                self.assertFalse((root / project.PROJECT_DIR / "project.json").exists())

    def test_every_provider_link_resolves_and_vendored_links_are_relative(self):
        for provider, mode in self._cases():
            with self.subTest(provider=provider, mode=mode):
                root = self.new_project("links-{}-{}".format(provider, mode))
                result = bind.bind(root, provider_names=[provider], mode=mode)
                self.assertEqual(result["mode"], mode)
                provider_dir = root / ".{}".format(provider)
                links = [p for p in provider_dir.rglob("*") if p.is_symlink()]
                self.assertTrue(links, "{} bind produced no links".format(provider))
                for link in links:
                    self.assertTrue(link.exists(), "dangling: {}".format(link))
                    if mode == "vendored":
                        # Committed with the project: must resolve on every clone.
                        self.assertFalse(os.path.isabs(os.readlink(link)), str(link))

    def test_a_rebind_after_losing_project_json_keeps_the_registered_id(self):
        for provider, mode in self._cases():
            with self.subTest(provider=provider, mode=mode):
                root = self.new_project("lost-id-{}-{}".format(provider, mode))
                first = bind.bind(root, provider_names=[provider], mode=mode)
                (root / project.PROJECT_DIR / "project.json").unlink()

                second = bind.bind(root, provider_names=[provider], mode=mode)
                self.assertEqual(second["project_id"], first["project_id"])
                self.assertEqual(project.load(root)["project_id"], first["project_id"])
                at_path = [
                    pid for pid, entry in registry.entries().items()
                    if entry["path"] == str(root.resolve())
                ]
                self.assertEqual(at_path, [first["project_id"]])

    def test_vendored_bind_installs_every_selected_provider(self):
        selected = list(self._providers())
        root = self.new_project("vendored-all")
        result = bind.bind(root, provider_names=selected, mode="vendored")
        self.assertEqual(result["providers"], selected)
        kinds = {}
        for item in bind.read_manifest(result["project_id"])["artifacts"]:
            kinds.setdefault(item.get("provider", "claude"), []).append(item["path"])
        for provider in selected:
            self.assertTrue(kinds.get(provider), provider)
        if "codex" in selected:
            hooks = json.loads((root / providers.CODEX_HOOKS_FILE).read_text(encoding="utf-8"))
            command = hooks["hooks"]["Stop"][0]["hooks"][0]["command"]
            self.assertIn(".dev-team-agents/scripts/hooks/stop.sh", command)
            self.assertTrue((root / ".dev-team-agents" / "scripts" / "hooks" / "stop.sh").is_file())

    def test_installers_write_nothing_unrecorded_into_a_bound_project(self):
        for provider in self._providers():
            if provider not in providers.DELEGATED_INSTALLERS:
                continue
            with self.subTest(provider=provider):
                root = self.new_project("stray-" + provider)
                bind.bind(root, provider_names=[provider], mode="link")
                framework = root / project.PROJECT_DIR
                self.assertFalse((framework / "VERSION").exists())
                self.assertFalse((framework / "user-data").exists())

    def test_a_directory_level_manifest_migrates_without_quarantine(self):
        for provider in ("opencode", "codex"):
            if _missing_tools(provider):
                continue
            with self.subTest(provider=provider):
                root = self.new_project("legacy-" + provider)
                result = bind.bind(root, provider_names=[provider])
                project_id = result["project_id"]

                # Rewrite the manifest into the shape the old bind recorded.
                manifest = bind.read_manifest(project_id)
                manifest["artifacts"] = [
                    item for item in manifest["artifacts"] if item.get("provider") != provider
                ] + [
                    {"path": rel, "kind": "delegated", "provider": provider}
                    for rel in providers.LEGACY_DELEGATED_PATHS[provider]
                ]
                bind.jsonio.write_json_atomic(bind.manifest_file(project_id), manifest)
                self._seed(root, OWN_FILES[provider])

                again = bind.bind(root, provider_names=[provider])
                self.assertEqual(again["pruned"]["quarantined"], [])
                paths = {item["path"] for item in bind.read_manifest(project_id)["artifacts"]}
                for legacy in providers.LEGACY_DELEGATED_PATHS[provider]:
                    if legacy != providers.CODEX_HOOKS_FILE:
                        self.assertNotIn(legacy, paths)

                # And an unbind straight from the old shape removes only framework files.
                bind.jsonio.write_json_atomic(bind.manifest_file(project_id), manifest)
                unbound = bind.unbind(root)
                moved = {item["path"] for item in unbound["quarantined"]}
                self.assertFalse(moved & set(providers.LEGACY_DELEGATED_PATHS[provider]))
                for rel in OWN_FILES[provider]:
                    self.assertEqual((root / rel).read_text(encoding="utf-8"), "mine\n", rel)
                agents_dir = root / ".{}".format(provider) / "agents"
                self.assertFalse((agents_dir / "backend-developer.toml").exists())
                self.assertFalse((agents_dir / "backend-developer.md").exists())

    def test_codex_unbind_keeps_the_projects_own_hooks(self):
        if _missing_tools("codex"):
            self.skipTest("codex needs bash and python3")
        root = self.new_project("hooks")
        own_hook = {"matcher": "*", "hooks": [{"type": "command", "command": "echo mine"}]}
        self._seed(root, [providers.CODEX_HOOKS_FILE], json.dumps({"hooks": {"Stop": [own_hook]}}))

        bind.bind(root, provider_names=["codex"])
        wired = json.loads((root / providers.CODEX_HOOKS_FILE).read_text(encoding="utf-8"))
        self.assertGreater(len(wired["hooks"]["Stop"]), 1)
        self.assertNotIn(providers.CODEX_HOOKS_FILE, self._exclude_block(root))

        bind.unbind(root)
        left = json.loads((root / providers.CODEX_HOOKS_FILE).read_text(encoding="utf-8"))
        self.assertEqual(left["hooks"], {"Stop": [own_hook]})

    def test_codex_bind_never_deletes_outside_the_project(self):
        if _missing_tools("codex"):
            self.skipTest("codex needs bash and python3")
        prompt = self.fake_home / ".codex" / "prompts" / "devteam-plan.md"
        prompt.parent.mkdir(parents=True)
        prompt.write_text("mine\n", encoding="utf-8")
        local = "prompts/devteam-plan.md"
        root = self.new_project("prompts")
        self._seed(root, [".codex/" + local])

        bind.bind(root, provider_names=["codex"])
        self.assertTrue(prompt.exists())
        self.assertTrue((root / ".codex" / local).exists())


if __name__ == "__main__":
    unittest.main()
