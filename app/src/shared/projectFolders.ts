/**
 * Folders that group bound projects on the Projects screen (ADR-0021).
 *
 * App-local, like the display name (ADR-0016): the grouping lives in this app's
 * `settings.json` and never reaches the CLI, `project.json` or the store. It is one
 * client's way of arranging rows, not a property of a project.
 *
 * The model is a tree — every folder carries a `parentId` — and today's single level is a
 * limit, not a shape: `MAX_FOLDER_DEPTH` is the one number that says how deep a folder may
 * sit, every function here walks the tree without assuming a depth, and the validator
 * refuses anything deeper. Allowing subfolders later means raising that constant and
 * offering "New subfolder" in the UI, with no change to the stored format.
 *
 * Shared by the main process (which validates every write) and the renderer (which applies
 * the same transforms optimistically), so the two cannot disagree about what is valid.
 */

/** How many levels of folders exist. 1 = folders only, no subfolders. */
export const MAX_FOLDER_DEPTH = 1;
export const FOLDER_NAME_MAX_LENGTH = 60;
export const MAX_FOLDERS = 200;
/** Far above any real number of bound projects; exists so the file cannot grow without limit. */
export const MAX_MEMBERSHIP = 10_000;
export const PROJECT_ID_MAX_LENGTH = 128;

const FOLDER_ID_PATTERN = /^[A-Za-z0-9-]{1,64}$/;
const STATE_KEYS: ReadonlySet<string> = new Set(['folders', 'membership']);
const FOLDER_KEYS: ReadonlySet<string> = new Set(['id', 'name', 'parentId', 'collapsed']);

export interface ProjectFolder {
  readonly id: string;
  readonly name: string;
  /** `null` for a top-level folder. */
  readonly parentId: string | null;
  readonly collapsed: boolean;
}

export interface ProjectFolders {
  readonly folders: readonly ProjectFolder[];
  /** `project_id` → folder id. A project absent from the map is in no folder. */
  readonly membership: Readonly<Record<string, string>>;
}

export type ProjectFoldersAnswer =
  | { readonly ok: true; readonly folders: ProjectFolders }
  | { readonly ok: false; readonly message: string };

export const NO_FOLDERS: ProjectFolders = Object.freeze({ folders: Object.freeze([]), membership: Object.freeze({}) });

