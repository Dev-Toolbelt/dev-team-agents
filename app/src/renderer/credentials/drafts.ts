/**
 * The staged edits of the local credentials form, as pure functions so the rules a person
 * cannot see (what counts as a change, which ops a save sends, in what order) are testable
 * without a DOM.
 *
 * A draft only records what the person touched, keyed by the JSON pointer of the leaf. A save
 * is the diff between those entries and the loaded view: untouched leaves are never sent, so
 * a hand edit elsewhere in the file survives.
 */

import type { CredentialsLocalView, CredentialsPatchOp, CredentialsSecretLeaf } from '../../shared/api.js';

export const WORK_FEEDBACK_ACTIVE = '/work_feedback_active';
export const WORK_FEEDBACK_INTERVAL = '/work_feedback_interval_minutes';

/** Leaf names whose value is never read back; the CLI reports them as `{secret, set}`. */
export const SECRET_KEYS: ReadonlySet<string> = new Set(['password', 'token', 'secret', 'apiKey', 'privateKey']);

export const DATABASE_FIELDS = ['type', 'host', 'port', 'database', 'username', 'password'] as const;
export type DatabaseField = (typeof DATABASE_FIELDS)[number];

export type SecretDraft = { readonly kind: 'replace'; readonly value: string } | { readonly kind: 'remove' };

export interface NewRow {
  readonly id: number;
  readonly values: Readonly<Record<DatabaseField, string>>;
}

export interface Drafts {
  /** Plain leaves by pointer: text, a switch, or a list of strings. */
  readonly values: Readonly<Record<string, string | boolean | readonly string[]>>;
  readonly secrets: Readonly<Record<string, SecretDraft>>;
  /** Original indices of database rows the person removed, by list pointer. */
  readonly removed: Readonly<Record<string, readonly number[]>>;
  /** Database rows the person added, by list pointer. */
  readonly added: Readonly<Record<string, readonly NewRow[]>>;
}

export const EMPTY_DRAFTS: Drafts = { values: {}, secrets: {}, removed: {}, added: {} };

export interface DraftReport {
  readonly ops: readonly CredentialsPatchOp[];
  /** Why a draft cannot be saved, by pointer. */
  readonly problems: Readonly<Record<string, string>>;
  /** Edits pending, including the ones that cannot be saved yet. */
  readonly changes: number;
}

// ── pointers and lookups ─────────────────────────────────────────────────────

