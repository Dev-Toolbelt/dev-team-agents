import { useMemo, useState } from 'react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Empty, Loading, Problem } from '../Problem.js';
import { useOperation, type Load } from '../useOperation.js';
import type { CatalogKind, CatalogSummary } from '../../shared/api.js';

const KINDS: readonly CatalogKind[] = ['agents', 'skills', 'commands'];

/**
 * `devteam catalog` and its three listings, plus `catalog show` for one entry.
 *
 * The kind is chosen from a fixed set of three; the renderer never composes a command.
 * The filter is client-side over the listing already fetched — filtering by re-invoking
 * the CLI per keystroke would be a process spawn per character.
 */
export function Catalog() {
  const [kind, setKind] = useState<CatalogKind>('agents');
  const [selected, setSelected] = useState<string | null>(null);

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
            setSelected(null);
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
            {each === kind ? <Listing kind={each} onSelect={setSelected} /> : null}
          </TabsContent>
        ))}
      </Tabs>

      {selected !== null ? <Detail name={selected} onClose={() => setSelected(null)} /> : null}
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
        {project_id !== null ? (
          <>
            Resolved against project <span className="font-mono">{project_id}</span>.
          </>
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

function Listing({ kind, onSelect }: { kind: CatalogKind; onSelect: (name: string) => void }) {
  const [filter, setFilter] = useState('');
  const { state } = useOperation(() => window.devteam.catalogListing(kind), [kind]);

  const entries = useMemo(() => {
    if (state.phase !== 'done' || !state.result.ok) return [];
    const needle = filter.trim().toLowerCase();
    if (needle === '') return state.result.data.entries;
    return state.result.data.entries.filter(
      (entry) =>
        entry.name.toLowerCase().includes(needle) || (entry.description ?? '').toLowerCase().includes(needle),
    );
  }, [state, filter]);

  if (state.phase === 'loading') return <Loading what={`devteam catalog ${kind}`} />;
  if (!state.result.ok) return <Problem problem={state.result} />;

  const showsTier = kind === 'agents';

  return (
    <div className="space-y-3">
      <Input
        type="search"
        value={filter}
        onChange={(event) => setFilter(event.target.value)}
        placeholder={`Filter ${kind}…`}
        aria-label={`Filter ${kind}`}
        className="max-w-sm"
      />
      {entries.length === 0 ? (
        <Empty>
          {state.result.data.entries.length === 0 ? `No ${kind} in the bound version.` : `No ${kind} match "${filter}".`}
        </Empty>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead scope="col">Name</TableHead>
              {showsTier ? <TableHead scope="col">Tier</TableHead> : null}
              {showsTier ? <TableHead scope="col">Model</TableHead> : null}
              {kind === 'skills' ? <TableHead scope="col">Category</TableHead> : null}
              <TableHead scope="col">Description</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {entries.map((entry) => (
              <TableRow key={entry.name}>
                <TableCell>
                  <Button variant="link" className="h-auto p-0 font-mono text-xs" onClick={() => onSelect(entry.name)}>
                    {entry.name}
                  </Button>
                  {entry.malformed === true ? (
                    <Badge variant="destructive" className="ml-2">
                      malformed
                    </Badge>
                  ) : null}
                </TableCell>
                {showsTier ? (
                  <TableCell>{entry.tier != null ? <Badge variant="outline">{entry.tier}</Badge> : '—'}</TableCell>
                ) : null}
                {showsTier ? <TableCell className="font-mono text-xs">{entry.model ?? '—'}</TableCell> : null}
                {kind === 'skills' ? <TableCell>{entry.category ?? '—'}</TableCell> : null}
                <TableCell className="text-muted-foreground">
                  {/* A malformed entry has no description — its `error` is the only thing
                      the payload can say about it, and the summary's count is unactionable
                      without it. The name shown is a fallback from the path. */}
                  {entry.malformed === true ? (
                    <span className="text-destructive">{entry.error ?? 'could not be read; the CLI gave no reason'}</span>
                  ) : (
                    (entry.description ?? '—')
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </div>
  );
}

function Detail({ name, onClose }: { name: string; onClose: () => void }) {
  const { state } = useOperation(() => window.devteam.catalogEntry(name), [name]);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="font-mono text-sm">{name}</CardTitle>
        {state.phase === 'done' && state.result.ok ? (
          <CardDescription>
            {state.result.data.kind}
            {state.result.data.path !== null ? ` · ${state.result.data.path}` : ''}
          </CardDescription>
        ) : null}
        <Button variant="ghost" size="sm" onClick={onClose} className="justify-self-end">
          Close
        </Button>
      </CardHeader>
      <CardContent>
        {state.phase === 'loading' ? (
          <Loading what="devteam catalog show" />
        ) : !state.result.ok ? (
          <Problem problem={state.result} />
        ) : (
          <pre className="max-h-96 overflow-auto rounded-md bg-muted p-3 font-mono text-xs whitespace-pre-wrap">
            {state.result.data.body === '' ? '(no body)' : state.result.data.body}
          </pre>
        )}
      </CardContent>
    </Card>
  );
}
