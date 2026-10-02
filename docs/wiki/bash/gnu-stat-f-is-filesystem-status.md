# GNU stat -f prints filesystem status then fails

**Origin:** Cross-platform stat probe logic | 2026-10-02
**Tags:** stat, -f, -c, filesystem status, GNU, multi-line output, file-stat.sh, Ubuntu

> GNU `stat -f` is **not** an alias for BSD `stat -f`. It prints a multi-line filesystem status block to stdout and exits with failure. Probing for timestamp with `stat -f %m file` captures garbage and `$?` returns non-zero.

---

## What it is

On GNU coreutils (Linux, including WSL and GitHub's ubuntu-latest runner), `stat -f` does not print file modification time. Instead, it prints a multi-line filesystem summary (block size, inodes, usage) and exits 1.

The command appears to succeed (output captured), but the timestamp is meaningless and the exit code signals failure.

## How it works

```bash
# Wrong: BSD form first. On GNU, `stat -f` succeeds at printing a filesystem block for the file,
# then fails on `%m`, so $(...) captures that block AND the fallback's number.
mtime=$(stat -f %m "$f" 2>/dev/null || stat -c %Y "$f" 2>/dev/null)

# Right: GNU form first (it fails silently on BSD), then BSD, and validate before arithmetic.
v=$(stat -c %Y "$f" 2>/dev/null) || v=""
case "$v" in ''|*[!0-9]*) v=$(stat -f %m "$f" 2>/dev/null) || v="" ;; esac
case "$v" in ''|*[!0-9]*) v=0 ;; esac
```

This is the pattern in `scripts/hooks/lib/file-stat.sh`.

## Gotchas

- **The output looks plausible** — it is a multi-line block of data, not an error message, so a naive capture succeeds invisibly.
- **Validating numeric before using the value is load-bearing.** A timestamp check that only looks at exit code will be fooled.
- **This only happens on GNU systems.** Tests passing locally on macOS and failing in CI on Ubuntu are a classic signal.

## References

- `scripts/hooks/lib/file-stat.sh` — canonical portable stat probe
- Reproduced on: Ubuntu 22.04, GitHub Actions ubuntu-latest runner
