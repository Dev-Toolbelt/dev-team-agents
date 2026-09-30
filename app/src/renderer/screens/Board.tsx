import { useEffect, useId, useMemo, useState } from 'react';
import {
  Activity,
  ArrowLeft,
  Bot,
  Check,
  CircleAlert,
  Clock,
  Copy,
  Moon,
  Pause,
  RefreshCw,
  Settings2,
  Sparkles,
  SquareTerminal,
  TriangleAlert,
  Braces,
} from 'lucide-react';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Empty } from '../Problem.js';
import {
  PERIODS,
  basename,
  boardProjectName,
  buildKanban,
  formatDuration,
  isRunning,
  percent,
  stepDurations,
  viewProject,
  type KanbanItem,
  type Period,
  type ProjectView,
} from '../boardModel.js';
import {
  BOARD_SETTING_BOUNDS,
  type BoardCounts,
  type BoardFeed,
  type BoardProject,
  type BoardSession,
  type BoardSessionStatus,
  type BoardSettings,
} from '../../shared/api.js';

const EMPTY_FEED: BoardFeed = { status: 'starting', detail: null, projects: [] };
const DEFAULT_SETTINGS: BoardSettings = {
  staleAfterMinutes: BOARD_SETTING_BOUNDS.staleAfterMinutes.fallback,
  doneRetentionDays: BOARD_SETTING_BOUNDS.doneRetentionDays.fallback,
};

const SELECT_CLASS =
  'h-9 rounded-md border border-input bg-transparent px-3 text-sm shadow-xs outline-none focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50 dark:bg-input/30';

const PROVIDER_LABELS: Readonly<Record<string, string>> = {
  claude: 'Claude Code',
  codex: 'Codex',
  opencode: 'opencode',
};

const PROVIDER_ICONS: Readonly<Record<string, typeof Bot>> = {
  claude: Sparkles,
  codex: SquareTerminal,
  opencode: Braces,
};

function providerLabel(provider: string): string {
  return PROVIDER_LABELS[provider] ?? provider;
}

/** The provider's mark. Its name is always available as text: the icon is never the only cue. */
export function ProviderIcon({ provider, withLabel = false }: { provider: string; withLabel?: boolean }) {
  const Icon = PROVIDER_ICONS[provider] ?? Bot;
  const label = providerLabel(provider);
  return (
    <span className="inline-flex items-center gap-1" title={label}>
      <Icon className="size-3.5 shrink-0" role="img" aria-label={withLabel ? undefined : label} aria-hidden={withLabel ? true : undefined} />
      {withLabel ? <span>{label}</span> : null}
    </span>
  );
}

const STATUS_ICON: Readonly<Record<BoardSessionStatus, typeof Activity>> = {
  active: Activity,
  idle: Pause,
  ended: Moon,
};

const STATUS_WORD: Readonly<Record<BoardSessionStatus, string>> = {
  active: 'Active',
  idle: 'Idle',
  ended: 'Ended',
};

/** Re-renders on an interval so "time in column" keeps moving without a new snapshot. */
function useNow(clock: () => number, intervalMs: number): number {
  const [now, setNow] = useState(() => Math.floor(clock() / 1000));
  useEffect(() => {
    setNow(Math.floor(clock() / 1000));
    const timer = setInterval(() => setNow(Math.floor(clock() / 1000)), intervalMs);
    return () => clearInterval(timer);
  }, [clock, intervalMs]);
  return now;
}

/**
 * The task board (ADR-0018): every project whose agent sessions created a todo list, and,
 * one click in, that project's kanban. Read-only — nothing here edits, moves or deletes a
 * task. The data is the main process's snapshot of `devteam tasks watch`; this screen only
 * narrows it (period, session, retention) and formats it.
 */
