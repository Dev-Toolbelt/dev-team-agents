# A write-gate regex must stop at the command boundary

**Origin:** Hook task board payload parsing | 2026-10-02
**Tags:** regex, hook, payload, sed, quote, IN_CMD, gateway, 04-task-board.sh, test flakiness

> Write-shape gateway regexes that do not stop at the unescaped closing quote of the JSON `"command"` field cross into adjacent fields (e.g., `"cwd"`). A random character in a temp directory name can match a pattern meant for the command, re-triggering tool calls and fork loops.

---

## What it is

In `scripts/hooks/pre-tool-use/04-task-board.sh`, the payload parser uses regexes to detect shapes like `sed -i` (dangerous rewrites). The pattern `[^|;&]*` stops at any shell metacharacter — but it does not know about JSON string boundaries. A regex that crosses from the `"command"` field into the next field can match unrelated content.

The symptom is flaky tests: a temp directory name containing `-` and `i` can pattern-match as `sed -i`, spuriously re-trigging the gate.

## How it works

```bash
# Wrong regex (crosses field boundary):
IN_CMD='[^|;&]*'  # stops at shell chars, but not at the closing quote
sed -n "/\"command\": \"$IN_CMD.*sed -i/p"  # may match into "cwd" field

# Correct regex (stops at unescaped quote):
IN_CMD='([^|;&"\\]|\\.)*'  # matches any char except unescaped quote
# Breaking it down:
#   [^|;&"\\]    = any char except |, ;, &, ", or \ (end of unescaped substring)
#   \\\\.        = escaped char (backslash + any char)
#   (...)*       = repeat: unescaped chars + escaped sequences
```

For a command string `sed -i`, the correct regex stops at the closing `"` of the command field and never sees the cwd or other fields.

## Gotchas

- **A simple `-i` appearing in any part of the payload will match.** Even a file path like `/tmp/test-i/file` can trigger the gate if the regex is not scoped to the command field.
- **It shows up as a flaky test, not a failure.** Whether a random temp directory name contains a `-…i` decides it, so `test_direct_work` failed now and then on any OS. `test_a_read_is_judged_by_its_command_not_by_the_rest_of_the_payload` pins it with a fixed `dir-xi` cwd.
- **The gate is a safety net, not a parse.** Escaping the regex correctly requires understanding JSON string encoding rules, not just shell syntax.

## References

- `scripts/hooks/pre-tool-use/04-task-board.sh` — task board write gate
- `tests/test_direct_work.py` — test cases exercising write shapes
