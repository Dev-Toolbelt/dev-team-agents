import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import type { BuildInfo, CliResolution, CliSource } from '../../shared/api.js';

const SOURCE_LABEL: Record<CliSource, string> = {
  configured: 'configured path',
  path: 'PATH',
  homebrew: 'Homebrew',
  winget: 'winget',
};

/**
 * The detail behind the header: which CLI, from where, and what this build can change.
 *
 * ADR-0011 makes the app a client of one CLI, and "which `devteam` is this?" is a question
 * the user cannot answer from the outside — so the answer stays one tab away, never hidden.
 * The header keeps only the store version, which is what the Projects screen compares
 * against; the path, source, contract and write actions live here, where there is room to
 * label them.
 */
export function About({
  build,
  resolution,
  onReResolve,
}: {
  build: BuildInfo | null;
  resolution: CliResolution | null;
  onReResolve: () => void;
}) {
  const cli = resolution !== null && resolution.found ? resolution.cli : null;

  return (
    <section aria-labelledby="about-heading" className="space-y-4">
      <h2 id="about-heading" className="text-base font-semibold">
        About
      </h2>

      <dl className="grid grid-cols-[max-content_1fr] items-baseline gap-x-6 gap-y-2 text-sm">
        <dt className="text-muted-foreground">devteam CLI</dt>
        <dd className="flex flex-wrap items-center gap-2">
          {cli !== null ? (
            <>
              <span className="font-mono text-xs">{cli.path}</span>
              <Badge variant="outline">via {SOURCE_LABEL[cli.source]}</Badge>
            </>
          ) : (
            <span className="text-destructive">No devteam CLI found.</span>
          )}
          <Button variant="link" size="sm" className="h-auto p-0 text-xs" onClick={onReResolve}>
            Re-resolve
          </Button>
        </dd>

        <dt className="text-muted-foreground">Store version</dt>
        <dd>{cli?.storeVersion ?? 'not installed'}</dd>

        <dt className="text-muted-foreground">JSON contract</dt>
        <dd>{cli?.jsonContract ?? '?'}</dd>

        <dt className="text-muted-foreground">Write actions</dt>
        <dd>
          <WriteActions build={build} />
        </dd>

        <dt className="text-muted-foreground">App</dt>
        <dd>
          {build !== null ? (
            <>
              {build.appVersion} · Electron {build.electronVersion}
              {build.packaged ? '' : ' · development'}
              {!build.codeSigned ? ' · unsigned' : ''}
            </>
          ) : (
            '…'
          )}
        </dd>
      </dl>
    </section>
  );
}

/**
 * What this build can change, in plain language. The commands it can actually run are
 * enumerated rather than left to a claim that could silently drift from `compat.MUTATING`.
 */
function WriteActions({ build }: { build: BuildInfo | null }) {
  if (build === null) return <>…</>;
  if (!build.hasWriteActions) return <Badge variant="secondary">no write actions</Badge>;
  if (build.mutatingCommandsRun.length === 0) {
    return <span className="text-muted-foreground">declared, but no mutating command is run yet</span>;
  }
  return (
    <span className="flex flex-wrap gap-1">
      {build.mutatingCommandsRun.map((command) => (
        <Badge key={command} variant="outline" className="font-mono">
          {command}
        </Badge>
      ))}
    </span>
  );
}
