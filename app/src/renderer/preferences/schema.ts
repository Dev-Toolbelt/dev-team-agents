/**
 * How the settings screen presents each preference: group, control, validation, unit.
 *
 * **Presentation only.** The canonical schema — which keys exist and their defaults — is
 * `scripts/lib/preferences-defaults.json`, read by the CLI and returned by `prefs list`. A
 * key `prefs list` returns that is not described here is still shown, as a read-only row
 * under "Other", so a key added to the framework before this table learns about it is
 * visible rather than silently dropped. A key described here that `prefs list` does not
 * return is not rendered at all.
 *
 * No React in this file: the validators are exercised directly by `test/preferences.test.ts`.
 */

import type { PreferenceValue } from '../../shared/api.js';
import {
  integerRange,
  textProblem,
  validateBranchName,
  validateBrowserName,
  validateLanguageTag,
  validateRelativePath,
} from '../../shared/preferenceRules.js';

// The validators live beside the rules the main process enforces; re-exported so the
// screen and its tests have one import path for presentation concerns.
export { validateBranchName, validateBrowserName, validateLanguageTag, validateRelativePath };

export type GroupId = 'general' | 'context' | 'memory' | 'worktrees' | 'notifications' | 'qa';

export interface Group {
  readonly id: GroupId;
  readonly title: string;
  readonly description: string;
}

export const GROUPS: readonly Group[] = [
  { id: 'general', title: 'General', description: 'Language, updates and what this project shares.' },
  {
    id: 'context',
    title: 'Context & session',
    description: 'When agents warn about the context window, and how long a dirty tree may go uncommitted.',
  },
  { id: 'memory', title: 'Memory & docs', description: 'How long session memory is kept and when docs count as stale.' },
  { id: 'worktrees', title: 'Worktrees', description: 'Whether each task gets its own git worktree, and how it is finished.' },
  { id: 'notifications', title: 'Notifications', description: 'What the harness tells you while agents work.' },
  { id: 'qa', title: 'QA & CI', description: 'Browser testing and the cached CI detection.' },
];

export interface ChoiceOption {
  /** `null` is a real value here: it is what "ask" or "auto-detect" is stored as. */
  readonly value: string | null;
  readonly label: string;
  readonly description?: string;
}

export type Control =
  | { readonly type: 'switch' }
  | {
      readonly type: 'integer';
      readonly min: number;
      readonly max: number;
      readonly unit: string;
      /** Group digits as you type (`200,000`). Only for values large enough to misread. */
      readonly grouped?: boolean;
      readonly presets?: readonly { readonly label: string; readonly value: number }[];
    }
  /** A fixed list rendered as a `<select>`, optionally with a free-text "Other…". */
  | {
      readonly type: 'select';
      readonly options: readonly ChoiceOption[];
      readonly other?: { readonly label: string; readonly placeholder: string; readonly validate: (text: string) => string | null };
    }
  /** A short fixed list rendered as radio cards, each with its consequence. */
  | { readonly type: 'cards'; readonly options: readonly ChoiceOption[] }
  /** Free text where empty means `null` — the "Auto-detect" state. */
  | {
      readonly type: 'text';
      readonly placeholder: string;
      readonly nullable: boolean;
      readonly validate: (text: string) => string | null;
    }
  | { readonly type: 'readonly'; readonly reason: string };

export interface Field {
  readonly key: string;
  readonly group: GroupId;
  readonly label: string;
  readonly help: string;
  readonly control: Control;
  /** A consent key (`CONSENT_KEYS` in `prefs.py`): off until someone explicitly opts in. */
  readonly consent?: boolean;
  /** Dimmed with this note while the named switch is off. Still editable. */
  readonly dependsOn?: { readonly key: string; readonly note: string };
}

// ── the table ───────────────────────────────────────────────────────────────────

