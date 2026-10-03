# The secret scanner scans only git-committable files in a work tree

**Origin:** Local Supabase stack for the account service | 2026-10-02
**Tags:** secret scanner, secret_scan.py, service_role, jwt, gitignore, .local, git ls-files, package scan

> Inside a git work tree, `.github/scripts/ci/secret_scan.py` scans tracked and untracked-but-not-ignored files only, because the local Supabase stack writes the public demo service-role JWT under the gitignored `infra/supabase/.local/`.

---

## What it is

The scanner fails on any `service_role` JWT or `sb_secret_` key. Running the local stack leaves the
Supabase CLI's demo service-role key (public, the same on every install) inside `infra/supabase/.local/`.
A full walk of the tree flagged it and failed the test suite on any machine that had run the stack.

## How it works

`scan_tree()` asks git for its candidates (`_git_candidates()`: tracked plus untracked files that are not
ignored). A file git ignores cannot be committed, so it cannot leak through the repository. Outside a
git work tree, such as the stripped package CI checks, the scanner still walks every file.

## Gotchas

- Untracked files are still scanned: a key dropped in a new, not-yet-added file fails the scan.
- Gitignoring a path is what exempts it. Never add a path to `.gitignore` to quiet the scanner unless
  the file really must stay out of git.

## References

- `.github/scripts/ci/secret_scan.py`, `tests/test_secret_scan.py`
- `.gitignore` (`infra/supabase/.local/`)
