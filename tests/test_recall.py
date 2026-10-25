"""Prompt recall (ADR-0048, docs/specs/prompt-recall.md).

`scripts/lib/recall.py` matches a prompt against the ADR, wiki and reuse indexes;
`scripts/hooks/user-prompt-submit/05-recall.sh` gates it, delivers the lines and drains queued
hints. Both run for real against a throwaway git repository and scratch state directory.
"""

import json
import os
import stat
import subprocess
import sys
import unittest

from devteam_support import REPO_ROOT, StoreTestCase, make_git_project, requires_bash

from devteam import providers

RECALL = REPO_ROOT / "scripts" / "lib" / "recall.py"
HOOK = REPO_ROOT / "scripts" / "hooks" / "user-prompt-submit" / "05-recall.sh"
DISPATCHER = REPO_ROOT / "scripts" / "hooks" / "user-prompt-submit.sh"
PLUGIN = REPO_ROOT / "opencode" / "plugin" / "dev-team-agents.ts"
DEFAULTS = REPO_ROOT / "scripts" / "lib" / "preferences-defaults.json"
HINTS = REPO_ROOT / "scripts" / "hooks" / "lib" / "context-hints.sh"

#: How the recall lines reach the model on each provider (spec S11-S13). Fails when a provider
#: is added without a case.
DELIVERY = {"claude": "hook-stdout", "codex": "hook-stdout", "opencode": "plugin-system-transform"}

ADR_INDEX = "# ADRs\n\n## Index\n\n| ADR | Status | Keywords | Read it when |\n|---|---|---|---|\n{rows}"
WIKI_INDEX = "# Wiki\n\n| Entry | Keywords | Read it when |\n|---|---|---|\n{rows}"
REUSE_HEADER = "| name | type | rule | detection | canonical_ref | scope | severity | added |\n|---|---|---|---|---|---|---|---|\n"
PROMPT = "please fix the webhook retries for the billing queue"


def adr_row(name, status, keywords, when):
    return "| `{}` | {} | {} | {} |\n".format(name, status, keywords, when)


class _Recall(StoreTestCase):
    def setUp(self):
        super().setUp()
        self.repo = make_git_project(self.tmp / "app")
        self.state = self.tmp / "state"
        self.state.mkdir()
        self.shown = self.tmp / "shown"

    def write(self, rel, text):
        path = self.repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def adrs(self, *rows):
        self.write("docs/development/adrs/README.md", ADR_INDEX.format(rows="".join(rows)))

    def wiki(self, *rows):
        self.write("docs/wiki/README.md", WIKI_INDEX.format(rows="".join(rows)))

    def reuse(self, *rows):
        self.write("docs/development/reuse-guidelines.md", REUSE_HEADER + "".join(r + "\n" for r in rows))

    def recall(self, prompt, shown=None, max_lines=5, max_chars=1200, raw=None):
        stdin = raw if raw is not None else json.dumps(prompt) + "}"
        result = subprocess.run(
            [sys.executable, "-I", str(RECALL), str(self.repo), str(shown or "-"), str(max_lines), str(max_chars)],
            input=stdin, capture_output=True, text=True,
        )
        return result.returncode, result.stdout, result.stderr


