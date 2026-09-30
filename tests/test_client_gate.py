"""The client write gate: a caller that declares what it understands is held to it.

`devteam compat --client` already *answered* "may this client write?" — but nothing made
the answer binding, which is the gap `docs/specs/v4-app-and-distribution.md` records:

    the app must still call `devteam compat` before it writes, because a user can
    upgrade the store from a terminal without touching the app, and **nothing on the
    framework side refuses a client that never asks**

The seam built for it is `--client-schemas <path>` / `DEVTEAM_CLIENT_SCHEMAS`, and the
property this file exists to hold is a pair, not a single behaviour:

1. a caller that **declares** is refused every mutating command it cannot understand,
   before anything on disk changes, and
2. a caller that **declares nothing** behaves exactly as it does today — because an
   anonymous invocation is indistinguishable from a human at a terminal, and the human's
   CLI is the one thing this gate may not touch.

The second is the assertion that matters most and the easiest to break silently, so it
is checked both ways round: the same command, in the same store, refused when declared
and performed when not.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import unittest

from devteam_support import CLI, StoreTestCase, make_git_project

# The parser walk is imported, not re-written. `tests/test_json_contract.py` already
# owns an *asserted* discovery walk (a broken walk that silently finds nothing fails its
# own tests there); a second copy here would be free to go stale in the direction that
# reports full coverage of a classification that is missing a command.
from test_json_contract import discover_commands

from devteam import compat, errors, paths, project, store


class ClientGateTestCase(StoreTestCase):
    """Shared fixtures: an installed store, and declaration files to point at."""

    def setUp(self):
        # `StoreTestCase.setUp` neutralises CLIENT_SCHEMAS_ENV along with the other
        # seams, so this file does not clear it a second time: a value inherited from
        # the developer's shell is already gone by the time this runs. Tests here set
        # the variable deliberately, via `run_cli(env=...)`.
        super().setUp()
        self.install_version("3.0.0", activate=True)

    # ── declaration files ────────────────────────────────────────────────────

    def write_declaration(self, name, schemas):
        path = self.tmp / name
        path.write_text(json.dumps(schemas), encoding="utf-8")
        return path

    def compatible(self, name="compatible.json"):
        """Everything the store carries, at the store's own numbers."""
        return self.write_declaration(name, compat.store_schemas())

    def one_behind(self, name="behind.json"):
        """Every shape declared, every one a version behind — so a refusal message has
        two real integers to print for each, which `client=(not declared)` would hide."""
        return self.write_declaration(
            name, {key: value - 1 for key, value in compat.store_schemas().items()}
        )

    def silent_about_one(self, name="silent.json"):
        """Current numbers for every shape except one, which is simply absent."""
        schemas = compat.store_schemas()
        self.omitted_shape = sorted(schemas)[0]
        return self.write_declaration(
            name, {k: v for k, v in schemas.items() if k != self.omitted_shape}
        )

    # ── invocation ───────────────────────────────────────────────────────────

    def run_in(self, cwd, *args, env_extra=None, timeout=None):
        """Run the real entry point in an explicit cwd, with stdin an empty pipe.

        `cwd` is explicit because `bind`, `sync`, `pin`, `migrate`, `upgrade` and
        `doctor` default an omitted path to the process's directory — inheriting the test
        runner's would point them at this repository.

        stdin is an empty pipe, never inherited: `cred set` reads its value from stdin
        and prompts without echo when stdin is a tty, so a gate that failed to refuse it
        would hang the suite on a password prompt instead of failing.

        `timeout` is `None` by default (no change for any existing caller). A test that
        deliberately points the CLI at something that can block forever — a FIFO with no
        writer — passes one explicitly, so a regression fails fast with
        `subprocess.TimeoutExpired` instead of hanging the whole suite.
        """
        env = dict(os.environ)
        env.update(env_extra or {})
        result = subprocess.run(
            [sys.executable, str(CLI), *args],
            cwd=str(cwd),
            input=b"",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            check=False,
            timeout=timeout,
        )
        return (
            result.returncode,
            result.stdout.decode("utf-8", "replace"),
            result.stderr.decode("utf-8", "replace"),
        )

    def fresh_dir(self, label="cwd"):
        self._counter = getattr(self, "_counter", 0) + 1
        path = self.tmp / "{}-{}".format(label, self._counter)
        path.mkdir()
        return path

    def fresh_project(self):
        self._counter = getattr(self, "_counter", 0) + 1
        return make_git_project(self.tmp / "proj-{}".format(self._counter), name="app")

    # ── snapshots ────────────────────────────────────────────────────────────

    @staticmethod
    def snapshot(root):
        """Every path under `root`, with a content digest — a refusal must not change it.

        Digests, not just names: a gate that refused *after* rewriting the registry or
        appending an audit line would leave the path set identical and be invisible to a
        listing. Symlinks are recorded by target without being followed, so a dangling
        one is a difference rather than a crash.
        """
        if not root.exists():
            return {}
        state = {}
        for path in sorted(root.rglob("*")):
            key = str(path.relative_to(root))
            if path.is_symlink():
                state[key] = "symlink -> {}".format(os.readlink(str(path)))
            elif path.is_dir():
                state[key] = "dir"
            else:
                state[key] = hashlib.sha256(path.read_bytes()).hexdigest()
        return state


class ClassificationCompletenessTest(unittest.TestCase):
    """Every command the parser can reach is classified — no silent default.

    `tests/test_json_contract.py` refuses a hardcoded command list because such a list
    goes stale the moment a command is added, and the first thing to notice would be a
    client in production. A *classification* keyed by hand has the same failure mode with
    a worse consequence: an unclassified command is one the gate has no stated opinion
    about. `compat.is_mutating` fails closed for exactly that reason, but failing closed
    is a safety net, not a substitute for deciding — so the table is checked against the
    real parser here.

    Building a parser touches no filesystem, so no store isolation is needed.
    """

    def test_every_invocable_leaf_is_classified(self):
        leaves, _groups = discover_commands()
        unclassified = sorted(leaf for leaf in leaves if compat.classify(leaf) is None)
        self.assertFalse(
            unclassified,
            "these commands exist in cli.build_parser() but appear in neither "
            "compat.MUTATING nor compat.READ_ONLY: {}. Add each one to the table that "
            "fits, with the reason beside it. Until then the gate treats it as mutating "
            "(compat.is_mutating fails closed), which is safe but undecided.".format(
                [" ".join(leaf) for leaf in unclassified]
            ),
        )

    def test_the_tables_do_not_disagree_with_each_other(self):
        overlap = sorted(set(compat.MUTATING) & set(compat.READ_ONLY))
        self.assertFalse(
            overlap,
            "classified twice, so `classify` answers by table order rather than by "
            "decision: {}".format([" ".join(path) for path in overlap]),
        )

    def test_no_table_entry_names_a_command_that_does_not_exist(self):
        # A stale entry is how a *renamed* command silently loses its classification:
        # the old tuple keeps the table looking complete while the new name falls
        # through to the fail-closed default. `test_every_invocable_leaf_is_classified`
        # would catch the new name; this catches the corpse it left behind, and names it.
        leaves, _groups = discover_commands()
        known = set(leaves)
        stale = sorted((set(compat.MUTATING) | set(compat.READ_ONLY)) - known)
        self.assertFalse(
            stale,
            "classified but not reachable from cli.build_parser() — renamed or removed? "
            "{}".format([" ".join(path) for path in stale]),
        )

    def test_an_unclassified_command_is_treated_as_mutating(self):
        # The fail-closed default itself, asserted rather than assumed: the omission a
        # contributor is most likely to make must not be the one that opens the gate.
        self.assertTrue(compat.is_mutating(("a-command-nobody-classified",)))
        self.assertIsNone(compat.classify(("a-command-nobody-classified",)))

    def test_compat_and_the_read_paths_are_not_gated(self):
        # Named individually because they are the ones that must keep working for a
        # client that has fallen behind: ADR-0011's rule is that such a client degrades
        # to read-only, so gating a read would be the opposite of the decision. `compat`
        # in particular is the command that explains the refusal.
        for path in (("compat",), ("version",), ("catalog",), ("cred", "get"), ("list",)):
            with self.subTest(command=" ".join(path)):
                self.assertFalse(compat.is_mutating(path), " ".join(path))


