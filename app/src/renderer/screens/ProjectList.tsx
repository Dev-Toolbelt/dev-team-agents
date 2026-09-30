/**
 * The Projects screen's table: rows grouped by folder (ADR-0021), selection, drag and drop,
 * bulk actions, and the sync coordination every sync button on the screen shares.
 *
 * `Projects.tsx` owns the listing and the filters and hands this the result; this owns
 * everything about how the rows are arranged and acted on in bulk.
 */
import { useEffect, useMemo, useRef, useState, type DragEvent, type ReactNode } from 'react';
import { AlertTriangle, CheckCircle2, FolderInput, FolderPlus } from 'lucide-react';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Table, TableBody, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Hint } from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';
import { Empty } from '../Problem.js';
import { unreachable } from '../useOperation.js';
import {
  BulkActionBar,
  DeleteFolderDialog,
  EmptyGroupRow,
  FolderHeaderRow,
  FolderNameDialog,
  MoveToMenu,
  NO_FOLDER_KEY,
  projectCount,
  setDragChip,
  useLastDefined,
  useProjectFolders,
  type BulkSyncState,
} from './ProjectFolders.js';
import { displayName, ProjectRow, type RowSyncState } from './ProjectRow.js';
import type { EnvironmentReport, ProjectRecord } from '../../shared/api.js';
import {
  buildFolderTree,
  createFolder,
  deleteFolder,
  folderNameProblem,
  folderOf,
  moveProjects,
  renameFolder,
  setFolderCollapsed,
  type FolderNode,
  type ProjectFolder,
} from '../../shared/projectFolders.js';

type FolderDialog =
  | { readonly kind: 'create'; readonly parentId: string | null; readonly moveIds: readonly string[] }
  | { readonly kind: 'rename'; readonly folder: ProjectFolder }
  | null;

/** The selection cell (checkbox and drag handle share it), then the six data columns. */
const COLUMNS = 7;

const IDLE_BULK: BulkSyncState = { phase: 'idle', done: 0, total: 0, failures: [], stopped: false };
const IDLE_ROW: RowSyncState = { phase: 'idle' };

/** Folder ids stay short and URL-safe; `crypto.randomUUID` needs a secure context the renderer may not be. */
function newFolderId(): string {
  const bytes = crypto.getRandomValues(new Uint8Array(12));
  return Array.from(bytes, (byte) => byte.toString(16).padStart(2, '0')).join('');
}

/**
 * Every sync the screen can start, in one place, so none runs beside another: each takes the
 * store lock, and two at once would report contention as a failure. Row state lives here
 * rather than in the row, so a row that remounts — because it moved to another folder —
 * keeps its in-flight state and its result.
 */
export function useProjectSyncs(onChanged: () => void) {
  const [rows, setRows] = useState<ReadonlyMap<string, RowSyncState>>(new Map());
  const [bulk, setBulk] = useState<BulkSyncState>(IDLE_BULK);
  const changed = useRef(onChanged);
  changed.current = onChanged;
  const mounted = useRef(true);
  const stop = useRef(false);
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);

  function setRow(id: string, state: RowSyncState): void {
    if (!mounted.current) return;
    setRows((previous) => new Map(previous).set(id, state));
  }

  async function runRow(id: string): Promise<void> {
    setRow(id, { phase: 'pending' });
    const result = await window.devteam.syncProject(id).catch(unreachable);
    setRow(id, { phase: 'done', result });
    if (result.ok && mounted.current) changed.current();
  }

  async function runBulk(targets: readonly { readonly id: string; readonly name: string }[]): Promise<void> {
    stop.current = false;
    const failures: { id: string; name: string; message: string }[] = [];
    setBulk({ phase: 'running', done: 0, total: targets.length, failures, stopped: false });
    let done = 0;
    for (const target of targets) {
      // Stops between projects, never mid-sync, and never after the screen is gone.
      if (stop.current || !mounted.current) break;
      const result = await window.devteam.syncProject(target.id).catch(unreachable);
      if (!result.ok) failures.push({ id: target.id, name: target.name, message: result.message });
      done += 1;
      if (mounted.current) setBulk({ phase: 'running', done, total: targets.length, failures: [...failures], stopped: false });
    }
    if (!mounted.current) return;
    setBulk({ phase: 'done', done, total: targets.length, failures, stopped: done < targets.length });
    changed.current();
  }

  const rowPending = [...rows.values()].some((state) => state.phase === 'pending');
  return {
    rowState: (id: string): RowSyncState => rows.get(id) ?? IDLE_ROW,
    runRow: (id: string) => void runRow(id),
    bulk,
    runBulk: (targets: readonly { readonly id: string; readonly name: string }[]) => void runBulk(targets),
    stopBulk: () => {
      stop.current = true;
    },
    dismissBulk: () => setBulk(IDLE_BULK),
    /** Any sync this hook started is still running. */
    busy: rowPending || bulk.phase === 'running',
  };
}

