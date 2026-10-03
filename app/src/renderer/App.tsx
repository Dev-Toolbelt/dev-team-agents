import { useCallback, useEffect, useRef, useState } from 'react';
import { CircleAlert, Lock, ShieldAlert } from 'lucide-react';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Toaster } from '@/components/ui/sonner';
import { Button } from '@/components/ui/button';
import { Hint } from '@/components/ui/tooltip';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Board } from './screens/Board.js';
import { Catalog } from './screens/Catalog.js';
import { Doctor } from './screens/Doctor.js';
import { Integrations } from './screens/Integrations.js';
import { Projects } from './screens/Projects.js';
import { NotificationBell } from './NotificationBell.js';
import { AccountGate } from './account/AccountGate.js';
import { AccountMenu } from './account/AccountMenu.js';
import { AccountProvider } from './account/AccountContext.js';
import { Profile } from './account/Profile.js';
import { Skills } from './screens/Skills.js';
import { ErrorBoundary } from './ErrorBoundary.js';
import { Loading } from './Problem.js';
import { isPrerelease } from '../shared/appVersion.js';
import { hostPlatformFrom } from '../shared/directoryPaths.js';
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
  CliInstallResult,
  CliResolution,
  EnvironmentReport,
  HandshakeView,
  OperationResult,
} from '../shared/api.js';

/**
 * The shell: which CLI was resolved, what the compatibility handshake said, and the
 * screens.
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
  // A startup call that rejects (IPC down, main process gone) is shown with a retry rather
  // than left as an endless "Looking for a devteam CLI…".
  const [loadError, setLoadError] = useState<string | null>(null);
  const loadErrorRef = useRef<HTMLDivElement>(null);
  const [tab, setTab] = useState('projects');
  // Bumped whenever an account-level integration write succeeds, so each project's
  // Integrations tab (kept mounted) reloads its account readout.
  const [integrationsNonce, setIntegrationsNonce] = useState(0);
  const onAccountChanged = useCallback(() => setIntegrationsNonce((n) => n + 1), []);
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
    window.devteam
      .takePendingProject()
      .then((projectId) => {
        if (projectId !== null) openProject(projectId);
      })
      .catch(() => undefined);
    return unsubscribe;
  }, []);

  // The start-up checks screen is replaced by the failure: move focus to it.
  useEffect(() => {
    if (!busy && loadError !== null) loadErrorRef.current?.focus();
  }, [busy, loadError]);

  async function load() {
    setBusy(true);
    setLoadError(null);
    try {
      const [info, resolved] = await Promise.all([window.devteam.buildInfo(), window.devteam.resolveCli()]);
      setBuild(info);
      setResolution(resolved);
      // After `resolveCli`, which re-reads the settings file and re-attempts the declaration.
      setEnvironment(await window.devteam.environment());
      // The handshake is only meaningful once a CLI exists to ask.
      setHandshake(resolved.found ? await window.devteam.handshake() : null);
    } catch (error) {
      setLoadError(String(error));
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  return (
    // ADR-0029: accounts are mandatory. The provider asks the CLI (`auth check`) once a CLI is
    // known to exist; the gate below decides what the answer lets the person see.
    <AccountProvider enabled={!busy && resolution !== null && resolution.found}>
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
            {build !== null ? <AppVersion version={build.appVersion} /> : null}
            <CliLine resolution={resolution} busy={busy} onRetry={() => void load()} />
            <div className="ml-auto flex items-center gap-2 self-center">
              <NotificationBell onOpenProject={openProject} />
              <AccountMenu onOpen={() => setTab('account')} />
            </div>
          </div>
        </header>

        {/* `relative` makes this the containing block of anything absolutely positioned inside
            (every `sr-only` text): without it they were placed against the page and stretched
            the body into a second scrollbar. `min-h-0` keeps the flex child inside the window. */}
        <main className="relative min-h-0 flex-1 overflow-auto px-6 py-5">
          {build !== null && !build.codeSigned && build.packaged ? <UnsignedBuildNotice /> : null}

          {/* Above the no-CLI branch on purpose: a malformed settings file is one reason the
              search found nothing, and the user needs both facts on the same screen. */}
          <EnvironmentBanner environment={environment} busy={busy} />

          {busy ? (
            <Loading what="the first-run checks" />
          ) : loadError !== null ? (
            <Alert ref={loadErrorRef} tabIndex={-1} variant="destructive" className="outline-hidden">
              <CircleAlert />
              <AlertTitle>The app could not finish its start-up checks</AlertTitle>
              <AlertDescription>
                <p>the app could not reach its own main process: {loadError}</p>
                <Button variant="outline" size="sm" onClick={() => void load()}>
                  Try again
                </Button>
              </AlertDescription>
            </Alert>
          ) : resolution === null || !resolution.found ? (
            <NoCli resolution={resolution} onRetry={() => void load()} />
          ) : (
            <AccountGate onOpenAccount={() => setTab('account')}>
              <HandshakeBanner handshake={handshake} />
              <Tabs value={tab} onValueChange={setTab}>
                <TabsList>
                  <TabsTrigger value="projects">Projects</TabsTrigger>
                  <TabsTrigger value="board">Board</TabsTrigger>
                  <TabsTrigger value="catalog">Catalog</TabsTrigger>
                  <TabsTrigger value="skills">Global Skills</TabsTrigger>
                  <TabsTrigger value="integrations">Integrations</TabsTrigger>
                  <TabsTrigger value="doctor">Diagnosis</TabsTrigger>
                  <TabsTrigger value="account">Account</TabsTrigger>
                </TabsList>
                {/* Kept mounted while another tab is shown: the project settings screen lives
                    inside this tab, and unmounting it would silently drop unsaved edits. */}
                <TabsContent value="projects" forceMount className="pt-4 data-[state=inactive]:hidden">
                  <ErrorBoundary label="The Projects screen" resetKey={tab}>
                    <Projects
                      environment={environment}
                      active={tab === 'projects'}
                      openRequest={openRequest}
                      onOpenIntegrations={() => setTab('integrations')}
                      integrationsNonce={integrationsNonce}
                    />
                  </ErrorBoundary>
                </TabsContent>
                {/* Kept mounted so the live feed keeps streaming; leaving the tab still returns
                    it to the overview (see `Board`). */}
                <TabsContent value="board" forceMount className="pt-4 data-[state=inactive]:hidden">
                  <Board active={tab === 'board'} />
                </TabsContent>
                <TabsContent value="catalog" className="pt-4">
                  <ErrorBoundary label="The Catalog screen">
                    <Catalog />
                  </ErrorBoundary>
                </TabsContent>
                <TabsContent value="skills" className="pt-4">
                  <ErrorBoundary label="The Global Skills screen">
                    <Skills environment={environment} />
                  </ErrorBoundary>
                </TabsContent>
                {/* Kept mounted: a typed token or an edited account field is a draft. */}
                <TabsContent value="integrations" forceMount className="pt-4 data-[state=inactive]:hidden">
                  <ErrorBoundary label="The Integrations screen">
                    <Integrations environment={environment} active={tab === 'integrations'} onAccountChanged={onAccountChanged} />
                  </ErrorBoundary>
                </TabsContent>
                <TabsContent value="doctor" className="pt-4">
                  <ErrorBoundary label="The Diagnosis screen">
                    <Doctor />
                  </ErrorBoundary>
                </TabsContent>
                <TabsContent value="account" className="pt-4">
                  <ErrorBoundary label="The Account screen">
                    <Profile />
                  </ErrorBoundary>
                </TabsContent>
              </Tabs>
            </AccountGate>
          )}
        </main>
        {/* Write results land here, outside every layout — see `toasts.tsx`. */}
        <Toaster position="bottom-right" richColors />
      </div>
    </AccountProvider>
  );
}

