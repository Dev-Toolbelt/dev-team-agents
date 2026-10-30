import {
  CREDENTIALS_MAX_SECRET_BYTES,
  CREDENTIALS_PRODUCTION_KEY,
  CREDENTIALS_SECRETS_KEY,
  CREDENTIALS_STORED_PENDING,
  type CredentialsPatchOp,
  type CredentialsSecretLeaf,
} from '../../shared/api.js';

/**
 * The free-form credentials file as the editor sees it (ADR-0024).
 *
 * An edit is an op in a journal, in the order the user made it. The working copy the screen draws is
 * the loaded document with that journal applied, using the same semantics `cred local patch` applies
 * on disk, so what is drawn is what a save writes. A hidden value never reaches the app: renaming
 * one is a `move` the CLI performs.
 */

export type Path = readonly (string | number)[];
export type Doc = Readonly<Record<string, unknown>>;

export const MAX_OPS = 64;

export const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null && !Array.isArray(value);

export function isSecretLeaf(value: unknown): value is CredentialsSecretLeaf {
  return isRecord(value) && value['secret'] === true && typeof value['set'] === 'boolean';
}

/** A group the editor descends into: an object or a list, never a hidden value. */
export const isContainer = (value: unknown): value is Record<string, unknown> | unknown[] =>
  Array.isArray(value) || (isRecord(value) && !isSecretLeaf(value));

export const isReserved = (key: string): boolean => key === CREDENTIALS_SECRETS_KEY || key === CREDENTIALS_PRODUCTION_KEY;

