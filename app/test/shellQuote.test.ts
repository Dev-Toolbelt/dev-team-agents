/**
 * The first task's quoting helper (ADR-0030). The values it has to carry are the ones that break
 * hand-rolled quoting: spaces, both kinds of quote, `$`, backticks, backslashes, semicolons,
 * newlines and non-ASCII. On POSIX the strongest check is the real thing — hand the quoted text
 * to `sh` and compare what it hands back.
 */
import { spawnSync } from 'node:child_process';

import { describe, expect, it } from 'vitest';

import { copyableCommand, joinQuoted, quoteCmd, quotePosix, quotePowerShell } from '../src/shared/shellQuote.js';

const NASTY: readonly string[] = [
  'plain',
  'with space',
  "it's",
  'say "hi"',
  '$HOME and ${PATH} and $(whoami)',
  '`whoami`',
  'back\\slash \\n',
  'semi;colon && pipe | redirect > file',
  'glob * ? [a-z] ~',
  '!history',
  '#not-a-comment',
  'line one\nline two',
  '/devteam:audit src --report-only',
  '$devteam-audit /Users/jose maria/proj',
  'caf\u00e9 \u65e5\u672c\u8a9e \ud83d\ude80',
  '',
  "'",
  "''",
  '-leading-dash',
];

describe('quotePosix', () => {
  it('leaves a plain word bare, so the copied command stays readable', () => {
    expect(quotePosix('claude')).toBe('claude');
    expect(quotePosix('/usr/local/bin/claude')).toBe('/usr/local/bin/claude');
    expect(quotePosix('--permission-mode')).toBe('--permission-mode');
  });

  it('single-quotes spaces, and keeps `$` and backticks literal', () => {
    expect(quotePosix('with space')).toBe("'with space'");
    expect(quotePosix('$devteam-audit src')).toBe("'$devteam-audit src'");
    expect(quotePosix('`whoami`')).toBe("'`whoami`'");
  });

  it('closes, escapes and reopens around a single quote, and quotes the empty string', () => {
    expect(quotePosix("it's")).toBe(`'it'\\''s'`);
    expect(quotePosix('')).toBe("''");
  });

  it('refuses a NUL byte, which no shell word can hold', () => {
    expect(quotePosix('a\0b')).toBeNull();
  });

  it.skipIf(process.platform === 'win32')('round-trips every nasty value through a real shell', () => {
    for (const value of NASTY) {
      const quoted = quotePosix(value);
      expect(quoted, JSON.stringify(value)).not.toBeNull();
      // `printf '%s'` prints its argument exactly; a quoting hole would change or split it.
      const out = spawnSync('sh', ['-c', `printf '%s' ${quoted}`], { encoding: 'utf8' });
      expect(out.status, JSON.stringify(value)).toBe(0);
      expect(out.stdout, JSON.stringify(value)).toBe(value);
    }
  });

  it.skipIf(process.platform === 'win32')('keeps a whole argv as separate words through a real shell', () => {
    const argv = ['claude', '--permission-mode', 'plan', '$devteam-audit /Users/jose maria/proj --report-only'];
    const line = joinQuoted(argv, quotePosix)!;
    const out = spawnSync('sh', ['-c', `for a in ${line}; do printf '[%s]' "$a"; done`], { encoding: 'utf8' });
    expect(out.stdout).toBe(argv.map((a) => `[${a}]`).join(''));
  });
});

describe('quotePowerShell', () => {
  it('single-quotes, doubling an embedded single quote', () => {
    expect(quotePowerShell('with space')).toBe("'with space'");
    expect(quotePowerShell("it's")).toBe("'it''s'");
    expect(quotePowerShell('$HOME `x` "y"')).toBe(`'$HOME \`x\` "y"'`);
  });

  it('doubles the typographic quotes PowerShell also treats as quotes', () => {
    expect(quotePowerShell('\u2018a\u2019')).toBe("'\u2018\u2018a\u2019\u2019'");
  });

  it('leaves a flag bare, quotes `%`, and refuses NUL', () => {
    expect(quotePowerShell('--sandbox')).toBe('--sandbox');
    expect(quotePowerShell('100%')).toBe("'100%'");
    expect(quotePowerShell('a\0')).toBeNull();
  });
});

describe('quoteCmd', () => {
  it('quotes spaces and keeps unicode and `$` literal', () => {
    expect(quoteCmd('C:\\Users\\Jos\u00e9 Maria\\proj')).toBe('"C:\\Users\\Jos\u00e9 Maria\\proj"');
    expect(quoteCmd('$HOME')).toBe('"$HOME"');
    expect(quoteCmd('claude')).toBe('claude');
  });

  it('refuses the characters no cmd.exe quoting can carry: a double quote, `%`, `!`, a line break, NUL', () => {
    for (const bad of ['say "hi"', '100%', '%PATH%', 'wow!', 'a\nb', 'a\r', 'a\0']) {
      expect(quoteCmd(bad), JSON.stringify(bad)).toBeNull();
    }
  });
});

describe('joinQuoted and copyableCommand', () => {
  it('uses the call operator when the program name itself needs quoting in PowerShell', () => {
    expect(copyableCommand('win32', 'C:\\proj', ['C:\\Program Files\\tool.exe', 'a'])).toBe(
      "Set-Location -LiteralPath C:\\proj; & 'C:\\Program Files\\tool.exe' a",
    );
  });

  it('gives null when any one word cannot be quoted', () => {
    expect(joinQuoted(['a', 'b"c'], quoteCmd)).toBeNull();
  });

  it('writes a cd-and-run line for a POSIX shell', () => {
    expect(copyableCommand('posix', '/Users/jose maria/proj', ['claude', '--permission-mode', 'plan', '/devteam:audit src'])).toBe(
      "cd '/Users/jose maria/proj' && claude --permission-mode plan '/devteam:audit src'",
    );
  });

  it('writes a Set-Location line for PowerShell', () => {
    expect(copyableCommand('win32', 'C:\\Users\\Jos\u00e9\\my proj', ['codex', '--sandbox', 'read-only', '$devteam-audit src'])).toBe(
      "Set-Location -LiteralPath 'C:\\Users\\Jos\u00e9\\my proj'; codex --sandbox read-only '$devteam-audit src'",
    );
  });
});
