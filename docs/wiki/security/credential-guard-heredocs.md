# Credential Guard and Heredoc Bodies

**Origin:** credential-guard false positive/negative fix | 2026-09-30
**Tags:** credential-guard, 03-credential-guard.sh, heredoc, credentials.local.json, session-summary, false positive, false negative, newline, segment, refuse, exit 2

> The guard judges command text segment by segment (path + disclosing verb in one segment); text inside a heredoc body is data, not commands, and must be dropped before segmenting.

---

## What it is

`scripts/hooks/pre-tool-use/03-credential-guard.sh` refuses a Bash call only when one segment both names a credential-store path and uses a verb that discloses or copies content. A session-summary entry written through `cat <<EOF` that merely mentions `credentials.local.json` (prose, a markdown table, text after `;`) was being read as commands and refused.

## How it works

1. Heredoc bodies are removed by delimiter (awk) before anything else.
2. Backslash-newline joins lines; an escaped `\n` inside a string is not a newline.
3. Real newlines are segment separators, alongside `;`, `&&`, `||`, `|`.
4. Each segment is tested for path + verb. Refuse exits 2, everything else exits 0.

Dropping the body by delimiter, rather than truncating the command at the first `<<`, is what closes the false negative: a dump on the line after a heredoc (`cat <<EOF ... EOF` then `cat credentials.local.json`) is still seen.

## Gotchas

- An unterminated `<<` falls back to the original text, so detection is never weakened by a malformed heredoc.
- Do not "fix" a false positive by widening an allow-list or truncating at `<<`; that reintroduces the false negative.
- Writing docs that mention credential files through a heredoc is safe; the same words on a plain command line beside a verb like `cat` or `cp` is still refused.
- The guard is hygiene, not a sandbox (ADR-0010); the real read path is `devteam cred get`.

## References

`tests/test_credential_guard.py` (17 tests pinning the refuse and allow decisions), ADR-0010.
