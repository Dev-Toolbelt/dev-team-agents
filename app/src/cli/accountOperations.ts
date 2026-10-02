/**
 * The account operations (ADR-0029): one function per `devteam auth` command the UI offers.
 *
 * Same discipline as `operations.ts`, whose `run()` they go through: the argument vector is
 * built here from validated values, `COMMAND_SHAPES` is consulted before anything is
 * spawned, and the payload is checked for the keys the screen reads.
 *
 * **Secrets.** A code or a password goes to the child's stdin and nowhere else — no flag
 * can carry one — and is redacted from everything the child returns. A rejected value is
 * refused here with a *category* (`password-length`) and never echoes the value. Nothing in
 * this file logs.
 *
 * **No token is ever read.** The documents carry the account, the licence and a few
 * booleans; the session lives in the CLI's secret store.
 */

import {
  AUTH_PROVIDERS,
  DEFAULT_GATE_MODE,
  codeProblem,
  displayNameProblem,
  emailProblem,
  newPasswordProblem,
  normalizeCode,
  normalizeEmail,
  signInPasswordProblem,
  type FieldProblem,
} from '../shared/accountRules.js';
import type {
  AuthAccount,
  AuthDeleted,
  AuthDisplayName,
  AuthEmailChanged,
  AuthEntitlement,
  AuthGateMode,
  AuthIdentity,
  AuthIdentityLinked,
  AuthIdentityUnlinked,
  AuthLoggedOut,
  AuthPasswordChanged,
  AuthProfile,
  AuthProvider,
  AuthSent,
  AuthState,
  EntitlementStatus,
  OperationResult,
} from '../shared/api.js';
import { ranAndAnswered } from './contract.js';
import { invokeDevteam } from './invoke.js';
import { argvProblem, run, toOperationResult, type CliContext } from './operations.js';

/** A browser sign-in waits up to five minutes for the callback; the child gets a little more. */
export const OAUTH_TIMEOUT_MS = 6 * 60_000;

const STATUSES: readonly EntitlementStatus[] = [
  'active',
  'trial',
  'trial_expired',
  'banned',
  'needs_online_check',
  'signed_out',
  'invalid',
];

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null && !Array.isArray(value);
const text = (value: unknown): string | null => (typeof value === 'string' ? value : null);
const num = (value: unknown): number | null => (typeof value === 'number' && Number.isFinite(value) ? value : null);

function refused(command: string, problem: string): OperationResult<never> {
  return {
    ok: false,
    kind: 'refused',
    // A category, never the value.
    message: `\`devteam ${command}\` was refused: ${problem}`,
    exitCode: null,
    command: `devteam ${command}`,
    durationMs: 0,
  };
}

/** The first problem among `[label, problem]` pairs, as `label: problem`, or `null`. */
function firstProblem(...checks: readonly (readonly [string, FieldProblem | null])[]): string | null {
  for (const [label, problem] of checks) if (problem !== null) return `${label}: ${problem}`;
  return null;
}

// ── payload validation ────────────────────────────────────────────────────────────

function asAccount(raw: unknown): AuthAccount | null {
  if (!isRecord(raw) || typeof raw['id'] !== 'string') return null;
  return {
    id: raw['id'],
    email: text(raw['email']),
    display_name: text(raw['display_name']),
    provider: text(raw['provider']),
  };
}

function asEntitlement(raw: unknown): AuthEntitlement | string {
  if (!isRecord(raw)) return 'no `entitlement` object';
  const status = STATUSES.includes(raw['status'] as EntitlementStatus) ? (raw['status'] as EntitlementStatus) : 'invalid';
  return {
    status,
    reason: text(raw['reason']),
    features: Array.isArray(raw['features']) ? raw['features'].filter((f): f is string => typeof f === 'string') : [],
    trial_ends_at: num(raw['trial_ends_at']),
    expires_at: num(raw['expires_at']),
  };
}

