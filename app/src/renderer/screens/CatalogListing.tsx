import { useId, useMemo, useState } from 'react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Empty, Loading, Problem } from '../Problem.js';
import { useOperation } from '../useOperation.js';
import type { CatalogEntry, CatalogKind } from '../../shared/api.js';

/** The select's "no category filter" value — not a category name the CLI can emit. */
const ALL_CATEGORIES = '';
/** Heading for skills whose payload carries no category; always sorted last. */
const UNCATEGORIZED = 'uncategorized';

/** Fixed locale, so the order is the same on every machine and in CI. */
const collator = new Intl.Collator('en');

const byName = (a: CatalogEntry, b: CatalogEntry) => collator.compare(a.name, b.name);

/** `||`, not `??`: an empty category would otherwise collide with `ALL_CATEGORIES`. */
function categoryOf(entry: CatalogEntry): string {
  return entry.category || UNCATEGORIZED;
}

function compareCategories(a: string, b: string): number {
  if (a === UNCATEGORIZED) return b === UNCATEGORIZED ? 0 : 1;
  if (b === UNCATEGORIZED) return -1;
  return collator.compare(a, b);
}

/**
 * One kind's listing. Every kind is sorted by name; skills are additionally grouped by
 * category (categories sorted, `uncategorized` last) and get a category filter.
 * Sorting, grouping and both filters are client-side over the listing already fetched.
 */
export function Listing({ kind }: { kind: CatalogKind }) {
  const [filter, setFilter] = useState('');
  const [category, setCategory] = useState(ALL_CATEGORIES);
  // Component state only: the app has no per-viewer persistence pattern for view toggles.
  const [showAllCommands, setShowAllCommands] = useState(false);
  const { state } = useOperation(() => window.devteam.catalogListing(kind), [kind]);

  const all = useMemo(() => {
    if (state.phase !== 'done' || !state.result.ok) return [];
    return [...state.result.data.entries].sort(byName);
  }, [state]);

  // ADR-0030 section 5: commands show the featured five by default. A store that marks none
  // as featured (an older version) shows every command rather than an empty list.
  const featured = useMemo(() => all.filter((entry) => entry.featured === true), [all]);
  const visible = kind === 'commands' && featured.length > 0 && !showAllCommands ? featured : all;

  const categories = useMemo(() => [...new Set(all.map(categoryOf))].sort(compareCategories), [all]);
  // A selection the current listing no longer has (e.g. after a reload) falls back to all,
  // rather than leaving an empty result with no matching option to undo it.
  const activeCategory = categories.includes(category) ? category : ALL_CATEGORIES;

  const entries = useMemo(() => {
    const needle = filter.trim().toLowerCase();
    return visible.filter(
      (entry) =>
        (activeCategory === ALL_CATEGORIES || categoryOf(entry) === activeCategory) &&
        (needle === '' ||
          entry.name.toLowerCase().includes(needle) ||
          (entry.description ?? '').toLowerCase().includes(needle)),
    );
  }, [visible, filter, activeCategory]);

  if (state.phase === 'loading') return <Loading what={`devteam catalog ${kind}`} />;
  if (!state.result.ok) return <Problem problem={state.result} />;

  const groupsByCategory = kind === 'skills';
  const narrowed = filter.trim() !== '' || activeCategory !== ALL_CATEGORIES;

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-2">
        <Input
          type="search"
          value={filter}
          onChange={(event) => setFilter(event.target.value)}
          placeholder={`Filter ${kind}…`}
          aria-label={`Filter ${kind}`}
          className="max-w-sm"
        />
        {kind === 'commands' && featured.length > 0 ? (
          <Button type="button" variant="outline" aria-pressed={showAllCommands} onClick={() => setShowAllCommands((on) => !on)}>
            {showAllCommands ? `Show featured commands (${featured.length})` : `Show all commands (${all.length})`}
          </Button>
        ) : null}
        {groupsByCategory ? (
          <select
            value={activeCategory}
            onChange={(event) => setCategory(event.target.value)}
            aria-label="Filter skills by category"
            className="h-9 rounded-md border border-input bg-transparent px-3 text-sm shadow-xs outline-none focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50 dark:bg-input/30"
          >
            <option value={ALL_CATEGORIES}>All categories</option>
            {categories.map((each) => (
              <option key={each} value={each}>
                {each}
              </option>
            ))}
          </select>
        ) : null}
      </div>
      {entries.length === 0 ? (
        <Empty>{all.length === 0 || !narrowed ? `No ${kind} in the bound version.` : `No ${kind} match the filters.`}</Empty>
      ) : groupsByCategory ? (
        <GroupedByCategory entries={entries} />
      ) : (
        <EntryTable kind={kind} entries={entries} />
      )}
    </div>
  );
}

function GroupedByCategory({ entries }: { entries: readonly CatalogEntry[] }) {
  // The heading id comes from useId, never from the category name, which may hold
  // characters an id cannot.
  const idPrefix = useId();
  const groups = useMemo(() => {
    const byCategory = new Map<string, CatalogEntry[]>();
    for (const entry of entries) {
      const key = categoryOf(entry);
      byCategory.set(key, [...(byCategory.get(key) ?? []), entry]);
    }
    return [...byCategory.entries()].sort(([a], [b]) => compareCategories(a, b));
  }, [entries]);

  return (
    <div className="space-y-6">
      {groups.map(([each, members], index) => (
        <section key={each} aria-labelledby={`${idPrefix}-${index}`} className="space-y-2">
          <h3 id={`${idPrefix}-${index}`} className="text-sm font-semibold">
            {each} <span className="font-normal text-muted-foreground">({members.length})</span>
          </h3>
          <EntryTable kind="skills" entries={members} />
        </section>
      ))}
    </div>
  );
}

function EntryTable({ kind, entries }: { kind: CatalogKind; entries: readonly CatalogEntry[] }) {
  const showsTier = kind === 'agents';

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead scope="col">Name</TableHead>
          {showsTier ? <TableHead scope="col">Tier</TableHead> : null}
          {showsTier ? <TableHead scope="col">Model</TableHead> : null}
          <TableHead scope="col">Description</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {entries.map((entry) => (
          <TableRow key={entry.name}>
            <TableCell>
              {/* Plain text for now — the markdown view behind a click was removed until it
                  renders the body properly. Kept in the brand colour it had as a link. */}
              <span className="font-mono text-xs text-primary">{entry.name}</span>
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
  );
}