const escapeSegment = (segment: string): string => segment.replace(/~/g, '~0').replace(/\//g, '~1');
const unescapeSegment = (segment: string): string => segment.replace(/~1/g, '/').replace(/~0/g, '~');

export function pointerOf(...segments: readonly (string | number)[]): string {
  return segments.map((segment) => `/${escapeSegment(String(segment))}`).join('');
}

export function segmentsOf(pointer: string): string[] {
  return pointer === '' ? [] : pointer.slice(1).split('/').map(unescapeSegment);
}

type Json = Record<string, unknown>;

export function isRecord(value: unknown): value is Json {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

export function isSecretLeaf(value: unknown): value is CredentialsSecretLeaf {
  return isRecord(value) && value['secret'] === true && typeof value['set'] === 'boolean';
}

export function valueAt(data: unknown, segments: readonly string[]): unknown {
  let node: unknown = data;
  for (const segment of segments) {
    if (Array.isArray(node)) node = node[Number(segment)];
    else if (isRecord(node)) node = node[segment];
    else return undefined;
  }
  return node;
}

/** What a text control shows for a saved leaf. */
export function savedText(saved: unknown): string {
  if (typeof saved === 'string') return saved;
  if (typeof saved === 'number') return String(saved);
  return '';
}

export function savedStrings(saved: unknown): readonly string[] {
  return Array.isArray(saved) ? saved.filter((item): item is string => typeof item === 'string') : [];
}

export function isSecretSet(saved: unknown): boolean {
  return isSecretLeaf(saved) ? saved.set : false;
}

// ── what the form shows ──────────────────────────────────────────────────────

export function textValue(view: CredentialsLocalView, drafts: Drafts, pointer: string): string {
  const draft = drafts.values[pointer];
  return typeof draft === 'string' ? draft : savedText(valueAt(view.data, segmentsOf(pointer)));
}

export function switchValue(view: CredentialsLocalView, drafts: Drafts, pointer: string): boolean {
  const draft = drafts.values[pointer];
  if (typeof draft === 'boolean') return draft;
  return valueAt(view.data, segmentsOf(pointer)) === true;
}

export function listValue(view: CredentialsLocalView, drafts: Drafts, pointer: string): readonly string[] {
  const draft = drafts.values[pointer];
  return Array.isArray(draft) ? (draft as readonly string[]) : savedStrings(valueAt(view.data, segmentsOf(pointer)));
}

/** Database rows still in the file, with the index each had when loaded. */
export function existingRows(view: CredentialsLocalView, drafts: Drafts, listPointer: string): readonly number[] {
  const saved = valueAt(view.data, segmentsOf(listPointer));
  const removed = drafts.removed[listPointer] ?? [];
  if (!Array.isArray(saved)) return [];
  return saved.map((_row, index) => index).filter((index) => !removed.includes(index));
}

// ── editing ──────────────────────────────────────────────────────────────────

export function setValue(drafts: Drafts, pointer: string, value: string | boolean | readonly string[]): Drafts {
  return { ...drafts, values: { ...drafts.values, [pointer]: value } };
}

export function setSecret(drafts: Drafts, pointer: string, draft: SecretDraft | undefined): Drafts {
  const secrets = { ...drafts.secrets };
  if (draft === undefined) delete secrets[pointer];
  else secrets[pointer] = draft;
  return { ...drafts, secrets };
}

export function removeDatabase(drafts: Drafts, listPointer: string, index: number): Drafts {
  const removed = drafts.removed[listPointer] ?? [];
  if (removed.includes(index)) return drafts;
  return { ...drafts, removed: { ...drafts.removed, [listPointer]: [...removed, index] } };
}

export function addDatabase(drafts: Drafts, listPointer: string): Drafts {
  const rows = drafts.added[listPointer] ?? [];
  const id = rows.reduce((max, row) => Math.max(max, row.id), 0) + 1;
  const values = Object.fromEntries(DATABASE_FIELDS.map((field) => [field, ''])) as Record<DatabaseField, string>;
  return { ...drafts, added: { ...drafts.added, [listPointer]: [...rows, { id, values }] } };
}

export function editAddedDatabase(
  drafts: Drafts,
  listPointer: string,
  id: number,
  field: DatabaseField,
  value: string,
): Drafts {
  const rows = (drafts.added[listPointer] ?? []).map((row) =>
    row.id === id ? { ...row, values: { ...row.values, [field]: value } } : row,
  );
  return { ...drafts, added: { ...drafts.added, [listPointer]: rows } };
}

export function removeAddedDatabase(drafts: Drafts, listPointer: string, id: number): Drafts {
  const rows = (drafts.added[listPointer] ?? []).filter((row) => row.id !== id);
  return { ...drafts, added: { ...drafts.added, [listPointer]: rows } };
}

// ── diff → ops ───────────────────────────────────────────────────────────────

function sameStrings(a: readonly string[], b: readonly string[]): boolean {
  return a.length === b.length && a.every((item, index) => item === b[index]);
}

/** A whole-number interval of at least one minute, or why not. */
export function intervalProblem(text: string): string | null {
  return /^\d+$/.test(text.trim()) && Number(text.trim()) >= 1 ? null : 'Enter a whole number of at least 1.';
}

/**
 * The value a text draft is stored as. The interval is a number; any other leaf keeps the
 * type the file already has, so a port someone wrote as a number stays one and the template's
 * string stays a string.
 */
function typedValue(pointer: string, saved: unknown, text: string): string | number {
  if (pointer === WORK_FEEDBACK_INTERVAL) return Number(text.trim());
  if (typeof saved === 'number' && /^-?\d+$/.test(text.trim())) return Number(text.trim());
  return text;
}

/**
 * The ops that make the file match the drafts. Ordered so each one is valid when applied after
 * the previous: leaf edits first, then removals from the highest index down (so earlier indices
 * stay put), then appends. A parent the file lacks is created by the first op that needs it.
 */
export function reportDrafts(view: CredentialsLocalView, drafts: Drafts): DraftReport {
  // Nothing edited yet: no clone of the document on every render of a pristine form.
  if (drafts === EMPTY_DRAFTS) return { ops: [], problems: {}, changes: 0 };
  const working: unknown = structuredClone(view.data ?? {});
  const ops: CredentialsPatchOp[] = [];
  const problems: Record<string, string> = {};
  let changes = 0;

  /** Set `segments` to `value`, creating the nearest missing ancestor in one op. */
  function emit(segments: readonly string[], value: unknown): void {
    let node: unknown = working;
    for (let depth = 0; depth < segments.length; depth += 1) {
      const key = segments[depth] as string;
      const last = depth === segments.length - 1;
      if (!isRecord(node)) {
        ops.push({ op: 'set', pointer: pointerOf(...segments), value });
        return;
      }
      if (last) {
        node[key] = value;
        ops.push({ op: 'set', pointer: pointerOf(...segments), value });
        return;
      }
      if (!(key in node)) {
        let nested: unknown = value;
        for (let i = segments.length - 1; i > depth; i -= 1) nested = { [segments[i] as string]: nested };
        node[key] = nested;
        ops.push({ op: 'set', pointer: pointerOf(...segments.slice(0, depth + 1)), value: nested });
        return;
      }
      node = node[key];
    }
  }

  const underRemovedRow = (pointer: string): boolean =>
    Object.entries(drafts.removed).some(([list, indices]) => indices.some((index) => pointer.startsWith(`${list}/${index}/`)));

  for (const [pointer, draft] of Object.entries(drafts.values)) {
    if (underRemovedRow(pointer)) continue;
    const segments = segmentsOf(pointer);
    const saved = valueAt(view.data, segments);
    if (typeof draft === 'boolean') {
      if (draft === (saved === true)) continue;
      changes += 1;
      emit(segments, draft);
    } else if (typeof draft === 'string') {
      if (pointer === WORK_FEEDBACK_INTERVAL) {
        const problem = intervalProblem(draft);
        if (problem !== null) {
          problems[pointer] = problem;
          changes += 1;
          continue;
        }
      }
      if (draft === savedText(saved) || (pointer === WORK_FEEDBACK_INTERVAL && Number(draft.trim()) === saved)) continue;
      changes += 1;
      emit(segments, typedValue(pointer, saved, draft));
    } else {
      if (sameStrings(draft, savedStrings(saved))) continue;
      changes += 1;
      emit(segments, [...draft]);
    }
  }

  for (const [pointer, draft] of Object.entries(drafts.secrets)) {
    if (underRemovedRow(pointer)) continue;
    const saved = valueAt(view.data, segmentsOf(pointer));
    if (draft.kind === 'replace') {
      if (draft.value === '') continue;
      changes += 1;
      emit(segmentsOf(pointer), draft.value);
    } else {
      if (!isSecretSet(saved)) continue;
      changes += 1;
      emit(segmentsOf(pointer), '');
    }
  }

  for (const [listPointer, indices] of Object.entries(drafts.removed)) {
    for (const index of [...indices].sort((a, b) => b - a)) {
      changes += 1;
      ops.push({ op: 'unset', pointer: `${listPointer}/${index}` });
    }
  }

  for (const [listPointer, rows] of Object.entries(drafts.added)) {
    if (rows.length === 0) continue;
    const segments = segmentsOf(listPointer);
    const current = valueAt(working, segments);
    if (current !== undefined && !Array.isArray(current)) {
      // Overwriting it would destroy whatever the file keeps there.
      problems[listPointer] = 'The file keeps something here that is not a list of databases. Fix it in the file before adding one.';
      changes += rows.length;
      continue;
    }
    if (current === undefined) emit(segments, []);
    for (const row of rows) {
      changes += 1;
      ops.push({ op: 'set', pointer: `${listPointer}/-`, value: { ...row.values } });
    }
  }

  return { ops, problems, changes };
}
