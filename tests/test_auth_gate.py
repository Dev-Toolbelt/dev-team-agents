"""The central account gate (ADR-0029 SR-30): allowlist, warn vs enforce, the offline window."""

from __future__ import annotations

import argparse
import io
import json
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

from auth_support import AuthTestCase  # noqa: E402

from devteam import auth, cli, entitlement
from devteam import auth_gate as gate  # noqa: E402
from devteam.output import Emitter  # noqa: E402

#: The command roots ADR-0029 never gates. A new subcommand is gated unless added here AND
#: to `gate.EXEMPT`, so this list changing is a reviewed decision, not a side effect.
EXEMPT_ROOTS = {"auth", "version", "path", "compat", "doctor", "unbind", "uninstall", "export"}


def leaf_paths():
    parser = cli.build_parser()
    found = []

    def walk(node, path):
        action = next((a for a in node._actions if isinstance(a, argparse._SubParsersAction)), None)
        if action is None:
            found.append(path)
            return
        for name, child in action.choices.items():
            walk(child, path + (name,))

    walk(parser, ())
    return [p for p in found if p]


class AllowlistTest(unittest.TestCase):
    def test_every_real_command_is_gated_unless_it_is_on_the_list(self):
        paths = leaf_paths()
        self.assertGreater(len(paths), 50)
        for path in paths:
            with self.subTest(path=" ".join(path)):
                self.assertEqual(gate.is_exempt(path), path[0] in EXEMPT_ROOTS)

    def test_the_exempt_list_names_only_known_roots(self):
        roots = {path[0] for path in leaf_paths()}
        unknown = {p[0] for p in gate.EXEMPT} - roots - {"quarantine"}
        self.assertEqual(unknown, set())

    def test_a_command_added_later_is_gated_by_default(self):
        for path in (("brand-new",), ("store", "frobnicate"), ("authx",), ("quarantine", "purge")):
            self.assertFalse(gate.is_exempt(path), path)

    def test_quarantine_restore_is_exempt(self):
        self.assertTrue(gate.is_exempt(("quarantine", "restore")))

    def test_gate_mode_defaults_to_warn_and_reads_anything_else_as_enforce(self):
        import os
        import tempfile

        def mode_of(config):
            with tempfile.TemporaryDirectory() as tmp:
                path = os.path.join(tmp, "c.json")
                with open(path, "w") as handle:
                    json.dump(config, handle)
                return gate.gate_mode(path)

        self.assertEqual(mode_of({}), "warn")
        self.assertEqual(mode_of({"gate_mode": "warn"}), "warn")
        self.assertEqual(mode_of({"gate_mode": "enforce"}), "enforce")
        self.assertEqual(mode_of({"gate_mode": "off"}), "enforce")
        self.assertEqual(mode_of({"gate_mode": None}), "enforce")

    def test_the_shipped_config_starts_in_warn(self):
        self.assertEqual(gate.gate_mode(), "warn")