export function Board({ active = true, clock = Date.now }: { active?: boolean; clock?: () => number }) {
  const [feed, setFeed] = useState<BoardFeed>(EMPTY_FEED);
  const [names, setNames] = useState<Readonly<Record<string, string>>>({});
  const [settings, setSettings] = useState<BoardSettings>(DEFAULT_SETTINGS);
  const [selected, setSelected] = useState<string | null>(null);
  const [period, setPeriod] = useState<Period>('7d');
  const [refreshing, setRefreshing] = useState(false);
  const now = useNow(clock, 1_000);

  useEffect(() => {
    let live = true;
    void window.devteam.taskBoard().then((initial) => {
      if (live) setFeed(initial);
    });
    void window.devteam.projectNames().then((each) => {
      if (live) setNames(each);
    });
    void window.devteam.boardSettings().then((each) => {
      if (live) setSettings(each);
    });
    const unsubscribe = window.devteam.onTaskBoard((next) => setFeed(next));
    return () => {
      live = false;
      unsubscribe();
    };
  }, []);

  // Names can change on the Projects tab; re-read when this tab is shown again.
  useEffect(() => {
    if (!active) return;
    let live = true;
    void window.devteam.projectNames().then((each) => {
      if (live) setNames(each);
    });
    return () => {
      live = false;
    };
  }, [active]);

  async function refresh() {
    setRefreshing(true);
    try {
      setFeed(await window.devteam.refreshTaskBoard());
    } finally {
      setRefreshing(false);
    }
  }

  const project = selected === null ? undefined : feed.projects.find((each) => each.project_id === selected);

  return (
    <section aria-labelledby="board-heading" className="space-y-4">
      <header className="flex flex-wrap items-baseline justify-between gap-4">
        <div>
          <h2 id="board-heading" className="text-base font-semibold">
            Task board
          </h2>
          <p className="text-sm text-muted-foreground">
            The todo lists your agent sessions keep, across every bound project. Read-only.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <label className="sr-only" htmlFor="board-period">
            Period
          </label>
          <select
            id="board-period"
            value={period}
            onChange={(event) => setPeriod(event.target.value as Period)}
            className={SELECT_CLASS}
          >
            {PERIODS.map((each) => (
              <option key={each.value} value={each.value}>
                {each.label}
              </option>
            ))}
          </select>
          <Button variant="outline" size="sm" onClick={() => void refresh()} disabled={refreshing}>
            <RefreshCw className={refreshing ? 'animate-spin' : ''} aria-hidden="true" />
            Refresh
          </Button>
          <BoardSettingsControl settings={settings} onSaved={setSettings} />
        </div>
      </header>

      <StreamNotice feed={feed} />

      {selected !== null && project !== undefined ? (
        <Kanban
          project={project}
          name={boardProjectName(project, names)}
          period={period}
          settings={settings}
          now={now}
          onBack={() => setSelected(null)}
        />
      ) : (
        <Overview
          feed={feed}
          names={names}
          period={period}
          now={now}
          gone={selected !== null}
          onOpen={setSelected}
        />
      )}
    </section>
  );
}

function StreamNotice({ feed }: { feed: BoardFeed }) {
  if (feed.status === 'live') return null;
  if (feed.status === 'unavailable') {
    return (
      <Alert variant="destructive">
        <CircleAlert />
        <AlertTitle>The task board is off</AlertTitle>
        <AlertDescription>{feed.detail ?? 'The task stream cannot run.'}</AlertDescription>
      </Alert>
    );
  }
  return (
    <p className="text-xs text-muted-foreground" role="status">
      {feed.status === 'retrying'
        ? (feed.detail ?? 'Reconnecting to the task stream.')
        : 'Waiting for the first snapshot of the task stream.'}
    </p>
  );
}

// ── the overview ──────────────────────────────────────────────────────────────

