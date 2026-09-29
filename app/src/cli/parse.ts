/**
 * "Exactly one JSON document on stdout" — the parser for that rule.
 *
 * `JSON.parse` alone cannot tell "one object" from "two objects concatenated": it
 * fails on both, identically, and a layer that treated a parse failure as "not JSON"
 * would report the wrong defect for the case that actually happens — a stray `print`
 * in a command, or a warning that escaped onto stdout instead of stderr. So stdout is
 * scanned into top-level segments first, and the count is part of the verdict.
 */

import type { CliDocument, ContractBreachReason } from './contract.js';

export interface ScanResult {
  /** Complete top-level JSON values, in order, as raw text. */
  readonly values: string[];
  /** Non-whitespace runs that do not begin a JSON value. */
  readonly garbage: string[];
  /** A value that began but never closed (unbalanced braces, truncated output). */
  readonly unterminated: string | null;
}

const WHITESPACE = new Set([' ', '\t', '\n', '\r', '\f', '\v']);

/**
 * Split text into top-level *structured* JSON values without parsing them.
 *
 * String-aware (a `}` inside a string does not close an object) and escape-aware (a
 * `\"` inside a string does not end it).
 *
 * **Only `{` and `[` start a value.** A bare quoted string or scalar is recorded as
 * garbage, even though JSON would accept it as a document. The contract says the document
 * is an object with an `ok` field, and counting loose strings as documents misclassified
 * the case that actually happens: a python traceback contains `File "x", line 1`, whose
 * `"x"` is a valid JSON string — so a traceback was reported as `multiple-documents`
 * rather than as `not-json`. `parseSingleDocument` still reports a lone scalar as
 * `not-an-object`, using the garbage it collected here.
 */
export function scanTopLevelJson(text: string): ScanResult {
  const values: string[] = [];
  const garbage: string[] = [];
  let unterminated: string | null = null;

  let i = 0;
  while (i < text.length) {
    const ch = text[i] as string;
    if (WHITESPACE.has(ch)) {
      i += 1;
      continue;
    }
    const start = i;
    if (ch === '{' || ch === '[') {
      let depth = 0;
      let inString = false;
      let escaped = false;
      let closed = false;
      for (; i < text.length; i += 1) {
        const c = text[i] as string;
        if (inString) {
          if (escaped) escaped = false;
          else if (c === '\\') escaped = true;
          else if (c === '"') inString = false;
          continue;
        }
        if (c === '"') inString = true;
        else if (c === '{' || c === '[') depth += 1;
        else if (c === '}' || c === ']') {
          depth -= 1;
          if (depth === 0) {
            i += 1;
            closed = true;
            break;
          }
        }
      }
      if (closed) values.push(text.slice(start, i));
      else {
        unterminated = text.slice(start);
        break;
      }
      continue;
    }
    if (ch === '"') {
      // A quoted run. Skipped over as one unit so its contents cannot be mistaken for
      // structure, and recorded as garbage: see the header for why it is not a value.
      let closed = false;
      let escaped = false;
      i += 1;
      for (; i < text.length; i += 1) {
        const c = text[i] as string;
        if (escaped) escaped = false;
        else if (c === '\\') escaped = true;
        else if (c === '"') {
          i += 1;
          closed = true;
          break;
        }
      }
      if (!closed) {
        unterminated = text.slice(start);
        break;
      }
      garbage.push(text.slice(start, i));
      continue;
    }
    // A bare token: plain text, or a JSON scalar. Either way it is not the object the
    // contract describes; read to the next whitespace or structural character.
    while (i < text.length) {
      const c = text[i] as string;
      if (WHITESPACE.has(c) || c === '{' || c === '[' || c === '"') break;
      i += 1;
    }
    garbage.push(text.slice(start, i));
  }

  return { values, garbage, unterminated };
}

export type ParseVerdict =
  | { readonly ok: true; readonly document: CliDocument }
  | { readonly ok: false; readonly reason: ContractBreachReason; readonly detail: string };