export interface FolderNode {
  readonly folder: ProjectFolder;
  /** 1 for a top-level folder. */
  readonly depth: number;
  readonly children: readonly FolderNode[];
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function unknownKey(record: Record<string, unknown>, allowed: ReadonlySet<string>): string | undefined {
  return Object.keys(record).find((key) => !allowed.has(key));
}

function projectIdProblem(projectId: string): string | null {
  if (projectId === '') return 'a membership entry has an empty project id';
  if (projectId.length > PROJECT_ID_MAX_LENGTH) return `a project id is longer than ${PROJECT_ID_MAX_LENGTH} characters`;
  return null;
}

/** A name with ` (n)` appended, the base shortened so the whole stays within the limit. */
function suffixed(name: string, n: number): string {
  const suffix = ` (${n})`;
  return `${name.slice(0, FOLDER_NAME_MAX_LENGTH - suffix.length).trimEnd()}${suffix}`;
}

function sameName(a: string, b: string): boolean {
  return a.trim().toLocaleLowerCase() === b.trim().toLocaleLowerCase();
}

/** 1 for a top-level folder; `Infinity` for a folder whose ancestry is broken or cyclic. */
export function folderDepth(folders: readonly ProjectFolder[], id: string): number {
  const byId = new Map(folders.map((folder) => [folder.id, folder]));
  let depth = 0;
  let cursor = byId.get(id);
  const seen = new Set<string>();
  while (cursor !== undefined) {
    if (seen.has(cursor.id)) return Infinity;
    seen.add(cursor.id);
    depth += 1;
    if (cursor.parentId === null) return depth;
    cursor = byId.get(cursor.parentId);
  }
  return Infinity;
}

/** Whether a folder may hold another folder — false at the depth limit. */
export function canNestIn(folders: readonly ProjectFolder[], parentId: string | null): boolean {
  if (parentId === null) return true;
  return folderDepth(folders, parentId) < MAX_FOLDER_DEPTH;
}

/**
 * Why `name` cannot be used for a folder under `parentId`, or `null` when it can.
 * Names are unique among siblings, compared case-insensitively; `exceptId` is the folder
 * being renamed, which may keep its own name.
 */
export function folderNameProblem(
  folders: readonly ProjectFolder[],
  name: string,
  parentId: string | null,
  exceptId: string | null = null,
): string | null {
  const trimmed = name.trim();
  if (trimmed === '') return 'A folder needs a name.';
  if (trimmed.length > FOLDER_NAME_MAX_LENGTH) return `A folder name is at most ${FOLDER_NAME_MAX_LENGTH} characters.`;
  const clash = folders.find((folder) => folder.id !== exceptId && folder.parentId === parentId && sameName(folder.name, trimmed));
  if (clash !== undefined) return `A folder named “${clash.name}” already exists here.`;
  return null;
}

/**
 * Write-side check for a whole state, run by the main process before anything is written.
 * Returns a sentence, never a partial repair: a state the renderer built wrongly is a bug
 * to report, not something to silently reshape into a different grouping.
 */
export function projectFoldersProblem(value: unknown): string | null {
  if (!isRecord(value)) return 'the folders are not an object';
  const extra = unknownKey(value, STATE_KEYS);
  if (extra !== undefined) return `unknown key ${JSON.stringify(extra)}`;
  const { folders, membership } = value;
  if (!Array.isArray(folders)) return '`folders` is not a list';
  if (folders.length > MAX_FOLDERS) return `at most ${MAX_FOLDERS} folders are allowed`;
  if (!isRecord(membership)) return '`membership` is not an object';
  if (Object.keys(membership).length > MAX_MEMBERSHIP) return `at most ${MAX_MEMBERSHIP} projects can be filed`;

  const ids = new Set<string>();
  for (const folder of folders as unknown[]) {
    if (!isRecord(folder)) return 'a folder is not an object';
    const extraKey = unknownKey(folder, FOLDER_KEYS);
    if (extraKey !== undefined) return `a folder has an unknown key ${JSON.stringify(extraKey)}`;
    const { id, name, parentId, collapsed } = folder;
    if (typeof id !== 'string' || !FOLDER_ID_PATTERN.test(id)) return `folder id ${JSON.stringify(id)} is not valid`;
    if (ids.has(id)) return `folder id ${id} appears twice`;
    ids.add(id);
    if (typeof name !== 'string') return `folder ${id} has no name`;
    // Checked raw, not trimmed: what is validated must be exactly what gets written.
    if (name !== name.trim()) return `folder ${id} has a name with surrounding spaces`;
    if (parentId !== null && typeof parentId !== 'string') return `folder ${id} has an invalid parent`;
    if (typeof collapsed !== 'boolean') return `folder ${id} has an invalid collapsed flag`;
  }
  const typed = folders as ProjectFolder[];
  for (const folder of typed) {
    if (folder.parentId !== null && !ids.has(folder.parentId)) return `folder ${folder.name} has a parent that does not exist`;
    const depth = folderDepth(typed, folder.id);
    if (depth === Infinity) return `folder ${folder.name} is inside itself`;
    if (depth > MAX_FOLDER_DEPTH) return `folder ${folder.name} is nested deeper than ${MAX_FOLDER_DEPTH} level${MAX_FOLDER_DEPTH === 1 ? '' : 's'}`;
    const problem = folderNameProblem(typed, folder.name, folder.parentId, folder.id);
    if (problem !== null) return problem;
  }
  for (const [projectId, folderId] of Object.entries(membership)) {
    const idProblem = projectIdProblem(projectId);
    if (idProblem !== null) return idProblem;
    if (typeof folderId !== 'string' || !ids.has(folderId)) return `project ${projectId} is in a folder that does not exist`;
  }
  return null;
}

/**
 * A copy of a state that passed `projectFoldersProblem`, rebuilt field by field. The main
 * process writes this, never the object the renderer sent, so nothing but the model's own
 * fields can reach `settings.json`.
 */
export function sanitizeProjectFolders(valid: ProjectFolders): ProjectFolders {
  return {
    folders: valid.folders.map(({ id, name, parentId, collapsed }) => ({ id, name, parentId, collapsed })),
    membership: Object.fromEntries(Object.entries(valid.membership).map(([projectId, folderId]) => [projectId, folderId])),
  };
}

/**
 * Read-side normalisation: whatever is in the file, the app still opens. Unlike the write
 * check, this salvages — a folder with a missing parent moves to the top level, a folder
 * deeper than the limit (written by a newer app that allowed subfolders) is lifted to the
 * deepest allowed level, a duplicate name gets a suffix, and membership pointing at a
 * folder that no longer exists is dropped. Nothing about a bound project is lost: a
 * project whose folder is gone is simply in no folder.
 */
export function normalizeProjectFolders(value: unknown): ProjectFolders {
  if (!isRecord(value)) return NO_FOLDERS;
  const rawFolders = Array.isArray(value['folders']) ? (value['folders'] as unknown[]) : [];
  const seen = new Set<string>();
  let folders: ProjectFolder[] = [];
  for (const raw of rawFolders.slice(0, MAX_FOLDERS)) {
    if (!isRecord(raw)) continue;
    const { id, name, parentId, collapsed } = raw;
    if (typeof id !== 'string' || !FOLDER_ID_PATTERN.test(id) || seen.has(id)) continue;
    if (typeof name !== 'string' || name.trim() === '') continue;
    seen.add(id);
    folders.push({
      id,
      name: name.trim().slice(0, FOLDER_NAME_MAX_LENGTH),
      parentId: typeof parentId === 'string' ? parentId : null,
      collapsed: collapsed === true,
    });
  }
  folders = folders.map((folder) => (folder.parentId !== null && !seen.has(folder.parentId) ? { ...folder, parentId: null } : folder));
  // Lift anything too deep (or cyclic) to the deepest ancestor that is within the limit.
  folders = folders.map((folder) => {
    if (folderDepth(folders, folder.id) <= MAX_FOLDER_DEPTH) return folder;
    return { ...folder, parentId: allowedAncestor(folders, folder) };
  });
  // Disambiguate sibling names that collide, keeping the first one unchanged.
  const named: ProjectFolder[] = [];
  for (const folder of folders) {
    let name = folder.name;
    for (let n = 2; folderNameProblem(named, name, folder.parentId) !== null; n += 1) name = suffixed(folder.name, n);
    named.push({ ...folder, name });
  }
  const rawMembership = isRecord(value['membership']) ? value['membership'] : {};
  // `fromEntries`, not assignment: a `__proto__` key must become an own property, not a prototype.
  const membership = Object.fromEntries(
    Object.entries(rawMembership)
      .filter((entry): entry is [string, string] => {
        const [projectId, folderId] = entry;
        return projectIdProblem(projectId) === null && typeof folderId === 'string' && seen.has(folderId);
      })
      .slice(0, MAX_MEMBERSHIP),
  );
  return { folders: named, membership };
}

function allowedAncestor(folders: readonly ProjectFolder[], folder: ProjectFolder): string | null {
  const byId = new Map(folders.map((entry) => [entry.id, entry]));
  const chain: string[] = [];
  const seen = new Set<string>([folder.id]);
  let parentId = folder.parentId;
  while (parentId !== null && !seen.has(parentId)) {
    seen.add(parentId);
    chain.unshift(parentId);
    parentId = byId.get(parentId)?.parentId ?? null;
  }
  // `chain` runs root → direct parent; a folder may sit under at most MAX_FOLDER_DEPTH - 1 ancestors.
  const keep = chain.slice(0, MAX_FOLDER_DEPTH - 1);
  return keep.length === 0 ? null : keep[keep.length - 1]!;
}

/** Folders as a tree, siblings sorted by name. */
export function buildFolderTree(state: ProjectFolders): readonly FolderNode[] {
  const byParent = new Map<string | null, ProjectFolder[]>();
  for (const folder of state.folders) {
    const siblings = byParent.get(folder.parentId) ?? [];
    siblings.push(folder);
    byParent.set(folder.parentId, siblings);
  }
  const build = (parentId: string | null, depth: number, seen: ReadonlySet<string>): FolderNode[] =>
    (byParent.get(parentId) ?? [])
      .filter((folder) => !seen.has(folder.id))
      .sort((a, b) => a.name.localeCompare(b.name, undefined, { sensitivity: 'base', numeric: true }))
      .map((folder) => ({ folder, depth, children: build(folder.id, depth + 1, new Set([...seen, folder.id])) }));
  return build(null, 1, new Set());
}

/** Every folder in display order (depth-first), for menus. */
export function flattenFolderTree(tree: readonly FolderNode[]): readonly FolderNode[] {
  return tree.flatMap((node) => [node, ...flattenFolderTree(node.children)]);
}

export function folderOf(state: ProjectFolders, projectId: string): string | null {
  return Object.hasOwn(state.membership, projectId) ? state.membership[projectId]! : null;
}

export function createFolder(state: ProjectFolders, id: string, name: string, parentId: string | null = null): ProjectFolders {
  return { ...state, folders: [...state.folders, { id, name: name.trim(), parentId, collapsed: false }] };
}

export function renameFolder(state: ProjectFolders, id: string, name: string): ProjectFolders {
  return { ...state, folders: state.folders.map((folder) => (folder.id === id ? { ...folder, name: name.trim() } : folder)) };
}

export function setFolderCollapsed(state: ProjectFolders, id: string, collapsed: boolean): ProjectFolders {
  return { ...state, folders: state.folders.map((folder) => (folder.id === id ? { ...folder, collapsed } : folder)) };
}

/**
 * Remove a folder. Never removes a project: its projects and subfolders move up to the
 * deleted folder's own parent — the top level, today, which means "no folder".
 */
export function deleteFolder(state: ProjectFolders, id: string): ProjectFolders {
  const target = state.folders.find((folder) => folder.id === id);
  if (target === undefined) return state;
  const folders = state.folders
    .filter((folder) => folder.id !== id)
    .map((folder) => (folder.parentId === id ? { ...folder, parentId: target.parentId } : folder));
  const membership = Object.fromEntries(
    Object.entries(state.membership).flatMap(([projectId, folderId]): [string, string][] => {
      if (folderId !== id) return [[projectId, folderId]];
      return target.parentId === null ? [] : [[projectId, target.parentId]];
    }),
  );
  return { folders, membership };
}

/** Put every project in `projectIds` into `folderId`, or into no folder when it is `null`. */
export function moveProjects(state: ProjectFolders, projectIds: Iterable<string>, folderId: string | null): ProjectFolders {
  if (folderId !== null && !state.folders.some((folder) => folder.id === folderId)) return state;
  const entries = new Map(Object.entries(state.membership));
  for (const projectId of projectIds) {
    if (folderId === null) entries.delete(projectId);
    else entries.set(projectId, folderId);
  }
  return { ...state, membership: Object.fromEntries(entries) };
}

/** Drop membership for projects no longer bound. Returns `state` itself when nothing changed. */
export function pruneMembership(state: ProjectFolders, boundProjectIds: ReadonlySet<string>): ProjectFolders {
  const entries = Object.entries(state.membership);
  const kept = entries.filter(([projectId]) => boundProjectIds.has(projectId));
  if (kept.length === entries.length) return state;
  return { ...state, membership: Object.fromEntries(kept) };
}

export function isEmptyFolders(state: ProjectFolders): boolean {
  return state.folders.length === 0 && Object.keys(state.membership).length === 0;
}
