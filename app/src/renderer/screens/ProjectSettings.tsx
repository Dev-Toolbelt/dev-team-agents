import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { ArrowLeft, CheckCircle2, Info, RotateCcw, Undo2 } from 'lucide-react';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
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
import { Switch } from '@/components/ui/switch';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Hint } from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';
import { SaveBar } from '../SaveBar.js';
import { SELECT_CLASS } from '../formStyles.js';
import { Loading, Problem } from '../Problem.js';
import { ProjectPlugins } from './ProjectPlugins.js';
import { useAction, useOperation } from '../useOperation.js';
import { isWithheld, type Withheld } from '../writeActionGating.js';
import {
  BOOLEAN_SELECT_KEYS,
  FIELD_BY_KEY,
  FIELDS,
  GROUPS,
  crossFieldErrors,
  formatInteger,
  parseDraft,
  sameValue,
  type DraftInput,
  type Field,
  type GroupId,
} from '../preferences/schema.js';
import type {
  EnvironmentReport,
  PreferenceChange,
  PreferenceOrigin,
  PreferenceUpdateReport,
  PreferenceValue,
  ProjectPreferencesView,
  ProjectRecord,
} from '../../shared/api.js';

/** The CLI subcommand the save runs — what `EnvironmentReport.withheld` is keyed by. */
const SAVE_COMMAND = 'prefs set';

type Drafts = Readonly<Record<string, DraftInput>>;

/** One field's state, derived on every render from the loaded values plus the draft. */
interface FieldState {
  readonly original: unknown;
  readonly origin: PreferenceOrigin | undefined;
  /** What a reset falls back to — the cascade without the project layer. `undefined` when unknown. */
  readonly inherited: unknown;
  readonly draft: DraftInput | undefined;
  readonly resetPending: boolean;
  /** The value the field would have after saving, or `undefined` while it cannot be known. */
  readonly effective: unknown;
  /**
   * What the control shows. Separate from `effective` because `null` is a real value here —
   * "Ask on first use", "Auto-detect" — and `effective ?? original` read it as absent, so
   * choosing it snapped the control back to the old value while the save would send `null`.
   */
  readonly display: unknown;
  readonly error: string | null;
  /** The error comes from a rule spanning two fields, not from this field's own input. */
  readonly crossError: boolean;
  readonly changed: boolean;
}

/** A just-saved batch, waiting for the reload that proves it landed. */
interface AwaitingReload {
  readonly written: ReadonlySet<string>;
  readonly before: ProjectPreferencesView;
}

/**
 * Every preference of one bound project, grouped and validated, written to **that
 * project's layer only** (`prefs set --scope project`).
 *
 * Edits are staged, not written per keystroke: each write is a CLI process that also
 * re-materialises `resolved/preferences.json`, and a half-applied form is harder to reason
 * about than an explicit Save. A failed save stops at the failing key and says which keys
 * were written before it — the batch is not a transaction and the screen does not pretend
 * otherwise.
 */
