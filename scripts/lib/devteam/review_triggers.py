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

#: Agents each provider ships itself: spawning one is plumbing, not a unit of work the board shows
#: (docs/specs/task-board.md § Agent spawns are tasks). Compared case-insensitively. Claude Code:
#: its documented built-in subagents; Codex: the built-in roles of `codex-rs/core/src/agent/role.rs`
#: (`default` is also what an omitted `agent_type` resolves to); opencode: its `general` and `explore`
#: subagents. One list; keyed by provider so a provider added to ``providers.ALL_PROVIDERS`` must
#: decide its own.
BUILTIN_AGENTS = {
    "claude": ("explore", "plan", "general-purpose", "claude-code-guide", "statusline-setup"),
    "codex": ("default", "explorer", "worker"),
    "opencode": ("general", "explore"),
}

#: Slash commands (Claude Code, opencode) and the Codex skill aliases that run a review.
COMMANDS = ("/devteam:review", "/devteam:qa", "/review", "$devteam-review", "$devteam-qa")

#: Words that mean "review this" when the user writes them in a prompt (English, Portuguese).
KEYWORDS = ("review", "revisar", "revisão", "revisao", "revise", "qa", "testar", "test it")

#: A keyword directly governed by one of these is a refusal, not a request.
NEGATIONS = ("não", "nao", "sem", "no", "not", "don't", "dont", "without")
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
_FENCE_RE = re.compile(r"```.*?(?:```|\Z)", re.DOTALL)
_INLINE_CODE_RE = re.compile(r"`[^`\n]*`")
#: `qa` inside a path or an identifier (`docs/qa/x`, `qa-specialist`, `qa_report`, `a.qa`) is not the word.
_PATHLIKE_BEFORE_RE = re.compile(r"[/\\_.@#-]")
_PATHLIKE_AFTER_RE = re.compile(r"[/\\_@#-]")


def agent_name(value):
    """A review agent's bare name from a ``subagent_type``/``agent_type``, else ``None``.

    Plugins may namespace an agent (``team:qa-specialist``); the last segment decides.
    """
    if not isinstance(value, str):
        return None
    name = value.strip().rsplit(":", 1)[-1].strip().lower()
    return name if name in REVIEW_AGENTS else None


def spawn_name(value):
    """The bare agent name of a ``subagent_type``/``agent_type`` (plugin namespace dropped), else ``None``."""
    if not isinstance(value, str):
        return None
    name = value.strip().rsplit(":", 1)[-1].strip()
    return name or None


def is_builtin(provider, name):
    """True when ``name`` is one of ``provider``'s own agents. An unknown provider has none."""
    return isinstance(name, str) and name.strip().lower() in BUILTIN_AGENTS.get(provider, ())


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
        if _pathlike(text, match) or _negated(text, words, cursor, match.start()) or _is_question(text, match.start()):
            continue
        return ("prompt", match.group(1).lower())
    return None


def _pathlike(text, match):
    """True for ``qa`` touching a path separator or identifier joiner (``docs/qa/x``, ``qa_report``)."""
    if match.group(1).lower() != "qa":
        return False
    before = text[match.start() - 1:match.start()]
    after = text[match.end():match.end() + 1]
    return bool(_PATHLIKE_BEFORE_RE.fullmatch(before) or _PATHLIKE_AFTER_RE.fullmatch(after))


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


def report_marker(text):
    """The ``findings=N`` of a report, or ``None``.

    Code (fenced or inline) is removed first, and only the LAST non-empty line counts, on its
    own: a report that quotes the marker while explaining it, or a diff that contains one,
    is not a result.
    """
    if not isinstance(text, str) or "review-result" not in text.lower():
        return None
    text = _INLINE_CODE_RE.sub("", _FENCE_RE.sub("", text))
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return None
    match = _MARKER_RE.fullmatch(lines[-1])
    return int(match.group(1)) if match else None


def markers(value):
    """Every report's marker in ``value`` (a string or any JSON structure), in order.

    One string is one report: see :func:`report_marker`.
    """
    found = []
    for text in _strings(value):
        n = report_marker(text)
        if n is not None:
            found.append(n)
    return found
