"""A contract sweep across the *whole* devteam CLI command surface (ADR-0011).

`tests/test_cli_contract.py` and `tests/test_update_and_contract.py` already pin
specific breakages (argparse failures emitting one document, an unexpected
exception reaching stdout as a traceback). Neither asserts the contract across
every subcommand, so a new or changed command can violate it silently -- the
first thing that would notice is the desktop app, in production, against a
user's store. This file is that missing sweep: it discovers the command surface
from the real parser (never a hardcoded list, which goes stale the moment a
command is added or renamed) and runs the parts of the contract that hold
universally, against three store states.

It also pins two surfaces that this sweep exists to guard, but that are new
enough to have no dedicated coverage yet: `devteam catalog` (ADR-0011's
read-only browse command) and `scripts/lib/devteam/compat.py` (the schema
numbers a client reads before it writes to the store).
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import unittest

from devteam_support import CLI, StoreTestCase, make_git_project

from devteam import bind as bind_module
from devteam import cli as devteam_cli
from devteam import compat, creds, errors, paths, project, registry


VALID_EXIT_CODES = {
    errors.EXIT_OK,
    errors.EXIT_FINDINGS,
    errors.EXIT_USAGE,
    errors.EXIT_ENVIRONMENT,
    errors.EXIT_CONFLICT,
}

# Commands the bulk sweep invokes with no other arguments. Both are excluded,
# named explicitly rather than silently skipped:
#   - `update` reaches the network to fetch a release; run offline it can hang
#     or fail unpredictably instead of exercising the contract.
#   - `uninstall` removes the core store. Even though that store is this test's
#     own isolated $DEVTEAM_HOME, running it mid-sweep would pull the store out
#     from under every command that runs after it in the same state.
# Every other discovered command is safe bare: it either performs a read, or it
# fails validation (a missing required argument) before doing anything, which
# is exactly the path this sweep means to exercise.
SKIP_INVOCATION = {
    ("update",): "reaches the network to fetch a release",
    ("uninstall",): "removes the core store the rest of the sweep still needs",
    # Runs until its stdin closes or it is sent SIGTERM, and its `--json` stdout is
    # JSON Lines, not one document — the one streaming exception. Its contract (one
    # compact document per event, each with `ok`, `end` last) is pinned in
    # `test_notifications.WatchTest`, against a real stream.
    ("notifications", "watch"): "streams until stdin closes; covered by test_notifications",
}


def discover_commands(parser=None):
    """Walk the real parser's subparsers tree. Never a hardcoded command list.

    Returns ``(leaves, groups)``, both lists of path tuples (e.g. ``("cred",
    "get")``). A path is a *leaf* when its subparser has its own handler
    (``set_defaults(func=...)``) -- it is directly invocable. A path is a
    *group* when its subparser itself has a nested ``_SubParsersAction`` --
    it must be walked further. The two are not exclusive: `catalog` (added
    alongside `store`/`prefs`/`cred`, but a valid, meaningful call on its own
    the way those three are not) is both -- `devteam catalog` alone has a
    handler, and `devteam catalog agents|skills|commands|show` are its own
    invocable leaves.

    A hardcoded list is a list that goes stale the moment someone adds a
    command -- exactly the failure this suite exists to prevent.
    """
    if parser is None:
        parser = devteam_cli.build_parser()

    def walk(node, prefix):
        leaves = []
        groups = []
        for action in node._actions:
            if not isinstance(action, argparse._SubParsersAction):
                continue
            for name, sub in action.choices.items():
                path = prefix + (name,)
                has_handler = bool(getattr(sub, "_defaults", {}).get("func"))
                if has_handler:
                    leaves.append(path)
                nested = [a for a in sub._actions if isinstance(a, argparse._SubParsersAction)]
                if nested:
                    groups.append(path)
                    child_leaves, child_groups = walk(sub, path)
                    leaves.extend(child_leaves)
                    groups.extend(child_groups)
        return leaves, groups

    return walk(parser, ())


class DiscoveryTest(unittest.TestCase):
    """The enumeration itself is asserted -- a broken walk would silently test nothing.

    Building a parser is pure (no filesystem I/O), so this does not need the
    store isolation `StoreTestCase` provides.
    """

    def test_discovery_finds_a_plausible_command_surface(self):
        leaves, groups = discover_commands()
        self.assertGreaterEqual(
            len(leaves),
            20,
            "the parser walk found suspiciously few commands -- it is probably broken, "
            "not testing a suite that shrank that far",
        )
        self.assertEqual(len(leaves), len(set(leaves)), "the walk reported a command twice")

    def test_every_group_contributes_at_least_one_nested_command(self):
        # A group is only ever added to `groups` because its subparser carries a
        # nested `_SubParsersAction` -- so if the walk into it finds zero leaves,
        # the walk itself is broken (e.g. it stopped resolving `.choices`), not
        # the command surface. This is what catches a `catalog`-shaped group
        # (or any future one) landing with the walk silently skipping it.
        leaves, groups = discover_commands()
        self.assertTrue(groups, "no group commands were discovered at all -- the walk is broken")
        for group in groups:
            nested = [leaf for leaf in leaves if leaf[: len(group)] == group and leaf != group]
            self.assertTrue(
                nested,
                "{} is a group (has nested subcommands) but the walk found none under it "
                "-- the walk is broken".format(" ".join(group)),
            )

    def test_every_leaf_has_a_handler(self):
        # `main()` calls `args.func(args, emitter)` unconditionally once a command
        # resolves to a leaf; a leaf with no handler would crash there regardless
        # of the contract. Catching it here, at discovery time, says which command
        # is missing `set_defaults(func=...)` instead of a bare AttributeError.
        parser = devteam_cli.build_parser()

        def handler_for(node, path):
            if not path:
                return getattr(node, "_defaults", {}).get("func")
            for action in node._actions:
                if isinstance(action, argparse._SubParsersAction) and path[0] in action.choices:
                    return handler_for(action.choices[path[0]], path[1:])
            return None

        leaves, _groups = discover_commands(parser)
        for leaf in leaves:
            self.assertIsNotNone(
                handler_for(parser, leaf), "{} has no handler".format(" ".join(leaf))
            )


class ContractSweepTest(StoreTestCase):
    """Sweeps every discovered leaf command against three store states.

    Most commands fail validation with no arguments -- that is the point: the
    failure itself must still honour the contract. `run_cli_in` (unlike
    `StoreTestCase.run_cli`) always passes an explicit `cwd`, because several
    commands (`bind`, `unbind`, `sync`, `pin`, `migrate`, `upgrade`, `doctor`)
    default an omitted path argument to the process's current directory
    (`project.resolve_root`) -- inheriting the test runner's own cwd would let
    a bare sweep call operate on this repository itself instead of the
    isolated store. Every invocation below gets a *fresh* directory rather than
    a directory shared across commands in the same state: `bind` writes a
    project identity file even when it goes on to fail (no active version to
    resolve), so reusing one directory would let an earlier command's partial
    side effect change what a later command in the same state sees.
    """

    @staticmethod
    def run_cli_in(cwd, *args):
        result = subprocess.run(
            [sys.executable, str(CLI), *args],
            cwd=str(cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=dict(os.environ),
            check=False,
        )
        return (
            result.returncode,
            result.stdout.decode("utf-8", "replace"),
            result.stderr.decode("utf-8", "replace"),
        )

    def _fresh_dir(self):
        self._dir_counter = getattr(self, "_dir_counter", 0) + 1
        d = self.tmp / "cwd-{}".format(self._dir_counter)
        d.mkdir()
        return d

    def _fresh_bound_project(self):
        self._dir_counter = getattr(self, "_dir_counter", 0) + 1
        root = make_git_project(self.tmp / "bound-{}".format(self._dir_counter), name="p{}".format(self._dir_counter))
        code, out, err = self.run_cli("bind", str(root), "--json")
        self.assertEqual(code, 0, "sweep fixture: bind failed: {}".format(err))
        json.loads(out)
        return root

    def _assert_stdout_not_json_document(self, label, mode, out):
        if out.strip():
            with self.assertRaises(
                ValueError, msg="{}: {} mode wrote a JSON document to stdout".format(label, mode)
            ):
                json.loads(out)

    def _assert_json_contract(self, label, code, out, err):
        self.assertIn(
            code, VALID_EXIT_CODES, "{}: exit code {} is outside the documented set".format(label, code)
        )
        # Channels must not cross: stderr carries warnings and human text, never
        # the JSON document itself.
        self._assert_stdout_not_json_document(label + " (stderr)", "json", err)

        if not out.strip():
            return  # "empty or exactly one document" -- empty conforms too.

        try:
            body = json.loads(out)
        except ValueError:
            self.fail("{}: --json stdout is not one parseable document: {!r}".format(label, out[:300]))
        self.assertIsInstance(body, dict, "{}: --json stdout is not a JSON object".format(label))
        self.assertIn("ok", body, "{}: payload carries no 'ok' field".format(label))

        if code == errors.EXIT_OK:
            self.assertTrue(body["ok"], "{}: exit 0 but ok=False: {}".format(label, body))
        else:
            self.assertFalse(body["ok"], "{}: exit {} but ok=True: {}".format(label, code, body))
            if code != errors.EXIT_FINDINGS:
                # A genuine error (usage/environment/conflict) always carries the
                # error shape from `DevteamError.payload()`. Exit 1 ("findings")
                # is different -- e.g. `doctor`'s warn/fail status -- and is not
                # required to carry `error`/`exit_code`.
                self.assertIn("error", body, "{}: exit {} payload has no 'error'".format(label, code))
                self.assertTrue(body["error"], "{}: 'error' is empty".format(label))
                self.assertEqual(
                    body.get("exit_code"),
                    code,
                    "{}: payload exit_code does not match the process exit code".format(label),
                )

    def _sweep(self, state_label, cwd_factory):
        leaves, _groups = discover_commands()
        runnable = [path for path in leaves if path not in SKIP_INVOCATION]
        self.assertTrue(runnable)
        for path in runnable:
            label = "{} [{}]".format(" ".join(path), state_label)
            with self.subTest(state=state_label, command=" ".join(path)):
                json_code, json_out, json_err = self.run_cli_in(cwd_factory(), *path, "--json")
                self._assert_json_contract(label, json_code, json_out, json_err)

                human_code, human_out, human_err = self.run_cli_in(cwd_factory(), *path)
                self.assertIn(
                    human_code,
                    VALID_EXIT_CODES,
                    "{}: human-mode exit code {} outside the documented set".format(label, human_code),
                )
                self._assert_stdout_not_json_document(label, "human", human_out)

        for path, reason in SKIP_INVOCATION.items():
            self.assertIn(path, leaves, "{} was expected to still be discoverable ({})".format(path, reason))

    def test_sweep_against_an_empty_store(self):
        """Nothing installed, nothing bound -- the state most commands hit first."""
        self._sweep("empty-store", self._fresh_dir)

    def test_sweep_against_an_installed_but_unbound_store(self):
        """A version is active, but the working directory is not a bound project."""
        self.install_version("3.0.0", activate=True)
        self._sweep("installed-unbound", self._fresh_dir)

    def test_sweep_against_an_installed_and_bound_project(self):
        """A version is active and the command runs inside an actual bound project.

        Each command gets its OWN freshly bound project (via `_fresh_bound_project`)
        rather than one shared across the state: `unbind`, reached early in
        discovery order, would otherwise remove the binding out from under every
        command that runs after it in the same sweep.
        """
        self.install_version("3.0.0", activate=True)
        self._sweep("installed-bound", self._fresh_bound_project)


class CredGetJsonRefusalTest(StoreTestCase):
    """`cred get` refuses `--json` -- a documented, deliberate exception.

    ADR-0010 and `CLAUDE-md/cli.md` § The `--json` contract: wrapping a secret
    in a JSON document puts it somewhere a client is likely to log, so this
    command emits one plain value on stdout and nothing else, and refuses
    `--json` with a normal, conforming error document (exit 2) instead. That
    refusal IS the contract for this command -- if this test ever fails because
    `cred get --json` started emitting the value, that is a regression in
    `cli.py` to fix, not a signal to relax this test.
    """

    def test_cred_get_refuses_json_as_a_conforming_usage_error(self):
        self.install_version("3.0.0", activate=True)
        project_root = self.new_project()
        code, out, _err = self.run_cli("bind", str(project_root), "--json")
        self.assertEqual(code, 0)
        json.loads(out)

        code, _out, _err = self.run_cli(
            "cred",
            "set",
            "mykey",
            "--purpose",
            "contract test",
            "--path",
            str(project_root),
            input_text="s3cr3t-value\n",
        )
        self.assertEqual(code, 0)

        code, out, err = self.run_cli(
            "cred", "get", "mykey", "--path", str(project_root), "--json"
        )
        self.assertEqual(code, errors.EXIT_USAGE)
        body = json.loads(out)  # still exactly one document, per the general contract
        self.assertFalse(body["ok"])
        self.assertEqual(body["exit_code"], errors.EXIT_USAGE)
        self.assertIn("--json", body["error"])
        self.assertNotIn("s3cr3t-value", out)
        self.assertNotIn("s3cr3t-value", err)

        # And the sanctioned path (no --json) still delivers the value and
        # nothing else, so the refusal above is not a regression in disguise.
        code, out, _err = self.run_cli("cred", "get", "mykey", "--path", str(project_root))
        self.assertEqual(code, 0)
        self.assertEqual(out.strip("\n"), "s3cr3t-value")


class CatalogContractTest(StoreTestCase):
    """`devteam catalog` (ADR-0011's read-only browse command behind the app).

    Two behaviours beyond the generic sweep, both from the coordinator's brief:
    it must create nothing in the data store on any path (not even a machine
    identity), and a file with malformed frontmatter must degrade to a flagged
    entry rather than raise.
    """

    def _install_active_version(self):
        code, out, _err = self.run_cli(
            "store", "install", "--from", str(self.source), "--version", "3.0.0", "--json"
        )
        self.assertEqual(code, 0)
        json.loads(out)
        code, out, _err = self.run_cli("store", "use", "3.0.0", "--json")
        self.assertEqual(code, 0)
        json.loads(out)

    def _data_snapshot(self):
        data_dir = paths.data_dir()
        if not data_dir.exists():
            return None
        return sorted(str(p.relative_to(data_dir)) for p in data_dir.rglob("*"))

    def test_catalog_creates_nothing_in_the_data_store(self):
        # `store install`/`store use` themselves touch `data/` (they take the
        # store lock, which mints a machine id and a lock directory) -- that is
        # their own, unrelated side effect. The snapshot is taken AFTER that
        # bootstrap, so what is asserted here is specifically that `catalog`
        # adds nothing on top of it: no bound-project record, no registry
        # entry, no second machine id.
        self._install_active_version()
        cwd = self.tmp / "unbound-cwd"
        cwd.mkdir()

        before = self._data_snapshot()
        self.assertIsNotNone(before, "expected store install/use to have created data/")

        for args in (
            ("catalog", "--json"),
            ("catalog", "agents", "--json"),
            ("catalog", "skills", "--json"),
            ("catalog", "commands", "--json"),
            ("catalog", "show", "no-such-entry", "--json"),
        ):
            with self.subTest(command=" ".join(args)):
                code, out, _err = ContractSweepTest.run_cli_in(cwd, *args)
                self.assertIn(code, VALID_EXIT_CODES)
                if out.strip():
                    json.loads(out)
                after = self._data_snapshot()
                self.assertEqual(
                    before,
                    after,
                    "{} changed the data store: {} -> {}".format(" ".join(args), before, after),
                )

        # The `data/` snapshot above already includes `machine-id` and the
        # machine subtree by name, so a catalog call minting a *second* machine
        # id or otherwise touching that file would already have failed the
        # `assertEqual(before, after, ...)` checks in the loop -- this is the
        # same "creates nothing" claim `registry.load()` documents for reads
        # (`paths.machine_id(create=False)` is that read-only probe), just
        # verified structurally rather than restated here.
        self.assertIsNotNone(paths.machine_id(create=False))

    def test_catalog_is_both_a_leaf_and_a_group(self):
        # `catalog` alone is a valid, meaningful call (unlike `store`/`prefs`/
        # `cred`, which need a subcommand) -- this is exactly the shape
        # `discover_commands` must not collapse into "only a group".
        leaves, groups = discover_commands()
        self.assertIn(("catalog",), leaves, "bare `catalog` should be directly invocable")
        self.assertIn(("catalog",), groups, "`catalog` should also be walked for nested subcommands")
        for sub in ("agents", "skills", "commands", "show"):
            self.assertIn(("catalog", sub), leaves)

    def test_malformed_frontmatter_degrades_instead_of_raising(self):
        # A well-formed sibling proves the degradation is per-file, not
        # per-command: one bad file must not hide the good ones, or the catalog
        # is useless for finding the bad file in the first place.
        (self.source / "agents" / "well-formed-agent.md").write_text(
            "---\nname: well-formed-agent\ndescription: fine\ntier: backend-exec\nmodel: sonnet\n---\nBody.\n",
            encoding="utf-8",
        )
        broken_skill_dir = self.source / "skills" / "testing" / "broken-skill"
        broken_skill_dir.mkdir(parents=True, exist_ok=True)
        (broken_skill_dir / "SKILL.md").write_text(
            "---\nname broken-skill missing its colon\ndescription: bad\n---\nBody.\n",
            encoding="utf-8",
        )
        (self.source / "commands" / "well-formed-command.md").write_text(
            "---\ndescription: fine\n---\nBody.\n", encoding="utf-8"
        )
        (self.source / "commands" / "unterminated.md").write_text(
            "---\ndescription: never closed\nno closing delimiter below\n", encoding="utf-8"
        )

        self.install_version("3.0.0", activate=True)
        cwd = self.tmp / "malformed-cwd"
        cwd.mkdir()

        code, out, _err = ContractSweepTest.run_cli_in(cwd, "catalog", "agents", "--json")
        self.assertEqual(code, 0)
        agents = json.loads(out)["agents"]
        by_name = {entry["name"]: entry for entry in agents}
        # `agents/backend-developer.md` from the shared fixture has no
        # frontmatter at all -- a third, distinct malformed shape alongside the
        # two crafted below (missing colon, unterminated block).
        self.assertTrue(by_name["backend-developer"]["malformed"])
        self.assertEqual(by_name["backend-developer"]["path"], "agents/backend-developer.md")
        self.assertFalse(by_name["well-formed-agent"].get("malformed"))
        self.assertEqual(by_name["well-formed-agent"]["tier"], "backend-exec")

        code, out, _err = ContractSweepTest.run_cli_in(cwd, "catalog", "skills", "--json")
        self.assertEqual(code, 0)
        skills = json.loads(out)["skills"]
        broken = [s for s in skills if s.get("malformed")]
        self.assertTrue(broken, "expected the crafted broken skill to appear, flagged")
        self.assertTrue(any("testing/broken-skill" in s["path"] for s in broken))

        code, out, _err = ContractSweepTest.run_cli_in(cwd, "catalog", "commands", "--json")
        self.assertEqual(code, 0)
        commands = json.loads(out)["commands"]
        by_name = {entry["name"]: entry for entry in commands}
        self.assertTrue(by_name["unterminated"]["malformed"])
        self.assertFalse(by_name["well-formed-command"].get("malformed"))

        # A malformed entry is excluded from `catalog show` lookup by name --
        # it is only reachable through the kind listing that flagged it.
        code, out, _err = ContractSweepTest.run_cli_in(cwd, "catalog", "show", "unterminated", "--json")
        self.assertEqual(code, errors.EXIT_USAGE)
        body = json.loads(out)
        self.assertFalse(body["ok"])

        code, out, _err = ContractSweepTest.run_cli_in(cwd, "catalog", "show", "well-formed-command", "--json")
        self.assertEqual(code, 0)
        shown = json.loads(out)
        self.assertEqual(shown["kind"], "commands")
        self.assertFalse(shown.get("malformed"))


class CompatContractTest(StoreTestCase):
    """`scripts/lib/devteam/compat.py` -- the schema numbers a client reads
    before it writes to the store (ADR-0011: "compatibility is declared, not
    assumed"). Had no coverage before this file.
    """

    def test_store_schemas_reads_from_the_owning_modules_not_a_copy(self):
        # Compared directly against the modules that own each number -- a test
        # that would fail if `compat.py` ever hardcoded one of these instead of
        # importing it, which is the whole point of the module existing.
        expected = {
            "project": project.SCHEMA,
            "project_layout": project.CURRENT_LAYOUT,
            "registry": registry.SCHEMA,
            "bind_manifest": bind_module.MANIFEST_SCHEMA,
            "credentials": creds.SCHEMA,
        }
        self.assertEqual(compat.store_schemas(), expected)
        for value in expected.values():
            self.assertIsInstance(value, int)

    def test_unsupported_by_empty_for_a_client_that_claims_every_current_shape(self):
        current = compat.store_schemas()
        self.assertEqual(compat.unsupported_by(current), {})

    def test_unsupported_by_reports_a_client_one_behind_on_one_shape(self):
        current = compat.store_schemas()
        behind = dict(current)
        one_name = next(iter(behind))
        behind[one_name] = current[one_name] - 1
        result = compat.unsupported_by(behind)
        self.assertEqual(set(result), {one_name})
        self.assertEqual(result[one_name], {"store": current[one_name], "client": current[one_name] - 1})

    def test_unsupported_by_treats_silence_as_unsupported_not_as_compatible(self):
        # A client that says nothing about a shape must NOT be read as claiming
        # support for it -- that is the specific assertion the coordinator called
        # out, and it is the one bug class this test exists to catch: a client
        # silently allowed to write a structure it has never seen.
        current = compat.store_schemas()
        one_name = next(iter(current))
        silent = {name: value for name, value in current.items() if name != one_name}
        result = compat.unsupported_by(silent)
        self.assertIn(one_name, result)
        self.assertEqual(result[one_name], {"store": current[one_name], "client": None})

    def test_unsupported_by_ignores_a_shape_the_store_no_longer_carries(self):
        # An older store is readable by a newer client -- only the reverse
        # direction (store ahead of client) is ever reported.
        current = compat.store_schemas()
        ahead_client = dict(current)
        ahead_client["a_future_shape_this_store_does_not_have"] = 99
        self.assertEqual(compat.unsupported_by(ahead_client), {})

    def test_unsupported_by_rejects_a_non_mapping(self):
        with self.assertRaises(TypeError):
            compat.unsupported_by(["not", "a", "mapping"])

    def test_unsupported_by_treats_a_non_int_claim_as_unsupported(self):
        # A bool is an int subclass in Python -- explicitly excluded so a client
        # that sent `true` is not silently treated as schema version `1`.
        current = compat.store_schemas()
        one_name = next(iter(current))
        client = dict(current)
        client[one_name] = True
        result = compat.unsupported_by(client)
        self.assertIn(one_name, result)

    def test_min_app_version_is_present_and_none(self):
        # Present-but-None, not absent: the first app release must be able to
        # read this field even though no minimum is asserted yet.
        described = compat.describe()
        self.assertIn("min_app_version", described)
        self.assertIsNone(described["min_app_version"])

    def test_version_json_carries_the_compat_block_wired_to_the_same_source(self):
        self.install_version("3.0.0", activate=True)
        code, out, _err = self.run_cli("version", "--json")
        self.assertEqual(code, 0)
        payload = json.loads(out)
        self.assertIn("compat", payload)
        block = payload["compat"]
        self.assertIn("min_app_version", block)
        self.assertIsNone(block["min_app_version"])
        self.assertEqual(block["json_contract"], compat.JSON_CONTRACT_VERSION)
        self.assertEqual(block["store_schemas"], compat.store_schemas())


class AppFacingKeySetContractTest(StoreTestCase):
    """Golden key-set assertions for the commands the desktop app actually reads.

    The rest of this file proves every command emits one well-formed document
    with `ok` -- the envelope. It does NOT prove the document still has the
    fields a client reads: a `software-architect` review of the sweep found
    that dropping `project_id` from `bind --json` would pass every check above.
    ADR-0011 says plainly that "changing an output shape is a breaking change",
    so this class pins the exact top-level key set of the payloads the app-facing
    surface returns, plus the per-record key set for the handful of commands
    whose payload is a list a UI table binds to.

    IMPORTANT: a failure here is not necessarily a bug. It means an app-facing
    JSON shape changed, and somebody has to decide -- per ADR-0011 -- whether
    that is a breaking change the app needs to know about. If this test fails,
    read the diff of added/removed keys, decide whether the change is
    deliberate, and only then update the expected set below. Do not "fix" a
    failure here by blindly copying the new key set in; that defeats the
    entire point of the test.

    Each expected set below is deliberately written out in full, in one place,
    so that updating it is a conscious, reviewable edit -- not a side effect of
    some helper that infers "the fields that happen to be present."
    """

    # Every successful `--json` payload gets `ok` from `Emitter.emit()` -- that
    # part is already covered by the generic sweep above, so it is added
    # automatically by `_assert_exact_keys` rather than repeated in every entry
    # below, keeping each entry about the command's own, command-specific shape.
    EXPECTED = {
        "path": {
            "platform",
            "devteam_home",
            "core",
            "data",
            "cache",
            "versions",
            "current_file",
            "machine_id",
            "machine",
            "registry",
            "global_preferences",
            "credentials",
            "secrets",
            "projects",
        },
        "version": {"current", "installed", "core", "compat"},
        "compat": {
            "json_contract",
            "min_app_version",
            "store_schemas",
            "client_schemas",
            "may_write",
            "unsupported",
        },
        "list": {"current", "projects"},
        "list.record": {
            "project_id",
            "path",
            "providers",
            "mode",
            "pin",
            "resolves_to",
            "path_exists",
        },
        "doctor": {"status", "findings", "actions"},
        "bind": {
            "project_id",
            "path",
            "version",
            "mode",
            "providers",
            "artifacts",
            "retired",
            "merged_project_files",
            "pin",
            "identity_created",
            "pruned",
            "gitignore",
            "git_exclude",
            "fallback_reason",
            "preferences_import",
        },
        "store list": {"installed", "current", "pinned"},
        "catalog": {"version", "project_id", "counts", "malformed"},
        "catalog agents": {"version", "project_id", "agents", "count"},
        "catalog agents.record": {"name", "tier", "model", "description", "path", "version"},
        "catalog skills": {"version", "project_id", "skills", "count"},
        "catalog skills.record": {"name", "description", "category", "path", "version"},
        "catalog commands": {"version", "project_id", "commands", "count"},
        "catalog commands.record": {"name", "description", "path", "version"},
        "catalog show <name>": {
            "name",
            "tier",
            "model",
            "description",
            "path",
            "version",
            "kind",
            "body",
            "project_id",
        },
        # `doctor` findings (`doctor._finding()`): `hint` is added to the dict only
        # when truthy, so it is an OPTIONAL key, not a fourth required one -- a
        # finding with no hint has exactly the required set, one with a hint has
        # required | {"hint"}, and nothing else is ever legal either way.
        "doctor.finding.required": {"level", "category", "message"},
        "doctor.finding.optional": {"hint"},
        # `catalog`'s `counts` and `malformed` maps share this shape -- both are
        # `{agents, skills, commands}` per `cli.py`'s catalog handler.
        "catalog.counts": {"agents", "skills", "commands"},
        "catalog.malformed": {"agents", "skills", "commands"},
        # A malformed catalog entry (`catalog._malformed_entry`-style construction):
        # the well-formed fields (`tier`/`model`/`description` for agents,
        # `description` for commands) are NOT carried over -- only `name`, `path`
        # and `version` survive, plus `malformed` and `error`. Verified against the
        # actual payload for `agents/backend-developer.md` and `commands/plan.md`,
        # both deliberately frontmatter-less in the shared fixture.
        "catalog agents.malformed.record": {"name", "path", "version", "malformed", "error"},
        "catalog commands.malformed.record": {"name", "path", "version", "malformed", "error"},
        # `compat.unsupported_by()` return value, per shape name.
        "compat.unsupported.record": {"store", "client"},
        "prefs list": {"project_id", "version", "values", "origin", "unknown"},
        "cred list": {"project_id", "credentials", "count"},
        "cred list.record": {"key", "purpose", "source", "ref", "scope", "layer"},
        "cred backends": {"available", "default", "probed"},
        # `problems` is unconditional. This pin caught it appearing only on the
        # findings branch, which made the payload's shape depend on the data — a
        # client doing `payload.problems.length` would have worked until the day
        # everything was fine. The source was changed to always emit it (empty list
        # included); `main()`'s exit-1 check is truthiness-based, so `[]` still
        # means success. The shape change was the deliberate fix, not this pin.
        "cred check": {"project_id", "findings", "problems"},
    }

    # A key whose name alone suggests it might carry an actual secret value,
    # rather than a reference to one. `cred list` is the one command where this
    # matters in practice -- `creds._public_view` builds its dict field-by-field
    # precisely so a value can never leak through it by accident -- but the
    # check is run against every payload in this class for good measure.
    _SECRET_LIKE_KEYS = {"value", "secret", "password", "token"}

    def _assert_exact_keys(self, label, payload, expected_fields):
        expected = set(expected_fields) | {"ok"}
        actual = set(payload)
        if actual == expected:
            return
        added = sorted(actual - expected)
        removed = sorted(expected - actual)
        self.fail(
            "{}: app-facing payload shape changed.\n"
            "  added:   {}\n"
            "  removed: {}\n"
            "This is not automatically a bug -- per ADR-0011, changing an "
            "output shape is a breaking change. Decide whether this change is "
            "deliberate and, if so, update AppFacingKeySetContractTest.EXPECTED "
            "to match; do not treat this failure as something to silence.".format(
                label, added or "(none)", removed or "(none)"
            )
        )

    def _assert_record_keys(self, label, record, expected_fields):
        expected = set(expected_fields)
        actual = set(record)
        if actual == expected:
            return
        added = sorted(actual - expected)
        removed = sorted(expected - actual)
        self.fail(
            "{}: record shape changed.\n"
            "  added:   {}\n"
            "  removed: {}\n"
            "This is not automatically a bug -- see AppFacingKeySetContractTest's "
            "class docstring.".format(label, added or "(none)", removed or "(none)")
        )

    def _assert_finding_keys(self, label, finding):
        """A doctor finding's `hint` key is present only when truthy (see
        `doctor._finding()`), so this is not a plain exact-keys check: a finding
        must carry exactly the required set, optionally plus `hint`, and nothing
        else -- a required key vanishing and an optional key being absent must
        produce two different failures, not the same one.
        """
        required = self.EXPECTED["doctor.finding.required"]
        optional = self.EXPECTED["doctor.finding.optional"]
        actual = set(finding)
        missing_required = required - actual
        unexpected = actual - required - optional
        # `_finding()` only ever sets `hint` when it is truthy -- a present-but-falsy
        # `hint` (None, "", ...) would mean the source stopped honouring that
        # contract, which a plain key-set check would miss entirely.
        falsy_hint = "hint" in finding and not finding["hint"]
        if not missing_required and not unexpected and not falsy_hint:
            return
        self.fail(
            "{}: finding shape changed.\n"
            "  missing required: {}\n"
            "  unexpected keys:  {}\n"
            "  falsy hint present: {}\n"
            "This is not automatically a bug -- see AppFacingKeySetContractTest's "
            "class docstring.".format(
                label,
                sorted(missing_required) or "(none)",
                sorted(unexpected) or "(none)",
                falsy_hint,
            )
        )

    def _assert_no_secret_like_keys(self, label, payload):
        leaked = sorted(
            key for key in payload if key.lower() in self._SECRET_LIKE_KEYS
        )
        self.assertFalse(
            leaked,
            "{}: payload carries a key whose name suggests a secret value: {} "
            "-- app-facing payloads must carry references, never values "
            "(see `creds._public_view`)".format(label, leaked),
        )

    def setUp(self):
        super().setUp()
        # A well-formed agent and command, added to the fixture source tree the
        # same way `test_malformed_frontmatter_degrades_instead_of_raising`
        # does above -- the default fixture's `agents/backend-developer.md` and
        # `commands/plan.md` are deliberately frontmatter-less (malformed), so a
        # clean record for those two kinds needs its own file. The default
        # `skills/shared/project-context/SKILL.md` fixture is already
        # well-formed and is reused as-is for the skills record.
        (self.source / "agents" / "sample-agent.md").write_text(
            "---\nname: sample-agent\ndescription: a sample agent\ntier: backend-exec\n"
            "model: sonnet\n---\nBody.\n",
            encoding="utf-8",
        )
        (self.source / "commands" / "sample-command.md").write_text(
            "---\ndescription: a sample command\n---\nBody.\n", encoding="utf-8"
        )
        self.install_version("3.0.0", activate=True)
        self.project_root = self.new_project()
        code, out, err = self.run_cli("bind", str(self.project_root), "--json")
        self.assertEqual(code, 0, "fixture bind failed: {}".format(err))
        self.bind_payload = json.loads(out)

    def _run_ok(self, *args):
        code, out, err = self.run_cli(*args)
        self.assertEqual(code, 0, "{}: expected success, got {}: {}".format(" ".join(args), code, err))
        payload = json.loads(out)
        self.assertTrue(payload.get("ok"), "{}: ok was not True: {}".format(" ".join(args), payload))
        return payload

    def test_path(self):
        payload = self._run_ok("path", "--json")
        self._assert_exact_keys("path", payload, self.EXPECTED["path"])

    def test_version(self):
        payload = self._run_ok("version", "--json")
        self._assert_exact_keys("version", payload, self.EXPECTED["version"])

    def test_compat(self):
        # Bare `devteam compat --json`, no `--client`: `may_write` stays `None`
        # (nothing was asked), which is also what keeps `ok` True here.
        payload = self._run_ok("compat", "--json")
        self._assert_exact_keys("compat", payload, self.EXPECTED["compat"])

    def test_compat_unsupported_record(self):
        # A client one behind on one shape (mirrors
        # `CompatContractTest.test_unsupported_by_reports_a_client_one_behind_on_one_shape`)
        # so `unsupported` is actually populated instead of the empty-dict case
        # `test_compat` above exercises. `--client` makes `ok` False and exits 1
        # -- a different top-level shape (it gains `client_schemas`) that is not
        # what this test is pinning, so it goes through `run_cli` directly
        # rather than `_run_ok`/`_assert_exact_keys`.
        current = compat.store_schemas()
        one_name = next(iter(current))
        behind = dict(current)
        behind[one_name] = current[one_name] - 1
        code, out, err = self.run_cli("compat", "--json", "--client", json.dumps(behind))
        self.assertEqual(code, 1, "expected a behind client to fail compat: {}".format(err))
        payload = json.loads(out)
        self.assertIn(one_name, payload["unsupported"])
        self._assert_record_keys(
            "compat.unsupported.record",
            payload["unsupported"][one_name],
            self.EXPECTED["compat.unsupported.record"],
        )

    def test_list(self):
        payload = self._run_ok("list", "--json")
        self._assert_exact_keys("list", payload, self.EXPECTED["list"])
        self.assertTrue(payload["projects"], "expected the fixture-bound project to be listed")
        self._assert_record_keys(
            "list.record", payload["projects"][0], self.EXPECTED["list.record"]
        )

    def test_doctor(self):
        payload = self._run_ok("doctor", str(self.project_root), "--json")
        self._assert_exact_keys("doctor", payload, self.EXPECTED["doctor"])
        self.assertTrue(payload["findings"], "expected the bound fixture to produce at least one finding")
        for finding in payload["findings"]:
            self._assert_finding_keys("doctor.finding", finding)

        # The fixture bound project is clean, so none of its findings carry a
        # `hint` -- the optional key needs a scenario that actually exercises it.
        # An unbound directory produces a WARN with a hint (`doctor.check_project`:
        # "... is not a bound project" / "Run `devteam bind`."), which both proves
        # `hint` is accepted when present and confirms it is genuinely optional
        # rather than always-absent-in-practice.
        unbound_dir = self.tmp / "doctor-unbound-dir"
        unbound_dir.mkdir()
        code, out, err = self.run_cli("doctor", str(unbound_dir), "--json")
        unbound_payload = json.loads(out)
        self.assertEqual(unbound_payload.get("ok"), False, "an unbound dir should not report ok")
        with_hint = [f for f in unbound_payload["findings"] if "hint" in f]
        self.assertTrue(with_hint, "expected the unbound-project finding to carry a hint")
        for finding in with_hint:
            self._assert_finding_keys("doctor.finding (with hint)", finding)
            self.assertEqual(set(finding), self.EXPECTED["doctor.finding.required"] | {"hint"})

    def test_bind(self):
        # Reuse the bind already performed in setUp rather than binding again --
        # bind is written to be idempotent, but the golden assertion only needs
        # one successful payload, not a second invocation.
        self.assertTrue(self.bind_payload.get("ok", True) is not False)
        self._assert_exact_keys("bind", self.bind_payload, self.EXPECTED["bind"])

    def test_store_list(self):
        payload = self._run_ok("store", "list", "--json")
        self._assert_exact_keys("store list", payload, self.EXPECTED["store list"])

    def test_catalog(self):
        payload = self._run_ok("catalog", "--path", str(self.project_root), "--json")
        self._assert_exact_keys("catalog", payload, self.EXPECTED["catalog"])
        self._assert_record_keys("catalog.counts", payload["counts"], self.EXPECTED["catalog.counts"])
        self._assert_record_keys("catalog.malformed", payload["malformed"], self.EXPECTED["catalog.malformed"])

    def test_catalog_agents(self):
        payload = self._run_ok(
            "catalog", "agents", "--path", str(self.project_root), "--json"
        )
        self._assert_exact_keys("catalog agents", payload, self.EXPECTED["catalog agents"])
        by_name = {entry["name"]: entry for entry in payload["agents"]}
        self.assertIn("sample-agent", by_name, "expected the well-formed fixture agent")
        self._assert_record_keys(
            "catalog agents.record", by_name["sample-agent"], self.EXPECTED["catalog agents.record"]
        )
        # `agents/backend-developer.md` is deliberately frontmatter-less in the
        # shared fixture (see setUp's comment) -- it is the malformed entry this
        # command must also produce, with the smaller, distinct record shape.
        self.assertIn("backend-developer", by_name, "expected the malformed fixture agent")
        self.assertTrue(by_name["backend-developer"]["malformed"])
        self._assert_record_keys(
            "catalog agents.malformed.record",
            by_name["backend-developer"],
            self.EXPECTED["catalog agents.malformed.record"],
        )

    def test_catalog_skills(self):
        payload = self._run_ok(
            "catalog", "skills", "--path", str(self.project_root), "--json"
        )
        self._assert_exact_keys("catalog skills", payload, self.EXPECTED["catalog skills"])
        by_name = {entry["name"]: entry for entry in payload["skills"]}
        self.assertIn("project-context", by_name, "expected the well-formed fixture skill")
        self._assert_record_keys(
            "catalog skills.record", by_name["project-context"], self.EXPECTED["catalog skills.record"]
        )

    def test_catalog_commands(self):
        payload = self._run_ok(
            "catalog", "commands", "--path", str(self.project_root), "--json"
        )
        self._assert_exact_keys("catalog commands", payload, self.EXPECTED["catalog commands"])
        by_name = {entry["name"]: entry for entry in payload["commands"]}
        self.assertIn("sample-command", by_name, "expected the well-formed fixture command")
        self._assert_record_keys(
            "catalog commands.record",
            by_name["sample-command"],
            self.EXPECTED["catalog commands.record"],
        )
        # `commands/plan.md` is deliberately frontmatter-less in the shared
        # fixture (see setUp's comment) -- the malformed counterpart entry.
        self.assertIn("plan", by_name, "expected the malformed fixture command")
        self.assertTrue(by_name["plan"]["malformed"])
        self._assert_record_keys(
            "catalog commands.malformed.record",
            by_name["plan"],
            self.EXPECTED["catalog commands.malformed.record"],
        )

    def test_catalog_show(self):
        payload = self._run_ok(
            "catalog", "show", "sample-agent", "--path", str(self.project_root), "--json"
        )
        self._assert_exact_keys("catalog show <name>", payload, self.EXPECTED["catalog show <name>"])
        self.assertEqual(payload["kind"], "agents")

    def test_prefs_list(self):
        payload = self._run_ok("prefs", "list", "--path", str(self.project_root), "--json")
        self._assert_exact_keys("prefs list", payload, self.EXPECTED["prefs list"])

    def test_cred_list(self):
        # A clean credential, declared through the sanctioned path (value on
        # stdin, never argv) so `cred list` has a real record to pin, not just
        # the empty-list shape.
        code, _out, err = self.run_cli(
            "cred",
            "set",
            "sample-key",
            "--purpose",
            "key-set contract test",
            "--path",
            str(self.project_root),
            input_text="s3cr3t-value\n",
        )
        self.assertEqual(code, 0, "fixture cred set failed: {}".format(err))

        payload = self._run_ok("cred", "list", "--path", str(self.project_root), "--json")
        self._assert_exact_keys("cred list", payload, self.EXPECTED["cred list"])
        self._assert_no_secret_like_keys("cred list", payload)
        self.assertEqual(payload["count"], 1)
        record = payload["credentials"][0]
        self._assert_record_keys("cred list.record", record, self.EXPECTED["cred list.record"])
        self._assert_no_secret_like_keys("cred list.record", record)
        # Belt and suspenders: the value itself must not appear anywhere in the
        # serialized payload, not just be absent from the key names.
        self.assertNotIn("s3cr3t-value", json.dumps(payload))

    def test_cred_backends(self):
        # Unlike every other `cred` subcommand, `backends` takes no `--path` --
        # it describes the machine's available secret stores, not a project
        # (see `cli.py`: it is wired with the bare `leaf()` helper, not
        # `cred_leaf()`, and its handler calls only `secrets_module.describe()`).
        payload = self._run_ok("cred", "backends", "--json")
        self._assert_exact_keys("cred backends", payload, self.EXPECTED["cred backends"])

    def test_cred_check(self):
        # No credential declared in this test's own store, so `findings` is
        # deterministically empty. The shape is asserted to be the SAME either way:
        # `problems` used to appear only on the non-empty branch, and this pin is what
        # surfaced it. Both states are checked, because "the shape does not depend on
        # the data" is the property worth holding and one state cannot show it.
        empty = self._run_ok("cred", "check", "--path", str(self.project_root), "--json")
        self._assert_exact_keys("cred check", empty, self.EXPECTED["cred check"])
        self.assertEqual(empty["problems"], [])

        # Declare a credential on the last-resort backend, which `creds.check` reports
        # as `insecure-backend`, so the populated branch is exercised too. In-process is
        # fine here: the fixture already points `$DEVTEAM_HOME` at this test's store.
        creds.set_entry(
            "shape.probe",
            "exercise the populated branch",
            project_id=self.bind_payload["project_id"],
            value="irrelevant",
            backend="insecure",
        )
        # Exit 1 is correct now — findings are exactly what "ran and reported a problem
        # it did not fix" means — so this cannot go through `_run_ok`.
        code, out, err = self.run_cli("cred", "check", "--path", str(self.project_root), "--json")
        self.assertEqual(code, 1, "expected findings to exit 1, got {}: {}".format(code, err))
        populated = json.loads(out)
        self._assert_exact_keys("cred check", populated, self.EXPECTED["cred check"])
        self.assertTrue(populated["problems"])


if __name__ == "__main__":
    unittest.main()
