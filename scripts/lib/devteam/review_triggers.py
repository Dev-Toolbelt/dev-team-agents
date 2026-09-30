"""What starts and ends a review window on the task board (ADR-0018, In Review amendment).

Everything the hooks need to decide "is this a review?" lives here, in one tested place:
the review/QA agent names, the review commands, the prompt keywords (with negation) and the
``<!-- review-result: findings=N -->`` marker. Nothing here touches disk.

The bash gates in front of the CLI are deliberately looser than these rules (a substring
test); this module is the authority, the gates only avoid forking python for a call that
cannot match.
"""

from __future__ import annotations

import re

#: Agents that review or test other agents' work. Their final report ends with the marker.
REVIEW_AGENTS = ("qa-specialist", "code-reviewer", "backend-reviewer", "frontend-reviewer")

#: Slash commands (Claude Code, opencode) and the Codex skill aliases that run a review.
COMMANDS = ("/devteam:review", "/devteam:qa", "/review", "$devteam-review", "$devteam-qa")

#: Words that mean "review this" when the user writes them in a prompt (English, Portuguese).
KEYWORDS = ("review", "revisar", "revisão", "revisao", "revise", "qa", "testar", "test it")

#: A keyword preceded by one of these within three words is a refusal, not a request.
NEGATIONS = ("não", "nao", "sem", "no", "not", "don't", "dont", "without", "skip")
NEGATION_WINDOW = 3

_COMMAND_RE = re.compile(
    r"^\s*(" + "|".join(re.escape(c) for c in COMMANDS) + r")(?=\s|$)", re.IGNORECASE
)
_KEYWORD_RE = re.compile(
    r"(?<!\w)(" + "|".join(r"\s+".join(re.escape(p) for p in k.split()) for k in KEYWORDS) + r")(?!\w)",
    re.IGNORECASE | re.UNICODE,
)
_WORD_RE = re.compile(r"[\w'’]+", re.UNICODE)
_MARKER_RE = re.compile(r"<!--\s*review-result:\s*findings\s*=\s*(\d{1,6})\s*-->", re.IGNORECASE)


def agent_name(value):
    """A review agent's bare name from a ``subagent_type``/``agent_type``, else ``None``.

    Plugins may namespace an agent (``team:qa-specialist``); the last segment decides.
    """
    if not isinstance(value, str):
        return None
    name = value.strip().rsplit(":", 1)[-1].strip().lower()
    return name if name in REVIEW_AGENTS else None


def _negated(text, start):
    words = _WORD_RE.findall(text[:start].replace("’", "'"))
    return any(w.lower() in NEGATIONS for w in words[-NEGATION_WINDOW:])


def prompt_trigger(prompt):
    """``(kind, source)`` when ``prompt`` asks for a review, else ``None``.

    ``kind`` is ``"command"`` (a review command at the start of the prompt) or ``"prompt"``
    (a keyword the user wrote). A keyword is word-bounded, case-insensitive and skipped when
    a negation stands within three words before it.
    """
    if not isinstance(prompt, str) or not prompt.strip():
        return None
    command = _COMMAND_RE.match(prompt)
    if command:
        return ("command", command.group(1).lower())
    for match in _KEYWORD_RE.finditer(prompt):
        if not _negated(prompt, match.start()):
            return ("prompt", match.group(1).lower())
    return None


def _strings(value, depth=0):
    if depth > 6:
        return
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _strings(item, depth + 1)
    elif isinstance(value, list):
        for item in value[:200]:
            yield from _strings(item, depth + 1)


def markers(value):
    """Every ``findings=N`` marker in ``value`` (a string or any JSON structure), in order."""
    found = []
    for text in _strings(value):
        found.extend(int(m.group(1)) for m in _MARKER_RE.finditer(text))
    return found
