/**
 * The rules an integration card applies to an `IntegrationView`, as pure functions so what a
 * person cannot see (which fields show, what counts as a change, what blocks a save) is
 * testable without a DOM. Nothing here knows an integration by name.
 */
import type { IntegrationField, IntegrationFieldScope, IntegrationView } from '../../shared/api.js';
import type { Standing } from '../cards/CardShell.js';

export type FieldDrafts = Readonly<Record<string, string>>;

const AMBER = 'border-amber-500/60 text-amber-800 dark:text-amber-300';

/** The one badge a card leads with. Problems the last test found outrank a plain "Connected". */
export function standingOf(view: IntegrationView): Standing {
  if (view.auth.stale) return { label: 'Token needs reconnecting', variant: 'outline', className: AMBER };
  switch (view.status.state) {
    case 'invalid_token':
      return { label: 'Invalid token', variant: 'destructive' };
    case 'rate_limited':
      return { label: 'Rate limited', variant: 'outline', className: AMBER };
    case 'unreachable':
      return { label: 'Unreachable', variant: 'outline', className: AMBER };
    default:
  }
  if (!view.connected) return { label: 'Not connected', variant: 'secondary' };
  if (view.status.state === 'connected') {
    return { label: 'Connected', variant: 'outline', className: 'border-green-600 text-green-800 dark:text-green-300' };
  }
  return { label: 'Not tested', variant: 'outline', className: 'text-muted-foreground' };
}

/** The value in `values` for a field, falling back to its declared default, then to nothing. */
export function savedValue(field: IntegrationField, values: Readonly<Record<string, string>>): string {
  return values[field.key] ?? field.default ?? '';
}

export function scopeValues(view: IntegrationView, scope: IntegrationFieldScope): Readonly<Record<string, string>> {
  return scope === 'account' ? view.account : (view.project ?? {});
}

/** What a field shows and would send: its draft, else the saved value. */
export function effectiveValue(field: IntegrationField, values: Readonly<Record<string, string>>, drafts: FieldDrafts): string {
  return field.key in drafts ? (drafts[field.key] ?? '') : savedValue(field, values);
}

/** The fields of one scope that are visible given the values they depend on. */
export function visibleFields(view: IntegrationView, scope: IntegrationFieldScope, drafts: FieldDrafts): IntegrationField[] {
  const values = scopeValues(view, scope);
  const scoped = view.fields.filter((field) => field.scope === scope);
  return scoped.filter((field) => {
    const rule = field.visible_when;
    if (rule === null) return true;
    const controlling = scoped.find((candidate) => candidate.key === rule.key);
    const current = controlling !== undefined ? effectiveValue(controlling, values, drafts) : (values[rule.key] ?? '');
    return current === rule.equals;
  });
}

export interface FieldState {
  readonly field: IntegrationField;
  readonly display: string;
  readonly changed: boolean;
  readonly error: string | null;
}

/** One state per visible field; a required field left blank is an error, never a silent write. */
export function fieldStates(view: IntegrationView, scope: IntegrationFieldScope, drafts: FieldDrafts): FieldState[] {
  const values = scopeValues(view, scope);
  return visibleFields(view, scope, drafts).map((field) => {
    const display = effectiveValue(field, values, drafts);
    const changed = field.key in drafts && display !== savedValue(field, values);
    const error = field.required && display.trim() === '' ? 'This is required.' : null;
    return { field, display, changed, error };
  });
}

/** Drafts that differ from what is saved, for visible fields only; a hidden field's draft is never written. */
export function changedValues(states: readonly FieldState[]): Record<string, string> {
  return Object.fromEntries(states.filter((state) => state.changed).map((state) => [state.field.key, state.display.trim()]));
}