/** `auth status|check|login|otp verify|password reset --finish`'s shared document. */
export function asAuthState(body: Record<string, unknown>): AuthState | string {
  if (typeof body['signed_in'] !== 'boolean') return 'no boolean `signed_in`';
  if (typeof body['entitled'] !== 'boolean') return 'no boolean `entitled`';
  const entitlement = asEntitlement(body['entitlement']);
  if (typeof entitlement === 'string') return entitlement;
  const online = isRecord(body['online']) ? body['online'] : {};
  const mode = body['gate_mode'];
  const gate: AuthGateMode = mode === 'warn' || mode === 'enforce' ? mode : DEFAULT_GATE_MODE;
  return {
    signed_in: body['signed_in'],
    account: asAccount(body['account']),
    entitled: body['entitled'],
    entitlement,
    online_ok: typeof online['ok'] === 'boolean' ? online['ok'] : null,
    secret_backend_insecure: body['secret_backend_insecure'] === true,
    warnings: Array.isArray(body['warnings']) ? body['warnings'].filter((w): w is string => typeof w === 'string') : [],
    gate_mode: gate,
  };
}

const asSent = (body: Record<string, unknown>): AuthSent | string =>
  body['sent'] === true ? { sent: true } : 'no `sent: true`';

function asIdentities(raw: unknown): AuthIdentity[] {
  if (!Array.isArray(raw)) return [];
  return raw.filter(isRecord).flatMap((item) =>
    typeof item['provider'] === 'string'
      ? [{ id: text(item['id']), provider: item['provider'], email: text(item['email']) }]
      : [],
  );
}

function asProfile(body: Record<string, unknown>): AuthProfile | string {
  const raw = body['account'];
  if (!isRecord(raw) || typeof raw['id'] !== 'string') return 'no `account`';
  return {
    id: raw['id'],
    email: text(raw['email']),
    display_name: text(raw['display_name']),
    signup_method: text(raw['signup_method']),
    identities: asIdentities(raw['identities']),
    pending_email: text(raw['pending_email']),
  };
}

const asDisplayName = (body: Record<string, unknown>): AuthDisplayName | string =>
  typeof body['display_name'] === 'string' ? { display_name: body['display_name'] } : 'no `display_name`';

const asEmailChanged = (body: Record<string, unknown>): AuthEmailChanged | string =>
  typeof body['confirmed'] === 'boolean' ? { confirmed: body['confirmed'], email: text(body['email']) } : 'no boolean `confirmed`';

const asPasswordChanged = (body: Record<string, unknown>): AuthPasswordChanged | string =>
  body['changed'] === true ? { changed: true, other_sessions_revoked: body['other_sessions_revoked'] === true } : 'no `changed: true`';

const asLinked = (body: Record<string, unknown>): AuthIdentityLinked | string =>
  typeof body['linked'] === 'string' ? { linked: body['linked'], identities: asIdentities(body['identities']) } : 'no `linked`';

const asUnlinked = (body: Record<string, unknown>): AuthIdentityUnlinked | string =>
  typeof body['unlinked'] === 'string' ? { unlinked: body['unlinked'] } : 'no `unlinked`';

const asDeleted = (body: Record<string, unknown>): AuthDeleted | string =>
  body['deleted'] === true ? { deleted: true } : 'no `deleted: true`';

const asLoggedOut = (body: Record<string, unknown>): AuthLoggedOut | string =>
  typeof body['signed_in'] === 'boolean'
    ? { signed_in: body['signed_in'], server_revoked: typeof body['server_revoked'] === 'boolean' ? body['server_revoked'] : null }
    : 'no boolean `signed_in`';

// ── reads ─────────────────────────────────────────────────────────────────────────

export function authStatus(context: CliContext): Promise<OperationResult<AuthState>> {
  return run(context, ['auth', 'status'], asAuthState);
}

/**
 * `auth check` exits 1 (not entitled) or 3 (an online check is needed and impossible) with
 * the *same document* plus `error`, so a blocked account arrives as an error document.
 * That is state the blocked screen renders, not a failure: it is returned `ok` with
 * `outcome: 'findings'` and `entitled: false`. An error document without that body (not
 * configured, lock) stays the failure it is.
 */
export async function authCheck(context: CliContext): Promise<OperationResult<AuthState>> {
  const args = ['auth', 'check'];
  const problem = argvProblem(args);
  if (problem !== null) return run(context, args, asAuthState);
  const result = await invokeDevteam({ ...context, args, timeoutMs: context.timeoutMs ?? 30_000 });
  if (ranAndAnswered(result) && result.document.kind === 'error' && isRecord(result.document.body['entitlement'])) {
    const state = asAuthState(result.document.body);
    if (typeof state !== 'string') {
      return { ok: true, outcome: 'findings', data: state, command: result.command.display, durationMs: result.durationMs };
    }
  }
  return toOperationResult(result, asAuthState);
}