class IncompatibleDeclarationRefusesEveryMutatingCommandTest(ClientGateTestCase):
    """Driven from the classification, not from a list typed here.

    A mutating command added tomorrow is covered the moment it is classified — which
    `ClassificationCompletenessTest` forces — instead of waiting for someone to remember
    this file.
    """

    def probe_args(self):
        """Arguments that only make the parse succeed, so the *gate* is what is tested.

        argparse runs before the gate, so a command invoked without its required
        arguments fails at exit 2 and proves nothing about the refusal. These supply the
        minimum.

        Two entries are chosen so that a **broken** gate does something harmless instead
        of something destructive, because this sweep deliberately covers the two commands
        `tests/test_json_contract.py` refuses to invoke at all:
          - `update --ref not-a-version` fails ref validation before the first network
            call, so a gate that let it through cannot reach out to the network.
          - `uninstall --purge` (no `--yes`) is refused by the command itself before
            anything is removed, so a gate that let it through cannot delete this
            store.
        Excluding the two most destructive commands would leave the gate unproven exactly
        where it matters most.

        A new mutating command with required arguments and no entry here fails with exit
        2 instead of 4, and the assertion below says which command needs an entry.
        """
        return {
            ("store", "install"): ("--from", str(self.source)),
            ("store", "use"): ("3.0.0",),
            ("prefs", "set"): ("language", "en"),
            ("prefs", "unset"): ("language",),
            ("tasks", "mark"): ("--state", "idle"),
            ("plugin", "enable"): ("probe",),
            ("plugin", "disable"): ("probe",),
            ("plugin", "config", "set"): ("probe", "key", "value"),
            ("plugin", "config", "unset"): ("probe", "key"),
            ("plugin", "run"): ("probe", "action"),
            ("cred", "set"): ("probe-key", "--purpose", "gate probe"),
            ("cred", "unset"): ("probe-key",),
            ("cred", "import"): (str(self.tmp / "no-such-credentials.local.json"),),
            ("import",): (str(self.tmp / "no-such-archive.tar.gz"),),
            ("update",): ("--ref", "not-a-version"),
            ("uninstall",): ("--purge",),
            # A source that does not exist and a name nothing has: a gate that let either
            # through fails validation instead of touching the (pinned) user home.
            ("skills", "install"): ("--source", str(self.tmp / "no-such-skill")),
            ("skills", "remove"): ("no-such-skill",),
        }

    def _sweep(self, seam, declaration):
        """Every mutating command, refused through one declaration seam, changing nothing.

        Parametrised by seam because the two are separate code paths in
        `compat.client_declaration` and only the flag was swept: the environment variable
        was asserted to gate `bind` alone. A variable is the seam a client actually uses —
        exporting once is the whole reason it exists — so it is the one where a gap would
        be in production, and `PrecedenceTest` proving precedence on one command does not
        prove the variable reaches the gate on the other eighteen.
        """
        extra = self.probe_args()
        mutating = sorted(path for path in compat.MUTATING)
        self.assertTrue(mutating, "the classification is empty — nothing was swept")

        for path in mutating:
            label = " ".join(path)
            with self.subTest(seam=seam, command=label):
                before = self.snapshot(self.home)
                args = [*path, *extra.get(path, ())]
                env_extra = None
                if seam == "--client-schemas":
                    args += ["--client-schemas", str(declaration)]
                else:
                    env_extra = {compat.CLIENT_SCHEMAS_ENV: str(declaration)}
                code, out, err = self.run_in(
                    self.fresh_project(), *args, env_extra=env_extra
                )
                self.assertEqual(
                    code,
                    errors.EXIT_CONFLICT,
                    "{} via {}: expected the gate to refuse with exit {}, got {}. If this "
                    "command takes required arguments, add them to probe_args() — a "
                    "usage error at exit 2 never reaches the gate.\nstdout: {}\nstderr: "
                    "{}".format(label, seam, errors.EXIT_CONFLICT, code, out[:400], err[:400]),
                )
                self.assertIn(label, err, "{}: the refusal does not name the command".format(label))
                self.assertIn(
                    seam, err, "{}: the refusal does not name the seam".format(label)
                )
                self.assertEqual(
                    before,
                    self.snapshot(self.home),
                    "{}: the store changed although the command was refused".format(label),
                )

    def test_every_mutating_command_is_refused_and_changes_nothing(self):
        self._sweep("--client-schemas", self.one_behind())

    def test_every_mutating_command_is_refused_through_the_environment_variable_too(self):
        self._sweep(compat.CLIENT_SCHEMAS_ENV, self.one_behind("behind-env.json"))

    def test_the_refusal_names_every_blocking_shape_with_both_numbers(self):
        declaration = self.one_behind()
        code, _out, err = self.run_in(
            self.fresh_project(), "bind", "--client-schemas", str(declaration)
        )
        self.assertEqual(code, errors.EXIT_CONFLICT)
        for name, store_version in compat.store_schemas().items():
            # Both numbers, per shape: a message that says only "incompatible" leaves
            # the client's author guessing which number to move.
            self.assertIn(
                "{} (store={}, client={})".format(name, store_version, store_version - 1),
                err,
                "the refusal does not report {} with both numbers".format(name),
            )

    def test_silence_about_a_shape_is_unsupported_and_the_gate_does_not_re_derive_it(self):
        # `compat.unsupported_by` already rules that a shape the client never mentions is
        # unsupported. What is asserted here is that the gate *delegates* to it: the
        # refusal's `details.unsupported` is compared against the value computed
        # in-process from the same declaration. A second implementation at the call site
        # would be free to drift on exactly this case — the one where a client writes a
        # structure it has never seen.
        declaration = self.silent_about_one()
        code, out, _err = self.run_in(
            self.fresh_project(), "bind", "--client-schemas", str(declaration), "--json"
        )
        self.assertEqual(code, errors.EXIT_CONFLICT)
        body = json.loads(out)
        expected = compat.unsupported_by(json.loads(declaration.read_text(encoding="utf-8")))
        self.assertEqual(body["details"]["unsupported"], expected)
        self.assertEqual(set(expected), {self.omitted_shape})
        self.assertIsNone(expected[self.omitted_shape]["client"])
        self.assertFalse(body["details"]["may_write"])


class NoDeclarationIsUnchangedTest(ClientGateTestCase):
    """The human's CLI. Nothing here may differ from before the gate existed."""

    def test_a_mutating_command_with_no_declaration_still_mutates(self):
        # The pair that makes the point: the SAME command, in the SAME store, refused
        # when the caller declares an incompatible client and performed when it declares
        # nothing. If the gate ever starts refusing anonymous callers, this fails.
        declaration = self.one_behind()

        refused_project = self.fresh_project()
        code, _out, _err = self.run_in(
            refused_project, "bind", "--client-schemas", str(declaration)
        )
        self.assertEqual(code, errors.EXIT_CONFLICT)
        self.assertFalse((refused_project / ".dev-team-agents" / "project.json").exists())

        anonymous_project = self.fresh_project()
        code, out, err = self.run_in(anonymous_project, "bind", "--json")
        self.assertEqual(code, 0, "anonymous bind failed: {}".format(err))
        payload = json.loads(out)
        self.assertTrue(payload["ok"])
        self.assertTrue((anonymous_project / ".dev-team-agents" / "project.json").exists())
        # The gate must not have leaked a field into the payload: ADR-0011 makes an
        # output shape change a breaking change, and `tests/test_json_contract.py` pins
        # bind's exact key set — this says the same thing at the point of the change.
        self.assertNotIn("client_schemas", payload)
        self.assertNotIn("unsupported", payload)

    def test_a_read_only_command_answers_identically_declared_or_not(self):
        # `path --json` is pure: same store, same output, byte for byte. Asserting the
        # three cases are identical is what catches the gate emitting a warning, a note
        # or an extra key on the read path — where ADR-0011 says an incompatible client
        # must keep working.
        cwd = self.fresh_dir()
        anonymous = self.run_in(cwd, "path", "--json")
        with_compatible = self.run_in(
            cwd, "path", "--json", "--client-schemas", str(self.compatible())
        )
        with_incompatible = self.run_in(
            cwd, "path", "--json", "--client-schemas", str(self.one_behind())
        )
        self.assertEqual(anonymous, with_compatible)
        self.assertEqual(anonymous, with_incompatible)
        self.assertEqual(anonymous[0], 0)

    def test_a_behind_client_can_still_read_a_credential(self):
        # "Degrade to read-only" has to mean read-only *works*. `cred get` is the read
        # that was the closest judgment call in the classification (it appends an audit
        # line), so it is the one asserted end to end: a client a version behind still
        # gets the value.
        project_root = self.fresh_project()
        code, _out, err = self.run_in(project_root, "bind", "--json")
        self.assertEqual(code, 0, err)

        result = subprocess.run(
            [sys.executable, str(CLI), "cred", "set", "gate-key", "--purpose", "gate test"],
            cwd=str(project_root),
            input=b"s3cr3t-value\n",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=dict(os.environ),
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr.decode())

        code, out, err = self.run_in(
            project_root, "cred", "get", "gate-key", "--client-schemas", str(self.one_behind())
        )
        self.assertEqual(code, 0, "a behind client was denied a read: {}".format(err))
        self.assertEqual(out.strip("\n"), "s3cr3t-value")

    def test_cred_get_still_refuses_json_under_an_incompatible_declaration(self):
        # `cred get`'s `--json` refusal is a documented exception to the contract
        # (ADR-0010: a secret must not travel inside a document a caller pipes or logs).
        # Classifying it read-only is what keeps that refusal the answer a client gets;
        # a gate that refused first would replace a documented exit 2 with an exit 4 and
        # send every client looking in the wrong place.
        project_root = self.fresh_project()
        code, _out, err = self.run_in(project_root, "bind", "--json")
        self.assertEqual(code, 0, err)
        code, out, _err = self.run_in(
            project_root,
            "cred",
            "get",
            "any-key",
            "--json",
            "--client-schemas",
            str(self.one_behind()),
        )
        self.assertEqual(code, errors.EXIT_USAGE)
        body = json.loads(out)
        self.assertIn("--json", body["error"])

    def test_an_empty_environment_variable_is_not_a_declaration(self):
        # `export DEVTEAM_CLIENT_SCHEMAS=` is a shell saying "no value". Reading it as an
        # empty declaration would refuse every write in that session — silence about
        # every shape is unsupported — with a message naming a file called "". A wrapper
        # that unsets by assigning empty must land on the anonymous path.
        project_root = self.fresh_project()
        code, _out, err = self.run_in(
            project_root, "bind", "--json", env_extra={compat.CLIENT_SCHEMAS_ENV: ""}
        )
        self.assertEqual(code, 0, err)
        self.assertTrue((project_root / ".dev-team-agents" / "project.json").exists())


