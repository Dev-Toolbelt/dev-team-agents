# macOS Keychain add-generic-password Double-Entry Trap

**Origin:** Credentials backend implementation (M3) | 2026-09-28
**Tags:** macOS, keychain, security, add-generic-password, double-entry, prompt, exit code, -w flag

> `security add-generic-password -w <value>` prompts for confirmation (double-entry) when called with a literal value; if the two entries mismatch, it exits 0 while silently storing an **empty** password.

---

## What it is

The macOS `security` command can set a keychain password by reading it from the command line (`-w <value>`, where value is the actual secret) or by prompting interactively without it. When invoked with `-w` and a literal value from the shell, the prompt is unavoidable: `security` always asks the user to re-enter the value for confirmation, even in non-interactive contexts (scripts, piped input, CI).

## How it works

The flag `-w` has two behaviors:

1. **With an argument**: `security add-generic-password -w mypassword ...`
   - Stores `mypassword` and prompts the user to re-enter it for confirmation
   - If the two entries match, exits 0 and the value is stored
   - If the two entries **mismatch**, exits 0 (not an error code) and **silently stores an empty string** instead

2. **Without an argument** (reading from stdin or terminal):
   - `security add-generic-password -w` (no argument after `-w`) expects a password via stdin or an interactive prompt
   - This is the correct way to pipe a value from a variable or stdin

The pitfall: a script that does `security add-generic-password -w "$TOKEN"` in a non-interactive context (CI, a piped command, an agent's Bash call) will hang waiting for the confirmation prompt. If the prompt somehow completes (timeout, automated response), and the two entries don't match, the command exits 0 while storing nothing.

## Gotchas

- **Exit code does not indicate success.** Exit 0 means the command completed, not that the value was stored. Verification requires reading the value back and checking it against the original.
- **Empty password is stored silently.** There is no error message, stderr stays empty, and the audit log (if kept) shows an add-generic-password call that succeeded. The problem surfaces later when the value is read and found to be empty.
- **The double-entry is mandatory.** There is no flag to skip it or to read both from stdin automatically. The only clean path is to read the value from stdin with `-w` and no argument (so the prompt is also stdin-based), or to skip the confirmation entirely by using a Python/Objective-C API instead of the shell command.
- **The trap is worst in CI.** A GitHub Actions workflow that pipes a secret from the environment into this command will hang silently for seconds before timing out, and may leave an empty password in the keychain if the timeout happens between the prompt and the confirmation.

## Adapter solution (used in `scripts/lib/devteam/secrets.py`)

The implementation works around this by:
1. Reading the value from stdin (the caller pipes it)
2. Calling `security add-generic-password -w` **without** an argument, so both the value and the confirmation go through stdin as a two-line stream
3. Reading the value back immediately after writing it
4. Comparing it against the original to detect the mismatch-silent-empty case
5. Failing loudly if the values don't match (the user gets an error, not a silently-broken keychain entry)

This transforms the exit-0-on-mismatch silent failure into an explicit, auditable error.

## References

- [security(1) man page](https://ss64.com/osx/security.html) — `-w` flag documentation
- [ADR-0010](../docs/development/adrs/0010-credential-references-and-the-secret-backend-cascade.md) — Credential references and backend cascade
- `scripts/lib/devteam/secrets.py` — The keychain adapter that catches this trap
