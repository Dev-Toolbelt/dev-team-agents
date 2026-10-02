"""The session's own work is one "Direct work" card (docs/specs/task-board.md § Direct work).

Work the main session does itself — an edit tool, a write-shaped shell command — with no plan
step and no agent covering it lands on one card per session. These tests pin it on every
provider: what counts, what is covered elsewhere and suppressed, the turn excerpt and its
redaction, the Stop that completes the card, and the gate that keeps python off the hot path.
"""

import json
import os
import unittest

from devteam_support import requires_bash

from devteam import providers, tasks

import test_tasks as tt
from test_tasks import PRE_TOOL_USE, STOP_SUB, T0, BoardCase, todo, todo_write

USER_PROMPT = PRE_TOOL_USE.parent.parent / "user-prompt-submit" / "01-task-board.sh"


def claude_edit(session, **extra):
    return dict({"session_id": session, "tool_name": "Edit", "tool_input": {"file_path": "a.py"}}, **extra)


def claude_shell(session, command, **extra):
    return dict({"session_id": session, "tool_name": "Bash", "tool_input": {"command": command}}, **extra)


def codex_edit(session, **extra):
    return dict({"session_id": session, "turn_id": "turn-1", "tool_name": "apply_patch",
                 "tool_input": {"input": "*** Begin Patch"}}, **extra)


def codex_shell(session, command, **extra):
    return dict({"session_id": session, "turn_id": "turn-1", "tool_name": "Bash",
                 "tool_input": {"command": command}}, **extra)


def claude_read(session, **extra):
    return dict({"session_id": session, "tool_name": "Read", "tool_input": {"file_path": "a.py"}}, **extra)


def codex_read(session, **extra):
    return dict({"session_id": session, "turn_id": "turn-1", "tool_name": "mcp__docs__search",
                 "tool_input": {"q": "x"}}, **extra)


def opencode_read(session, **extra):
    return dict({"sessionID": session, "tool": "read", "args": {"filePath": "a.py"}}, **extra)


def opencode_edit(session, **extra):
    return dict({"sessionID": session, "tool": "edit", "args": {"filePath": "a.py"}}, **extra)


def opencode_shell(session, command, **extra):
    return dict({"sessionID": session, "tool": "bash", "args": {"command": command}}, **extra)


#: One (edit, shell, read) triple per provider in `providers.ALL_PROVIDERS`: a provider added
#: without a case fails `test_every_provider_has_its_direct_capture_decided`.
CALLS = {
    "claude": (claude_edit, claude_shell, claude_read),
    "codex": (codex_edit, codex_shell, codex_read),
    "opencode": (opencode_edit, opencode_shell, opencode_read),
}


class ParityTest(unittest.TestCase):
    def test_every_provider_has_its_direct_capture_decided(self):
        self.assertEqual(set(CALLS), set(providers.ALL_PROVIDERS))
        self.assertEqual(set(tasks._DIRECT_EDIT_TOOLS), set(providers.ALL_PROVIDERS))
        self.assertEqual(set(tasks._DIRECT_SHELL_TOOLS), set(providers.ALL_PROVIDERS))


