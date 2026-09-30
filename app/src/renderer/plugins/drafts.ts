/**
 * The staged edits of one plugin's config form, as pure functions so the rules a person
 * cannot see (what counts as a change, what blocks a save) can be tested without a DOM.
 *
 * A draft holds what the control holds: a boolean, a string, an enum value, a list of
 * strings — and, for an integer, the **text being typed**, because "12x" has to be a value
 * the field can show and flag rather than one it silently rejects.
 */

import type { PluginConfigChange, PluginConfigField, PluginConfigValue } from '../../shared/api.js';
import { isBlank, isEditable, pluginValueProblem, samePluginValue } from '../../shared/pluginRules.js';

export type Drafts = Readonly<Record<string, unknown>>;

export interface FieldDraftState {
  /** What the control shows: the draft when there is one, otherwise the saved value. */
  readonly display: unknown;
  /** The value a save would send; `undefined` when the draft is not a valid value. */
  readonly value: PluginConfigValue | undefined;
  readonly error: string | null;
  readonly changed: boolean;
}

/** The saved value of a field, falling back to the manifest default. */
export function savedValue(field: PluginConfigField, config: Readonly<Record<string, unknown>>): unknown {
  return field.key in config ? config[field.key] : field.default;
}

export function fieldDraftState(
  field: PluginConfigField,
  config: Readonly<Record<string, unknown>>,
  drafts: Drafts,
): FieldDraftState {
  const saved = savedValue(field, config);
  if (!(field.key in drafts)) return { display: saved, value: undefined, error: null, changed: false };

  const draft = drafts[field.key];
  let candidate: unknown = draft;
  if (field.type === 'integer') {
    const text = typeof draft === 'string' ? draft.trim() : '';
    if (text === '') {
      return {
        display: draft,
        value: undefined,
        error: field.required ? 'This is required.' : 'Enter a whole number.',
        changed: true,
      };
    }
    if (!/^-?\d+$/.test(text)) return { display: draft, value: undefined, error: 'Enter a whole number.', changed: true };
    candidate = Number(text);
  }

  // A string field left empty means "no value": it is sent as `unset`, not as a blank.
  if (field.type === 'string' && typeof candidate === 'string' && candidate === '') {
    const error = field.required ? 'This is required.' : null;
    return { display: draft, value: undefined, error, changed: !isBlank(saved) };
  }

  const problem = pluginValueProblem(field, candidate);
  if (problem !== null) return { display: draft, value: undefined, error: problem, changed: true };
  if (field.required && isBlank(candidate)) {
    return { display: draft, value: undefined, error: 'This is required.', changed: true };
  }
  return {
    display: draft,
    value: candidate as PluginConfigValue,
    error: null,
    changed: !samePluginValue(candidate, saved),
  };
}

export interface DraftBatch {
  readonly changes: readonly PluginConfigChange[];
  /** Fields whose draft cannot be saved; they block the whole save. */
  readonly invalid: readonly string[];
  /** Drafts that are equal to the saved value are not changes and do not count. */
  readonly dirtyKeys: readonly string[];
}

export function draftBatch(
  fields: readonly PluginConfigField[],
  config: Readonly<Record<string, unknown>>,
  drafts: Drafts,
): DraftBatch {
  const changes: PluginConfigChange[] = [];
  const invalid: string[] = [];
  const dirtyKeys: string[] = [];
  for (const field of fields) {
    if (!isEditable(field) || !(field.key in drafts)) continue;
    const state = fieldDraftState(field, config, drafts);
    if (!state.changed) continue;
    dirtyKeys.push(field.key);
    if (state.error !== null) {
      invalid.push(field.key);
    } else if (state.value === undefined) {
      changes.push({ key: field.key, action: 'unset' });
    } else {
      changes.push({ key: field.key, action: 'set', value: state.value });
    }
  }
  return { changes, invalid, dirtyKeys };
}

export interface Proposal {
  readonly drafts: Drafts;
  /** Keys the proposal changes relative to the saved config. */
  readonly filled: readonly string[];
  /** Keys in the answer that this form has no editable field for, or whose value did not fit. */
  readonly skipped: readonly string[];
}

/**
 * Turn an `output: "config"` action's answer into drafts. Nothing is written: the values
 * land in the form for a person to review and save. A key the plugin does not declare, or a
 * value that would not pass the field's own rules, is skipped and reported instead of being
 * put in a draft that could never be saved.
 */
export function proposalToDrafts(
  fields: readonly PluginConfigField[],
  config: Readonly<Record<string, unknown>>,
  output: Readonly<Record<string, unknown>>,
): Proposal {
  const drafts: Record<string, unknown> = {};
  const filled: string[] = [];
  const skipped: string[] = [];
  const byKey = new Map(fields.map((field) => [field.key, field]));
  for (const [key, value] of Object.entries(output)) {
    const field = byKey.get(key);
    if (field === undefined || !isEditable(field) || pluginValueProblem(field, value) !== null) {
      skipped.push(key);
      continue;
    }
    if (samePluginValue(value, savedValue(field, config))) continue;
    drafts[key] = field.type === 'integer' ? String(value) : Array.isArray(value) ? [...(value as string[])] : value;
    filled.push(key);
  }
  return { drafts, filled, skipped };
}
