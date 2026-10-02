# Supabase infrastructure (ADR-0029)

Config as code for the accounts service. Dev-only: `infra/` is not shipped to user projects.
Two projects, both in `sa-east-1`: `devteam-dev` and `devteam-prod`. Secrets never enter git.

## Provision

1. Create each project in the dashboard (region `sa-east-1`, strong DB password stored in your vault).
2. Create OAuth apps: Google (consent screen, scopes `openid email profile`) and GitHub (scope
   `user:email`, primary verified email only). Callback URL for both:
   `https://<project-ref>.supabase.co/auth/v1/callback`. Use separate apps for dev and prod.
3. Export the variables from `.env.example` in your shell for the environment you target.

## Link and push

```bash
supabase link --project-ref <ref>        # run once per target
supabase config push                      # pushes config.toml (auth, rate limits, templates)
supabase db push                          # migrations
supabase functions deploy                 # entitlement, account-delete
supabase secrets set ENTITLEMENT_ED25519_PRIVATE_KEY=... ENTITLEMENT_KID=... BAN_HMAC_KEY=...
```

## Edge Functions

`functions/entitlement` signs the offline entitlement and `functions/account-delete` deletes an account
after a fresh authentication (ADR-0029 SR-33 to SR-39). Both run with JWT verification on (the default) and
read `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`, which the platform injects.

| Secret | Value |
|--------|-------|
| `ENTITLEMENT_ED25519_PRIVATE_KEY` | Base64 of the PKCS#8 DER private key (see the keypair section) |
| `ENTITLEMENT_KID` | Key id placed in the token header; must match a public key embedded in the CLI |
| `BAN_HMAC_KEY` | Random pepper for the email HMAC, 32+ bytes (`openssl rand -base64 48`). Changing it orphans every `banned_identities` and `trial_consumed` row, so treat it as write-once |

```bash
supabase functions deploy entitlement account-delete
deno test --no-lock -q functions/     # no network, no secrets needed
```

Never set `BAN_HMAC_KEY` from the database or commit it. The `dev` and `prod` projects get different values.
Banning a user: `runbooks/ban-user.md`.

Run from `infra/supabase/` (or pass `--workdir`). Dashboard-only settings that `config.toml`
cannot express: leaked-password protection (paid plan, SR-15), the GitHub scope on the OAuth app,
and the dev project's extra redirect entry for the fake IdP seam.

## Redirect allow-list

`http://127.0.0.1:*/callback`. GoTrue matches `additional_redirect_urls` as glob patterns, where `*`
matches any run of non-`/` characters, so it covers the OS-assigned port. If a `supabase config push`
or a live OAuth attempt rejects it, fall back to a fixed range (for example ports 53682-53690 listed
one per entry) and make the CLI listener pick from that range. This was not exercised against a live project.

## Ed25519 keypair and kid rotation

```bash
openssl genpkey -algorithm ed25519 -out entitlement.pem
openssl pkey -in entitlement.pem -pubout -outform DER | tail -c 32 | base64   # public key for the CLI source
openssl pkcs8 -topk8 -nocrypt -in entitlement.pem -outform DER | base64       # value of the private key secret
```

Delete `entitlement.pem` after storing the secret. Never reuse a key across dev and prod.
Rotation: generate a new pair with a new `kid`, ship a CLI release that embeds both public keys,
wait until the old CLI versions age out, then `supabase secrets set` the new private key and `ENTITLEMENT_KID`,
and drop the old public key in a later release. Entitlements live at most 30 days, so the overlap is bounded.

## SMTP sender DNS

On the sender domain publish SPF (`v=spf1 include:<provider> -all`), the provider's DKIM CNAME/TXT
records, and DMARC (`_dmarc` TXT `v=DMARC1; p=quarantine; rua=mailto:dmarc@<domain>`; move to `reject` once clean).
Verify with the provider's checker and send a test OTP before enabling signups.

## Validation

`supabase start` validates `config.toml` locally. Keep `.env` out of git.
