# Python on Windows reads cp1252 and writes CRLF unless told otherwise

**Origin:** opencode installer and half the test suite failing on the Windows runner | 2026-10-02
**Tags:** windows, encoding, cp1252, UTF-8, UnicodeDecodeError, PYTHONUTF8, read_text, write_text, CRLF, newline, fixtures, bytes, command line length, WinError 206, readlink, 8.3 short name, permission bits

> On Windows, Python's default text encoding is the locale's (cp1252 on the runner) and text-mode writes translate `\n` to `\r\n`. The repo's files are UTF-8 with em dashes and arrows, so every `open()`/`read_text()` without `encoding=` is a `UnicodeDecodeError` waiting to happen, and every `write_text` fixture is a byte mismatch.

---

## What broke and how it is handled

- **Shipped inline python** (heredocs in the installers): the opencode installer crashed decoding its own command snippet. `scripts/lib/python.sh` exports `PYTHONUTF8=1` **on Windows only** (when not already set), which turns on UTF-8 mode for every python those scripts start.
- **The CLI and the render engine** pass `encoding="utf-8"` explicitly, and the renderer writes with `newline="\n"`.
- **Tests:** read with `encoding="utf-8"`, and write fixtures that are compared byte for byte with `write_bytes(text.encode("utf-8"))`. `Path.write_text` has no `newline=` before Python 3.10, and the floor is 3.9.

## Other portable-test traps found in the same runs

- **Command-line length:** Windows caps the whole command line at 32 KiB (`WinError 206`). Linux caps a single argv string at 128 KiB (`E2BIG`). A test that passes a huge value on argv must stay under both.
- **Paths:** `os.readlink` returns a `\\?\`-prefixed target, and temp directories show up under 8.3 short names (`RUNNER~1`). Compare `os.path.normcase(os.path.realpath(...))` on both sides.
- **Permission bits:** every file reads `0666`. Assert modes only where `devteam_support.POSIX_MODES` holds. The same reason made `devteam doctor` skip its credentials mode warning on Windows.

## References

- `scripts/lib/python.sh`: the `PYTHONUTF8` export
- `tests/test_credentials_local.py`: fixtures written with `write_bytes()`, and `assertMode`, which asserts permission bits only where they exist
- `tests/devteam_support.py`: `POSIX_MODES`, `requires_posix_modes`, `requires_bash`
