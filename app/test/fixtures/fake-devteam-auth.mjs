#!/usr/bin/env node
/**
 * A fake `devteam` for the account tests (`test/accountOperations.test.ts`) only.
 *
 * It answers the `auth` commands with documents shaped like `scripts/lib/devteam/auth.py`'s,
 * reads secrets from stdin exactly as the real CLI does (one per line, in the order it
 * prompts), and appends every invocation — argv and the stdin lines it received — to the
 * JSONL file named by `FAKE_AUTH_LOG`, so a test can assert that a secret reached stdin and
 * never argv. The scenario (`FAKE_AUTH_SCENARIO`) only chooses what `status`/`check` say.
 *
 * Accepted secrets: code `12345678`, password `correct-horse-battery`. Anything else is the
 * CLI's fixed rejection.
 */

import { appendFileSync } from 'node:fs';
import { createInterface } from 'node:readline';

const args = process.argv.slice(2);
const clientSchemas = args.indexOf('--client-schemas');
if (clientSchemas !== -1) args.splice(clientSchemas, 2);
const json = args.indexOf('--json');
if (json !== -1) args.splice(json, 1);

const log = process.env['FAKE_AUTH_LOG'];
const scenario = process.env['FAKE_AUTH_SCENARIO'] ?? 'entitled';
const received = [];
const record = () => {
  if (log !== undefined) appendFileSync(log, `${JSON.stringify({ argv: args, stdin: received })}\n`);
};

const lines = [];
const waiting = [];
let closed = false;
const reader = createInterface({ input: process.stdin });
reader.on('line', (line) => {
  received.push(line);
  const next = waiting.shift();
  if (next !== undefined) next(line);
  else lines.push(line);
});
reader.on('close', () => {
  closed = true;
  for (const next of waiting.splice(0)) next(null);
});
function nextLine() {
  if (lines.length > 0) return Promise.resolve(lines.shift());
  if (closed) return Promise.resolve(null);
  return new Promise((resolve) => waiting.push(resolve));
}

const emit = (body) => process.stdout.write(`${JSON.stringify(body)}\n`);
function fail(code, error, reason, extra = {}) {
  emit({ ok: false, error, exit_code: code, details: { reason }, ...extra });
  process.exitCode = code;
}

const ACCOUNT = { id: 'acc-1', email: 'ana@example.com', display_name: 'Ana Souza', provider: 'email', signed_in_at: 1 };
const ENTITLEMENT = { status: 'active', reason: null, token_status: 'valid', features: [], trial_ends_at: null, expires_at: 2_000_000_000 };
function state(overrides = {}) {
  return {
    ok: true,
    signed_in: true,
    account: ACCOUNT,
    entitled: true,
    entitlement: ENTITLEMENT,
    online: { attempted: true, ok: true },
    last_online_check: 1,
    secret_backend: 'keychain',
    secret_backend_insecure: false,
    environment: 'prod',
    gate_mode: process.env['FAKE_AUTH_GATE_MODE'] ?? 'warn',
    test_seam: false,
    warnings: [],
    ...overrides,
  };
}

