import { ArrowLeft } from 'lucide-react';

import { Button } from '@/components/ui/button';

/**
 * The way back from a detail screen to the list it was opened from. One component, so every
 * drill-down reads the same: an arrow and the destination's name above the heading.
 *
 * The visible text is the destination alone; the accessible name says it is a way back, which
 * the arrow says to a sighted user and nothing says to a screen reader.
 */
export function BackNav({ to, onBack }: { to: string; onBack: () => void }) {
  return (
    <nav aria-label="Back">
      <Button variant="ghost" size="sm" className="-ml-2 text-muted-foreground" aria-label={`Back to ${to}`} onClick={onBack}>
        <ArrowLeft aria-hidden="true" />
        {to}
      </Button>
    </nav>
  );
}
