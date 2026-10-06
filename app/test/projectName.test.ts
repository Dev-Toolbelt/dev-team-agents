/** `projectNameProblem` is the one rule the renderer's Save button and the main process share. */
import { describe, expect, it } from 'vitest';

import { PROJECT_NAME_MAX_LENGTH, projectNameProblem } from '../src/shared/api.js';

describe('projectNameProblem', () => {
  it.each(['Storefront', 'proj 2', '  padded  ', 'ação — ünï', 'a'])('accepts %j', (name) => {
    expect(projectNameProblem(name)).toBeNull();
  });

  it('accepts exactly the maximum length, and measures after trimming', () => {
    expect(projectNameProblem('x'.repeat(PROJECT_NAME_MAX_LENGTH))).toBeNull();
    expect(projectNameProblem(`  ${'x'.repeat(PROJECT_NAME_MAX_LENGTH)}  `)).toBeNull();
  });

  it.each(['', ' ', ' \t ', '\n'])('refuses empty or whitespace-only %j', (name) => {
    expect(projectNameProblem(name)).toMatch(/needs a name/);
  });

  it('refuses a name one character over the maximum', () => {
    expect(projectNameProblem('x'.repeat(PROJECT_NAME_MAX_LENGTH + 1))).toMatch(/at most 120/);
  });

  it.each(['a\u0000b', 'a\tb', 'a\nb', 'a\u001bb', 'a\u007fb', 'a\u0085b'])('refuses control characters in %j', (name) => {
    expect(projectNameProblem(name)).toMatch(/control characters/);
  });

  it('does not take non-strings as input at the type level, and the IPC layer rejects them first', () => {
    // @ts-expect-error — documents that callers must narrow before asking
    expect(() => projectNameProblem(42)).toThrow();
  });
});