/**
 * Turn stdout into exactly one `CliDocument`, or say precisely what was wrong.
 *
 * The success/error discrimination is on the **document**, not on the exit code: exit 1
 * carries a payload from `devteam doctor` and an error document from a bare
 * `DevteamError`, so the exit code cannot be used to guess the shape. An error document
 * is one with `ok === false`, a string `error` and a numeric `exit_code`; anything else
 * with an `ok` field is a payload.
 */
export function parseSingleDocument(stdout: string): ParseVerdict {
  if (stdout.trim() === '') {
    return {
      ok: false,
      reason: 'empty-stdout',
      detail: 'stdout carried no output; a --json invocation always emits one document',
    };
  }

  const scan = scanTopLevelJson(stdout);

  if (scan.unterminated !== null) {
    return {
      ok: false,
      reason: 'not-json',
      detail: `stdout ended in the middle of a JSON value after ${scan.values.length} complete document(s)`,
    };
  }
  if (scan.values.length === 0) {
    // One lone token that happens to be valid JSON — `3`, `"x"`, `null` — is a command
    // emitting the wrong *shape*, which is a different report from "something that is not
    // JSON reached stdout". `Emitter.emit` always dumps a dict, so this is defensive.
    if (scan.garbage.length === 1 && isJsonValue(scan.garbage[0] as string)) {
      return {
        ok: false,
        reason: 'not-an-object',
        detail: `the document is a bare JSON value, not an object with an "ok" field: ${preview(scan.garbage[0] as string)}`,
      };
    }
    return {
      ok: false,
      reason: 'not-json',
      detail: `stdout held no JSON document: ${preview(stdout)}`,
    };
  }
  if (scan.values.length > 1) {
    return {
      ok: false,
      reason: 'multiple-documents',
      detail: `stdout held ${scan.values.length} top-level JSON documents; the contract allows exactly one`,
    };
  }
  if (scan.garbage.length > 0) {
    return {
      ok: false,
      reason: 'trailing-output',
      detail: `one JSON document plus ${scan.garbage.length} non-JSON fragment(s) on stdout: ${preview(scan.garbage.join(' '))}`,
    };
  }

  let parsed: unknown;
  try {
    parsed = JSON.parse(scan.values[0] as string);
  } catch (error) {
    return {
      ok: false,
      reason: 'not-json',
      detail: `stdout is not valid JSON: ${error instanceof Error ? error.message : String(error)}`,
    };
  }

  if (parsed === null || typeof parsed !== 'object' || Array.isArray(parsed)) {
    return {
      ok: false,
      reason: 'not-an-object',
      detail: `the document is a ${Array.isArray(parsed) ? 'array' : typeof parsed}; the contract says it is an object with an "ok" field`,
    };
  }

  const body = parsed as Record<string, unknown>;
  if (!('ok' in body) || typeof body['ok'] !== 'boolean') {
    return {
      ok: false,
      reason: 'missing-ok',
      detail: 'the document has no boolean "ok" field',
    };
  }

  if (body['ok'] === false && typeof body['error'] === 'string' && typeof body['exit_code'] === 'number') {
    const doc: CliDocument = {
      kind: 'error',
      ok: false,
      error: body['error'],
      exitCode: body['exit_code'],
      ...(typeof body['hint'] === 'string' ? { hint: body['hint'] } : {}),
      ...(isRecord(body['details']) ? { details: body['details'] } : {}),
      body,
    };
    return { ok: true, document: doc };
  }

  return { ok: true, document: { kind: 'payload', ok: body['ok'], body } };
}

function isJsonValue(text: string): boolean {
  try {
    JSON.parse(text);
    return true;
  } catch {
    return false;
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function preview(text: string, limit = 160): string {
  const flat = text.replace(/\s+/g, ' ').trim();
  return flat.length > limit ? `${flat.slice(0, limit)}…` : flat;
}
