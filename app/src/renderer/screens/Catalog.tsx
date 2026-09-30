import { useState } from 'react';

import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useOperation, type Load } from '../useOperation.js';
import { Listing } from './CatalogListing.js';
import type { CatalogKind, CatalogSummary } from '../../shared/api.js';

const KINDS: readonly CatalogKind[] = ['agents', 'skills', 'commands'];

/**
 * `devteam catalog` and its three listings, plus `catalog show` for one entry.
 *
 * The kind is chosen from a fixed set of three; the renderer never composes a command.
 * Filtering, sorting and grouping are client-side (see `CatalogListing.tsx`) — re-invoking
 * the CLI per keystroke would be a process spawn per character.
 */
export function Catalog() {
  const [kind, setKind] = useState<CatalogKind>('agents');

  const summary = useOperation(() => window.devteam.catalogSummary());

  return (
    <section aria-labelledby="catalog-heading" className="space-y-4">
      <header className="flex items-baseline justify-between gap-4">
        <div>
          <h2 id="catalog-heading" className="text-base font-semibold">
            Catalog
          </h2>
          <CatalogSummaryLine state={summary.state} />
        </div>
        <Button variant="outline" size="sm" onClick={summary.reload}>
          Refresh
        </Button>
      </header>

      <Tabs
        value={kind}
        onValueChange={(next) => {
          // Narrowed rather than cast: Radix hands back a string, and the bridge accepts
          // only these three. A value from outside the set is ignored.
          if (KINDS.includes(next as CatalogKind)) {
            setKind(next as CatalogKind);
          }
        }}
      >
        <TabsList>
          {KINDS.map((each) => (
            <TabsTrigger key={each} value={each}>
              {each}
            </TabsTrigger>
          ))}
        </TabsList>
        {KINDS.map((each) => (
          <TabsContent key={each} value={each} className="pt-4">
            {each === kind ? <Listing kind={each} /> : null}
          </TabsContent>
        ))}
      </Tabs>
    </section>
  );
}

const SUMMARY_KINDS: readonly CatalogKind[] = KINDS;

/**
 * What `devteam catalog` actually returned.
 *
 * It used to return `null` on success: the command was spawned, `operations.ts` validated
 * `version`, `project_id`, `counts` and `malformed`, and none of it reached a screen. The
 * **malformed** counts are the one thing `CLAUDE-md/cli.md` says this surface exists to
 * expose, so a user with a broken skill saw a normal-looking catalog. `project_id` is also
 * the app's answer to "which project did you resolve?", which is why it is named here
 * rather than left implicit.
 */
function CatalogSummaryLine({ state }: { state: Load<CatalogSummary> }) {
  if (state.phase === 'loading') return <p className="text-sm text-muted-foreground">Reading the catalog…</p>;
  if (!state.result.ok) {
    return <p className="text-sm text-destructive">{state.result.message}</p>;
  }
  const { version, project_id, counts, malformed } = state.result.data;
  const broken = SUMMARY_KINDS.filter((kind) => malformed[kind] > 0);

  return (
    <div className="space-y-1">
      <p className="text-sm text-muted-foreground">
        Version <span className="font-mono">{version ?? 'unknown'}</span> ·{' '}
        {SUMMARY_KINDS.map((kind) => `${counts[kind]} ${kind}`).join(' · ')}
      </p>
      <p className="text-xs text-muted-foreground">
        {/* A project is named, never shown by its UUID — the id means nothing on screen. */}
        {project_id !== null ? (
          'Resolved against a bound project.'
        ) : (
          'No project resolved — this build has no project picker, so the catalog is the bound version’s own.'
        )}
      </p>
      {broken.length > 0 ? (
        <p className="text-sm text-destructive">
          {broken.map((kind) => `${malformed[kind]} ${kind}`).join(' · ')} could not be read. They are listed below,
          marked <span className="font-semibold">malformed</span>, with the error from the CLI.
        </p>
      ) : null}
    </div>
  );
}