class CompatibleDeclarationPassesTest(ClientGateTestCase):
    def test_a_declared_compatible_client_performs_the_mutation(self):
        project_root = self.fresh_project()
        code, out, err = self.run_in(
            project_root, "bind", "--json", "--client-schemas", str(self.compatible())
        )
        self.assertEqual(code, 0, "a compatible client was refused: {}".format(err))
        payload = json.loads(out)
        self.assertTrue(payload["ok"])
        # The mutation actually happened — a gate that "passed" by turning the command
        # into a no-op would satisfy an exit-code-only assertion.
        self.assertTrue((project_root / ".dev-team-agents" / "project.json").exists())
        self.assertEqual(
            json.loads((project_root / ".dev-team-agents" / "project.json").read_text())[
                "project_id"
            ],
            payload["project_id"],
        )

    def test_a_client_ahead_of_the_store_is_not_refused(self):
        # An older store read by a newer client is the direction that works
        # (`unsupported_by` ignores it). Asserted through the gate so the two cannot
        # disagree: over-blocking here would make every client upgrade break every write
        # until the store caught up.
        #
        # The shape to bump is picked from the REAL schema names, before the synthetic
        # one is added. Choosing it afterwards made this test vacuous: `a_future_shape`
        # sorts first, so `sorted(schemas)[0]` selected the synthetic key and the `+= 5`
        # never landed on a shape the store actually carries — nothing was ahead, and the
        # over-blocking mutation this test exists to catch (`claimed != store_version` in
        # `unsupported_by`) passed it untouched.
        store_schemas = compat.store_schemas()
        ahead_shape = sorted(store_schemas)[0]
        schemas = dict(store_schemas)
        schemas[ahead_shape] = store_schemas[ahead_shape] + 5
        schemas["a_future_shape"] = 99
        self.assertGreater(
            schemas[ahead_shape],
            store_schemas[ahead_shape],
            "the declaration is not actually ahead of the store on any real shape, so "
            "this test would pass against a gate that blocks a newer client",
        )
        # Pinned in-process too: a declaration ahead on a real shape must compare as
        # supported. This is the assertion that dies under `claimed != store_version`,
        # and it dies here rather than only through a subprocess exit code.
        self.assertEqual(compat.unsupported_by(schemas), {})

        ahead = self.write_declaration("ahead.json", schemas)
        project_root = self.fresh_project()
        code, _out, err = self.run_in(
            project_root, "bind", "--json", "--client-schemas", str(ahead)
        )
        self.assertEqual(code, 0, err)
        self.assertTrue((project_root / ".dev-team-agents" / "project.json").exists())


class MalformedDeclarationIsAUsageErrorTest(ClientGateTestCase):
    """The fail-open case is the dangerous one: a broken file must never read as silence.

    Every case below asserts three things — exit 2 (not 4, which means "your declaration
    is fine and says no"), the file named in the message, and the command not performed.
    """

    def _bad_declaration_refused(self, label, path_text, expect_in_message=None):
        project_root = self.fresh_project()
        code, out, err = self.run_in(
            project_root, "bind", "--json", "--client-schemas", path_text
        )
        self.assertEqual(
            code,
            errors.EXIT_USAGE,
            "{}: expected a usage error, got {}: {}{}".format(label, code, out[:300], err[:300]),
        )
        body = json.loads(out)
        self.assertFalse(body["ok"])
        self.assertEqual(body["exit_code"], errors.EXIT_USAGE)
        self.assertIn(
            path_text,
            body["error"],
            "{}: the error does not name the declaration file".format(label),
        )
        if expect_in_message:
            self.assertIn(expect_in_message, body["error"], label)
        self.assertFalse(
            (project_root / ".dev-team-agents" / "project.json").exists(),
            "{}: the command ran anyway — a malformed declaration was treated as no "
            "declaration, which is the fail-open case this gate exists to avoid".format(label),
        )

    def test_not_json_at_all(self):
        path = self.tmp / "not-json.json"
        path.write_text("this is not json\n", encoding="utf-8")
        self._bad_declaration_refused("not JSON", str(path), "not valid JSON")

    def test_json_that_is_not_an_object(self):
        path = self.tmp / "array.json"
        path.write_text('["project", 1]', encoding="utf-8")
        self._bad_declaration_refused("a JSON array", str(path), "not a JSON object")

    def test_a_value_that_is_not_an_integer(self):
        schemas = dict(compat.store_schemas())
        schemas["project"] = "1"
        path = self.write_declaration("string-value.json", schemas)
        self._bad_declaration_refused("a string value", str(path), "not an integer")

    def test_a_boolean_value_is_not_an_integer_either(self):
        # `bool` subclasses `int` in Python, so `true` would otherwise be read as schema
        # version 1 — a client that sent a flag where a number belongs would be scored as
        # understanding shape 1 of everything.
        schemas = dict(compat.store_schemas())
        schemas["registry"] = True
        path = self.write_declaration("bool-value.json", schemas)
        self._bad_declaration_refused("a boolean value", str(path), "not an integer")

    def test_a_missing_file(self):
        missing = self.tmp / "does-not-exist.json"
        self._bad_declaration_refused("a missing file", str(missing), "could not be read")

    def test_a_malformed_environment_variable_is_reported_the_same_way(self):
        # Same validation on the ambient path, and the message names the file the
        # variable pointed at — a client whose wrapper exported a stale path has to be
        # told which path.
        path = self.tmp / "env-not-json.json"
        path.write_text("{oops", encoding="utf-8")
        project_root = self.fresh_project()
        code, out, _err = self.run_in(
            project_root,
            "bind",
            "--json",
            env_extra={compat.CLIENT_SCHEMAS_ENV: str(path)},
        )
        self.assertEqual(code, errors.EXIT_USAGE)
        self.assertIn(str(path), json.loads(out)["error"])
        self.assertFalse((project_root / ".dev-team-agents" / "project.json").exists())


