"""A renamed session shows its new title on the board, on every provider, with no turn in between.

A rename writes the provider's own record of the title — Claude Code appends a `custom-title` line
to the transcript, Codex appends to `$CODEX_HOME/session_index.jsonl` — and runs no hook, so the
CLI reads those at view time (`tasks.live_title`). opencode keeps the title in its own storage; its
plugin pushes the rename through `session-retitle.sh` → `devteam tasks retitle`.
"""

import json
import os
import shutil
from pathlib import Path
from unittest import mock

from devteam_support import requires_bash

from devteam import providers, tasks

import test_tasks as tt
from test_direct_work import claude_edit, codex_edit, opencode_edit
from test_tasks import T0

RETITLE = tt.HOOKS / "session-retitle.sh"


def _line(path, entry):
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry) + "\n")


class _Claude:
    """The transcript a Claude Code session writes; a rename appends a `custom-title` line."""

    def __init__(self, case, session):
        self.path = case.tmp / "transcript-{}.jsonl".format(session)
        self.session = session

    def start(self, title):
        _line(self.path, {"type": "user", "message": {"content": "hi"}})
        _line(self.path, {"type": "custom-title", "customTitle": title, "sessionId": self.session})
        return claude_edit(self.session, transcript_path=str(self.path))

    def rename(self, title):
        _line(self.path, {"type": "custom-title", "customTitle": title, "sessionId": self.session})


class _Codex:
    """Codex's session index; a rename appends the thread's new name."""

    def __init__(self, case, session):
        home = case.tmp / "codex-home"
        home.mkdir(exist_ok=True)
        patcher = mock.patch.dict(os.environ, {"CODEX_HOME": str(home)})
        patcher.start()
        case.addCleanup(patcher.stop)
        self.index = home / "session_index.jsonl"
        self.session = session

    def start(self, title):
        _line(self.index, {"id": self.session, "thread_name": title})
        return codex_edit(self.session)

    def rename(self, title):
        _line(self.index, {"id": "someone-else", "thread_name": "unrelated"})
        _line(self.index, {"id": self.session, "thread_name": title})


class _Opencode:
    """No file the CLI can read: the plugin's `session.updated` runs `session-retitle.sh`."""

    def __init__(self, case, session):
        self.case = case
        self.session = session

    def start(self, title):
        return opencode_edit(self.session, session_title=title)

    def rename(self, title):
        self.case.run_script(RETITLE, {"session_id": self.session, "sessionID": self.session, "session_title": title})


#: How each provider renames a session. One entry per provider in `providers.ALL_PROVIDERS`: a
#: provider added without a case fails `test_every_provider_has_its_rename_decided`.
RENAMES = {"claude": _Claude, "codex": _Codex, "opencode": _Opencode}


@requires_bash()
class SessionRenameTest(tt.BoardCase):
    # `HookTest`'s shim and runner, borrowed rather than inherited: inheriting would run its tests again.
    run_script = tt.HookTest.run_script
    python_calls = tt.HookTest.python_calls

    def setUp(self):
        super().setUp()
        Path(tasks.tasks_dir(self.root, self.project_id)).parent.mkdir(parents=True, exist_ok=True)
        self.shim = self.tmp / "shim"
        self.shim.mkdir()
        self.calls = self.tmp / "python-calls"
        real = shutil.which("python3")
        (self.shim / "python3").write_text('#!/bin/sh\necho x >> "{}"\nexec "{}" "$@"\n'.format(self.calls, real), encoding="utf-8")
        (self.shim / "python3").chmod(0o755)
        tasks._LIVE_CACHE.clear()
        self.addCleanup(tasks._LIVE_CACHE.clear)

    def title_in_view(self, session, now=T0 + 10):
        for project in self.view(now=now):
            for entry in project["sessions"]:
                if entry["session_id"] == session:
                    return entry["title"]
        return None

    def test_every_provider_has_its_rename_decided(self):
        self.assertEqual(set(RENAMES), set(providers.ALL_PROVIDERS))

    def test_a_rename_between_turns_reaches_the_board_on_every_provider(self):
        for provider, kind in RENAMES.items():
            with self.subTest(provider=provider):
                session = "rename-" + provider
                source = kind(self, session)
                self.assertTrue(self.rec(source.start("Old title"), now=T0)["recorded"])
                self.assertEqual(self.title_in_view(session), "Old title")
                source.rename("Desafio 7D capa e link")
                self.assertEqual(self.title_in_view(session), "Desafio 7D capa e link")

    def test_a_session_renamed_after_it_ended_is_renamed_on_the_board_too(self):
        for provider, kind in RENAMES.items():
            with self.subTest(provider=provider):
                session = "ended-" + provider
                source = kind(self, session)
                self.rec(source.start("Before"), now=T0)
                tasks.mark(self.root, {"session_id": session, "sessionID": session}, "ended", now=T0 + 1)
                source.rename("After")
                self.assertEqual(self.title_in_view(session, now=T0 + tasks.DEFAULT_ENDED_AFTER + 10), "After")

    def test_the_view_never_writes_the_record(self):
        source = _Claude(self, "ro")
        self.rec(source.start("Old"), now=T0)
        path = tasks.record_path(self.root, self.project_id, "ro")
        before = path.read_bytes()
        source.rename("New")
        self.assertEqual(self.title_in_view("ro"), "New")
        self.assertEqual(path.read_bytes(), before)

    def test_an_unchanged_title_file_is_not_read_again(self):
        source = _Claude(self, "cached")
        self.rec(source.start("Old"), now=T0)
        with mock.patch.object(tasks, "_transcript_title", wraps=tasks._transcript_title) as read:
            self.title_in_view("cached")
            self.title_in_view("cached")
            self.assertEqual(read.call_count, 1)
            source.rename("New")
            self.assertEqual(self.title_in_view("cached"), "New")
            self.assertEqual(read.call_count, 2)

    def test_a_missing_title_file_falls_back_to_the_stored_title(self):
        source = _Claude(self, "gone")
        self.rec(source.start("Stored"), now=T0)
        Path(source.path).unlink()
        self.assertEqual(self.title_in_view("gone"), "Stored")

    def test_retitle_changes_only_the_title_and_skips_an_unknown_session(self):
        self.rec(opencode_edit("oc", session_title="One"), now=T0)
        path = tasks.record_path(self.root, self.project_id, "oc")
        before = json.loads(path.read_text(encoding="utf-8"))
        self.assertTrue(tasks.retitle(self.root, {"sessionID": "oc", "session_title": "Two"})["retitled"])
        after = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(after["title"], "Two")
        self.assertEqual({k: v for k, v in after.items() if k != "title"}, {k: v for k, v in before.items() if k != "title"})
        self.assertFalse(tasks.retitle(self.root, {"sessionID": "oc", "session_title": "Two"})["retitled"])
        self.assertFalse(tasks.retitle(self.root, {"sessionID": "nobody", "session_title": "X"})["retitled"])

    def test_the_retitle_hook_forks_no_python_without_a_record(self):
        self.run_script(RETITLE, {"sessionID": "no-record", "session_title": "X"})
        self.assertEqual(self.python_calls(), 0)
