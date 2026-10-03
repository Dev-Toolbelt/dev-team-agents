/**
 * The `devteam auth` commands this app may run (ADR-0029), kept apart from
 * `operations.ts` so that file does not grow by another screen's worth and so
 * `accountOperations.ts` can import the shapes without a cycle.
 *
 * Every leaf is `compat.STORE_NEUTRAL` — it writes only machine-local session records or the
 * remote account, never a declared store shape, and a user must always be able to sign in —
 * so they join `READ_ONLY_COMMANDS` (the never-refused set), not `GATED_COMMANDS`. `test/operations.test.ts` checks that against
 * `compat.py` itself.
 *
 * **No flag takes a secret.** A code or a password is read by the CLI from stdin, one per
 * line in the order it prompts (`CLAUDE-md/cli.md` § Account), so nothing here can carry one.
 */

export const ACCOUNT_COMMANDS: readonly (readonly string[])[] = Object.freeze([
  ['auth', 'login'],
  ['auth', 'logout'],
  ['auth', 'status'],
  ['auth', 'check'],
  ['auth', 'otp', 'start'],
  ['auth', 'otp', 'verify'],
  ['auth', 'password', 'reset'],
  ['auth', 'password', 'change'],
  ['auth', 'profile', 'show'],
  ['auth', 'profile', 'update'],
  ['auth', 'profile', 'email'],
  ['auth', 'profile', 'link'],
  ['auth', 'profile', 'unlink'],
  ['auth', 'delete'],
]);

type Shape = {
  readonly operands: 0 | 1 | 2 | 3;
  readonly flags: Readonly<Record<string, 'value' | 'bare' | 'repeatable'>>;
};

const PROVIDER_FLAGS = { '--google': 'bare', '--github': 'bare' } as const;

/** Keyed like `COMMAND_SHAPES`: the command words joined with a space. */
export const ACCOUNT_SHAPES: Readonly<Record<string, Shape>> = Object.freeze({
  'auth login': {
    operands: 0,
    flags: { ...PROVIDER_FLAGS, '--email': 'value', '--password': 'bare', '--signup': 'bare', '--send-code': 'bare', '--finish': 'bare', '--name': 'value' },
  },
  'auth logout': { operands: 0, flags: {} },
  'auth status': { operands: 0, flags: {} },
  'auth check': { operands: 0, flags: {} },
  'auth otp start': { operands: 0, flags: { '--email': 'value', '--name': 'value' } },
  'auth otp verify': { operands: 0, flags: { '--email': 'value' } },
  'auth password reset': { operands: 0, flags: { '--email': 'value', '--send-code': 'bare', '--finish': 'bare' } },
  'auth password change': { operands: 0, flags: {} },
  'auth profile show': { operands: 0, flags: {} },
  'auth profile update': { operands: 0, flags: { '--name': 'value' } },
  'auth profile email': { operands: 0, flags: { '--new': 'value', '--confirm': 'bare' } },
  'auth profile link': { operands: 0, flags: PROVIDER_FLAGS },
  'auth profile unlink': { operands: 0, flags: PROVIDER_FLAGS },
  'auth delete': { operands: 0, flags: { '--yes': 'bare', '--send-code': 'bare' } },
});