#: Shell commands `tasks.writes()` must accept; the bash gate must let every one through.
WRITE_COMMANDS = (
    "git commit -m 'x'", "rtk git push", "git -C /x commit -m y", 'git -C "/a b" commit', "echo hi > out.txt",
    "echo a >> log", "cmd 2> err.log", "sed -i '' s/a/b/ f", "perl -pi -e s/a/b/ f", "npm install", "npm i x",
    "go get x", "cat a | tee b", "FOO=1 rm -rf x", "python3 -m pip install x", "mkdir -p d && ls",
    "echo hi\nmkdir foo", "bash -lc 'git commit -m x'", "bash -lc 'mv a b && echo ok'",
    # Remote, container, cluster and service changes.
    "ssh jornalimpactopress-vps 'docker rm -f jornalimpactocotia-wpcli-run-15ef08b9b9e8'",
    "ssh -o ConnectTimeout=10 -p 22 host 'rm -f /tmp/a'", "ssh host docker exec c wp cache flush",
    "bash -lc 'ssh host \"docker restart c\"'", "docker rm -f x", "docker compose up -d",
    "docker compose -f a.yml restart web", "docker-compose down", "docker container prune -f", "podman run x",
    "kubectl apply -f a.yml", "kubectl -n prod rollout restart deploy/x", "helm upgrade x chart",
    "systemctl restart nginx", "sudo systemctl reload nginx", "service nginx restart", "scp a host:/b",
    "rsync -a a host:b",
)
#: Read-only shapes common enough that the bash gate must not fork python for them either.
READ_COMMANDS = (
    "ls -la", "grep -r foo . 2>/dev/null", "git status", "git log --oneline -5", "git -c a=b diff", "npm test",
    "cmd 2>&1", "cmd 2>&1 | head", "cat f > /dev/null", "sed -n 1,5p f", "git log --grep=reset", "pytest -k update",
    "ssh host 'docker ps'", "ssh -i key host", "ssh -o ConnectTimeout=10 host 'docker ps -a --filter name=cotia'",
    "docker ps -a", "docker logs -f x", "docker inspect x", "docker compose ps", "docker compose logs web",
    "docker image ls", "kubectl get pods", "kubectl -n x describe pod y", "kubectl rollout status deploy/x",
    "helm list", "systemctl status nginx", "service nginx status",
)


class WritesTest(unittest.TestCase):
    def test_write_shaped_commands(self):
        for command in WRITE_COMMANDS + (["bash", "-lc", "touch f"], ["bash", "-lc", "mv a b && echo done"]):
            self.assertTrue(tasks.writes(command), command)

    def test_read_only_commands(self):
        # Operators and `>` inside quotes are words, never a split or a redirect.
        for command in READ_COMMANDS + ("grep -rn '=>' src", "jq '.a > 1' f.json", "echo 'a; rm x'", "", None, 42):
            self.assertFalse(tasks.writes(command), command)


class RedactTest(unittest.TestCase):
    def test_secret_shapes_are_masked(self):
        cases = {
            "use sk-abc123456789xyz": "sk-abc123456789xyz",
            "API_KEY=hunter2": "hunter2",
            "ghp_aaaaaaaaaaaa": "ghp_aaaaaaaaaaaa",
            "sk_live_51Habcdefgh": "sk_live_51Habcdefgh",
            '{"password": "hunter2xyz"}': "hunter2xyz",
            "Authorization: Bearer abcDEF123456": "abcDEF123456",
            "postgres://admin:S3cretPw@db/x": "S3cretPw",
            "AIzaSyA1234567890abcdefghijklmnopqrstu": "AIzaSyA1234567890",
            "aws_secret_access_key wJalrXUtnFEMI": "wJalrXUtnFEMI",
            "PASS=abc123": "abc123",
            "senha: xyz123": "xyz123",
            "my password is hunter2xyz": "hunter2xyz",
            "key 4f8a9b2c7d1e6f3a5b8c9d0e1f2a3b4c5d6e7f8a9b0aa": "4f8a9b2c7d1e6f3a5b8c9d0e1f2a3b4c5d6e7f8a9b0aa",
            "curl -H 'Authorization: Basic dXNlcjpwYXNzd29yZA=='": "dXNlcjpwYXNzd29yZA",
            "Authorization: token abcdef123": "abcdef123",
            "curl -H 'X-Api-Key: 9f8e7d6c' https://x": "9f8e7d6c",
            "mysql -uroot -pS3cretPass1 app": "S3cretPass1",
        }
        for text, secret in cases.items():
            self.assertNotIn(secret, tasks.redact(text), text)
        self.assertEqual(tasks.redact("API_KEY=hunter2"), "API_KEY=[redacted]")

    def test_ordinary_text_is_left_alone(self):
        for text in (
            "edit scripts/hooks/pre-tool-use/04-task-board.sh now",
            "the cache key: abc",
            "revert a1b2c3d4e5f6a7b8c9d0a1b2c3d4e5f6a7b8c9d0 please",
        ):
            self.assertEqual(tasks.redact(text), text)

    def test_every_task_text_is_redacted_and_cleaned_like_the_excerpt(self):
        spawn = {"session_id": "s1", "tool_name": "Agent", "hook_event_name": "PreToolUse",
                 "tool_input": {"subagent_type": "backend-developer", "description": "deploy with GITHUB_TOKEN=ghp_abcdefghijklmnop1234"}}
        texts = [tasks.normalize(spawn, "claude")["op"][1]["content"], tasks._task_text("ship it API_KEY=hunter2\u202e")]
        for text in texts:
            self.assertIn("[redacted]", text)
            self.assertNotIn("ghp_abcdefghijklmnop1234", text)
            self.assertNotIn("hunter2", text)
            self.assertNotIn("\u202e", text)

    def test_invisible_characters_are_dropped_from_the_excerpt(self):
        self.assertEqual(tasks._excerpt("abc\u202edef\u200b ghi"), "abc def ghi")

    def test_the_excerpt_is_the_first_line_decoded_and_cut(self):
        raw = ': "corrige o bug \\u00e9\\nsegunda linha"'
        self.assertEqual(tasks._excerpt(tasks._decode_prompt(raw)), "corrige o bug é")
        self.assertEqual(tasks._decode_prompt(': "cut mid escape \\u00'), "cut mid escape ")
        long = tasks._excerpt("x " * 200)
        self.assertEqual(len(long), tasks.DIRECT_EXCERPT)