export function ProjectSettings({
  project,
  name,
  environment,
  active,
  onBack,
}: {
  project: ProjectRecord;
  name: string;
  environment: EnvironmentReport | null;
  /** Whether the tab holding this screen is the visible one; it stays mounted while hidden. */
  active: boolean;
  onBack: () => void;
}) {
  const projectId = project.project_id;
  const { state, refreshing, reload } = useOperation(() => window.devteam.projectPreferences(projectId), [projectId]);
  const [drafts, setDrafts] = useState<Drafts>({});
  const [resets, setResets] = useState<ReadonlySet<string>>(new Set());
  const [confirmLeave, setConfirmLeave] = useState(false);
  const [tab, setTab] = useState<'preferences' | 'plugins'>('preferences');
  // The Plugins tab loads (and runs each plugin's status script) on first visit, then stays
  // mounted so switching tabs never discards a half-edited config form.
  const [pluginsVisited, setPluginsVisited] = useState(false);
  const [pluginDirty, setPluginDirty] = useState(0);
  const onPluginDirty = useCallback((count: number) => setPluginDirty(count), []);
  const [saved, setSaved] = useState<PreferenceUpdateReport | null>(null);
  const [awaiting, setAwaiting] = useState<AwaitingReload | null>(null);
  const headingRef = useRef<HTMLHeadingElement>(null);
  const save = useAction((changes: readonly PreferenceChange[]) =>
    window.devteam.updateProjectPreferences(projectId, changes),
  );

  const loaded = state.phase === 'done' && state.result.ok ? state.result.data : null;

  // Focus moves to the screen that just replaced the list, or a keyboard user is left on <body>.
  useEffect(() => {
    headingRef.current?.focus();
  }, []);

  // The section the user is reading, highlighted in the side nav: the last one whose top
  // has scrolled past a line near the top of the viewport, or the last one at the bottom
  // of the page (a short final section never reaches that line). Listened for in the
  // capture phase because the scrolling element is an ancestor, not the window.
  const [activeSection, setActiveSection] = useState<string>(GROUPS[0]?.id ?? '');
  useEffect(() => {
    const update = () => {
      const sections = GROUPS.map((group) => document.getElementById(`settings-${group.id}`)).filter(
        (element): element is HTMLElement => element !== null,
      );
      if (sections.length === 0) return;
      const scroller = sections[0]!.closest('main') ?? document.scrollingElement ?? null;
      // "At the bottom" only means something when there is anything to scroll.
      const atBottom =
        scroller != null &&
        scroller.scrollHeight > scroller.clientHeight &&
        scroller.scrollTop + scroller.clientHeight >= scroller.scrollHeight - 2;
      const current = atBottom
        ? sections[sections.length - 1]!
        : (sections.filter((section) => section.getBoundingClientRect().top <= 140).pop() ?? sections[0]!);
      setActiveSection(current.id.replace(/^settings-/, ''));
    };
    update();
    document.addEventListener('scroll', update, { capture: true, passive: true });
    return () => document.removeEventListener('scroll', update, { capture: true });
  }, [loaded !== null]);

  // A saved draft is dropped only once the reload has brought the value back from the CLI,
  // so the form never flashes the old value between the save and the reload.
  useEffect(() => {
    if (awaiting === null || loaded === null || loaded === awaiting.before) return;
    setDrafts((previous) => Object.fromEntries(Object.entries(previous).filter(([key]) => !awaiting.written.has(key))));
    setResets((previous) => new Set([...previous].filter((key) => !awaiting.written.has(key))));
    setAwaiting(null);
  }, [loaded, awaiting]);

  const fieldStates = useMemo(() => {
    const states = new Map<string, FieldState>();
    if (loaded === null) return states;
    const effective: Record<string, PreferenceValue | undefined> = {};
    for (const field of FIELDS) {
      if (!(field.key in loaded.values)) continue;
      const original = loaded.values[field.key];
      const inherited = loaded.inherited !== null && field.key in loaded.inherited ? loaded.inherited[field.key] : undefined;
      const draft = drafts[field.key];
      const resetPending = resets.has(field.key);
      let value: unknown = original;
      let display: unknown = original;
      let error: string | null = null;
      if (resetPending) {
        value = inherited;
        display = inherited === undefined ? original : inherited;
      } else if (draft !== undefined) {
        const parsed = parseDraft(field, draft);
        if (parsed.ok) {
          value = parsed.value;
          display = parsed.value;
        } else {
          value = undefined;
          error = parsed.error;
        }
      }
      effective[field.key] = value as PreferenceValue | undefined;
      states.set(field.key, {
        original,
        origin: loaded.origin[field.key],
        inherited,
        draft,
        resetPending,
        effective: value,
        display,
        error,
        crossError: false,
        changed: resetPending || (draft !== undefined && (error !== null || !sameValue(value, original))),
      });
    }
    const cross = crossFieldErrors(effective);
    for (const [key, message] of Object.entries(cross)) {
      const current = states.get(key);
      if (current !== undefined && current.error === null) states.set(key, { ...current, error: message, crossError: true });
    }
    return states;
  }, [loaded, drafts, resets]);

  const changes: PreferenceChange[] = [];
  let invalid = 0;
  for (const [key, field] of fieldStates) {
    if (!field.changed) continue;
    if (field.resetPending) changes.push({ key, action: 'unset' });
    else if (field.error !== null) invalid += 1;
    else changes.push({ key, action: 'set', value: field.effective as PreferenceValue });
  }
  // A cross-field error blocks the save only when this batch touches the pair: a pair that
  // was already invalid in the store (set from the CLI) must not hold unrelated edits hostage.
  const crossPairChanged = [...fieldStates.values()].some((field) => field.crossError && field.changed);
  const blockingErrors = [...fieldStates.values()].filter(
    (field) => field.error !== null && (!field.crossError || crossPairChanged || field.changed),
  ).length;
  const dirtyCount = changes.length + invalid;
  const dirty = dirtyCount > 0;

  const gate: Withheld =
    environment === null
      ? { withheld: true, reason: 'the app has not finished checking its own preconditions' }
      : isWithheld(environment.withheld, SAVE_COMMAND);
  // Busy until the reload lands, not only while the CLI runs: the form is disabled for the
  // whole window, so an edit made in it cannot be dropped along with the saved drafts.
  const busy = save.state.phase === 'pending' || awaiting !== null;
  const canSave = dirty && blockingErrors === 0 && !gate.withheld && !busy;

  function setDraft(key: string, input: DraftInput) {
    setSaved(null);
    setDrafts((previous) => ({ ...previous, [key]: input }));
    setResets((previous) => {
      if (!previous.has(key)) return previous;
      const next = new Set(previous);
      next.delete(key);
      return next;
    });
  }

  function undo(key: string) {
    setDrafts((previous) => Object.fromEntries(Object.entries(previous).filter(([name]) => name !== key)));
    setResets((previous) => {
      const next = new Set(previous);
      next.delete(key);
      return next;
    });
  }

  function markReset(key: string) {
    setSaved(null);
    undo(key);
    setResets((previous) => new Set(previous).add(key));
  }

  function discard() {
    setDrafts({});
    setResets(new Set());
    save.reset();
  }

  async function runSave() {
    if (!canSave || loaded === null) return;
    const before = loaded;
    const result = await save.run(changes);
    if (!result.ok) return;
    setSaved(result.data.failed === null ? result.data : null);
    setAwaiting({ written: new Set(result.data.applied.map((change) => change.key)), before });
    reload();
  }

  // ⌘S / Ctrl+S saves, the shortcut every settings form on the platform honours — but only
  // while this screen is the one on show. It stays mounted behind another tab, and a
  // listener on `window` would otherwise save from the Catalog. Read through refs so the
  // listener is attached once and still sees this render's state.
  const saveShortcut = useRef(runSave);
  saveShortcut.current = runSave;
  const shortcutLive = useRef(false);
  shortcutLive.current = active && !confirmLeave && tab === 'preferences';
  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if (!shortcutLive.current) return;
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 's') {
        event.preventDefault();
        void saveShortcut.current();
      }
    }
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  const unsavedTotal = dirtyCount + pluginDirty;

  function requestBack() {
    if (unsavedTotal > 0) setConfirmLeave(true);
    else onBack();
  }

  const status =
    blockingErrors > 0
      ? `${blockingErrors} value${blockingErrors === 1 ? ' needs' : 's need'} fixing before you can save`
      : dirty
        ? `${dirtyCount} unsaved change${dirtyCount === 1 ? '' : 's'}`
        : '';

  const header = (
    <header className="space-y-3">
      <nav aria-label="Breadcrumb">
        <Button variant="ghost" size="sm" className="-ml-2 text-muted-foreground" onClick={requestBack}>
          <ArrowLeft aria-hidden="true" />
          Projects
        </Button>
      </nav>
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <div className="min-w-0">
          <h2 id="settings-heading" ref={headingRef} tabIndex={-1} className="text-base font-semibold outline-none">
            {name} <span className="font-normal text-muted-foreground">· Settings</span>
          </h2>
          <p className="truncate font-mono text-xs text-muted-foreground" title={project.path}>
            {project.path}
          </p>
        </div>
        {loaded !== null ? <Badge variant="outline">store {loaded.version}</Badge> : null}
      </div>
      <p className="flex items-start gap-2 text-sm text-muted-foreground">
        <Info className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
        <span>
          Changes are saved to this project only. A value marked <OriginBadge origin="global" /> or{' '}
          <OriginBadge origin="defaults" /> is inherited; editing it overrides it here, and{' '}
          <span className="font-medium text-foreground">Reset</span> brings the inherited value back.
        </span>
      </p>
    </header>
  );

  const problem = state.phase === 'done' && !state.result.ok ? state.result : null;
  const others = (loaded === null ? [] : Object.keys(loaded.values))
    .filter((key) => !FIELD_BY_KEY.has(key) && !key.startsWith('_'))
    .sort();
  const groups = GROUPS.map((group) => ({
    group,
    fields: FIELDS.filter((field) => field.group === group.id && fieldStates.has(field.key)),
  })).filter((entry) => entry.fields.length > 0);
  const changedIn = (id: GroupId) =>
    FIELDS.filter((field) => field.group === id && fieldStates.get(field.key)?.changed === true).length;

  const lastSave = save.state.phase === 'done' ? save.state.result : null;

  return (
    <section aria-labelledby="settings-heading" className="space-y-5">
      {header}

      <Tabs
        value={tab}
        onValueChange={(next) => {
          setTab(next as 'preferences' | 'plugins');
          if (next === 'plugins') setPluginsVisited(true);
        }}
      >
        <TabsList aria-label="Project settings sections">
          <TabsTrigger value="preferences">
            Preferences
            <TabCount count={dirtyCount} />
          </TabsTrigger>
          <TabsTrigger value="plugins">
            Plugins
            <TabCount count={pluginDirty} />
          </TabsTrigger>
        </TabsList>

        {/* Both panels stay mounted (`forceMount`) so switching tabs keeps every draft. */}
        <TabsContent value="preferences" forceMount className="mt-3 space-y-5">
          {/* Mounted for the screen's whole life, so a change of text is announced; a region
              created together with its text is often missed by screen readers. */}
          <p aria-live="polite" className="sr-only">
            {busy ? 'Saving…' : refreshing ? 'Reloading preferences…' : status}
          </p>


          {state.phase === 'loading' ? <Loading what="devteam prefs list" /> : null}
          {problem !== null ? (
            <div className="space-y-4">
              <Problem problem={problem} />
              <Button variant="outline" size="sm" onClick={reload}>
                Try again
              </Button>
            </div>
          ) : null}

          {loaded !== null ? (
            <>
              {gate.withheld ? (
                <Alert>
                  <Info />
                  <AlertTitle>Saving is unavailable right now</AlertTitle>
                  <AlertDescription>You can still review every value. Reason: {gate.reason}.</AlertDescription>
                </Alert>
              ) : null}

              {saved !== null ? (
                <div
                  role="status"
                  className="flex items-center gap-2 rounded-md border border-green-600 bg-green-50 px-3 py-2 text-sm text-green-900 dark:border-green-500 dark:bg-green-950 dark:text-green-200"
                >
                  <CheckCircle2 className="size-4 shrink-0" aria-hidden="true" />
                  Saved {saved.applied.length} change{saved.applied.length === 1 ? '' : 's'} to this project. Agents read the new
                  values from their next run.
                </div>
              ) : null}
              {lastSave !== null && !lastSave.ok ? <Problem problem={lastSave} /> : null}
              {lastSave !== null && lastSave.ok && lastSave.data.failed !== null ? (
                <div className="space-y-2">
                  <p className="text-sm">
                    {lastSave.data.applied.length === 0
                      ? 'Nothing was saved.'
                      : `${lastSave.data.applied.length} change${lastSave.data.applied.length === 1 ? ' was' : 's were'} saved (${lastSave.data.applied.map((change) => FIELD_BY_KEY.get(change.key)?.label ?? change.key).join(', ')}) before one failed.`}{' '}
                    <span className="font-medium">
                      {FIELD_BY_KEY.get(lastSave.data.failed.change.key)?.label ?? lastSave.data.failed.change.key}
                    </span>{' '}
                    and anything after it are still unsaved.
                  </p>
                  <Problem problem={lastSave.data.failed.problem} />
                </div>
              ) : null}

              <div className="grid gap-6 lg:grid-cols-[11rem_minmax(0,1fr)]">
                <nav aria-label="Settings sections" className="hidden lg:block">
                  <ul className="sticky top-0 space-y-1 text-sm">
                    {groups.map(({ group }) => {
                      const count = changedIn(group.id);
                      return (
                        <li key={group.id}>
                          <a
                            href={`#settings-${group.id}`}
                            aria-current={activeSection === group.id ? 'location' : undefined}
                            onClick={(event) => {
                              event.preventDefault();
                              setActiveSection(group.id);
                              document.getElementById(`settings-${group.id}`)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
                            }}
                            className={cn(
                              'flex items-center justify-between rounded-md border-l-2 px-2 py-1.5 hover:bg-accent hover:text-accent-foreground',
                              activeSection === group.id
                                ? 'border-primary bg-accent font-medium text-foreground'
                                : 'border-transparent text-muted-foreground',
                            )}
                          >
                            {group.title}
                            {count > 0 ? (
                              <span className="rounded-full bg-primary px-1.5 text-xs font-medium text-primary-foreground">
                                <span className="sr-only">, changed: </span>
                                {count}
                              </span>
                            ) : null}
                          </a>
                        </li>
                      );
                    })}
                  </ul>
                </nav>

                {/* Disabled while a save is in flight and until its reload lands — see `busy`. */}
                <fieldset disabled={busy} aria-busy={busy} className="min-w-0 space-y-6">
                  {groups.map(({ group, fields }) => (
                    <section
                      key={group.id}
                      id={`settings-${group.id}`}
                      aria-labelledby={`settings-${group.id}-title`}
                      className="scroll-mt-4 rounded-xl border bg-card text-card-foreground shadow-sm"
                    >
                      <header className="border-b px-5 py-4">
                        <h3 id={`settings-${group.id}-title`} className="font-semibold">
                          {group.title}
                        </h3>
                        <p className="text-sm text-muted-foreground">{group.description}</p>
                      </header>
                      <div className="divide-y px-5">
                        {fields.map((field) => {
                          const fieldState = fieldStates.get(field.key) as FieldState;
                          const dependency = field.dependsOn;
                          const dimmed =
                            dependency !== undefined && fieldStates.get(dependency.key)?.effective === false;
                          return (
                            <div key={field.key}>
                              <FieldRow
                                field={field}
                                state={fieldState}
                                dimmed={dimmed}
                                onDraft={(input) => setDraft(field.key, input)}
                                onUndo={() => undo(field.key)}
                                onReset={() => markReset(field.key)}
                              />
                              {/* Right under the pair it draws, not at the end of the group. */}
                              {field.key === 'context_window_percent_limit' ? <ContextMeter states={fieldStates} /> : null}
                            </div>
                          );
                        })}
                      </div>
                    </section>
                  ))}

                  {others.length > 0 ? (
                    <section
                      aria-labelledby="settings-other-title"
                      className="rounded-xl border bg-card text-card-foreground shadow-sm"
                    >
                      <header className="border-b px-5 py-4">
                        <h3 id="settings-other-title" className="font-semibold">
                          Other
                        </h3>
                        <p className="text-sm text-muted-foreground">
                          Keys this app does not know how to edit yet. Change them with{' '}
                          <code className="font-mono text-xs">devteam prefs set</code>.
                        </p>
                      </header>
                      <dl className="divide-y px-5">
                        {others.map((key) => (
                          <div key={key} className="flex flex-wrap items-center justify-between gap-2 py-3">
                            <dt className="flex items-center gap-2 font-mono text-xs">
                              {key}
                              <OriginBadge origin={loaded?.origin[key]} />
                              {loaded?.unknown.includes(key) ? <Badge variant="destructive">unknown key</Badge> : null}
                            </dt>
                            <dd className="font-mono text-xs text-muted-foreground">{JSON.stringify(loaded?.values[key])}</dd>
                          </div>
                        ))}
                      </dl>
                    </section>
                  ) : null}
                </fieldset>
              </div>

              <SaveBar
                dirtyCount={dirtyCount}
                invalid={blockingErrors}
                status={status}
                saving={busy}
                canSave={canSave}
                withheld={gate.withheld ? gate.reason : null}
                onDiscard={discard}
                onSave={() => void runSave()}
              />
            </>
          ) : null}
        </TabsContent>

        <TabsContent value="plugins" forceMount className="mt-3">
          {pluginsVisited ? (
            <ProjectPlugins project={project} environment={environment} onDirtyChange={onPluginDirty} />
          ) : null}
        </TabsContent>
      </Tabs>

      <Dialog open={confirmLeave} onOpenChange={setConfirmLeave}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Discard unsaved changes?</DialogTitle>
            <DialogDescription>
              {unsavedTotal} change{unsavedTotal === 1 ? '' : 's'} to {name} will be lost.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setConfirmLeave(false)}>
              Keep editing
            </Button>
            <Button
              variant="destructive"
              onClick={() => {
                setConfirmLeave(false);
                onBack();
              }}
            >
              Discard and leave
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </section>
  );
}

