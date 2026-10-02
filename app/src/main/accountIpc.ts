/**
 * The IPC channels for the account (ADR-0029): one per named operation in `shared/api.ts`.
 *
 * Every channel runs a `devteam auth` command through `cli/accountOperations.ts`; the
 * renderer supplies values (an address, a code, a password) and never a command. Every
 * argument is re-checked here and again by the operation — a type is a compile-time claim
 * and this is a process boundary. **Nothing the renderer sends is logged or kept**: a code
 * or password lives in the one call that carries it, and the single piece of state this
 * module holds is the child process of a password sign-up that is waiting for its emailed
 * code (`SignUpFlow`), which holds the password only inside that child's own stdin.
 */

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
  authPasswordSignUp,
  authProfileGet,
  authProfileUpdate,
  authStatus,
} from '../cli/accountOperations.js';
import type { CliContext } from '../cli/operations.js';
import { AUTH_PROVIDERS, codeProblem, normalizeCode } from '../shared/accountRules.js';
import { CHANNELS, type AuthProvider, type AuthSignUpPending, type AuthState, type OperationResult } from '../shared/api.js';

/**
 * How long a sign-up child is watched for an early refusal before the screen moves on to
 * the code step. The CLI says nothing under `--json` when the code is sent, so "still
 * running after this long" is the only signal that it got past the password policy and the
 * network call; anything slower is simply reported when the code is submitted.
 */
export const SIGNUP_SETTLE_MS = 4_000;

type Failure = Extract<OperationResult<never>, { ok: false }>;

function refusedArgument(command: string): Failure {
  return {
    ok: false,
    kind: 'refused',
    message: `\`devteam ${command}\` was not given an argument this app recognises.`,
    exitCode: null,
    command: `devteam ${command}`,
    durationMs: 0,
  };
}

const NO_CLI: Failure = {
  ok: false,
  kind: 'unavailable',
  message: 'No `devteam` CLI was found on this host.',
  hint: 'Install it with the devteam installer, or point the app at one with DEVTEAM_CLI_PATH.',
  exitCode: null,
  command: 'devteam',
  durationMs: 0,
};

interface PendingSignUp {
  readonly final: Promise<OperationResult<AuthState>>;
  readonly submitCode: (code: string | null) => void;
  settled: OperationResult<AuthState> | null;
}

/**
 * The one password sign-up in flight. A second `start` ends the first; `finish` hands the
 * emailed code to the waiting child and returns what it answers; `cancel` ends it.
 */
export class SignUpFlow {
  private pending: PendingSignUp | null = null;

  constructor(private readonly settleMs: number = SIGNUP_SETTLE_MS) {}

  async start(
    context: CliContext,
    email: string,
    password: string,
    name: string | null,
  ): Promise<OperationResult<AuthSignUpPending>> {
    this.cancel();
    let submitCode!: (code: string | null) => void;
    const code = new Promise<string | null>((resolve) => {
      submitCode = resolve;
    });
    const entry: PendingSignUp = {
      final: authPasswordSignUp(context, email, password, name, code),
      submitCode,
      settled: null,
    };
    void entry.final.then((result) => {
      entry.settled = result;
    });
    this.pending = entry;

    let timer: ReturnType<typeof setTimeout> | undefined;
    const waited = new Promise<null>((resolve) => {
      timer = setTimeout(() => resolve(null), this.settleMs);
    });
    const early = await Promise.race([entry.final, waited]);
    clearTimeout(timer);
    if (early === null) {
      return {
        ok: true,
        outcome: 'success',
        data: { pending: true },
        command: 'devteam auth login',
        durationMs: this.settleMs,
      };
    }
    if (this.pending === entry) this.pending = null;
    if (!early.ok) return early;
    // It cannot finish without a code; a document here means the CLI changed.
    return {
      ok: false,
      kind: 'contract-breach',
      message: '`devteam auth login` finished before it was given the emailed code.',
      exitCode: null,
      command: early.command,
      durationMs: early.durationMs,
    };
  }

  async finish(code: string): Promise<OperationResult<AuthState>> {
    const entry = this.pending;
    if (entry === null) {
      return {
        ok: false,
        kind: 'refused',
        message: 'No sign-up is waiting for a code. Start again.',
        exitCode: null,
        command: 'devteam auth login',
        durationMs: 0,
      };
    }
    // A malformed code is refused *before* it is sent: the CLI reads one code and ends, so
    // a typo that reached it would cost the whole sign-up.
    const problem = codeProblem(code);
    if (problem !== null) return { ...refusedArgument('auth login'), message: `\`devteam auth login\` was refused: code: ${problem}` };
    if (entry.settled === null) entry.submitCode(normalizeCode(code));
    this.pending = null;
    return entry.final;
  }

  cancel(): void {
    const entry = this.pending;
    this.pending = null;
    if (entry !== null && entry.settled === null) entry.submitCode(null);
  }
}

