import { useEffect, useRef, useState } from 'react';
import { Check, Copy, Loader2 } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { COPY } from './copy.js';

/** Moves focus to an element when it mounts, so a step change is announced and keyboard users land on it. */
export function useFocusOnMount<T extends HTMLElement>() {
  const ref = useRef<T>(null);
  useEffect(() => {
    ref.current?.focus();
  }, []);
  return ref;
}

/** A polite, announced "working" line. */
export function Busy({ text }: { text: string }) {
  return (
    <p role="status" className="flex items-center gap-2 py-2 text-sm text-muted-foreground">
      <Loader2 className="size-4 animate-spin" aria-hidden="true" />
      {text}
    </p>
  );
}

/**
 * A command in a read-only box with a button that copies it. The text stays selectable, so
 * when the clipboard is refused the person can still copy it by hand.
 */
export function CommandBox({ text, label = COPY.machine.copy }: { text: string; label?: string }) {
  const [state, setState] = useState<'idle' | 'copied' | 'failed'>('idle');

  async function copy() {
    try {
      await navigator.clipboard.writeText(text);
      setState('copied');
    } catch {
      setState('failed');
    }
  }

  return (
    <div className="flex flex-col gap-2">
      <pre
        tabIndex={0}
        aria-label="Command"
        className="overflow-x-auto rounded-md border bg-muted px-3 py-2 font-mono text-xs break-all whitespace-pre-wrap"
      >
        {text}
      </pre>
      <div className="flex items-center gap-3">
        <Button type="button" variant="outline" size="sm" onClick={() => void copy()}>
          {state === 'copied' ? <Check aria-hidden="true" /> : <Copy aria-hidden="true" />}
          {label}
        </Button>
        <span role="status" className="text-xs text-muted-foreground">
          {state === 'copied' ? COPY.copyDone : state === 'failed' ? COPY.copyFailed : ''}
        </span>
      </div>
    </div>
  );
}