class DeclarationValueNeverReachesOutputTest(ClientGateTestCase):
    """A security review's MEDIUM finding: the old message echoed the offending value.

    `DEVTEAM_CLIENT_SCHEMAS` is ambient and inherited, so a wrapper or CI step pointed at
    the wrong JSON file handed this process a one-string read primitive against any UTF-8
    JSON file it can open — the first non-integer value came back out through `--json`,
    into a CI log, and into the desktop app's error screen. A layout-1 credentials file is
    a JSON object of string values, which is exactly the shape that trips the "not an
    integer" branch on its first key, so it stands in for the file a stale seam is most
    likely to be misdirected at. Every assertion here failed against the code before the
    fix — the old message format was `"... is not an integer: {!r}".format(value)`.
    """

    def test_a_string_value_never_appears_in_stdout_or_stderr(self):
        secret = "sk-super-secret-do-not-print-4f9c2b"
        declaration = self.write_declaration("leaky.json", {"api_key": secret, "project": 1})
        project_root = self.fresh_project()
        code, out, err = self.run_in(
            project_root, "bind", "--json", "--client-schemas", str(declaration)
        )
        self.assertEqual(
            code, errors.EXIT_USAGE, "stdout: {}\nstderr: {}".format(out[:300], err[:300])
        )
        self.assertNotIn(secret, out, "the declared value leaked into stdout")
        self.assertNotIn(secret, err, "the declared value leaked into stderr")
        body = json.loads(out)
        # The key and the type it got wrong are still reported — only the value is gone.
        self.assertIn("api_key", body["error"])
        self.assertIn("not an integer", body["error"])
        self.assertIn("str", body["error"])
        self.assertFalse((project_root / ".dev-team-agents" / "project.json").exists())

    def test_a_boolean_value_never_appears_either(self):
        # `bool` is a subclass of `int`, so this branch fires for `true`/`false` too, and
        # the old `{!r}` formatting printed `True`/`False` just as readily as a string.
        declaration = self.write_declaration("leaky-bool.json", {"registry": True})
        project_root = self.fresh_project()
        code, out, err = self.run_in(
            project_root, "bind", "--json", "--client-schemas", str(declaration)
        )
        self.assertEqual(code, errors.EXIT_USAGE)
        self.assertNotIn("True", out)
        self.assertNotIn("True", err)
        self.assertIn("bool", json.loads(out)["error"])

    def test_the_leak_is_closed_on_the_environment_variable_seam_too(self):
        # The seam the finding names explicitly: ambient, inherited, and the one a
        # wrapper script sets once for a whole session.
        secret = "another-secret-should-never-print-9z"
        declaration = self.write_declaration("leaky-env.json", {"credentials": secret})
        project_root = self.fresh_project()
        code, out, err = self.run_in(
            project_root,
            "bind",
            "--json",
            env_extra={compat.CLIENT_SCHEMAS_ENV: str(declaration)},
        )
        self.assertEqual(code, errors.EXIT_USAGE)
        self.assertNotIn(secret, out)
        self.assertNotIn(secret, err)

    def test_a_credentials_shaped_file_leaks_nothing_across_every_key(self):
        # The exact shape the finding calls out: a layout-1 credentials file is a JSON
        # object of string values, so every key in it trips the same branch.
        fake_credentials = {
            "github-token": "ghp_totallyrealsecretvalue000000000000",
            "db-password": "hunter2-but-longer-and-more-secret",
        }
        declaration = self.write_declaration("fake-credentials.json", fake_credentials)
        project_root = self.fresh_project()
        code, out, err = self.run_in(
            project_root, "bind", "--json", "--client-schemas", str(declaration)
        )
        self.assertEqual(code, errors.EXIT_USAGE)
        for secret in fake_credentials.values():
            self.assertNotIn(secret, out)
            self.assertNotIn(secret, err)


class DeclarationFileReadIsBoundedTest(ClientGateTestCase):
    """A security review's LOW finding: an unbounded, non-regular-file read.

    `load_client_schemas` used to call `Path(path).read_text()` with no check that the
    path was a regular file and no cap on how much it would read. The reviewer reproduced
    two hangs from that: a FIFO with no writer blocks `open()` forever, and a character
    device such as `/dev/zero` never raises EOF, so the read never returns and the
    interpreter's heap grows for as long as something keeps consuming it.
    """

    def test_a_fifo_is_refused_promptly_instead_of_blocking_forever(self):
        # `open()` in read mode blocks waiting for a writer no matter how small the
        # eventual read would be, so this test must never depend on the read completing.
        # A generous timeout turns a regression into a fast, legible test failure instead
        # of a hung suite.
        if not hasattr(os, "mkfifo"):
            self.skipTest("no FIFOs on this platform")
        fifo_path = self.tmp / "declaration.fifo"
        os.mkfifo(str(fifo_path))
        project_root = self.fresh_project()
        try:
            code, out, err = self.run_in(
                project_root,
                "bind",
                "--json",
                "--client-schemas",
                str(fifo_path),
                timeout=10,
            )
        except subprocess.TimeoutExpired:
            self.fail(
                "reading the FIFO declaration hung past a 10s timeout instead of being "
                "refused as 'not a regular file' — the fix regressed and the gate is "
                "opening a non-regular path unconditionally again"
            )
        self.assertEqual(
            code, errors.EXIT_USAGE, "stdout: {}\nstderr: {}".format(out[:300], err[:300])
        )
        body = json.loads(out)
        self.assertIn(str(fifo_path), body["error"])
        self.assertIn("not a regular file", body["error"])
        self.assertFalse((project_root / ".dev-team-agents" / "project.json").exists())

    def test_a_directory_is_refused_as_not_a_regular_file(self):
        directory = self.tmp / "a-directory.json"
        directory.mkdir()
        project_root = self.fresh_project()
        code, out, _err = self.run_in(
            project_root, "bind", "--json", "--client-schemas", str(directory)
        )
        self.assertEqual(code, errors.EXIT_USAGE)
        self.assertIn("not a regular file", json.loads(out)["error"])
        self.assertFalse((project_root / ".dev-team-agents" / "project.json").exists())

    def test_an_oversized_declaration_is_refused_by_name(self):
        # Stands in for the reviewer's `/dev/zero` case with a deterministic, portable
        # fixture: a large *valid* JSON document, so a fix that merely truncated the read
        # and then tried to parse it could not accidentally slip through as "malformed
        # JSON" instead of being caught by the size check itself.
        oversized = self.tmp / "oversized.json"
        padding = {"k{}".format(i): i for i in range(2000)}
        oversized.write_text(json.dumps(padding), encoding="utf-8")
        self.assertGreater(
            oversized.stat().st_size,
            compat.MAX_DECLARATION_BYTES,
            "the fixture is not actually over the cap — strengthen it",
        )
        project_root = self.fresh_project()
        code, out, err = self.run_in(
            project_root, "bind", "--json", "--client-schemas", str(oversized)
        )
        self.assertEqual(
            code, errors.EXIT_USAGE, "stdout: {}\nstderr: {}".format(out[:300], err[:300])
        )
        body = json.loads(out)
        self.assertIn(str(oversized), body["error"])
        self.assertIn(str(compat.MAX_DECLARATION_BYTES), body["error"])
        self.assertFalse((project_root / ".dev-team-agents" / "project.json").exists())

    def test_a_well_formed_declaration_under_the_cap_is_unaffected(self):
        # The cap must not tighten around ordinary use — a real declaration is a handful
        # of shape names mapped to small integers, nowhere near the limit.
        project_root = self.fresh_project()
        code, out, err = self.run_in(
            project_root, "bind", "--json", "--client-schemas", str(self.compatible())
        )
        self.assertEqual(code, 0, "stdout: {}\nstderr: {}".format(out[:300], err[:300]))
        self.assertTrue((project_root / ".dev-team-agents" / "project.json").exists())


class HintExampleTracksTheStoreSchemasTest(ClientGateTestCase):
    """The stale-example finding: a hardcoded hint literal quoted `registry: 3` long
    after `registry.SCHEMA` became `1`. The fix derives the example from
    `store_schemas()` instead of a literal, so it cannot go stale silently again.
    """

    def test_the_not_json_hint_embeds_the_real_store_numbers(self):
        path = self.tmp / "not-json.json"
        path.write_text("nope", encoding="utf-8")
        code, out, _err = self.run_in(
            self.fresh_project(), "bind", "--json", "--client-schemas", str(path)
        )
        self.assertEqual(code, errors.EXIT_USAGE)
        hint = json.loads(out)["hint"]
        self.assertIn(json.dumps(compat.store_schemas()), hint)
        # The exact stale literal this replaced must not come back.
        self.assertNotIn('"registry": 3', hint)

    def test_the_non_integer_value_hint_is_unchanged(self):
        # Only the two JSON-parsing hints used the stale literal; this one names no
        # example and must not be touched by the fix.
        schemas = dict(compat.store_schemas())
        schemas["project"] = "not-a-number"
        declaration = self.write_declaration("bad-type.json", schemas)
        code, out, _err = self.run_in(
            self.fresh_project(), "bind", "--json", "--client-schemas", str(declaration)
        )
        self.assertEqual(code, errors.EXIT_USAGE)
        self.assertIn("is left out", json.loads(out)["hint"])


