import { useEffect, useState } from 'react';
import { CircleAlert, Info, Lock, ShieldAlert } from 'lucide-react';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Catalog } from './screens/Catalog.js';
import { Doctor } from './screens/Doctor.js';
import { Projects } from './screens/Projects.js';
import { Loading } from './Problem.js';
// From derived/, never from the brand source beside it: Vite emits whatever it is handed,
// and the 2400px source put 224 kB of bundle into a 20px image. Regenerate with
// `bash build/make-icon.sh`. Imported rather than referenced from `public/` so a missing
// asset is a build error — over `file://` a wrong path is a silent 404.
import brandSymbol from './logo/derived/symbol-128.png';
import lockupLight from './logo/derived/horizontal-light-720.png';
import lockupDark from './logo/derived/horizontal-dark-720.png';
import type {
  BuildInfo,
  CliResolution,
  CliSource,
  EnvironmentReport,
  HandshakeView,
  OperationResult,
} from '../shared/api.js';

/**
 * The shell: which CLI was resolved, what the compatibility handshake said, and the three
 * read-only screens.
 *
 * The header is not decoration. ADR-0011 makes the app a client of one CLI, and "which
 * `devteam` is this?" is the question a user cannot answer from the outside — an app that
 * silently resolved a different binary from the user's terminal would report the harness
 * in a state the terminal disagrees with. So the resolved path, its source and its store
 * version sit at the top of every screen.
 */
export function App() {
  const [build, setBuild] = useState<BuildInfo | null>(null);
  const [resolution, setResolution] = useState<CliResolution | null>(null);
  const [environment, setEnvironment] = useState<EnvironmentReport | null>(null);
  const [handshake, setHandshake] = useState<OperationResult<HandshakeView> | null>(null);
  const [busy, setBusy] = useState(true);

  async function load() {
    setBusy(true);
    const [info, resolved] = await Promise.all([window.devteam.buildInfo(), window.devteam.resolveCli()]);
    setBuild(info);
    setResolution(resolved);
    // After `resolveCli`, which re-reads the settings file and re-attempts the declaration.
    setEnvironment(await window.devteam.environment());
    // The handshake is only meaningful once a CLI exists to ask.
    setHandshake(resolved.found ? await window.devteam.handshake() : null);
    setBusy(false);
  }

  useEffect(() => {
    void load();
  }, []);

  return (
    <div className="flex h-full flex-col">
      <header className="app-drag border-b bg-card/60 px-6 pt-8 pb-4">
        <div className="no-drag flex flex-wrap items-baseline gap-x-3 gap-y-1">
          {/* The symbol, not the horizontal lockup. The brand guide's horizontal and
              principal compositions both carry the slogan, and it says to avoid the
              slogan at sizes that hurt its legibility — at a 20px header it would be
              unreadable. The mark alone is the composition the guide defines for this
              ("Símbolo: somente o asterisco existente"). `aria-hidden` because the
              heading beside it already announces the name; two labels would be read
              twice. Height only, so the aspect ratio is never distorted. */}
          <img
            src={brandSymbol}
            alt=""
            aria-hidden="true"
            className="h-5 w-auto self-center"
          />
          <h1 className="text-lg font-semibold tracking-tight">dev-team-agents</h1>
          <WriteActionsBadge build={build} />
          {build !== null && !build.codeSigned ? <Badge variant="destructive">unsigned build</Badge> : null}
          {build !== null ? (
            <span className="text-xs text-muted-foreground">
              app {build.appVersion} · Electron {build.electronVersion}
              {build.packaged ? '' : ' · development'}
            </span>
          ) : null}
        </div>
        <CliLine resolution={resolution} busy={busy} onRetry={() => void load()} />
      </header>

      <main className="flex-1 overflow-auto px-6 py-5">
        {build !== null && !build.codeSigned && build.packaged ? (
          <Alert variant="destructive" className="mb-4">
            <ShieldAlert />
            <AlertTitle>This build is not signed or notarised</AlertTitle>
            <AlertDescription>
              No Apple Developer ID exists for this project yet, so nothing here has been through{' '}
              <code className="font-mono">codesign</code> or <code className="font-mono">notarytool</code>. Do not
              distribute it, and do not treat the <code className="font-mono">.dmg</code> as shippable.
            </AlertDescription>
          </Alert>
        ) : null}

        {/* Above the no-CLI branch on purpose: a malformed settings file is one reason the
            search found nothing, and the user needs both facts on the same screen. */}
        <EnvironmentBanner environment={environment} busy={busy} />

        {busy ? (
          <Loading what="the first-run checks" />
        ) : resolution === null || !resolution.found ? (
          <NoCli resolution={resolution} onRetry={() => void load()} />
        ) : (
          <>
            <HandshakeBanner handshake={handshake} />
            <Tabs defaultValue="projects">
              <TabsList>
                <TabsTrigger value="projects">Projects</TabsTrigger>
                <TabsTrigger value="catalog">Catalog</TabsTrigger>
                <TabsTrigger value="doctor">Diagnosis</TabsTrigger>
              </TabsList>
              <TabsContent value="projects" className="pt-4">
                <Projects environment={environment} />
              </TabsContent>
              <TabsContent value="catalog" className="pt-4">
                <Catalog />
              </TabsContent>
              <TabsContent value="doctor" className="pt-4">
                <Doctor />
              </TabsContent>
            </Tabs>
          </>
        )}
      </main>
    </div>
  );
}

