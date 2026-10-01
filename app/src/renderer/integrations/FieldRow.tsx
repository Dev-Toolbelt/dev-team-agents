import { useState } from 'react';
import { Undo2 } from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import type { IntegrationResources, OperationResult } from '../../shared/api.js';
import { SELECT_CLASS } from '../formStyles.js';
import { Problem } from '../Problem.js';
import type { FieldState } from './model.js';

type Loaded = { readonly ok: true; readonly data: IntegrationResources } | Extract<OperationResult<never>, { ok: false }>;

/**
 * One row of an integration's form, drawn from the `IntegrationField` alone: the control
 * follows the field's type, never its key. A field that names a `resource` gets a picker that
 * loads its options on demand, and a `detected` value is offered as a one-click suggestion.
 */
export function FieldRow({
  idPrefix,
  state,
  disabled,
  detected,
  loadOptions,
  loadDisabledReason,
  onDraft,
  onUndo,
  stacked = false,
}: {
  idPrefix: string;
  state: FieldState;
  disabled: boolean;
  /** A value inferred without the user, offered when it differs from what is shown. */
  detected?: string | undefined;
  /** Loads the options of `field.resource`; absent where no picker makes sense (account scope). */
  loadOptions?: ((kind: string) => Promise<OperationResult<IntegrationResources>>) | undefined;
  loadDisabledReason?: string | null | undefined;
  onDraft: (value: string) => void;
  onUndo: () => void;
  /** The control under its label rather than beside it — where the form belongs to the label above it. */
  stacked?: boolean;
}) {
  const { field, display, changed, error } = state;
  const id = `${idPrefix}-${field.key}`;
  const helpId = `${id}-help`;
  const errorId = `${id}-error`;
  const describedBy = [field.help !== null ? helpId : null, error !== null ? errorId : null].filter(Boolean).join(' ') || undefined;
  const [options, setOptions] = useState<Loaded | null>(null);
  const [loading, setLoading] = useState(false);
  const picker = field.resource !== null && loadOptions !== undefined;
  const suggestion = detected !== undefined && detected !== '' && detected !== display ? detected : null;

  async function load() {
    if (field.resource === null || loadOptions === undefined) return;
    setLoading(true);
    try {
      const result = await loadOptions(field.resource);
      setOptions(result);
    } catch (error_) {
      setOptions({ ok: false, kind: 'unavailable', message: String(error_), exitCode: null, command: '(ipc)', durationMs: 0 });
    } finally {
      setLoading(false);
    }
  }

  return (
    <div
      className={stacked ? 'grid gap-2 py-4' : 'grid gap-3 py-4 md:grid-cols-[minmax(0,1fr)_minmax(0,22rem)] md:gap-6'}
      data-changed={changed || undefined}
      data-layout={stacked ? 'stacked' : undefined}
    >
      <div className="min-w-0 space-y-1">
        <div className="flex flex-wrap items-center gap-2">
          {changed ? <span className="size-1.5 rounded-full bg-primary" aria-hidden="true" title="Changed" /> : null}
          <Label htmlFor={id} className="text-sm font-medium">
            {field.label}
          </Label>
          {field.required ? (
            <Badge variant="outline" className="font-normal text-muted-foreground">
              required
            </Badge>
          ) : null}
        </div>
        {field.help !== null ? (
          <p id={helpId} className="text-xs text-muted-foreground">
            {field.help}
          </p>
        ) : null}
        {changed ? (
          <Button variant="link" size="sm" className="h-auto p-0 text-xs" disabled={disabled} onClick={onUndo}>
            <Undo2 aria-hidden="true" />
            Undo<span className="sr-only"> {field.label}</span>
          </Button>
        ) : null}
      </div>

      <div className="min-w-0 space-y-1.5">
        {field.type === 'enum' ? (
          <select
            id={id}
            value={display}
            disabled={disabled}
            aria-invalid={error !== null || undefined}
            aria-describedby={describedBy}
            className={SELECT_CLASS}
            onChange={(event) => onDraft(event.target.value)}
          >
            {!field.options.some((option) => option.value === display) ? <option value="">Select…</option> : null}
            {field.options.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        ) : (
          <Input
            id={id}
            value={display}
            disabled={disabled}
            placeholder={field.placeholder ?? undefined}
            spellCheck={false}
            autoComplete="off"
            aria-invalid={error !== null || undefined}
            aria-describedby={describedBy}
            className="font-mono"
            onChange={(event) => onDraft(event.target.value)}
          />
        )}
        {error !== null ? (
          <p id={errorId} className="text-xs text-destructive">
            {error}
          </p>
        ) : null}
        {suggestion !== null ? (
          <Button variant="outline" size="sm" disabled={disabled} onClick={() => onDraft(suggestion)}>
            Use detected: {suggestion}
          </Button>
        ) : null}
        {picker ? (
          <div className="space-y-1.5">
            <Button
              variant="outline"
              size="sm"
              disabled={disabled || loading || (loadDisabledReason ?? null) !== null}
              title={loadDisabledReason ?? undefined}
              onClick={() => void load()}
            >
              {loading ? 'Loading…' : 'Load options'}
            </Button>
            {options !== null && options.ok ? (
              <div className="space-y-1">
                <select
                  aria-label={`${field.label} options`}
                  value=""
                  disabled={disabled}
                  className={SELECT_CLASS}
                  onChange={(event) => {
                    if (event.target.value !== '') onDraft(event.target.value);
                  }}
                >
                  <option value="">{options.data.items.length === 0 ? 'No options found' : 'Choose…'}</option>
                  {options.data.items.map((item) => (
                    <option key={item.value} value={item.value}>
                      {item.label}
                    </option>
                  ))}
                </select>
                {options.data.truncated ? (
                  <p className="text-xs text-muted-foreground">Only the first options are listed; type the value above if yours is missing.</p>
                ) : null}
              </div>
            ) : null}
            {options !== null && !options.ok ? <Problem problem={options} /> : null}
          </div>
        ) : null}
      </div>
    </div>
  );
}
