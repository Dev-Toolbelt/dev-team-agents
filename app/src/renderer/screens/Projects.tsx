import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Empty, Loading, Problem } from '../Problem.js';
import { useOperation } from '../useOperation.js';

/**
 * Three states, because the payload has three.
 *
 * `path_exists` is `null` when the CLI did not say, and that is **not** the same claim as
 * "the directory is gone". A red `missing` badge beside a path that exists is the shape
 * ADR-0015's own unmitigated risk names — "a bound project shown unbound leads the user to
 * a destructive action in the terminal" — so an unknown is labelled as one.
 */
function PathState({ exists }: { exists: boolean | null }) {
  if (exists === true) return null;
  if (exists === false) return <Badge variant="destructive">missing</Badge>;
  return (
    <Badge variant="outline" title="`devteam list --json` returned no boolean `path_exists` for this row">
      not checked
    </Badge>
  );
}

/**
 * `devteam list --json`. A real `<table>`, not a grid of divs: the data is tabular, the
 * browser gives row/column semantics to a screen reader for free, and there is no
 * interaction here that a kit component would buy anything for.
 */
export function Projects() {
  const { state, reload } = useOperation((): ReturnType<typeof window.devteam.listProjects> => window.devteam.listProjects());

  if (state.phase === 'loading') return <Loading what="devteam list" />;
  if (!state.result.ok) return <Problem problem={state.result} />;

  const { current, projects } = state.result.data;

  return (
    <section aria-labelledby="projects-heading" className="space-y-4">
      <header className="flex items-baseline justify-between gap-4">
        <div>
          <h2 id="projects-heading" className="text-base font-semibold">
            Bound projects
          </h2>
          <p className="text-sm text-muted-foreground">
            {projects.length === 0
              ? 'None yet.'
              : `${projects.length} project${projects.length === 1 ? '' : 's'} bound to this store.`}
            {current !== null ? ` Store version ${current} is current.` : ' No store version is current.'}
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={reload}>
          Refresh
        </Button>
      </header>

      {projects.length === 0 ? (
        <Empty>
          Nothing is bound. Run <code className="font-mono">devteam bind</code> in a project — this build is
          read-only and cannot bind one for you.
        </Empty>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead scope="col">Project</TableHead>
              <TableHead scope="col">Resolves to</TableHead>
              <TableHead scope="col">Mode</TableHead>
              <TableHead scope="col">Providers</TableHead>
              <TableHead scope="col">Path</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {projects.map((project) => (
              <TableRow key={project.project_id}>
                <TableCell className="font-mono text-xs">{project.project_id}</TableCell>
                <TableCell>
                  {project.resolves_to ?? '—'}
                  {project.pin !== null ? (
                    <Badge variant="secondary" className="ml-2">
                      pinned {project.pin}
                    </Badge>
                  ) : null}
                </TableCell>
                <TableCell>{project.mode ?? '—'}</TableCell>
                <TableCell>{project.providers.length === 0 ? '—' : project.providers.join(', ')}</TableCell>
                {/* The badge sits outside the truncating span, not inside it. A `truncate`
                    cell clipped it at the ellipsis, so the one row that most needed a
                    `missing` badge — a long path — was the one row that never showed it. */}
                <TableCell className="font-mono text-xs">
                  <span className="flex items-center gap-2">
                    <span className="max-w-[24rem] truncate" title={project.path}>
                      {project.path}
                    </span>
                    <PathState exists={project.path_exists} />
                  </span>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </section>
  );
}
