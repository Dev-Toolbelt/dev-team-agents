# Hosted Supabase rejects some auth settings that the local stack accepts

**Origin:** Provisioning the dev Supabase project (ADR-0029) | 2026-10-10
**Tags:** supabase, config push, config.toml, rate_limit, free plan, email template, SMTP, email OTP, all-or-nothing, config diff

> On the Free plan with the default email provider, `supabase config push` cannot apply email templates, and without custom SMTP the hosted mail carries a link where the CLI expects an 8-digit code.

---

## What it is

`supabase config push` sends the whole `infra/supabase/config.toml` to a hosted project. The local stack
(`dev-local.sh`) accepts values that the hosted API refuses, so a config that starts locally can fail on push.

## How it works

| Setting | Hosted behaviour |
|---|---|
| `auth.rate_limit.anonymous_users = 0` (and `sms_sent`, `web3`) | Rejected: "Expected a value greater than or equal to 1". `config.toml` uses 1; the methods stay disabled. `tests/test_supabase_config.py::test_every_rate_limit_is_accepted_by_the_hosted_api` enforces `>= 1`. |
| `[auth.email.template.*]` and `[auth.email.notification.*]` on Free, default provider | Rejected: "Email template modification is not available for free tier projects using the default email provider." |
| Any rejected section | The auth push is all-or-nothing. A rejected push applies nothing to auth. (The `api` section had already been applied separately.) |
| Undeclared property `auth.external.google.email_optional` | Sent at its config default alongside a declared change. The push printed it; no error. |

## Gotchas

- **Email OTP needs custom SMTP on hosted.** With the default templates the mail carries a link, while the CLI
  expects the 8-digit code. Google sign-in does not depend on email, so it works without SMTP.
- The Supabase default email provider delivers only to members of the Supabase organization, at a low hourly rate.
- `supabase config diff` does not compare: smtp host, user, port, admin_email and sender_name; the GitHub
  `client_id`; `rate_limit.email_sent`. It also lists remote-only properties. A clean diff does not prove those
  values match.
- `config push` requires every `env(...)` variable that `config.toml` reads. With SMTP or GitHub not ready,
  push from a temporary copy of `infra/supabase` with `[auth.email.smtp]` and `[auth.external.github]` set to
  `enabled = false`, the same change `dev-local.sh` makes locally. Do not edit the committed file for this.

## References

- `infra/supabase/README.md` § Link and push
- `infra/supabase/config.toml` (`[auth.rate_limit]`)
- `tests/test_supabase_config.py`
