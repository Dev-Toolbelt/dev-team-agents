# Supabase CLI paths resolve from the workdir, not from supabase/

**Origin:** Local Supabase stack for the account service | 2026-10-02
**Tags:** supabase, cli, config.toml, content_path, email templates, workdir, dev-local.sh, symlink, copy

> A relative `content_path` in `config.toml` resolves from the directory that *holds* `supabase/`, so it must start with `./supabase/`; `supabase start` and `config push` both fail otherwise.

---

## What it is

`infra/supabase/config.toml` points the auth email templates at files beside it. Written as
`./templates/confirmation.html`, the CLI looked for `<workdir>/templates/…` and failed, because the CLI's
working directory is the parent of `supabase/`, not `supabase/` itself. The committed value is
`./supabase/templates/confirmation.html`, and `tests/test_supabase_config.py` checks that every
`content_path` resolves from the workdir.

## How it works

`infra/supabase/dev-local.sh` builds a CLI project under the gitignored `infra/supabase/.local/` and
runs the stack from there:

- `config.toml`, `migrations/`, `functions/`, `templates/` and `seed.sql` are **copied** in. The CLI
  resolves symlinks and refuses paths outside the project, so a symlinked tree does not work.
- The copy switches `[auth.email.smtp]`, `[auth.external.google]` and `[auth.external.github]` off, so
  mail goes to Mailpit (`:54324`). The committed `config.toml` is never edited for local use: making
  those sections `env()` booleans would let a `config push` silently turn off production SMTP.
- It writes local-only secrets (Ed25519 key with a `test-` kid, ban pepper, `ENTITLEMENT_ISSUER`) under
  `.local/`. `env` prints the CLI test seam variables and a throwaway `DEVTEAM_HOME`.

## Gotchas

- Inside the stack, `SUPABASE_URL` is the gateway's internal address, so the entitlement function would
  sign the wrong `iss` and the CLI rejects the token as `wrong_issuer`. `ENTITLEMENT_ISSUER` overrides it
  locally; leave it unset in the cloud.
- `reset` drops the database but keeps the keys; deleting `.local/` means new keys and a fresh sign-in.

## References

- `infra/supabase/dev-local.sh`, `infra/supabase/README.md` § Local development
- `tests/test_supabase_config.py`
