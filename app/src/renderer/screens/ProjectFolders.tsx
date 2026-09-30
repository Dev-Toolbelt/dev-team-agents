/**
 * The Projects screen's folders (ADR-0021): the state hook and the pieces the table is
 * built from. The model and every rule live in `shared/projectFolders.ts`; this file only
 * renders them and saves through the bridge.
 */
import { useEffect, useRef, useState, type DragEvent, type ReactNode } from 'react';
import {
  Check,
  ChevronRight,
  Folder,
  FolderInput,
  FolderMinus,
  FolderOpen,
  FolderPlus,
  MoreHorizontal,
  Pencil,
  Trash2,
  X,
} from 'lucide-react';

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
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { TableCell, TableRow } from '@/components/ui/table';
import { cn } from '@/lib/utils';
import { WriteButton } from '../WriteButton.js';
import type { EnvironmentReport } from '../../shared/api.js';
import {
  canNestIn,
  flattenFolderTree,
  NO_FOLDERS,
  pruneMembership,
  type FolderNode,
  type ProjectFolder,
  type ProjectFolders,
  type ProjectFoldersAnswer,
} from '../../shared/projectFolders.js';

/** The drop-target key for "no folder". Never a valid folder id (ids have no underscore). */
export const NO_FOLDER_KEY = '__none__';

export function projectCount(count: number): string {
  return `${count} project${count === 1 ? '' : 's'}`;
}

/**
 * The folder state, applied optimistically and saved in order.
 *
 * Every change is shown at once and queued for saving. A refused or failed save puts the
 * screen back to the last state the main process accepted and says why; any change queued
 * after the failed one was built on top of it, so it is dropped rather than saved, and the
 * message counts it.
 *
 * **Until the stored folders have been read, nothing can be changed.** A read that failed
 * is not "no folders": treating it as one would let the user's first move save an empty
 * grouping over the real one. `ready` stays false, the screen says so and offers a retry.
 */
export function useProjectFolders(boundIds: ReadonlySet<string> | null) {
  const [folders, setFolders] = useState<ProjectFolders>(NO_FOLDERS);
  const [phase, setPhase] = useState<'loading' | 'ready' | 'unavailable'>('loading');
  const [readNonce, setReadNonce] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState('');
  const latest = useRef<ProjectFolders>(NO_FOLDERS);
  const confirmed = useRef<ProjectFolders>(NO_FOLDERS);
  const queue = useRef<Promise<void>>(Promise.resolve());
  const generation = useRef(0);
  const failure = useRef({ message: '', dropped: 0 });
  const ready = phase === 'ready';

  useEffect(() => {
    let live = true;
    setPhase('loading');
    void window.devteam.projectFolders().then(
      (read) => {
        if (!live) return;
        latest.current = read;
        confirmed.current = read;
        setFolders(read);
        setPhase('ready');
      },
      () => {
        if (live) setPhase('unavailable');
      },
    );
    return () => {
      live = false;
    };
  }, [readNonce]);

  /** A silent change that fails is undone silently too: the user never asked for it. */
  function rollBack(message: string, silent: boolean): void {
    generation.current += 1;
    failure.current = { message: silent ? 'The folders could not be saved.' : message, dropped: 0 };
    latest.current = confirmed.current;
    setFolders(confirmed.current);
    if (silent) return;
    setStatus('');
    setError(message);
  }

  /**
   * `silent` is for housekeeping the user did not ask for: it neither announces anything
   * nor clears an error the user has not read yet.
   */
  function apply(transform: (state: ProjectFolders) => ProjectFolders, options: { announce?: string; silent?: boolean } = {}): void {
    if (!ready) return;
    const silent = options.silent === true;
    const next = transform(latest.current);
    if (next === latest.current) return;
    latest.current = next;
    setFolders(next);
    if (!silent) {
      setError(null);
      setStatus(options.announce ?? '');
    }
    const started = generation.current;
    const save = async (): Promise<void> => {
      if (started !== generation.current) {
        failure.current.dropped += 1;
        const { message, dropped } = failure.current;
        setError(`${message} ${dropped} later change${dropped === 1 ? ' was' : 's were'} undone with it.`);
        return;
      }
      try {
        const answer: ProjectFoldersAnswer = await window.devteam.saveProjectFolders(next);
        if (answer.ok) confirmed.current = answer.folders;
        else rollBack(answer.message, silent);
      } catch (reason) {
        rollBack(`The folders could not be saved: ${String(reason)}`, silent);
      }
    };
    // The terminal `catch` keeps one unexpected throw from poisoning every later save.
    queue.current = queue.current.then(save).catch(() => undefined);
  }

  // A project unbound since it was filed leaves a dangling entry; drop it on the next
  // listing, silently — it is housekeeping, not something the user did.
  useEffect(() => {
    if (!ready || boundIds === null) return;
    apply((state) => pruneMembership(state, boundIds), { silent: true });
  }, [ready, boundIds]);

  return {
    folders,
    ready,
    unavailable: phase === 'unavailable',
    retry: () => setReadNonce((n) => n + 1),
    error,
    status,
    apply,
    dismissError: () => setError(null),
  };
}