export function authProfileGet(context: CliContext): Promise<OperationResult<AuthProfile>> {
  return run(context, ['auth', 'profile', 'show'], asProfile);
}

// ── sign-in ───────────────────────────────────────────────────────────────────────

const providerFlag = (provider: AuthProvider): string => `--${provider}`;
const providerProblem = (provider: unknown): string | null =>
  AUTH_PROVIDERS.includes(provider as AuthProvider) ? null : 'provider: unknown';

export function authLoginOAuth(context: CliContext, provider: AuthProvider): Promise<OperationResult<AuthState>> {
  const problem = providerProblem(provider);
  if (problem !== null) return Promise.resolve(refused('auth login', problem));
  return run({ ...context, timeoutMs: OAUTH_TIMEOUT_MS }, ['auth', 'login', providerFlag(provider)], asAuthState);
}

export function authOtpStart(context: CliContext, email: string, name: string | null): Promise<OperationResult<AuthSent>> {
  const problem = firstProblem(['email', emailProblem(email)], ['name', name === null ? null : displayNameProblem(name)]);
  if (problem !== null) return Promise.resolve(refused('auth otp start', problem));
  return run(
    context,
    ['auth', 'otp', 'start', '--email', normalizeEmail(email), ...(name === null ? [] : ['--name', name.trim()])],
    asSent,
  );
}

export function authOtpVerify(context: CliContext, email: string, code: string): Promise<OperationResult<AuthState>> {
  const problem = firstProblem(['email', emailProblem(email)], ['code', codeProblem(code)]);
  if (problem !== null) return Promise.resolve(refused('auth otp verify', problem));
  const secret = normalizeCode(code);
  return run(context, ['auth', 'otp', 'verify', '--email', normalizeEmail(email)], asAuthState, secret, [secret]);
}

export function authPasswordSignIn(context: CliContext, email: string, password: string): Promise<OperationResult<AuthState>> {
  const problem = firstProblem(['email', emailProblem(email)], ['password', signInPasswordProblem(password)]);
  if (problem !== null) return Promise.resolve(refused('auth login', problem));
  return run(
    context,
    ['auth', 'login', '--email', normalizeEmail(email), '--password'],
    asAuthState,
    password,
    [password],
  );
}

/**
 * Password sign-up, stage one: `auth login --email … --password --signup --send-code`. The
 * password goes to stdin, the CLI creates the account at the identity provider and mails
 * the confirmation code, and the process ends. Nothing is held between the stages; the
 * provider keeps the unconfirmed account.
 */
export function authPasswordSignUpSend(
  context: CliContext,
  email: string,
  password: string,
  name: string | null,
): Promise<OperationResult<AuthSent>> {
  const problem = firstProblem(
    ['email', emailProblem(email)],
    ['password', newPasswordProblem(password)],
    ['name', name === null ? null : displayNameProblem(name)],
  );
  if (problem !== null) return Promise.resolve(refused('auth login', problem));
  return run(
    context,
    [
      'auth', 'login', '--email', normalizeEmail(email), '--password', '--signup', '--send-code',
      ...(name === null ? [] : ['--name', name.trim()]),
    ],
    asSent,
    password,
    [password],
  );
}

/** Stage two: `auth login --email … --password --signup --finish`, the emailed code on stdin. */
export function authPasswordSignUpFinish(
  context: CliContext,
  email: string,
  code: string,
): Promise<OperationResult<AuthState>> {
  const problem = firstProblem(['email', emailProblem(email)], ['code', codeProblem(code)]);
  if (problem !== null) return Promise.resolve(refused('auth login', problem));
  const secret = normalizeCode(code);
  return run(
    context,
    ['auth', 'login', '--email', normalizeEmail(email), '--password', '--signup', '--finish'],
    asAuthState,
    secret,
    [secret],
  );
}

// ── password ──────────────────────────────────────────────────────────────────────

export function authPasswordResetStart(context: CliContext, email: string): Promise<OperationResult<AuthSent>> {
  const problem = firstProblem(['email', emailProblem(email)]);
  if (problem !== null) return Promise.resolve(refused('auth password reset', problem));
  return run(context, ['auth', 'password', 'reset', '--email', normalizeEmail(email), '--send-code'], asSent);
}

