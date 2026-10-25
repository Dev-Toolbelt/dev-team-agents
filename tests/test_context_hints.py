"""The context-hints channel (ADR-0048): a per-session queue drained by the next prompt.

`scripts/hooks/lib/context-hints.sh` is sourced by hooks that raise a hint and by
`05-recall.sh` that drains it. These tests run it in bash against a throwaway git repository
and a scratch state directory, never the developer's own.
"""

import subprocess
import unittest

from devteam_support import REPO_ROOT, StoreTestCase, make_git_project, requires_bash

from devteam import providers

LIB = REPO_ROOT / "scripts" / "hooks" / "lib" / "context-hints.sh"
PLUGIN = REPO_ROOT / "opencode" / "plugin" / "dev-team-agents.ts"

#: How a hint line reaches the model on each provider. `stdout`: the UserPromptSubmit hook's
#: output is added to the context. `plugin`: opencode drops chat.message output, so the plugin
#: captures the prefixed lines and pushes them in experimental.chat.system.transform.
#: Fails when a provider is added without a case.
HINT_DELIVERY = {"claude": "stdout", "codex": "stdout", "opencode": "plugin"}


@requires_bash()
class ContextHintsTest(StoreTestCase):
    def setUp(self):
        super().setUp()
        self.repo = make_git_project(self.tmp / "app")
        self.state = self.tmp / "state"
        self.state.mkdir()

    def sh(self, body):
        script = '. "{}"; devteam_hints_init || exit 9; {}'.format(LIB, body)
        env = {"PATH": __import__("os").environ["PATH"], "HOME": str(self.tmp), "USER_DATA_DIR": str(self.state)}
        result = subprocess.run(["bash", "-c", script], cwd=str(self.repo), env=env, capture_output=True, text=True)
        return result.returncode, result.stdout

    def queue(self, session="s1"):
        return self.state / ".context-hints-{}".format(session)

    def test_every_provider_has_a_delivery_case(self):
        self.assertEqual(set(HINT_DELIVERY), set(providers.ALL_PROVIDERS))

    def test_opencode_plugin_forwards_both_prefixes_to_the_system_prompt(self):
        source = PLUGIN.read_text(encoding="utf-8")
        for provider in providers.ALL_PROVIDERS:
            if HINT_DELIVERY[provider] != "plugin":
                continue
            with self.subTest(provider=provider):
                self.assertIn('startsWith("[DEVTEAM:RECALL]")', source)
                self.assertIn('startsWith("[DEVTEAM:HINT]")', source)
                self.assertIn("output.system.push(CONTEXT_FRAMING, ...lines)", source)

    def test_session_id_accepts_safe_ids_and_rejects_unsafe_ones(self):
        cases = {
            '{"session_id":"abc-123"}': "abc-123",
            '{"sessionId": "A.b_c"}': "A.b_c",
            '{"prompt":"x"}': "",
            '{"session_id":"../etc"}': "",
            '{"session_id":""}': "",
        }
        for payload, expected in cases.items():
            with self.subTest(payload=payload):
                code, out = self.sh("devteam_hints_session_id '{}'".format(payload))
                self.assertEqual((code, out), (0, expected))

    def test_enqueue_then_drain_prints_the_line_and_empties_the_queue(self):  # [spec:prompt-recall#S14]
        self.sh("devteam_hints_enqueue s1 'first hint'; devteam_hints_enqueue s1 'second hint'")
        self.assertEqual(self.queue().read_text().splitlines(), ["first hint", "second hint"])
        code, out = self.sh("devteam_hints_drain s1")
        self.assertEqual((code, out), (0, "first hint\nsecond hint\n"))
        self.assertFalse(self.queue().exists())

    def test_duplicate_lines_are_queued_once(self):
        self.sh("devteam_hints_enqueue s1 same; devteam_hints_enqueue s1 same")
        self.assertEqual(self.queue().read_text().splitlines(), ["same"])

    def test_a_delivered_hint_is_never_queued_again_in_that_session(self):  # [spec:prompt-recall#S6]
        self.sh("devteam_hints_enqueue s1 once; devteam_hints_drain s1")
        self.sh("devteam_hints_enqueue s1 once")
        self.assertFalse(self.queue().exists())
        self.sh("devteam_hints_enqueue s2 once")
        self.assertEqual(self.queue("s2").read_text().splitlines(), ["once"])

    def test_drain_respects_the_line_cap_and_leaves_the_rest_queued(self):  # [spec:prompt-recall#S5] [spec:prompt-recall#S14]
        self.sh("for i in 1 2 3 4 5 6 7; do devteam_hints_enqueue s1 \"line $i\"; done")
        code, out = self.sh("devteam_hints_drain s1")
        self.assertEqual(out.splitlines(), ["line {}".format(i) for i in range(1, 6)])
        self.assertEqual(self.queue().read_text().splitlines(), ["line 6", "line 7"])

    def test_drain_respects_the_character_cap(self):
        self.sh("devteam_hints_enqueue s1 aaaaaaaaaa; devteam_hints_enqueue s1 bbbbbbbbbb")
        code, out = self.sh("devteam_hints_drain s1 5 15")
        self.assertEqual(out, "aaaaaaaaaa\n")
        self.assertEqual(self.queue().read_text().splitlines(), ["bbbbbbbbbb"])

    def test_default_caps_are_five_lines_and_1200_characters(self):
        code, out = self.sh('echo "$DEVTEAM_HINTS_MAX_LINES $DEVTEAM_HINTS_MAX_CHARS"')
        self.assertEqual(out.strip(), "5 1200")

    def test_lines_are_cleaned_and_bounded(self):
        self.sh("devteam_hints_enqueue s1 $'bad\\x01line\\x1b[31m'; devteam_hints_enqueue s1 \"$(printf 'x%.0s' $(seq 1 400))\"")
        lines = self.queue().read_text().splitlines()
        self.assertEqual(lines[0], "badline[31m")
        self.assertEqual(len(lines[1]), 300)

    def test_invisible_format_characters_are_stripped(self):
        line = "a\u202eb\u200bc\ufeffd\u2028e\u2066f\u00adg\u0085h\u00e9\u2014i"
        self.sh("devteam_hints_enqueue s1 '{}'".format(line))
        self.assertEqual(self.queue().read_text().splitlines(), ["abcdefgh\u00e9\u2014i"])

    def test_no_session_means_no_queue(self):
        code, out = self.sh("devteam_hints_enqueue '' hint; devteam_hints_drain ''")
        self.assertEqual((code, out), (0, ""))
        self.assertEqual([p.name for p in self.state.iterdir()], [])

    def test_a_symlinked_queue_is_never_followed(self):
        target = self.tmp / "elsewhere"
        target.write_text("planted\n")
        self.queue().symlink_to(target)
        self.sh("devteam_hints_enqueue s1 hint")
        self.assertEqual(target.read_text(), "planted\n")
        code, out = self.sh("devteam_hints_drain s1")
        self.assertEqual((code, out), (0, ""))

    def test_drain_of_an_empty_queue_prints_nothing(self):
        self.assertEqual(self.sh("devteam_hints_drain s1"), (0, ""))

    def test_the_queue_and_shown_records_are_machine_local(self):
        from devteam import paths
        self.assertTrue(paths.is_machine_local_record(".context-hints-s1"))
        self.assertTrue(paths.is_machine_local_record(".context-shown-s1"))


if __name__ == "__main__":
    unittest.main()