export const FIELDS: readonly Field[] = [
  // General
  {
    key: 'language',
    group: 'general',
    label: 'Conversation language',
    help: 'The language agents use when talking to you. Documentation stays in English.',
    control: {
      type: 'select',
      options: [
        { value: 'en', label: 'English' },
        { value: 'pt-BR', label: 'Português (Brasil)' },
        { value: 'es', label: 'Español' },
      ],
      other: { label: 'Other…', placeholder: 'BCP 47 tag, e.g. fr-CA', validate: validateLanguageTag },
    },
  },
  {
    key: 'auto_update',
    group: 'general',
    label: 'Update automatically',
    help: 'Apply a new dev-team-agents version as soon as one is detected.',
    consent: true,
    control: { type: 'switch' },
  },
  {
    key: 'update_check_interval_hours',
    group: 'general',
    label: 'Check for updates every',
    help: 'How often the session start looks for a new version.',
    control: { type: 'integer', ...integerRange('update_check_interval_hours'), unit: 'hours', presets: [{ label: 'Daily', value: 24 }, { label: 'Weekly', value: 168 }] },
  },
  {
    key: 'telemetry',
    group: 'general',
    label: 'Anonymous usage telemetry',
    help: 'Send anonymous, aggregate usage events. PRIVACY.md lists exactly what is sent.',
    consent: true,
    control: { type: 'switch' },
  },

  // Context & session
  {
    key: 'model_max_tokens',
    group: 'context',
    label: 'Model context window',
    help: 'The context size of the model you run, used to turn token counts into a percentage.',
    control: {
      type: 'integer',
      ...integerRange('model_max_tokens'),
      unit: 'tokens',
      grouped: true,
      presets: [
        { label: '200K', value: 200_000 },
        { label: '1M', value: 1_000_000 },
      ],
    },
  },
  {
    key: 'context_window_percent_warning',
    group: 'context',
    label: 'Warn at',
    help: 'Context usage at which agents emit a warning notification.',
    control: { type: 'integer', ...integerRange('context_window_percent_warning'), unit: '%' },
  },
  {
    key: 'context_window_percent_limit',
    group: 'context',
    label: 'Critical at',
    help: 'Context usage at which agents emit a critical notification and suggest compacting.',
    control: { type: 'integer', ...integerRange('context_window_percent_limit'), unit: '%' },
  },
  {
    key: 'session_no_commit_turns',
    group: 'context',
    label: 'Remind to commit after',
    help: 'Turns of work on a dirty tree with no commit before a one-time reminder.',
    control: { type: 'integer', ...integerRange('session_no_commit_turns'), unit: 'turns' },
  },

  // Memory & docs
  {
    key: 'session_summary_max_days',
    group: 'memory',
    label: 'Keep session summaries for',
    help: 'Entries older than this are trimmed from the session summary.',
    control: { type: 'integer', ...integerRange('session_summary_max_days'), unit: 'days' },
  },
  {
    key: 'session_summary_max_entries',
    group: 'memory',
    label: 'Maximum session summary entries',
    help: 'The session summary is trimmed to this many entries, newest first.',
    control: { type: 'integer', ...integerRange('session_summary_max_entries'), unit: 'entries' },
  },
  {
    key: 'docs_stale_after_days',
    group: 'memory',
    label: 'Docs are stale after',
    help: 'When project.md, the session summary and the last health check count as out of date.',
    control: { type: 'integer', ...integerRange('docs_stale_after_days'), unit: 'days' },
  },
  {
    key: 'auto_learn_before_commit',
    group: 'memory',
    label: 'Learn before every commit',
    help: 'Run /devteam:learn before committing, so decisions reach the docs and wiki.',
    control: { type: 'switch' },
  },

  // Worktrees
  {
    key: 'worktree_active',
    group: 'worktrees',
    label: 'Use a worktree per task',
    help: 'Start each task in its own git worktree without asking. Off: agents ask only for a branch name.',
    control: { type: 'switch' },
  },
  {
    key: 'worktree_base_branch',
    group: 'worktrees',
    label: 'Base branch',
    help: 'The branch worktrees start from and merge back into.',
    dependsOn: { key: 'worktree_active', note: 'Applies when worktrees are on.' },
    control: { type: 'text', placeholder: 'Auto-detect the default branch', nullable: true, validate: validateBranchName },
  },
  {
    key: 'worktree_path',
    group: 'worktrees',
    label: 'Worktree directory',
    help: 'Where worktrees are created, relative to the project root.',
    dependsOn: { key: 'worktree_active', note: 'Applies when worktrees are on.' },
    control: { type: 'text', placeholder: '.worktrees', nullable: false, validate: validateRelativePath },
  },
  {
    key: 'worktree_commit_action',
    group: 'worktrees',
    label: 'After a commit in a worktree',
    help: 'What /devteam:commit does once the commit is made.',
    dependsOn: { key: 'worktree_active', note: 'Applies when worktrees are on.' },
    control: {
      type: 'cards',
      options: [
        { value: 'ask', label: 'Ask each time', description: 'Show the chooser after every commit.' },
        { value: 'finalize', label: 'Finalize', description: 'Rebase, merge into the base branch and remove the worktree.' },
        { value: 'rebase', label: 'Rebase only', description: 'Rebase onto the base branch and keep working.' },
        { value: 'commit-only', label: 'Commit only', description: 'Leave the worktree exactly as it is.' },
      ],
    },
  },
  {
    key: 'worktree_docker_isolate',
    group: 'worktrees',
    label: 'Isolated Docker stack per worktree',
    help: 'Give each worktree its own Docker Compose project, ports and volumes, when Docker is present.',
    dependsOn: { key: 'worktree_active', note: 'Applies when worktrees are on.' },
    control: { type: 'switch' },
  },

  // Notifications
  {
    key: 'suppress_notifications',
    group: 'notifications',
    label: 'Mute notifications',
    help: 'Silence every harness notification — context warnings, stale docs, commit reminders.',
    control: { type: 'switch' },
  },

  // QA & CI
  {
    key: 'qa_browser',
    group: 'qa',
    label: 'QA browser',
    help: 'The browser qa-specialist drives when the in-app browser is unavailable.',
    control: {
      type: 'select',
      options: [
        { value: null, label: 'Ask on first use' },
        { value: 'chrome', label: 'Google Chrome' },
        { value: 'chromium', label: 'Chromium' },
        { value: 'firefox', label: 'Firefox' },
        { value: 'safari', label: 'Safari' },
        { value: 'edge', label: 'Microsoft Edge' },
      ],
      other: { label: 'Other…', placeholder: 'Browser name, e.g. brave', validate: validateBrowserName },
    },
  },
  {
    key: 'ci_cd_detected',
    group: 'qa',
    label: 'GitHub Actions',
    help: 'A cached detection that decides whether pushing offers to watch CI. Auto-detect re-checks it.',
    control: {
      type: 'select',
      options: [
        { value: null, label: 'Auto-detect' },
        { value: 'true', label: 'Present — offer to watch CI' },
        { value: 'false', label: 'Absent — push without asking' },
      ],
    },
  },
];