async function main() {
  const [a, b, c] = args.slice(1);
  const command = args[0] === 'auth' ? [a, ...(b !== undefined && !b.startsWith('-') ? [b] : []), ...(c !== undefined && !c.startsWith('-') && b !== undefined && !b.startsWith('-') ? [c] : [])].join(' ') : args[0];

  if (args[0] !== 'auth') return fail(2, `unknown command ${command}`, 'usage');

  if (a === 'status' || a === 'check') {
    if (scenario === 'entitled') return emit(state());
    const status = scenario === 'signed_out' ? 'signed_out' : scenario;
    const view = state({
      signed_in: status !== 'signed_out',
      account: status === 'signed_out' ? null : ACCOUNT,
      entitled: false,
      entitlement: { ...ENTITLEMENT, status, reason: status },
    });
    if (a === 'status') return emit(view);
    emit({ ...view, ok: false, error: 'the trial for this account has ended', exit_code: 1, hint: 'Run `devteam auth status`.', details: { reason: status } });
    process.exitCode = status === 'needs_online_check' ? 3 : 1;
    return undefined;
  }

  if (a === 'login') {
    if (args.includes('--google') || args.includes('--github')) return emit(state({ method: 'oauth' }));
    if (args.includes('--signup') && args.includes('--send-code')) {
      const password = await nextLine();
      if (scenario === 'signup_unreachable') return fail(3, 'the account server could not be reached', 'unreachable');
      if (password === null || password.length < 10) return fail(2, 'the password must be 10 to 64 characters and at most 72 bytes in UTF-8', 'usage');
      return emit({ ok: true, sent: true, message: 'If this address can sign in, a code was sent to it.', expires_in: 600 });
    }
    if (args.includes('--signup') && args.includes('--finish')) {
      const code = await nextLine();
      return code === '12345678' ? emit(state({ method: 'password-signup' })) : fail(1, 'the code is invalid or has expired', 'invalid_code');
    }
    if (args.includes('--signup')) {
      const password = await nextLine();
      if (scenario === 'signup_unreachable') return fail(3, 'the account server could not be reached', 'unreachable');
      if (password === null || password.length < 10) return fail(2, 'the password must be 10 to 64 characters and at most 72 bytes in UTF-8', 'usage');
      const code = await nextLine();
      return code === '12345678' ? emit(state({ method: 'password-signup' })) : fail(1, 'the code is invalid or has expired', 'invalid_code');
    }
    const password = await nextLine();
    return password === 'correct-horse-battery' ? emit(state({ method: 'password' })) : fail(1, 'invalid credentials', 'invalid_credentials');
  }
  if (a === 'otp' && b === 'start') return emit({ ok: true, sent: true, message: 'If this address can sign in, a code was sent to it.', expires_in: 600 });
  if (a === 'otp' && b === 'verify') {
    const code = await nextLine();
    return code === '12345678' ? emit(state({ method: 'email-otp' })) : fail(1, 'the code is invalid or has expired', 'invalid_code');
  }
  if (a === 'password' && b === 'reset') {
    if (args.includes('--send-code')) return emit({ ok: true, sent: true });
    const code = await nextLine();
    const password = await nextLine();
    if (code !== '12345678') return fail(1, 'the code is invalid or has expired', 'invalid_code');
    return password !== null && password.length >= 10 ? emit(state({ method: 'password-reset' })) : fail(2, 'bad password', 'usage');
  }
  if (a === 'password' && b === 'change') {
    const current = await nextLine();
    const next = await nextLine();
    if (current !== 'correct-horse-battery') return fail(1, 'invalid credentials', 'invalid_credentials');
    return next === null ? fail(2, 'expected a value on stdin', 'usage') : emit({ ok: true, changed: true, other_sessions_revoked: true });
  }
  if (a === 'profile' && (b === 'show' || b === undefined || b.startsWith('-'))) {
    return emit({
      ok: true,
      account: {
        id: 'acc-1',
        email: 'ana@example.com',
        display_name: 'Ana Souza',
        signup_method: 'email',
        created_at: '2026-01-01',
        identities: [{ id: 'i-1', provider: 'email', email: 'ana@example.com' }],
        pending_email: null,
      },
    });
  }
  if (a === 'profile' && b === 'update') return emit({ ok: true, display_name: args[args.indexOf('--name') + 1] });
  if (a === 'profile' && b === 'email') {
    if (!args.includes('--confirm')) return emit({ ok: true, sent: true, pending_email: args[args.indexOf('--new') + 1] });
    const first = await nextLine();
    await nextLine();
    return first === '12345678' ? emit({ ok: true, confirmed: true, email: args[args.indexOf('--new') + 1] }) : fail(1, 'the code is invalid or has expired', 'invalid_code');
  }
  if (a === 'profile' && b === 'link') return emit({ ok: true, linked: args.includes('--google') ? 'google' : 'github', identities: [] });
  if (a === 'profile' && b === 'unlink') {
    return scenario === 'last_identity'
      ? fail(1, 'that is the only way to sign in to this account', 'last_identity')
      : emit({ ok: true, unlinked: args.includes('--google') ? 'google' : 'github' });
  }
  if (a === 'delete') {
    if (args.includes('--send-code')) return emit({ ok: true, sent: true });
    const code = await nextLine();
    return code === '12345678' ? emit({ ok: true, deleted: true, signed_in: false }) : fail(1, 'the code is invalid or has expired', 'invalid_code');
  }
  if (a === 'logout') return emit({ ok: true, signed_in: false, was_signed_in: true, server_revoked: true });
  return fail(2, `unhandled ${command}`, 'usage');
}

await main();
record();
reader.close();