// ── dialogs ─────────────────────────────────────────────────────────────────────

/** `value` while it is non-null, then the last non-null value — for content that animates out. */
export function useLastDefined<T>(value: T | null): T | null {
  const last = useRef(value);
  if (value !== null) last.current = value;
  return value ?? last.current;
}

/** Create or rename. `problemFor` is `folderNameProblem` bound to the right siblings. */
export function FolderNameDialog({
  open,
  onOpenChange,
  title,
  description,
  initialName = '',
  submitLabel,
  problemFor,
  onSubmit,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description: string;
  initialName?: string;
  submitLabel: string;
  problemFor: (name: string) => string | null;
  onSubmit: (name: string) => void;
}) {
  const [name, setName] = useState(initialName);
  const [touched, setTouched] = useState(false);
  useEffect(() => {
    if (open) {
      setName(initialName);
      setTouched(false);
    }
  }, [open, initialName]);
  const problem = problemFor(name);
  const unchanged = initialName !== '' && name.trim() === initialName.trim();

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <form
          className="grid gap-4"
          onSubmit={(event) => {
            event.preventDefault();
            setTouched(true);
            if (unchanged) onOpenChange(false);
            else if (problem === null) {
              onSubmit(name.trim());
              onOpenChange(false);
            }
          }}
        >
          <DialogHeader>
            <DialogTitle>{title}</DialogTitle>
            <DialogDescription>{description}</DialogDescription>
          </DialogHeader>
          <div className="grid gap-2">
            <Label htmlFor="folder-name">Name</Label>
            <Input
              id="folder-name"
              autoFocus
              value={name}
              placeholder="e.g. Sites, Online stores, Apps"
              aria-invalid={touched && problem !== null && !unchanged}
              aria-describedby="folder-name-problem"
              onChange={(event) => {
                setName(event.target.value);
                setTouched(true);
              }}
            />
            <p id="folder-name-problem" className="min-h-4 text-xs text-destructive" aria-live="polite">
              {touched && !unchanged && name.trim() !== '' ? problem : null}
            </p>
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={problem !== null && !unchanged}>
              {submitLabel}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

export function DeleteFolderDialog({
  folder,
  memberCount,
  onOpenChange,
  onConfirm,
}: {
  folder: ProjectFolder | null;
  memberCount: number;
  onOpenChange: (open: boolean) => void;
  onConfirm: () => void;
}) {
  // The last folder shown, so the title does not go blank during the close animation.
  const shown = useLastDefined(folder);
  return (
    <Dialog open={folder !== null} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Delete the folder “{shown?.name}”?</DialogTitle>
          <DialogDescription>
            {memberCount === 0
              ? 'The folder is empty.'
              : `Its ${projectCount(memberCount)} will move to “No folder”.`}{' '}
            No project is unbound, and nothing in any project changes.
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            variant="destructive"
            onClick={() => {
              onConfirm();
              onOpenChange(false);
            }}
          >
            Delete folder
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ── menus ───────────────────────────────────────────────────────────────────────

/** Visible as a check, read as words: an icon's own label is not reliably exposed. */
function CurrentMark() {
  return (
    <>
      <Check className="ml-auto" aria-hidden="true" />
      <span className="sr-only">(current folder)</span>
    </>
  );
}

/**
 * The "Move to" menu, shared by the row action and the bulk bar. The keyboard path to
 * everything drag and drop does — drag and drop is never the only way to file a project.
 */
export function MoveToMenu({
  tree,
  current,
  onMove,
  onNewFolder,
  trigger,
  disabled = false,
}: {
  disabled?: boolean;
  tree: readonly FolderNode[];
  /** The folder every moved project is already in, when they share one; `undefined` when mixed. */
  current: string | null | undefined;
  onMove: (folderId: string | null) => void;
  onNewFolder: () => void;
  trigger: ReactNode;
}) {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild disabled={disabled}>
        {trigger}
      </DropdownMenuTrigger>
      <DropdownMenuContent className="w-56">
        <DropdownMenuLabel>Move to</DropdownMenuLabel>
        {flattenFolderTree(tree).map((node) => (
          <DropdownMenuItem
            key={node.folder.id}
            disabled={current === node.folder.id}
            onSelect={() => onMove(node.folder.id)}
            style={{ paddingLeft: `${0.5 + (node.depth - 1) * 1}rem` }}
          >
            <Folder />
            <span className="truncate">{node.folder.name}</span>
            {current === node.folder.id ? <CurrentMark /> : null}
          </DropdownMenuItem>
        ))}
        <DropdownMenuItem disabled={current === null} onSelect={() => onMove(null)}>
          <FolderMinus />
          No folder
          {current === null ? <CurrentMark /> : null}
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem onSelect={onNewFolder}>
          <FolderPlus />
          New folder…
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

// ── table pieces ────────────────────────────────────────────────────────────────

export function FolderHeaderRow({
  node,
  folders,
  count,
  expanded,
  forcedOpen,
  selection,
  onToggleSelection,
  onToggleExpanded,
  onRename,
  onDelete,
  onNewSubfolder,
  columns,
  editable,
}: {
  /** False until the stored folders have been read. */
  editable: boolean;
  node: FolderNode;
  folders: readonly ProjectFolder[];
  /** Visible projects, including those in subfolders. */
  count: number;
  expanded: boolean;
  /** A text filter is showing the folder's matches regardless of its collapsed state. */
  forcedOpen: boolean;
  selection: boolean | 'indeterminate';
  onToggleSelection: (checked: boolean) => void;
  onToggleExpanded: () => void;
  onRename: () => void;
  onDelete: () => void;
  onNewSubfolder: () => void;
  columns: number;
}) {
  const { folder, depth } = node;
  const Icon = expanded ? FolderOpen : Folder;
  return (
    <TableRow className="bg-muted/50 hover:bg-muted/60" data-folder-header={folder.id}>
      <TableCell className="w-14">
        <Checkbox
          checked={selection}
          disabled={count === 0}
          onCheckedChange={(checked) => onToggleSelection(checked === true)}
          aria-label={`Select every project in ${folder.name}`}
        />
      </TableCell>
      <TableCell colSpan={columns - 2}>
        <button
          type="button"
          onClick={() => {
            if (!forcedOpen) onToggleExpanded();
          }}
          // `aria-disabled`, not `disabled`: a disabled button leaves the tab order, and the
          // folder would vanish from keyboard navigation for as long as a filter is typed.
          aria-disabled={forcedOpen}
          aria-expanded={expanded}
          title={forcedOpen ? 'Open while the filter shows its matches' : undefined}
          className="group inline-flex items-center gap-2 rounded-sm font-semibold outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50 aria-disabled:cursor-default"
          style={{ paddingLeft: `${(depth - 1) * 1.25}rem` }}
        >
          <ChevronRight
            className={cn('size-4 text-muted-foreground transition-transform', expanded && 'rotate-90')}
            aria-hidden="true"
          />
          <Icon className="size-4 text-primary" aria-hidden="true" />
          <span>{folder.name}</span>
          <span className="rounded-full bg-background px-2 py-0.5 text-xs font-normal text-muted-foreground">
            {count}
          </span>
        </button>
      </TableCell>
      <TableCell className="text-right">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon-xs" disabled={!editable} aria-label={`Folder actions for ${folder.name}`}>
              <MoreHorizontal />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent>
            <DropdownMenuItem onSelect={onRename}>
              <Pencil />
              Rename…
            </DropdownMenuItem>
            {canNestIn(folders, folder.id) ? (
              <DropdownMenuItem onSelect={onNewSubfolder}>
                <FolderPlus />
                New subfolder…
              </DropdownMenuItem>
            ) : null}
            <DropdownMenuSeparator />
            <DropdownMenuItem variant="destructive" onSelect={onDelete}>
              <Trash2 />
              Delete folder…
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </TableCell>
    </TableRow>
  );
}

export function NoFolderHeaderRow({
  count,
  selection,
  onToggleSelection,
  columns,
}: {
  count: number;
  selection: boolean | 'indeterminate';
  onToggleSelection: (checked: boolean) => void;
  columns: number;
}) {
  return (
    <TableRow className="bg-muted/50 hover:bg-muted/60" data-folder-header={NO_FOLDER_KEY}>
      <TableCell className="w-14">
        <Checkbox
          checked={selection}
          disabled={count === 0}
          onCheckedChange={(checked) => onToggleSelection(checked === true)}
          aria-label="Select every project in no folder"
        />
      </TableCell>
      <TableCell colSpan={columns - 1}>
        <span className="inline-flex items-center gap-2 font-semibold text-muted-foreground">
          <FolderMinus className="size-4" aria-hidden="true" />
          No folder
          <span className="rounded-full bg-background px-2 py-0.5 text-xs font-normal">{count}</span>
        </span>
      </TableCell>
    </TableRow>
  );
}

export function EmptyGroupRow({ columns, children }: { columns: number; children: ReactNode }) {
  return (
    <TableRow className="hover:bg-transparent">
      <TableCell colSpan={columns} className="py-3 text-center text-xs text-muted-foreground">
        {children}
      </TableCell>
    </TableRow>
  );
}

export interface BulkSyncState {
  readonly phase: 'idle' | 'running' | 'done';
  readonly done: number;
  readonly total: number;
  readonly failures: readonly { readonly id: string; readonly name: string; readonly message: string }[];
  /** The user stopped the run before every project was synced. */
  readonly stopped: boolean;
}

export function BulkActionBar({
  count,
  tree,
  current,
  anyInFolder,
  environment,
  bulkSync,
  editable,
  syncBlocked,
  onMove,
  onNewFolder,
  onSync,
  onCancelSync,
  onClear,
}: {
  /** False until the stored folders have been read. */
  editable: boolean;
  /** Another sync (Sync all, or a row's) is running. */
  syncBlocked: boolean;
  onCancelSync: () => void;
  count: number;
  tree: readonly FolderNode[];
  current: string | null | undefined;
  anyInFolder: boolean;
  environment: EnvironmentReport | null;
  bulkSync: BulkSyncState;
  onMove: (folderId: string | null) => void;
  onNewFolder: () => void;
  onSync: () => void;
  onClear: () => void;
}) {
  const running = bulkSync.phase === 'running';
  return (
    // A labelled region, not `role="toolbar"`: a toolbar promises arrow-key navigation
    // between its controls, which these plain buttons do not implement.
    <div
      role="region"
      aria-label="Actions for the selected projects"
      className="sticky top-0 z-10 flex flex-wrap items-center gap-2 rounded-md border border-primary/30 bg-primary/5 px-3 py-2 shadow-sm backdrop-blur"
    >
      <span className="text-sm font-medium" aria-live="polite">
        {count} selected
      </span>
      <span className="mx-1 h-4 w-px bg-border" aria-hidden="true" />
      <MoveToMenu
        tree={tree}
        current={current}
        onMove={onMove}
        onNewFolder={onNewFolder}
        disabled={!editable}
        trigger={
          <Button variant="outline" size="xs" disabled={!editable}>
            <FolderInput />
            Move to…
          </Button>
        }
      />
      <Button variant="outline" size="xs" disabled={!editable || !anyInFolder} onClick={() => onMove(null)}>
        <FolderMinus />
        Remove from folder
      </Button>
      <WriteButton
        command="sync"
        environment={environment}
        variant="outline"
        size="xs"
        tooltip={
          syncBlocked
            ? 'Another sync is running; this waits for it to finish'
            : 'Re-apply the store version to each selected project, one after another'
        }
        disabled={running || syncBlocked}
        onClick={onSync}
      >
        {running ? `Syncing ${Math.min(bulkSync.done + 1, bulkSync.total)} of ${bulkSync.total}…` : 'Sync selected'}
      </WriteButton>
      {running ? (
        <Button variant="outline" size="xs" onClick={onCancelSync}>
          Stop after this one
        </Button>
      ) : null}
      <Button variant="ghost" size="xs" className="ml-auto" onClick={onClear} disabled={running}>
        <X />
        Clear selection
      </Button>
    </div>
  );
}

/**
 * The image under the pointer while dragging: a small chip naming what moves, instead of
 * the browser's snapshot of a single table cell. Removed once the browser has copied it.
 */
export function setDragChip(event: DragEvent, label: string): void {
  const transfer = event.dataTransfer as DataTransfer | undefined;
  if (transfer === undefined || transfer === null) return;
  transfer.effectAllowed = 'move';
  transfer.setData('text/plain', label);
  if (typeof transfer.setDragImage !== 'function') return;
  const chip = document.createElement('div');
  chip.textContent = label;
  chip.className = 'fixed -top-24 left-0 rounded-md bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground shadow-lg';
  document.body.appendChild(chip);
  transfer.setDragImage(chip, 12, 12);
  setTimeout(() => chip.remove(), 0);
}