/** `ci_cd_detected` is the one select whose stored values are booleans, not strings. */
/**
 * Keys the framework still writes into `preferences.json` but no longer reads. Not shown at
 * all: listing them under "other keys" would offer a setting that does nothing. The main
 * process keeps refusing writes to them (`PREFERENCE_RULES` marks them `readonly`).
 */
export const RETIRED_KEYS: ReadonlySet<string> = new Set(['transcript_multiplier']);

export const BOOLEAN_SELECT_KEYS: ReadonlySet<string> = new Set(['ci_cd_detected']);

export const FIELD_BY_KEY: ReadonlyMap<string, Field> = new Map(FIELDS.map((field) => [field.key, field]));

// ── parsing a draft ─────────────────────────────────────────────────────────────

/**
 * What a control holds while the user edits. Numbers and text are kept as the typed
 * string so a half-typed value (`2,00`) is not rewritten under the cursor.
 */
export type DraftInput =
  | { readonly kind: 'value'; readonly value: PreferenceValue }
  | { readonly kind: 'text'; readonly text: string };

export type Parsed = { readonly ok: true; readonly value: PreferenceValue } | { readonly ok: false; readonly error: string };

/** Digits only, with the grouping the field displays. Anything else is left for the validator. */
export function formatInteger(value: number, grouped: boolean): string {
  return grouped ? value.toLocaleString('en-US') : String(value);
}

export function parseDraft(field: Field, input: DraftInput): Parsed {
  const { control } = field;
  if (input.kind === 'value') return { ok: true, value: input.value };
  const text = input.text.trim();

  if (control.type === 'integer') {
    const digits = text.replace(/[,\s_]/g, '');
    if (digits === '') return { ok: false, error: 'Enter a number.' };
    if (!/^\d+$/.test(digits)) return { ok: false, error: 'Whole numbers only.' };
    const value = Number(digits);
    if (value < control.min || value > control.max) {
      return {
        ok: false,
        error: `Between ${formatInteger(control.min, control.grouped === true)} and ${formatInteger(control.max, control.grouped === true)} ${control.unit}.`,
      };
    }
    return { ok: true, value };
  }

  if (control.type === 'text') {
    if (text === '') return control.nullable ? { ok: true, value: null } : { ok: false, error: 'This cannot be empty.' };
    const error = textProblem(text) ?? control.validate(text);
    return error === null ? { ok: true, value: text } : { ok: false, error };
  }

  if (control.type === 'select' && control.other !== undefined) {
    if (text === '') return { ok: false, error: 'Enter a value, or pick one from the list.' };
    const error = textProblem(text) ?? control.other.validate(text);
    return error === null ? { ok: true, value: text } : { ok: false, error };
  }

  return { ok: true, value: text };
}

/**
 * Rules that span two fields. Returned per key so each message sits under the field it
 * is about; both fields of a pair get it, since editing either one fixes it.
 */
export function crossFieldErrors(values: Readonly<Record<string, PreferenceValue | undefined>>): Record<string, string> {
  const errors: Record<string, string> = {};
  const warning = values['context_window_percent_warning'];
  const limit = values['context_window_percent_limit'];
  if (typeof warning === 'number' && typeof limit === 'number' && warning >= limit) {
    errors['context_window_percent_warning'] = 'The warning has to come before the critical level.';
    errors['context_window_percent_limit'] = 'The critical level has to be above the warning.';
  }
  return errors;
}

/** Deep enough for every value `prefs set` can store. */
export function sameValue(left: unknown, right: unknown): boolean {
  if (Array.isArray(left) || Array.isArray(right)) return JSON.stringify(left) === JSON.stringify(right);
  return left === right;
}
