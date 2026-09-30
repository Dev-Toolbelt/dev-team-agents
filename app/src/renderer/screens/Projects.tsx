import { useEffect, useRef, useState } from 'react';
import { AlertTriangle, CheckCircle2, ChevronRight } from 'lucide-react';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Hint } from '@/components/ui/tooltip';
import { Empty, Loading, Problem } from '../Problem.js';
import { ProjectSettings } from './ProjectSettings.js';
import { useAction, useOperation } from '../useOperation.js';
import { isWithheld, type Withheld } from '../writeActionGating.js';
import type {
  BindMode,
  BindProvider,
  BindReport,
  EnvironmentReport,
  PreferencesImport,
  ProjectRecord,
  SyncAllReport,
  UnbindReport,
  UpgradePlan,
  UpgradeReport,
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
const MODE_DESCRIPTIONS: Record<BindMode, string> = {
  auto: 'Detects whether this system supports symlinks and behaves like Link or Copy accordingly.',
  link: 'Framework updates reach this project automatically — no extra step needed.',
  copy: 'For Windows systems without symlink permission. Requires running sync by hand after every update.',
  vendored: 'Also copies the framework in, but commits it into this project’s own repository.',
};

/**
 * The last path segment, POSIX or Windows — the picker can hand back either. Falls back
 * to the whole string on the degenerate input a directory picker never actually returns
 * (empty, or all separators), so a caller always has something to render.
 */
function basename(path: string): string {
  const trimmed = path.replace(/[/\\]+$/, '');
  const segments = trimmed.split(/[/\\]/);
  const last = segments[segments.length - 1];
  return last !== undefined && last !== '' ? last : path;
}

/**
 * The name shown for a project: its stored name, or the directory's own basename.
 *
 * The fallback is load-bearing, not cosmetic — see `DevteamBridge.projectNames`'s doc
 * comment in `shared/api.ts`. It applies identically to a project this app never had the
 * chance to name (bound from the terminal) and one bound here and left unnamed, so
 * **no row anywhere in this screen ever renders a bare UUID**.
 */
function displayName(path: string, projectId: string, names: Readonly<Record<string, string>>): string {
  return names[projectId] ?? basename(path);
}

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
 * Whether a project resolves to the store's current version.
 *
 * Nothing at all when the store has no current version: "outdated" relative to nothing is
 * a claim the payload cannot support. The icon is never the only signal — the tooltip text
 * is also the accessible name, so a colour-blind or screen-reader user gets the same fact.
 */
function VersionState({ resolvesTo, current }: { resolvesTo: string; current: string | null }) {
  if (current === null) return null;
  if (resolvesTo === current) {
    const label = `Up to date — the store's current version is ${current}.`;
    return (
      <Hint content={label}>
        <span role="img" aria-label={label} className="inline-flex text-green-600 dark:text-green-500">
          <CheckCircle2 className="size-4" aria-hidden="true" />
        </span>
      </Hint>
    );
  }
  const label = `Outdated — the store's current version is ${current}.`;
  return (
    <Hint content={label}>
      <span role="img" aria-label={label} className="inline-flex text-amber-600 dark:text-amber-500">
        <AlertTriangle className="size-4" aria-hidden="true" />
      </span>
    </Hint>
  );
}

/**
 * A write button that knows how to disable itself.
 *
 * Centralised so no row can forget the withheld check — item 5 of the brief is "the UI must
 * say why in plain language and must not present the action as available", and a button
 * that has to remember to ask `isWithheld` on its own is a button that eventually doesn't.
 */
function WriteButton({
  command,
  environment,
  tooltip,
  children,
  ...props
}: {
  command: string;
  environment: EnvironmentReport | null;
  /** What the action does, shown on hover. A withheld reason replaces it — that is the more urgent fact. */
  tooltip?: string;
} & React.ComponentProps<typeof Button>) {
  // `environment === null` means the report has not arrived yet, not that nothing is
  // withheld — so it fails CLOSED. Reading an unanswered precondition as "no objection"
  // would enable every write action during the window before the app has checked whether
  // it could even write its own schema declaration, which is exactly the window in which
  // it must not write. The reason is worded as a wait, not a refusal, because it is one.
  const gate: Withheld =
    environment === null
      ? { withheld: true, reason: 'the app has not finished checking its own preconditions' }
      : isWithheld(environment.withheld, command);
  if (gate.withheld) {
    // The tooltip hangs on a wrapper, not on the button: a `disabled` button receives no
    // mouse events, so a tooltip on it is never triggered. The reason also goes into
    // `aria-label`, because a disabled control is not focusable and a tooltip a screen
    // reader never reaches is not an explanation. `EnvironmentBanner` in `App.tsx` states
    // the same reason once, visibly, for the sighted case — this is the per-control echo.
    return (
      <Hint content={`Withheld: ${gate.reason}`}>
        <span className="inline-flex">
          <Button
            {...props}
            disabled
            // The visible label when it is a plain string, and the CLI subcommand otherwise.
            // Not `String(children)`: a ReactNode stringifies to "[object Object]", which is
            // how a screen reader would have been told the reason.
            aria-label={`${typeof children === 'string' ? children : command} — withheld: ${gate.reason}`}
          >
            {children}
          </Button>
        </span>
      </Hint>
    );
  }
  const button = <Button {...props}>{children}</Button>;
  if (tooltip === undefined) return button;
  // Wrapped in a span for the same reason as above: while pending the button is disabled
  // and would otherwise swallow the hover that shows the tooltip.
  return (
    <Hint content={tooltip}>
      <span className="inline-flex">{button}</span>
    </Hint>
  );
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
}: {
  environment: EnvironmentReport | null;
  /** Whether this tab is the visible one. The tab stays mounted (see `App.tsx`), so it refetches on return. */
  active?: boolean;
  /**
   * A notification asked to show this project. The nonce makes a second request for the
   * same project a new request rather than an unchanged prop.
   */
  openRequest?: { readonly projectId: string; readonly nonce: number } | null;
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
    void window.devteam.projectNames().then((names) => {
      if (live) setProjectNames(names);
    });
    return () => {
      live = false;
    };
  }, [namesNonce]);
  function reload() {
    reloadList();
    setNamesNonce((n) => n + 1);
  }

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

  // Opened only when no settings screen is: one that is open may hold unsaved edits, and
  // its own "leave with unsaved changes?" guard must not be bypassed by a notification.
  useEffect(() => {
    if (openRequest === null) return;
    setOpenSettings((current) => current ?? openRequest.projectId);
  }, [openRequest?.nonce]);

  // Keeping the tab mounted preserves unsaved settings, but it also stopped the refetch a
  // remount used to give for free; returning to the tab asks `list` again.
  const wasActive = useRef(active);
  useEffect(() => {
    if (active && !wasActive.current) reload();
    wasActive.current = active;
  });

  if (state.phase === 'loading') return <Loading what="devteam list" />;
  if (!state.result.ok) return <Problem problem={state.result} />;

  const { current, projects } = state.result.data;

  const settingsFor = openSettings === null ? undefined : projects.find((project) => project.project_id === openSettings);
  if (settingsFor !== undefined) {
    return (
      <ProjectSettings
        project={settingsFor}
        name={displayName(settingsFor.path, settingsFor.project_id, projectNames)}
        environment={environment}
        active={active}
        onBack={() => {
          setReturnFocusTo(settingsFor.project_id);
          setOpenSettings(null);
          reload();
        }}
      />
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

  return (
    <section aria-labelledby="projects-heading" className="space-y-4">
      <header className="flex flex-wrap items-baseline justify-between gap-4">
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
          {/* A reload no longer replaces the table — see `useOperation`'s `refreshing`. This
              is how the refresh stays visible without unmounting the row that a write action
              just wrote a notice into. `aria-live` so it is announced rather than only seen. */}
          <p aria-live="polite" className="text-xs text-muted-foreground">
            {refreshing ? 'Refreshing the project list…' : null}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {projects.length > 0 ? (
            <WriteButton
              command="sync"
              environment={environment}
              variant="outline"
              size="sm"
              tooltip="Re-apply the current store version to every bound project that is not pinned"
              disabled={syncAll.state.phase === 'pending'}
              onClick={() => {
                void syncAll.run().then((result) => {
                  if (result.ok) reload();
                });
              }}
            >
              {syncAll.state.phase === 'pending' ? 'Syncing all…' : 'Sync all'}
            </WriteButton>
          ) : null}
          <WriteButton
            command="bind"
            environment={environment}
            size="sm"
            tooltip="Bind a new project directory to this store"
            onClick={() => setBindOpen(true)}
          >
            Bind…
          </WriteButton>
          <Hint content="Reload the project list from the CLI">
            <Button variant="outline" size="sm" onClick={reload}>
              Refresh
            </Button>
          </Hint>
        </div>
      </header>

      {syncAll.state.phase === 'done' && !syncAll.state.result.ok ? <Problem problem={syncAll.state.result} /> : null}
      {syncAll.state.phase === 'done' && syncAll.state.result.ok ? (
        <SyncAllSummary report={syncAll.state.result.data} />
      ) : null}
      {syncAll.state.phase === 'done' ? <Notice result={syncAll.state.result} /> : null}

      {projects.length === 0 ? (
        <Empty>Nothing is bound yet. Use Bind above to choose a project directory.</Empty>
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
          {/* Announced the same way `refreshing`, above, is — a filter that silently changes
              which rows are on screen is exactly the kind of update a screen reader user
              would otherwise miss entirely. */}
          <p aria-live="polite" className="text-xs text-muted-foreground">
            Showing {filteredProjects.length} of {projects.length} project{projects.length === 1 ? '' : 's'}.
          </p>
          {filteredProjects.length === 0 ? (
            // Distinct from the "nothing is bound yet" empty state above: that one means
            // there is nothing to show the user at all, this one means there is something,
            // just not anything these filters let through — the fix is "loosen a filter",
            // not "go bind a project".
            <Empty>No bound project matches these filters.</Empty>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead scope="col">Project</TableHead>
                  <TableHead scope="col">Version</TableHead>
                  <TableHead scope="col">Mode</TableHead>
                  <TableHead scope="col">Providers</TableHead>
                  <TableHead scope="col">Path</TableHead>
                  <TableHead scope="col">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredProjects.map((project) => (
                  <ProjectRow
                    key={project.project_id}
                    project={project}
                    environment={environment}
                    projectNames={projectNames}
                    current={current}
                    onChanged={reload}
                    onOpenSettings={() => setOpenSettings(project.project_id)}
                  />
                ))}
              </TableBody>
            </Table>
          )}
        </>
      )}

      <BindDialog
        open={bindOpen}
        onOpenChange={setBindOpen}
        environment={environment}
        onBound={() => {
          setBindOpen(false);
          reload();
        }}
      />
    </section>
  );
}

