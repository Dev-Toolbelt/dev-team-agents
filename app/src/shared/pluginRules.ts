/**
 * What a plugin config value may be, per field type — shared by the renderer (to say why a
 * draft cannot be saved) and the main process (to refuse the same draft again, because the
 * renderer is not trusted to have checked).
 *
 * Nothing here names a plugin. The rules read a `PluginConfigField` the CLI described, so a
 * plugin added to the core needs no change in this file (ADR-0019 § 5).
 */

import type { PluginConfigField, PluginConfigValue } from './api.js';

/** ADR-0019 § 1: `^[a-z][a-z0-9-]{1,31}$`. */
export const PLUGIN_NAME = /^[a-z][a-z0-9-]{1,31}$/;
/** An action id; looser than a plugin name because the manifest schema does not pin it further. */
export const PLUGIN_ACTION_ID = /^[a-z][a-z0-9_-]{0,63}$/;
/** A config key. `targetPaths` is camelCase, so this is not the preference-key rule. */
export const PLUGIN_CONFIG_KEY = /^[A-Za-z][A-Za-z0-9_]{0,63}$/;

export const MAX_LIST_ITEMS = 200;
export const MAX_TEXT_LENGTH = 500;

/** The field types this app can render and write. */
export const EDITABLE_TYPES: readonly string[] = ['boolean', 'string', 'integer', 'string_list', 'enum'];

export function isEditable(field: PluginConfigField): boolean {
  return EDITABLE_TYPES.includes(field.type);
}

function hasControlCharacter(text: string): boolean {
  return [...text].some((char) => char.charCodeAt(0) < 0x20);
}

/** Why one list entry cannot be used, or `null`. Shared with the list editor's Add button. */
export function listItemProblem(item: string): string | null {
  if (item.trim() === '') return 'Enter a value first.';
  if (item.trim() !== item) return 'Remove the spaces around the value.';
  if (hasControlCharacter(item)) return 'This cannot contain control characters.';
  if (item.length > MAX_TEXT_LENGTH) return `Keep each entry under ${MAX_TEXT_LENGTH} characters.`;
  return null;
}

/**
 * Why `value` cannot be stored in `field`, or `null` when it can.
 *
 * `string` is refused when empty or when it begins with `-`: the empty string is what
 * "no value" means (use `unset`), and a leading dash would be read by `argparse` as a flag.
 * A negative integer starts with a dash for the same reason, so it is refused with its own
 * message — the CLI's argv cannot carry it.
 */
export function pluginValueProblem(field: PluginConfigField, value: unknown): string | null {
  switch (field.type) {
    case 'boolean':
      return typeof value === 'boolean' ? null : 'This must be on or off.';
    case 'integer': {
      if (typeof value !== 'number' || !Number.isSafeInteger(value)) return 'Enter a whole number.';
      if (value < 0) return 'Negative numbers cannot be passed to the CLI.';
      if (field.min !== null && value < field.min) return `Must be at least ${field.min}.`;
      if (field.max !== null && value > field.max) return `Must be at most ${field.max}.`;
      return null;
    }
    case 'string': {
      if (typeof value !== 'string') return 'This must be text.';
      if (value.trim() === '') return 'This cannot be empty; remove the setting instead.';
      if (value.trim() !== value) return 'Remove the spaces around the value.';
      if (value.startsWith('-')) return 'This cannot begin with "-".';
      if (hasControlCharacter(value)) return 'This cannot contain control characters.';
      if (value.length > MAX_TEXT_LENGTH) return `Keep this under ${MAX_TEXT_LENGTH} characters.`;
      return null;
    }
    case 'enum': {
      if (typeof value !== 'string') return 'Pick one of the listed options.';
      return field.options.some((option) => option.value === value) ? null : 'Pick one of the listed options.';
    }
    case 'string_list': {
      if (!Array.isArray(value)) return 'This must be a list.';
      if (value.length > MAX_LIST_ITEMS) return `Keep the list under ${MAX_LIST_ITEMS} entries.`;
      const seen = new Set<string>();
      for (const item of value as unknown[]) {
        if (typeof item !== 'string') return 'Every entry must be text.';
        const problem = listItemProblem(item);
        if (problem !== null) return problem;
        if (seen.has(item)) return `"${item}" is listed twice.`;
        seen.add(item);
      }
      return null;
    }
    default:
      return `This app cannot edit a setting of type "${field.type}".`;
  }
}

/**
 * The string `plugin config set` parses back into `value` (ADR-0019 § 3): a JSON array for
 * `string_list`, `true`/`false` for a boolean, base 10 for an integer, the text itself
 * otherwise. Call `pluginValueProblem` first; this does not re-validate.
 */
export function serializePluginValue(field: PluginConfigField, value: PluginConfigValue): string {
  if (field.type === 'string_list') return JSON.stringify(value);
  if (typeof value === 'boolean') return value ? 'true' : 'false';
  return String(value);
}

/** Structural equality for the value shapes a config can hold. */
export function samePluginValue(a: unknown, b: unknown): boolean {
  if (Array.isArray(a) && Array.isArray(b)) {
    return a.length === b.length && a.every((item, index) => item === b[index]);
  }
  return a === b;
}

/** True for `''`, `[]` and `null`/`undefined` — what "required but not filled in" means. */
export function isBlank(value: unknown): boolean {
  if (value === null || value === undefined) return true;
  if (typeof value === 'string') return value.trim() === '';
  if (Array.isArray(value)) return value.length === 0;
  return false;
}