const escapeToken = (token: string | number): string => String(token).replace(/~/g, '~0').replace(/\//g, '~1');

export const pointerOf = (path: Path): string => path.map((token) => `/${escapeToken(token)}`).join('');

export function valueAt(doc: unknown, path: Path): unknown {
  let node: unknown = doc;
  for (const token of path) {
    if (Array.isArray(node) && typeof token === 'number') node = node[token];
    else if (isRecord(node) && typeof token === 'string') node = node[token];
    else return undefined;
  }
  return node;
}

/** The names `$secrets` marks in `node`, or an empty set when it is absent or malformed. */
export function markedIn(node: unknown): ReadonlySet<string> {
  const listed = isRecord(node) ? node[CREDENTIALS_SECRETS_KEY] : undefined;
  return new Set(Array.isArray(listed) ? listed.filter((name): name is string => typeof name === 'string') : []);
}

/** Whether `path` itself, or any object above it, carries `"$production": true`. */
export function productionAt(doc: unknown, path: Path): { own: boolean; inherited: boolean } {
  const own = valueAt(doc, [...path, CREDENTIALS_PRODUCTION_KEY]) === true;
  let inherited = false;
  for (let depth = 0; depth < path.length; depth += 1) {
    if (valueAt(doc, [...path.slice(0, depth), CREDENTIALS_PRODUCTION_KEY]) === true) inherited = true;
  }
  return { own, inherited };
}

// ── references (ADR-0053) ────────────────────────────────────────────────────────

/** The reserved key of a leaf that points at a value instead of holding it. */
export const REFERENCE_KEY = '$ref';

// These mirror `_OP_REF` and `_BW_REF` in credentials_local.py, which match the whole string.
/* eslint-disable no-control-regex -- the CLI refuses control characters in a reference */
const OP_REFERENCE = /^op:\/\/[^\s\u0000-\u001f]+$/;
const BW_REFERENCE =
  /^bw:\/\/[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}\/[^\s/\u0000-\u001f][^/\u0000-\u001f]{0,127}$/;
/* eslint-enable no-control-regex */

/** Why `text` is not a reference the user may write by hand (it mirrors the CLI's check), or `null`. */
export function referenceProblem(text: string): string | null {
  const ref = text.trim();
  return OP_REFERENCE.test(ref) || BW_REFERENCE.test(ref)
    ? null
    : 'Use op://vault/item/field (1Password) or bw://item-uuid/field (Bitwarden)';
}

/** Why `text` cannot be stored as a secret value, or `null`. Mirrors the CLI's limits (ADR-0010, ADR-0053). */
export function secretValueProblem(text: string): string | null {
  if (new TextEncoder().encode(text).length > CREDENTIALS_MAX_SECRET_BYTES) {
    return `Too long: a secret holds at most ${CREDENTIALS_MAX_SECRET_BYTES} bytes`;
  }
  return /[\n\r\0]/.test(text) ? 'A secret cannot contain a line break or NUL' : null;
}

/** What `cred local show` would report as `stored` for a reference typed by hand. */
const storedOfReference = (ref: string): string => (ref.startsWith('bw://') ? 'bw' : 'op');

/** A secret the file keeps as plain text: `stored` is `null`, not merely absent (an older CLI). */
export const isPlaintextSecret = (value: unknown): value is CredentialsSecretLeaf =>
  isSecretLeaf(value) && value.set && value.stored === null;

// ── applying ops, mirroring credentials_local.py ─────────────────────────────────

function tokensOf(pointer: string): string[] {
  return pointer
    .slice(1)
    .split('/')
    .map((raw) => raw.replace(/~1/g, '/').replace(/~0/g, '~'));
}

function step(node: unknown, token: string): unknown {
  if (Array.isArray(node)) return node[Number(token)];
  return isRecord(node) ? node[token] : undefined;
}

function setIn(doc: Record<string, unknown>, tokens: string[], value: unknown): void {
  let node: unknown = doc;
  for (const token of tokens.slice(0, -1)) {
    if (isRecord(node) && !(token in node)) node[token] = {};
    node = step(node, token);
  }
  const last = tokens[tokens.length - 1] ?? '';
  if (Array.isArray(node)) {
    if (last === '-' || Number(last) === node.length) node.push(value);
    else node[Number(last)] = value;
  } else if (isRecord(node)) node[last] = value;
}

function unsetIn(doc: Record<string, unknown>, tokens: string[]): void {
  let node: unknown = doc;
  for (const token of tokens.slice(0, -1)) node = step(node, token);
  const last = tokens[tokens.length - 1] ?? '';
  if (Array.isArray(node)) node.splice(Number(last), 1);
  else if (isRecord(node)) delete node[last];
}

const referenceLeaf = (stored: string): CredentialsSecretLeaf => ({ secret: true, set: true, marked: true, stored });

/** Add the key at `tokens` to its parent's `$secrets`, as `set-secret` does on disk. */
function markSecret(doc: Record<string, unknown>, tokens: string[]): void {
  const key = tokens[tokens.length - 1];
  const parent = tokens.slice(0, -1).reduce<unknown>(step, doc);
  if (key === undefined || !isRecord(parent) || Array.isArray(parent)) return;
  const names = markedIn(parent);
  if (!names.has(key)) parent[CREDENTIALS_SECRETS_KEY] = [...names, key].sort();
}

/** The working copy: `data` with `ops` applied in order. Never mutates `data`. */
export function applyOps(data: Doc, ops: readonly CredentialsPatchOp[]): Doc {
  const doc = structuredClone(data) as Record<string, unknown>;
  for (const op of ops) {
    if (op.op === 'set') {
      const ref = isRecord(op.value) ? op.value[REFERENCE_KEY] : undefined;
      // A hand-written reference reads back redacted, so the working copy shows it the same way.
      setIn(doc, tokensOf(op.pointer), typeof ref === 'string' ? referenceLeaf(storedOfReference(ref)) : structuredClone(op.value));
    } else if (op.op === 'set-secret') {
      // The CLI stores the value and writes a reference; the working copy shows it as stored.
      const tokens = tokensOf(op.pointer);
      setIn(doc, tokens, referenceLeaf(CREDENTIALS_STORED_PENDING));
      markSecret(doc, tokens);
    } else if (op.op === 'unset') unsetIn(doc, tokensOf(op.pointer));
    else {
      const value = tokensOf(op.from).reduce<unknown>(step, doc);
      unsetIn(doc, tokensOf(op.from));
      setIn(doc, tokensOf(op.pointer), value);
    }
  }
  return doc;
}

/** Append `op`, folding it into the previous op when both set the same pointer. */
export function record(ops: readonly CredentialsPatchOp[], ...added: CredentialsPatchOp[]): CredentialsPatchOp[] {
  const out = [...ops];
  for (const op of added) {
    const last = out[out.length - 1];
    // The last write to a pointer wins, so a typed value then a reference (or the reverse) is one op.
    const writes = (candidate: CredentialsPatchOp | undefined): boolean => candidate?.op === 'set' || candidate?.op === 'set-secret';
    if (writes(op) && writes(last) && last !== undefined && 'pointer' in last && last.pointer === op.pointer) out[out.length - 1] = op;
    else out.push(op);
  }
  return out;
}

// ── edits ────────────────────────────────────────────────────────────────────────

export type Edit =
  | { kind: 'value'; path: Path; value: unknown }
  /** A secret value typed by the user: the CLI stores it and keeps a reference (ADR-0053). */
  | { kind: 'secret-value'; path: Path; value: string }
  /** A password-manager reference typed by hand (`op://…`, `bw://…`): not itself secret. */
  | { kind: 'reference'; path: Path; ref: string }
  | { kind: 'add'; parent: Path; key: string | null; value: unknown }
  | { kind: 'remove'; path: Path }
  | { kind: 'rename'; path: Path; to: string }
  | { kind: 'move'; path: Path; into: Path }
  | { kind: 'secret'; path: Path; marked: boolean }
  | { kind: 'production'; path: Path; on: boolean };

/** Why `edit` cannot be made against `doc`, or `null`. */
export function editProblem(doc: Doc, edit: Edit): string | null {
  if (edit.kind === 'reference') return referenceProblem(edit.ref);
  if (edit.kind === 'secret-value') return secretValueProblem(edit.value);
  const parentOf = (path: Path): unknown => valueAt(doc, path.slice(0, -1));
  if (edit.kind === 'add' && edit.key !== null) {
    const key = edit.key.trim();
    if (key === '') return 'A name is required';
    if (key.startsWith('$')) return 'Names starting with $ are reserved';
    if (isRecord(valueAt(doc, edit.parent)) && key in (valueAt(doc, edit.parent) as Record<string, unknown>)) {
      return `"${key}" already exists here`;
    }
  }
  if (edit.kind === 'rename') {
    const to = edit.to.trim();
    if (to === '') return 'A name is required';
    if (to.startsWith('$')) return 'Names starting with $ are reserved';
    const parent = parentOf(edit.path);
    if (isRecord(parent) && to !== edit.path[edit.path.length - 1] && to in parent) return `"${to}" already exists here`;
  }
  if (edit.kind === 'move') {
    const key = edit.path[edit.path.length - 1];
    if (typeof key !== 'string') return 'Only a named field or group can be moved';
    if (pointerOf(edit.path.slice(0, -1)) === pointerOf(edit.into)) return 'It is already in that group';
    if (isInside(edit.into, edit.path)) return 'A group cannot move inside itself';
    const target = valueAt(doc, edit.into);
    if (!isRecord(target) || isSecretLeaf(target)) return 'Pick a group to move it into';
    if (key in target) return `That group already has "${key}"`;
  }
  return null;
}

/** Whether `path` is `ancestor` or sits below it. */
const isInside = (path: Path, ancestor: Path): boolean =>
  path.length >= ancestor.length && ancestor.every((token, index) => token === path[index]);

/**
 * Every group `path` could move into: the file itself and each object in it, outside `path`'s own
 * subtree and other than its current parent. Lists are left out: what moves keeps its name.
 */
export function moveTargets(doc: Doc, path: Path): Path[] {
  const key = path[path.length - 1];
  const out: Path[] = [];
  const walk = (node: unknown, at: Path): void => {
    if (!isRecord(node) || isSecretLeaf(node) || isInside(at, path)) return;
    if (pointerOf(at) !== pointerOf(path.slice(0, -1)) && !(typeof key === 'string' && key in node)) out.push(at);
    for (const [child, value] of Object.entries(node)) if (!isReserved(child)) walk(value, [...at, child]);
  };
  walk(doc, []);
  return out;
}

/** The ops that make `edit`, given the working copy `doc` it was made against. */
export function opsFor(doc: Doc, edit: Edit): CredentialsPatchOp[] {
  switch (edit.kind) {
    case 'value':
      return [{ op: 'set', pointer: pointerOf(edit.path), value: edit.value }];
    case 'secret-value':
      return [{ op: 'set-secret', pointer: pointerOf(edit.path), value: edit.value }];
    case 'reference':
      return [{ op: 'set', pointer: pointerOf(edit.path), value: { [REFERENCE_KEY]: edit.ref.trim() } }];
    case 'add': {
      const parent = valueAt(doc, edit.parent);
      const token = Array.isArray(parent) ? '-' : (edit.key ?? '').trim();
      return [{ op: 'set', pointer: `${pointerOf(edit.parent)}/${escapeToken(token)}`, value: edit.value }];
    }
    case 'remove': {
      const ops: CredentialsPatchOp[] = [{ op: 'unset', pointer: pointerOf(edit.path) }];
      return [...ops, ...secretsListOps(doc, edit.path.slice(0, -1), edit.path[edit.path.length - 1], null)];
    }
    case 'rename': {
      const from = edit.path[edit.path.length - 1];
      const to = edit.to.trim();
      if (to === from) return [];
      const target = [...edit.path.slice(0, -1), to];
      return [
        { op: 'move', from: pointerOf(edit.path), pointer: pointerOf(target) },
        ...secretsListOps(doc, edit.path.slice(0, -1), from, to),
      ];
    }
    case 'move': {
      const from = edit.path[edit.path.length - 1];
      if (typeof from !== 'string') return [];
      const parent = edit.path.slice(0, -1);
      const ops: CredentialsPatchOp[] = [{ op: 'move', from: pointerOf(edit.path), pointer: pointerOf([...edit.into, from]) }];
      // A secret stays a secret where it lands: its mark moves with it.
      if (markedIn(valueAt(doc, parent)).has(from)) {
        ops.push(...secretsListOps(doc, parent, from, null));
        const names = new Set(markedIn(valueAt(doc, edit.into)));
        names.add(from);
        ops.push(listOp(edit.into, names));
      }
      return ops;
    }
    case 'secret': {
      const parent = edit.path.slice(0, -1);
      const key = edit.path[edit.path.length - 1];
      if (typeof key !== 'string') return [];
      const names = new Set(markedIn(valueAt(doc, parent)));
      if (edit.marked) names.add(key);
      else names.delete(key);
      return [listOp(parent, names)];
    }
    case 'production':
      return edit.on
        ? [{ op: 'set', pointer: pointerOf([...edit.path, CREDENTIALS_PRODUCTION_KEY]), value: true }]
        : [{ op: 'unset', pointer: pointerOf([...edit.path, CREDENTIALS_PRODUCTION_KEY]) }];
  }
}

function listOp(parent: Path, names: ReadonlySet<string>): CredentialsPatchOp {
  const pointer = pointerOf([...parent, CREDENTIALS_SECRETS_KEY]);
  return names.size === 0 ? { op: 'unset', pointer } : { op: 'set', pointer, value: [...names].sort() };
}

/** Keep `$secrets` in step when a marked key is removed (`to === null`) or renamed. */
function secretsListOps(doc: Doc, parent: Path, from: string | number | undefined, to: string | null): CredentialsPatchOp[] {
  if (typeof from !== 'string') return [];
  const names = new Set(markedIn(valueAt(doc, parent)));
  if (!names.has(from)) return [];
  names.delete(from);
  if (to !== null) names.add(to);
  return [listOp(parent, names)];
}

// ── search ───────────────────────────────────────────────────────────────────────

/**
 * Pointers of every node that matches `query` (on a key name or a visible scalar value), plus
 * their ancestors so the match stays reachable. `null` when there is no query. A hidden value is
 * never searched: it is not in the app.
 */
export function searchHits(doc: Doc, query: string): ReadonlySet<string> | null {
  const needle = query.trim().toLowerCase();
  if (needle === '') return null;
  const hits = new Set<string>();
  const walk = (node: unknown, path: Path): void => {
    const entries: [string | number, unknown][] = Array.isArray(node)
      ? node.map((item, index) => [index, item])
      : isRecord(node)
        ? Object.entries(node).filter(([key]) => !isReserved(key))
        : [];
    for (const [key, child] of entries) {
      const childPath = [...path, key];
      const own =
        (typeof key === 'string' && key.toLowerCase().includes(needle)) ||
        (!isContainer(child) && !isSecretLeaf(child) && scalarText(child).toLowerCase().includes(needle));
      if (own) for (let depth = 1; depth <= childPath.length; depth += 1) hits.add(pointerOf(childPath.slice(0, depth)));
      if (isContainer(child)) walk(child, childPath);
    }
  };
  walk(doc, []);
  return hits;
}

/** A scalar as the text a field shows: empty for null, the plain spelling otherwise. */
export function scalarText(value: unknown): string {
  return typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean' ? String(value) : '';
}

/** Parse the text typed into a field the way the value it replaces was typed. */
export function coerce(text: string, previous: unknown): { value: unknown; problem: string | null } {
  if (typeof previous === 'number') {
    const trimmed = text.trim();
    if (trimmed !== '' && Number.isFinite(Number(trimmed))) return { value: Number(trimmed), problem: null };
    return { value: text, problem: 'Must be a number' };
  }
  return { value: text, problem: null };
}

/** Pointers of every secret the working copy shows as plain text in the file (ADR-0053 § 5). */
export function plaintextSecrets(doc: Doc): { pointer: string; production: boolean }[] {
  const found: { pointer: string; production: boolean }[] = [];
  const walk = (node: unknown, path: Path): void => {
    const entries: [string | number, unknown][] = Array.isArray(node)
      ? node.map((item, index) => [index, item])
      : isRecord(node)
        ? Object.entries(node).filter(([key]) => !isReserved(key))
        : [];
    for (const [key, child] of entries) {
      const childPath = [...path, key];
      if (isPlaintextSecret(child)) {
        const production = productionAt(doc, childPath.slice(0, -1));
        found.push({ pointer: pointerOf(childPath), production: production.own || production.inherited });
      } else if (isContainer(child)) walk(child, childPath);
    }
  };
  walk(doc, []);
  return found;
}

/** Whether `op` is a typed secret or a hand-written reference: the writes a secret field holds back. */
const isSecretWrite = (op: CredentialsPatchOp): boolean =>
  op.op === 'set-secret' || (op.op === 'set' && isRecord(op.value) && typeof op.value[REFERENCE_KEY] === 'string');

/** `ops` without the pending secret value or reference for `pointer`: what clearing the field means. */
export function forgetSecretWrite(ops: readonly CredentialsPatchOp[], pointer: string): CredentialsPatchOp[] {
  return ops.filter((op) => !(isSecretWrite(op) && 'pointer' in op && op.pointer === pointer));
}

/** Pointers that hold a typed secret or reference not saved yet. */
export function pendingSecretPointers(ops: readonly CredentialsPatchOp[]): ReadonlySet<string> {
  return new Set(ops.filter(isSecretWrite).map((op) => ('pointer' in op ? op.pointer : '')));
}

/** `ops` without any pending secret write at `pointer` or below it: what removing that field means. */
export function forgetSecretWritesUnder(ops: readonly CredentialsPatchOp[], pointer: string): CredentialsPatchOp[] {
  return ops.filter((op) => !(isSecretWrite(op) && 'pointer' in op && (op.pointer === pointer || op.pointer.startsWith(`${pointer}/`))));
}
