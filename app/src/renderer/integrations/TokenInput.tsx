import { KeyRound } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import type { IntegrationView } from '../../shared/api.js';

/**
 * The write-only secret field. It is never pre-filled: a stored token is shown as a fact
 * ("Stored in <backend>") with Replace and Remove, and typing is only offered when there is
 * nothing stored or the person chose Replace. The value lives in the caller's state only
 * until a submit, which clears it.
 */
export function TokenInput({
  id,
  auth,
  value,
  replacing,
  disabled,
  onChange,
  onReplace,
  onCancelReplace,
  onRemove,
  removeDisabledReason,
}: {
  id: string;
  auth: IntegrationView['auth'];
  value: string;
  replacing: boolean;
  disabled: boolean;
  onChange: (value: string) => void;
  onReplace: () => void;
  onCancelReplace: () => void;
  onRemove: () => void;
  removeDisabledReason: string | null;
}) {
  const showInput = !auth.has_token || auth.stale || replacing;
  const helpId = `${id}-help`;
  return (
    <div className="grid gap-3 py-4 md:grid-cols-[minmax(0,1fr)_minmax(0,22rem)] md:gap-6">
      <div className="min-w-0 space-y-1">
        <Label htmlFor={showInput ? id : undefined} className="text-sm font-medium">
          {auth.label}
        </Label>
        {auth.help !== null ? (
          <p id={helpId} className="text-xs text-muted-foreground">
            {auth.help}
          </p>
        ) : null}
      </div>
      <div className="min-w-0 space-y-2">
        {showInput ? (
          <>
            <Input
              id={id}
              type="password"
              value={value}
              disabled={disabled}
              autoComplete="off"
              spellCheck={false}
              placeholder={auth.has_token ? 'Paste the new token' : 'Paste a token'}
              aria-describedby={auth.help !== null ? helpId : undefined}
              className="font-mono"
              onChange={(event) => onChange(event.target.value)}
            />
            <p className="text-xs text-muted-foreground">Write-only: stored in the OS keychain, never shown again.</p>
            {auth.has_token && !auth.stale ? (
              <Button variant="link" size="sm" className="h-auto p-0 text-xs" disabled={disabled} onClick={onCancelReplace}>
                Keep the stored token
              </Button>
            ) : null}
          </>
        ) : (
          <div className="flex flex-wrap items-center gap-2">
            <span className="flex items-center gap-1.5 text-sm">
              <KeyRound className="size-4 text-muted-foreground" aria-hidden="true" />
              Stored in {auth.backend ?? 'the secret store'}
            </span>
            <Button variant="outline" size="sm" disabled={disabled} onClick={onReplace}>
              Replace<span className="sr-only"> token</span>
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={disabled || removeDisabledReason !== null}
              title={removeDisabledReason ?? undefined}
              onClick={onRemove}
            >
              Remove<span className="sr-only"> token</span>
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
