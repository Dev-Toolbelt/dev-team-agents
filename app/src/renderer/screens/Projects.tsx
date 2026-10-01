import { useEffect, useRef, useState } from 'react';
import { AlertTriangle, CheckCircle2, FolderSync, Plus, RefreshCw } from 'lucide-react';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import {
  Dialog,
  DialogBody,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Hint } from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';
import { Empty, Loading, Problem } from '../Problem.js';
import { ProjectList, useProjectSyncs } from './ProjectList.js';
import { basename, displayName, settingsButtonId } from './ProjectRow.js';
import { ProjectSettings } from './ProjectSettings.js';
import { useAction, useOperation } from '../useOperation.js';
import { toastFailure, toastPartialFailure, toastResult } from '../toasts.js';
import { Notice, WriteButton } from '../WriteButton.js';
import type {
  BindMode,
  BindProvider,
  BindReport,
  EnvironmentReport,
  MigrateRequest,
  MigrationPlan,
  MigrationReport,
  OperationResult,
  PreferencesImport,
  SyncAllReport,
} from '../../shared/api.js';

const PROVIDERS: readonly BindProvider[] = ['claude', 'opencode', 'codex'];

// The values sent to the CLI — never change these. The label shown to the user is a
// separate concern (`PROVIDER_LABELS`, below).
const PROVIDER_LABELS: Record<BindProvider, string> = {
  claude: 'Claude Code (Anthropic)',
  codex: 'Codex (OpenAI)',
  opencode: 'Opencode',
};

// `link` first: it is what the app recommends, and putting the recommendation first
// reads as a recommendation rather than as something buried in a list sorted some other
// way. The other three keep no particular order among themselves.
const MODES: readonly BindMode[] = ['link', 'auto', 'copy', 'vendored'];

const MODE_LABELS: Record<BindMode, string> = {
  link: 'Link',
  auto: 'Auto',
  copy: 'Copy',
  vendored: 'Vendored',
};

// `link` is what the app recommends — it is the only mode where a store update reaches a
// bound project with no further step. `auto` stays the CLI's own default (it probes for
// symlink support and resolves to `link` or `copy` accordingly); this constant only decides
// what the dialog pre-selects and labels, never the CLI contract.
const RECOMMENDED_MODE: BindMode = 'link';

// One line per mode, phrased as the consequence a user cares about — not the mechanism.
// One line each (reuse guideline `app_support_copy`): the consequence that decides the
// choice, not how the mode works — `CLAUDE-md/cli.md` § bind modes has that.
const MODE_DESCRIPTIONS: Record<BindMode, string> = {
  auto: 'Link if symlinks work here, else Copy.',
  link: 'Updates reach the project automatically.',
  copy: 'No symlinks; run sync after each update.',
  vendored: 'Copies the framework into your repo.',
};

/** A bound project as the bind dialog needs it: where it is, and what the list calls it. */
interface BoundDirectory {
  readonly path: string;
  readonly name: string;
}

/** Without trailing separators, and with Windows separators normalised: paths compared as written. */
function normalizeDirectory(path: string): string {
  return path.replace(/\\/g, '/').replace(/\/+$/, '');
}

/**
 * The bound project `chosen` is, or sits inside — or `undefined`. Compared by whole path
 * components, so `/repo/app-2` is not read as inside `/repo/app`.
 */
function boundDirectory(chosen: string, bound: readonly BoundDirectory[]): BoundDirectory | undefined {
  const target = normalizeDirectory(chosen);
  return bound.find((project) => {
    const root = normalizeDirectory(project.path);
    return target === root || target.startsWith(`${root}/`);
  });
}

/**
 * `devteam list --json`, plus the project lifecycle: bind, sync, pin, unbind, upgrade.
 *
 * A real `<table>`, not a grid of divs: the data is tabular, the browser gives row/column
 * semantics to a screen reader for free, and there is no interaction here that a kit
 * component would buy anything for.
 */