function Overview({
  feed,
  names,
  period,
  now,
  gone,
  onOpen,
}: {
  feed: BoardFeed;
  names: Readonly<Record<string, string>>;
  period: Period;
  now: number;
  gone: boolean;
  onOpen: (projectId: string) => void;
}) {
  const views = useMemo(
    () =>
      feed.projects
        .map((project) => viewProject(project, period, now))
        .filter((view): view is ProjectView => view !== null),
    [feed.projects, period, now],
  );

  if (views.length === 0) {
    if (feed.status === 'unavailable') return null;
    return (
      <Empty>
        {feed.projects.length === 0
          ? 'No project has tasks yet. When an agent session writes a todo list in a bound project, it shows up here.'
          : 'No project has tasks in this period.'}
      </Empty>
    );
  }

  return (
    <>
      {gone ? <p className="text-sm text-muted-foreground">That project no longer has tasks.</p> : null}
      <ul className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3" aria-label="Projects with tasks">
        {views.map((view) => (
          <li key={view.project.project_id}>
            <ProjectCard view={view} name={boardProjectName(view.project, names)} onOpen={() => onOpen(view.project.project_id)} />
          </li>
        ))}
      </ul>
    </>
  );
}

function ProjectCard({ view, name, onOpen }: { view: ProjectView; name: string; onOpen: () => void }) {
  const { counts } = view;
  return (
    <button
      type="button"
      onClick={onOpen}
      className="flex w-full flex-col gap-3 rounded-lg border bg-card p-4 text-left text-card-foreground shadow-xs transition-colors hover:bg-accent focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50 focus-visible:outline-hidden"
    >
      <span className="flex items-start justify-between gap-2">
        <span className="min-w-0 truncate text-sm font-semibold">{name}</span>
        <span className="flex shrink-0 items-center gap-2 text-muted-foreground">
          {view.providers.map((provider) => (
            <ProviderIcon key={provider} provider={provider} />
          ))}
        </span>
      </span>
      <span className="text-xs text-muted-foreground">
        {view.sessionsTotal} {view.sessionsTotal === 1 ? 'session' : 'sessions'} ({view.sessionsActive} active)
        {' · '}
        {counts.total} {counts.total === 1 ? 'task' : 'tasks'}
      </span>
      <ProgressBar counts={counts} />
      <CountsRow counts={counts} />
      {view.stale > 0 || view.abandoned > 0 ? (
        <span className="flex flex-wrap gap-2">
          {view.stale > 0 ? <StaleBadge count={view.stale} /> : null}
          {view.abandoned > 0 ? <AbandonedBadge count={view.abandoned} /> : null}
        </span>
      ) : null}
    </button>
  );
}

function StaleBadge({ count }: { count?: number }) {
  return (
    <Badge
      variant="outline"
      className="border-warning text-foreground"
      title="In progress for longer than the stale threshold in a session that is still running"
    >
      <Clock aria-hidden="true" />
      {count === undefined ? 'Stale' : `${count} stale`}
    </Badge>
  );
}

function AbandonedBadge({ count }: { count?: number }) {
  return (
    <Badge
      variant="outline"
      className="border-destructive text-foreground"
      title="Still open when its session ended"
    >
      <TriangleAlert aria-hidden="true" />
      {count === undefined ? 'Abandoned' : `${count} abandoned`}
    </Badge>
  );
}

/** Stacked bar plus the figures beside it: the colours alone never carry the meaning. */
function ProgressBar({ counts }: { counts: BoardCounts }) {
  const label = `${counts.todo} to do, ${counts.in_progress} in progress, ${counts.done} done`;
  return (
    <span role="img" aria-label={label} className="flex h-2 w-full overflow-hidden rounded-full bg-muted">
      <span className="bg-muted-foreground/40" style={{ width: `${percent(counts.todo, counts.total)}%` }} />
      <span className="bg-warning" style={{ width: `${percent(counts.in_progress, counts.total)}%` }} />
      <span className="bg-success" style={{ width: `${percent(counts.done, counts.total)}%` }} />
    </span>
  );
}

