import { useEffect, useState } from 'react';
import { Bell, BellOff, CircleAlert, CircleArrowUp, CircleCheck, Info, TriangleAlert } from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Switch } from '@/components/ui/switch';
import type {
  AppNotification,
  BackgroundSettings,
  NotificationFeed,
  NotificationLevel,
  ProjectId,
} from '../shared/api.js';

const EMPTY: NotificationFeed = { status: 'starting', detail: null, items: [], unread: 0, paused: false };

const LEVEL_ICON: Readonly<Record<NotificationLevel, typeof Info>> = {
  info: Info,
  warning: TriangleAlert,
  critical: CircleAlert,
};

const LEVEL_TONE: Readonly<Record<NotificationLevel, string>> = {
  info: 'text-muted-foreground',
  warning: 'text-amber-600 dark:text-amber-500',
  critical: 'text-destructive',
};

const LEVEL_WORD: Readonly<Record<NotificationLevel, string>> = {
  info: 'Info',
  warning: 'Warning',
  critical: 'Critical',
};

interface Presentation {
  readonly icon: typeof Info;
  readonly tone: string;
  readonly word: string;
}

const INFORMATIVE_TONE = 'text-sky-600 dark:text-sky-400';

/**
 * Codes whose look is not their level's. The hook raises an available update as a
 * `warning` so a user can suppress it apart from applied ones, but nothing is wrong —
 * it reads as news, not as a problem.
 */
const CODE_PRESENTATION: Readonly<Record<string, Presentation>> = {
  'update.available': { icon: CircleArrowUp, tone: INFORMATIVE_TONE, word: 'Update available' },
  'update.applied': { icon: CircleCheck, tone: INFORMATIVE_TONE, word: 'Updated' },
};

function presentation(item: AppNotification): Presentation {
  return (
    CODE_PRESENTATION[item.code] ?? {
      icon: LEVEL_ICON[item.level],
      tone: LEVEL_TONE[item.level],
      word: LEVEL_WORD[item.level],
    }
  );
}

/**
 * The header's bell: what the hooks raised, newest first, and the controls for how the
 * app delivers it.
 *
 * The feed is owned by the main process, which shows each notification natively the
 * moment it lands — with this window closed, too. This component only mirrors it: it
 * subscribes, renders, and tells the main process when the list has been looked at.
 */
export function NotificationBell({ onOpenProject }: { onOpenProject: (projectId: ProjectId) => void }) {
  const [feed, setFeed] = useState<NotificationFeed>(EMPTY);
  const [background, setBackground] = useState<BackgroundSettings | null>(null);
  const [open, setOpen] = useState(false);
  const [backgroundError, setBackgroundError] = useState<string | null>(null);

  useEffect(() => {
    let live = true;
    // A refused or failed read leaves the empty feed; the subscription below still fills it.
    window.devteam
      .notificationFeed()
      .then((initial) => {
        if (live) setFeed(initial);
      })
      .catch(() => undefined);
    const unsubscribe = window.devteam.onNotificationFeed((next) => setFeed(next));
    return () => {
      live = false;
      unsubscribe();
    };
  }, []);

  useEffect(() => {
    if (!open) return;
    // Opening the list is reading it.
    // Marking read is best effort: on a failure the list stays as it was.
    window.devteam.markNotificationsRead().then(setFeed).catch(() => undefined);
    window.devteam
      .backgroundSettings()
      .then((next) => {
        setBackground(next);
        setBackgroundError(null);
      })
      .catch((error: unknown) => setBackgroundError(errorText(error)));
  }, [open]);

  const label =
    feed.unread > 0 ? `Notifications, ${feed.unread} new` : feed.paused ? 'Notifications, paused' : 'Notifications';
  const BellIcon = feed.paused ? BellOff : Bell;

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button variant="ghost" size="sm" aria-label={label} title={label} className="relative">
          <BellIcon className="size-4" aria-hidden="true" />
          {feed.unread > 0 ? (
            <span
              aria-hidden="true"
              className="absolute -top-0.5 -right-0.5 min-w-4 rounded-full bg-primary px-1 text-center text-[10px] leading-4 font-semibold text-primary-foreground"
            >
              {feed.unread > 99 ? '99+' : feed.unread}
            </span>
          ) : null}
        </Button>
      </PopoverTrigger>
      <PopoverContent aria-label="Notifications">
        <div className="flex items-center justify-between border-b px-4 py-3">
          <h2 className="text-sm font-semibold">Notifications</h2>
          <StreamStatus feed={feed} />
        </div>

        {feed.items.length === 0 ? (
          <p className="px-4 py-6 text-center text-sm text-muted-foreground">
            Nothing yet. Notices from your agent sessions appear here and as system notifications.
          </p>
        ) : (
          <ul className="max-h-80 divide-y overflow-auto">
            {feed.items.map((item) => (
              <NotificationRow
                key={item.id}
                item={item}
                onOpen={() => {
                  setOpen(false);
                  onOpenProject(item.projectId);
                }}
              />
            ))}
          </ul>
        )}

        <div className="space-y-3 border-t px-4 py-3">
          <div className="flex items-center justify-between gap-3">
            <Label htmlFor="notifications-paused" className="text-sm">
              Pause system notifications
            </Label>
            <Switch
              id="notifications-paused"
              checked={feed.paused}
              // A failure keeps the previous state: the switch is controlled by `feed.paused`.
              onCheckedChange={(checked) => {
                window.devteam.setNotificationsPaused(checked).then(setFeed).catch(() => undefined);
              }}
            />
          </div>
          <LoginItemControl settings={background} loadError={backgroundError} onChange={setBackground} />
        </div>
      </PopoverContent>
    </Popover>
  );
}