export function Projects({
  environment,
  active = true,
  openRequest = null,
  onOpenIntegrations,
  integrationsNonce = 0,
}: {
  environment: EnvironmentReport | null;
  /** Whether this tab is the visible one. The tab stays mounted (see `App.tsx`), so it refetches on return. */
  active?: boolean;
  /**
   * A notification asked to show this project. The nonce makes a second request for the
   * same project a new request rather than an unchanged prop.
   */
  openRequest?: { readonly projectId: string; readonly nonce: number } | null;
  /** A project's Integrations tab asked to go to the top-level Integrations tab. */
  onOpenIntegrations?: (() => void) | undefined;
  /** Bumped when an account write made each project's Integrations tab stale. */
  integrationsNonce?: number;
}) {
  const { state, refreshing, reload: reloadList } = useOperation((): ReturnType<typeof window.devteam.listProjects> => window.devteam.listProjects());
  const [bindOpen, setBindOpen] = useState(false);
  const syncAll = useAction(() => window.devteam.syncAllProjects());

  // The app's own names, fetched separately from `list` because they live in this app's
  // settings file, not the store. Re-fetched every time the project list itself reloads —
  // the only write action that can change this map is `bind`, but re-fetching on every
  // reload is one effect instead of threading a second, bind-specific refresh through
  // every call site that already calls `reload()`.
  const [projectNames, setProjectNames] = useState<Readonly<Record<string, string>>>({});
  const [namesNonce, setNamesNonce] = useState(0);
  useEffect(() => {
    let live = true;
    // A failed read leaves the map as it was: every name falls back to the directory's
    // basename, which is what the map being empty already means.
    void window.devteam
      .projectNames()
      .then((names) => {
        if (live) setProjectNames(names);
      })
      .catch(() => {
        if (live) setProjectNames({});
      });
    return () => {
      live = false;
    };
  }, [namesNonce]);
  function reload() {
    reloadList();
    setNamesNonce((n) => n + 1);
  }

  // Every sync on the screen goes through one coordinator, so none runs beside another.
  const syncs = useProjectSyncs(reload);

  const [filterText, setFilterText] = useState('');
  const [filterMode, setFilterMode] = useState<BindMode | 'all'>('all');
  const [filterProviders, setFilterProviders] = useState<ReadonlySet<BindProvider>>(new Set());
  // The project whose settings are open, by id — the record itself is looked up in the
  // current listing, so a reload never leaves the screen holding a stale one.
  const [openSettings, setOpenSettings] = useState<string | null>(null);
  // The project whose settings just closed: focus goes back to its name, not to <body>.
  const [returnFocusTo, setReturnFocusTo] = useState<string | null>(null);
  useEffect(() => {
    if (returnFocusTo === null || openSettings !== null) return;
    document.getElementById(settingsButtonId(returnFocusTo))?.focus();
    setReturnFocusTo(null);
  });

  // A project a notification asked for while another one's settings were open.
  const [deferredOpen, setDeferredOpen] = useState<string | null>(null);
  // Never over an open settings screen: it may hold unsaved edits, and its own "leave with
  // unsaved changes?" guard must not be bypassed by a notification. The request waits,
  // is said out loud above that screen, and is honoured when the user leaves it.
  useEffect(() => {
    if (openRequest === null) return;
    if (openSettings === null) setOpenSettings(openRequest.projectId);
    else if (openSettings !== openRequest.projectId) setDeferredOpen(openRequest.projectId);
  }, [openRequest?.nonce]);

  // Keeping the tab mounted preserves unsaved settings, but it also stopped the refetch a
  // remount used to give for free; returning to the tab asks `list` again.
  const wasActive = useRef(active);
  useEffect(() => {
    if (active && !wasActive.current) reload();
    wasActive.current = active;
  });

  if (state.phase === 'loading') return <Loading what="devteam list" />;
  if (!state.result.ok) {
    return (
      <div className="space-y-3">
        <Problem problem={state.result} />
        <Button variant="outline" size="sm" onClick={reload}>
          Try again
        </Button>
      </div>
    );
  }

  const { current, projects } = state.result.data;

  const settingsFor = openSettings === null ? undefined : projects.find((project) => project.project_id === openSettings);
  if (settingsFor !== undefined) {
    const waiting = deferredOpen === null ? undefined : projects.find((project) => project.project_id === deferredOpen);
    return (
      <>
        {waiting !== undefined ? (
          <Alert className="mb-4" role="status">
            <AlertTitle>
              A notification asked to open {displayName(waiting.path, waiting.project_id, projectNames)}
            </AlertTitle>
            <AlertDescription>It opens when you leave these settings.</AlertDescription>
          </Alert>
        ) : null}
        <ProjectSettings
          // Keyed by project: drafts, tabs and pending flags belong to one project, and
          // must not carry over when a notification opens another.
          key={settingsFor.project_id}
          project={settingsFor}
          name={displayName(settingsFor.path, settingsFor.project_id, projectNames)}
          environment={environment}
          active={active}
          onOpenIntegrations={onOpenIntegrations}
          integrationsNonce={integrationsNonce}
          onBack={() => {
            if (waiting !== undefined) {
              setOpenSettings(waiting.project_id);
            } else {
              setReturnFocusTo(settingsFor.project_id);
              setOpenSettings(null);
            }
            setDeferredOpen(null);
            reload();
          }}
          onDismiss={() => {
            // Like Back: a project a notification is waiting to open is what the tab shows next.
            setOpenSettings(waiting !== undefined ? waiting.project_id : null);
            setDeferredOpen(null);
          }}
          onChanged={reload}
          onUnbound={() => {
            // The project is gone, so there is no row to return focus to.
            setOpenSettings(null);
            setDeferredOpen(null);
            reload();
          }}
        />
      </>
    );
  }

  const normalizedFilterText = filterText.trim().toLowerCase();
  const filteredProjects = projects.filter((project) => {
    if (normalizedFilterText !== '') {
      const name = displayName(project.path, project.project_id, projectNames).toLowerCase();
      if (!name.includes(normalizedFilterText) && !project.path.toLowerCase().includes(normalizedFilterText)) {
        return false;
      }
    }
    if (filterMode !== 'all' && project.mode !== filterMode) return false;
    // Any-of, not all-of: three checkboxes that all narrow together would need every one
    // checked to see a project bound with just one provider, which reads as "everything
    // is filtered out" the first time someone tries it.
    if (filterProviders.size > 0 && !project.providers.some((provider) => filterProviders.has(provider as BindProvider))) {
      return false;
    }
    return true;
  });

  const filtering = normalizedFilterText !== '' || filterMode !== 'all' || filterProviders.size > 0;

  const refreshButton = (
    <Hint content="Reload the project list from the CLI">
      <Button variant="outline" size="xs" onClick={reload}>
        <RefreshCw className={refreshing ? 'animate-spin' : ''} aria-hidden="true" />
        Refresh
      </Button>
    </Hint>
  );

  return (
    <section aria-labelledby="projects-heading" className="space-y-4">
      <header className="flex flex-wrap items-baseline justify-between gap-4">
        <div>
          <h2 id="projects-heading" className="text-base font-semibold">
            Projects
          </h2>
          <p className="text-sm text-muted-foreground">
            {projects.length === 0
              ? 'None yet.'
              : `${projects.length} project${projects.length === 1 ? '' : 's'} bound to this store.`}
            {current !== null ? ` Store version ${current} is current.` : ' No store version is current.'}
          </p>
          {/* A reload no longer replaces the table — see `useOperation`'s `refreshing`. This
              is how the refresh stays visible without unmounting the row that a write action
              just wrote a notice into. `aria-live` so it is announced rather than only seen. */}
          <p aria-live="polite" className="text-xs text-muted-foreground">
            {refreshing ? 'Refreshing the project list…' : null}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {/* With no projects there is no table toolbar to hold Refresh, so it stays here. */}
          {projects.length === 0 ? refreshButton : null}
          <WriteButton
            command="bind"
            environment={environment}
            size="sm"
            tooltip="Bind a new project directory to this store"
            onClick={() => setBindOpen(true)}
          >
            <Plus />
            New project
          </WriteButton>
        </div>
      </header>

      {projects.length === 0 ? (
        <Empty>Nothing is bound yet. Use New project above to choose a project directory.</Empty>
      ) : (
        <>
          <ProjectFilters
            text={filterText}
            onText={setFilterText}
            mode={filterMode}
            onMode={setFilterMode}
            providers={filterProviders}
            onToggleProvider={(provider, checked) => {
              setFilterProviders((previous) => {
                const next = new Set(previous);
                if (checked) next.add(provider);
                else next.delete(provider);
                return next;
              });
            }}
          />
          <ProjectList
            projects={projects}
            filteredProjects={filteredProjects}
            filtering={filtering}
            textFiltering={normalizedFilterText !== ''}
            projectNames={projectNames}
            environment={environment}
            current={current}
            syncs={syncs}
            syncAllPending={syncAll.state.phase === 'pending'}
            onChanged={reload}
            onOpenSettings={setOpenSettings}
            toolbar={
              <>
                <WriteButton
                  command="sync"
                  environment={environment}
                  variant="outline"
                  size="xs"
                  tooltip="Re-apply the current store version to every bound project that is not pinned"
                  disabled={syncAll.state.phase === 'pending' || syncs.busy}
                  onClick={() => {
                    void syncAll.run().then((result) => {
                      if (!result.ok) {
                        toastFailure(result);
                        return;
                      }
                      if (result.data.problems.length > 0) toastPartialFailure(syncAllSummary(result.data), result.notice);
                      else toastResult(result, syncAllSummary(result.data));
                      reload();
                    });
                  }}
                >
                  <FolderSync aria-hidden="true" />
                  {syncAll.state.phase === 'pending' ? 'Syncing all…' : 'Sync all'}
                </WriteButton>
                {refreshButton}
              </>
            }
          />
        </>
      )}

      <BindDialog
        open={bindOpen}
        onOpenChange={setBindOpen}
        environment={environment}
        onBound={reload}
        bound={projects.map((project) => ({
          path: project.path,
          name: displayName(project.path, project.project_id, projectNames),
        }))}
      />
    </section>
  );
}