function CountsRow({ counts }: { counts: BoardCounts }) {
  const cells: readonly { readonly label: string; readonly value: number; readonly dot: string }[] = [
    { label: 'To do', value: counts.todo, dot: 'bg-muted-foreground/40' },
    { label: 'In progress', value: counts.in_progress, dot: 'bg-warning' },
    { label: 'Done', value: counts.done, dot: 'bg-success' },
  ];
  return (
    <dl className="grid grid-cols-3 gap-2 text-xs">
      {cells.map((cell) => (
        <div key={cell.label}>
          <dt className="flex items-center gap-1 text-muted-foreground">
            <span aria-hidden="true" className={`inline-block size-2 rounded-full ${cell.dot}`} />
            {cell.label}
          </dt>
          <dd className="font-medium tabular-nums">
            {cell.value} <span className="text-muted-foreground">({percent(cell.value, counts.total)}%)</span>
          </dd>
        </div>
      ))}
    </dl>
  );
}

// ── the project kanban ────────────────────────────────────────────────────────

function Kanban({
  project,
  name,
  period,
  settings,
  now,
  onBack,
}: {
  project: BoardProject;
  name: string;
  period: Period;
  settings: BoardSettings;
  now: number;
  onBack: () => void;
}) {
  const [sessionId, setSessionId] = useState<string>('all');
  const [hideOldDone, setHideOldDone] = useState(true);
  const [localPeriod, setLocalPeriod] = useState<Period>(period);
  const hideId = useId();

  // A session that vanished from the snapshot must not leave the filter selecting nothing.
  const effectiveSession = project.sessions.some((each) => each.session_id === sessionId) ? sessionId : 'all';
  const view = useMemo(
    () => buildKanban(project, { sessionId: effectiveSession, period: localPeriod, hideOldDone, retentionDays: settings.doneRetentionDays }, now),
    [project, effectiveSession, localPeriod, hideOldDone, settings.doneRetentionDays, now],
  );
  const shownSessions = project.sessions.filter((each) => effectiveSession === 'all' || each.session_id === effectiveSession);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <Button variant="ghost" size="sm" onClick={onBack}>
          <ArrowLeft aria-hidden="true" />
          Back to the board
        </Button>
        <h3 className="text-base font-semibold">{name}</h3>
        <span className="font-mono text-xs text-muted-foreground">{project.root}</span>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <label className="text-sm" htmlFor="kanban-session">
          Session
        </label>
        <select
          id="kanban-session"
          value={effectiveSession}
          onChange={(event) => setSessionId(event.target.value)}
          className={SELECT_CLASS}
        >
          <option value="all">All sessions</option>
          {project.sessions.map((each) => (
            <option key={each.session_id} value={each.session_id}>
              {sessionLabel(each)}
            </option>
          ))}
        </select>
        <label className="text-sm" htmlFor="kanban-period">
          Period
        </label>
        <select
          id="kanban-period"
          value={localPeriod}
          onChange={(event) => setLocalPeriod(event.target.value as Period)}
          className={SELECT_CLASS}
        >
          {PERIODS.map((each) => (
            <option key={each.value} value={each.value}>
              {each.label}
            </option>
          ))}
        </select>
        <span className="flex items-center gap-2">
          <Checkbox id={hideId} checked={hideOldDone} onCheckedChange={(checked) => setHideOldDone(checked === true)} />
          <Label htmlFor={hideId} className="text-sm">
            Hide done older than {settings.doneRetentionDays} {settings.doneRetentionDays === 1 ? 'day' : 'days'}
          </Label>
        </span>
      </div>

      <SessionStrip projectId={project.project_id} sessions={shownSessions} />

      <div className="grid gap-4 md:grid-cols-3">
        <Column title="To do" items={view.todo} now={now} />
        <Column title="In progress" items={view.in_progress} now={now} />
        <Column
          title="Done"
          items={view.done}
          now={now}
          note={view.hiddenDone > 0 ? `${view.hiddenDone} older done ${view.hiddenDone === 1 ? 'task is' : 'tasks are'} hidden` : null}
        />
      </div>
    </div>
  );
}

function sessionLabel(session: BoardSession): string {
  const where = session.branch ?? (session.cwd !== '' ? basename(session.cwd) : 'no branch');
  return `${providerLabel(session.provider)} · ${where} · ${session.session_id.slice(0, 8)}`;
}

