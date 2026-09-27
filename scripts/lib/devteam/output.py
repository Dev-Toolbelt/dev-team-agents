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

    def warn(self, message):
        """Advisory text. Always stderr, so ``--json`` stdout stays parseable."""
        self.stderr.write("devteam: {}\n".format(message))

    def line(self, message=""):
        """Human-only output; suppressed entirely under ``--json``."""
        if not self.as_json:
            self.stdout.write("{}\n".format(message))

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
        if self.as_json:
            json.dump(
                error.payload(), self.stdout, indent=2, ensure_ascii=False, sort_keys=True
            )
            self.stdout.write("\n")
        else:
            self.stderr.write("devteam: error: {}\n".format(error.message))
            if error.hint:
                self.stderr.write("  hint: {}\n".format(error.hint))
        return error.exit_code
