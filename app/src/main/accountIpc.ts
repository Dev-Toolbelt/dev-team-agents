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
  authPasswordSignUpFinish,
  authPasswordSignUpSend,
  authProfileGet,
  authProfileUpdate,
  authStatus,
} from '../cli/accountOperations.js';
import type { CliContext } from '../cli/operations.js';
import { AUTH_PROVIDERS } from '../shared/accountRules.js';
import { CHANNELS, type AuthProvider, type AuthSignUpPending, type AuthState, type OperationResult } from '../shared/api.js';

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

/**
 * The one password sign-up in flight, as two CLI runs: `start` sends the confirmation code
 * (`--send-code`) and remembers the address; `finish` completes it (`--finish`) with the
 * code. Only the address is held here; the provider keeps the unconfirmed account. A
 * wrong code leaves the sign-up open so the user can retype it; `cancel` forgets it.
 */
export class SignUpFlow {
  private email: string | null = null;

  async start(
    context: CliContext,
    email: string,
    password: string,
    name: string | null,
  ): Promise<OperationResult<AuthSignUpPending>> {
    this.cancel();
    const sent = await authPasswordSignUpSend(context, email, password, name);
    if (!sent.ok) return sent;
    this.email = email;
    return { ...sent, data: { pending: true } };
  }

  async finish(context: CliContext, code: string): Promise<OperationResult<AuthState>> {
    const email = this.email;
    if (email === null) {
      return {
        ok: false,
        kind: 'refused',
        message: 'No sign-up is waiting for a code. Start again.',
        exitCode: null,
        command: 'devteam auth login',
        durationMs: 0,
      };
    }
    const result = await authPasswordSignUpFinish(context, email, code);
    if (result.ok && this.email === email) this.email = null;
    return result;
  }

  cancel(): void {
    this.email = null;
  }
}

export interface AccountIpcDeps {
  /** `ipcMain.handle` behind the sender check — see `trustedHandler` in `security.ts`. */
  readonly handle: (channel: string, listener: (event: unknown, ...args: unknown[]) => unknown) => void;
  readonly context: () => Promise<CliContext | null>;
}

const isString = (value: unknown): value is string => typeof value === 'string';
const isProvider = (value: unknown): value is AuthProvider => AUTH_PROVIDERS.includes(value as AuthProvider);

export function registerAccountIpc(deps: AccountIpcDeps): { readonly signUp: SignUpFlow } {
  const signUp = new SignUpFlow();
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
    isString(code) ? withCli((ctx) => signUp.finish(ctx, code)) : refusedArgument('auth login'),
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
