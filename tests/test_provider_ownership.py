"""Provider parity: a bind never touches what the project already has, on any provider.

Runs the real installers and render engine — the store version is installed from
this repository — because the guarantee lives in the bash installers as much as
in `bind.py`, and a stubbed installer would prove only the stub.
"""

import json
import os
import shutil
import unittest
from pathlib import Path

from devteam_support import REPO_ROOT, StoreTestCase, requires_bash

from devteam import bind, migrate, project, providers, registry, versions
from devteam.errors import ConflictError

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
