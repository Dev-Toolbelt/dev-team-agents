/**
 * How a resolved `devteam` is started on Windows. Pure: the platform and the file system
 * are injected, so this runs on every host and never spawns anything.
 */

import { describe, expect, it } from 'vitest';

import { childEnvironment } from '../src/cli/invoke.js';
import { findWindowsPython, isAbsoluteEntry, launchCommand } from '../src/cli/launch.js';

const SCRIPT = 'C:\\repo\\scripts\\cli\\devteam';

function present(...files: string[]): (path: string) => boolean {
  return (path) => files.includes(path);
}

describe('launchCommand', () => {
  it('leaves POSIX untouched', () => {
    expect(launchCommand('/opt/devteam', ['list'], { PATH: '/usr/bin' }, 'darwin', () => true)).toEqual({
      command: '/opt/devteam',
      args: ['list'],
    });
  });

  it('spawns a real .exe directly on Windows', () => {
    const exe = 'C:\\Program Files\\devteam\\devteam.exe';
    expect(launchCommand(exe, ['list'], { PATH: 'C:\\Python' }, 'win32', () => true)).toEqual({
      command: exe,
      args: ['list'],
    });
  });

  it('runs an extensionless script through py.exe -3 first', () => {
    const env = { Path: 'C:\\Windows;C:\\Python312' };
    const launch = launchCommand(
      SCRIPT,
      ['list', '--json'],
      env,
      'win32',
      present(SCRIPT, 'C:\\Python312\\python.exe', 'C:\\Windows\\py.exe'),
    );
    expect(launch).toEqual({ command: 'C:\\Windows\\py.exe', args: ['-3', SCRIPT, 'list', '--json'] });
  });

  it('falls back to python.exe', () => {
    const launch = launchCommand(SCRIPT, ['x'], { PATH: 'C:\\Python312' }, 'win32', present(SCRIPT, 'C:\\Python312\\python.exe'));
    expect(launch).toEqual({ command: 'C:\\Python312\\python.exe', args: [SCRIPT, 'x'] });
  });

  it('returns the binary unchanged when no interpreter exists, so the spawn reports its own error', () => {
    expect(launchCommand(SCRIPT, ['x'], { PATH: 'C:\\Nope' }, 'win32', () => false)).toEqual({
      command: SCRIPT,
      args: ['x'],
    });
  });

  it('leaves a missing binary to the spawn, so it reports not-found instead of a python exit', () => {
    const launch = launchCommand(SCRIPT, ['x'], { PATH: 'C:\\Python312' }, 'win32', present('C:\\Python312\\python.exe'));
    expect(launch).toEqual({ command: SCRIPT, args: ['x'] });
  });

  it('never picks an interpreter from a relative or drive-relative PATH entry', () => {
    const env = { PATH: '.;bin;\\tools;/tools;C:py' };
    const seen: string[] = [];
    expect(
      findWindowsPython(env, 'win32', (path) => {
        seen.push(path);
        return true;
      }),
    ).toBeNull();
    expect(seen).toEqual([]);
  });

  it('never looks for .cmd or .bat', () => {
    const seen: string[] = [];
    findWindowsPython({ PATH: 'C:\\Bin' }, 'win32', (path) => {
      seen.push(path);
      return false;
    });
    expect(seen.sort()).toEqual(['C:\\Bin\\py.exe', 'C:\\Bin\\python.exe']);
  });
});

describe('isAbsoluteEntry', () => {
  it('is strict on Windows', () => {
    expect(isAbsoluteEntry('C:\\a', 'win32')).toBe(true);
    expect(isAbsoluteEntry('d:/a', 'win32')).toBe(true);
    expect(isAbsoluteEntry('\\\\server\\share', 'win32')).toBe(true);
    for (const relative of ['.', 'bin', '\\a', '/a', 'C:a']) expect(isAbsoluteEntry(relative, 'win32')).toBe(false);
  });

  it('is POSIX-absolute elsewhere', () => {
    expect(isAbsoluteEntry('/usr/bin', 'linux')).toBe(true);
    expect(isAbsoluteEntry('.', 'linux')).toBe(false);
    expect(isAbsoluteEntry('bin', 'darwin')).toBe(false);
  });
});

describe('childEnvironment', () => {
  it('passes the Windows, proxy and credential variables the CLI and its children need', () => {
    const parent = {
      TEMP: 'C:\\t',
      TMP: 'C:\\t',
      PATHEXT: '.EXE',
      COMSPEC: 'C:\\cmd.exe',
      SYSTEMDRIVE: 'C:',
      WINDIR: 'C:\\Windows',
      HOMEDRIVE: 'C:',
      HOMEPATH: '\\Users\\x',
      HTTPS_PROXY: 'http://p',
      no_proxy: 'localhost',
      SSH_AUTH_SOCK: '/s',
      GH_TOKEN: 'a',
      GITHUB_TOKEN: 'b',
      GH_HOST: 'h',
      AWS_SECRET_ACCESS_KEY: 'nope',
    };
    const env = childEnvironment(parent, {}, 'linux');
    for (const [key, value] of Object.entries(parent)) {
      if (key === 'AWS_SECRET_ACCESS_KEY') expect(env[key]).toBeUndefined();
      else expect(env[key]).toBe(value);
    }
  });

  it('looks variables up case-insensitively on Windows and emits each once', () => {
    const env = childEnvironment({ Path: 'C:\\bin', SystemRoot: 'C:\\Windows', Http_Proxy: 'http://p' }, {}, 'win32');
    expect(env['PATH']).toBe('C:\\bin');
    expect(env['SYSTEMROOT']).toBe('C:\\Windows');
    const proxies = Object.keys(env).filter((key) => key.toLowerCase() === 'http_proxy');
    expect(proxies).toHaveLength(1);
    expect(env[proxies[0] as string]).toBe('http://p');
  });

  it('stays case-sensitive off Windows', () => {
    expect(childEnvironment({ Path: '/x' }, {}, 'linux')['PATH']).toBeUndefined();
  });
});