function syncAllSummary(report: SyncAllReport): string {
  return (
    `Synced ${report.synced.length} project${report.synced.length === 1 ? '' : 's'}.` +
    (report.problems.length > 0 ? ` ${report.problems.length} could not be synced.` : '')
  );
}

/**
 * Client-side filtering over the list `Projects` already loaded — there is no `list
 * --filter`, and the row counts here (a handful, not thousands) do not need one.
 *
 * The mode control is a native `<select>` rather than a kit component: this codebase has
 * no shadcn Select wrapper yet (only `RadioGroup` and `Checkbox` wrap a Radix primitive
 * here), and a native select is the more accessible and more testable choice for a plain
 * single-value dropdown — it needs no extra wiring to be keyboard- and
 * screen-reader-operable. Styled to match `Input` so it does not look like a stray
 * browser default beside it.
 */
function ProjectFilters({
  text,
  onText,
  mode,
  onMode,
  providers,
  onToggleProvider,
}: {
  text: string;
  onText: (value: string) => void;
  mode: BindMode | 'all';
  onMode: (value: BindMode | 'all') => void;
  providers: ReadonlySet<BindProvider>;
  onToggleProvider: (provider: BindProvider, checked: boolean) => void;
}) {
  return (
    <div className="flex flex-wrap items-end gap-4 rounded-md border border-border p-3">
      <div className="grid gap-1.5">
        <Label htmlFor="project-filter-text">Filter by name or path</Label>
        <Input
          id="project-filter-text"
          value={text}
          onChange={(event) => onText(event.target.value)}
          placeholder="e.g. my-project or /repo/my-project"
          className="w-64"
        />
      </div>

      <div className="grid gap-1.5">
        <Label htmlFor="project-filter-mode">Mode</Label>
        <select
          id="project-filter-mode"
          value={mode}
          onChange={(event) => onMode(event.target.value as BindMode | 'all')}
          className="h-9 rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-xs outline-none transition-[color,box-shadow] focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50 dark:bg-input/30"
        >
          <option value="all">All modes</option>
          {MODES.map((candidate) => (
            <option key={candidate} value={candidate}>
              {MODE_LABELS[candidate]}
            </option>
          ))}
        </select>
      </div>

      {/* A `role="group"` rather than a `<fieldset>`: a `<legend>` is laid out by the
          browser's fieldset rules and would not sit on the same baseline as the two `Label`s
          beside it. `h-9` puts the checkboxes on the input's centre line. */}
      <div role="group" aria-labelledby="project-filter-providers" className="grid gap-1.5">
        <Label id="project-filter-providers" asChild>
          <span>Providers</span>
        </Label>
        <div className="flex h-9 flex-wrap items-center gap-3">
          {PROVIDERS.map((provider) => (
            <div key={provider} className="flex items-center gap-2">
              <Checkbox
                id={`filter-provider-${provider}`}
                checked={providers.has(provider)}
                onCheckedChange={(checked) => onToggleProvider(provider, checked === true)}
              />
              <Label htmlFor={`filter-provider-${provider}`}>{PROVIDER_LABELS[provider]}</Label>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

/**
 * Bind a new project: choose a directory in the main process, pick providers and a mode,
 * confirm.
 *
 * The renderer never types or constructs a path — `chooseProjectDirectory()` opens the
 * native picker in the main process, and `{ chosen: false }` means the user dismissed it:
 * nothing is shown and nothing changes. `providers` stays omitted from the request until the
 * user checks something, so the CLI's own default stays authoritative there — this dialog
 * never invents a provider default of its own. `mode` is different: the app *does* have an
 * opinion (`RECOMMENDED_MODE`), so the radio starts pre-selected on it and the choice — link
 * or whatever the user switches to — is always sent, never omitted.
 */
function BindDialog({
  open,
  onOpenChange,
  environment,
  onBound,
  bound: boundProjects,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  environment: EnvironmentReport | null;
  onBound: () => void;
  /** The projects already bound, from the list on screen — a directory among them is refused. */
  bound: readonly BoundDirectory[];
}) {
  const [path, setPath] = useState<string | null>(null);
  const [name, setName] = useState('');
  const [providers, setProviders] = useState<ReadonlySet<BindProvider>>(new Set());
  const [mode, setMode] = useState<BindMode>(RECOMMENDED_MODE);
  const choose = useAction(
    () => window.devteam.chooseProjectDirectory(),
    // A picker that could not open is the same as one the user dismissed.
    () => ({ chosen: false }) as const,
  );
  const bind = useAction(() => {
    if (path === null) throw new Error('bind requested with no directory chosen');
    const trimmedName = name.trim();
    return window.devteam.bindProject({
      path,
      ...(providers.size > 0 ? { providers: Array.from(providers) } : {}),
      mode,
      // An empty field means "no name" — the fallback to the directory's basename lives at
      // render time (`displayName`), not here, so an empty string is never what gets
      // stored. See `BindRequest.name`'s doc comment in `shared/api.ts`.
      ...(trimmedName !== '' ? { name: trimmedName } : {}),
    });
  });

  // ── a v2 install in the chosen directory ─────────────────────────────────────
  //
  // Asked as soon as a directory is chosen: `migrate`'s plan writes nothing, and it is the
  // one question that tells a v2 install (in either shape) from a fresh directory. Exit 2
  // is "no v2 install here" — the ordinary bind applies. A plan means the Bind button
  // would only be refused, so the dialog offers the migration instead.
  const [detection, setDetection] = useState<{
    readonly path: string;
    readonly result: OperationResult<MigrationPlan> | null;
  } | null>(null);
  const detectionFor = useRef<string | null>(null);
  const [reviewing, setReviewing] = useState(false);

  function migrateRequest(): MigrateRequest {
    if (path === null) throw new Error('migration requested with no directory chosen');
    const trimmedName = name.trim();
    return {
      path,
      ...(providers.size > 0 ? { providers: Array.from(providers) } : {}),
      mode,
      ...(trimmedName !== '' ? { name: trimmedName } : {}),
    };
  }
  // The reviewed plan is fetched with the options on screen, so what Migrate runs is what
  // the user just read.
  const review = useAction(() => window.devteam.planMigration(migrateRequest()));
  const migrate = useAction(() => window.devteam.applyMigration(migrateRequest()));

  function chooseDirectory() {
    void choose.run().then((choice) => {
      // `{ chosen: false }` is a dismissed picker, not an error — say nothing, change
      // nothing, leave any previously chosen path (and name) as it was.
      if (!choice.chosen) return;
      setPath(choice.path);
      setName(basename(choice.path));
      setReviewing(false);
      review.reset();
      migrate.reset();
      bind.reset();
      // Already bound: refused on the spot, so nothing is asked of the CLI.
      if (boundDirectory(choice.path, boundProjects) === undefined) void detect(choice.path);
    });
  }

  async function detect(chosen: string) {
    detectionFor.current = chosen;
    setDetection({ path: chosen, result: null });
    const result = await window.devteam
      .planMigration({ path: chosen })
      .catch((): OperationResult<MigrationPlan> => ({
        ok: false,
        kind: 'unavailable',
        message: 'the app could not ask whether this directory has a v2 install',
        exitCode: null,
        command: 'devteam migrate',
        durationMs: 0,
      }));
    // A slower answer for a directory the user has since replaced is dropped.
    if (detectionFor.current === chosen) setDetection({ path: chosen, result });
  }

  function resetForm() {
    setPath(null);
    setName('');
    setProviders(new Set());
    setMode(RECOMMENDED_MODE);
    setDetection(null);
    detectionFor.current = null;
    setReviewing(false);
    choose.reset();
    bind.reset();
    review.reset();
    migrate.reset();
  }

  function close() {
    if (bind.state.phase === 'pending' || migrate.state.phase === 'pending') return;
    resetForm();
    onOpenChange(false);
  }

  // Reset on every **open**, not only on close: the parent can flip `open` without going
  // through `close()` above, and a dialog that stayed mounted with `bind.state.phase ===
  // 'done'` reopened still showing the last "Bound …" result instead of a fresh form. Keyed
  // on `open` alone: a reset is idempotent, so running it on an already-blank form (the
  // ordinary first-open case) costs nothing.
  useEffect(() => {
    if (open) resetForm();
    // Keyed on `open` alone, deliberately: `resetForm` is a fresh closure every render
    // and is not itself part of what should re-trigger this effect — see `UpgradeDialog`'s
    // identical `[open, projectId]` effect above for the same reasoning.
  }, [open]);

  const bound = bind.state.phase === 'done' && bind.state.result.ok ? bind.state.result.data : null;
  const boundName = name.trim() !== '' ? name.trim() : path !== null ? basename(path) : '';

  // A directory that is, or sits inside, a bound project. The CLI resolves a sub-directory to
  // its project root, so binding one would re-bind that project rather than add a new one.
  const alreadyBound = path !== null ? boundDirectory(path, boundProjects) : undefined;
  const detected = detection !== null && detection.path === path ? detection.result : null;
  const checking = path !== null && alreadyBound === undefined && detected === null;
  // exit 2 is the CLI's "no v2 install to migrate" — anything else that failed is a real
  // problem with this directory, and binding would fail on it too.
  const notV2 = detected !== null && !detected.ok && detected.exitCode === 2;
  const v2 = detected !== null && detected.ok ? detected.data : null;
  const detectionProblem = detected !== null && !detected.ok && !notV2 ? detected : null;
  const reviewed = review.state.phase === 'done' && review.state.result.ok ? review.state.result.data : null;
  const migrated = migrate.state.phase === 'done' && migrate.state.result.ok ? migrate.state.result.data : null;

  return (
    <Dialog open={open} onOpenChange={(next) => (next ? onOpenChange(true) : close())}>
      <DialogContent className="sm:max-w-xl">
        <DialogHeader>
          <DialogTitle>Bind a project</DialogTitle>
          <DialogDescription>Choose a directory, then confirm which providers and mode to bind it with.</DialogDescription>
        </DialogHeader>

        {/* The body scrolls and the header and footer stay: the dialog never runs past the
            window, and Bind / Migrate is always on screen. */}
        <DialogBody>
        {bound !== null ? (
          <BindResultSummary report={bound} name={boundName} />
        ) : migrated !== null ? (
          <MigrationReportSummary report={migrated} name={boundName} />
        ) : reviewing ? (
          <div className="space-y-3">
            {review.state.phase !== 'done' ? <Loading what="devteam migrate (plan)" /> : null}
            {review.state.phase === 'done' && !review.state.result.ok ? <Problem problem={review.state.result} /> : null}
            {reviewed !== null ? <MigrationPlanSummary plan={reviewed} /> : null}
            {migrate.state.phase === 'done' && !migrate.state.result.ok ? <Problem problem={migrate.state.result} /> : null}
            {migrate.state.phase === 'done' ? <Notice result={migrate.state.result} /> : null}
          </div>
        ) : (
          <div className="space-y-4">
            {path === null ? (
              <div className="space-y-2">
                <Button type="button" variant="outline" size="sm" onClick={chooseDirectory}>
                  Choose directory…
                </Button>
                <p className="font-mono text-xs text-muted-foreground">No directory chosen yet.</p>
              </div>
            ) : (
              // Colour is never the only signal: the icon and the word "chosen" carry the
              // same fact for a colour-blind user, and both are in the accessible name a
              // screen reader announces — the border alone would tell neither. The change
              // control sits inside the box it changes, instead of a line of its own above it.
              <div
                className={cn(
                  'flex items-center gap-2 rounded-md border py-1.5 pr-1.5 pl-3 text-sm',
                  alreadyBound === undefined
                    ? 'border-green-600 bg-green-50 text-green-900 dark:border-green-500 dark:bg-green-950 dark:text-green-200'
                    : 'border-destructive bg-destructive/10 text-destructive',
                )}
              >
                {alreadyBound === undefined ? (
                  <CheckCircle2 className="size-4 shrink-0" aria-hidden="true" />
                ) : (
                  <AlertTriangle className="size-4 shrink-0" aria-hidden="true" />
                )}
                <span className="min-w-0 flex-1 truncate" title={path}>
                  {alreadyBound === undefined ? 'Directory chosen: ' : 'Already bound: '}
                  <span className="font-mono text-xs">{path}</span>
                </span>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="h-7 shrink-0"
                  aria-label="Choose a different directory"
                  onClick={chooseDirectory}
                >
                  Change…
                </Button>
              </div>
            )}

            {alreadyBound !== undefined ? (
              <p role="alert" className="text-sm text-destructive">
                {normalizeDirectory(alreadyBound.path) === normalizeDirectory(path ?? '')
                  ? `This project is already bound as ${alreadyBound.name}.`
                  : `This directory is inside ${alreadyBound.name}, which is already bound.`}{' '}
                Choose a different directory.
              </p>
            ) : null}
            {checking ? (
              <p className="text-xs text-muted-foreground" aria-live="polite">
                Checking whether this directory already has dev-team-agents…
              </p>
            ) : null}
            {v2 !== null ? <V2Detected plan={v2} /> : null}
            {detectionProblem !== null ? <Problem problem={detectionProblem} /> : null}

            {/* Nothing but the picker until there is a directory to bind — providers and a
                mode asked for decisions about nothing yet. */}
            {path !== null && alreadyBound === undefined ? (
              <>
                <div className="grid gap-2">
                  <Label htmlFor="bind-project-name">Project name</Label>
                  <Input
                    id="bind-project-name"
                    value={name}
                    onChange={(event) => setName(event.target.value)}
                    placeholder={basename(path)}
                  />
                  <p className="text-xs text-muted-foreground">
                    Only shown in this app. Clear it to use the directory name.
                  </p>
                </div>

                <fieldset className="space-y-2">
                  <legend className="text-sm font-medium">Providers</legend>
                  <p className="text-xs text-muted-foreground">Leave all unchecked to use the CLI&apos;s own default.</p>
                  <div className="flex flex-wrap gap-x-5 gap-y-2">
                  {PROVIDERS.map((provider) => (
                    <div key={provider} className="flex items-center gap-2">
                      <Checkbox
                        id={`provider-${provider}`}
                        checked={providers.has(provider)}
                        onCheckedChange={(checked) => {
                          setProviders((current) => {
                            const next = new Set(current);
                            if (checked === true) next.add(provider);
                            else next.delete(provider);
                            return next;
                          });
                        }}
                      />
                      <Label htmlFor={`provider-${provider}`}>{PROVIDER_LABELS[provider]}</Label>
                    </div>
                  ))}
                  </div>
                </fieldset>

                <fieldset className="space-y-2">
                  <legend className="text-sm font-medium">Mode</legend>
                  {/* Two columns of option cards: the same four choices and their consequences
                      in half the height, and the whole card is the click target. */}
                  <RadioGroup
                    value={mode}
                    onValueChange={(value) => setMode(value as BindMode)}
                    className="grid gap-2 sm:grid-cols-2"
                  >
                    {MODES.map((candidate) => (
                      <label
                        key={candidate}
                        htmlFor={`mode-${candidate}`}
                        className={cn(
                          'flex cursor-pointer items-start gap-2 rounded-md border px-3 py-2 transition-colors hover:bg-accent/50',
                          mode === candidate ? 'border-primary bg-accent/40' : 'border-border',
                        )}
                      >
                        <RadioGroupItem
                          value={candidate}
                          id={`mode-${candidate}`}
                          // Named by the title alone and described by the consequence — the
                          // wrapping <label> would otherwise read both as the name.
                          aria-labelledby={`mode-${candidate}-label`}
                          aria-describedby={`mode-${candidate}-description`}
                          className="mt-0.5"
                        />
                        <span className="space-y-0.5">
                          <span id={`mode-${candidate}-label`} className="block text-sm font-medium leading-none">
                            {MODE_LABELS[candidate]}
                            {candidate === RECOMMENDED_MODE ? ' (recommended)' : ''}
                          </span>
                          <span id={`mode-${candidate}-description`} className="block text-xs text-muted-foreground">
                            {MODE_DESCRIPTIONS[candidate]}
                          </span>
                        </span>
                      </label>
                    ))}
                  </RadioGroup>
                </fieldset>
              </>
            ) : null}

            {bind.state.phase === 'done' && !bind.state.result.ok ? <Problem problem={bind.state.result} /> : null}
            {bind.state.phase === 'done' ? <Notice result={bind.state.result} /> : null}
          </div>
        )}
        </DialogBody>

        <DialogFooter>
          {reviewing && migrated === null ? (
            <Button variant="outline" disabled={migrate.state.phase === 'pending'} onClick={() => setReviewing(false)}>
              Back
            </Button>
          ) : (
            <Button
              variant="outline"
              disabled={bind.state.phase === 'pending' || migrate.state.phase === 'pending'}
              onClick={close}
            >
              {bound || migrated ? 'Close' : 'Cancel'}
            </Button>
          )}
          {bound || migrated ? (
            <Button onClick={close}>Done</Button>
          ) : v2 !== null && reviewing ? (
            <WriteButton
              command="migrate"
              environment={environment}
              tooltip="Quarantine the v2 framework, keep its memory, bind, and take the old paths out of git's index"
              disabled={reviewed === null || migrate.state.phase === 'pending'}
              onClick={() => {
                void migrate.run().then((result) => {
                  if (result.ok) onBound();
                });
              }}
            >
              {migrate.state.phase === 'pending' ? 'Migrating…' : 'Migrate'}
            </WriteButton>
          ) : v2 !== null ? (
            <WriteButton
              command="migrate"
              environment={environment}
              tooltip="Show exactly what the migration will do before anything changes"
              onClick={() => {
                setReviewing(true);
                void review.run();
              }}
            >
              Review migration
            </WriteButton>
          ) : (
            <WriteButton
              command="bind"
              environment={environment}
              disabled={
                path === null ||
                alreadyBound !== undefined ||
                checking ||
                detectionProblem !== null ||
                bind.state.phase === 'pending'
              }
              onClick={() => {
                void bind.run().then((result) => {
                  if (result.ok) onBound();
                });
              }}
            >
              {bind.state.phase === 'pending' ? 'Binding…' : 'Bind'}
            </WriteButton>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

const V2_LAYOUT_LABELS: Record<string, string> = {
  root: 'in .dev-team-agents/',
  'pre-root': 'in .claude/dev-team-agents/ (pre-v2.1.0)',
};

function v2Label(plan: { readonly layout: string; readonly install_dir: string }): string {
  return V2_LAYOUT_LABELS[plan.layout] ?? `in ${plan.install_dir}/`;
}

/** Shown as soon as the chosen directory turns out to hold a v2 install. */
function V2Detected({ plan }: { plan: MigrationPlan }) {
  return (
    <Alert>
      <AlertTriangle aria-hidden="true" />
      <AlertTitle>dev-team-agents v2 found</AlertTitle>
      <AlertDescription>
        {/* Two lines at most (reuse guideline `app_support_copy`): what happens, what to do.
            The quarantine, the kept memory and the untracked paths are itemised in the plan. */}
        <p>
          Found {v2Label(plan)}. It will be migrated, not bound — nothing is deleted. Review the plan first.
        </p>
      </AlertDescription>
    </Alert>
  );
}

/** A long path list, collapsed: a v2 install commits one link per skill. */
function PathList({ title, paths }: { title: string; paths: readonly string[] }) {
  if (paths.length === 0) return null;
  return (
    <details>
      <summary className="cursor-pointer font-medium">
        {title} ({paths.length})
      </summary>
      <ul className="mt-1 max-h-40 list-inside list-disc overflow-y-auto font-mono text-xs text-muted-foreground">
        {paths.map((path) => (
          <li key={path}>{path}</li>
        ))}
      </ul>
    </details>
  );
}

function MigrationPlanSummary({ plan }: { plan: MigrationPlan }) {
  const untrack = [...plan.git_tracked, ...plan.git_tracked_artifacts];
  return (
    <div className="space-y-2 text-sm">
      <p>
        v2 install {v2Label(plan)} · providers {plan.providers.join(', ') || '(detected)'} · mode {plan.mode}
      </p>
      <div>
        <p className="font-medium">What the migration does:</p>
        <ul className="list-inside list-disc text-xs text-muted-foreground">
          {plan.actions.map((action, index) => (
            <li key={index}>{action}</li>
          ))}
        </ul>
      </div>
      <PathList title="Leaves git's index (the files stay on disk, nothing is committed)" paths={untrack} />
    </div>
  );
}

/**
 * What the migration did, and what is left for the user: one commit. The untracked paths
 * are the whole reason this is its own summary — they are staged deletions in `git status`,
 * and a user who did not expect them would think something went wrong.
 */
function MigrationReportSummary({ report, name }: { report: MigrationReport; name: string }) {
  return (
    <div className="space-y-2 text-sm">
      <div className="flex items-center gap-2 text-green-700 dark:text-green-400">
        <CheckCircle2 className="size-4 shrink-0" aria-hidden="true" />
        <p className="font-medium">
          {name} is migrated and bound (version {report.version}).
        </p>
      </div>
      {report.quarantine_dir !== null ? (
        <p>
          The old framework is in <span className="font-mono text-xs">{report.quarantine_dir}</span>.
        </p>
      ) : null}
      {report.memory_moved.map((move) => (
        <p key={move.from}>
          Memory kept: <span className="font-mono text-xs">{move.from}</span> →{' '}
          <span className="font-mono text-xs">{move.to}</span>. Upgrade the project from its row to move it into the
          store.
        </p>
      ))}
      {report.context_paths_added.length > 0 ? (
        <p>
          Agents now also read <span className="font-mono text-xs">{report.context_paths_added.join(', ')}</span>.
        </p>
      ) : null}
      {report.untracked.length > 0 ? (
        <p>
          {report.untracked.length} old path{report.untracked.length === 1 ? '' : 's'} left git&apos;s index. Review
          them with <span className="font-mono text-xs">git status</span> and commit.
        </p>
      ) : null}
      {report.untrack_problem !== null ? (
        <p className="text-amber-700 dark:text-amber-400">Nothing was untracked: {report.untrack_problem}.</p>
      ) : null}
      <PathList title="Removed from git's index" paths={report.untracked} />
    </div>
  );
}

/**
 * `merged_project_files` is repeated here in plain language, not just listed: a bind that
 * silently dirties the working tree is discovered days later from `git status`.
 */
/**
 * What `bind` adopted from a v2 `preferences.json`. Worth a line of its own: those values
 * had silently stopped applying, and the file the user may remember editing is now gone
 * from the project — the sentence says where it went.
 */
function PreferencesImportSummary({ report }: { report: PreferencesImport }) {
  if (report.problem !== null) {
    return (
      <p className="text-amber-700 dark:text-amber-400">
        Preferences in <span className="font-mono text-xs">{report.source}</span> were not imported: {report.problem}.
      </p>
    );
  }
  const count = report.imported.length;
  return (
    <div className="space-y-1">
      <p>
        {count === 0
          ? 'The old preferences file held nothing new for this project.'
          : `${count} preference${count === 1 ? ' was' : 's were'} imported from the old preferences file.`}{' '}
        The file was moved out of the project; edit these values from the project&apos;s settings from now on.
      </p>
      {report.conflicts.length > 0 ? (
        <p className="text-xs text-muted-foreground">
          Kept this project&apos;s current value for: <span className="font-mono">{report.conflicts.join(', ')}</span>.
        </p>
      ) : null}
      {report.ignored.length > 0 ? (
        <p className="text-xs text-muted-foreground">
          Not imported: <span className="font-mono">{report.ignored.map((item) => `${item.key} (${item.reason})`).join(', ')}</span>.
        </p>
      ) : null}
    </div>
  );
}

function BindResultSummary({ report, name }: { report: BindReport | null; name: string }) {
  if (report === null) return null;
  return (
    <div className="space-y-2 text-sm">
      <p>
        <strong className="font-semibold">{name}</strong> is bound — version {report.version}, mode {report.mode}.
      </p>
      {report.preferences_import != null ? <PreferencesImportSummary report={report.preferences_import} /> : null}
      {report.merged_project_files.length > 0 ? (
        <div>
          <p className="font-medium">
            These files were merged into the project&apos;s own config — commit them yourself:
          </p>
          <ul className="list-inside list-disc font-mono text-xs text-muted-foreground">
            {report.merged_project_files.map((path) => (
              <li key={path}>{path}</li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}
