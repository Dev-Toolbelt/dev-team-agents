import { KeyRound } from 'lucide-react';
import { useEffect, useRef } from 'react';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import type { SecretDraft } from './drafts.js';

/**
 * A write-only secret field. The stored value is never read back, so it is never pre-filled:
 * the field says whether one is set, and typing is only offered after Replace (or Set). Remove
 * empties the value in the file and keeps the key, so the file keeps its shape.
 */
export function SecretInput({
  id,
  label,
  isSet,
  draft,
  disabled,
  onChange,
}: {
  id: string;
  label: string;
  isSet: boolean;
  draft: SecretDraft | undefined;
  disabled: boolean;
  onChange: (draft: SecretDraft | undefined) => void;
}) {
  const statusId = `${id}-status`;
  // Replacing the control a click came from would drop focus to the page; this puts it back.
  const inputRef = useRef<HTMLInputElement>(null);
  const startRef = useRef<HTMLButtonElement>(null);
  const undoRef = useRef<HTMLButtonElement>(null);
  const focusNext = useRef<'input' | 'start' | 'undo' | null>(null);
  const kind = draft?.kind;
  useEffect(() => {
    const target = focusNext.current;
    focusNext.current = null;
    if (target === 'input') inputRef.current?.focus();
    else if (target === 'start') startRef.current?.focus();
    else if (target === 'undo') undoRef.current?.focus();
  }, [kind]);
  const change = (next: SecretDraft | undefined, focus: 'input' | 'start' | 'undo'): void => {
    focusNext.current = focus;
    onChange(next);
  };
  return (
    <div className="min-w-0 space-y-1.5">
      <Label htmlFor={draft?.kind === 'replace' ? id : undefined} id={`${id}-label`} className="text-sm">
        {label}
      </Label>
      {draft?.kind === 'replace' ? (
        <div className="flex flex-wrap gap-2">
          <Input
            id={id}
            ref={inputRef}
            type="password"
            value={draft.value}
            disabled={disabled}
            autoComplete="new-password"
            spellCheck={false}
            placeholder={isSet ? 'Enter the new value' : 'Enter a value'}
            aria-describedby={statusId}
            className="min-w-0 flex-1 font-mono"
            onChange={(event) => onChange({ kind: 'replace', value: event.target.value })}
          />
          <Button type="button" variant="outline" size="sm" disabled={disabled} onClick={() => change(undefined, 'start')}>
            Cancel<span className="sr-only"> changing {label}</span>
          </Button>
        </div>
      ) : draft?.kind === 'remove' ? (
        <div className="flex flex-wrap items-center gap-2">
          <span id={statusId} className="text-sm text-muted-foreground">
            Will be removed when you save
          </span>
          <Button ref={undoRef} type="button" variant="outline" size="sm" disabled={disabled} onClick={() => change(undefined, 'start')}>
            Undo<span className="sr-only"> removing {label}</span>
          </Button>
        </div>
      ) : (
        <div role="group" aria-labelledby={`${id}-label`} className="flex flex-wrap items-center gap-2">
          <span id={statusId} className="flex items-center gap-1.5 text-sm">
            <KeyRound className="size-4 text-muted-foreground" aria-hidden="true" />
            {isSet ? 'Set' : 'Not set'}
          </span>
          <Button
            ref={startRef}
            type="button"
            variant="outline"
            size="sm"
            disabled={disabled}
            onClick={() => change({ kind: 'replace', value: '' }, 'input')}
          >
            {isSet ? 'Replace' : 'Set'}
            <span className="sr-only"> {label}</span>
          </Button>
          {isSet ? (
            <Button type="button" variant="outline" size="sm" disabled={disabled} onClick={() => change({ kind: 'remove' }, 'undo')}>
              Remove<span className="sr-only"> {label}</span>
            </Button>
          ) : null}
        </div>
      )}
      {draft?.kind === 'replace' ? (
        <p id={statusId} className="text-xs text-muted-foreground">
          Write-only: stored in the file, never shown again.
        </p>
      ) : null}
    </div>
  );
}