/** The unsaved-edit count on a tab, announced as text and not only as a number. */
function TabCount({ count }: { count: number }) {
  if (count === 0) return null;
  return (
    <span className="rounded-full bg-primary px-1.5 text-xs font-medium text-primary-foreground">
      <span className="sr-only">, unsaved changes: </span>
      {count}
    </span>
  );
}

// ── a field ──────────────────────────────────────────────────────────────────────

const ORIGIN_LABELS: Record<string, { label: string; hint: string; className: string }> = {
  project: {
    label: 'This project',
    hint: 'Set in this project’s own layer.',
    className: 'border-primary/40 bg-primary/10 text-foreground',
  },
  global: {
    label: 'Global',
    hint: 'Inherited from your global preferences, shared by every project on this machine.',
    className: 'text-muted-foreground',
  },
  defaults: {
    label: 'Default',
    hint: 'The value this store version ships with.',
    className: 'text-muted-foreground',
  },
  'consent-withheld': {
    label: 'Not opted in',
    hint: 'A consent setting nobody has turned on. It stays off until you enable it.',
    className: 'border-amber-500/50 text-amber-700 dark:text-amber-400',
  },
};

function OriginBadge({ origin }: { origin: PreferenceOrigin | undefined }) {
  if (origin === undefined) return null;
  const known = ORIGIN_LABELS[origin] ?? { label: origin, hint: `Set in the ${origin} layer.`, className: '' };
  return (
    <Hint content={known.hint}>
      <Badge variant="outline" className={cn('font-normal', known.className)} aria-label={`${known.label}: ${known.hint}`}>
        {known.label}
      </Badge>
    </Hint>
  );
}

