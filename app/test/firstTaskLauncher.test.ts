/**
 * Opening the first task in the user's terminal (ADR-0030): what script is written, what is
 * spawned, and what is refused — with a fake spawner and fake file writes, so no terminal opens.
 */
import { spawnSync } from 'node:child_process';

import { describe, expect, it, vi } from 'vitest';

import {
  batchScript,
  launchArgvProblem,
  launchInTerminal,
  posixScript,
  terminalCommands,
  type LauncherDeps,
  type Spawnable,
} from '../src/main/firstTaskLauncher.js';

const ARGV = ['claude', '--permission-mode', 'plan', '/devteam:audit src --report-only'];

describe('launchArgvProblem', () => {
  it('accepts a launch map argv', () => {
    expect(launchArgvProblem(ARGV)).toBeNull();
    expect(launchArgvProblem(['codex', '--sandbox', 'read-only', '$devteam-audit src'])).toBeNull();
  });

  it('refuses anything that is not a short list of strings starting with a plain program name', () => {
    expect(launchArgvProblem([])).not.toBeNull();
    expect(launchArgvProblem('claude')).not.toBeNull();
    expect(launchArgvProblem([1, 2])).not.toBeNull();
    expect(launchArgvProblem(['/bin/sh', '-c', 'x'])).not.toBeNull();
    expect(launchArgvProblem(['rm -rf', 'x'])).not.toBeNull();
    expect(launchArgvProblem(['-rf'])).not.toBeNull();
    expect(launchArgvProblem(['claude', 'a\0b'])).not.toBeNull();
    expect(launchArgvProblem(['claude', 'x'.repeat(5000)])).not.toBeNull();
  });
});

describe('posixScript', () => {
  it('removes itself, adds the usual bin directories after the user’s PATH, cds and runs the quoted argv', () => {
    const script = posixScript('/Users/jose maria/my proj', ARGV)!;
    const lines = script.split('\n');
    expect(lines[0]).toBe('#!/bin/sh');
    expect(lines).toContain('rm -f -- "$0"');
    expect(lines).toContain('PATH="$PATH:/opt/homebrew/bin:/usr/local/bin:$HOME/.local/bin"');
    expect(lines).toContain("cd -- '/Users/jose maria/my proj' || exit 1");
    expect(lines).toContain("claude --permission-mode plan '/devteam:audit src --report-only'");
  });

  it('never lets a hostile folder name or argument become a command', () => {
    const folder = "/tmp/a'; touch /tmp/pwned; echo '";
    const script = posixScript(folder, ['claude', '$(touch /tmp/pwned2)', '`touch /tmp/pwned3`'])!;
    if (process.platform === 'win32') return;
    // Replace the real program with `printf` so the script runs, and check it ran as data.
    const harmless = script
      .replace('rm -f -- "$0"\n', '')
      .replace(/^claude /m, 'printf "[%s]" ')
      .replace(`cd -- `, 'true ')
      .replace(' || exit 1', '');
    const out = spawnSync('sh', ['-c', harmless], { encoding: 'utf8' });
    expect(out.stdout).toBe('[$(touch /tmp/pwned2)][`touch /tmp/pwned3`]');
  });

  it('refuses a NUL byte', () => {
    expect(posixScript('/a', ['claude', 'a\0b'])).toBeNull();
  });
});

describe('batchScript', () => {
  it('cds to the folder with /d and runs the argv, CRLF line endings', () => {
    const script = batchScript('C:\\Users\\Jos\u00e9 Maria\\proj', ARGV)!;
    expect(script.split('\r\n')).toEqual([
      '@echo off',
      'cd /d "C:\\Users\\Jos\u00e9 Maria\\proj"',
      'claude --permission-mode plan "/devteam:audit src --report-only"',
      '',
    ]);
  });

  it('refuses a value with no safe cmd.exe quoting rather than guessing', () => {
    expect(batchScript('C:\\proj', ['claude', '100%'])).toBeNull();
    expect(batchScript('C:\\proj', ['claude', 'say "hi"'])).toBeNull();
    expect(batchScript('C:\\100%\\proj', ['claude'])).toBeNull();
  });
});

