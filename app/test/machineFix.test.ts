/**
 * "Fix" for a machine prerequisite (ADR-0030): only a plain command runs, never through a shell.
 */
import { describe, expect, it, vi } from 'vitest';

import { fixEnvironment, parseFixCommand, runMachineFix } from '../src/main/machineFix.js';

describe('parseFixCommand', () => {
  it('splits a plain command into words', () => {
    expect(parseFixCommand('brew install git')).toEqual(['brew', 'install', 'git']);
    expect(parseFixCommand('  devteam   store   install ')).toEqual(['devteam', 'store', 'install']);
  });

  it('refuses anything a shell would act on', () => {
    for (const bad of [
      'brew install git && rm -rf ~',
      'a | b',
      'a; b',
      'echo $HOME',
      'echo `x`',
      'a > /etc/x',
      "echo 'x'",
      'echo "x"',
      'a\nb',
      'a \\ b',
      '$(x)',
      'curl x | sh',
    ]) {
      expect(parseFixCommand(bad), bad).toBeNull();
    }
  });

  it('refuses an empty command, a program name that is not a plain name, and an overlong one', () => {
    expect(parseFixCommand('')).toBeNull();
    expect(parseFixCommand('   ')).toBeNull();
    expect(parseFixCommand('-x install')).toBeNull();
    expect(parseFixCommand(Array.from({ length: 20 }, () => 'a').join(' '))).toBeNull();
  });
});

describe('fixEnvironment', () => {
  it('appends the Homebrew and user bin directories off Windows, keeping the user’s own first', () => {
    const env = fixEnvironment({ PATH: '/usr/bin:/bin', HOME: '/Users/jose' }, 'darwin');
    expect(env['PATH']).toBe('/usr/bin:/bin:/opt/homebrew/bin:/usr/local/bin:/Users/jose/.local/bin');
  });

  it('does not repeat one already there, and leaves Windows alone', () => {
    expect(fixEnvironment({ PATH: '/opt/homebrew/bin:/bin' }, 'darwin')['PATH']).toBe('/opt/homebrew/bin:/bin:/usr/local/bin');
    const win = { PATH: 'C:\\x' };
    expect(fixEnvironment(win, 'win32')).toBe(win);
  });
});

describe('runMachineFix', () => {
  const env = { PATH: '/usr/bin' };

  it('runs the words with no shell and reports success', async () => {
    const run = vi.fn(() => Promise.resolve({ code: 0, output: '' }));
    const answer = await runMachineFix({ platform: 'darwin', env, cliPath: null, run }, 'brew install git');
    expect(answer).toEqual({ ran: true, succeeded: true, message: 'Done.' });
    expect(run).toHaveBeenCalledWith('brew', ['install', 'git'], expect.objectContaining({ PATH: expect.stringContaining('/opt/homebrew/bin') }));
  });

  it('runs `devteam` as the CLI the app resolved', async () => {
    const run = vi.fn(() => Promise.resolve({ code: 0, output: '' }));
    await runMachineFix({ platform: 'darwin', env, cliPath: '/opt/homebrew/bin/devteam', run }, 'devteam store install');
    expect(run).toHaveBeenCalledWith('/opt/homebrew/bin/devteam', ['store', 'install'], expect.anything());
  });

  it('reports a failed fix with the tail of its output', async () => {
    const run = vi.fn(() => Promise.resolve({ code: 1, output: 'Error: no network' }));
    const answer = await runMachineFix({ platform: 'darwin', env, cliPath: null, run }, 'brew install git');
    expect(answer).toMatchObject({ ran: true, succeeded: false, message: expect.stringContaining('no network') });
  });

  it('does not run a command that needs a shell', async () => {
    const run = vi.fn();
    const answer = await runMachineFix({ platform: 'darwin', env, cliPath: null, run }, 'curl x | sh');
    expect(answer.ran).toBe(false);
    expect(run).not.toHaveBeenCalled();
  });
});
