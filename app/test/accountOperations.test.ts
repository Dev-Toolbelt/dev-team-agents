/**
 * The account operations and the main-process boundary around them (ADR-0029), against
 * `fixtures/fake-devteam-auth.mjs`, which logs every invocation's argv and stdin.
 *
 * What these tests protect: a code or a password reaches the CLI on **stdin and nowhere
 * else** (never argv, never the result), a malformed value is refused before anything is
 * spawned, a blocked account is data rather than an error, and a held password sign-up is
 * completed, refused early or cancelled without leaving a process behind.
 *
 * Windows has no way to spawn the `.mjs` fixture with `shell: false` and the launcher the
 * other fixtures use is built per fixture; these cases are skipped there.
 */

import { mkdtemp, readFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

import { afterEach, beforeEach, describe, expect, it } from 'vitest';

import {
  authCheck,
  authDeleteConfirm,
  authDeleteStart,
  authEmailChangeConfirm,
  authEmailChangeStart,
  authIdentityLink,
  authIdentityUnlink,
  authLoginOAuth,
  authLogout,
  authOtpStart,
  authOtpVerify,
  authPasswordChange,
  authPasswordResetFinish,
  authPasswordResetStart,
  authPasswordSignIn,
  authProfileGet,
  authProfileUpdate,
  authStatus,
} from '../src/cli/accountOperations.js';
import type { CliContext } from '../src/cli/operations.js';
import { registerAccountIpc, SignUpFlow } from '../src/main/accountIpc.js';
import { CHANNELS } from '../src/shared/api.js';

const FAKE = fileURLToPath(new URL('./fixtures/fake-devteam-auth.mjs', import.meta.url));
const skipOnWindows = process.platform === 'win32';

let dir: string;
let logPath: string;

beforeEach(async () => {
  dir = await mkdtemp(join(tmpdir(), 'devteam-app-auth-'));
  logPath = join(dir, 'log.jsonl');
});
afterEach(async () => {
  await rm(dir, { recursive: true, force: true });
});

const context = (scenario = 'entitled', gateMode?: string): CliContext => ({
  binary: FAKE,
  cwd: dir,
  env: { FAKE_AUTH_LOG: logPath, FAKE_AUTH_SCENARIO: scenario, ...(gateMode === undefined ? {} : { FAKE_AUTH_GATE_MODE: gateMode }) },
});

interface Logged {
  readonly argv: readonly string[];
  readonly stdin: readonly string[];
}
async function invocations(): Promise<Logged[]> {
  const raw = await readFile(logPath, 'utf8').catch(() => '');
  return raw
    .split('\n')
    .filter((line) => line !== '')
    .map((line) => JSON.parse(line) as Logged);
}

const GOOD_CODE = '12345678';
const GOOD_PASSWORD = 'correct-horse-battery';

describe.skipIf(skipOnWindows)('reads', () => {
  it('maps `auth status` and keeps no token-like field', async () => {
    const result = await authStatus(context());
    expect(result.ok).toBe(true);
    if (!result.ok) throw new Error('unreachable');
    expect(result.data).toMatchObject({
      signed_in: true,
      entitled: true,
      account: { email: 'ana@example.com', display_name: 'Ana Souza' },
      entitlement: { status: 'active' },
      gate_mode: 'warn',
    });
    expect(JSON.stringify(result.data)).not.toMatch(/token|secret_backend\b/);
  });

  it('reads gate_mode from the status and check documents', async () => {
    const status = await authStatus(context('entitled', 'enforce'));
    expect(status.ok && status.data.gate_mode).toBe('enforce');
    const check = await authCheck(context('trial_expired', 'enforce'));
    expect(check.ok && check.data.gate_mode).toBe('enforce');
  });

  it('returns a not-entitled `auth check` (exit 1) as ok data with entitled: false', async () => {
    const result = await authCheck(context('trial_expired'));
    expect(result.ok).toBe(true);
    if (!result.ok) throw new Error('unreachable');
    expect(result.outcome).toBe('findings');
    expect(result.data.entitled).toBe(false);
    expect(result.data.entitlement.status).toBe('trial_expired');
  });

  it('returns the exit-3 online-check refusal the same way', async () => {
    const result = await authCheck(context('needs_online_check'));
    expect(result.ok && result.data.entitlement.status).toBe('needs_online_check');
  });

  it('reads signed-out as data too', async () => {
    const result = await authCheck(context('signed_out'));
    expect(result.ok && result.data.signed_in).toBe(false);
  });

  it('maps the profile with its identities', async () => {
    const result = await authProfileGet(context());
    expect(result.ok && result.data.identities).toEqual([{ id: 'i-1', provider: 'email', email: 'ana@example.com' }]);
  });
});

describe.skipIf(skipOnWindows)('secrets travel on stdin only', () => {
  it('sends an OTP code on stdin, not argv, and keeps it out of the result', async () => {
    const result = await authOtpVerify(context(), ' Ana@Example.com ', '1234 5678');
    expect(result.ok).toBe(true);
    const [call] = await invocations();
    expect(call?.argv).toEqual(['auth', 'otp', 'verify', '--email', 'ana@example.com']);
    expect(call?.stdin).toEqual([GOOD_CODE]);
    expect(JSON.stringify(result)).not.toContain(GOOD_CODE);
  });

  it('sends a sign-in password on stdin', async () => {
    const result = await authPasswordSignIn(context(), 'ana@example.com', GOOD_PASSWORD);
    expect(result.ok).toBe(true);
    const [call] = await invocations();
    expect(call?.argv).toEqual(['auth', 'login', '--email', 'ana@example.com', '--password']);
    expect(call?.argv.join(' ')).not.toContain(GOOD_PASSWORD);
    expect(call?.stdin).toEqual([GOOD_PASSWORD]);
  });

  it('turns a rejection into a failure with the CLI reason and no echo of the value', async () => {
    const result = await authPasswordSignIn(context(), 'ana@example.com', 'wrong-password-here');
    expect(result.ok).toBe(false);
    if (result.ok) throw new Error('unreachable');
    expect(result.reason).toBe('invalid_credentials');
    expect(JSON.stringify(result)).not.toContain('wrong-password-here');
  });

  it('reset --finish reads the code then the new password, in that order', async () => {
    const result = await authPasswordResetFinish(context(), 'ana@example.com', GOOD_CODE, 'a-brand-new-password');
    expect(result.ok).toBe(true);
    const [call] = await invocations();
    expect(call?.argv).toEqual(['auth', 'password', 'reset', '--email', 'ana@example.com', '--finish']);
    expect(call?.stdin).toEqual([GOOD_CODE, 'a-brand-new-password']);
  });

  it('password change reads current then new', async () => {
    const result = await authPasswordChange(context(), GOOD_PASSWORD, 'a-brand-new-password');
    expect(result.ok && result.data).toEqual({ changed: true, other_sessions_revoked: true });
    const [call] = await invocations();
    expect(call?.stdin).toEqual([GOOD_PASSWORD, 'a-brand-new-password']);
    expect(call?.argv).toEqual(['auth', 'password', 'change']);
  });

  it('email change confirm sends both codes, the second empty when skipped', async () => {
    await authEmailChangeConfirm(context(), 'new@example.com', GOOD_CODE, null);
    await authEmailChangeConfirm(context(), 'new@example.com', GOOD_CODE, '87654321');
    const calls = await invocations();
    expect(calls[0]?.argv).toEqual(['auth', 'profile', 'email', '--new', 'new@example.com', '--confirm']);
    // An empty second line is the same as end-of-input to the CLI's optional read.
    expect(calls[0]?.stdin).toEqual([GOOD_CODE]);
    expect(calls[1]?.stdin).toEqual([GOOD_CODE, '87654321']);
  });

  it('delete is send-code then yes with the code on stdin', async () => {
    expect((await authDeleteStart(context())).ok).toBe(true);
    expect((await authDeleteConfirm(context(), GOOD_CODE)).ok).toBe(true);
    const calls = await invocations();
    expect(calls[0]?.argv).toEqual(['auth', 'delete', '--send-code']);
    expect(calls[1]?.argv).toEqual(['auth', 'delete', '--yes']);
    expect(calls[1]?.stdin).toEqual([GOOD_CODE]);
  });
});

describe.skipIf(skipOnWindows)('the other commands build exactly the argv the CLI documents', () => {
  it('builds each one', async () => {
    await authLoginOAuth(context(), 'google');
    await authOtpStart(context(), 'ana@example.com', 'Ana');
    await authPasswordResetStart(context(), 'ana@example.com');
    await authProfileUpdate(context(), '  Ana S  ');
    await authEmailChangeStart(context(), 'New@Example.com');
    await authIdentityLink(context(), 'github');
    await authIdentityUnlink(context(), 'google');
    await authLogout(context());
    expect((await invocations()).map((call) => call.argv)).toEqual([
      ['auth', 'login', '--google'],
      ['auth', 'otp', 'start', '--email', 'ana@example.com', '--name', 'Ana'],
      ['auth', 'password', 'reset', '--email', 'ana@example.com', '--send-code'],
      ['auth', 'profile', 'update', '--name', 'Ana S'],
      ['auth', 'profile', 'email', '--new', 'new@example.com'],
      ['auth', 'profile', 'link', '--github'],
      ['auth', 'profile', 'unlink', '--google'],
      ['auth', 'logout'],
    ]);
  });

  it('reports unlinking the last identity with its reason', async () => {
    const result = await authIdentityUnlink(context('last_identity'), 'google');
    expect(!result.ok && result.reason).toBe('last_identity');
  });
});

describe.skipIf(skipOnWindows)('refusals happen before anything is spawned', () => {
  it.each([
    ['a malformed address', () => authOtpStart(context(), 'not-an-address', null)],
    ['an address that would read as a flag', () => authOtpStart(context(), '-x@y.zz', null)],
    ['a name that would read as a flag', () => authProfileUpdate(context(), '--yes')],
    ['a code that is not 8 digits', () => authOtpVerify(context(), 'ana@example.com', '123')],
    ['a short new password', () => authPasswordResetFinish(context(), 'ana@example.com', GOOD_CODE, 'short')],
    ['a password with a line break', () => authPasswordSignIn(context(), 'ana@example.com', 'a\nb')],
    ['a delete code that is not digits', () => authDeleteConfirm(context(), 'abcdefgh')],
    ['an unknown provider', () => authIdentityLink(context(), 'myspace' as 'google')],
  ])('refuses %s', async (_name, call) => {
    const result = await call();
    expect(result.ok).toBe(false);
    if (result.ok) throw new Error('unreachable');
    expect(result.kind).toBe('refused');
    expect(result.durationMs).toBe(0);
    expect(await invocations()).toEqual([]);
  });

  it('names the category of the problem and never the value', async () => {
    const result = await authPasswordResetFinish(context(), 'ana@example.com', GOOD_CODE, 'tiny-pw');
    if (result.ok) throw new Error('unreachable');
    expect(result.message).toContain('password-length');
    expect(result.message).not.toContain('tiny-pw');
  });
});

describe.skipIf(skipOnWindows)('SignUpFlow: a two-stage password sign-up', () => {
  const start = (flow: SignUpFlow, password = GOOD_PASSWORD) =>
    flow.start(context(), 'ana@example.com', password, 'Ana');

  it('sends the password at start, the code at finish, in two runs, and signs in', async () => {
    const flow = new SignUpFlow();
    const started = await start(flow);
    expect(started.ok && started.data).toEqual({ pending: true });
    const finished = await flow.finish(context(), '1234 5678');
    expect(finished.ok && finished.data.signed_in).toBe(true);
    const [first, second] = await invocations();
    expect(first?.argv).toEqual([
      'auth', 'login', '--email', 'ana@example.com', '--password', '--signup', '--send-code', '--name', 'Ana',
    ]);
    expect(first?.stdin).toEqual([GOOD_PASSWORD]);
    expect(second?.argv).toEqual(['auth', 'login', '--email', 'ana@example.com', '--password', '--signup', '--finish']);
    expect(second?.stdin).toEqual([GOOD_CODE]);
    expect(JSON.stringify([started, finished])).not.toContain(GOOD_PASSWORD);
  });

  it('reports a failure from start itself, and holds nothing', async () => {
    const flow = new SignUpFlow();
    const started = await flow.start(context('signup_unreachable'), 'ana@example.com', GOOD_PASSWORD, null);
    expect(started.ok).toBe(false);
    if (started.ok) throw new Error('unreachable');
    expect(started.reason).toBe('unreachable');
    expect(JSON.stringify(started)).not.toContain(GOOD_PASSWORD);
    expect((await flow.finish(context(), GOOD_CODE)).ok).toBe(false);
  });

  it('refuses a malformed code without sending it, so the sign-up survives a typo', async () => {
    const flow = new SignUpFlow();
    await start(flow);
    const bad = await flow.finish(context(), '12ab');
    expect(bad.ok).toBe(false);
    if (bad.ok) throw new Error('unreachable');
    expect(bad.kind).toBe('refused');
    expect(await invocations()).toHaveLength(1);
    expect((await flow.finish(context(), GOOD_CODE)).ok).toBe(true);
  });

  it('finish with nothing pending is refused and spawns nothing', async () => {
    const flow = new SignUpFlow();
    expect((await flow.finish(context(), GOOD_CODE)).ok).toBe(false);
    expect(await invocations()).toEqual([]);
  });

  it('cancel forgets the pending sign-up', async () => {
    const flow = new SignUpFlow();
    await start(flow);
    flow.cancel();
    expect((await flow.finish(context(), GOOD_CODE)).ok).toBe(false);
    expect(await invocations()).toHaveLength(1);
  });

  it('a wrong code is reported and the sign-up stays open for a retry', async () => {
    const flow = new SignUpFlow();
    await start(flow);
    const result = await flow.finish(context(), '00000000');
    expect(!result.ok && result.reason).toBe('invalid_code');
    expect((await flow.finish(context(), GOOD_CODE)).ok).toBe(true);
  });
});

describe.skipIf(skipOnWindows)('the IPC handlers', () => {
  type Handler = (event: unknown, ...args: unknown[]) => unknown;
  function register(ctx: CliContext | null) {
    const handlers = new Map<string, Handler>();
    const flow = registerAccountIpc({
      handle: (channel, listener) => {
        handlers.set(channel, listener);
      },
      context: () => Promise.resolve(ctx),
    });
    return { handlers, flow, call: (channel: string, ...args: unknown[]) => handlers.get(channel)?.({}, ...args) };
  }

  it('registers a handler for every account channel', () => {
    const { handlers } = register(context());
    const channels = Object.entries(CHANNELS).filter(([name]) => name.startsWith('auth'));
    expect(channels.length).toBeGreaterThanOrEqual(21);
    for (const [, channel] of channels) expect(handlers.has(channel), channel).toBe(true);
  });

  it('answers unavailable when no CLI was found', async () => {
    const { call } = register(null);
    const result = (await call(CHANNELS.authCheck)) as { ok: boolean; kind?: string };
    expect(result).toMatchObject({ ok: false, kind: 'unavailable' });
  });

  it.each([
    [CHANNELS.authOtpStart, [42, null]],
    [CHANNELS.authOtpVerify, ['a@b.co', 12345678]],
    [CHANNELS.authPasswordSignIn, ['a@b.co', { password: 'x' }]],
    [CHANNELS.authPasswordSignUpStart, ['a@b.co', null, null]],
    [CHANNELS.authPasswordSignUpFinish, [12345678]],
    [CHANNELS.authPasswordResetFinish, ['a@b.co', GOOD_CODE, undefined]],
    [CHANNELS.authPasswordChange, [GOOD_PASSWORD, 7]],
    [CHANNELS.authEmailChangeConfirm, ['a@b.co', GOOD_CODE, 5]],
    [CHANNELS.authIdentityLink, ['facebook']],
    [CHANNELS.authLoginOAuth, [{}]],
    [CHANNELS.authDeleteConfirm, [null]],
  ])('refuses a wrongly typed argument on %s without spawning', async (channel, args) => {
    const { call } = register(context());
    const result = (await call(channel, ...args)) as { ok: boolean; kind?: string; durationMs?: number };
    expect(result).toMatchObject({ ok: false, kind: 'refused', durationMs: 0 });
    expect(await invocations()).toEqual([]);
  });

  it('runs a valid sign-in end to end', async () => {
    const { call } = register(context());
    const result = (await call(CHANNELS.authPasswordSignIn, 'ana@example.com', GOOD_PASSWORD)) as { ok: boolean };
    expect(result.ok).toBe(true);
  });

  it('drives the held sign-up through its three channels', async () => {
    const { call } = register(context());
    expect(await call(CHANNELS.authPasswordSignUpStart, 'ana@example.com', GOOD_PASSWORD, null)).toMatchObject({ ok: true, data: { pending: true } });
    expect(await call(CHANNELS.authPasswordSignUpFinish, GOOD_CODE)).toMatchObject({ ok: true });
    await call(CHANNELS.authPasswordSignUpCancel);
  });
});
