/**
 * Quoting for the first task's command line (ADR-0030).
 *
 * The first task is opened in the user's own terminal, which means a command line that a
 * shell parses. Its pieces come from the CLI's launch map (flags, a prompt that contains
 * spaces and, for Codex, a `$`) and from a folder the user chose (any character the file
 * system allows). Nothing here concatenates those into a string a shell could re-read as
 * something else: every argument is quoted for the one shell that will read it, or the
 * quoting is refused.
 *
 * Three shells, three rules:
 *  - POSIX `sh`/`bash`/`zsh`: single quotes keep every character literal except `'`, which is
 *    closed, escaped and reopened (`'\''`). Complete for any string except NUL.
 *  - PowerShell: single quotes keep everything literal except `'`, which is doubled. The
 *    typographic single quotes PowerShell also treats as quotes are doubled too.
 *  - `cmd.exe` batch: there is no complete rule. Inside double quotes `%` still expands and a
 *    `"` cannot be escaped, so an argument with either, or with a line break, is refused
 *    (`null`) and the caller falls back to "copy the command".
 *
 * No module here imports `electron` or `node:*`: the renderer builds its "copy the command"
 * text with the same functions the main process builds the launch script with.
 */

/** Characters that never need quoting in a POSIX shell word. */
const POSIX_SAFE = /^[A-Za-z0-9_@%+=:,./-]+$/;

/** A string a shell can carry at all: no NUL byte. */
function hasNul(value: string): boolean {
  return value.includes('\0');
}

/**
 * One argument as a single POSIX shell word, or `null` for a NUL byte (not representable).
 * An empty string becomes `''`; a plain word is left bare so the copied text stays readable.
 */
export function quotePosix(value: string): string | null {
  if (hasNul(value)) return null;
  if (value === '') return "''";
  if (POSIX_SAFE.test(value)) return value;
  return `'${value.replace(/'/g, `'\\''`)}'`;
}

/** One argument as a single PowerShell word, or `null` for a NUL byte. */
export function quotePowerShell(value: string): string | null {
  if (hasNul(value)) return null;
  if (value === '') return "''";
  // A leading dash is fine bare: to a native command `--sandbox` is an ordinary argument, and
  // quoting the program name itself would turn it into a string (see `copyableCommand`).
  // No `,` (the array operator) and no `@` (splatting): both mean something bare.
  if (/^[A-Za-z0-9_+=:./\\-]+$/.test(value)) return value;
  // U+2018, U+2019, U+201A and U+201B are quote characters to PowerShell as well.
  return `'${value.replace(/['‘’‚‛]/g, (quote) => quote + quote)}'`;
}

/**
 * One argument as a `cmd.exe` word inside a batch file, or `null` when no quoting is safe:
 * `"` (cannot be escaped), `%` (expands even inside quotes), a line break, a NUL, or `!`
 * (expands under delayed expansion, which a user's registry setting can turn on).
 */
export function quoteCmd(value: string): string | null {
  if (/["%!\r\n\0]/.test(value)) return null;
  if (value === '') return '""';
  if (/^[A-Za-z0-9_@+=:,./\\-]+$/.test(value)) return value;
  return `"${value}"`;
}

/** Every argument quoted with `quote`, joined by a space; `null` when any one cannot be. */
export function joinQuoted(argv: readonly string[], quote: (value: string) => string | null): string | null {
  const words: string[] = [];
  for (const arg of argv) {
    const word = quote(arg);
    if (word === null) return null;
    words.push(word);
  }
  return words.join(' ');
}

/** Platforms the "copy the command" text is written for. Anything not Windows is a POSIX shell. */
export type CopyPlatform = 'win32' | 'posix';

/**
 * The line a user pastes into a terminal to do what the app would have done: change into the
 * folder and run the provider. PowerShell on Windows (Windows Terminal's default), a POSIX shell
 * elsewhere. `null` when an argument cannot be quoted for that shell.
 */
export function copyableCommand(platform: CopyPlatform, cwd: string, argv: readonly string[]): string | null {
  if (platform === 'win32') {
    const dir = quotePowerShell(cwd);
    const command = joinQuoted(argv, quotePowerShell);
    if (dir === null || command === null) return null;
    // A quoted program name is a string to PowerShell, not a command: it needs the call operator.
    return `Set-Location -LiteralPath ${dir}; ${command.startsWith("'") ? '& ' : ''}${command}`;
  }
  const dir = quotePosix(cwd);
  const command = joinQuoted(argv, quotePosix);
  return dir === null || command === null ? null : `cd ${dir} && ${command}`;
}