/**
 * This app's own version, beside the store's — two different things, both named so the
 * header never shows a bare number. A pre-release (see `isPrerelease`) carries a "beta"
 * badge: the build is for testing, and the badge goes away on its own at the first
 * stable version.
 */
function AppVersion({ version }: { version: string }) {
  return (
    <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
      app {version}
      {isPrerelease(version) ? (
        <Hint content="A pre-release build, for testing">
          <Badge className="bg-warning text-warning-foreground">
            beta
          </Badge>
        </Hint>
      ) : null}
    </span>
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
          <div className="flex flex-wrap items-center gap-2">
            {hostPlatform() === 'win32' ? <InstallCliButton onInstalled={onRetry} /> : null}
            <Button variant="outline" size="sm" onClick={onRetry}>
              Look again
            </Button>
          </div>
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

  // Compatible: nothing to say. Only a problem earns a banner.
  return null;
}

/** Read at render time, not module load, so a test can set the platform per case. */
function hostPlatform() {
  return hostPlatformFrom(typeof navigator === 'undefined' ? undefined : navigator.platform);
}

/**
 * "Install the CLI" (ADR-0028), Windows only: the main process downloads the newest CLI
 * installer from GitHub, checks its SHA-256 and runs its wizard. On success the app looks
 * again, which finds the CLI in the installer's directory even though this process
 * started with the old PATH.
 */
function InstallCliButton({ onInstalled }: { onInstalled: () => void }) {
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<CliInstallResult | null>(null);

  const install = async () => {
    setRunning(true);
    setResult(null);
    try {
      const outcome = await window.devteam.installCli();
      setResult(outcome);
      if (outcome.outcome === 'installed') onInstalled();
    } catch (error) {
      setResult({ outcome: 'failed', message: `The install could not be started: ${String(error)}` });
    } finally {
      setRunning(false);
    }
  };

  return (
    <>
      <Button size="sm" onClick={() => void install()} disabled={running}>
        {running ? 'Installing the CLI…' : 'Install the CLI'}
      </Button>
      {/* Still on this screen after an install means the CLI was not found: say so, rather
          than letting a successful install look like nothing happened. */}
      {result !== null ? (
        <p role="status" className="basis-full">
          {result.outcome === 'installed'
            ? `${result.message} The app has not found it yet: choose Look again, or restart the app.`
            : result.message}
        </p>
      ) : null}
    </>
  );
}

/**
 * The unsigned-build warning, worded for the platform it is read on: a Windows user was
 * shown Apple's signing tools and a `.dmg` they never downloaded. The text sits in one
 * `<p>` because `AlertDescription` is a grid — loose text and `<code>` siblings each
 * became a row of their own.
 */
function UnsignedBuildNotice() {
  return (
    <Alert variant="destructive" className="mb-4">
      <ShieldAlert />
      {hostPlatform() === 'win32' ? (
        <>
          <AlertTitle>This build is not signed</AlertTitle>
          <AlertDescription>
            <p>
              No Authenticode certificate exists for this project yet, so this installer is unsigned and Windows
              SmartScreen warns before it runs. Do not distribute it, and do not treat the{' '}
              <code className="font-mono">.exe</code> as shippable.
            </p>
          </AlertDescription>
        </>
      ) : (
        <>
          <AlertTitle>This build is not signed or notarised</AlertTitle>
          <AlertDescription>
            <p>
              No Apple Developer ID exists for this project yet, so nothing here has been through{' '}
              <code className="font-mono">codesign</code> or <code className="font-mono">notarytool</code>. Do not
              distribute it, and do not treat the <code className="font-mono">.dmg</code> as shippable.
            </p>
          </AlertDescription>
        </>
      )}
    </Alert>
  );
}
