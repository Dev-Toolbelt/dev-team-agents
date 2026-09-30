/**
 * The settings screen's presentation table and its validators — pure, no React, no CLI.
 *
 * The table must describe exactly the keys the framework ships: a key the defaults gain
 * would otherwise land in "Other" as read-only without anyone noticing, and a key described
 * here that the defaults dropped would be dead code. Both directions are checked against
 * `scripts/lib/preferences-defaults.json`, the canonical schema, read from the repo.
 */
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

import { describe, expect, it } from 'vitest';

import {
  FIELDS,
  GROUPS,
  crossFieldErrors,
  parseDraft,
  validateBranchName,
  validateLanguageTag,
  validateRelativePath,
  type Field,
} from '../src/renderer/preferences/schema.js';
import { PREFERENCE_RULES, textProblem, valueProblem } from '../src/shared/preferenceRules.js';

const DEFAULTS = JSON.parse(
  readFileSync(fileURLToPath(new URL('../../scripts/lib/preferences-defaults.json', import.meta.url)), 'utf8'),
) as Record<string, unknown>;

function field(key: string): Field {
  const found = FIELDS.find((candidate) => candidate.key === key);
  if (found === undefined) throw new Error(`no field ${key}`);
  return found;
}

describe('the presentation table matches the shipped defaults', () => {
  it('describes every default key exactly once, and nothing else', () => {
    const described = FIELDS.map((candidate) => candidate.key);
    expect(new Set(described).size).toBe(described.length);
    expect([...described].sort()).toEqual(Object.keys(DEFAULTS).sort());
  });

  it('has a main-process rule for every default key, and nothing else', () => {
    expect(Object.keys(PREFERENCE_RULES).sort()).toEqual(Object.keys(DEFAULTS).sort());
  });

  it('accepts every shipped default except the read-only one', () => {
    for (const [key, value] of Object.entries(DEFAULTS)) {
      if (PREFERENCE_RULES[key]?.kind === 'readonly') continue;
      expect(valueProblem(key, value as never), key).toBeNull();
    }
  });

  it('puts every field in a declared group, and leaves no group empty', () => {
    const groupIds = new Set(GROUPS.map((group) => group.id));
    for (const candidate of FIELDS) expect(groupIds.has(candidate.group), candidate.key).toBe(true);
    for (const group of GROUPS) expect(FIELDS.some((candidate) => candidate.group === group.id), group.id).toBe(true);
  });

  it('marks exactly the CLI consent keys as consent', () => {
    expect(FIELDS.filter((candidate) => candidate.consent === true).map((candidate) => candidate.key).sort()).toEqual([
      'auto_update',
      'telemetry',
    ]);
  });

  it('has every integer default inside its own range, so the default is never shown as invalid', () => {
    for (const candidate of FIELDS) {
      if (candidate.control.type !== 'integer') continue;
      const value = DEFAULTS[candidate.key] as number;
      expect(value, candidate.key).toBeGreaterThanOrEqual(candidate.control.min);
      expect(value, candidate.key).toBeLessThanOrEqual(candidate.control.max);
    }
  });
});

describe('parsing a draft', () => {
  it('reads grouped digits and enforces the range', () => {
    const tokens = field('model_max_tokens');
    expect(parseDraft(tokens, { kind: 'text', text: '200,000' })).toEqual({ ok: true, value: 200000 });
    expect(parseDraft(tokens, { kind: 'text', text: '999' })).toMatchObject({ ok: false });
    expect(parseDraft(tokens, { kind: 'text', text: '' })).toMatchObject({ ok: false, error: 'Enter a number.' });
    expect(parseDraft(field('session_no_commit_turns'), { kind: 'text', text: '1.5' })).toMatchObject({ ok: false });
  });

  it('turns an empty nullable text into null, and refuses an empty required one', () => {
    expect(parseDraft(field('worktree_base_branch'), { kind: 'text', text: '  ' })).toEqual({ ok: true, value: null });
    expect(parseDraft(field('worktree_path'), { kind: 'text', text: '' })).toMatchObject({ ok: false });
  });

  it('validates a select’s free-text “Other” value', () => {
    expect(parseDraft(field('language'), { kind: 'text', text: 'fr-CA' })).toEqual({ ok: true, value: 'fr-CA' });
    expect(parseDraft(field('language'), { kind: 'text', text: 'French' })).toMatchObject({ ok: false });
  });

  it('passes a chosen value through untouched', () => {
    expect(parseDraft(field('ci_cd_detected'), { kind: 'value', value: false })).toEqual({ ok: true, value: false });
  });
});

describe('validators', () => {
  it('accepts BCP 47 tags and refuses words', () => {
    for (const tag of ['en', 'pt-BR', 'es-419', 'zh-Hant-TW']) expect(validateLanguageTag(tag), tag).toBeNull();
    for (const tag of ['English', 'pt_BR', 'e']) expect(validateLanguageTag(tag), tag).not.toBeNull();
  });

  it('accepts real branch names and refuses what git refuses', () => {
    for (const name of ['main', 'release/2.x', 'feature/a-b_c']) expect(validateBranchName(name), name).toBeNull();
    for (const name of ['-x', 'a b', 'a..b', 'a~1', 'x.lock', 'x/', '/x']) expect(validateBranchName(name), name).not.toBeNull();
  });

  it('keeps the worktree directory inside the project', () => {
    for (const path of ['.worktrees', '.dev-team-agents/worktrees']) expect(validateRelativePath(path), path).toBeNull();
    for (const path of ['/tmp/wt', '~/wt', '../wt', 'a/../../b', 'C:\\wt']) expect(validateRelativePath(path), path).not.toBeNull();
  });

  it('requires the context warning to come before the critical level', () => {
    expect(crossFieldErrors({ context_window_percent_warning: 55, context_window_percent_limit: 60 })).toEqual({});
    const errors = crossFieldErrors({ context_window_percent_warning: 60, context_window_percent_limit: 60 });
    expect(Object.keys(errors).sort()).toEqual(['context_window_percent_limit', 'context_window_percent_warning']);
    // An unparsable partner is its own error; the pair rule does not pile a second one on.
    expect(crossFieldErrors({ context_window_percent_warning: 70, context_window_percent_limit: undefined })).toEqual({});
  });
});

describe('the rules the main process enforces', () => {
  it('refuses a value of the wrong type for its key', () => {
    expect(valueProblem('model_max_tokens', true)).not.toBeNull();
    expect(valueProblem('model_max_tokens', null)).not.toBeNull();
    expect(valueProblem('worktree_active', 'true')).not.toBeNull();
    expect(valueProblem('ci_cd_detected', null)).toBeNull();
    expect(valueProblem('qa_browser', null)).toBeNull();
    expect(valueProblem('worktree_path', null)).not.toBeNull();
    expect(valueProblem('not_a_key', 1)).not.toBeNull();
  });

  it('refuses text the CLI would read as a literal or as a flag', () => {
    for (const text of ['null', 'None', 'TRUE', '-x', ' padded', 'a'.repeat(201)]) expect(textProblem(text), text).not.toBeNull();
    expect(textProblem('chrome')).toBeNull();
  });
});
