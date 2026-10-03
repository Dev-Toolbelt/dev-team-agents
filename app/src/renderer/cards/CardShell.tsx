import { ChevronRight } from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { Hint } from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';

export type Standing = {
  readonly label: string;
  readonly variant: 'default' | 'secondary' | 'destructive' | 'outline';
  readonly className?: string;
};

/**
 * The frame every settings card shares: a bordered section with a collapsible body, a header
 * of title, standing badge and description, and a chevron that locks open while the card has
 * unsaved edits or a running action. It knows nothing about what goes inside.
 */
export function CardShell({
  titleId,
  title,
  icon,
  description,
  standing,
  badges,
  headerEnd,
  notices,
  dataAttr,
  open,
  onOpenChange,
  lockedReason,
  children,
}: {
  titleId: string;
  title: string;
  /** A mark drawn in a tile before the title (an integration's logo). */
  icon?: React.ReactNode;
  description: string;
  standing: Standing;
  /** Extra badges beside the standing one. */
  badges?: React.ReactNode;
  /** Controls placed after the chevron (a plugin's enable switch). */
  headerEnd?: React.ReactNode;
  /** Always-visible content between the header and the collapsible body. */
  notices?: React.ReactNode;
  dataAttr: Readonly<Record<string, string>>;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Why the card cannot collapse right now, or null. */
  lockedReason: string | null;
  children: React.ReactNode;
}) {
  const expanded = open || lockedReason !== null;
  const trigger = (
    <CollapsibleTrigger asChild disabled={lockedReason !== null}>
      <Button
        variant="ghost"
        size="icon-sm"
        aria-label={`${expanded ? 'Hide' : 'Show'} ${title} details`}
        title={lockedReason ?? undefined}
      >
        <ChevronRight className={cn('transition-transform', expanded && 'rotate-90')} aria-hidden="true" />
      </Button>
    </CollapsibleTrigger>
  );

  return (
    <section aria-labelledby={titleId} className="rounded-xl border bg-card text-card-foreground shadow-sm" {...dataAttr}>
      <Collapsible open={expanded} onOpenChange={onOpenChange}>
        <header className="px-5 py-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="flex min-w-0 items-start gap-3">
              {icon !== undefined ? (
                <span className="flex size-10 shrink-0 items-center justify-center rounded-lg border bg-muted/40">{icon}</span>
              ) : null}
              <div className="min-w-0 space-y-1">
                <div className="flex flex-wrap items-center gap-2">
                  <h3 id={titleId} className="font-semibold">
                    {title}
                  </h3>
                  <Badge variant={standing.variant} className={cn('font-normal', standing.className)}>
                    {standing.label}
                  </Badge>
                  {badges}
                </div>
                <p className="text-sm text-muted-foreground">{description}</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              {lockedReason !== null ? (
                <Hint content={lockedReason}>
                  <span className="inline-flex">{trigger}</span>
                </Hint>
              ) : (
                trigger
              )}
              {headerEnd}
            </div>
          </div>
        </header>
        {notices}
        <CollapsibleContent forceMount hidden={!expanded} className="data-[state=closed]:hidden">
          {children}
        </CollapsibleContent>
      </Collapsible>
    </section>
  );
}