class GateBehaviourTest(AuthTestCase):
    def run_mode(self, mode, *argv):
        with mock.patch.object(gate, "gate_mode", return_value=mode):
            return self.run_inproc(list(argv))

    def test_enforce_blocks_a_gated_command_when_signed_out(self):
        for argv in (("list",), ("store", "list"), ("prefs", "list"), ("tasks", "list")):
            with self.subTest(argv=argv):
                code, out, _err = self.run_mode("enforce", *argv, "--json")
                body = json.loads(out)
                self.assertEqual(code, 1, body)
                self.assertFalse(body["ok"])
                self.assertEqual(body["entitled"], False)
                self.assertIn("devteam auth login", body["hint"])

    def test_enforce_human_message_names_the_remedy(self):
        code, _out, err = self.run_mode("enforce", "list")
        self.assertEqual(code, 1)
        self.assertIn("devteam list is blocked", err)
        self.assertIn("devteam auth login", err)

    def test_enforce_never_blocks_the_exempt_commands(self):
        for argv in (("version",), ("path",), ("compat",), ("auth", "status")):
            with self.subTest(argv=argv):
                code, _out, err = self.run_mode("enforce", *argv, "--json")
                self.assertEqual(code, 0, err)

    def test_warn_prints_one_stderr_line_and_proceeds(self):
        code, out, err = self.run_mode("warn", "list", "--json")
        self.assertEqual(code, 0, err)
        self.assertTrue(json.loads(out)["ok"])
        notice = [line for line in err.splitlines() if "devteam list" in line]
        self.assertEqual(len(notice), 1, err)
        self.assertIn("upcoming release", notice[0])

    def test_warn_leaves_the_json_document_untouched(self):
        _code, gated, _ = self.run_mode("warn", "list", "--json")
        self.signed_in = self.sign_in()
        _code, entitled, err = self.run_mode("warn", "list", "--json")
        self.assertEqual(json.loads(gated), json.loads(entitled))
        self.assertNotIn("upcoming release", err)

    def test_an_entitled_account_passes_in_both_modes(self):
        self.sign_in()
        for mode in ("warn", "enforce"):
            code, _out, err = self.run_mode(mode, "list", "--json")
            self.assertEqual(code, 0, err)
            self.assertNotIn("blocked", err)

    def test_the_cached_license_inside_its_offline_window_does_not_block(self):
        self.sign_in()
        self.idp.stop()
        before = len(self.idp.calls)
        code, _out, err = self.run_mode("enforce", "list", "--json")
        self.assertEqual(code, 0, err)
        self.assertEqual(len(self.idp.calls), before)

    def test_an_online_check_that_cannot_be_made_blocks_in_enforce_with_exit_3(self):
        view = {"entitlement": {"reason": "expired", "status": "needs_online_check"}}
        refusal = auth.EntitlementRefusal(3, "an online license check is required", "Connect.", view)
        with mock.patch.object(auth, "cmd_check", side_effect=refusal):
            code, out, _err = self.run_mode("enforce", "list", "--json")
        self.assertEqual(code, 3)
        self.assertFalse(json.loads(out)["ok"])
        with mock.patch.object(auth, "cmd_check", side_effect=refusal):
            code, _out, err = self.run_mode("warn", "list", "--json")
        self.assertEqual(code, 0, err)

    def test_the_core_self_update_stays_allowed_but_withholds_the_project_sync(self):
        view = {"entitlement": {"reason": "no_session", "status": "signed_out"}}
        refusal = auth.EntitlementRefusal(1, "you are not signed in", "Run `devteam auth login`.", view)
        args = argparse.Namespace(no_sync=False)
        emitter = Emitter(as_json=True, stdout=io.StringIO(), stderr=io.StringIO())
        with mock.patch.object(auth, "cmd_check", side_effect=refusal):
            with mock.patch.object(gate, "gate_mode", return_value="enforce"):
                gate.apply(("update",), args, emitter)
                self.assertTrue(args.no_sync)
                for blocked in (("sync",), ("bind",), ("upgrade",)):
                    with self.assertRaises(auth.EntitlementRefusal, msg=blocked):
                        gate.apply(blocked, argparse.Namespace(), emitter)


class BannerLineTest(AuthTestCase):
    def test_signed_out(self):
        self.assertIn("signed out", gate.banner_line())

    def test_signed_in_reads_the_cache_without_the_network(self):
        self.sign_in()
        before = len(self.idp.calls)
        self.idp.stop()
        line = gate.banner_line()
        self.assertTrue(line.startswith(("signed in", "trial ends in")), line)
        self.assertEqual(len(self.idp.calls), before)

    def test_it_never_raises(self):
        with mock.patch.object(entitlement, "load_identity", side_effect=RuntimeError("boom")):
            self.assertEqual(gate.banner_line(), "")


class ReadOnlyGateTest(unittest.TestCase):
    """A gated read-only command with no session must create nothing under DEVTEAM_HOME."""

    def test_gated_read_only_commands_leave_the_store_empty(self):
        import os
        import subprocess
        import tempfile

        cli_path = Path(__file__).resolve().parent.parent / "scripts" / "cli" / "devteam"
        for command in (["list"], ["catalog", "summary"]):
            with self.subTest(command=" ".join(command)), tempfile.TemporaryDirectory() as home:
                env = {k: v for k, v in os.environ.items() if not k.startswith("DEVTEAM_")}
                env["DEVTEAM_HOME"] = home
                subprocess.run(
                    [sys.executable, str(cli_path), *command, "--json"],
                    env=env, capture_output=True, check=False, timeout=60,
                )
                self.assertEqual(list(Path(home).rglob("*")), [])


if __name__ == "__main__":
    unittest.main()