function SessionStrip({ projectId, sessions }: { projectId: string; sessions: readonly BoardSession[] }) {
  if (sessions.length === 0) return null;
  return (
    <ul aria-label="Sessions" className="space-y-2">
      {sessions.map((session) => (
        <SessionRow key={session.session_id} projectId={projectId} session={session} />
      ))}
    </ul>
  );
}

function SessionRow({ projectId, session }: { projectId: string; session: BoardSession }) {
  const [message, setMessage] = useState<{ readonly ok: boolean; readonly text: string } | null>(null);
  const StatusIcon = STATUS_ICON[session.status];
  const where = session.branch ?? 'no branch';

  async function copy() {
    const answer = await window.devteam.copyResumeCommand({ projectId, sessionId: session.session_id });
    setMessage(answer.copied ? { ok: true, text: 'Resume command copied' } : { ok: false, text: answer.message });
  }

  return (
    <li className="flex flex-wrap items-center gap-x-4 gap-y-1 rounded-md border bg-card px-3 py-2 text-sm">
      <span className="flex items-center gap-1.5 font-medium">
        <ProviderIcon provider={session.provider} withLabel />
      </span>
      <span className="font-mono text-xs">{where}</span>
      <span className="flex items-center gap-1 text-xs" data-status={session.status}>
        <StatusIcon className="size-3.5" aria-hidden="true" />
        {STATUS_WORD[session.status]}
      </span>
      <span className="text-xs text-muted-foreground">
        {session.counts.todo} to do · {session.counts.in_progress} in progress · {session.counts.done} done
      </span>
      <span className="ml-auto flex items-center gap-2">
        {message !== null ? (
          <span role="status" className={`text-xs ${message.ok ? 'text-muted-foreground' : 'text-destructive'}`}>
            {message.text}
          </span>
        ) : null}
        <Button
          variant="outline"
          size="sm"
          disabled={session.resume_command === null}
          title={session.resume_command === null ? 'No resume command is available for this session' : session.resume_command}
          aria-label={`Copy resume command for the ${providerLabel(session.provider)} session on ${where}`}
          onClick={() => void copy()}
        >
          {message?.ok === true ? <Check aria-hidden="true" /> : <Copy aria-hidden="true" />}
          Copy resume command
        </Button>
      </span>
    </li>
  );
}

function Column({
  title,
  items,
  now,
  note = null,
}: {
  title: string;
  items: readonly KanbanItem[];
  now: number;
  note?: string | null;
}) {
  const headingId = useId();
  return (
    <section aria-labelledby={headingId} className="min-w-0 rounded-lg bg-muted/40 p-3">
      <h4 id={headingId} className="mb-3 flex items-center justify-between text-sm font-semibold">
        {title}
        <span className="rounded-full bg-muted px-2 text-xs font-medium tabular-nums" aria-label={`${items.length} tasks`}>
          {items.length}
        </span>
      </h4>
      {items.length === 0 ? (
        <p className="py-2 text-xs text-muted-foreground">Nothing here.</p>
      ) : (
        <ul className="space-y-2">
          {items.map((item) => (
            <TaskCard key={`${item.session.session_id}:${item.task.key}`} item={item} now={now} />
          ))}
        </ul>
      )}
      {note !== null ? <p className="mt-2 text-xs text-muted-foreground">{note}</p> : null}
    </section>
  );
}

/**
 * One task. Focusable, so the per-step times that hover reveals are reachable from the
 * keyboard too: the same panel opens on `:focus-within`, and the card points at it with
 * `aria-describedby`, so a screen reader hears it without opening anything.
 */
