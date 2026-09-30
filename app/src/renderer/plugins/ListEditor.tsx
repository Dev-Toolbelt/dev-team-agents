import { useId, useRef, useState } from 'react';
import { Plus, X } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { listItemProblem } from '../../shared/pluginRules.js';

/**
 * Add `raw` to `list`, or say why not. Pure so the rules are tested without a DOM: an entry
 * is trimmed first (a pasted path often carries a trailing space), then refused when empty,
 * malformed or already listed.
 */
export function addListItem(
  list: readonly string[],
  raw: string,
): { readonly ok: true; readonly list: readonly string[] } | { readonly ok: false; readonly error: string } {
  const item = raw.trim();
  const problem = listItemProblem(item);
  if (problem !== null) return { ok: false, error: problem };
  if (list.includes(item)) return { ok: false, error: `"${item}" is already in the list.` };
  return { ok: true, list: [...list, item] };
}

/**
 * An editable list of strings: one row per entry with a remove button, and an input with an
 * Add button underneath. Enter in the input adds, so the whole thing works from the
 * keyboard; after a removal focus returns to the input, so it is never stranded on a row
 * that no longer exists.
 */
export function ListEditor({
  id,
  label,
  value,
  onChange,
  placeholder,
  disabled = false,
  describedBy,
  invalid = false,
}: {
  id: string;
  /** The field's label, used to name the list and the buttons for assistive technology. */
  label: string;
  value: readonly string[];
  onChange: (next: readonly string[]) => void;
  placeholder?: string | undefined;
  disabled?: boolean;
  describedBy?: string | undefined;
  invalid?: boolean;
}) {
  const [text, setText] = useState('');
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const errorId = useId();

  function add() {
    const result = addListItem(value, text);
    if (!result.ok) {
      setError(result.error);
      return;
    }
    setError(null);
    setText('');
    onChange(result.list);
    inputRef.current?.focus();
  }

  return (
    <div className="space-y-2">
      {value.length > 0 ? (
        <ul aria-label={label} className="divide-y rounded-md border">
          {value.map((item) => (
            <li key={item} className="flex items-center justify-between gap-2 px-3 py-1.5">
              <span className="min-w-0 truncate font-mono text-sm" title={item}>
                {item}
              </span>
              <Button
                type="button"
                variant="ghost"
                size="icon-sm"
                disabled={disabled}
                aria-label={`Remove ${item} from ${label}`}
                onClick={() => {
                  onChange(value.filter((entry) => entry !== item));
                  inputRef.current?.focus();
                }}
              >
                <X aria-hidden="true" />
              </Button>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-xs italic text-muted-foreground">Nothing listed yet.</p>
      )}
      <div className="flex gap-2">
        <Input
          ref={inputRef}
          id={id}
          value={text}
          disabled={disabled}
          placeholder={placeholder}
          spellCheck={false}
          autoComplete="off"
          aria-invalid={invalid || error !== null || undefined}
          aria-describedby={[describedBy, error !== null ? errorId : null].filter(Boolean).join(' ') || undefined}
          className="font-mono"
          onChange={(event) => {
            setText(event.target.value);
            if (error !== null) setError(null);
          }}
          onKeyDown={(event) => {
            if (event.key === 'Enter') {
              // Not a form submit: the card has no <form>, and Enter here means "add this entry".
              event.preventDefault();
              add();
            }
          }}
        />
        <Button type="button" variant="outline" disabled={disabled} onClick={add}>
          <Plus aria-hidden="true" />
          Add<span className="sr-only"> to {label}</span>
        </Button>
      </div>
      {error !== null ? (
        <p id={errorId} role="alert" className="text-xs text-destructive">
          {error}
        </p>
      ) : null}
    </div>
  );
}