class RecallMatchingTest(_Recall):
    def test_a_relevant_accepted_adr_is_pointed_out_without_its_body(self):  # [spec:prompt-recall#S1]
        self.adrs(adr_row("0007-queue-policy.md", "Accepted", "webhook, retry", "changing delivery or retry behavior"))
        self.write("docs/development/adrs/0007-queue-policy.md", "# ADR\nSECRET BODY TEXT\n")
        code, out, err = self.recall(PROMPT)
        self.assertEqual(code, 0)
        self.assertEqual(
            out.splitlines(),
            ["[DEVTEAM:RECALL] docs/development/adrs/0007-queue-policy.md (ADR) — changing delivery or retry behavior"],
        )
        self.assertNotIn("SECRET", out)

    def test_an_entry_sharing_one_keyword_outside_its_title_is_not_delivered(self):  # [spec:prompt-recall#S2]
        self.adrs(adr_row("0001-payment-gateway.md", "Accepted", "webhook, retry", "payments"))
        self.assertEqual(self.recall("look at the webhook payload shape please")[1], "")

    def test_one_keyword_found_in_the_title_is_enough(self):  # [spec:prompt-recall#S2]
        self.adrs(adr_row("0001-webhook-signing.md", "Accepted", "webhook, hmac", "signing webhooks"))
        out = self.recall("look at the webhook payload shape please")[1]
        self.assertIn("0001-webhook-signing.md", out)

    def test_only_accepted_adrs_are_recalled(self):  # [spec:prompt-recall#S3]
        for status in ("Proposed", "Superseded", "Deprecated", "Rejected"):
            with self.subTest(status=status):
                self.adrs(adr_row("0007-queue-policy.md", status, "webhook, retry", "x"))
                self.assertEqual(self.recall(PROMPT)[1], "")

    def test_wiki_and_reuse_rows_are_recalled_strongest_first(self):  # [spec:prompt-recall#S4]
        self.wiki("| `orders/billing-queue.md` | billing, queue, webhook | Touching the billing queue |\n")
        self.reuse("| retry-helper | design-rule | Use the helper | | src/retry.ts | | | |")
        lines = self.recall(PROMPT)[1].splitlines()
        self.assertEqual(len(lines), 2)
        self.assertIn("docs/wiki/orders/billing-queue.md (wiki)", lines[0])
        self.assertIn("docs/development/reuse-guidelines.md#retry-helper (reuse rule)", lines[1])

    def test_at_most_five_lines_within_the_character_budget(self):  # [spec:prompt-recall#S5]
        rows = "".join(
            adr_row("{:04d}-queue-{}.md".format(i, i), "Accepted", "webhook, retry", "x" * 150) for i in range(1, 9)
        )
        self.adrs(rows)
        out = self.recall(PROMPT)[1]
        self.assertEqual(len(out.splitlines()), 5)
        self.assertLessEqual(len(out), 1200)

    def test_the_character_cap_can_cut_before_the_line_cap(self):  # [spec:prompt-recall#S5]
        rows = "".join(adr_row("{:04d}-queue.md".format(i), "Accepted", "webhook, retry", "y" * 150) for i in range(1, 5))
        self.adrs(rows)
        out = self.recall(PROMPT, max_chars=400)[1]
        self.assertLessEqual(len(out), 400)
        self.assertGreaterEqual(len(out.splitlines()), 1)

    def test_a_pointer_is_delivered_once_per_shown_file(self):  # [spec:prompt-recall#S6]
        self.adrs(adr_row("0007-queue-policy.md", "Accepted", "webhook, retry", "x"))
        first = self.recall(PROMPT, shown=self.shown)[1]
        self.assertNotEqual(first, "")
        self.assertEqual(self.recall(PROMPT, shown=self.shown)[1], "")
        self.assertEqual(self.recall(PROMPT, shown=self.tmp / "other-session")[1], first)

    def test_a_short_prompt_prints_nothing(self):  # [spec:prompt-recall#S7]
        self.adrs(adr_row("0007-webhook-retry.md", "Accepted", "webhook, retry", "x"))
        self.assertNotEqual(self.recall("webhook retry!")[1], "")
        self.assertEqual(self.recall("webhook")[1], "")
        self.assertEqual(self.recall("go on")[1], "")

    def test_a_project_with_no_index_prints_nothing(self):  # [spec:prompt-recall#S9]
        self.assertEqual(self.recall(PROMPT), (0, "", ""))

    def test_malformed_input_fails_open(self):  # [spec:prompt-recall#S10]
        self.adrs("| garbage \x00 |||\n| `broken | Accepted\n")
        for raw in ("", "no quote at all", '"unterminated \\', '"\\ud800 bad escape "'):
            with self.subTest(raw=raw):
                code, out, err = self.recall(None, raw=raw)
                self.assertEqual((code, err), (0, ""))

    def test_control_characters_never_reach_the_output(self):  # [spec:prompt-recall#S10]
        self.adrs(adr_row("0007-queue-policy.md", "Accepted", "webhook, retry", "do\x1b[31m this"))
        out = self.recall(PROMPT)[1]
        self.assertNotIn("\x1b", out)

    def test_invisible_format_characters_never_reach_the_output(self):  # [spec:prompt-recall#S10]
        self.adrs(adr_row("0007-queue-policy.md", "Accepted", "webhook, retry", "do\u202e this\u200b now\ufeff!"))
        out = self.recall(PROMPT)[1]
        for ch in ("\u202e", "\u200b", "\ufeff"):
            self.assertNotIn(ch, out)
        self.assertIn("do this now!", out)

    def test_the_recall_adds_little_time(self):  # [spec:prompt-recall#S15]
        import time
        self.adrs("".join(adr_row("{:04d}-queue-{}.md".format(i, i), "Accepted", "webhook, retry", "x") for i in range(1, 60)))
        start = time.monotonic()
        self.recall(PROMPT)
        self.assertLess(time.monotonic() - start, 2.0)  # generous: includes interpreter start-up on CI