export function authPasswordResetFinish(
  context: CliContext,
  email: string,
  code: string,
  newPassword: string,
): Promise<OperationResult<AuthState>> {
  const problem = firstProblem(['email', emailProblem(email)], ['code', codeProblem(code)], ['password', newPasswordProblem(newPassword)]);
  if (problem !== null) return Promise.resolve(refused('auth password reset', problem));
  const secret = normalizeCode(code);
  return run(
    context,
    ['auth', 'password', 'reset', '--email', normalizeEmail(email), '--finish'],
    asAuthState,
    `${secret}\n${newPassword}`,
    [secret, newPassword],
  );
}

export function authPasswordChange(context: CliContext, current: string, next: string): Promise<OperationResult<AuthPasswordChanged>> {
  const problem = firstProblem(['current password', signInPasswordProblem(current)], ['new password', newPasswordProblem(next)]);
  if (problem !== null) return Promise.resolve(refused('auth password change', problem));
  return run(context, ['auth', 'password', 'change'], asPasswordChanged, `${current}\n${next}`, [current, next]);
}

// ── profile ───────────────────────────────────────────────────────────────────────

export function authProfileUpdate(context: CliContext, name: string): Promise<OperationResult<AuthDisplayName>> {
  const problem = firstProblem(['name', displayNameProblem(name)]);
  if (problem !== null) return Promise.resolve(refused('auth profile update', problem));
  return run(context, ['auth', 'profile', 'update', '--name', name.trim()], asDisplayName);
}

export function authEmailChangeStart(context: CliContext, newEmail: string): Promise<OperationResult<AuthSent>> {
  const problem = firstProblem(['email', emailProblem(newEmail)]);
  if (problem !== null) return Promise.resolve(refused('auth profile email', problem));
  return run(context, ['auth', 'profile', 'email', '--new', normalizeEmail(newEmail)], asSent);
}

export function authEmailChangeConfirm(
  context: CliContext,
  newEmail: string,
  codeNew: string,
  codeCurrent: string | null,
): Promise<OperationResult<AuthEmailChanged>> {
  const problem = firstProblem(
    ['email', emailProblem(newEmail)],
    ['code', codeProblem(codeNew)],
    ['current code', codeCurrent === null ? null : codeProblem(codeCurrent)],
  );
  if (problem !== null) return Promise.resolve(refused('auth profile email', problem));
  const first = normalizeCode(codeNew);
  const second = codeCurrent === null ? '' : normalizeCode(codeCurrent);
  return run(
    context,
    ['auth', 'profile', 'email', '--new', normalizeEmail(newEmail), '--confirm'],
    asEmailChanged,
    `${first}\n${second}`,
    second === '' ? [first] : [first, second],
  );
}

export function authIdentityLink(context: CliContext, provider: AuthProvider): Promise<OperationResult<AuthIdentityLinked>> {
  const problem = providerProblem(provider);
  if (problem !== null) return Promise.resolve(refused('auth profile link', problem));
  return run({ ...context, timeoutMs: OAUTH_TIMEOUT_MS }, ['auth', 'profile', 'link', providerFlag(provider)], asLinked);
}

export function authIdentityUnlink(context: CliContext, provider: AuthProvider): Promise<OperationResult<AuthIdentityUnlinked>> {
  const problem = providerProblem(provider);
  if (problem !== null) return Promise.resolve(refused('auth profile unlink', problem));
  return run(context, ['auth', 'profile', 'unlink', providerFlag(provider)], asUnlinked);
}

// ── delete and sign-out ───────────────────────────────────────────────────────────

export function authDeleteStart(context: CliContext): Promise<OperationResult<AuthSent>> {
  return run(context, ['auth', 'delete', '--send-code'], asSent);
}

export function authDeleteConfirm(context: CliContext, code: string): Promise<OperationResult<AuthDeleted>> {
  const problem = firstProblem(['code', codeProblem(code)]);
  if (problem !== null) return Promise.resolve(refused('auth delete', problem));
  const secret = normalizeCode(code);
  return run(context, ['auth', 'delete', '--yes'], asDeleted, secret, [secret]);
}

export function authLogout(context: CliContext): Promise<OperationResult<AuthLoggedOut>> {
  return run(context, ['auth', 'logout'], asLoggedOut);
}
