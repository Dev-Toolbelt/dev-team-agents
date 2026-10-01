/**
 * What each preference may hold — one table, read by the renderer to validate as the user
 * types and by the main process to refuse a value before any argv exists.
 *
 * Two copies had already diverged once: the ranges lived only in the renderer, so the main
 * process accepted `model_max_tokens = true` (which `_coerce` in `prefs.py` stores as a
 * boolean, because it reads `true`/`false`/`null` before it looks at the default's type)
 * and any out-of-range number. A renderer is not trusted to have validated anything; this
 * table is what the process boundary checks against.
 *
 * Pure, no imports: safe for the main process, the preload and the renderer alike.
 */

import type { PreferenceValue } from './api.js';

export type PreferenceRule =
  | { readonly kind: 'boolean' }
  /** `true`, `false`, or `null` for "not detected yet". */
  | { readonly kind: 'nullable-boolean' }
  | { readonly kind: 'integer'; readonly min: number; readonly max: number }
  | { readonly kind: 'choice'; readonly values: readonly string[] }
  | {
      readonly kind: 'text';
      /** `null` is a stored value meaning "ask" or "auto-detect". */
      readonly nullable: boolean;
      readonly validate: (text: string) => string | null;
    }
  /** Shown, never written — a deprecated key. */
  | { readonly kind: 'readonly' };

/** Opt-in keys (`CONSENT_KEYS` in `prefs.py`): turning one on needs the user's own confirmation. */
export const CONSENT_KEYS: ReadonlySet<string> = new Set(['telemetry', 'auto_update']);

// ── text validators ─────────────────────────────────────────────────────────────

/**
 * What no stored text may look like, whatever the key: a value `_coerce` would read as a
 * literal instead of text, one `argparse` would read as a flag, or one no field needs.
 */
export function textProblem(text: string): string | null {
  if (text.trim() === '' || text.trim() !== text) return 'This cannot be empty or start or end with spaces.';
  if (text.startsWith('-')) return 'This cannot begin with "-".';
  if ([...text].some((char) => char.charCodeAt(0) < 0x20)) return 'This cannot contain control characters.';
  if (['null', 'none', 'true', 'false'].includes(text.toLowerCase())) return `"${text}" is a reserved word here.`;
  if (text.length > 200) return 'Keep this under 200 characters.';
  return null;
}

/** BCP 47, loosely: a language subtag and optional region/script subtags (`pt-BR`, `zh-Hant-TW`). */
export function validateLanguageTag(text: string): string | null {
  return /^[a-z]{2,3}(-[A-Za-z0-9]{2,8})*$/.test(text) ? null : 'Use a BCP 47 tag such as en, pt-BR or es-419.';
}

/**
 * A branch name `git check-ref-format --branch` would accept, minus the rare cases
 * (`@{`-sequences inside a name) that no base branch ever uses.
 */
export function validateBranchName(text: string): string | null {
  if (text.startsWith('-')) return 'A branch name cannot begin with "-".';
  if (/\s/.test(text)) return 'A branch name cannot contain spaces.';
  if (/[~^:?*[\\]/.test(text)) return 'A branch name cannot contain ~ ^ : ? * [ or \\.';
  if (text.includes('..') || text.includes('//') || text.includes('@{')) return 'A branch name cannot contain "..", "//" or "@{".';
  if (text.startsWith('/') || text.endsWith('/') || text.endsWith('.') || text.endsWith('.lock')) {
    return 'A branch name cannot start or end with "/", or end with "." or ".lock".';
  }
  return null;
}

/** A path inside the project: relative, no `..` segment, no home or drive prefix. */
export function validateRelativePath(text: string): string | null {
  if (text.startsWith('/') || text.startsWith('~') || /^[A-Za-z]:[\\/]/.test(text) || text.startsWith('\\')) {
    return 'Use a path relative to the project root, e.g. .worktrees.';
  }
  if (text.split(/[\\/]/).some((segment) => segment === '..')) return 'The path must stay inside the project (no "..").';
  if (text.startsWith('-')) return 'A path cannot begin with "-".';
  return null;
}

export function validateBrowserName(text: string): string | null {
  return /^[A-Za-z0-9][A-Za-z0-9 ._+-]{0,40}$/.test(text) ? null : 'Use the browser’s name, e.g. brave.';
}

// ── the table ───────────────────────────────────────────────────────────────────

export const PREFERENCE_RULES: Readonly<Record<string, PreferenceRule>> = Object.freeze({
  language: { kind: 'text', nullable: false, validate: validateLanguageTag },
  auto_update: { kind: 'boolean' },
  update_check_interval_hours: { kind: 'integer', min: 1, max: 720 },
  telemetry: { kind: 'boolean' },
  model_max_tokens: { kind: 'integer', min: 1000, max: 10_000_000 },
  context_window_percent_warning: { kind: 'integer', min: 1, max: 100 },
  context_window_percent_limit: { kind: 'integer', min: 1, max: 100 },
  session_no_commit_turns: { kind: 'integer', min: 1, max: 200 },
  session_summary_max_days: { kind: 'integer', min: 1, max: 3650 },
  session_summary_max_entries: { kind: 'integer', min: 1, max: 1000 },
  docs_stale_after_days: { kind: 'integer', min: 1, max: 3650 },
  auto_learn_before_commit: { kind: 'boolean' },
  worktree_active: { kind: 'boolean' },
  worktree_base_branch: { kind: 'text', nullable: true, validate: validateBranchName },
  worktree_path: { kind: 'text', nullable: false, validate: validateRelativePath },
  worktree_commit_action: { kind: 'choice', values: ['ask', 'finalize', 'rebase', 'commit-only'] },
  worktree_docker_isolate: { kind: 'boolean' },
  suppress_notifications: { kind: 'boolean' },
  qa_browser: { kind: 'text', nullable: true, validate: validateBrowserName },
  ci_cd_detected: { kind: 'nullable-boolean' },
});

/** The range of an integer key, for the renderer's controls. Throws on a non-integer key: a table error. */
export function integerRange(key: string): { readonly min: number; readonly max: number } {
  const rule = PREFERENCE_RULES[key];
  if (rule === undefined || rule.kind !== 'integer') throw new Error(`${key} is not an integer preference`);
  return { min: rule.min, max: rule.max };
}

/** Why `value` may not be written to `key`, or `null`. The message is shown to the user as-is. */
export function valueProblem(key: string, value: PreferenceValue): string | null {
  const rule = PREFERENCE_RULES[key];
  if (rule === undefined) return `\`${key}\` is not a preference this app edits.`;
  switch (rule.kind) {
    case 'readonly':
      return `\`${key}\` is read-only here.`;
    case 'boolean':
      return typeof value === 'boolean' ? null : `\`${key}\` must be on or off.`;
    case 'nullable-boolean':
      return value === null || typeof value === 'boolean' ? null : `\`${key}\` must be yes, no or auto-detect.`;
    case 'integer':
      if (typeof value !== 'number' || !Number.isInteger(value)) return `\`${key}\` must be a whole number.`;
      return value >= rule.min && value <= rule.max ? null : `\`${key}\` must be between ${rule.min} and ${rule.max}.`;
    case 'choice':
      return typeof value === 'string' && rule.values.includes(value)
        ? null
        : `\`${key}\` must be one of: ${rule.values.join(', ')}.`;
    case 'text': {
      if (value === null) return rule.nullable ? null : `\`${key}\` cannot be empty.`;
      if (typeof value !== 'string') return `\`${key}\` must be text.`;
      return textProblem(value) ?? rule.validate(value);
    }
  }
}