function FieldRow({
  field,
  state,
  dimmed,
  onDraft,
  onUndo,
  onReset,
}: {
  field: Field;
  state: FieldState;
  dimmed: boolean;
  onDraft: (input: DraftInput) => void;
  onUndo: () => void;
  onReset: () => void;
}) {
  const id = `pref-${field.key}`;
  const helpId = `${id}-help`;
  const errorId = `${id}-error`;
  const describedBy = [helpId, state.error !== null ? errorId : null].filter(Boolean).join(' ');
  const readonly = field.control.type === 'readonly';

  return (
    <div
      className={cn(
        'grid gap-3 py-4',
        // Radio cards need the width to read as cards; everything else sits beside its label.
        field.control.type !== 'cards' && 'md:grid-cols-[minmax(0,1fr)_minmax(0,22rem)] md:gap-6',
        dimmed && 'opacity-60',
      )}
      data-changed={state.changed || undefined}
    >
      <div className="min-w-0 space-y-1">
        <div className="flex flex-wrap items-center gap-2">
          {state.changed ? (
            <span className="size-1.5 rounded-full bg-primary" aria-hidden="true" title="Changed" />
          ) : null}
          <Label id={`${id}-label`} htmlFor={readonly ? undefined : id} className="text-sm font-medium">
            {field.label}
          </Label>
          {state.resetPending ? (
            <Badge variant="outline" className="font-normal text-muted-foreground">
              {state.inherited === undefined
                ? 'reverts to the inherited value on save'
                : `reverts to ${describeValue(state.inherited)} on save`}
            </Badge>
          ) : state.draft === undefined ? (
            <OriginBadge origin={state.origin} />
          ) : null}
          {field.consent === true ? (
            <Badge variant="outline" className="font-normal text-muted-foreground">
              consent
            </Badge>
          ) : null}
        </div>
        <p id={helpId} className="text-xs text-muted-foreground">
          {field.help}
          {dimmed && field.dependsOn !== undefined ? <span className="block italic">{field.dependsOn.note}</span> : null}
        </p>
        <div className="flex gap-3 pt-0.5">
          {state.changed ? (
            <Button variant="link" size="sm" className="h-auto p-0 text-xs" onClick={onUndo}>
              <Undo2 aria-hidden="true" />
              Undo
            </Button>
          ) : state.origin === 'project' && !readonly ? (
            <Hint content="Remove this value from the project so the global or default value applies again">
              <Button variant="link" size="sm" className="h-auto p-0 text-xs text-muted-foreground" onClick={onReset}>
                <RotateCcw aria-hidden="true" />
                Reset to inherited
              </Button>
            </Hint>
          ) : null}
        </div>
      </div>

      <div className="min-w-0 space-y-1.5">
        <Control
          id={id}
          field={field}
          state={state}
          describedBy={describedBy}
          onDraft={onDraft}
        />
        {state.error !== null ? (
          <p id={errorId} className="text-xs text-destructive">
            {state.error}
          </p>
        ) : null}
      </div>
    </div>
  );
}