class DirectWorkTest(BoardCase):
    def directs(self, session):
        return [t for t in self.load(session)["tasks"] if t.get("kind") == "direct"]

    def prompt(self, session, text, at):
        path = tasks.record_path(self.root, self.project_id, session)
        path.parent.mkdir(parents=True, exist_ok=True)
        prompt = tasks._prompt_path(path)
        prompt.write_text(': ' + json.dumps(text) + ', "x": 1}', encoding="utf-8")
        os.utime(str(prompt), (at, at))
        tasks.direct_marker(path).unlink(missing_ok=True)

    def test_an_edit_and_a_write_shaped_shell_call_open_one_card_on_every_provider(self):
        for provider in providers.ALL_PROVIDERS:
            with self.subTest(provider=provider):
                edit, shell, _ = CALLS[provider]
                session = "d-" + provider
                self.prompt(session, "fix the login bug", T0)
                self.assertTrue(self.rec(edit(session), now=T0 + 1)["recorded"])
                self.assertTrue(self.rec(shell(session, "git commit -m x"), now=T0 + 2)["recorded"])
                (card,) = self.directs(session)
                self.assertEqual((card["content"], card["status"], card["owner"]), ("Direct work", "in_progress", "main"))
                self.assertEqual(card["turns"], [{"text": "fix the login bug", "at": T0}])
                self.assertEqual(self.load(session)["provider"], provider)

    def test_a_read_only_turn_opens_the_card_in_to_do_on_every_provider(self):
        for provider in providers.ALL_PROVIDERS:
            with self.subTest(provider=provider):
                _, shell, read = CALLS[provider]
                session = "r-" + provider
                self.prompt(session, "are the containers healthy?", T0)
                self.assertTrue(self.rec(shell(session, "git status"), now=T0 + 1)["recorded"])
                self.assertTrue(self.rec(read(session), now=T0 + 2)["recorded"])
                (card,) = self.directs(session)
                self.assertEqual(card["status"], "pending")
                self.assertEqual(card["turns"], [{"text": "are the containers healthy?", "at": T0}])
                tasks.mark(self.root, {"session_id": session, "sessionID": session}, "idle", now=T0 + 3)
                self.assertEqual(self.directs(session)[0]["status"], "pending")

    def test_a_write_promotes_the_card_and_a_later_read_never_demotes_it(self):
        self.prompt("s1", "check then fix", T0)
        self.rec(claude_read("s1"), now=T0 + 1)
        self.rec(claude_edit("s1"), now=T0 + 2)
        self.rec(claude_read("s1"), now=T0 + 3)
        (card,) = self.directs("s1")
        self.assertEqual([h["status"] for h in card["history"]], ["pending", "in_progress"])
        tasks.mark(self.root, {"session_id": "s1"}, "idle", now=T0 + 4)
        self.assertEqual(self.directs("s1")[0]["status"], "completed")
        # The card follows the latest turn: a question after the work is something to do again.
        self.prompt("s1", "and the logs?", T0 + 10)
        self.rec(claude_read("s1"), now=T0 + 11)
        (card,) = self.directs("s1")
        self.assertEqual(card["status"], "pending")
        self.assertEqual([t["text"] for t in card["turns"]], ["check then fix", "and the logs?"])

    def test_a_read_turn_covered_by_a_plan_retires_the_card_at_stop(self):
        self.prompt("s1", "plan the feature", T0)
        self.rec(claude_read("s1"), now=T0 + 1)
        self.rec(todo_write("s1", [todo("Step 1: A", "pending")]), now=T0 + 2)
        tasks.mark(self.root, {"session_id": "s1"}, "idle", now=T0 + 3)
        (card,) = self.directs("s1")
        self.assertEqual((card["status"], card["removed_at"]), ("pending", T0 + 3))
        self.assertNotIn("direct", [t["kind"] for t in self.view(now=T0 + 5)[0]["sessions"][0]["tasks"]])

    def test_a_card_left_in_to_do_is_not_abandoned_work(self):
        self.prompt("s1", "a question", T0)
        self.rec(claude_read("s1"), now=T0 + 1)
        result = tasks.mark(self.root, {"session_id": "s1"}, "ended", now=T0 + 2)
        self.assertEqual(result["open"], 0)
        (view,) = self.view(now=T0 + 5)[0]["sessions"][0]["tasks"]
        self.assertEqual((view["kind"], view["column"], view["abandoned"]), ("direct", "todo", False))

    def test_the_todo_tools_that_only_read_their_list_are_not_work(self):
        for payload in ({"session_id": "s1", "tool_name": "TaskList", "tool_input": {}},
                        {"sessionID": "s1", "tool": "todoread", "args": {}}):
            self.assertFalse(self.rec(payload)["recorded"], payload)

    def test_a_subagents_edit_is_its_agent_tasks_work(self):
        self.assertFalse(self.rec(claude_edit("s1", agent_id="a1"))["recorded"])
        self.assertFalse(self.rec(codex_edit("s2", agent_id="a1"))["recorded"])
        self.assertFalse(self.rec(opencode_edit("s3", parent_id="p1"))["recorded"])

    def test_an_in_progress_plan_step_covers_the_edit(self):
        self.rec(todo_write("s1", [todo("Step 1: do it", "in_progress")]), now=T0)
        self.rec(claude_edit("s1"), now=T0 + 1)
        self.assertEqual(self.directs("s1"), [])

    def test_an_agent_spawned_this_turn_covers_the_edit_but_not_one_from_an_earlier_turn(self):
        self.rec({"session_id": "s1", "tool_name": "Agent", "tool_use_id": "c1",
                  "tool_input": {"description": "d", "prompt": "p", "subagent_type": "backend-developer"}}, now=T0 + 5)
        self.prompt("s1", "first", T0)
        self.rec(claude_edit("s1"), now=T0 + 6)
        self.assertEqual(self.directs("s1"), [])
        self.prompt("s1", "second", T0 + 100)
        self.rec(claude_edit("s1"), now=T0 + 101)
        self.assertEqual([t["text"] for t in self.directs("s1")[0]["turns"]], ["second"])

    def test_a_plan_finished_in_a_turn_with_direct_work_still_notifies(self):
        self.rec(todo_write("s1", [todo("Step 1: do it", "in_progress")]), now=T0)
        self.prompt("s1", "wrap up", T0 + 5)
        tasks.mark(self.root, {"session_id": "s1"}, "idle", now=T0 + 6)
        self.rec(claude_edit("s1"), now=T0 + 10)  # a new turn, no step in progress yet... the step still is
        self.rec(todo_write("s1", [todo("Step 1: do it", "completed")]), now=T0 + 11)
        self.rec(claude_edit("s1"), now=T0 + 12)
        result = self.rec(todo_write("s1", [todo("Step 1: do it", "completed")]), now=T0 + 13)
        self.assertTrue(result["all_done"])
        # Same turn, the other order: direct work first, then the plan's last step.
        self.rec(todo_write("s2", [todo("Step 1: do it", "pending")]), now=T0)
        self.prompt("s2", "do it", T0 + 1)
        self.rec(claude_edit("s2"), now=T0 + 2)
        self.assertEqual(self.directs("s2")[0]["status"], "in_progress")
        finished = self.rec(todo_write("s2", [todo("Step 1: do it", "completed")]), now=T0 + 3)
        self.assertTrue(finished["became_all_done"])

    def test_without_a_prompt_file_the_work_continues_the_last_turn(self):
        # A Stop hook asked the model to go on (session summary) after the prompt file was cleared.
        self.prompt("s1", "translate the packages", T0)
        self.rec(claude_edit("s1"), now=T0 + 1)
        tasks.mark(self.root, {"session_id": "s1"}, "idle", now=T0 + 2)
        tasks._prompt_path(tasks.record_path(self.root, self.project_id, "s1")).unlink()
        self.rec(claude_read("s1"), now=T0 + 3)
        self.assertEqual(self.directs("s1")[0]["status"], "completed")
        self.rec(claude_edit("s1"), now=T0 + 4)
        tasks.mark(self.root, {"session_id": "s1"}, "idle", now=T0 + 5)
        (card,) = self.directs("s1")
        self.assertEqual(card["turns"], [{"text": "translate the packages", "at": T0}])
        self.assertEqual([h["status"] for h in card["history"]], ["in_progress", "completed", "in_progress", "completed"])

    def test_a_continuation_that_only_reads_opens_no_card(self):
        self.assertFalse(self.rec(claude_read("s1"), now=T0)["recorded"])
        self.rec(claude_edit("s1"), now=T0 + 1)
        (card,) = self.directs("s1")
        self.assertEqual((card["status"], card["turns"]), ("in_progress", []))

    def test_a_background_agents_report_is_not_a_turn_on_every_provider(self):
        # Replays the shape of a real session: work done, then agents report back while idle.
        for provider in providers.ALL_PROVIDERS:
            with self.subTest(provider=provider):
                edit, _, read = CALLS[provider]
                session = "n-" + provider
                self.prompt(session, "translate the Cusco packages", T0)
                self.rec(edit(session), now=T0 + 1)
                tasks.mark(self.root, {"session_id": session, "sessionID": session}, "idle", now=T0 + 2)
                for n, injected in enumerate(tasks._INJECTED_PROMPTS):
                    at = T0 + 10 * (n + 1)
                    self.prompt(session, injected + "\n<task-id>x</task-id>", at)
                    self.rec(read(session), now=at + 1)
                    tasks.mark(self.root, {"session_id": session, "sessionID": session}, "idle", now=at + 2)
                (card,) = self.directs(session)
                self.assertEqual(card["status"], "completed")
                self.assertEqual([t["text"] for t in card["turns"]], ["translate the Cusco packages"])
                # Acting on the report is work: it moves the card, still without a turn of its own.
                self.prompt(session, "<task-notification>done", T0 + 100)
                self.rec(edit(session), now=T0 + 101)
                self.assertEqual(self.directs(session)[0]["status"], "in_progress")
                self.assertEqual(len(self.directs(session)[0]["turns"]), 1)

    def test_stop_completes_the_card_without_a_session_done_and_the_next_turn_revives_it(self):
        self.prompt("s1", "one", T0)
        self.rec(claude_edit("s1"), now=T0 + 1)
        result = tasks.mark(self.root, {"session_id": "s1"}, "idle", now=T0 + 2)
        self.assertFalse(result["became_all_done"])
        self.assertEqual(self.directs("s1")[0]["status"], "completed")
        self.prompt("s1", "two", T0 + 10)
        self.rec(claude_edit("s1"), now=T0 + 11)
        (card,) = self.directs("s1")
        self.assertEqual(card["status"], "in_progress")
        self.assertEqual([h["status"] for h in card["history"]], ["in_progress", "completed", "in_progress"])
        self.assertEqual([t["text"] for t in card["turns"]], ["one", "two"])

    def test_turns_are_capped_and_a_secret_in_the_prompt_is_never_stored(self):
        for n in range(tasks.DIRECT_TURNS_CAP + 3):
            self.prompt("s1", "turn {} token=abc123".format(n), T0 + 10 * n)
            self.rec(claude_edit("s1"), now=T0 + 10 * n + 1)
        turns = self.directs("s1")[0]["turns"]
        self.assertEqual(len(turns), tasks.DIRECT_TURNS_CAP)
        self.assertEqual(turns[-1]["text"], "turn {} token=[redacted]".format(tasks.DIRECT_TURNS_CAP + 2))
        raw = tasks.record_path(self.root, self.project_id, "s1").read_text(encoding="utf-8")
        self.assertNotIn("abc123", raw)

    def test_a_native_list_never_touches_the_direct_card(self):
        self.rec(claude_edit("s1"), now=T0)
        self.rec(todo_write("s1", [todo("A")]), now=T0 + 1)
        self.rec(todo_write("s1", []), now=T0 + 2)
        (card,) = self.directs("s1")
        self.assertIsNone(card["removed_at"])

    def test_the_view_carries_kind_and_turns(self):
        self.prompt("s1", "ship it", T0)
        self.rec(claude_edit("s1"), now=T0 + 1)
        self.rec(todo_write("s1", [todo("A")]), now=T0 + 2)
        views = {t["kind"]: t for t in self.view(now=T0 + 5)[0]["sessions"][0]["tasks"]}
        self.assertEqual(views["direct"]["turns"], [{"text": "ship it", "at": T0}])
        self.assertEqual(views["todo"]["turns"], [])


