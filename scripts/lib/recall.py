"""Prompt recall (ADR-0047): pointers to the ADRs, wiki entries and reuse rules a prompt touches.

Usage: python3 -I recall.py <repo-root> <shown-file|-> <max-lines> <max-chars>   (prompt JSON text on stdin)

stdin carries the payload from the `"prompt"` key onward, cut at a fixed size; the first JSON string
in it is the prompt. Matches it against the three retrieval indexes and prints at most <max-lines>
`[DEVTEAM:RECALL]` lines, best first, within <max-chars>. Each pointer is printed once per session:
<shown-file> lists the keys already delivered and receives the new ones. Pointers only, never a body.

An entry is shown when the prompt shares two of its keywords, or one keyword found in its title or
name. Any error prints nothing and exits 0.
"""

import json
import os
import re
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import docs_root  # noqa: E402
import index_lint  # noqa: E402

PREFIX = "[DEVTEAM:RECALL]"
WORD_RE = re.compile(r"[a-z0-9]+")
READ_WHEN_MAX = 160
STOP = frozenset(
    "about after again also because before between being could every first from have into more most "
    "must never other should still than that their then there these they this those through under "
    "until when where which while with without would your".split()
)


def stem(word):
    if len(word) > 4 and word.endswith("ies"):
        return word[:-3] + "y"
    if len(word) > 5 and word.endswith("ing"):
        return word[:-3]
    if len(word) > 4 and word.endswith("ed"):
        return word[:-2]
    if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


def stems(text):
    return [stem(w) for w in WORD_RE.findall(text.lower())]


def prompt_text(raw):
    """The first JSON string in `raw`, decoded; best effort when the cut falls inside it."""
    start = raw.find('"')
    if start < 0:
        return ""
    i, n = start + 1, len(raw)
    while i < n:
        if raw[i] == "\\":
            i += 2
            continue
        if raw[i] == '"':
            break
        i += 1
    body = raw[start + 1 : i]
    try:
        return json.loads('"' + body + '"')
    except ValueError:
        return body.replace("\\n", " ").replace("\\t", " ").replace('\\"', '"')


def contains(seq, sub):
    size = len(sub)
    return size > 0 and any(seq[i : i + size] == sub for i in range(len(seq) - size + 1))


def score(prompt_stems, keywords, title_stems):
    """(matched keyword count, whether one of them is in the title) -> a rank, or 0 below the bar."""
    matched = strong = 0
    for kw in keywords:
        parts = stems(kw)
        if not parts or (len(parts) == 1 and len(parts[0]) < 3):
            continue
        if contains(prompt_stems, parts):
            matched += 1
            if all(p in title_stems for p in parts):
                strong += 1
    if matched >= 2 or strong >= 1:
        return matched * 2 + strong * 3
    return 0


def clip(text, size):
    text = " ".join(text.split())
    return text if len(text) <= size else text[: size - 1].rstrip() + "…"


def adr_candidates(root, docs):
    directory = index_lint.adr_dir(root, docs)
    text = index_lint.read(os.path.join(directory, "README.md")) if directory else None
    if text is None:
        return
    rel = os.path.relpath(directory, root).replace(os.sep, "/")
    for name, cells in index_lint.index_rows(text).items():
        if len(cells) < 3 or not cells[0].lower().startswith("accepted"):
            continue
        title = re.sub(r"^(?:adr-)?\d+-", "", name[:-3] if name.endswith(".md") else name, flags=re.I)
        yield "{}/{}".format(rel, name), "ADR", cells[1].split(","), stems(title.replace("-", " ")), cells[2]


def wiki_candidates(root, docs):
    wiki = os.path.join(root, docs, "wiki")
    text = index_lint.read(os.path.join(wiki, "README.md")) if index_lint.inside(root, wiki) else None
    if text is None:
        return
    for name, cells in index_lint.index_rows(text).items():
        if len(cells) < 2:
            continue
        slug = os.path.splitext(name)[0].replace("/", " ").replace("-", " ").replace("_", " ")
        yield "{}/wiki/{}".format(docs, name), "wiki", cells[0].split(","), stems(slug), cells[1]


def reuse_candidates(root, docs):
    try:
        rel = docs_root.doc_path(root, "reuse-guidelines")
    except (KeyError, OSError, ValueError):
        rel = ""
    text = index_lint.read(os.path.join(root, rel)) if rel else None
    if text is None:
        return
    for line in text.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 3 or not line.lstrip().startswith("|") or cells[0] in ("name", "") or set(cells[0]) <= {"-"}:
            continue
        name, rule = cells[0], cells[2]
        name_words = name.replace("_", " ").replace("-", " ").replace(".", " ")
        rule_words = [w for w in WORD_RE.findall(rule.lower()) if len(w) >= 7 and w not in STOP]
        keywords = [w for w in name_words.split() if len(w) >= 5] + rule_words
        yield "{}#{}".format(rel, name), "reuse rule", keywords, stems(name_words), clip(rule, READ_WHEN_MAX)


#: Control and invisible format characters (bidi overrides, zero-width, line/paragraph separators); the
#: same set as devteam.tasks._INVISIBLE, mirrored because this script runs standalone. Index text
#: becomes model context, so it is stripped from every emitted line.
INVISIBLE = re.compile("[\u0000-\u001f\u007f-\u009f\u00ad\u061c\u180e\u200b-\u200f\u2028-\u202e\u2060-\u2064\u2066-\u206f\ufeff]")


def main(argv):
    root, shown_path, max_lines, max_chars = argv[1], argv[2], int(argv[3]), int(argv[4])
    prompt = prompt_text(sys.stdin.read())
    if len(prompt.strip()) < 12:
        return
    docs = docs_root.write_root(root)
    shown = set()
    if shown_path != "-" and index_lint.regular(shown_path):
        with open(shown_path, encoding="utf-8", errors="replace") as handle:
            shown = {line.rstrip("\n") for line in handle}
    prompt_stems = stems(prompt)
    ranked = []
    for source in (adr_candidates, wiki_candidates, reuse_candidates):
        for position, (pointer, kind, keywords, title, read_when) in enumerate(source(root, docs)):
            key = "recall:" + pointer
            if key in shown:
                continue
            rank = score(prompt_stems, [k.strip() for k in keywords if k.strip()], set(title))
            if rank:
                ranked.append((-rank, len(ranked), key, "{} {} ({}) — {}".format(PREFIX, pointer, kind, clip(read_when, READ_WHEN_MAX))))
    ranked.sort()
    out, used = [], 0
    for _neg, _pos, key, line in ranked:
        line = INVISIBLE.sub("", line)
        if len(out) >= max_lines or used + len(line) + 1 > max_chars:
            break
        out.append((key, line))
        used += len(line) + 1
    if not out:
        return
    if shown_path != "-" and not os.path.islink(shown_path):
        try:
            fd = os.open(shown_path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write("".join(key + "\n" for key, _ in out))
        except OSError:
            pass
    sys.stdout.write("".join(line + "\n" for _, line in out))


if __name__ == "__main__":
    try:
        main(sys.argv)
    except Exception:  # noqa: BLE001 — recall never disturbs a prompt
        pass
    sys.exit(0)