/** A value as a person reads it, for the reset badge. */
function describeValue(value: unknown): string {
  if (value === null) return 'not set';
  if (typeof value === 'boolean') return value ? 'on' : 'off';
  if (typeof value === 'number') return value.toLocaleString('en-US');
  if (typeof value === 'string') return `“${value}”`;
  return JSON.stringify(value);
}

// ── controls ─────────────────────────────────────────────────────────────────────

const NULL_OPTION = '__null__';
const OTHER_OPTION = '__other__';

function encode(value: unknown): string {
  if (value === null || value === undefined) return NULL_OPTION;
  return typeof value === 'string' ? value : JSON.stringify(value);
}

function Control({
  id,
  field,
  state,
  describedBy,
  onDraft,
}: {
  id: string;
  field: Field;
  state: FieldState;
  describedBy: string;
  onDraft: (input: DraftInput) => void;
}) {
  const { control } = field;
  const invalid = state.error !== null;
  const disabled = state.resetPending;
  const shown = state.display;

  if (control.type === 'readonly') {
    return (
      <div className="flex items-center gap-2">
        <span className="font-mono text-sm">{JSON.stringify(state.original)}</span>
        <Badge variant="secondary" className="font-normal">
          {control.reason}
        </Badge>
      </div>
    );
  }

  if (control.type === 'switch') {
    const list = Array.isArray(state.original) && state.draft === undefined ? (state.original as unknown[]) : null;
    const checked = list !== null ? list.length > 0 : shown === true;
    return (
      <div className="space-y-1">
        <div className="flex h-9 items-center gap-3">
          <Switch
            id={id}
            checked={checked}
            disabled={disabled}
            aria-describedby={describedBy}
            onCheckedChange={(next) => onDraft({ kind: 'value', value: next })}
          />
          <span className="text-sm text-muted-foreground" aria-hidden="true">
            {checked ? 'On' : 'Off'}
          </span>
        </div>
        {list !== null ? (
          <p className="text-xs text-muted-foreground">
            Currently muted for: {list.map(String).join(', ')} (set from the CLI). Switching replaces the list.
          </p>
        ) : null}
      </div>
    );
  }

  if (control.type === 'integer') {
    const grouped = control.grouped === true;
    const text =
      state.draft?.kind === 'text'
        ? state.draft.text
        : typeof shown === 'number'
          ? formatInteger(shown, grouped)
          : '';
    const current = typeof state.effective === 'number' ? state.effective : null;
    const step = (delta: number) => {
      const base = current ?? (typeof state.original === 'number' ? state.original : control.min);
      const next = Math.min(control.max, Math.max(control.min, base + delta));
      onDraft({ kind: 'text', text: formatInteger(next, grouped) });
    };
    return (
      <div className="space-y-2">
        <div className="relative">
          <Input
            id={id}
            inputMode="numeric"
            autoComplete="off"
            value={text}
            disabled={disabled}
            aria-invalid={invalid || undefined}
            aria-describedby={describedBy}
            className="pr-20 tabular-nums"
            onChange={(event) => onDraft({ kind: 'text', text: event.target.value })}
            onBlur={() => {
              // Masking on blur, not per keystroke, so the caret never jumps mid-edit.
              if (current !== null && state.draft?.kind === 'text') onDraft({ kind: 'text', text: formatInteger(current, grouped) });
            }}
            onKeyDown={(event) => {
              if (event.key === 'ArrowUp' || event.key === 'ArrowDown') {
                event.preventDefault();
                const size = event.shiftKey ? (grouped ? 100_000 : 10) : grouped ? 1_000 : 1;
                step(event.key === 'ArrowUp' ? size : -size);
              }
            }}
          />
          <span
            className="pointer-events-none absolute inset-y-0 right-3 flex items-center text-sm text-muted-foreground"
            aria-hidden="true"
          >
            {control.unit}
          </span>
        </div>
        {control.presets !== undefined ? (
          <div className="flex flex-wrap gap-1.5" role="group" aria-label={`${field.label} presets`}>
            {control.presets.map((preset) => (
              <Button
                key={preset.label}
                type="button"
                variant={current === preset.value ? 'secondary' : 'outline'}
                size="xs"
                disabled={disabled}
                aria-pressed={current === preset.value}
                onClick={() => onDraft({ kind: 'text', text: formatInteger(preset.value, grouped) })}
              >
                {preset.label}
              </Button>
            ))}
          </div>
        ) : null}
      </div>
    );
  }

  if (control.type === 'text') {
    const text = state.draft?.kind === 'text' ? state.draft.text : typeof shown === 'string' ? shown : '';
    return (
      <div className="space-y-2">
        <Input
            id={id}
            value={text}
            placeholder={control.placeholder}
            spellCheck={false}
            autoComplete="off"
            disabled={disabled}
            aria-invalid={invalid || undefined}
            aria-describedby={describedBy}
            className="font-mono"
            onChange={(event) => onDraft({ kind: 'text', text: event.target.value })}
          />
        {control.nullable && text.trim() !== '' ? (
          <Button
            type="button"
            variant="link"
            size="sm"
            className="h-auto p-0 text-xs"
            disabled={disabled}
            onClick={() => onDraft({ kind: 'text', text: '' })}
          >
            {control.placeholder}
          </Button>
        ) : null}
      </div>
    );
  }

  if (control.type === 'cards') {
    return (
      <RadioGroup
        value={encode(shown)}
        disabled={disabled}
        aria-labelledby={`${id}-label`}
        aria-describedby={describedBy}
        onValueChange={(value) => onDraft({ kind: 'value', value: value === NULL_OPTION ? null : value })}
        className="grid-cols-2 lg:grid-cols-4"
      >
        {control.options.map((option, index) => {
          const optionId = index === 0 ? id : `${id}-${encode(option.value)}`;
          const selected = encode(shown) === encode(option.value);
          return (
            <label
              key={encode(option.value)}
              htmlFor={optionId}
              className={cn(
                'flex cursor-pointer items-start gap-2.5 rounded-lg border p-3 transition-colors hover:bg-accent/50',
                selected && 'border-primary bg-primary/5',
              )}
            >
              <RadioGroupItem value={encode(option.value)} id={optionId} className="mt-0.5" />
              <span className="space-y-0.5">
                <span className="block text-sm font-medium">{option.label}</span>
                {option.description !== undefined ? (
                  <span className="block text-xs text-muted-foreground">{option.description}</span>
                ) : null}
              </span>
            </label>
          );
        })}
      </RadioGroup>
    );
  }

  // select
  const booleanValues = BOOLEAN_SELECT_KEYS.has(field.key);
  const listed = new Set(control.options.map((option) => encode(option.value)));
  const otherMode =
    control.other !== undefined &&
    (state.draft?.kind === 'text' || (state.draft === undefined && !listed.has(encode(shown))));
  const otherText =
    state.draft?.kind === 'text' ? state.draft.text : typeof shown === 'string' && !listed.has(shown) ? shown : '';
  return (
    <div className="space-y-2">
      <select
        id={id}
        value={otherMode ? OTHER_OPTION : encode(shown)}
        disabled={disabled}
        aria-describedby={describedBy}
        aria-invalid={invalid || undefined}
        className={SELECT_CLASS}
        onChange={(event) => {
          const raw = event.target.value;
          if (raw === OTHER_OPTION) {
            onDraft({ kind: 'text', text: otherText });
            return;
          }
          const value: PreferenceValue =
            raw === NULL_OPTION ? null : booleanValues ? raw === 'true' : raw;
          onDraft({ kind: 'value', value });
        }}
      >
        {control.options.map((option) => (
          <option key={encode(option.value)} value={encode(option.value)}>
            {option.label}
          </option>
        ))}
        {control.other !== undefined ? <option value={OTHER_OPTION}>{control.other.label}</option> : null}
      </select>
      {otherMode && control.other !== undefined ? (
        <Input
          aria-label={`${field.label}, custom value`}
          value={otherText}
          placeholder={control.other.placeholder}
          spellCheck={false}
          autoComplete="off"
          autoFocus={state.draft?.kind === 'text' && otherText === ''}
          disabled={disabled}
          aria-invalid={invalid || undefined}
          aria-describedby={describedBy}
          className="font-mono"
          onChange={(event) => onDraft({ kind: 'text', text: event.target.value })}
        />
      ) : null}
    </div>
  );
}