function TaskCard({ item, now }: { item: KanbanItem; now: number }) {
  const { session, task } = item;
  const detailId = useId();
  const steps = stepDurations(task, now, isRunning(session, task));
  const where = session.branch ?? 'no branch';
  return (
    <li
      tabIndex={0}
      aria-describedby={detailId}
      className="group relative rounded-md border bg-card p-3 text-sm text-card-foreground shadow-xs focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50 focus-visible:outline-hidden"
    >
      <p className={task.column === 'done' ? 'text-muted-foreground' : undefined}>{task.content}</p>
      <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
        <span className="inline-flex items-center gap-1" title={`${providerLabel(session.provider)} session`}>
          <ProviderIcon provider={session.provider} />
          <span className="font-mono">{where}</span>
        </span>
        <span className="inline-flex items-center gap-1">
          <Clock className="size-3" aria-hidden="true" />
          <span className="sr-only">Time in this column: </span>
          {formatDuration(now - task.status_since)}
        </span>
        {task.stale ? <StaleBadge /> : null}
        {task.abandoned ? <AbandonedBadge /> : null}
      </div>
      <div
        id={detailId}
        role="tooltip"
        className="absolute inset-x-2 top-full z-20 mt-1 hidden rounded-md border bg-popover p-2 text-xs text-popover-foreground shadow-md group-hover:block group-focus-within:block group-focus-visible:block"
      >
        <p className="mb-1 font-medium">Time per step</p>
        <ul>
          {steps.map((step) => (
            <li key={step.status} className="flex justify-between gap-4">
              <span>
                {step.label}
                {step.current ? ' (now)' : ''}
              </span>
              <span className="tabular-nums">{formatDuration(step.seconds)}</span>
            </li>
          ))}
        </ul>
      </div>
    </li>
  );
}

// ── settings ──────────────────────────────────────────────────────────────────

function BoardSettingsControl({ settings, onSaved }: { settings: BoardSettings; onSaved: (settings: BoardSettings) => void }) {
  const [open, setOpen] = useState(false);
  const [stale, setStale] = useState(String(settings.staleAfterMinutes));
  const [retention, setRetention] = useState(String(settings.doneRetentionDays));
  const [problem, setProblem] = useState<string | null>(null);
  const staleBounds = BOARD_SETTING_BOUNDS.staleAfterMinutes;
  const retentionBounds = BOARD_SETTING_BOUNDS.doneRetentionDays;

  useEffect(() => {
    if (!open) return;
    setStale(String(settings.staleAfterMinutes));
    setRetention(String(settings.doneRetentionDays));
    setProblem(null);
  }, [open, settings]);

  async function save() {
    const answer = await window.devteam.setBoardSettings({
      staleAfterMinutes: Number(stale),
      doneRetentionDays: Number(retention),
    });
    if (answer.ok) {
      onSaved(answer.settings);
      setOpen(false);
    } else {
      setProblem(answer.message);
    }
  }

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button variant="outline" size="sm">
          <Settings2 aria-hidden="true" />
          Board settings
        </Button>
      </PopoverTrigger>
      <PopoverContent aria-label="Board settings" className="space-y-3 p-4">
        <div className="space-y-1">
          <Label htmlFor="board-stale-after">Stale after (minutes)</Label>
          <Input
            id="board-stale-after"
            type="number"
            inputMode="numeric"
            min={staleBounds.min}
            max={staleBounds.max}
            value={stale}
            onChange={(event) => setStale(event.target.value)}
          />
          <p className="text-xs text-muted-foreground">
            An in-progress task older than this, in a running session, is flagged stale ({staleBounds.min} to{' '}
            {staleBounds.max}).
          </p>
        </div>
        <div className="space-y-1">
          <Label htmlFor="board-done-retention">Show done for (days)</Label>
          <Input
            id="board-done-retention"
            type="number"
            inputMode="numeric"
            min={retentionBounds.min}
            max={retentionBounds.max}
            value={retention}
            onChange={(event) => setRetention(event.target.value)}
          />
          <p className="text-xs text-muted-foreground">
            The kanban hides done tasks older than this by default ({retentionBounds.min} to {retentionBounds.max}).
          </p>
        </div>
        {problem !== null ? (
          <p role="alert" className="text-xs text-destructive">
            {problem}
          </p>
        ) : null}
        <Button size="sm" onClick={() => void save()}>
          Save
        </Button>
      </PopoverContent>
    </Popover>
  );
}