@requires_bash()
class RecallHookTest(_Recall):
    def prefs(self, **values):
        self.write(".dev-team-agents/resolved/preferences.json", json.dumps(values))

    def hook(self, prompt, session="sess-1", stub_python=None):
        payload = json.dumps({"session_id": session, "prompt": prompt})
        env = {"PATH": os.environ["PATH"], "HOME": str(self.tmp), "USER_DATA_DIR": str(self.state)}
        if stub_python:
            env["PATH"] = str(stub_python) + os.pathsep + env["PATH"]
        result = subprocess.run(["bash", str(HOOK)], input=payload, cwd=str(self.repo), env=env, capture_output=True, text=True)
        return result.returncode, result.stdout, result.stderr

    def enqueue(self, session, *lines):
        script = '. "{}"; devteam_hints_init; {}'.format(
            HINTS, "; ".join("devteam_hints_enqueue {} '{}'".format(session, l) for l in lines))
        env = {"PATH": os.environ["PATH"], "HOME": str(self.tmp), "USER_DATA_DIR": str(self.state)}
        subprocess.run(["bash", "-c", script], cwd=str(self.repo), env=env, check=True)

    def indexed(self):
        self.adrs(adr_row("0007-queue-policy.md", "Accepted", "webhook, retry", "changing delivery or retry behavior"))

    def test_every_provider_has_a_delivery_case(self):
        self.assertEqual(set(DELIVERY), set(providers.ALL_PROVIDERS))

    def test_delivery_on_every_provider(self):  # [spec:prompt-recall#S11] [spec:prompt-recall#S12] [spec:prompt-recall#S13]
        self.indexed()
        source = PLUGIN.read_text(encoding="utf-8")
        code, out, _ = self.hook(PROMPT)
        self.assertEqual(code, 0)
        self.assertTrue(out.startswith("[DEVTEAM:RECALL] docs/development/adrs/0007-queue-policy.md"))
        for provider in providers.ALL_PROVIDERS:
            with self.subTest(provider=provider):
                if DELIVERY[provider] == "hook-stdout":
                    self.assertIn("[DEVTEAM:RECALL]", out)
                else:
                    self.assertEqual(DELIVERY[provider], "plugin-system-transform")
                    self.assertIn('l.startsWith("[DEVTEAM:RECALL]") || l.startsWith("[DEVTEAM:HINT]")', source)
                    self.assertIn('"experimental.chat.system.transform"', source)
                    self.assertIn("output.system.push(CONTEXT_FRAMING, ...lines)", source)

    def test_the_dispatcher_runs_the_recall_script(self):  # [spec:prompt-recall#S11]
        self.indexed()
        env = {"PATH": os.environ["PATH"], "HOME": str(self.tmp), "USER_DATA_DIR": str(self.state)}
        payload = json.dumps({"session_id": "d1", "prompt": PROMPT})
        result = subprocess.run(["bash", str(DISPATCHER)], input=payload, cwd=str(self.repo), env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("[DEVTEAM:RECALL]", result.stdout)

    def test_each_pointer_is_delivered_once_per_session(self):  # [spec:prompt-recall#S6]
        self.indexed()
        self.assertIn("RECALL", self.hook(PROMPT, session="a")[1])
        self.assertEqual(self.hook(PROMPT, session="a")[1], "")
        self.assertIn("RECALL", self.hook(PROMPT, session="b")[1])

    def test_a_short_prompt_never_starts_an_interpreter(self):  # [spec:prompt-recall#S7]
        self.indexed()
        stub = self.tmp / "bin"
        stub.mkdir()
        marker = self.tmp / "python-started"
        fake = stub / "python3"
        fake.write_text('#!/bin/sh\ntouch "{}"\nexit 0\n'.format(marker))
        fake.chmod(fake.stat().st_mode | stat.S_IXUSR)
        for prompt in ("yes", "go on", "ok thanks"):
            with self.subTest(prompt=prompt):
                self.assertEqual(self.hook(prompt, stub_python=stub)[:2], (0, ""))
                self.assertFalse(marker.exists())
        self.hook(PROMPT, stub_python=stub)
        self.assertTrue(marker.exists(), "the stub must be what a long prompt reaches, or this test proves nothing")

    def test_recall_active_false_silences_recall_but_hints_still_drain(self):  # [spec:prompt-recall#S8] [spec:prompt-recall#S14]
        self.indexed()
        self.prefs(recall_active=False)
        self.enqueue("sess-1", "queued by another hook")
        code, out, _ = self.hook(PROMPT)
        self.assertEqual(code, 0)
        self.assertEqual(out, "[DEVTEAM:HINT] queued by another hook\n")

    def test_recall_active_true_or_absent_delivers(self):  # [spec:prompt-recall#S8]
        self.indexed()
        self.assertIn("RECALL", self.hook(PROMPT)[1])
        self.prefs(recall_active=True)
        self.assertIn("RECALL", self.hook(PROMPT, session="other")[1])

    def test_no_index_no_interpreter(self):  # [spec:prompt-recall#S9]
        stub = self.tmp / "bin"
        stub.mkdir()
        marker = self.tmp / "python-started"
        fake = stub / "python3"
        fake.write_text('#!/bin/sh\ntouch "{}"\n'.format(marker))
        fake.chmod(fake.stat().st_mode | stat.S_IXUSR)
        self.assertEqual(self.hook(PROMPT, stub_python=stub)[:2], (0, ""))
        self.assertFalse(marker.exists())

    def test_fail_open_on_a_broken_state_dir_and_a_malformed_index(self):  # [spec:prompt-recall#S10]
        self.write("docs/development/adrs/README.md", "\x00\x01 not a table | | |\n| `x | Accepted\n")
        blocker = self.tmp / "state-is-a-file"
        blocker.write_text("x")
        self.state = blocker
        code, out, err = self.hook(PROMPT)
        self.assertEqual(code, 0)
        self.assertNotIn("Traceback", out + err)
        self.assertNotIn("Error", out)

    def test_queued_hints_drain_after_recall_within_the_shared_cap(self):  # [spec:prompt-recall#S14] [spec:prompt-recall#S5]
        self.indexed()
        self.enqueue("sess-1", "h1", "h2", "h3", "h4", "h5")
        lines = self.hook(PROMPT)[1].splitlines()
        self.assertEqual(len(lines), 5)
        self.assertTrue(lines[0].startswith("[DEVTEAM:RECALL]"))
        self.assertEqual(lines[1:], ["[DEVTEAM:HINT] h1", "[DEVTEAM:HINT] h2", "[DEVTEAM:HINT] h3", "[DEVTEAM:HINT] h4"])
        rest = self.hook("another long enough prompt here", session="sess-1")[1].splitlines()
        self.assertEqual(rest, ["[DEVTEAM:HINT] h5"])
        self.assertEqual(self.hook("yet another long enough prompt", session="sess-1")[1], "")

    def test_hint_drain_ignores_the_short_prompt_gate(self):  # [spec:prompt-recall#S14]
        self.enqueue("sess-1", "pending")
        self.assertEqual(self.hook("ok")[1], "[DEVTEAM:HINT] pending\n")


class PreferenceDefaultsTest(unittest.TestCase):
    def test_the_four_context_delivery_keys_default_to_true(self):
        defaults = json.loads(DEFAULTS.read_text(encoding="utf-8"))
        for key in ("recall_active", "check_active", "repair_hints_active", "branch_overlap_active"):
            with self.subTest(key=key):
                self.assertIs(defaults[key], True)


if __name__ == "__main__":
    unittest.main()