class RefusalConformsToTheJsonContractTest(ClientGateTestCase):
    """Both output forms of a refusal, against the documented envelope."""

    def test_json_form(self):
        code, out, err = self.run_in(
            self.fresh_project(), "bind", "--json", "--client-schemas", str(self.one_behind())
        )
        self.assertEqual(code, errors.EXIT_CONFLICT)
        self.assertIn(code, {0, 1, 2, 3, 4})
        body = json.loads(out)  # exactly one document, and it parses
        self.assertIsInstance(body, dict)
        self.assertFalse(body["ok"])
        self.assertTrue(body["error"])
        self.assertEqual(body["exit_code"], code)
        self.assertEqual(body["details"]["store_schemas"], compat.store_schemas())
        self.assertFalse(body["details"]["may_write"])
        # stderr must never carry the document — that channel is warnings and human text.
        if err.strip():
            with self.assertRaises(ValueError):
                json.loads(err)

    def test_human_form(self):
        code, out, err = self.run_in(
            self.fresh_project(), "bind", "--client-schemas", str(self.one_behind())
        )
        self.assertEqual(code, errors.EXIT_CONFLICT)
        self.assertIn("would write to this store", err)
        self.assertIn("hint:", err)
        # Human mode never writes a JSON document to stdout.
        if out.strip():
            with self.assertRaises(ValueError):
                json.loads(out)


class PrecedenceTest(ClientGateTestCase):
    """Flag over environment variable, stated once and asserted in both directions."""

    def test_the_flag_wins_when_it_is_compatible_and_the_variable_is_not(self):
        project_root = self.fresh_project()
        code, _out, err = self.run_in(
            project_root,
            "bind",
            "--json",
            "--client-schemas",
            str(self.compatible()),
            env_extra={compat.CLIENT_SCHEMAS_ENV: str(self.one_behind())},
        )
        self.assertEqual(code, 0, "the ambient variable overrode the explicit flag: {}".format(err))
        self.assertTrue((project_root / ".dev-team-agents" / "project.json").exists())

    def test_the_flag_wins_when_it_is_incompatible_and_the_variable_is_not(self):
        # The other direction, which is the one that matters for safety: an exported
        # compatible declaration must not launder a call that declares itself behind.
        code, out, _err = self.run_in(
            self.fresh_project(),
            "bind",
            "--json",
            "--client-schemas",
            str(self.one_behind()),
            env_extra={compat.CLIENT_SCHEMAS_ENV: str(self.compatible())},
        )
        self.assertEqual(code, errors.EXIT_CONFLICT)
        self.assertEqual(json.loads(out)["details"]["declared_by"], "--client-schemas")

    def test_the_variable_alone_gates_and_says_so(self):
        code, out, _err = self.run_in(
            self.fresh_project(),
            "bind",
            "--json",
            env_extra={compat.CLIENT_SCHEMAS_ENV: str(self.one_behind())},
        )
        self.assertEqual(code, errors.EXIT_CONFLICT)
        details = json.loads(out)["details"]
        # Named, so a client whose wrapper three layers up exported the variable is told
        # about the variable rather than about a flag it never passed.
        self.assertEqual(details["declared_by"], compat.CLIENT_SCHEMAS_ENV)

    def test_precedence_is_resolved_in_one_place(self):
        # In-process, against the same function the CLI calls: the wiring above proves
        # the seam end to end, and this pins the rule itself so it cannot be re-decided
        # per call site.
        flag = self.compatible("p-flag.json")
        env = self.one_behind("p-env.json")
        declaration = compat.client_declaration(
            str(flag), {compat.CLIENT_SCHEMAS_ENV: str(env)}
        )
        self.assertEqual(declaration.origin, "--client-schemas")
        self.assertEqual(declaration.schemas, compat.store_schemas())

        declaration = compat.client_declaration(None, {compat.CLIENT_SCHEMAS_ENV: str(env)})
        self.assertEqual(declaration.origin, compat.CLIENT_SCHEMAS_ENV)

        self.assertIsNone(compat.client_declaration(None, {}))
        self.assertIsNone(compat.client_declaration(None, {compat.CLIENT_SCHEMAS_ENV: "   "}))


class CompatAnswersTheDeclaredClientTest(ClientGateTestCase):
    """`compat` is read-only, so it always answers — and it reads the same seam."""

    def test_compat_reports_may_write_from_the_global_seam(self):
        code, out, _err = self.run_in(
            self.fresh_dir(), "compat", "--json", "--client-schemas", str(self.one_behind())
        )
        # Exit 1, not 4: here the negative answer is the command's *finding*, not a
        # refusal to act. The two codes are deliberately different — an incompatible
        # client asking is a successful question; the same client writing is a conflict.
        self.assertEqual(code, errors.EXIT_FINDINGS)
        payload = json.loads(out)
        self.assertFalse(payload["may_write"])
        self.assertTrue(payload["unsupported"])

    def test_an_explicit_client_flag_outranks_the_global_seam(self):
        code, out, _err = self.run_in(
            self.fresh_dir(),
            "compat",
            "--json",
            "--client",
            json.dumps(compat.store_schemas()),
            "--client-schemas",
            str(self.one_behind()),
        )
        self.assertEqual(code, 0)
        self.assertTrue(json.loads(out)["may_write"])

    def test_compat_is_answerable_by_a_client_that_cannot_write(self):
        # The refusal's hint tells the client to run `devteam compat --client-file …`.
        # That has to work for a client that is behind, or the guidance is a dead end.
        behind = self.one_behind()
        code, out, _err = self.run_in(
            self.fresh_dir(), "compat", "--json", "--client-file", str(behind)
        )
        self.assertEqual(code, errors.EXIT_FINDINGS)
        payload = json.loads(out)
        self.assertEqual(
            payload["unsupported"],
            compat.unsupported_by(json.loads(behind.read_text(encoding="utf-8"))),
        )


class CompatErrorDocumentsAreADecidedShapeTest(ClientGateTestCase):
    """`devteam compat`'s malformed-declaration documents, after the parsers were merged.

    `cmd_compat` used to carry its own reader and its own validation. Sharing
    `compat.parse_client_schemas`/`load_client_schemas` with the gate is what keeps the two
    from disagreeing about what a valid declaration is — but it changed four of this
    command's error documents, and in one case the **key set**: `--client '[]'` used to
    reach `UsageError(str(exc))` re-wrapping a `TypeError` from `unsupported_by`, with no
    `hint` at all, and now has one.

    **That addition is kept, deliberately.** `hint` is an optional key of the *error*
    envelope, not of a command's payload — `errors.DevteamError.payload()` emits it only
    when set, so its presence already varies from error to error within this same command
    (`--client-file /nope` has always carried one). No client can treat it as a fixed key
    of `compat`, `AppFacingKeySetContractTest` pins the success payloads only, and an
    added human-readable hint cannot break a caller branching on `ok`/`error`/`exit_code`.
    Restoring the old set would mean deliberately keeping the one malformed-declaration
    message that tells the caller nothing about how to fix it, on the surface whose entire
    job is telling a client what to correct.

    The test exists so the next person finds the decision rather than the diff.
    """

    def _compat_error(self, *args):
        code, out, _err = self.run_in(self.fresh_dir(), "compat", "--json", *args)
        self.assertEqual(code, errors.EXIT_USAGE, out[:300])
        return json.loads(out)

    def test_a_non_object_declaration_carries_a_hint(self):
        body = self._compat_error("--client", "[]")
        self.assertEqual(
            set(body),
            {"ok", "error", "exit_code", "hint"},
            "the key set of this error document changed again — see the class docstring "
            "for why `hint` is there, and decide before editing this assertion",
        )
        self.assertIn("not a JSON object", body["error"])
        self.assertIn("--client", body["error"])
        self.assertTrue(body["hint"])

    def test_the_envelope_carries_hint_only_when_there_is_one(self):
        # The reason the key set above is a decision and not a contract violation: `hint`
        # is conditional by construction, so it was never a fixed key of this command.
        self.assertEqual(
            set(errors.UsageError("no hint here").payload()), {"ok", "error", "exit_code"}
        )
        self.assertIn("hint", errors.UsageError("x", hint="y").payload())