/**
 * What this build can change, in plain language.
 *
 * `BuildInfo.noWriteActions: true` — a literal type the compiler itself would have had to
 * be edited to admit a write action — is gone. `hasWriteActions` is a boolean, and this
 * build sets it `true`: the project lifecycle (bind, unbind, sync, pin, upgrade) is
 * reachable from the UI. The badge says so, and the commands it can actually run are
 * enumerated rather than left to a claim that could silently drift from
 * `compat.MUTATING`.
 */
function WriteActionsBadge({ build }: { build: BuildInfo | null }) {
  if (build === null) return null;
  if (!build.hasWriteActions) return <Badge variant="secondary">no write actions</Badge>;
  return (
    <Badge
      variant="outline"
      title={
        build.mutatingCommandsRun.length > 0
          ? `Commands this build can run that change the store: ${build.mutatingCommandsRun.join(', ')}`
          : 'This build declares write actions but runs no mutating command yet.'
      }
    >
      write actions: {build.mutatingCommandsRun.length > 0 ? build.mutatingCommandsRun.join(', ') : 'none run'}
    </Badge>
  );
}

const SOURCE_LABEL: Record<CliSource, string> = {
  configured: 'configured path',
  path: 'PATH',
  homebrew: 'Homebrew',
  winget: 'winget',
};

function CliLine({
  resolution,
  busy,
  onRetry,
}: {
  resolution: CliResolution | null;
  busy: boolean;
  onRetry: () => void;
}) {
  if (busy || resolution === null) {
    return <p className="no-drag pt-1 text-xs text-muted-foreground">Looking for a devteam CLI…</p>;
  }
  if (!resolution.found) {
    return (
      <p className="no-drag flex items-center gap-2 pt-1 text-xs text-destructive">
        <CircleAlert className="size-3.5" aria-hidden="true" />
        No devteam CLI found.
        <Button variant="link" size="sm" className="h-auto p-0 text-xs" onClick={onRetry}>
          Look again
        </Button>
      </p>
    );
  }
  const { cli } = resolution;
  return (
    <p className="no-drag flex flex-wrap items-center gap-x-2 gap-y-1 pt-1 text-xs text-muted-foreground">
      <span className="font-mono">{cli.path}</span>
      <Badge variant="outline">via {SOURCE_LABEL[cli.source]}</Badge>
      <span>
        store {cli.storeVersion ?? 'not installed'} · json contract {cli.jsonContract ?? '?'}
      </span>
      <Button variant="link" size="sm" className="h-auto p-0 text-xs" onClick={onRetry}>
        Re-resolve
      </Button>
    </p>
  );
}

/**
 * The app's own preconditions, when one of them is not met.
 *
 * Both states here used to be invisible. The declaration write was caught with a comment
 * claiming "the UI can see it" — no field of any view model carried it, so a failed write
 * meant every call ran undeclared and the one mutating command ran **ungated**. And
 * `readSettings` returns a `problem` documented as "Reported, never silently ignored" that
 * nothing read, so a malformed `settings.json` produced the no-CLI screen with no
 * explanation of why the path the user had set was ignored.
 *
 * Renders nothing when both are fine: a banner that is always there is one nobody reads.
 */
