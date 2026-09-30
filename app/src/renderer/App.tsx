import { useEffect, useState } from 'react';
import { CircleAlert, Info, Lock, ShieldAlert } from 'lucide-react';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Catalog } from './screens/Catalog.js';
import { Doctor } from './screens/Doctor.js';
import { Projects } from './screens/Projects.js';
import { NotificationBell } from './NotificationBell.js';
import { Loading } from './Problem.js';
// From derived/, never from the brand source beside it: Vite emits whatever it is handed,
// and the 2400px source put 224 kB of bundle into a 20px image. Regenerate with
// `bash build/make-icon.sh`. Imported rather than referenced from `public/` so a missing
// asset is a build error — over `file://` a wrong path is a silent 404.
import wordmarkLight from './logo/derived/wordmark-light-720.png';
import wordmarkDark from './logo/derived/wordmark-dark-720.png';
import lockupLight from './logo/derived/horizontal-light-720.png';
import lockupDark from './logo/derived/horizontal-dark-720.png';
import type {
  BuildInfo,
  CliResolution,
  EnvironmentReport,
  HandshakeView,
  OperationResult,
} from '../shared/api.js';

/**
 * The shell: which CLI was resolved, what the compatibility handshake said, and the three
 * read-only screens.
 *
 * The header carries only what changes a decision on every screen: the store version (what
 * Projects compares against), whether a CLI was found at all, and the unsigned-build
 * warning. "Which `devteam` is this?" — path, source, contract, write actions — is answered
 * in full in the platform's native About window (ADR-0011) — see `main/about.ts`.
 */
export function App() {
  const [build, setBuild] = useState<BuildInfo | null>(null);
  const [resolution, setResolution] = useState<CliResolution | null>(null);
  const [environment, setEnvironment] = useState<EnvironmentReport | null>(null);
  const [handshake, setHandshake] = useState<OperationResult<HandshakeView> | null>(null);
  const [busy, setBusy] = useState(true);
  const [tab, setTab] = useState('projects');
  const [openRequest, setOpenRequest] = useState<{ projectId: string; nonce: number } | null>(null);

  function openProject(projectId: string) {
    setTab('projects');
    setOpenRequest((previous) => ({ projectId, nonce: (previous?.nonce ?? 0) + 1 }));
  }

  // A native notification (or the tray) was clicked; the main process already showed the
  // window. Subscribe first, then take what a click asked for before this window could
  // hear it — the handshake that keeps a click on a fresh window from being lost.
  useEffect(() => {
    const unsubscribe = window.devteam.onOpenProject(openProject);
    void window.devteam.takePendingProject().then((projectId) => {
      if (projectId !== null) openProject(projectId);
    });
    return unsubscribe;
  }, []);

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
          {/* The lockup with the slogan cropped off, not the symbol and not the full
              composition. The guide warns against the slogan at a size that hurts its
              legibility, which is why this row carried the symbol alone before —
              removing the slogan is what makes the lockup usable here at all. The crop
              is measured, not eyeballed; `build/make-icon.sh` records the alpha bands it
              was taken from. Height only, so the ratio is never distorted.

              Two images rather than one `<picture>`, because the dark variant needs a
              style the light one must not have. The brand pack has no transparent
              white-letter horizontal lockup — the guide's *negativa* is white letters and
              orange on a **solid black** field — and a black rectangle on this header's
              oklch(0.185) background reads as a pasted box. `mix-blend-screen` makes that
              black composite away to nothing while leaving the white and the orange
              intact, so the sanctioned asset is used unmodified rather than a new
              treatment being invented for it. Screen on the light variant would wash it
              out, so it is applied to this one only — which a shared `<img>` could not do.

              The name lives in the heading as text: with only one image visible per
              scheme, an `alt` on either would leave the other scheme's heading unnamed. */}
          <h1 className="self-center">
            <span className="sr-only">dev-team-agents</span>
            <img src={wordmarkLight} alt="" aria-hidden="true" className="h-7 w-auto dark:hidden" />
            <img
              src={wordmarkDark}
              alt=""
              aria-hidden="true"
              className="hidden h-7 w-auto mix-blend-screen dark:block"
            />
          </h1>
          {build !== null && !build.codeSigned ? <Badge variant="destructive">unsigned build</Badge> : null}
          <CliLine resolution={resolution} busy={busy} onRetry={() => void load()} />
          <div className="ml-auto self-center">
            <NotificationBell onOpenProject={openProject} />
          </div>
        </div>
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
            <Tabs value={tab} onValueChange={setTab}>
              <TabsList>
                <TabsTrigger value="projects">Projects</TabsTrigger>
                <TabsTrigger value="catalog">Catalog</TabsTrigger>
                <TabsTrigger value="doctor">Diagnosis</TabsTrigger>
              </TabsList>
              {/* Kept mounted while another tab is shown: the project settings screen lives
                  inside this tab, and unmounting it would silently drop unsaved edits. */}
              <TabsContent value="projects" forceMount className="pt-4 data-[state=inactive]:hidden">
                <Projects environment={environment} active={tab === 'projects'} openRequest={openRequest} />
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
    return <span className="text-xs text-muted-foreground">Looking for a devteam CLI…</span>;
  }
  if (!resolution.found) {
    return (
      <span className="flex items-center gap-2 text-xs text-destructive">
        <CircleAlert className="size-3.5" aria-hidden="true" />
        No devteam CLI found.
        <Button variant="link" size="sm" className="h-auto p-0 text-xs" onClick={onRetry}>
          Look again
        </Button>
      </span>
    );
  }
  return (
    <span className="text-xs text-muted-foreground">store {resolution.cli.storeVersion ?? 'not installed'}</span>
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