class PreSplitStoreTest(ClientGateTestCase):
    """The gate's **position**, and what a read-only command may answer without the move.

    Every other fixture in this file installs a store that is already in the post-ADR-0013
    split layout, so `store.adopt_machine_layout()` is a no-op on all of them. That made
    two separate properties untestable at once:

    * **where the gate sits.** Moving the gate block below `adopt_machine_layout()` in
      `cli.main` left the whole file green, because on a split store there is nothing for
      the relocation to write and a refusal is inert either way.
    * **what the relocation is.** It rewrites `registry` and `bind_manifest` — the exact
      shapes an incompatible client declares it cannot read — so running it on that
      caller's behalf is the gate letting through the one write it exists to stop.

    This class fabricates the pre-split layout from a real bound project and pins both.
    It is also where the third property is pinned: with the relocation skipped, a
    read-only command answers against the layout on disk, and `paths.registry_file()`
    resolves only the split path — so a command that reads the registry answers as though
    nothing were bound. `compat.NEEDS_MACHINE_LAYOUT` names those, and the sweep below
    measures the membership instead of trusting it.
    """

    #: Arguments that only make the parse succeed, as `probe_args` does for the mutating
    #: sweep. Driven off `compat.READ_ONLY` so a read-only command added tomorrow is
    #: swept the day it is classified.
    READ_PROBE_ARGS = {
        ("prefs", "get"): ("language",),
        # The fixture source tree's agents carry no frontmatter, so this resolves to "not
        # found" (exit 2). That is fine and deliberate: what the sweep asserts is that a
        # command's answer does not CHANGE between the two layouts, whatever the answer is.
        ("catalog", "show"): ("backend-developer",),
    }

    #: `cred get` is the one read-only command excluded from the byte-identical sweep, and
    #: not because it is awkward: it appends an audit line, so two runs of it are
    #: guaranteed to differ, and it refuses `--json` by design (ADR-0010) so there is no
    #: document to compare. `NoDeclarationIsUnchangedTest` already asserts end to end that
    #: a behind client still gets the value and still gets the documented `--json`
    #: refusal; nothing about the layout changes either.
    # `notifications watch` streams until its stdin closes, so it cannot be run for "one
    # answer" twice and compared; its pre-split behaviour is the refusal
    # `NEEDS_MACHINE_LAYOUT` gives it, which the migration-error tests already cover.
    READ_SWEEP_EXCLUDED = {("cred", "get"), ("notifications", "watch"), ("tasks", "watch")}

    def setUp(self):
        super().setUp()
        self.project_root = self.fresh_project()
        code, out, err = self.run_in(self.project_root, "bind", "--json")
        self.assertEqual(code, 0, "fixture bind failed: {}".format(err))
        self.project_id = json.loads(out)["project_id"]
        self.behind = self.one_behind()

    # ── fixture ──────────────────────────────────────────────────────────────

    def read_sweep_commands(self):
        """Every read-only leaf, with the arguments its parse needs."""
        return [
            (path, self.READ_PROBE_ARGS.get(path, ()))
            for path in sorted(compat.READ_ONLY)
            if path not in self.READ_SWEEP_EXCLUDED
        ]

    def make_pre_split(self):
        """Put this store's machine-local records back at the pre-ADR-0013 paths.

        Built by de-splitting a store that a real `bind` wrote, rather than by
        hand-writing a legacy registry: the records then hold exactly what the current
        code produces, so a difference the sweep reports is the layout and nothing else.
        The project's own pointers are moved back too — a store written before the split
        resolved `state-dir` and `memory-dir` at the portable per-project directory, and a
        fixture that left them pointing into the machine subtree would be testing a
        half-migrated store that never existed.
        """
        data = paths.data_dir()
        machine_registry = paths.registry_file()
        self.assertTrue(
            machine_registry.is_file(),
            "the fixture expects a split store to de-split; found no {}".format(
                machine_registry
            ),
        )
        shutil.move(str(machine_registry), str(data / "registry.json"))

        legacy = paths.project_data_dir(self.project_id)
        legacy.mkdir(parents=True, exist_ok=True)
        machine_project = paths.machine_project_dir(self.project_id)
        moved = []
        if machine_project.is_dir():
            for item in sorted(machine_project.iterdir()):
                if item.is_file():
                    shutil.move(str(item), str(legacy / item.name))
                    moved.append(item.name)
        self.assertIn("bind-manifest.json", moved, "the bind wrote no manifest to move")

        for pointer in (project.STATE_DIR_POINTER, project.MEMORY_DIR_POINTER):
            (self.project_root / ".dev-team-agents" / pointer).write_text(
                str(legacy) + "\n", encoding="utf-8"
            )

        self.assertTrue(
            store.machine_layout_pending(),
            "the fixture did not produce a pre-split store, so nothing below is testing "
            "the relocation",
        )

    # ── the gate's position ──────────────────────────────────────────────────

    def test_a_refused_mutating_command_relocates_nothing(self):
        # The assertion that fails when the gate moves below `adopt_machine_layout()`:
        # there, the refusal still returns exit 4, but the store has already been
        # rewritten on behalf of the client that was just told it may not write.
        self.make_pre_split()
        before = self.snapshot(self.home)
        code, out, err = self.run_in(
            self.fresh_project(), "bind", "--json", "--client-schemas", str(self.behind)
        )
        self.assertEqual(code, errors.EXIT_CONFLICT, "{}{}".format(out[:300], err[:300]))
        self.assertEqual(
            before,
            self.snapshot(self.home),
            "the store was relocated although the command was refused — the gate is "
            "running after store.adopt_machine_layout() instead of before it",
        )
        self.assertTrue(
            (paths.data_dir() / "registry.json").is_file(),
            "registry.json left the pre-split path during a refused command",
        )

    def test_every_mutating_command_refused_on_a_pre_split_store_relocates_nothing(self):
        # The same property across the whole classification, not just `bind`: a gate that
        # moved below the relocation for one command moved for all of them, and a gate
        # that grows a per-command exemption should fail here rather than on the one
        # command nobody swept.
        self.make_pre_split()
        extra = IncompatibleDeclarationRefusesEveryMutatingCommandTest.probe_args(self)
        before = self.snapshot(self.home)
        for path in sorted(compat.MUTATING):
            label = " ".join(path)
            with self.subTest(command=label):
                code, out, err = self.run_in(
                    self.fresh_project(),
                    *path,
                    *extra.get(path, ()),
                    "--client-schemas",
                    str(self.behind),
                )
                self.assertEqual(
                    code, errors.EXIT_CONFLICT, "{}: {}{}".format(label, out[:300], err[:300])
                )
                self.assertEqual(
                    before,
                    self.snapshot(self.home),
                    "{}: the store changed although the command was refused".format(label),
                )

    # ── what a read-only command may answer ──────────────────────────────────

    def test_a_read_only_command_answers_the_pre_split_truth_or_is_refused(self):
        """The sweep that measures `compat.NEEDS_MACHINE_LAYOUT` instead of trusting it.

        Each read-only command is run twice under the **same** incompatible declaration:
        once on the split store, once after de-splitting. The answer must be identical —
        the relocation is skipped, so the command reports the store as it is — or the
        command must be refused with the migration error. Anything else is a command
        quietly answering wrong, which is the failure `devteam list` had: exit 0,
        `projects: []`, no error anywhere.
        """
        commands = self.read_sweep_commands()
        self.assertTrue(commands, "no read-only command was swept")

        split_answers = {}
        for path, args in commands:
            split_answers[path] = self.run_in(
                self.project_root, *path, *args, "--json", "--client-schemas", str(self.behind)
            )

        self.make_pre_split()
        before = self.snapshot(self.home)
        refused = set()
        for path, args in commands:
            label = " ".join(path)
            with self.subTest(command=label):
                code, out, err = self.run_in(
                    self.project_root,
                    *path,
                    *args,
                    "--json",
                    "--client-schemas",
                    str(self.behind),
                )
                self.assertEqual(
                    before,
                    self.snapshot(self.home),
                    "{}: the store was relocated for a client that declared it cannot "
                    "read the shapes the relocation writes".format(label),
                )
                if code == errors.EXIT_ENVIRONMENT and "machine-local records" in out:
                    refused.add(path)
                    body = json.loads(out)
                    self.assertFalse(body["ok"])
                    self.assertTrue(body["details"]["machine_layout_pending"])
                    continue
                self.assertEqual(
                    (code, out),
                    split_answers[path][:2],
                    "{}: answers differently on a pre-split store than on the same store "
                    "after relocation. It reads a machine-local record, so it must be "
                    "listed in compat.NEEDS_MACHINE_LAYOUT and refused — a clear refusal "
                    "beats a wrong answer.\nstderr: {}".format(label, err[:300]),
                )

        # A command the sweep cannot run cannot be measured; its entry stands on the
        # reason written beside it in `compat.py`.
        self.assertEqual(
            refused,
            set(compat.NEEDS_MACHINE_LAYOUT) - self.READ_SWEEP_EXCLUDED,
            "the commands that actually cannot answer on a pre-split store are not the "
            "ones compat.NEEDS_MACHINE_LAYOUT names. Add or remove the entry, with the "
            "reason beside it.",
        )

    def test_list_is_refused_rather_than_reporting_an_empty_store(self):
        # The measured case, named: the positive control is the same store answered
        # anonymously, which relocates and finds the project. Without it, "refused" could
        # be a store that genuinely has nothing bound.
        self.make_pre_split()
        code, out, _err = self.run_in(
            self.project_root, "list", "--json", "--client-schemas", str(self.behind)
        )
        self.assertEqual(code, errors.EXIT_ENVIRONMENT)
        body = json.loads(out)
        self.assertIn("list", body["error"])
        self.assertIn("pre-split paths", body["error"])
        self.assertIn("one-time migration", body["hint"])
        self.assertEqual(
            body["details"]["unsupported"],
            compat.unsupported_by(json.loads(self.behind.read_text(encoding="utf-8"))),
        )

        code, out, err = self.run_in(self.project_root, "list", "--json")
        self.assertEqual(code, 0, err)
        self.assertEqual(
            [entry["project_id"] for entry in json.loads(out)["projects"]],
            [self.project_id],
            "the anonymous control did not find the bound project, so the refusal above "
            "proves nothing",
        )

    def test_the_escape_hatch_answers_on_a_pre_split_store(self):
        # The refusal's own hint sends a behind client to `devteam compat`. That command,
        # plus `version` and `path`, must answer on a store that has not been relocated —
        # otherwise the guidance is a dead end for exactly the caller it is written for.
        self.make_pre_split()
        before = self.snapshot(self.home)
        for path, expected in ((("compat",), errors.EXIT_FINDINGS), (("version",), 0), (("path",), 0)):
            label = " ".join(path)
            with self.subTest(command=label):
                code, out, err = self.run_in(
                    self.project_root, *path, "--json", "--client-schemas", str(self.behind)
                )
                self.assertEqual(code, expected, "{}: {}{}".format(label, out[:200], err[:200]))
                self.assertTrue(json.loads(out))
                self.assertEqual(before, self.snapshot(self.home), label)
        # `compat` answered the question the hint promises it answers.
        code, out, _err = self.run_in(
            self.project_root, "compat", "--json", "--client-schemas", str(self.behind)
        )
        self.assertFalse(json.loads(out)["may_write"])

    def test_a_compatible_declaration_still_gets_the_relocation(self):
        # The skip is scoped to an *incompatible* declaration, not to any declaration. A
        # client that understands every shape is exactly as entitled to the migration as a
        # human, and blocking it would strand every store the app touches first.
        self.make_pre_split()
        code, out, err = self.run_in(
            self.project_root, "path", "--json", "--client-schemas", str(self.compatible())
        )
        self.assertEqual(code, 0, err)
        self.assertFalse(
            (paths.data_dir() / "registry.json").exists(),
            "a compatible client did not get the relocation",
        )
        self.assertTrue(paths.registry_file().is_file())
        self.assertFalse(store.machine_layout_pending())

    def test_an_anonymous_caller_still_gets_the_relocation(self):
        # The human's CLI, on the one store shape where this change could have touched it.
        self.make_pre_split()
        code, _out, err = self.run_in(self.project_root, "path", "--json")
        self.assertEqual(code, 0, err)
        self.assertFalse(store.machine_layout_pending())
        self.assertIn("moved", err, "the relocation warning is no longer reported")


