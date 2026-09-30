import { memo, useEffect, useId, useMemo, useRef, useState, type FormEvent } from 'react';
import {
  Activity,
  ArrowLeft,
  Bot,
  Check,
  ChevronDown,
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
  percentLabels,
  sessionsInPeriod,
  stepDurations,
  timeInColumn,
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
  type BoardReview,
  type BoardSession,
  type BoardSessionStatus,
  type BoardSettings,
} from '../../shared/api.js';

/** How long "Resume command copied" stays on screen. */
const COPIED_MESSAGE_MS = 3_000;
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

/**
 * Epoch seconds, floored to `bucketSeconds`, re-sampled on that interval so "time in column"
 * keeps moving without a new snapshot. While `enabled` is false (the Board tab is mounted
 * but hidden) no timer runs, and the value is re-sampled the moment it turns true again.
 */
function useNow(clock: () => number, bucketSeconds: number, enabled: boolean): number {
  const sample = () => Math.floor(clock() / 1000 / bucketSeconds) * bucketSeconds;
  const [now, setNow] = useState(sample);
  useEffect(() => {
    if (!enabled) return;
    setNow(sample());
    const timer = setInterval(() => setNow(sample()), bucketSeconds * 1000);
    return () => clearInterval(timer);
  }, [clock, bucketSeconds, enabled]);
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
  const [loadFailed, setLoadFailed] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);
  const [projectGone, setProjectGone] = useState(false);
  const loadFailedRef = useRef(false);
  // The overview only shows whole-minute figures (counts, a period cutoff); the seconds live in the kanban.
  const now = useNow(clock, 60, active);

  useEffect(() => {
    let live = true;
    // Subscribe first: a push that lands before the initial read answers is newer than it.
    let pushed = false;
    const unsubscribe = window.devteam.onTaskBoard((next) => {
      pushed = true;
      if (loadFailedRef.current) {
        // A push that recovers from a failed first load also retires that load's alert.
        loadFailedRef.current = false;
        setProblem(null);
      }
      setLoadFailed(false);
      setFeed(next);
    });
    window.devteam.taskBoard().then(
      (initial) => {
        if (live && !pushed) setFeed(initial);
      },
      (error: unknown) => {
        if (!live) return;
        loadFailedRef.current = true;
        setLoadFailed(true);
        setProblem(`The task board could not be loaded: ${errorText(error)}`);
      },
    );
    window.devteam.projectNames().then(
      (each) => {
        if (live) setNames(each);
      },
      () => undefined, // the board falls back to directory names
    );
    window.devteam.boardSettings().then(
      (each) => {
        if (live) setSettings(each);
      },
      () => undefined, // the board falls back to the default thresholds
    );
    return () => {
      live = false;
      unsubscribe();
    };
  }, []);

  // Names can change on the Projects tab; re-read when this tab is shown again.
  useEffect(() => {
    if (!active) return;
    let live = true;
    window.devteam.projectNames().then(
      (each) => {
        if (live) setNames(each);
      },
      () => undefined,
    );
    return () => {
      live = false;
    };
  }, [active]);

  async function refresh() {
    setRefreshing(true);
    setProblem(null);
    try {
      setFeed(await window.devteam.refreshTaskBoard());
      loadFailedRef.current = false;
      setLoadFailed(false);
    } catch (error) {
      setProblem(`The task board could not be refreshed: ${errorText(error)}`);
    } finally {
      setRefreshing(false);
    }
  }

  const project = selected === null ? undefined : feed.projects.find((each) => each.project_id === selected);

  // A project that loses all its tasks leaves the kanban for good: a later snapshot that
  // brings it back must not pull the user into it again.
  useEffect(() => {
    if (selected !== null && project === undefined && !loadFailed && feed.status !== 'starting') {
      setSelected(null);
      setProjectGone(true);
    }
  }, [selected, project, loadFailed, feed.status]);

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
          <label className="text-sm" htmlFor="board-period">
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

      {problem !== null ? (
        <Alert variant="destructive">
          <CircleAlert />
          <AlertTitle>Something went wrong</AlertTitle>
          <AlertDescription>{problem}</AlertDescription>
        </Alert>
      ) : null}

      <StreamNotice feed={feed} />

      {projectGone && selected === null ? (
        <p className="text-sm text-muted-foreground" role="status">
          That project no longer has tasks.
        </p>
      ) : null}

      {loadFailed ? null : selected !== null && project !== undefined ? (
        <Kanban
          project={project}
          name={boardProjectName(project, names)}
          period={period}
          settings={settings}
          clock={clock}
          active={active}
          onBack={() => setSelected(null)}
        />
      ) : (
        <Overview
          feed={feed}
          names={names}
          period={period}
          now={now}
          onOpen={(projectId) => {
            setProjectGone(false);
            setSelected(projectId);
          }}
        />
      )}
    </section>
  );
}

