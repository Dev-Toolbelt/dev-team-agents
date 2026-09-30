"""The ``--json`` contract.

With ``--json`` stdout carries exactly one JSON document and nothing else, so a
caller can pipe it straight into a parser. Human text and warnings never share
that channel: warnings always go to stderr, in both modes.
"""

from __future__ import annotations

import json
import sys


class Emitter:
    def __init__(self, as_json=False, stdout=None, stderr=None):
        self.as_json = as_json
        self.stdout = stdout if stdout is not None else sys.stdout
        self.stderr = stderr if stderr is not None else sys.stderr
        self._emitted = False
        self.streamed = False
        #: Set by `main` for a streaming command. Its stdout is JSON Lines, so even a
        #: failure has to be one compact line — an indented document there is a first
        #: line of `{`, which a reader can only call a protocol error, and the exit code
        #: that explains the failure is never looked at.
        self.lines = False

    def warn(self, message):
        """Advisory text. Always stderr, so ``--json`` stdout stays parseable."""
        self.stderr.write("devteam: {}\n".format(message))

    def line(self, message=""):
        """Human-only output; suppressed entirely under ``--json``."""
        if not self.as_json:
            self.stdout.write("{}\n".format(message))

    def raw(self, text):
        """Write exactly ``text`` plus one LF to stdout, undecorated.

        For the one command whose stdout **is** the payload: `devteam cred get`
        prints a secret and nothing else, so it can be consumed by
        ``TOKEN="$(devteam cred get …)"`` without a parser. It is never used under
        ``--json`` — that combination is refused, because wrapping a secret in a
        document puts it somewhere a client would log.

        Written through the underlying binary buffer when there is one, rather
        than through the text wrapper's own ``write``: on Windows, a text-mode
        stream translates every ``\\n`` to ``\\r\\n`` at the OS level, which is
        harmless for human-readable output but not here — this command's entire
        contract is "exactly the value and a newline, nothing else", and
        ``TOKEN="$(devteam cred get …)"`` strips only a trailing ``\\n``. A
        trailing ``\\r`` would ride along inside every value a caller reads,
        silently, in a bearer token or a shell variable. Falls back to a plain
        text write for a caller-supplied stream with no ``.buffer`` — an
        ``io.StringIO`` used directly in a test, which does no translation of
        its own.
        """
        payload = "{}\n".format(text)
        buffer = getattr(self.stdout, "buffer", None)
        if buffer is not None:
            buffer.write(payload.encode("utf-8"))
            buffer.flush()
        else:
            self.stdout.write(payload)
        self._emitted = True

    def stream(self, event, human=None):
        """One event of a long-running command: a single JSON line, flushed at once.

        The one exception to "exactly one JSON document": `devteam notifications
        watch --json` runs until its reader goes away, so its stdout is JSON Lines —
        one compact document per line, each carrying ``ok``. Compact, not indented,
        because a reader splits on newlines. Flushed per event, because a reader
        waiting on a pipe sees nothing a buffer is still holding. Once anything has
        been streamed, ``main`` emits no final document of its own.
        """
        body = dict(event)
        body.setdefault("ok", True)
        if self.as_json:
            self.stdout.write(json.dumps(body, ensure_ascii=False, sort_keys=True) + "\n")
        elif human:
            self.stdout.write("{}\n".format(human))
        self.stdout.flush()
        self._emitted = True
        self.streamed = True

    def emit(self, payload, human=None):
        """Terminal output for a successful command.

        ``payload`` is the JSON body and always carries ``ok``. ``human`` is a
        string or a callable rendering the same information for a terminal.
        """
        body = dict(payload)
        body.setdefault("ok", True)
        if self.as_json:
            json.dump(body, self.stdout, indent=2, ensure_ascii=False, sort_keys=True)
            self.stdout.write("\n")
        elif human is not None:
            text = human() if callable(human) else human
            if text:
                self.stdout.write("{}\n".format(text.rstrip("\n")))
        self._emitted = True
        return body

    def fail(self, error):
        """Render a :class:`~devteam.errors.DevteamError` and return its code."""
        if self.as_json and self.lines:
            # The stream's terminal event: `{"event": "error", "ok": false, ...}`, the
            # same keys every failed command carries plus the event name a line reader
            # dispatches on.
            body = dict(error.payload(), event="error")
            self.stdout.write(json.dumps(body, ensure_ascii=False, sort_keys=True) + "\n")
            self.stdout.flush()
        elif self.as_json:
            json.dump(
                error.payload(), self.stdout, indent=2, ensure_ascii=False, sort_keys=True
            )
            self.stdout.write("\n")
        else:
            self.stderr.write("devteam: error: {}\n".format(error.message))
            if error.hint:
                self.stderr.write("  hint: {}\n".format(error.hint))
        return error.exit_code
