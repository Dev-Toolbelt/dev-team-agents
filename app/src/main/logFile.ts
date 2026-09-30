/**
 * A small diagnostic log for a packaged build.
 *
 * A packaged app has no terminal: a failed CLI spawn, a notification stream stuck in a
 * retry loop, or a crashed renderer would otherwise leave nothing anywhere to read. One
 * file under Electron's `logs` directory, appended synchronously (so a line written just
 * before a crash survives it) and rotated to a single `.old` sibling at a size cap, so it
 * can never grow without bound. **Logging must never be the thing that fails**: every
 * filesystem error is swallowed, because this runs inside crash handlers.
 *
 * Imports nothing from `electron`; `index.ts` supplies the directory.
 */

import { appendFileSync, mkdirSync, renameSync, statSync } from 'node:fs';
import { join } from 'node:path';

export const LOG_FILE_NAME = 'main.log';
export const OLD_LOG_FILE_NAME = 'main.old.log';
export const LOG_MAX_BYTES = 1024 * 1024;
/** Per message: one runaway line must not be the whole file. */
const MAX_LINE_CHARS = 8 * 1024;

export interface FileLog {
  readonly path: string;
  /** Append one timestamped line. Never throws. */
  readonly write: (message: string) => void;
}

export function createFileLog(directory: string, maxBytes: number = LOG_MAX_BYTES): FileLog {
  const path = join(directory, LOG_FILE_NAME);
  const old = join(directory, OLD_LOG_FILE_NAME);
  return {
    path,
    write: (message) => {
      try {
        mkdirSync(directory, { recursive: true });
        try {
          if (statSync(path).size >= maxBytes) renameSync(path, old);
        } catch {
          // No file yet, or it could not be rotated: appending still works.
        }
        // One line per call: a message with line breaks — including a lone `\r` or the
        // Unicode separators, which the CLI's text can carry — would read as several
        // records, or overwrite one in a terminal. Capped so one message cannot fill the file.
        const line = message.replace(/\r\n|[\r\n\u2028\u2029]/g, ' | ').slice(0, MAX_LINE_CHARS);
        appendFileSync(path, `${new Date().toISOString()} ${line}\n`, 'utf8');
      } catch {
        // See the header: a log that throws turns a diagnosis into a second failure.
      }
    },
  };
}

/** `error` as text with its stack when it has one, for the crash handlers. */
export function describeError(error: unknown): string {
  if (error instanceof Error) return error.stack ?? `${error.name}: ${error.message}`;
  try {
    return typeof error === 'string' ? error : JSON.stringify(error);
  } catch {
    return String(error);
  }
}