function NotificationRow({ item, onOpen }: { item: AppNotification; onOpen: () => void }) {
  const { icon: Icon, tone, word } = presentation(item);
  return (
    <li>
      <button
        type="button"
        onClick={onOpen}
        className="flex w-full items-start gap-3 px-4 py-3 text-left hover:bg-accent focus-visible:bg-accent focus-visible:outline-hidden"
      >
        {/* The icon is not the only signal: its word is in the accessible name. */}
        <Icon className={`mt-0.5 size-4 shrink-0 ${tone}`} aria-hidden="true" />
        <span className="min-w-0 flex-1">
          <span className="flex items-baseline justify-between gap-2">
            <span className="truncate text-sm font-medium">{item.projectName}</span>
            <time className="shrink-0 text-xs text-muted-foreground" dateTime={new Date(item.ts * 1000).toISOString()}>
              {relativeTime(item.ts)}
            </time>
          </span>
          <span className="sr-only">{word}: </span>
          <span className="block text-sm whitespace-pre-line text-muted-foreground">{item.message}</span>
        </span>
      </button>
    </li>
  );
}

function StreamStatus({ feed }: { feed: NotificationFeed }) {
  if (feed.status === 'live') {
    return (
      <Badge variant="outline" className="text-xs">
        live
      </Badge>
    );
  }
  const word = feed.status === 'unavailable' ? 'off' : feed.status === 'retrying' ? 'reconnecting' : 'starting';
  return (
    <Badge variant={feed.status === 'unavailable' ? 'destructive' : 'secondary'} className="text-xs" title={feed.detail ?? undefined}>
      {word}
    </Badge>
  );
}

/**
 * "Start at login", with what the OS actually recorded beside it. The switch shows the
 * user's choice; the line under it is the system's answer, and on an unsigned macOS build
 * the two can differ — which this says rather than hides.
 */
function LoginItemControl({
  settings,
  loadError,
  onChange,
}: {
  settings: BackgroundSettings | null;
  loadError: string | null;
  onChange: (settings: BackgroundSettings) => void;
}) {
  // A refused change keeps the previous settings and puts the reason where `detail` goes.
  const [changeError, setChangeError] = useState<string | null>(null);
  if (settings === null) {
    return loadError === null ? null : (
      <p className="text-xs text-destructive">Could not read the start-at-login setting: {loadError}</p>
    );
  }
  const disabled = settings.loginItemStatus === 'unsupported';
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between gap-3">
        <Label htmlFor="open-at-login" className="text-sm">
          Start at login, in the background
        </Label>
        <Switch
          id="open-at-login"
          checked={settings.openAtLogin}
          disabled={disabled}
          onCheckedChange={(checked) => {
            setChangeError(null);
            window.devteam
              .setOpenAtLogin(checked)
              .then(onChange)
              .catch((error: unknown) => setChangeError(errorText(error)));
          }}
        />
      </div>
      {changeError !== null ? (
        <p className="text-xs text-destructive">{changeError}</p>
      ) : settings.detail !== null ? (
        <p className="text-xs text-muted-foreground">{settings.detail}</p>
      ) : null}
    </div>
  );
}

function errorText(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

function relativeTime(epochSeconds: number): string {
  const seconds = Math.max(0, Math.round(Date.now() / 1000 - epochSeconds));
  if (seconds < 60) return 'just now';
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours} h ago`;
  return new Date(epochSeconds * 1000).toLocaleDateString();
}
