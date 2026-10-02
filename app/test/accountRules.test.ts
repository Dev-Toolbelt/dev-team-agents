/**
 * The account input rules, the admitted `auth` argv shapes, and the preload bridge's
 * handling of values that must reach main untouched.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ACCOUNT_COMMANDS } from '../src/cli/accountCommands.js';
import { ALLOWED_COMMANDS, GATED_COMMANDS, READ_ONLY_COMMANDS, argvProblem } from '../src/cli/operations.js';
import {
  codeProblem,
  displayNameProblem,
  emailProblem,
  initialsOf,
  newPasswordProblem,
  normalizeCode,
  normalizeEmail,
  signInPasswordProblem,
} from '../src/shared/accountRules.js';
import { CHANNELS, type DevteamBridge } from '../src/shared/api.js';

describe('input rules mirror the CLI', () => {
  it('normalises an address like the CLI does', () => {
    expect(normalizeEmail('  Ana.Souza@Example.COM ')).toBe('ana.souza@example.com');
    expect(emailProblem('ana@example.com')).toBeNull();
    expect(emailProblem('')).toBe('required');
    expect(emailProblem('ana@example')).toBe('email-invalid');
    expect(emailProblem('a b@example.com')).toBe('email-invalid');
    expect(emailProblem('-a@example.com')).toBe('email-invalid');
    expect(emailProblem(`${'a'.repeat(250)}@b.co`)).toBe('email-invalid');
  });

  it('wants exactly eight digits, ignoring spaces', () => {
    expect(normalizeCode(' 1234 5678 ')).toBe('12345678');
    expect(codeProblem('1234 5678')).toBeNull();
    expect(codeProblem('1234567')).toBe('code-invalid');
    expect(codeProblem('1234567a')).toBe('code-invalid');
    expect(codeProblem('')).toBe('required');
  });

  it('applies the password policy only to a password being set', () => {
    expect(newPasswordProblem('x'.repeat(9))).toBe('password-length');
    expect(newPasswordProblem('x'.repeat(10))).toBeNull();
    expect(newPasswordProblem('x'.repeat(64))).toBeNull();
    expect(newPasswordProblem('x'.repeat(65))).toBe('password-length');
    // 40 characters but 80 bytes in UTF-8: over the 72-byte limit.
    expect(newPasswordProblem('é'.repeat(40))).toBe('password-length');
    expect(newPasswordProblem('a\nb'.padEnd(12, 'c'))).toBe('unsafe-text');
    // A sign-in presents what was accepted earlier, so a short one is not refused here.
    expect(signInPasswordProblem('short')).toBeNull();
    expect(signInPasswordProblem('')).toBe('required');
    expect(signInPasswordProblem('a\rb')).toBe('unsafe-text');
  });

  it('bounds the display name and keeps it from reading as a flag', () => {
    expect(displayNameProblem('Ana Souza')).toBeNull();
    expect(displayNameProblem('   ')).toBe('required');
    expect(displayNameProblem('x'.repeat(81))).toBe('name-invalid');
    expect(displayNameProblem('--yes')).toBe('name-invalid');
    expect(displayNameProblem('a\u0000b')).toBe('name-invalid');
  });

  it('draws initials from the name, else the address, else a placeholder', () => {
    expect(initialsOf('ana souza', 'x@y.co')).toBe('AS');
    expect(initialsOf('Ana Maria de Souza', null)).toBe('AM');
    expect(initialsOf('Ana', null)).toBe('A');
    expect(initialsOf(null, 'zeca@example.com')).toBe('Z');
    expect(initialsOf('  ', '')).toBe('?');
  });
});

describe('the `auth` commands this app may run', () => {
  it('are all read-only for the compat gate, none of them gated', () => {
    const flat = (list: readonly (readonly string[])[]) => list.map((c) => c.join(' '));
    for (const command of flat(ACCOUNT_COMMANDS)) {
      expect(flat(READ_ONLY_COMMANDS), command).toContain(command);
      expect(flat(GATED_COMMANDS), command).not.toContain(command);
    }
    expect(flat(ALLOWED_COMMANDS).filter((c) => c.startsWith('auth')).sort()).toEqual(flat(ACCOUNT_COMMANDS).sort());
  });

  it('accept the documented shapes', () => {
    expect(argvProblem(['auth', 'login', '--google'])).toBeNull();
    expect(argvProblem(['auth', 'login', '--email', 'a@b.co', '--password', '--signup', '--name', 'Ana'])).toBeNull();
    expect(argvProblem(['auth', 'otp', 'start', '--email', 'a@b.co'])).toBeNull();
    expect(argvProblem(['auth', 'password', 'reset', '--email', 'a@b.co', '--finish'])).toBeNull();
    expect(argvProblem(['auth', 'profile', 'email', '--new', 'a@b.co', '--confirm'])).toBeNull();
    expect(argvProblem(['auth', 'delete', '--send-code'])).toBeNull();
    expect(argvProblem(['auth', 'delete', '--yes'])).toBeNull();
  });

  it('have no flag and no operand that could carry a secret', () => {
    // A password or code given as an operand, or under any flag, is refused by the boundary.
    expect(argvProblem(['auth', 'login', '--email', 'a@b.co', '--password', 'hunter2hunter2'])).not.toBeNull();
    expect(argvProblem(['auth', 'otp', 'verify', '--email', 'a@b.co', '--code', '12345678'])).not.toBeNull();
    expect(argvProblem(['auth', 'otp', 'verify', '--email', 'a@b.co', '12345678'])).not.toBeNull();
    expect(argvProblem(['auth', 'delete', '--yes', '12345678'])).not.toBeNull();
    expect(argvProblem(['auth', 'password', 'change', 'old', 'new'])).not.toBeNull();
    expect(argvProblem(['auth', 'login', '--token', 'x'])).not.toBeNull();
  });

  it('refuse subcommands the UI does not offer', () => {
    expect(argvProblem(['auth'])).not.toBeNull();
    expect(argvProblem(['auth', 'profile', 'identities'])).not.toBeNull();
  });
});

const invoke = vi.fn(() => Promise.resolve(undefined));
let exposed: DevteamBridge | null = null;
vi.mock('electron', () => ({
  ipcRenderer: { invoke: (...args: unknown[]) => (invoke as (...a: unknown[]) => unknown)(...args), on: vi.fn(), removeListener: vi.fn() },
  contextBridge: {
    exposeInMainWorld: (_name: string, api: unknown) => {
      exposed = api as DevteamBridge;
    },
  },
}));

describe('preload bridge — account', () => {
  beforeEach(async () => {
    invoke.mockClear();
    await import('../src/preload/index.js');
  });

  it('forwards each value as a plain string on its own channel and nothing else', async () => {
    await exposed!.authOtpVerify('a@b.co', '12345678');
    await exposed!.authPasswordSignUpStart('a@b.co', 'a-long-password', null);
    await exposed!.authEmailChangeConfirm('n@b.co', '12345678', null);
    await exposed!.authPasswordChange('old-password-1', 'new-password-1');
    expect(invoke.mock.calls).toEqual([
      [CHANNELS.authOtpVerify, 'a@b.co', '12345678'],
      [CHANNELS.authPasswordSignUpStart, 'a@b.co', 'a-long-password', null],
      [CHANNELS.authEmailChangeConfirm, 'n@b.co', '12345678', null],
      [CHANNELS.authPasswordChange, 'old-password-1', 'new-password-1'],
    ]);
  });

  it('exposes no generic way to run a command', () => {
    const names = Object.keys(exposed!).filter((name) => name.startsWith('auth'));
    expect(names.length).toBeGreaterThanOrEqual(21);
    expect(Object.keys(exposed!)).not.toContain('invoke');
    expect(Object.keys(exposed!)).not.toContain('run');
  });
});
