import { Undo2 } from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { cn } from '@/lib/utils';
import type { PluginConfigField, ProjectId } from '../../shared/api.js';
import { isEditable } from '../../shared/pluginRules.js';
import { SELECT_CLASS } from '../formStyles.js';
import type { FieldDraftState } from './drafts.js';
import { ListEditor } from './ListEditor.js';
import { PathPicker } from './PathPicker.js';

/**
 * One row of a plugin's config form, built only from the `PluginConfigField` the CLI
 * described. There is no branch on a plugin or a key: the control follows the field's type.
 */
export function ConfigField({
  idPrefix,
  projectId,
  field,
  state,
  disabled,
  onDraft,
  onUndo,
}: {
  idPrefix: string;
  projectId?: ProjectId | undefined;
  field: PluginConfigField;
  state: FieldDraftState;
  disabled: boolean;
  onDraft: (value: unknown) => void;
  onUndo: () => void;
}) {
  const id = `${idPrefix}-${field.key}`;
  const helpId = `${id}-help`;
  const errorId = `${id}-error`;
  const invalid = state.error !== null;
  const describedBy = [field.help !== null ? helpId : null, invalid ? errorId : null].filter(Boolean).join(' ') || undefined;
  const shown = state.display;

  return (
    <div className="grid gap-3 py-4 md:grid-cols-[minmax(0,1fr)_minmax(0,22rem)] md:gap-6" data-changed={state.changed || undefined}>
      <div className="min-w-0 space-y-1">
        <div className="flex flex-wrap items-center gap-2">
          {state.changed ? <span className="size-1.5 rounded-full bg-primary" aria-hidden="true" title="Changed" /> : null}
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
        {state.changed ? (
          <Button variant="link" size="sm" className="h-auto p-0 text-xs" disabled={disabled} onClick={onUndo}>
            <Undo2 aria-hidden="true" />
            Undo<span className="sr-only"> {field.label}</span>
          </Button>
        ) : null}
      </div>

      <div className="min-w-0 space-y-1.5">
        <Control
          id={id}
          projectId={projectId}
          field={field}
          shown={shown}
          disabled={disabled}
          invalid={invalid}
          describedBy={describedBy}
          onDraft={onDraft}
        />
        {invalid ? (
          <p id={errorId} className="text-xs text-destructive">
            {state.error}
          </p>
        ) : null}
      </div>
    </div>
  );
}

function Control({
  id,
  projectId,
  field,
  shown,
  disabled,
  invalid,
  describedBy,
  onDraft,
}: {
  id: string;
  projectId: ProjectId | undefined;
  field: PluginConfigField;
  shown: unknown;
  disabled: boolean;
  invalid: boolean;
  describedBy: string | undefined;
  onDraft: (value: unknown) => void;
}) {
  if (!isEditable(field)) {
    return (
      <div className="space-y-1">
        <span id={id} className="font-mono text-sm">
          {JSON.stringify(shown)}
        </span>
        <p className="text-xs text-muted-foreground">
          This app cannot edit a {field.type} setting. Use <code className="font-mono">devteam plugin config set</code>.
        </p>
      </div>
    );
  }

  if (field.type === 'boolean') {
    return (
      <div className="flex h-9 items-center gap-3">
        <Switch
          id={id}
          checked={shown === true}
          disabled={disabled}
          aria-describedby={describedBy}
          onCheckedChange={(next) => onDraft(next)}
        />
        <span className="text-sm text-muted-foreground" aria-hidden="true">
          {shown === true ? 'On' : 'Off'}
        </span>
      </div>
    );
  }

  if (field.type === 'string_list') {
    return (
      <ListEditor
        id={id}
        label={field.label}
        value={Array.isArray(shown) ? (shown as string[]) : []}
        placeholder={field.placeholder ?? undefined}
        disabled={disabled}
        invalid={invalid}
        describedBy={describedBy}
        picker={field.picker}
        projectId={projectId}
        onChange={(next) => onDraft(next)}
      />
    );
  }

  if (field.type === 'enum') {
    const value = typeof shown === 'string' ? shown : '';
    const listed = field.options.some((option) => option.value === value);
    return (
      <select
        id={id}
        value={value}
        disabled={disabled}
        aria-invalid={invalid || undefined}
        aria-describedby={describedBy}
        className={SELECT_CLASS}
        onChange={(event) => onDraft(event.target.value)}
      >
        {!listed ? <option value="">Select…</option> : null}
        {field.options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    );
  }

  if (field.type === 'integer') {
    const text = typeof shown === 'string' ? shown : typeof shown === 'number' ? String(shown) : '';
    const bounds =
      field.min !== null && field.max !== null
        ? `Between ${field.min} and ${field.max}.`
        : field.min !== null
          ? `At least ${field.min}.`
          : field.max !== null
            ? `At most ${field.max}.`
            : null;
    return (
      <div className="space-y-1">
        <Input
          id={id}
          inputMode="numeric"
          autoComplete="off"
          value={text}
          disabled={disabled}
          placeholder={field.placeholder ?? undefined}
          aria-invalid={invalid || undefined}
          aria-describedby={describedBy}
          className={cn('tabular-nums')}
          onChange={(event) => onDraft(event.target.value)}
        />
        {bounds !== null ? <p className="text-xs text-muted-foreground">{bounds}</p> : null}
      </div>
    );
  }

  if (field.picker !== null && projectId !== undefined) {
    return (
      <PathPicker
        id={id}
        label={field.label}
        picker={field.picker}
        projectId={projectId}
        value={typeof shown === 'string' ? shown : ''}
        placeholder={field.placeholder ?? undefined}
        disabled={disabled}
        describedBy={describedBy}
        invalid={invalid}
        onPick={(path) => onDraft(path)}
      />
    );
  }

  return (
    <Input
      id={id}
      value={typeof shown === 'string' ? shown : ''}
      disabled={disabled}
      placeholder={field.placeholder ?? undefined}
      spellCheck={false}
      autoComplete="off"
      aria-invalid={invalid || undefined}
      aria-describedby={describedBy}
      className="font-mono"
      onChange={(event) => onDraft(event.target.value)}
    />
  );
}