export type ProjectSyncs = ReturnType<typeof useProjectSyncs>;

export function ProjectList({
  projects,
  filteredProjects,
  filtering,
  textFiltering,
  projectNames,
  environment,
  current,
  syncs,
  syncAllPending,
  onChanged,
  onOpenSettings,
}: {
  projects: readonly ProjectRecord[];
  filteredProjects: readonly ProjectRecord[];
  /** Any filter narrows the list. */
  filtering: boolean;
  /** The text filter specifically: it opens collapsed folders that hold a match. */
  textFiltering: boolean;
  projectNames: Readonly<Record<string, string>>;
  environment: EnvironmentReport | null;
  current: string | null;
  syncs: ProjectSyncs;
  syncAllPending: boolean;
  onChanged: () => void;
  onOpenSettings: (projectId: string) => void;
}) {
  // Only ever mounted for a successful listing, so these are the bound projects: pruning
  // against them can never run on a failed or loading `list`.
  const boundIds = useMemo(() => new Set(projects.map((project) => project.project_id)), [projects]);
  const { folders, ready, unavailable, retry, error, status, apply, dismissError } = useProjectFolders(boundIds);
  const [selected, setSelected] = useState<ReadonlySet<string>>(new Set());
  const [folderDialog, setFolderDialog] = useState<FolderDialog>(null);
  const shownDialog = useLastDefined(folderDialog);
  const [deleting, setDeleting] = useState<ProjectFolder | null>(null);
  const shownDeleting = useLastDefined(deleting);
  // What is being dragged, held here rather than read from `dataTransfer`: the browser
  // hides a drag's data until the drop, and `dragover` must decide whether to accept it.
  const [dragging, setDragging] = useState<readonly string[] | null>(null);
  const [dropTarget, setDropTarget] = useState<string | null>(null);

  const hasFolders = folders.folders.length > 0;
  const tree = buildFolderTree(folders);
  const knownFolders = new Set(folders.folders.map((folder) => folder.id));
  const byFolder = new Map<string | null, ProjectRecord[]>();
  for (const project of filteredProjects) {
    const folderId = folderOf(folders, project.project_id);
    const key = folderId !== null && knownFolders.has(folderId) ? folderId : null;
    byFolder.set(key, [...(byFolder.get(key) ?? []), project]);
  }
  const noFolderRows = byFolder.get(null) ?? [];

  const isExpanded = (folder: ProjectFolder): boolean => !folder.collapsed || textFiltering;
  function deepRows(node: FolderNode): ProjectRecord[] {
    return [...(byFolder.get(node.folder.id) ?? []), ...node.children.flatMap(deepRows)];
  }
  /** The rows actually on screen: a collapsed folder's rows are not. */
  function renderedRows(node: FolderNode): ProjectRecord[] {
    if (!isExpanded(node.folder)) return [];
    return [...(byFolder.get(node.folder.id) ?? []), ...node.children.flatMap(renderedRows)];
  }
  const shownRows = hasFolders ? [...tree.flatMap(renderedRows), ...noFolderRows] : filteredProjects;
  const visibleIds = shownRows.map((project) => project.project_id);
  // Bulk actions act on what is selected **and on screen**: a row a filter hid, or a
  // collapsed folder hides, is never moved or synced by a button whose count the user sees.
  const selectedVisible = visibleIds.filter((id) => selected.has(id));
  const nameOf = (id: string): string => {
    const project = projects.find((candidate) => candidate.project_id === id);
    return project === undefined ? id : displayName(project.path, project.project_id, projectNames);
  };
  const syncBlocked = syncAllPending || syncs.busy;

  function selectionOf(ids: readonly string[]): boolean | 'indeterminate' {
    const count = ids.filter((id) => selected.has(id)).length;
    if (count === 0) return false;
    return count === ids.length ? true : 'indeterminate';
  }

  function select(ids: readonly string[], checked: boolean): void {
    setSelected((previous) => {
      const next = new Set(previous);
      for (const id of ids) {
        if (checked) next.add(id);
        else next.delete(id);
      }
      return next;
    });
  }

  /** The folder every one of `ids` is in, or `undefined` when they are spread across several. */
  function sharedFolder(ids: readonly string[]): string | null | undefined {
    const found = new Set(ids.map((id) => folderOf(folders, id)));
    return found.size === 1 ? [...found][0] : undefined;
  }

  function move(ids: readonly string[], folderId: string | null, clearSelection = false): void {
    const target = folders.folders.find((folder) => folder.id === folderId);
    // A folder deleted between opening a menu and choosing from it: nothing to move into.
    if (folderId !== null && target === undefined) return;
    const moving = ids.filter((id) => folderOf(folders, id) !== folderId);
    if (clearSelection) setSelected(new Set());
    if (moving.length === 0) return;
    const subject = moving.length === 1 ? nameOf(moving[0]!) : projectCount(moving.length);
    apply((state) => moveProjects(state, moving, folderId), {
      announce: target === undefined ? `Moved ${subject} out of its folder.` : `Moved ${subject} to “${target.name}”.`,
    });
  }

  function dropHandlers(key: string) {
    const folderId = key === NO_FOLDER_KEY ? null : key;
    return {
      onDragOver: (event: DragEvent<HTMLTableSectionElement>) => {
        if (dragging === null) return;
        event.preventDefault();
        if (event.dataTransfer) event.dataTransfer.dropEffect = 'move';
        if (dropTarget !== key) setDropTarget(key);
      },
      onDragLeave: (event: DragEvent<HTMLTableSectionElement>) => {
        if (event.currentTarget.contains(event.relatedTarget as Node | null)) return;
        setDropTarget((previous) => (previous === key ? null : previous));
      },
      onDrop: (event: DragEvent<HTMLTableSectionElement>) => {
        event.preventDefault();
        if (dragging !== null) move(dragging, folderId, dragging.length > 1);
        setDragging(null);
        setDropTarget(null);
      },
    };
  }

  function groupBody(key: string, header: ReactNode, rows: readonly ProjectRecord[], expanded: boolean, emptyText: string, depth: number) {
    return (
      <TableBody
        key={key}
        data-drop-target={key}
        {...dropHandlers(key)}
        className={cn(
          'border-t-8 border-background transition-colors',
          dropTarget === key && '[&>tr]:!bg-primary/10 [&>tr:first-child]:outline-2 [&>tr:first-child]:-outline-offset-2 [&>tr:first-child]:outline-primary',
        )}
      >
        {header}
        {expanded ? rows.length > 0 ? rows.map((project) => renderRow(project, depth)) : <EmptyGroupRow columns={COLUMNS}>{emptyText}</EmptyGroupRow> : null}
      </TableBody>
    );
  }

  /**
   * Projects in no folder, at the top level like files beside folders in a file manager:
   * no header of their own. The group is still the drop target that takes a project out of
   * its folder; with nothing in it, it shows a strip only while a filed project is dragged.
   */
  function rootBody() {
    const draggingFiled = dragging !== null && dragging.some((id) => folderOf(folders, id) !== null);
    if (noFolderRows.length === 0 && !draggingFiled) return null;
    return (
      <TableBody
        key={NO_FOLDER_KEY}
        data-drop-target={NO_FOLDER_KEY}
        {...dropHandlers(NO_FOLDER_KEY)}
        className={cn('border-t-8 border-background transition-colors', dropTarget === NO_FOLDER_KEY && '[&>tr]:!bg-primary/10')}
      >
        {noFolderRows.map((project) => renderRow(project, 0))}
        {noFolderRows.length === 0 ? (
          <EmptyGroupRow columns={COLUMNS}>
            <span className="inline-block w-full rounded-md border border-dashed border-primary/50 py-2">Drop here to take it out of its folder</span>
          </EmptyGroupRow>
        ) : null}
      </TableBody>
    );
  }

  function renderFolder(node: FolderNode): ReactNode[] {
    const { folder } = node;
    const rows = byFolder.get(folder.id) ?? [];
    const all = deepRows(node);
    // While filtering, a folder with nothing matching is noise; otherwise an empty folder
    // stays, because it is a place the user made to put things in.
    if (filtering && all.length === 0) return [];
    const expanded = isExpanded(folder);
    const forcedOpen = folder.collapsed && textFiltering;
    const allIds = all.map((project) => project.project_id);
    return [
      groupBody(
        folder.id,
        <FolderHeaderRow
          node={node}
          folders={folders.folders}
          editable={ready}
          count={all.length}
          expanded={expanded}
          forcedOpen={forcedOpen}
          // A collapsed folder counts as not selected: its rows are not on screen.
          selection={expanded ? selectionOf(allIds) : false}
          onToggleSelection={(checked) => {
            // Selecting a collapsed folder opens it, so what is selected is what is seen.
            if (checked && !expanded) apply((state) => setFolderCollapsed(state, folder.id, false));
            select(allIds, checked);
          }}
          onToggleExpanded={() =>
            // From the latest state, not this render's: two quick clicks must toggle twice.
            apply((state) => {
              const latest = state.folders.find((entry) => entry.id === folder.id);
              return latest === undefined ? state : setFolderCollapsed(state, folder.id, !latest.collapsed);
            })
          }
          onRename={() => setFolderDialog({ kind: 'rename', folder })}
          onDelete={() => setDeleting(folder)}
          onNewSubfolder={() => setFolderDialog({ kind: 'create', parentId: folder.id, moveIds: [] })}
          columns={COLUMNS}
        />,
        rows,
        expanded,
        'Empty — drag projects here, or use “Move to folder” on a row.',
        node.depth,
      ),
      ...(expanded ? node.children.flatMap(renderFolder) : []),
    ];
  }

  function renderRow(project: ProjectRecord, depth = 0) {
    const id = project.project_id;
    const isSelected = selected.has(id);
    return (
      <ProjectRow
        key={id}
        project={project}
        depth={depth}
        environment={environment}
        projectNames={projectNames}
        current={current}
        onChanged={onChanged}
        onOpenSettings={() => onOpenSettings(id)}
        selected={isSelected}
        onSelect={(checked) => select([id], checked)}
        dragging={dragging?.includes(id) ?? false}
        draggable={hasFolders && ready}
        onDragStart={(event) => {
          // Dragging a selected row carries the whole selection; an unselected one goes alone.
          const ids = isSelected ? selectedVisible : [id];
          setDragging(ids);
          setDragChip(event, ids.length === 1 ? nameOf(id) : `Moving ${projectCount(ids.length)}`);
        }}
        onDragEnd={() => {
          setDragging(null);
          setDropTarget(null);
        }}
        syncState={syncs.rowState(id)}
        syncBlocked={syncBlocked && syncs.rowState(id).phase !== 'pending'}
        onSync={() => syncs.runRow(id)}
        moveMenu={
          <MoveToMenu
            tree={tree}
            current={folderOf(folders, id)}
            disabled={!ready}
            onMove={(folderId) => move([id], folderId)}
            onNewFolder={() => setFolderDialog({ kind: 'create', parentId: null, moveIds: [id] })}
            trigger={
              <Button
                variant="ghost"
                size="icon-xs"
                disabled={!ready}
                aria-label={`Move ${displayName(project.path, id, projectNames)} to a folder`}
              >
                <FolderInput />
              </Button>
            }
          />
        }
      />
    );
  }

  const bulk = syncs.bulk;

  return (
    <>
      <div className="flex flex-wrap items-center justify-between gap-2">
        {/* Announced the same way the refresh line is — a filter that silently changes
            which rows are on screen is exactly the kind of update a screen reader user
            would otherwise miss entirely. */}
        <p aria-live="polite" className="text-xs text-muted-foreground">
          Showing {filteredProjects.length} of {projectCount(projects.length)}.
          {status !== '' ? ` ${status}` : ''}
        </p>
        <Hint content="Group projects on this screen — nothing in any project changes">
          <Button
            variant="outline"
            size="xs"
            disabled={!ready}
            onClick={() => setFolderDialog({ kind: 'create', parentId: null, moveIds: [] })}
          >
            <FolderPlus />
            New folder
          </Button>
        </Hint>
      </div>

      {unavailable ? (
        <Alert variant="destructive" role="alert">
          <AlertTriangle aria-hidden="true" />
          <AlertTitle>The folders could not be read</AlertTitle>
          <AlertDescription>
            <p>Projects are shown ungrouped, and folders cannot be changed until they are read, so nothing overwrites them.</p>
            <Button variant="outline" size="xs" className="mt-2" onClick={retry}>
              Try again
            </Button>
          </AlertDescription>
        </Alert>
      ) : null}
      {error !== null ? (
        <Alert variant="destructive" role="alert">
          <AlertTriangle aria-hidden="true" />
          <AlertTitle>The folder change was undone</AlertTitle>
          <AlertDescription>
            <p>{error}</p>
            <Button variant="outline" size="xs" className="mt-2" onClick={dismissError}>
              Dismiss
            </Button>
          </AlertDescription>
        </Alert>
      ) : null}
      {bulk.phase === 'done' ? (
        <Alert role="status" variant={bulk.failures.length > 0 ? 'destructive' : 'default'}>
          {bulk.failures.length > 0 ? <AlertTriangle aria-hidden="true" /> : <CheckCircle2 aria-hidden="true" />}
          <AlertTitle>
            Synced {bulk.done - bulk.failures.length} of {projectCount(bulk.total)}.
            {bulk.stopped ? ` Stopped before the other ${bulk.total - bulk.done}.` : ''}
          </AlertTitle>
          <AlertDescription>
            {bulk.failures.length > 0 ? (
              <ul className="list-disc pl-4">
                {bulk.failures.map((failure) => (
                  <li key={failure.id}>
                    <span className="font-medium">{failure.name}</span>: {failure.message}
                  </li>
                ))}
              </ul>
            ) : null}
            <Button variant="outline" size="xs" className="mt-2" onClick={syncs.dismissBulk}>
              Dismiss
            </Button>
          </AlertDescription>
        </Alert>
      ) : null}

      {filteredProjects.length === 0 ? (
        // Distinct from the "nothing is bound yet" empty state: that one means there is
        // nothing to show the user at all, this one means there is something, just not
        // anything these filters let through — the fix is "loosen a filter".
        <Empty>No bound project matches these filters.</Empty>
      ) : (
        <>
          {selectedVisible.length > 0 || bulk.phase === 'running' ? (
            <BulkActionBar
              count={selectedVisible.length}
              tree={tree}
              current={sharedFolder(selectedVisible)}
              anyInFolder={selectedVisible.some((id) => folderOf(folders, id) !== null)}
              environment={environment}
              bulkSync={bulk}
              editable={ready}
              syncBlocked={syncBlocked && bulk.phase !== 'running'}
              onMove={(folderId) => move(selectedVisible, folderId, true)}
              onNewFolder={() => setFolderDialog({ kind: 'create', parentId: null, moveIds: selectedVisible })}
              onSync={() => syncs.runBulk(selectedVisible.map((id) => ({ id, name: nameOf(id) })))}
              onCancelSync={syncs.stopBulk}
              onClear={() => setSelected(new Set())}
            />
          ) : null}
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead scope="col" className="w-14">
                  <Checkbox
                    checked={selectionOf(visibleIds)}
                    onCheckedChange={(checked) => select(visibleIds, checked === true)}
                    aria-label="Select every project shown"
                  />
                </TableHead>
                <TableHead scope="col">Project</TableHead>
                <TableHead scope="col">Version</TableHead>
                <TableHead scope="col">Mode</TableHead>
                <TableHead scope="col">Providers</TableHead>
                <TableHead scope="col">Path</TableHead>
                <TableHead scope="col">Actions</TableHead>
              </TableRow>
            </TableHeader>
            {hasFolders ? (
              <>
                {tree.flatMap(renderFolder)}
                {rootBody()}
              </>
            ) : (
              <TableBody>{filteredProjects.map((project) => renderRow(project))}</TableBody>
            )}
          </Table>
        </>
      )}

      <FolderNameDialog
        open={folderDialog !== null}
        onOpenChange={(open) => {
          if (!open) setFolderDialog(null);
        }}
        // From the last dialog shown, so the text does not flip to "New folder" while a
        // rename dialog animates out.
        title={shownDialog?.kind === 'rename' ? `Rename “${shownDialog.folder.name}”` : 'New folder'}
        description={
          shownDialog?.kind === 'create' && shownDialog.moveIds.length > 0
            ? `The ${projectCount(shownDialog.moveIds.length)} you chose will move into it.`
            : 'Folders only group rows on this screen, on this machine. Nothing in any project changes.'
        }
        initialName={shownDialog?.kind === 'rename' ? shownDialog.folder.name : ''}
        submitLabel={shownDialog?.kind === 'rename' ? 'Rename' : 'Create folder'}
        problemFor={(name) =>
          folderDialog === null
            ? null
            : folderDialog.kind === 'rename'
              ? folderNameProblem(folders.folders, name, folderDialog.folder.parentId, folderDialog.folder.id)
              : folderNameProblem(folders.folders, name, folderDialog.parentId)
        }
        onSubmit={(name) => {
          if (folderDialog === null) return;
          if (folderDialog.kind === 'rename') {
            const id = folderDialog.folder.id;
            apply((state) => renameFolder(state, id, name), { announce: `Renamed the folder to “${name}”.` });
            return;
          }
          const id = newFolderId();
          const { parentId, moveIds } = folderDialog;
          apply((state) => moveProjects(createFolder(state, id, name, parentId), moveIds, id), {
            announce:
              moveIds.length > 0 ? `Created “${name}” and moved ${projectCount(moveIds.length)} into it.` : `Created the folder “${name}”.`,
          });
          if (moveIds.length > 0) setSelected(new Set());
        }}
      />
      <DeleteFolderDialog
        folder={deleting}
        memberCount={
          shownDeleting === null ? 0 : projects.filter((project) => folderOf(folders, project.project_id) === shownDeleting.id).length
        }
        onOpenChange={(open) => {
          if (!open) setDeleting(null);
        }}
        onConfirm={() => {
          if (deleting === null) return;
          const { id, name } = deleting;
          apply((state) => deleteFolder(state, id), { announce: `Deleted the folder “${name}”.` });
        }}
      />
    </>
  );
}
