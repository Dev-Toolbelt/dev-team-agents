# Git Bash `sha256sum` prints a leading backslash on Windows paths, and its `tar` cannot extract zips

**Origin:** Windows Authenticode signing through SSL.com eSigner, CodeSignTool install step (ADR-0055) | 2026-10-31
**Tags:** windows, Git Bash, sha256sum, backslash, windows-latest, RUNNER_TEMP, GNU tar, unzip, zipfile, CodeSignTool

> On Git Bash, `sha256sum <file>` prints `\<hash>  D:\a\...` when the file name contains a backslash, so `cut -d' ' -f1` yields `\<hash>` and never matches a pinned hash. Hash from stdin with `sha256sum < "$file"`.

---

## Where it bites

`.github/scripts/release/install-codesigntool.sh` runs on `windows-latest` and checks the downloaded CodeSignTool archive against a pinned SHA-256. Every Windows path contains a backslash (`$RUNNER_TEMP` is `D:\a\_temp`), so the digest field starts with `\` and the pin check fails on a correct file.

## Fixes

| Problem | Fix |
|---------|-----|
| Leading `\` in the digest | Hash from stdin: `sha256sum < "$file"`. The output carries no file name, so nothing is escaped |
| `tar` cannot extract the archive | Git Bash `tar` is GNU tar and does not read `.zip`. Use `unzip` when present, else `python -m zipfile -e "$archive" "$dest"` |

## References

- `.github/scripts/release/install-codesigntool.sh`
- `docs/development/adrs/0055-windows-code-signing-goes-through-ssl-com-esigner-a-cloud-hsm-not-a-pfx.md`
