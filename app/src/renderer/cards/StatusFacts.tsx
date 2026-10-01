import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';

type Tone = 'positive' | 'warning' | 'neutral';

const FACT_TONE_CLASS: Record<Tone, string> = {
  positive: 'border-green-600 bg-green-50 text-green-900 dark:border-green-500 dark:bg-green-950 dark:text-green-200',
  warning: 'border-amber-500/50 text-amber-700 dark:text-amber-400',
  neutral: '',
};

/** A status summary and its labelled facts; a fact with a tone is drawn as a badge. */
export function StatusFacts({
  summary,
  facts,
}: {
  summary: string;
  facts: readonly { readonly label: string; readonly value: string; readonly tone: Tone | null }[];
}) {
  return (
    <>
      <p className="text-sm text-muted-foreground">{summary}</p>
      {facts.length > 0 ? (
        <dl className="grid grid-cols-[max-content_minmax(0,1fr)] gap-x-4 gap-y-1 text-sm">
          {facts.map((fact) => (
            <div key={fact.label} className="contents">
              <dt className="text-muted-foreground">{fact.label}</dt>
              <dd className={cn('min-w-0 break-words text-xs leading-5', fact.tone === null && 'font-mono')}>
                {fact.tone !== null ? (
                  <Badge variant="outline" className={FACT_TONE_CLASS[fact.tone]}>
                    {fact.value}
                  </Badge>
                ) : (
                  fact.value
                )}
              </dd>
            </div>
          ))}
        </dl>
      ) : null}
    </>
  );
}
