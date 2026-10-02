import { describe, expect, it } from 'vitest';

import { hostPlatformFrom, isSameDirectory, isSameOrInside, normalizeDirectory } from '../src/shared/directoryPaths.js';

describe('hostPlatformFrom', () => {
  it('maps navigator.platform', () => {
    expect(hostPlatformFrom('Win32')).toBe('win32');
    expect(hostPlatformFrom('MacIntel')).toBe('darwin');
    expect(hostPlatformFrom('Linux x86_64')).toBe('other');
    expect(hostPlatformFrom(undefined)).toBe('other');
  });
});

describe('normalizeDirectory', () => {
  it('strips trailing separators but keeps roots', () => {
    expect(normalizeDirectory('/a/b//', 'other')).toBe('/a/b');
    expect(normalizeDirectory('/', 'other')).toBe('/');
    expect(normalizeDirectory('C:\\', 'win32')).toBe('c:/');
    expect(normalizeDirectory('C:\\Repo\\', 'win32')).toBe('c:/repo');
  });

  it('keeps case on case-sensitive hosts and a backslash as a filename character', () => {
    expect(normalizeDirectory('/Repo\\x', 'other')).toBe('/Repo\\x');
  });
});

describe('isSameOrInside', () => {
  it('is case-insensitive on darwin and win32 only', () => {
    expect(isSameOrInside('/Users/X/Repo', '/users/x/repo', 'darwin')).toBe(true);
    expect(isSameOrInside('c:\\users\\x\\repo\\app', 'C:\\Users\\X\\Repo', 'win32')).toBe(true);
    expect(isSameOrInside('/Users/X/Repo', '/users/x/repo', 'other')).toBe(false);
  });

  it('treats both separators as one on win32', () => {
    expect(isSameOrInside('C:/repo/app', 'C:\\repo', 'win32')).toBe(true);
  });

  it('compares whole components', () => {
    expect(isSameOrInside('/repo/app-2', '/repo/app', 'other')).toBe(false);
    expect(isSameOrInside('/repo/app/x', '/repo/app/', 'other')).toBe(true);
  });

  it('a drive root contains its folders', () => {
    expect(isSameOrInside('C:\\repo', 'C:\\', 'win32')).toBe(true);
    expect(isSameOrInside('D:\\repo', 'C:\\', 'win32')).toBe(false);
    expect(isSameOrInside('/repo', '/', 'other')).toBe(true);
  });
});

describe('isSameDirectory', () => {
  it('ignores a trailing separator and case where the host does', () => {
    expect(isSameDirectory('C:\\Repo\\', 'c:/repo', 'win32')).toBe(true);
    expect(isSameDirectory('/a/b', '/a/b/c', 'other')).toBe(false);
  });
});