export interface AccountIpcDeps {
  /** `ipcMain.handle` behind the sender check — see `trustedHandler` in `security.ts`. */
  readonly handle: (channel: string, listener: (event: unknown, ...args: unknown[]) => unknown) => void;
  readonly context: () => Promise<CliContext | null>;
  readonly signUpSettleMs?: number;
}

const isString = (value: unknown): value is string => typeof value === 'string';
const isProvider = (value: unknown): value is AuthProvider => AUTH_PROVIDERS.includes(value as AuthProvider);

export function registerAccountIpc(deps: AccountIpcDeps): { readonly signUp: SignUpFlow } {
  const signUp = new SignUpFlow(deps.signUpSettleMs);
  const { handle } = deps;

  /** Resolve the CLI, then run `call` with it; `NO_CLI` when none was found. */
  async function withCli<T>(call: (ctx: CliContext) => Promise<OperationResult<T>>): Promise<OperationResult<T>> {
    const ctx = await deps.context();
    return ctx === null ? NO_CLI : call(ctx);
  }

  handle(CHANNELS.authStatus, () => withCli(authStatus));
  handle(CHANNELS.authCheck, () => withCli(authCheck));
  handle(CHANNELS.authLogout, () => withCli(authLogout));
  handle(CHANNELS.authProfileGet, () => withCli(authProfileGet));
  handle(CHANNELS.authDeleteStart, () => withCli(authDeleteStart));

  handle(CHANNELS.authLoginOAuth, (_event, provider) =>
    isProvider(provider) ? withCli((ctx) => authLoginOAuth(ctx, provider)) : refusedArgument('auth login'),
  );
  handle(CHANNELS.authOtpStart, (_event, email, name) =>
    isString(email) && (name === null || isString(name))
      ? withCli((ctx) => authOtpStart(ctx, email, name))
      : refusedArgument('auth otp start'),
  );
  handle(CHANNELS.authOtpVerify, (_event, email, code) =>
    isString(email) && isString(code) ? withCli((ctx) => authOtpVerify(ctx, email, code)) : refusedArgument('auth otp verify'),
  );
  handle(CHANNELS.authPasswordSignIn, (_event, email, password) =>
    isString(email) && isString(password)
      ? withCli((ctx) => authPasswordSignIn(ctx, email, password))
      : refusedArgument('auth login'),
  );

  handle(CHANNELS.authPasswordSignUpStart, (_event, email, password, name) =>
    isString(email) && isString(password) && (name === null || isString(name))
      ? withCli((ctx) => signUp.start(ctx, email, password, name))
      : refusedArgument('auth login'),
  );
  handle(CHANNELS.authPasswordSignUpFinish, (_event, code) =>
    isString(code) ? signUp.finish(code) : refusedArgument('auth login'),
  );
  handle(CHANNELS.authPasswordSignUpCancel, () => {
    signUp.cancel();
  });

  handle(CHANNELS.authPasswordResetStart, (_event, email) =>
    isString(email) ? withCli((ctx) => authPasswordResetStart(ctx, email)) : refusedArgument('auth password reset'),
  );
  handle(CHANNELS.authPasswordResetFinish, (_event, email, code, password) =>
    isString(email) && isString(code) && isString(password)
      ? withCli((ctx) => authPasswordResetFinish(ctx, email, code, password))
      : refusedArgument('auth password reset'),
  );
  handle(CHANNELS.authPasswordChange, (_event, current, next) =>
    isString(current) && isString(next) ? withCli((ctx) => authPasswordChange(ctx, current, next)) : refusedArgument('auth password change'),
  );
  handle(CHANNELS.authProfileUpdate, (_event, name) =>
    isString(name) ? withCli((ctx) => authProfileUpdate(ctx, name)) : refusedArgument('auth profile update'),
  );
  handle(CHANNELS.authEmailChangeStart, (_event, email) =>
    isString(email) ? withCli((ctx) => authEmailChangeStart(ctx, email)) : refusedArgument('auth profile email'),
  );
  handle(CHANNELS.authEmailChangeConfirm, (_event, email, codeNew, codeCurrent) =>
    isString(email) && isString(codeNew) && (codeCurrent === null || isString(codeCurrent))
      ? withCli((ctx) => authEmailChangeConfirm(ctx, email, codeNew, codeCurrent))
      : refusedArgument('auth profile email'),
  );
  handle(CHANNELS.authIdentityLink, (_event, provider) =>
    isProvider(provider) ? withCli((ctx) => authIdentityLink(ctx, provider)) : refusedArgument('auth profile link'),
  );
  handle(CHANNELS.authIdentityUnlink, (_event, provider) =>
    isProvider(provider) ? withCli((ctx) => authIdentityUnlink(ctx, provider)) : refusedArgument('auth profile unlink'),
  );
  handle(CHANNELS.authDeleteConfirm, (_event, code) =>
    isString(code) ? withCli((ctx) => authDeleteConfirm(ctx, code)) : refusedArgument('auth delete'),
  );

  return { signUp };
}