function EnvironmentBanner({ environment, busy }: { environment: EnvironmentReport | null; busy: boolean }) {
  if (environment === null) return null;
  const declarationFailed = environment.declaration.state === 'failed';
  const settingsProblem = environment.settings.problem;
  if (!declarationFailed && settingsProblem === null) return null;

  return (
    <Alert variant="destructive" className="mb-4">
      <ShieldAlert />
      <AlertTitle>
        {declarationFailed && settingsProblem !== null
          ? 'Two of this app’s own preconditions are not met'
          : declarationFailed
            ? 'This app could not declare which store shapes it understands'
            : 'This app’s settings file could not be used'}
      </AlertTitle>
      <AlertDescription>
        {environment.declaration.state === 'failed' ? (
          <>
            <p>
              <code className="font-mono">{environment.declaration.path}</code> could not be written:{' '}
              {environment.declaration.detail}
            </p>
            <p>
              The framework&apos;s write gate binds a client that declares itself, so without this file every call runs
              ungated.{' '}
              {environment.withheld.length > 0
                ? `The app is therefore refusing ${environment.withheld
                    .map((entry) => `\`devteam ${entry.command}\``)
                    .join(', ')} rather than running it unchecked.`
                : null}
            </p>
          </>
        ) : null}
        {settingsProblem !== null ? (
          <p>
            <code className="font-mono">{environment.settings.path}</code> {settingsProblem}. The CLI search ran{' '}
            <em>without</em> it, so a <code className="font-mono">cliPath</code> set in that file was not used.
          </p>
        ) : null}
        {busy ? null : (
          <p className="text-muted-foreground">
            Every invocation runs in <code className="font-mono">{environment.workingDirectory}</code>.
          </p>
        )}
      </AlertDescription>
    </Alert>
  );
}

function NoCli({ resolution, onRetry }: { resolution: CliResolution | null; onRetry: () => void }) {
  const rejected = resolution !== null && !resolution.found ? resolution.rejected : [];
  const remedy = resolution !== null && !resolution.found ? resolution.remedy : [];
  const searched = resolution !== null && !resolution.found ? resolution.searchedCount : 0;
  const bySource = resolution !== null && !resolution.found ? resolution.searchedBySource : [];

  return (
    <div className="space-y-6">
      {/* Above the alert, not inside it: a brand lockup in a destructive red box reads as
          marketing at the moment the user wants a problem solved. This is the one surface
          with the vertical room the horizontal composition needs — the brand guide warns
          against the slogan at sizes that hurt its legibility, which is why the header
          carries the symbol alone instead. The dark variant is the guide's *negativa*
          (letters to white, orange kept) rather than the mono white, chosen by
          prefers-color-scheme because the app follows the OS and has no theme toggle.
          `alt=""` because the header already names the app; two labels read twice. */}
      <picture>
        <source srcSet={lockupDark} media="(prefers-color-scheme: dark)" />
        <img src={lockupLight} alt="" aria-hidden="true" className="h-20 w-auto" />
      </picture>
      <Alert variant="destructive">
        <CircleAlert />
        <AlertTitle>No devteam CLI on this host</AlertTitle>
        <AlertDescription>
          <p>
            This app is a client of the <code className="font-mono">devteam</code> CLI and deliberately ships no copy of
            it. {searched} location{searched === 1 ? '' : 's'} were checked
            {bySource.length > 0 ? ':' : '.'}
          </p>
          {bySource.length > 0 ? (
            <ul className="list-inside list-disc font-mono text-xs">
              {bySource.map((entry) => (
                <li key={entry.source}>
                  {entry.label}: {entry.count}
                </li>
              ))}
            </ul>
          ) : null}
          {rejected.length > 0 ? (
            <ul className="list-inside list-disc font-mono text-xs">
              {rejected.map((entry) => (
                <li key={entry.path}>
                  {entry.path} — {entry.reason}
                </li>
              ))}
            </ul>
          ) : null}
          <ul className="list-inside list-disc">
            {remedy.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
          <Button variant="outline" size="sm" onClick={onRetry}>
            Look again
          </Button>
        </AlertDescription>
      </Alert>
    </div>
  );
}

/**
 * The handshake verdict, in plain language.
 *
 * Shown on every screen, not hidden behind a settings pane: ADR-0011's rule is that an
 * app which does not understand the store "degrades to read-only and says so", and a
 * verdict the user has to go looking for is not one the app said.
 */
function HandshakeBanner({ handshake }: { handshake: OperationResult<HandshakeView> | null }) {
  if (handshake === null) return null;
  if (!handshake.ok) {
    return (
      <Alert variant="destructive" className="mb-4">
        <CircleAlert />
        <AlertTitle>The compatibility check could not be completed</AlertTitle>
        <AlertDescription>
          <p>{handshake.message}</p>
          <p className="text-muted-foreground">The app stays read-only until it can be answered.</p>
        </AlertDescription>
      </Alert>
    );
  }

  const view = handshake.data;

  if (view.state === 'unknown') {
    return (
      <Alert variant="destructive" className="mb-4">
        <CircleAlert />
        <AlertTitle>Compatibility with this store is unknown</AlertTitle>
        <AlertDescription>
          <p>{view.summary}</p>
          <p className="text-muted-foreground">{view.detail}</p>
        </AlertDescription>
      </Alert>
    );
  }

  if (!view.mayWrite) {
    // `view.summary` already names every unsupported shape with both versions — see
    // `declaration.ts`'s `interpret()` — so this used to rebuild the identical list a
    // second time underneath it. One rendering of the same facts, not a scan-then-read
    // pair: the summary sentence is already parenthetical and per-shape.
    return (
      <Alert variant="destructive" className="mb-4">
        <Lock />
        <AlertTitle>This store keeps records in a shape this app does not understand</AlertTitle>
        <AlertDescription>
          <p>{view.summary}</p>
          <p className="text-muted-foreground">
            Everything below is still readable. Upgrade the app before it writes to this store — dropping the check
            would only hide the mismatch.
          </p>
        </AlertDescription>
      </Alert>
    );
  }

  return (
    <Alert className="mb-4">
      <Info />
      <AlertTitle>Compatible with this store</AlertTitle>
      <AlertDescription>
        <p>{view.summary}</p>
        <p className="font-mono text-xs text-muted-foreground">
          {Object.entries(view.storeSchemas)
            .sort(([a], [b]) => a.localeCompare(b))
            .map(([name, version]) => `${name}=${version}`)
            .join(' · ')}
        </p>
      </AlertDescription>
    </Alert>
  );
}
