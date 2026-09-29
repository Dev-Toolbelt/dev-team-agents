import { useCallback, useEffect, useState } from 'react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { selfCheck } from '../../cli/selfCheck.js';
import type { AppFinding, DoctorReport } from '../../shared/api.js';
import { Empty, Loading, Problem } from '../Problem.js';
import { useOperation, type Load } from '../useOperation.js';

/**
 * `devteam doctor --json`, above a self-check of the app itself.
 *
 * This screen is the reason exit 1 has its own outcome. `doctor` exits **1** whenever it
 * finds anything — which is most of the time, and is the case this screen exists to show.
 * A layer that treated exit 1 as failure would render an error here and no report, on the
 * single command whose findings are the product.
 *
 * `doctor` is the one command this app runs that `compat.MUTATING` lists — it repairs what
 * it finds. The app declares its schemas on every invocation, so when the store is ahead of
 * the app the framework's gate refuses this call with exit 4 and the screen says so rather
 * than running a repair the app does not understand. `--reassign-identity` is never passed.
 * Any repair `doctor` reports below was a write, and the screen labels it as one.
 *
 * `devteam doctor` diagnoses the store, the machine, the registry and a project — never the
 * app (ADR-0015). "This app" above is a different subject from "The store" below it, and the
 * two headings exist so a `fail` in one table is never read as a verdict on the other.
 */
function levelVariant(level: string): 'default' | 'secondary' | 'destructive' | 'outline' {
  switch (level) {
    case 'fail':
    case 'error':
      return 'destructive';
    case 'warn':
      return 'outline';
    case 'ok':
      return 'secondary';
    default:
      return 'default';
  }
}

type Loaded<T> = { readonly phase: 'loading' } | { readonly phase: 'done'; readonly value: T };

/**
 * `buildInfo`, `environment` and `resolveCli` are bare-value bridge calls — there is no
 * `OperationResult` union for `useOperation` to unwrap, because none of the three run the
 * CLI (see each field's own doc comment in `shared/api.ts`). This is `useOperation`'s
 * load-on-mount shape without the result branch it does not need; `deps` mirrors
 * `useOperation`'s own seam for the same reason — a fresh closure on every render cannot
 * be the identity the effect keys on.
 */
function useLoaded<T>(loader: () => Promise<T>, deps: readonly unknown[] = []): Loaded<T> {
  const [state, setState] = useState<Loaded<T>>({ phase: 'loading' });
  const run = useCallback(loader, deps);

  useEffect(() => {
    let live = true;
    void run().then((value) => {
      if (live) setState({ phase: 'done', value });
    });
    return () => {
      live = false;
    };
  }, [run]);

  return state;
}

/** The app-health table, shared shape with `DoctorFinding`'s rendering below it. */
function AppHealthTable({ status, findings }: { readonly status: string; readonly findings: readonly AppFinding[] }) {
  return (
    <>
      <p className="text-sm text-muted-foreground">
        Status <Badge variant={levelVariant(status)}>{status}</Badge>
      </p>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead scope="col">Level</TableHead>
            <TableHead scope="col">Category</TableHead>
            <TableHead scope="col">Finding</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {findings.map((finding, index) => (
            <TableRow key={`${finding.category}-${index}`}>
              <TableCell>
                <Badge variant={levelVariant(finding.level)}>{finding.level}</Badge>
              </TableCell>
              <TableCell className="font-mono text-xs">{finding.category}</TableCell>
              <TableCell>
                {finding.message}
                {finding.hint !== undefined ? (
                  <span className="block text-xs text-muted-foreground">{finding.hint}</span>
                ) : null}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </>
  );
}

export function Doctor() {
  const buildInfoLoad = useLoaded(() => window.devteam.buildInfo());
  const environmentLoad = useLoaded(() => window.devteam.environment());
  const resolutionLoad = useLoaded(() => window.devteam.resolveCli());
  const handshakeOp = useOperation(() => window.devteam.handshake());

  const { state, reload } = useOperation(() => window.devteam.doctor());

  return (
    <div className="space-y-8">
      <section aria-labelledby="app-health-heading" className="space-y-4">
        <header>
          <h2 id="app-health-heading" className="text-base font-semibold">
            This app
          </h2>
          <p className="text-xs text-muted-foreground">
            Derived from what the bridge already returns — no extra call to the CLI. Whether this build can run at
            all against the store below.
          </p>
        </header>

        {buildInfoLoad.phase === 'loading' ||
        environmentLoad.phase === 'loading' ||
        resolutionLoad.phase === 'loading' ||
        handshakeOp.state.phase === 'loading' ? (
          <Loading what="this app's own preconditions" />
        ) : (
          <AppHealthTable
            {...selfCheck({
              build: buildInfoLoad.value,
              environment: environmentLoad.value,
              resolution: resolutionLoad.value,
              handshake: handshakeOp.state.result,
            })}
          />
        )}
      </section>

      <StoreReport state={state} reload={reload} />
    </div>
  );
}

function StoreReport({ state, reload }: { readonly state: Load<DoctorReport>; readonly reload: () => void }) {
  if (state.phase === 'loading') return <Loading what="devteam doctor" />;
  if (!state.result.ok) return <Problem problem={state.result} />;

  const report = state.result.data;
  const ranWithFindings = state.result.outcome === 'findings';

  return (
    <section aria-labelledby="doctor-heading" className="space-y-4">
      <header className="flex items-baseline justify-between gap-4">
        <div>
          <h2 id="doctor-heading" className="text-base font-semibold">
            The store
          </h2>
          <p className="text-sm text-muted-foreground">
            Status <Badge variant={levelVariant(report.status)}>{report.status}</Badge>
            {ranWithFindings
              ? ' — the command ran and reported findings (exit 1). That is a result, not a failure.'
              : ' — nothing to report.'}
          </p>
          {/* Stated, not implied: the app passes `--no-project`, so this report is about the
              store and not about any project. Without it the project findings changed with
              the directory the app happened to be launched from. */}
          <p className="text-xs text-muted-foreground">
            Run as <code className="font-mono">devteam doctor --no-project</code> — the store only. This build has no
            project picker, so no project is diagnosed.
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={reload}>
          Re-run
        </Button>
      </header>

      {report.findings.length === 0 ? (
        <Empty>No findings.</Empty>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead scope="col">Level</TableHead>
              <TableHead scope="col">Category</TableHead>
              <TableHead scope="col">Finding</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {report.findings.map((finding, index) => (
              <TableRow key={`${finding.category}-${index}`}>
                <TableCell>
                  <Badge variant={levelVariant(finding.level)}>{finding.level}</Badge>
                </TableCell>
                <TableCell className="font-mono text-xs">{finding.category}</TableCell>
                <TableCell>
                  {finding.message}
                  {finding.hint !== undefined ? (
                    <span className="block text-xs text-muted-foreground">{finding.hint}</span>
                  ) : null}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}

      {report.actions.length > 0 ? (
        <div>
          <h3 className="text-sm font-semibold">Repairs performed — these were writes</h3>
          <p className="text-xs text-muted-foreground">
            <code className="font-mono">devteam doctor</code> is the one command this app runs that the framework
            classifies as mutating; it repairs what it finds rather than only reporting it.
          </p>
          <ul className="list-inside list-disc text-sm text-muted-foreground">
            {report.actions.map((action, index) => (
              <li key={index}>{action}</li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  );
}