@requires_bash()
class DirectHookTest(tt.HookTest):
    def board(self):
        return self.state / "task-board"

    def test_one_python_call_per_turn_and_stop_reopens_the_gate(self):
        self.run_script(USER_PROMPT, {"session_id": "s1", "prompt": "rename the module"})
        self.assertEqual(self.python_calls(), 0)
        for _ in range(3):
            self.run_script(PRE_TOOL_USE, claude_edit("s1", cwd=str(self.root)))
        self.assertEqual(self.python_calls(), 1)
        self.assertTrue((self.board() / ".direct-s1").is_file())
        payload = self.tmp / "stop.json"
        payload.write_text(json.dumps({"session_id": "s1"}), encoding="utf-8")
        self.run_script(STOP_SUB, "", extra_env={"DEVTEAM_HOOK_PAYLOAD": str(payload)})
        self.assertFalse((self.board() / ".direct-s1").exists())
        card = [t for t in self.load("s1")["tasks"] if t.get("kind") == "direct"][0]
        self.assertEqual((card["status"], card["turns"][0]["text"]), ("completed", "rename the module"))

    def test_every_provider_reaches_the_card_through_the_dispatcher(self):
        for provider in providers.ALL_PROVIDERS:
            with self.subTest(provider=provider):
                edit, _, _ = CALLS[provider]
                session = "h-" + provider
                self.assertEqual(self.run_script(PRE_TOOL_USE, edit(session)).stdout, b"")
                self.assertEqual(self.load(session)["tasks"][0]["kind"], "direct")

    def test_subagent_and_list_reading_calls_fork_no_python(self):
        for payload in (claude_edit("s1", agent_id="a1"), claude_read("s1", agent_id="a1"),
                        opencode_edit("s1", parent_id="p1"), {"session_id": "s1", "tool_name": "TaskList"}):
            self.run_script(PRE_TOOL_USE, payload)
        self.assertEqual(self.python_calls(), 0)

    def test_at_most_two_python_calls_a_turn_one_for_reads_one_for_writes(self):
        self.run_script(USER_PROMPT, {"session_id": "s1", "prompt": "look, then fix"})
        for command in READ_COMMANDS:
            self.run_script(PRE_TOOL_USE, claude_shell("s1", command, cwd=str(self.root)))
        self.run_script(PRE_TOOL_USE, claude_read("s1", cwd=str(self.root)))
        self.assertEqual(self.python_calls(), 1)
        for _ in range(3):
            self.run_script(PRE_TOOL_USE, claude_edit("s1", cwd=str(self.root)))
            self.run_script(PRE_TOOL_USE, claude_read("s1", cwd=str(self.root)))
        self.assertEqual(self.python_calls(), 2)
        self.assertEqual(self.load("s1")["tasks"][0]["status"], "in_progress")
        payload = self.tmp / "stop.json"
        payload.write_text(json.dumps({"session_id": "s1"}), encoding="utf-8")
        self.run_script(STOP_SUB, "", extra_env={"DEVTEAM_HOOK_PAYLOAD": str(payload)})
        self.assertEqual(sorted(p.name for p in self.board().glob(".direct*")), [])

    def test_the_gate_lets_every_write_through(self):
        # The gate must be a superset of `tasks.writes()`, or a real write never reaches the CLI.
        for n, command in enumerate(WRITE_COMMANDS):
            before = self.python_calls()
            self.run_script(PRE_TOOL_USE, claude_shell("w{}".format(n), command))
            self.assertEqual(self.python_calls(), before + 1, command)

    def test_an_edit_whose_content_names_agent_id_is_still_direct_work(self):
        edit = claude_edit("s1", tool_input={"file_path": "a.json", "content": '{"agent_id": "x", "parent_id": "y"}'})
        self.run_script(PRE_TOOL_USE, edit)
        self.assertEqual(self.load("s1")["tasks"][0]["kind"], "direct")

    def test_the_prompt_file_is_the_first_line_owner_only_and_gone_after_stop_and_session_end(self):
        self.run_script(USER_PROMPT, {"session_id": "s1", "prompt": "first line\nsecond secret line"})
        prompt = self.board() / ".prompt-s1"
        self.assertNotIn("second", prompt.read_text(encoding="utf-8"))
        self.assertEqual(prompt.stat().st_mode & 0o077, 0)
        payload = self.tmp / "stop.json"
        payload.write_text(json.dumps({"session_id": "s1"}), encoding="utf-8")
        self.run_script(STOP_SUB, "", extra_env={"DEVTEAM_HOOK_PAYLOAD": str(payload)})
        self.assertFalse(prompt.exists())
        self.run_script(USER_PROMPT, {"session_id": "s1", "prompt": "again"})
        self.run_script(tt.SESSION_END, {"session_id": "s1"})
        self.assertFalse(prompt.exists())

    def test_the_prompt_file_skips_leading_blank_lines(self):
        self.run_script(USER_PROMPT, {"session_id": "s1", "prompt": "\n \n\tfix the hero image\nmore"})
        raw = (self.board() / ".prompt-s1").read_text(encoding="utf-8")
        self.assertEqual(tasks._excerpt(tasks._decode_prompt(raw)), "fix the hero image")
        self.run_script(USER_PROMPT, {"session_id": "s1", "prompt": "plain"})
        raw = (self.board() / ".prompt-s1").read_text(encoding="utf-8")
        self.assertEqual(tasks._excerpt(tasks._decode_prompt(raw)), "plain")

    def test_a_prompt_forks_no_python_and_clears_the_marker(self):
        self.board().mkdir(parents=True, exist_ok=True)
        (self.board() / ".direct-s1").write_text("", encoding="utf-8")
        self.run_script(USER_PROMPT, {"session_id": "s1", "prompt": "hello there"})
        self.assertFalse((self.board() / ".direct-s1").exists())
        self.assertIn("hello there", (self.board() / ".prompt-s1").read_text(encoding="utf-8"))
        self.assertEqual(self.python_calls(), 0)


if __name__ == "__main__":
    unittest.main()
