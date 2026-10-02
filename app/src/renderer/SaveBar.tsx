import { Button } from '@/components/ui/button';
import { Hint } from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';

/**
 * The bar a form shows while it has unsaved edits: what is pending, Discard, and Save.
 *
 * By default it is fixed to the bottom edge of the window, so Save is always in the same place
 * whatever the length of the form: a sticky bar sat right under a short form, mid-window. A
 * spacer of the bar's height keeps the end of the form from hiding behind it. It stops short
 * of the right edge so the content's scrollbar stays reachable.
 *
 * `inline` drops that placement, for a form that lives inside a card (a plugin's config) and
 * must not pin itself to the window edge.
 */
export function SaveBar({
  dirtyCount,
  invalid,
  status,
  saving,
  canSave,
  withheld,
  onDiscard,
  onSave,
  inline = false,
  label = 'Unsaved changes',
  saveLabel = 'Save changes',
  shortcut = true,
}: {
  dirtyCount: number;
  invalid: number;
  /** The same sentence the screen's always-mounted live region announces. */
  status: string;
  saving: boolean;
  canSave: boolean;
  withheld: string | null;
  onDiscard: () => void;
  onSave: () => void;
  inline?: boolean;
  label?: string;
  saveLabel?: string;
  /** Whether to advertise ⌘S; only the screen that binds the shortcut should. */
  shortcut?: boolean;
}) {
  if (dirtyCount === 0 && !saving) return null;
  const saveButton = (
    <Button size="sm" disabled={!canSave} onClick={onSave}>
      {saving ? 'Saving…' : saveLabel}
      {!saving && shortcut ? (
        <kbd className="ml-1 rounded border border-current/30 px-1 font-sans text-[10px] opacity-70">⌘S</kbd>
      ) : null}
    </Button>
  );
  const bar = (
    <div
      role="region"
      aria-label={label}
      className={cn(
        'flex flex-wrap items-center justify-between gap-3 border-t bg-card/95 py-3',
        inline
          ? 'rounded-b-xl px-5'
          : 'fixed bottom-0 left-0 right-[10px] z-20 px-6 shadow-[0_-4px_12px_-8px_rgb(0_0_0/0.25)] backdrop-blur',
      )}
    >
      <p className={cn('text-sm', invalid > 0 ? 'text-destructive' : 'text-muted-foreground')}>
        {saving ? 'Saving…' : status}
      </p>
      <div className="flex items-center gap-2">
        <Button variant="outline" size="sm" disabled={saving} onClick={onDiscard}>
          Discard
        </Button>
        {withheld !== null ? (
          <Hint content={`Withheld: ${withheld}`}>
            <span className="inline-flex">{saveButton}</span>
          </Hint>
        ) : (
          saveButton
        )}
      </div>
    </div>
  );
  if (inline) return bar;
  return (
    <>
      <div aria-hidden="true" data-testid="save-bar-spacer" className="h-16" />
      {bar}
    </>
  );
}