// ── the context meter ───────────────────────────────────────────────────────────

/**
 * The two thresholds drawn on one bar, in tokens as well as percent — "55%" of an unknown
 * window is not something a person can judge, "110,000 tokens" is.
 */
function ContextMeter({ states }: { states: ReadonlyMap<string, FieldState> }) {
  const warning = states.get('context_window_percent_warning')?.effective;
  const limit = states.get('context_window_percent_limit')?.effective;
  const contextWindow = states.get('model_max_tokens')?.effective;
  if (typeof warning !== 'number' || typeof limit !== 'number' || warning >= limit) return null;
  const tokens = (percent: number) =>
    typeof contextWindow === 'number' ? ` (${Math.round((contextWindow * percent) / 100).toLocaleString('en-US')} tokens)` : '';
  return (
    <div className="space-y-2 pb-4">
      <div
        className="relative h-2 overflow-hidden rounded-full bg-muted"
        role="img"
        aria-label={`Warning from ${warning}% and critical from ${limit}% of the context window`}
      >
        <div className="absolute inset-y-0 bg-amber-500/70" style={{ left: `${warning}%`, width: `${limit - warning}%` }} />
        <div className="absolute inset-y-0 right-0 bg-destructive/70" style={{ left: `${limit}%` }} />
      </div>
      <p className="text-xs text-muted-foreground">
        Agents warn at <span className="font-medium text-foreground">{warning}%</span>
        {tokens(warning)} and go critical at <span className="font-medium text-foreground">{limit}%</span>
        {tokens(limit)}.
      </p>
    </div>
  );
}