class GroupWithNoSubcommandTest(ClientGateTestCase):
    """`devteam store` under a declaration is still "needs a subcommand", not a refusal.

    `cli.main` gates only a parse that resolved to a handler (`hasattr(args, "func")`).
    Removing that guard left every test green while changing `devteam store`, `devteam
    prefs` and `devteam cred` from exit 2 with a usable message to exit 4 about a command
    the caller never named: the group path is in neither classification table, so
    `compat.is_mutating` fails closed on it — correct as a default, wrong as an answer to
    a question that was never a command.
    """

    GROUPS = {
        "store": "store needs a subcommand",
        "prefs": "prefs needs a subcommand",
        "cred": "cred needs a subcommand",
        "skills": "skills needs a subcommand",
    }

    def test_a_group_is_a_usage_error_under_an_incompatible_declaration(self):
        for group, message in sorted(self.GROUPS.items()):
            with self.subTest(group=group):
                code, out, err = self.run_in(
                    self.fresh_dir(), group, "--json", "--client-schemas", str(self.one_behind())
                )
                self.assertEqual(
                    code,
                    errors.EXIT_USAGE,
                    "`devteam {}` with a declaration answered {} instead of a usage "
                    "error — the gate is being handed a group path.\n{}{}".format(
                        group, code, out[:300], err[:300]
                    ),
                )
                body = json.loads(out)
                self.assertIn(message, body["error"])
                self.assertNotIn("details", body)

    def test_a_group_answers_identically_declared_or_not(self):
        # The pair, as everywhere else in this file: the declaration must make no
        # difference at all on a path that is not a command.
        for group in sorted(self.GROUPS):
            with self.subTest(group=group):
                cwd = self.fresh_dir()
                anonymous = self.run_in(cwd, group, "--json")
                declared = self.run_in(
                    cwd, group, "--json", "--client-schemas", str(self.one_behind())
                )
                self.assertEqual(anonymous, declared)


class RefusalDetailsAreThePinnedContractTest(ClientGateTestCase):
    """The exact `details` key set of a refusal, and every value in it.

    `docs/specs/v4-app-and-distribution.md` marks the refusal scenario `[MET]` on all
    seven keys, and until this existed three of them — `command`, `declaration_source`,
    `client_schemas` — were asserted by no test at all, and nothing pinned the key set in
    either direction. ADR-0011 makes `--json` the app's public API, so the set is a
    contract: a client reading `details.unsupported` to render "upgrade to understand
    registry v3" breaks silently when the key is renamed.

    A failure here is a **decision**, not a bug — the same rule
    `tests/test_json_contract.py`'s `AppFacingKeySetContractTest` states for the success
    payloads. Read the added and removed keys, decide whether the change is deliberate,
    and only then edit the set below.
    """

    EXPECTED_DETAILS = {
        "command",
        "declared_by",
        "declaration_source",
        "client_schemas",
        "store_schemas",
        "unsupported",
        "may_write",
    }

    def test_the_write_refusal_details_key_set_and_values(self):
        declaration = self.one_behind()
        declared = json.loads(declaration.read_text(encoding="utf-8"))
        code, out, _err = self.run_in(
            self.fresh_project(),
            "prefs",
            "set",
            "language",
            "en",
            "--json",
            "--client-schemas",
            str(declaration),
        )
        self.assertEqual(code, errors.EXIT_CONFLICT)
        details = json.loads(out)["details"]

        actual = set(details)
        if actual != self.EXPECTED_DETAILS:
            self.fail(
                "the refusal's details shape changed.\n"
                "  added:   {}\n"
                "  removed: {}\n"
                "Per ADR-0011 an output shape change is a breaking change. Decide whether "
                "this is deliberate, then update EXPECTED_DETAILS — do not treat this "
                "failure as something to silence.".format(
                    sorted(actual - self.EXPECTED_DETAILS) or "(none)",
                    sorted(self.EXPECTED_DETAILS - actual) or "(none)",
                )
            )

        # Every value, so the pin is a contract and not just a list of key names.
        self.assertEqual(details["command"], "prefs set")
        self.assertEqual(details["declared_by"], "--client-schemas")
        self.assertEqual(details["declaration_source"], str(declaration))
        self.assertEqual(details["client_schemas"], declared)
        self.assertEqual(details["store_schemas"], compat.store_schemas())
        self.assertEqual(details["unsupported"], compat.unsupported_by(declared))
        self.assertIs(details["may_write"], False)

    def test_the_command_key_is_the_full_leaf_path(self):
        # `prefs set`, not `prefs` and not `set`: a client routing on `details.command`
        # cannot tell two leaves of one group apart from either half alone.
        for path, extra in ((("prefs", "unset"), ("language",)), (("bind",), ())):
            with self.subTest(command=" ".join(path)):
                code, out, _err = self.run_in(
                    self.fresh_project(),
                    *path,
                    *extra,
                    "--json",
                    "--client-schemas",
                    str(self.one_behind()),
                )
                self.assertEqual(code, errors.EXIT_CONFLICT)
                self.assertEqual(json.loads(out)["details"]["command"], " ".join(path))