describe('terminalCommands', () => {
  it('opens a .command script with `open -a Terminal` on macOS, the path as an argument', () => {
    expect(terminalCommands('darwin', '/tmp/x/first-task.command')).toEqual([
      { command: 'open', args: ['-a', 'Terminal', '/tmp/x/first-task.command'] },
    ]);
  });

  it('tries Windows Terminal first and falls back to cmd on Windows', () => {
    const commands = terminalCommands('win32', 'C:\\Temp\\x\\first-task.cmd');
    expect(commands.map((c) => c.command)).toEqual(['wt.exe', 'cmd.exe']);
    expect(commands[0]!.args).toEqual(['cmd.exe', '/k', 'C:\\Temp\\x\\first-task.cmd']);
    expect(commands[1]!.args).toEqual(['/d', '/c', 'start', '', 'cmd.exe', '/k', 'C:\\Temp\\x\\first-task.cmd']);
  });

  it('skips Windows Terminal for a path with `;`, which it would read as a command separator', () => {
    expect(terminalCommands('win32', 'C:\\a;b\\x.cmd').map((c) => c.command)).toEqual(['cmd.exe']);
  });

  it('has nothing for another system', () => {
    expect(terminalCommands('linux', '/tmp/x')).toEqual([]);
  });
});

describe('launchInTerminal', () => {
  function deps(overrides: Partial<LauncherDeps> = {}) {
    const written: { path: string; content: string }[] = [];
    const started: Spawnable[] = [];
    const base: LauncherDeps = {
      platform: 'darwin',
      tempDir: '/tmp',
      makeDir: (prefix) => Promise.resolve(`/tmp/${prefix}abc`),
      writeScript: (path, content) => {
        written.push({ path, content });
        return Promise.resolve();
      },
      start: (spec) => {
        started.push(spec);
        return Promise.resolve(true);
      },
      ...overrides,
    };
    return { base, written, started };
  }

  it('writes the script and opens Terminal on it', async () => {
    const { base, written, started } = deps();
    expect(await launchInTerminal(base, '/work/my app', ARGV)).toEqual({ launched: true });
    expect(written).toHaveLength(1);
    expect(written[0]!.path).toBe('/tmp/devteam-first-task-abc/first-task.command');
    expect(written[0]!.content).toContain("cd -- '/work/my app'");
    expect(started).toEqual([{ command: 'open', args: ['-a', 'Terminal', written[0]!.path] }]);
  });

  it('falls back from Windows Terminal to cmd when the first cannot start', async () => {
    const attempts: string[] = [];
    const { base } = deps({
      platform: 'win32',
      start: (spec) => {
        attempts.push(spec.command);
        return Promise.resolve(spec.command !== 'wt.exe');
      },
    });
    expect(await launchInTerminal(base, 'C:\\work', ARGV)).toEqual({ launched: true });
    expect(attempts).toEqual(['wt.exe', 'cmd.exe']);
  });

  it('reports no terminal when nothing could start', async () => {
    const { base } = deps({ start: () => Promise.resolve(false) });
    expect(await launchInTerminal(base, '/work', ARGV)).toMatchObject({ launched: false });
  });

  it('writes and spawns nothing for an argv it refuses, a folder with an unquotable character, or Linux', async () => {
    const spy = vi.fn(() => Promise.resolve(true));
    const { base, written } = deps({ start: spy });
    expect(await launchInTerminal(base, '/work', ['/bin/sh', '-c', 'x'])).toMatchObject({ launched: false });
    expect(await launchInTerminal(deps({ platform: 'win32', start: spy }).base, 'C:\\100%', ['claude'])).toMatchObject({ launched: false });
    expect(await launchInTerminal(deps({ platform: 'linux', start: spy }).base, '/work', ARGV)).toMatchObject({ launched: false });
    expect(spy).not.toHaveBeenCalled();
    expect(written).toEqual([]);
  });

  it('says so when the script cannot be written', async () => {
    const { base } = deps({ writeScript: () => Promise.reject(new Error('disk full')) });
    expect(await launchInTerminal(base, '/work', ARGV)).toMatchObject({ launched: false, message: expect.stringContaining('disk full') });
  });
});
