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

#: A keyword directly governed by one of these is a refusal, not a request.
NEGATIONS = ("não", "nao", "sem", "no", "not", "don't", "dont", "without", "skip")
#: "Directly governed": the negation is one of the two words before the keyword, with no
#: punctuation between them and none of :data:`NEGATION_BREAKS` in between ("not only review
#: but fix" and "no problem, review it" are requests).
NEGATION_WINDOW = 2
NEGATION_BREAKS = ("only", "just", "apenas", "somente")

#: A sentence that opens with one of these and ends in "?" asks about a thing; it does not order it.
QUESTION_OPENERS = ("what", "how", "why", "o que", "como", "por que", "por quê", "por que")
QUESTION_LOOKAROUND = 240

_COMMAND_RE = re.compile(
    r"^\s*(" + "|".join(re.escape(c) for c in COMMANDS) + r")(?=\s|$)", re.IGNORECASE
)
_KEYWORD_RE = re.compile(
    r"(?<!\w)(" + "|".join(r"\s+".join(re.escape(p) for p in k.split()) for k in KEYWORDS) + r")(?!\w)",
    re.IGNORECASE | re.UNICODE,
)
_WORD_RE = re.compile(r"[\w'’]+", re.UNICODE)
_BREAK_RE = re.compile(r"[,;:.!?()\n]")
_SENTENCE_END_RE = re.compile(r"[.!?\n]")
_MARKER_RE = re.compile(r"<!--\s*review-result:\s*findings\s*=\s*(\d{1,6})\s*-->", re.IGNORECASE)


def agent_name(value):
    """A review agent's bare name from a ``subagent_type``/``agent_type``, else ``None``.

    Plugins may namespace an agent (``team:qa-specialist``); the last segment decides.
    """
    if not isinstance(value, str):
        return None
    name = value.strip().rsplit(":", 1)[-1].strip().lower()
    return name if name in REVIEW_AGENTS else None


def _is_question(text, start):
    """True when the keyword at ``start`` sits in a question that opens with an interrogative."""
    head = text[max(0, start - QUESTION_LOOKAROUND):start]
    ends = list(_SENTENCE_END_RE.finditer(head))
    sentence_start = ends[-1].end() if ends else 0
    opening = head[sentence_start:].lstrip().lower()
    if not any(opening.startswith(o) and not opening[len(o):len(o) + 1].isalnum() for o in QUESTION_OPENERS):
        return False
    tail = text[start:start + QUESTION_LOOKAROUND]
    end = _SENTENCE_END_RE.search(tail)
    return end is not None and tail[end.start()] == "?"


def prompt_trigger(prompt):
    """``(kind, source)`` when ``prompt`` asks for a review, else ``None``.

    ``kind`` is ``"command"`` (a review command at the start of the prompt) or ``"prompt"``
    (a keyword the user wrote). A keyword is word-bounded and case-insensitive; it is skipped
    when a negation directly governs it or it sits in a question ("what does the QA agent do?").
    One pass over the words with a two-word window: the cost is linear in the prompt.
    """
    if not isinstance(prompt, str) or not prompt.strip():
        return None
    command = _COMMAND_RE.match(prompt)
    if command:
        return ("command", command.group(1).lower())
    text = prompt.replace("’", "'")
    words = [(m.start(), m.end(), m.group().lower()) for m in _WORD_RE.finditer(text)]
    cursor = 0
    for match in _KEYWORD_RE.finditer(text):
        while cursor < len(words) and words[cursor][0] < match.start():
            cursor += 1
        if _negated(text, words, cursor, match.start()) or _is_question(text, match.start()):
            continue
        return ("prompt", match.group(1).lower())
    return None


def _negated(text, words, index, start):
    """Whether a negation among the ``NEGATION_WINDOW`` words before word ``index`` governs it."""
    for at in range(max(0, index - NEGATION_WINDOW), index):
        _, end, word = words[at]
        if word not in NEGATIONS:
            continue
        between = words[at + 1:index]
        if any(w[2] in NEGATION_BREAKS for w in between) or _BREAK_RE.search(text, end, start):
            continue
        return True
    return False


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