function SyncAllSummary({ report }: { report: SyncAllReport }) {
  return (
    <p className="text-sm text-muted-foreground">
      Synced {report.synced.length} project{report.synced.length === 1 ? '' : 's'}.
      {report.problems.length > 0 ? ` ${report.problems.length} could not be synced.` : ''}
    </p>
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

function settingsButtonId(projectId: string): string {
  return `open-settings-${projectId}`;
}

type RowDialog = 'pin' | 'unbind' | 'upgrade' | null;

/**
 * One bound project's row, plus the dialogs its actions open.
 *
 * Only one dialog is open per row at a time — `dialog` is a single field, not three
 * booleans, so opening one can never leave another half-open behind it.
 */
function ProjectRow({
  project,
  environment,
  projectNames,
  current,
  onChanged,
  onOpenSettings,
}: {
  project: ProjectRecord;
  environment: EnvironmentReport | null;
  projectNames: Readonly<Record<string, string>>;
  current: string | null;
  onChanged: () => void;
  onOpenSettings: () => void;
}) {
  const [dialog, setDialog] = useState<RowDialog>(null);
  const sync = useAction(() => window.devteam.syncProject(project.project_id));
  const name = displayName(project.path, project.project_id, projectNames);

  return (
    <TableRow>
      <TableCell>
        {/* The name only. `project_id` is a UUID that means nothing to the reader and is
            never rendered — `devteam list` in a terminal is where a debugger gets it. The
            name is the way into the project's settings, so it is a real button. */}
        <Hint content="Open this project's settings">
          <button
            type="button"
            id={settingsButtonId(project.project_id)}
            onClick={onOpenSettings}
            className="group inline-flex items-center gap-1 rounded-sm font-medium outline-none hover:text-primary focus-visible:ring-[3px] focus-visible:ring-ring/50"
            aria-label={`${name} — open settings`}
          >
            {name}
            <ChevronRight className="size-3.5 text-muted-foreground transition-transform group-hover:translate-x-0.5 group-hover:text-primary" aria-hidden="true" />
          </button>
        </Hint>
      </TableCell>
      <TableCell>
        <span className="flex items-center gap-2 whitespace-nowrap">
          {project.resolves_to !== null ? (
            <>
              <Badge variant="outline">{project.resolves_to}</Badge>
              <VersionState resolvesTo={project.resolves_to} current={current} />
            </>
          ) : (
            <span className="text-muted-foreground">—</span>
          )}
          {project.pin !== null ? <Badge variant="secondary">pinned {project.pin}</Badge> : null}
        </span>
      </TableCell>
      <TableCell>{project.mode ?? '—'}</TableCell>
      <TableCell>{project.providers.length === 0 ? '—' : project.providers.join(', ')}</TableCell>
      {/* The badge sits outside the truncating span, not inside it. A `truncate` cell
          clipped it at the ellipsis, so the one row that most needed a `missing` badge — a
          long path — was the one row that never showed it. */}
      <TableCell className="font-mono text-xs">
        <span className="flex items-center gap-2">
          <span className="max-w-[24rem] truncate" title={project.path}>
            {project.path}
          </span>
          <PathState exists={project.path_exists} />
        </span>
      </TableCell>
      <TableCell>
        <div className="flex flex-nowrap items-center gap-2 whitespace-nowrap">
          <WriteButton
            command="sync"
            environment={environment}
            variant="outline"
            size="xs"
            tooltip="Re-apply this project's store version to its files"
            disabled={sync.state.phase === 'pending'}
            onClick={() => {
              void sync.run().then((result) => {
                if (result.ok) onChanged();
              });
            }}
          >
            {sync.state.phase === 'pending' ? 'Syncing…' : 'Sync'}
          </WriteButton>
          <WriteButton
            command="pin"
            environment={environment}
            variant="outline"
            size="xs"
            tooltip="Hold this project on a specific version, or release the pin"
            onClick={() => setDialog('pin')}
          >
            Pin…
          </WriteButton>
          <WriteButton
            command="upgrade"
            environment={environment}
            variant="outline"
            size="xs"
            tooltip="Move this project's memory into the store — shows the plan first"
            onClick={() => setDialog('upgrade')}
          >
            Upgrade…
          </WriteButton>
          <WriteButton
            command="unbind"
            environment={environment}
            variant="destructive"
            size="xs"
            tooltip="Remove this project from the store — asks for confirmation first"
            onClick={() => setDialog('unbind')}
          >
            Unbind…
          </WriteButton>
        </div>
        {sync.state.phase === 'done' && !sync.state.result.ok ? (
          <div className="pt-2">
            <Problem problem={sync.state.result} />
          </div>
        ) : null}
        {sync.state.phase === 'done' ? <Notice result={sync.state.result} /> : null}
      </TableCell>

      <PinDialog
        open={dialog === 'pin'}
        onOpenChange={(open) => setDialog(open ? 'pin' : null)}
        projectId={project.project_id}
        name={name}
        currentPin={project.pin}
        onChanged={onChanged}
      />
      <UnbindDialog
        open={dialog === 'unbind'}
        onOpenChange={(open) => setDialog(open ? 'unbind' : null)}
        project={project}
        name={name}
        onUnbound={() => {
          setDialog(null);
          onChanged();
        }}
      />
      <UpgradeDialog
        open={dialog === 'upgrade'}
        onOpenChange={(open) => setDialog(open ? 'upgrade' : null)}
        projectId={project.project_id}
        name={name}
        onApplied={onChanged}
      />
    </TableRow>
  );
}

/** Set or release a pin. `setPin(id, null)` releases it — not `setPin(id, '')`. */
function PinDialog({
  open,
  onOpenChange,
  projectId,
  name,
  currentPin,
  onChanged,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  projectId: string;
  name: string;
  currentPin: string | null;
  onChanged: () => void;
}) {
  const [version, setVersion] = useState('');
  const pin = useAction((v: string | null) => window.devteam.setPin(projectId, v));

  function close() {
    pin.reset();
    setVersion('');
    onOpenChange(false);
  }

  return (
    <Dialog open={open} onOpenChange={(next) => (next ? onOpenChange(true) : close())}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Pin {name}</DialogTitle>
          <DialogDescription>
            {currentPin !== null
              ? `Currently pinned to ${currentPin}. Set a different version, or release the pin to track the store's current version again.`
              : 'Not pinned — this project tracks the store’s current version. Set a version to pin it.'}
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-2">
          <Label htmlFor="pin-version">Version</Label>
          <Input
            id="pin-version"
            value={version}
            onChange={(event) => setVersion(event.target.value)}
            placeholder="e.g. 2.48.0"
          />
        </div>

        {pin.state.phase === 'done' && !pin.state.result.ok ? <Problem problem={pin.state.result} /> : null}
        {pin.state.phase === 'done' && pin.state.result.ok ? (
          <p className="text-sm text-muted-foreground">
            {pin.state.result.data.pin !== null ? `Pinned to ${pin.state.result.data.pin}.` : 'Pin released.'}
          </p>
        ) : null}
        {pin.state.phase === 'done' ? <Notice result={pin.state.result} /> : null}

        <DialogFooter>
          {currentPin !== null ? (
            <Button
              variant="outline"
              disabled={pin.state.phase === 'pending'}
              onClick={() => {
                void pin.run(null).then((result) => {
                  if (result.ok) onChanged();
                });
              }}
            >
              Release pin
            </Button>
          ) : null}
          <Button
            disabled={pin.state.phase === 'pending' || version.trim() === ''}
            onClick={() => {
              void pin.run(version.trim()).then((result) => {
                if (result.ok) onChanged();
              });
            }}
          >
            {pin.state.phase === 'pending' ? 'Setting…' : 'Set pin'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

/**
 * Unbind's explicit confirm step. States what will happen before the destructive action can
 * fire — a single stray click on a row action must not be able to unbind a project.
 */
function UnbindDialog({
  open,
  onOpenChange,
  project,
  name,
  onUnbound,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  project: ProjectRecord;
  name: string;
  onUnbound: () => void;
}) {
  const unbind = useAction(() => window.devteam.unbindProject(project.project_id));

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Unbind {name}?</DialogTitle>
          <DialogDescription>
            This removes the store&apos;s link to <span className="font-mono">{project.path}</span>. Files this store
            manages are quarantined, not deleted; the project&apos;s own files are left alone.
          </DialogDescription>
        </DialogHeader>

        {unbind.state.phase === 'done' && !unbind.state.result.ok ? <Problem problem={unbind.state.result} /> : null}
        {unbind.state.phase === 'done' && unbind.state.result.ok ? (
          <UnbindResultSummary report={unbind.state.result.data} />
        ) : null}
        {unbind.state.phase === 'done' ? <Notice result={unbind.state.result} /> : null}

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          {unbind.state.phase === 'done' && unbind.state.result.ok ? (
            <Button onClick={onUnbound}>Done</Button>
          ) : (
            <Button
              variant="destructive"
              disabled={unbind.state.phase === 'pending'}
              onClick={() => void unbind.run()}
            >
              {unbind.state.phase === 'pending' ? 'Unbinding…' : 'Unbind'}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

/**
 * `quarantined` is the one the user must read — it names where their files went.
 * `unlinked` is ~159 entries on a claude-only bind, so its length is shown, not the list.
 */
/**
 * What a command said on stderr **while succeeding**.
 *
 * `OperationResult.notice` exists because the CLI uses stderr to tell the user something
 * the JSON payload has no field for — `bind` outside a git repository exits 0 with a
 * complete document and warns there that the bind artifacts were added to no ignore file,
 * which is how they get committed by accident. Rendering the payload alone would show a
 * clean success and drop exactly the sentence that mattered. Not `destructive`: the command
 * worked, and styling a warning as a failure teaches the user to ignore both.
 */
function Notice({ result }: { result: { readonly ok: boolean; readonly notice?: string } }) {
  if (!result.ok || result.notice === undefined) return null;
  return (
    <Alert className="mt-2">
      <AlertTitle>The command succeeded and reported this</AlertTitle>
      <AlertDescription>
        <p className="whitespace-pre-wrap font-mono text-xs">{result.notice}</p>
      </AlertDescription>
    </Alert>
  );
}

function UnbindResultSummary({ report }: { report: UnbindReport }) {
  return (
    <div className="space-y-1 text-sm">
      <p>{report.unlinked.length} link{report.unlinked.length === 1 ? '' : 's'} removed.</p>
      {report.quarantined.length > 0 ? (
        <div>
          <p className="font-medium">Quarantined to:</p>
          <ul className="list-inside list-disc font-mono text-xs text-muted-foreground">
            {report.quarantined.map((entry, index) => (
              <li key={index}>{entry.to ?? '(no destination reported)'}</li>
            ))}
          </ul>
        </div>
      ) : null}
      {report.problems.length > 0 ? (
        <p className="text-destructive">{report.problems.length} problem{report.problems.length === 1 ? '' : 's'} reported.</p>
      ) : null}
    </div>
  );
}

/**
 * The two-step upgrade, structurally enforced: `apply` is not offered until `plan` has
 * resolved, and the plan is what shows `collisions`, `git_tracked` and `actions` before
 * anything happens. The plan is fetched automatically on open — it only reads — and the
 * apply step still needs its own explicit click.
 */
function UpgradeDialog({
  open,
  onOpenChange,
  projectId,
  name,
  onApplied,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  projectId: string;
  name: string;
  onApplied: () => void;
}) {
  const plan = useAction(() => window.devteam.planUpgrade(projectId));
  const apply = useAction(() => window.devteam.applyUpgrade(projectId));

  useEffect(() => {
    if (open) {
      void plan.run();
    } else {
      plan.reset();
      apply.reset();
    }
    // `plan`/`apply` are re-created every render (fresh closures from `useAction`), but
    // their `run`/`reset` identities are what would matter here and `reset` is stable;
    // this effect is keyed on the dialog's own open/target, not on those closures.
  }, [open, projectId]);

  const planData = plan.state.phase === 'done' && plan.state.result.ok ? plan.state.result.data : null;
  const nothingToDo = planData !== null && planData.actions.length === 0;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>Upgrade {name}</DialogTitle>
          <DialogDescription>
            Moves this project&apos;s memory into the store and quarantines what it moved. Nothing changes until
            Apply is confirmed below.
          </DialogDescription>
        </DialogHeader>

        {plan.state.phase !== 'done' ? <Loading what="devteam upgrade (plan)" /> : null}
        {plan.state.phase === 'done' && !plan.state.result.ok ? <Problem problem={plan.state.result} /> : null}
        {planData !== null ? <UpgradePlanSummary plan={planData} /> : null}

        {apply.state.phase === 'done' && !apply.state.result.ok ? <Problem problem={apply.state.result} /> : null}
        {apply.state.phase === 'done' && apply.state.result.ok ? (
          <UpgradeReportSummary report={apply.state.result.data} />
        ) : null}
        {apply.state.phase === 'done' ? <Notice result={apply.state.result} /> : null}

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            {apply.state.phase === 'done' && apply.state.result.ok ? 'Close' : 'Cancel'}
          </Button>
          {apply.state.phase === 'done' && apply.state.result.ok ? (
            <Button
              onClick={() => {
                onApplied();
                onOpenChange(false);
              }}
            >
              Done
            </Button>
          ) : (
            <Button
              disabled={planData === null || nothingToDo || apply.state.phase === 'pending'}
              onClick={() => void apply.run()}
              title={nothingToDo ? 'The plan has no actions — there is nothing to apply.' : undefined}
            >
              {apply.state.phase === 'pending' ? 'Applying…' : 'Apply'}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function UpgradePlanSummary({ plan }: { plan: UpgradePlan }) {
  return (
    <div className="space-y-2 text-sm">
      <p>
        Layout {plan.from_layout} → {plan.to_layout} · {plan.files} file{plan.files === 1 ? '' : 's'} · destination{' '}
        <span className="font-mono text-xs">{plan.destination}</span>
      </p>
      {plan.actions.length === 0 ? (
        <p className="text-muted-foreground">The plan has no actions — this project has nothing to upgrade.</p>
      ) : (
        <div>
          <p className="font-medium">Actions:</p>
          <ul className="list-inside list-disc text-xs text-muted-foreground">
            {plan.actions.map((action, index) => (
              <li key={index}>{action}</li>
            ))}
          </ul>
        </div>
      )}
      {plan.collisions.length > 0 ? (
        <div>
          <p className="font-medium text-destructive">Collisions:</p>
          <ul className="list-inside list-disc font-mono text-xs text-destructive">
            {plan.collisions.map((path) => (
              <li key={path}>{path}</li>
            ))}
          </ul>
        </div>
      ) : null}
      {plan.git_tracked.length > 0 ? (
        <div>
          <p className="font-medium">Git-tracked paths this touches:</p>
          <ul className="list-inside list-disc font-mono text-xs text-muted-foreground">
            {plan.git_tracked.map((path) => (
              <li key={path}>{path}</li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}

/**
 * `state_pointer`/`memory_pointer` and `git_tracked` are surfaced because they are exactly
 * what changed on disk and what the user still owes a commit — the same honesty `bind`'s
 * `merged_project_files` needs, for the same reason.
 */
function UpgradeReportSummary({ report }: { report: UpgradeReport }) {
  return (
    <div className="space-y-2 text-sm">
      <p>
        Copied {report.copied} file{report.copied === 1 ? '' : 's'} to{' '}
        <span className="font-mono text-xs">{report.destination}</span>.
      </p>
      {report.quarantined !== null ? (
        <p>
          Quarantined to <span className="font-mono text-xs">{report.quarantined}</span>.
        </p>
      ) : null}
      <p className="font-mono text-xs text-muted-foreground">
        state → {report.state_pointer} · memory → {report.memory_pointer}
      </p>
      {report.git_tracked.length > 0 ? (
        <div>
          <p className="font-medium">Commit these yourself:</p>
          <ul className="list-inside list-disc font-mono text-xs text-muted-foreground">
            {report.git_tracked.map((path) => (
              <li key={path}>{path}</li>
            ))}
          </ul>
        </div>
      ) : null}
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
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  environment: EnvironmentReport | null;
  onBound: () => void;
}) {
  const [path, setPath] = useState<string | null>(null);
  const [name, setName] = useState('');
  const [providers, setProviders] = useState<ReadonlySet<BindProvider>>(new Set());
  const [mode, setMode] = useState<BindMode>(RECOMMENDED_MODE);
  const choose = useAction(() => window.devteam.chooseProjectDirectory());
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

  function resetForm() {
    setPath(null);
    setName('');
    setProviders(new Set());
    setMode(RECOMMENDED_MODE);
    choose.reset();
    bind.reset();
  }

  function close() {
    resetForm();
    onOpenChange(false);
  }

  // Reset on every **open**, not only on close. `onBound` (in `Projects`) closes this
  // dialog by calling the parent's `onOpenChange` directly — the "Done" button's own path
  // — which bypasses `close()` above entirely. Without this effect, `BindDialog` stayed
  // mounted with `bind.state.phase === 'done'` from the previous bind, so pressing
  // "Bind…" again reopened the dialog still showing the last "Bound …" result instead of
  // a fresh form. Keyed on `open` alone: a reset is idempotent, so running it again on an
  // already-blank form (the ordinary first-open case) costs nothing.
  useEffect(() => {
    if (open) resetForm();
    // Keyed on `open` alone, deliberately: `resetForm` is a fresh closure every render
    // and is not itself part of what should re-trigger this effect — see `UpgradeDialog`'s
    // identical `[open, projectId]` effect above for the same reasoning.
  }, [open]);

  const bound = bind.state.phase === 'done' && bind.state.result.ok ? bind.state.result.data : null;
  const boundName = name.trim() !== '' ? name.trim() : path !== null ? basename(path) : '';

  return (
    <Dialog open={open} onOpenChange={(next) => (next ? onOpenChange(true) : close())}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Bind a project</DialogTitle>
          <DialogDescription>Choose a directory, then confirm which providers and mode to bind it with.</DialogDescription>
        </DialogHeader>

        {bound !== null ? (
          <BindResultSummary report={bound} name={boundName} />
        ) : (
          <div className="space-y-4">
            <div className="space-y-2">
              <Button
                type="button"
                variant={path === null ? 'outline' : 'link'}
                size="sm"
                className={path === null ? undefined : 'h-auto px-0'}
                onClick={() => {
                  void choose.run().then((choice) => {
                    // `{ chosen: false }` is a dismissed picker, not an error — say nothing,
                    // change nothing, leave any previously chosen path (and name) as it was.
                    if (choice.chosen) {
                      setPath(choice.path);
                      setName(basename(choice.path));
                    }
                  });
                }}
              >
                {path === null ? 'Choose directory…' : 'Choose a different directory…'}
              </Button>

              {path === null ? (
                <p className="font-mono text-xs text-muted-foreground">No directory chosen yet.</p>
              ) : (
                // Colour is never the only signal: the icon and the word "chosen" carry the
                // same fact for a colour-blind user, and both are in the accessible name a
                // screen reader announces — the border alone would tell neither.
                <div className="flex items-center gap-2 rounded-md border border-green-600 bg-green-50 px-3 py-2 text-sm text-green-900 dark:border-green-500 dark:bg-green-950 dark:text-green-200">
                  <CheckCircle2 className="size-4 shrink-0" aria-hidden="true" />
                  <span>
                    Directory chosen: <span className="font-mono text-xs">{path}</span>
                  </span>
                </div>
              )}
            </div>

            {/* Nothing but the picker until there is a directory to bind — providers and a
                mode asked for decisions about nothing yet. */}
            {path !== null ? (
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
                </fieldset>

                <fieldset className="space-y-2">
                  <legend className="text-sm font-medium">Mode</legend>
                  <RadioGroup value={mode} onValueChange={(value) => setMode(value as BindMode)}>
                    {MODES.map((candidate) => (
                      <div key={candidate} className="flex items-start gap-2">
                        <RadioGroupItem
                          value={candidate}
                          id={`mode-${candidate}`}
                          aria-describedby={`mode-${candidate}-description`}
                          className="mt-1"
                        />
                        <div>
                          <Label htmlFor={`mode-${candidate}`}>
                            {MODE_LABELS[candidate]}
                            {candidate === RECOMMENDED_MODE ? ' (recommended)' : ''}
                          </Label>
                          <p id={`mode-${candidate}-description`} className="text-xs text-muted-foreground">
                            {MODE_DESCRIPTIONS[candidate]}
                          </p>
                        </div>
                      </div>
                    ))}
                  </RadioGroup>
                </fieldset>
              </>
            ) : null}

            {bind.state.phase === 'done' && !bind.state.result.ok ? <Problem problem={bind.state.result} /> : null}
            {bind.state.phase === 'done' ? <Notice result={bind.state.result} /> : null}
          </div>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={close}>
            {bound ? 'Close' : 'Cancel'}
          </Button>
          {bound ? (
            <Button onClick={onBound}>Done</Button>
          ) : (
            <WriteButton
              command="bind"
              environment={environment}
              disabled={path === null || bind.state.phase === 'pending'}
              onClick={() => void bind.run()}
            >
              {bind.state.phase === 'pending' ? 'Binding…' : 'Bind'}
            </WriteButton>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
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