function errorText(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
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
  onOpen,
}: {
  feed: BoardFeed;
  names: Readonly<Record<string, string>>;
  period: Period;
  now: number;
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
    if (feed.projects.length === 0 && feed.status !== 'live') {
      return <Empty>{feed.status === 'retrying' ? 'Reconnecting to the task stream…' : 'Loading the task board…'}</Empty>;
    }
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
      {view.stale > 0 || view.abandoned > 0 || view.withFindings > 0 ? (
        <span className="flex flex-wrap gap-2">
          {view.withFindings > 0 ? <FindingsBadge label={`${view.withFindings} with findings`} /> : null}
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

function FindingsBadge({ label }: { label: string }) {
  return (
    <Badge variant="outline" className="border-destructive text-foreground" title="Review found issues that are still to be fixed">
      <TriangleAlert aria-hidden="true" />
      {label}
    </Badge>
  );
}

/** The review badge of a card: the state is always in the words, never only in the colour. */
function ReviewBadge({ review }: { review: BoardReview }) {
  if (review.state === 'findings') {
    const n = review.findings;
    return <FindingsBadge label={n === null ? 'Findings' : `${n} ${n === 1 ? 'finding' : 'findings'}`} />;
  }
  return (
    <Badge
      variant="outline"
      className="border-warning text-foreground"
      title={review.state === 'pending' ? 'Waiting for the review result' : 'The review finished but its result has not been read yet'}
    >
      <Clock aria-hidden="true" />
      {review.state === 'pending' ? 'Awaiting review' : 'Result not read'}
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
  const label = `${counts.todo} to do, ${counts.in_progress} in progress, ${counts.in_review} in review, ${counts.done} done`;
  const segment = (value: number) => ({ flex: `${value} 1 0%` });
  return (
    <span role="img" aria-label={label} className="flex h-2 w-full overflow-hidden rounded-full bg-muted">
      <span className="bg-muted-foreground/40" style={segment(counts.todo)} />
      <span className="bg-warning" style={segment(counts.in_progress)} />
      <span className="bg-info" style={segment(counts.in_review)} />
      <span className="bg-success" style={segment(counts.done)} />
    </span>
  );
}

function CountsRow({ counts }: { counts: BoardCounts }) {
  const shares = percentLabels(counts);
  const cells: readonly { readonly label: string; readonly value: number; readonly dot: string; readonly share: number }[] = [
    { label: 'To do', value: counts.todo, dot: 'bg-muted-foreground/40', share: shares[0] },
    { label: 'In progress', value: counts.in_progress, dot: 'bg-warning', share: shares[1] },
    { label: 'In Review', value: counts.in_review, dot: 'bg-info', share: shares[2] },
    { label: 'Done', value: counts.done, dot: 'bg-success', share: shares[3] },
  ];
  return (
    <dl className="grid grid-cols-2 gap-2 text-xs sm:grid-cols-4">
      {cells.map((cell) => (
        <div key={cell.label}>
          <dt className="flex items-center gap-1 text-muted-foreground">
            <span aria-hidden="true" className={`inline-block size-2 rounded-full ${cell.dot}`} />
            {cell.label}
          </dt>
          <dd className="font-medium tabular-nums">
            {cell.value} <span className="text-muted-foreground">({cell.share}%)</span>
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
  clock,
  active,
  onBack,
}: {
  project: BoardProject;
  name: string;
  period: Period;
  settings: BoardSettings;
  clock: () => number;
  active: boolean;
  onBack: () => void;
}) {
  // Filtering (period cutoff, done retention) only needs whole minutes; the per-second
  // tick below exists for running cards alone, and only while one is on screen.
  const coarseNow = useNow(clock, 60, active);
  const [sessionId, setSessionId] = useState<string>('all');
  const [hideOldDone, setHideOldDone] = useState(true);
  const [onlyFindings, setOnlyFindings] = useState(false);
  const hideId = useId();
  const findingsId = useId();

  const sessionsInRange = useMemo(() => sessionsInPeriod(project, period, coarseNow), [project, period, coarseNow]);
  // A session that vanished from the snapshot or fell out of the period must not leave the filter selecting nothing.
  const effectiveSession = sessionsInRange.some((each) => each.session_id === sessionId) ? sessionId : 'all';
  const view = useMemo(
    () =>
      buildKanban(
        project,
        { sessionId: effectiveSession, period, hideOldDone, retentionDays: settings.doneRetentionDays, onlyFindings },
        coarseNow,
      ),
    [project, effectiveSession, period, hideOldDone, onlyFindings, settings.doneRetentionDays, coarseNow],
  );
  const anyRunning = [...view.todo, ...view.in_progress, ...view.in_review].some((item) => isRunning(item.session, item.task));
  const tick = useNow(clock, 1, active && anyRunning);
  const shownSessions = sessionsInRange.filter((each) => effectiveSession === 'all' || each.session_id === effectiveSession);

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
          {sessionsInRange.map((each) => (
            <option key={each.session_id} value={each.session_id}>
              {sessionLabel(each)}
            </option>
          ))}
        </select>
        <span className="flex items-center gap-2">
          <Checkbox id={hideId} checked={hideOldDone} onCheckedChange={(checked) => setHideOldDone(checked === true)} />
          <Label htmlFor={hideId} className="text-sm">
            Hide done older than {settings.doneRetentionDays} {settings.doneRetentionDays === 1 ? 'day' : 'days'}
          </Label>
        </span>
        <span className="flex items-center gap-2">
          <Checkbox id={findingsId} checked={onlyFindings} onCheckedChange={(checked) => setOnlyFindings(checked === true)} />
          <Label htmlFor={findingsId} className="text-sm">
            With findings
          </Label>
        </span>
      </div>

      <SessionStrip projectId={project.project_id} sessions={shownSessions} />

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Column title="To do" items={view.todo} now={tick} />
        <Column title="In progress" items={view.in_progress} now={tick} />
        <Column title="In Review" items={view.in_review} now={tick} />
        <Column
          title="Done"
          items={view.done}
          now={tick}
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
  const [copying, setCopying] = useState(false);
  const inFlight = useRef(false);
  const StatusIcon = STATUS_ICON[session.status];
  const where = session.branch ?? 'no branch';

  // A confirmation is about the command that was copied; it fades, and a new command voids it.
  useEffect(() => {
    if (message?.ok !== true) return;
    const timer = setTimeout(() => setMessage(null), COPIED_MESSAGE_MS);
    return () => clearTimeout(timer);
  }, [message]);
  useEffect(() => {
    setMessage(null);
  }, [session.resume_command]);

  async function copy() {
    if (inFlight.current) return;
    inFlight.current = true;
    setCopying(true);
    try {
      const answer = await window.devteam.copyResumeCommand({ projectId, sessionId: session.session_id });
      setMessage(answer.copied ? { ok: true, text: 'Resume command copied' } : { ok: false, text: answer.message });
    } catch (error) {
      setMessage({ ok: false, text: `Nothing was copied: ${errorText(error)}` });
    } finally {
      inFlight.current = false;
      setCopying(false);
    }
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
        {session.counts.todo} to do · {session.counts.in_progress} in progress
        {session.counts.in_review > 0 ? ` · ${session.counts.in_review} in review` : ''} · {session.counts.done} done
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
          disabled={session.resume_command === null || copying}
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
        <span className="rounded-full bg-muted px-2 text-xs font-medium tabular-nums">
          <span aria-hidden="true">{items.length}</span>
          <span className="sr-only">{items.length === 1 ? '1 task' : `${items.length} tasks`}</span>
        </span>
      </h4>
      {items.length === 0 ? (
        <p className="py-2 text-xs text-muted-foreground">Nothing here.</p>
      ) : (
        <ul className="space-y-2">
          {items.map((item) => (
            <TaskCard
              key={`${item.session.session_id}:${item.task.key}`}
              item={item}
              now={isRunning(item.session, item.task) ? now : 0}
            />
          ))}
        </ul>
      )}
      {note !== null ? <p className="mt-2 text-xs text-muted-foreground">{note}</p> : null}
    </section>
  );
}

/**
 * One task. The per-step times sit behind a disclosure button, not a hover tooltip: one tab
 * stop per card instead of two, nothing that overlaps its neighbours, and Escape closes it.
 */
const TaskCard = memo(function TaskCard({ item, now }: { item: KanbanItem; now: number }) {
  const { session, task } = item;
  const ids = useId();
  const contentId = `${ids}-content`;
  const detailId = `${ids}-steps`;
  const [open, setOpen] = useState(false);
  const toggle = useRef<HTMLButtonElement>(null);
  const running = isRunning(session, task);
  const inColumn = timeInColumn(session, task, now, running);
  const steps = stepDurations(task, now, running, inColumn);
  const where = session.branch ?? 'no branch';
  return (
    <li className="min-w-0">
      <article
        aria-labelledby={contentId}
        onKeyDown={(event) => {
          if (event.key === 'Escape' && open) {
            event.stopPropagation();
            setOpen(false);
            toggle.current?.focus();
          }
        }}
        className="rounded-md border bg-card p-3 text-sm text-card-foreground shadow-xs"
      >
        <p id={contentId} className={`break-words [overflow-wrap:anywhere] ${task.column === 'done' ? 'text-muted-foreground' : ''}`}>
          {task.content}
        </p>
        <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
          <span className="inline-flex items-center gap-1" title={`${providerLabel(session.provider)} session`}>
            <ProviderIcon provider={session.provider} />
            <span className="font-mono">{where}</span>
          </span>
          <span className="inline-flex items-center gap-1">
            <Clock className="size-3" aria-hidden="true" />
            <span className="sr-only">Time in this column: </span>
            {formatDuration(inColumn)}
          </span>
          {task.review !== null && task.column === 'in_review' ? <ReviewBadge review={task.review} /> : null}
          {task.stale ? <StaleBadge /> : null}
          {task.abandoned ? <AbandonedBadge /> : null}
          <button
            ref={toggle}
            type="button"
            aria-expanded={open}
            aria-controls={detailId}
            aria-label={`Time per step, ${task.content}`}
            onClick={() => setOpen((was) => !was)}
            className="inline-flex items-center gap-1 rounded-sm underline-offset-2 hover:underline focus-visible:ring-[3px] focus-visible:ring-ring/50 focus-visible:outline-hidden"
          >
            Time per step
            <ChevronDown className={`size-3 transition-transform ${open ? 'rotate-180' : ''}`} aria-hidden="true" />
          </button>
        </div>
        <div id={detailId} hidden={!open} className="mt-2 rounded-md border bg-muted/40 p-2 text-xs text-foreground">
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
      </article>
    </li>
  );
});

// ── settings ──────────────────────────────────────────────────────────────────

function BoardSettingsControl({ settings, onSaved }: { settings: BoardSettings; onSaved: (settings: BoardSettings) => void }) {
  const [open, setOpen] = useState(false);
  const [stale, setStale] = useState(String(settings.staleAfterMinutes));
  const [retention, setRetention] = useState(String(settings.doneRetentionDays));
  const [problem, setProblem] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const savingRef = useRef(false);
  const staleBounds = BOARD_SETTING_BOUNDS.staleAfterMinutes;
  const retentionBounds = BOARD_SETTING_BOUNDS.doneRetentionDays;

  useEffect(() => {
    if (!open) return;
    setStale(String(settings.staleAfterMinutes));
    setRetention(String(settings.doneRetentionDays));
    setProblem(null);
  }, [open, settings]);

  async function save(event: FormEvent) {
    event.preventDefault();
    if (savingRef.current) return;
    savingRef.current = true;
    setSaving(true);
    try {
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
    } catch (error) {
      setProblem(`The settings could not be saved: ${errorText(error)}`);
    } finally {
      savingRef.current = false;
      setSaving(false);
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
      <PopoverContent aria-label="Board settings" className="p-4">
        <form onSubmit={(event) => void save(event)} className="space-y-3">
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
          <Button size="sm" type="submit" disabled={saving}>
            Save
          </Button>
        </form>
      </PopoverContent>
    </Popover>
  );
}
