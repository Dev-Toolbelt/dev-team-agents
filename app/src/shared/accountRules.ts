/**
 * Input rules for the account screens (ADR-0029), shared by the renderer (to disable a
 * submit early) and the main process (the boundary that actually refuses).
 *
 * They mirror `scripts/lib/devteam/auth_gotrue.py` (`normalize_email`, `normalize_code`,
 * `validate_new_password`, `normalize_display_name`). The CLI stays the authority: a rule
 * that drifts here only changes *where* a bad value is refused, never whether it is. Each
 * function returns a problem key, never a sentence, so the renderer can word it in the
 * user's language and main can word it in English.
 *
 * Imports nothing from `electron` or the DOM.
 */

export const CODE_LENGTH = 8;
export const PASSWORD_MIN_CHARS = 10;
export const PASSWORD_MAX_CHARS = 64;
export const PASSWORD_MAX_BYTES = 72;
export const DISPLAY_NAME_MAX = 80;
export const EMAIL_MAX = 254;
/** A sign-in password is only length-bounded: one accepted earlier must still work. */
export const SIGN_IN_PASSWORD_MAX = 1024;

/** The word a person types to confirm deleting the account. */
export const DELETE_CONFIRM_WORD = 'delete';

export type AuthProvider = 'google' | 'github';
export const AUTH_PROVIDERS: readonly AuthProvider[] = Object.freeze(['google', 'github']);

/**
 * Whether the blocked state stops the app (`enforce`) or only warns (`warn`).
 *
 * The CLI's `gate_mode` is compiled into `auth-config.json` and reported in the
 * `auth status` and `auth check` documents. The app reads it from there; before the first
 * document arrives, or when a CLI predating the field answers, it acts as `warn`: a
 * dismissible banner, never a lock-out the CLI itself has not been told to apply.
 */
export type AuthGateMode = 'warn' | 'enforce';
export const DEFAULT_GATE_MODE: AuthGateMode = 'warn';

export type FieldProblem =
  | 'required'
  | 'email-invalid'
  | 'code-invalid'
  | 'password-length'
  | 'name-invalid'
  | 'unsafe-text';

const EMAIL_SHAPE = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

// eslint-disable-next-line no-control-regex
const CONTROL = /[\u0000-\u001f\u007f]/;

/** The address the CLI would use: NFC, trimmed, lower-cased. */
export function normalizeEmail(value: string): string {
  return value.normalize('NFC').trim().toLowerCase();
}

export function emailProblem(value: string): FieldProblem | null {
  const text = normalizeEmail(value);
  if (text === '') return 'required';
  // A value beginning with `-` would read as a flag in the argument vector.
  if (text.length > EMAIL_MAX || text.startsWith('-') || CONTROL.test(text) || !EMAIL_SHAPE.test(text)) {
    return 'email-invalid';
  }
  return null;
}

/** The digits of a code, spaces dropped, as the CLI reads it. */
export function normalizeCode(value: string): string {
  return value.trim().replace(/ /g, '');
}

export function codeProblem(value: string): FieldProblem | null {
  const text = normalizeCode(value);
  if (text === '') return 'required';
  return new RegExp(`^[0-9]{${CODE_LENGTH}}$`).test(text) ? null : 'code-invalid';
}

/** A password being **set**: the policy of SR-15. */
export function newPasswordProblem(value: string): FieldProblem | null {
  if (value === '') return 'required';
  const text = value.normalize('NFC');
  const chars = [...text].length;
  const bytes = new TextEncoder().encode(text).length;
  if (chars < PASSWORD_MIN_CHARS || chars > PASSWORD_MAX_CHARS || bytes > PASSWORD_MAX_BYTES) {
    return 'password-length';
  }
  // eslint-disable-next-line no-control-regex
  if (/[\r\n\u0000]/.test(text)) return 'unsafe-text';
  return null;
}

/**
 * The shortest password worth sending at sign-in. Every account's password was set under the
 * 10-character policy, so a shorter one cannot be right; refusing it here also keeps a value
 * too short to redact safely (`MIN_REDACTABLE` in `cli/invoke.ts`) out of a child's stdin.
 */
export const SIGN_IN_PASSWORD_MIN = 4;

/** A password being **presented**: no policy beyond what can travel on one stdin line. */
export function signInPasswordProblem(value: string): FieldProblem | null {
  if (value === '') return 'required';
  // eslint-disable-next-line no-control-regex
  if (value.length > SIGN_IN_PASSWORD_MAX || /[\r\n\u0000]/.test(value)) return 'unsafe-text';
  if (value.length < SIGN_IN_PASSWORD_MIN) return 'password-length';
  return null;
}

export function displayNameProblem(value: string): FieldProblem | null {
  const text = value.normalize('NFC').trim();
  if (text === '') return 'required';
  // Code points, as the CLI counts them, not UTF-16 units: an emoji is one character.
  if ([...text].length > DISPLAY_NAME_MAX || CONTROL.test(text) || text.startsWith('-')) return 'name-invalid';
  return null;
}

/** Up to two letters for the avatar: the name's initials, else the address's first letter. */
export function initialsOf(displayName: string | null, email: string | null): string {
  const fromName = (displayName ?? '')
    .trim()
    .split(/\s+/)
    .filter((part) => part !== '')
    .map((part) => [...part][0] ?? '')
    .slice(0, 2)
    .join('');
  if (fromName !== '') return fromName.toLocaleUpperCase();
  const first = [...(email ?? '').trim()][0];
  return first === undefined ? '?' : first.toLocaleUpperCase();
}