class EmptyFlagValueIsNotSilenceTest(ClientGateTestCase):
    """`--client-schemas ""` is a caller that got a value wrong, not a caller that said nothing.

    The flag was tested for truthiness, so the empty string fell through to the
    environment variable and resolved to `None` — the anonymous, ungated path. That is the
    fail-open `compat.parse_client_schemas` forbids in its own docstring, reached by the
    most ordinary shell idiom a client wrapper has: `--client-schemas "$SCHEMAS"` with
    `SCHEMAS` unset.

    The asymmetry with the environment variable is deliberate and asserted below in both
    directions: a shell cannot distinguish an absent variable from an empty one, so empty
    means unset there — and only there.
    """

    def test_an_empty_flag_value_is_a_usage_error(self):
        for label, value in (("empty", ""), ("whitespace", "  ")):
            with self.subTest(value=label):
                project_root = self.fresh_project()
                code, out, err = self.run_in(
                    project_root, "bind", "--json", "--client-schemas", value
                )
                self.assertEqual(
                    code,
                    errors.EXIT_USAGE,
                    "--client-schemas {!r} was not refused: {}{}".format(
                        value, out[:300], err[:300]
                    ),
                )
                body = json.loads(out)
                self.assertIn("--client-schemas", body["error"])
                self.assertFalse(
                    (project_root / ".dev-team-agents" / "project.json").exists(),
                    "the command ran with the declaration silently dropped — the "
                    "fail-open case this gate exists to avoid",
                )

    def test_an_empty_flag_does_not_fall_through_to_the_environment_variable(self):
        # The specific mechanism: with a *compatible* declaration exported, a truthiness
        # test on the flag would make the empty flag resolve to the variable and succeed,
        # hiding the caller's mistake behind an unrelated declaration.
        project_root = self.fresh_project()
        code, out, _err = self.run_in(
            project_root,
            "bind",
            "--json",
            "--client-schemas",
            "",
            env_extra={compat.CLIENT_SCHEMAS_ENV: str(self.compatible())},
        )
        self.assertEqual(code, errors.EXIT_USAGE, out[:300])
        self.assertFalse((project_root / ".dev-team-agents" / "project.json").exists())

    def test_the_resolver_itself_separates_the_two_seams(self):
        # In-process, against the one function that owns the rule, so the asymmetry is
        # pinned as a rule and not only as an exit code. The variable side must stay
        # exactly as it is: it is documented, tested and relied upon.
        with self.assertRaises(errors.UsageError):
            compat.client_declaration("", {})
        with self.assertRaises(errors.UsageError):
            compat.client_declaration("   ", {})
        self.assertIsNone(compat.client_declaration(None, {compat.CLIENT_SCHEMAS_ENV: ""}))
        self.assertIsNone(compat.client_declaration(None, {compat.CLIENT_SCHEMAS_ENV: "  "}))
        self.assertIsNone(compat.client_declaration(None, {}))


class UnreadableDeclarationIsADocumentNotATracebackTest(ClientGateTestCase):
    """Failures of `read_text` and `json.loads` that are neither OSError nor JSONDecodeError.

    `Path.read_text(encoding="utf-8")` raises `UnicodeDecodeError` (a `ValueError`) and
    `json.loads` raises `RecursionError` on deeply nested input. Neither was caught, and
    the gate block in `cli.main` had `except DevteamError` only — so both reached the shell
    as a traceback, with **stdout empty under `--json`** (ADR-0011 says exactly one
    document goes out) and exit **1**, which this CLI defines as "ran and reported a
    problem it did not fix". A client branching on `$?` read a crash as a finding.

    Asserted on both seams that read a file, and on `devteam compat` as well, because that
    is the command the refusal's hint sends a behind client to run.
    """

    NESTING = 200000

    def not_utf8(self):
        path = self.tmp / "not-utf8.json"
        path.write_bytes(b"\xff\xfe{\"project\": 1}")
        return path

    def too_deep(self):
        path = self.tmp / "too-deep.json"
        path.write_text("[" * self.NESTING + "]" * self.NESTING, encoding="utf-8")
        return path

    def _one_document_usage_error(self, label, code, out, err):
        self.assertEqual(
            code,
            errors.EXIT_USAGE,
            "{}: expected exit {} (a malformed question), got {}. Exit 1 would tell a "
            "client the command ran and found something.\nstdout: {}\nstderr: {}".format(
                label, errors.EXIT_USAGE, code, out[:200], err[:400]
            ),
        )
        self.assertTrue(out.strip(), "{}: --json emitted no document at all".format(label))
        body = json.loads(out)  # exactly one document, and it parses
        self.assertFalse(body["ok"])
        self.assertEqual(body["exit_code"], errors.EXIT_USAGE)
        self.assertNotIn(
            "Traceback", err, "{}: a traceback reached the shell".format(label)
        )
        return body

    def test_the_gate_reports_both_through_the_contract(self):
        for label, path in (("not UTF-8", self.not_utf8()), ("too deep", self.too_deep())):
            with self.subTest(case=label):
                project_root = self.fresh_project()
                code, out, err = self.run_in(
                    project_root, "bind", "--json", "--client-schemas", str(path)
                )
                body = self._one_document_usage_error(label, code, out, err)
                self.assertIn(str(path), body["error"])
                self.assertIn("--client-schemas", body["error"])
                self.assertFalse(
                    (project_root / ".dev-team-agents" / "project.json").exists(),
                    "{}: the command ran with an unreadable declaration".format(label),
                )

    def test_the_environment_variable_seam_reports_both_the_same_way(self):
        for label, path in (("not UTF-8", self.not_utf8()), ("too deep", self.too_deep())):
            with self.subTest(case=label):
                project_root = self.fresh_project()
                code, out, err = self.run_in(
                    project_root,
                    "bind",
                    "--json",
                    env_extra={compat.CLIENT_SCHEMAS_ENV: str(path)},
                )
                body = self._one_document_usage_error(label, code, out, err)
                self.assertIn(compat.CLIENT_SCHEMAS_ENV, body["error"])
                self.assertFalse((project_root / ".dev-team-agents" / "project.json").exists())

    def test_compat_reports_both_the_same_way(self):
        for label, path in (("not UTF-8", self.not_utf8()), ("too deep", self.too_deep())):
            with self.subTest(case=label):
                code, out, err = self.run_in(
                    self.fresh_dir(), "compat", "--json", "--client-file", str(path)
                )
                body = self._one_document_usage_error(label, code, out, err)
                self.assertIn("--client-file", body["error"])

    def test_an_unforeseen_exception_in_the_gate_is_still_one_document(self):
        # The `except Exception` net in `cli.main`'s gate block, exercised directly. Both
        # live triggers above are converted to `UsageError` inside `compat` now, so nothing
        # reaches the net by itself — and an untested net is exactly how those two reached
        # the shell as tracebacks to begin with. Patched in-process because there is no
        # input that produces a non-`DevteamError` here any more, which is the point.
        from devteam import cli

        def boom(flag_value=None, environ=None):
            raise RuntimeError("something nobody predicted")

        original = compat.client_declaration
        compat.client_declaration = boom
        self.addCleanup(setattr, compat, "client_declaration", original)

        out, err = io.StringIO(), io.StringIO()
        code = cli.main(["path", "--json"], stdout=out, stderr=err)
        self.assertEqual(
            code,
            errors.EXIT_ENVIRONMENT,
            "an unexpected exception in the gate did not land on the contract",
        )
        body = json.loads(out.getvalue())
        self.assertFalse(body["ok"])
        self.assertIn("RuntimeError", body["error"])
        self.assertNotIn("Traceback", err.getvalue())

    def test_a_declaration_file_names_the_seam_that_carried_it(self):
        # The property `compat`'s docstring argues for, and the one that was lost when the
        # two parsers were merged: `--client-file /nope/x.json could not be read`, not a
        # bare path the caller never typed on its own.
        missing = self.tmp / "nope.json"
        cases = (
            ("--client-file", ("compat", "--json", "--client-file", str(missing)), {}),
            (
                "--client-schemas",
                ("bind", "--json", "--client-schemas", str(missing)),
                {},
            ),
            (
                compat.CLIENT_SCHEMAS_ENV,
                ("bind", "--json"),
                {compat.CLIENT_SCHEMAS_ENV: str(missing)},
            ),
        )
        for seam, args, env_extra in cases:
            with self.subTest(seam=seam):
                code, out, _err = self.run_in(
                    self.fresh_project(), *args, env_extra=env_extra
                )
                self.assertEqual(code, errors.EXIT_USAGE)
                message = json.loads(out)["error"]
                self.assertIn(str(missing), message)
                self.assertIn(
                    seam,
                    message,
                    "the message does not say which seam carried the declaration: "
                    "{!r}".format(message),
                )


if __name__ == "__main__":
    unittest.main()
