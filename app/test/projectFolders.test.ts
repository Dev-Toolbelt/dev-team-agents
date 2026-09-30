/**
 * The folder model (ADR-0021). Two properties carry the feature: no operation ever loses a
 * bound project (deleting a folder files its projects one level up, never away), and the
 * depth limit is enforced by the validator the main process runs — so raising it later is
 * a one-constant change, and until then nothing deeper can be written.
 */
import { describe, expect, it } from 'vitest';

import {
  FOLDER_NAME_MAX_LENGTH,
  MAX_FOLDER_DEPTH,
  MAX_FOLDERS,
  MAX_MEMBERSHIP,
  PROJECT_ID_MAX_LENGTH,
  NO_FOLDERS,
  buildFolderTree,
  canNestIn,
  createFolder,
  deleteFolder,
  folderNameProblem,
  moveProjects,
  normalizeProjectFolders,
  projectFoldersProblem,
  pruneMembership,
  renameFolder,
  sanitizeProjectFolders,
  setFolderCollapsed,
  type ProjectFolder,
  type ProjectFolders,
} from '../src/shared/projectFolders.js';

function folder(id: string, name: string, parentId: string | null = null): ProjectFolder {
  return { id, name, parentId, collapsed: false };
}

const TWO: ProjectFolders = {
  folders: [folder('sites', 'Sites'), folder('apps', 'Apps')],
  membership: { p1: 'sites', p2: 'sites', p3: 'apps' },
};

describe('folderNameProblem', () => {
  it('refuses blank, too long and a sibling clash that differs only in case', () => {
    expect(folderNameProblem(TWO.folders, '   ', null)).toMatch(/needs a name/);
    expect(folderNameProblem(TWO.folders, 'x'.repeat(61), null)).toMatch(/at most 60/);
    expect(folderNameProblem(TWO.folders, ' sites ', null)).toMatch(/already exists/);
  });

  it('lets a folder keep its own name on rename, and allows the name under another parent', () => {
    expect(folderNameProblem(TWO.folders, 'Sites', null, 'sites')).toBeNull();
    expect(folderNameProblem(TWO.folders, 'Sites', 'apps')).toBeNull();
  });
});

describe('projectFoldersProblem — the write gate', () => {
  it('accepts a valid state and the empty state', () => {
    expect(projectFoldersProblem(TWO)).toBeNull();
    expect(projectFoldersProblem(NO_FOLDERS)).toBeNull();
  });

  it(`refuses nesting deeper than MAX_FOLDER_DEPTH (${MAX_FOLDER_DEPTH})`, () => {
    const nested = { folders: [folder('a', 'A'), folder('b', 'B', 'a')], membership: {} };
    expect(projectFoldersProblem(nested)).toMatch(/nested deeper/);
  });

  it('refuses cycles, unknown parents, duplicate ids and duplicate sibling names', () => {
    expect(projectFoldersProblem({ folders: [folder('a', 'A', 'a')], membership: {} })).toMatch(/inside itself/);
    expect(projectFoldersProblem({ folders: [folder('a', 'A', 'ghost')], membership: {} })).toMatch(/does not exist/);
    expect(projectFoldersProblem({ folders: [folder('a', 'A'), folder('a', 'B')], membership: {} })).toMatch(/twice/);
    expect(projectFoldersProblem({ folders: [folder('a', 'A'), folder('b', 'a')], membership: {} })).toMatch(/already exists/);
  });

  it('refuses membership pointing at a missing folder, bad ids and malformed shapes', () => {
    expect(projectFoldersProblem({ folders: [], membership: { p1: 'gone' } })).toMatch(/does not exist/);
    expect(projectFoldersProblem({ folders: [folder('bad id!', 'A')], membership: {} })).toMatch(/not valid/);
    expect(projectFoldersProblem({ folders: {}, membership: {} })).toMatch(/not a list/);
    expect(projectFoldersProblem([])).toMatch(/not an object/);
    expect(projectFoldersProblem({ folders: [{ id: 'a', name: 'A', parentId: null }], membership: {} })).toMatch(/collapsed/);
  });

  it(`refuses more than ${MAX_FOLDERS} folders`, () => {
    const many = Array.from({ length: MAX_FOLDERS + 1 }, (_unused, index) => folder(`f${index}`, `F${index}`));
    expect(projectFoldersProblem({ folders: many, membership: {} })).toMatch(/at most/);
  });
});

describe('normalizeProjectFolders — the read side salvages, never throws', () => {
  it('returns the empty state for anything that is not an object', () => {
    expect(normalizeProjectFolders(undefined)).toEqual(NO_FOLDERS);
    expect(normalizeProjectFolders('x')).toEqual(NO_FOLDERS);
  });

  it('lifts a too-deep folder (written by a newer app) to the top level and keeps its projects', () => {
    const read = normalizeProjectFolders({
      folders: [folder('a', 'A'), folder('b', 'B', 'a')],
      membership: { p1: 'b' },
    });
    expect(read.folders.find((entry) => entry.id === 'b')?.parentId).toBeNull();
    expect(read.membership).toEqual({ p1: 'b' });
    expect(projectFoldersProblem(read)).toBeNull();
  });

  it('drops invalid entries, renames clashing siblings and drops membership to missing folders', () => {
    const read = normalizeProjectFolders({
      folders: [folder('a', 'Sites'), folder('b', 'sites'), { id: 'c' }, 'junk', folder('d', 'Orphan', 'ghost')],
      membership: { p1: 'a', p2: 'gone', p3: 42 },
    });
    expect(read.folders.map((entry) => entry.name)).toEqual(['Sites', 'sites (2)', 'Orphan']);
    expect(read.folders.find((entry) => entry.id === 'd')?.parentId).toBeNull();
    expect(read.membership).toEqual({ p1: 'a' });
    expect(projectFoldersProblem(read)).toBeNull();
  });
});

describe('operations', () => {
  it('deleting a folder moves its projects to no folder and never drops another folder\'s', () => {
    const next = deleteFolder(TWO, 'sites');
    expect(next.folders.map((entry) => entry.id)).toEqual(['apps']);
    expect(next.membership).toEqual({ p3: 'apps' });
  });

  it('deleting a folder files its projects and subfolders under its parent, whatever the depth', () => {
    // Built by hand: the model walks any depth even though the validator caps it today.
    const deep: ProjectFolders = {
      folders: [folder('a', 'A'), folder('b', 'B', 'a'), folder('c', 'C', 'b')],
      membership: { p1: 'b', p2: 'c' },
    };
    const next = deleteFolder(deep, 'b');
    expect(next.folders.find((entry) => entry.id === 'c')?.parentId).toBe('a');
    expect(next.membership).toEqual({ p1: 'a', p2: 'c' });
  });

  it('moves many projects at once, and null takes them out of any folder', () => {
    const moved = moveProjects(TWO, ['p1', 'p3', 'p9'], 'apps');
    expect(moved.membership).toEqual({ p1: 'apps', p2: 'sites', p3: 'apps', p9: 'apps' });
    expect(moveProjects(moved, ['p1', 'p2'], null).membership).toEqual({ p3: 'apps', p9: 'apps' });
  });

  it('create, rename and collapse change only what they name', () => {
    const created = createFolder(TWO, 'games', '  Games ');
    expect(created.folders.at(-1)).toEqual({ id: 'games', name: 'Games', parentId: null, collapsed: false });
    expect(renameFolder(created, 'games', 'Play').folders.at(-1)?.name).toBe('Play');
    expect(setFolderCollapsed(created, 'apps', true).folders.find((entry) => entry.id === 'apps')?.collapsed).toBe(true);
    expect(created.membership).toBe(TWO.membership);
  });

  it('prunes membership of unbound projects, and returns the same object when nothing changed', () => {
    expect(pruneMembership(TWO, new Set(['p1', 'p2', 'p3']))).toBe(TWO);
    expect(pruneMembership(TWO, new Set(['p1'])).membership).toEqual({ p1: 'sites' });
  });

  it('builds a tree with siblings sorted by name, and caps nesting through canNestIn', () => {
    const tree = buildFolderTree({ folders: [folder('z', 'zeta'), folder('a', 'Alpha'), folder('n', 'app 10'), folder('m', 'app 9')], membership: {} });
    expect(tree.map((node) => node.folder.name)).toEqual(['Alpha', 'app 9', 'app 10', 'zeta']);
    expect(tree.every((node) => node.depth === 1)).toBe(true);
    expect(canNestIn(TWO.folders, null)).toBe(true);
    expect(canNestIn(TWO.folders, 'sites')).toBe(MAX_FOLDER_DEPTH > 1);
  });
});

describe('the IPC boundary stores only what the model defines', () => {
  it('refuses unknown keys, padded names and oversized membership or project ids', () => {
    expect(projectFoldersProblem({ ...TWO, extra: 1 })).toMatch(/unknown key "extra"/);
    expect(projectFoldersProblem({ folders: [{ ...folder('a', 'A'), note: 'x' }], membership: {} })).toMatch(/unknown key "note"/);
    // Checked raw: a megabyte of spaces around a short name must not pass as "short".
    expect(projectFoldersProblem({ folders: [folder('a', `${' '.repeat(1_000_000)}A`)], membership: {} })).toMatch(/surrounding spaces/);
    const many = Object.fromEntries(Array.from({ length: MAX_MEMBERSHIP + 1 }, (_unused, index) => [`p${index}`, 'sites']));
    expect(projectFoldersProblem({ folders: TWO.folders, membership: many })).toMatch(/at most/);
    expect(projectFoldersProblem({ folders: TWO.folders, membership: { ['x'.repeat(PROJECT_ID_MAX_LENGTH + 1)]: 'sites' } })).toMatch(/longer than/);
  });

  it('sanitize rebuilds the value from the model\'s own fields only', () => {
    const dirty = { folders: [{ ...folder('a', 'A'), note: 'x' }], membership: { p1: 'a' }, extra: 1 } as unknown as ProjectFolders;
    expect(JSON.parse(JSON.stringify(sanitizeProjectFolders(dirty)))).toEqual({ folders: [folder('a', 'A')], membership: { p1: 'a' } });
  });
});

describe('whatever the reader produces, the writer accepts', () => {
  const long = 'n'.repeat(FOLDER_NAME_MAX_LENGTH);
  const inputs: unknown[] = [
    undefined,
    null,
    [],
    { folders: [folder('a', long), folder('b', long), folder('c', long.toUpperCase())], membership: {} },
    { folders: [folder('a', `  ${long}x  `)], membership: {} },
    { folders: [folder('a', 'A', 'b'), folder('b', 'B', 'a')], membership: { p1: 'a' } },
    { folders: [folder('a', 'A'), folder('b', 'B', 'a'), folder('c', 'B', 'b')], membership: { p1: 'c' } },
    { folders: [{ ...folder('a', 'A'), note: 1 }], membership: { ['__proto__']: 'a', ['x'.repeat(500)]: 'a', p2: 'a' }, extra: true },
  ];
  it.each(inputs.map((input, index) => [index, input]))('input %i normalizes to a state projectFoldersProblem accepts', (_index, input) => {
    expect(projectFoldersProblem(normalizeProjectFolders(input))).toBeNull();
  });

  it('keeps a __proto__ project id as data, never as a prototype', () => {
    const read = normalizeProjectFolders({ folders: [folder('a', 'A')], membership: JSON.parse('{"__proto__":"a"}') });
    expect(Object.getPrototypeOf(read.membership)).toBe(Object.prototype);
    expect(Object.keys(read.membership)).toEqual(['__proto__']);
  });

  it('suffixes a duplicate at the length limit without exceeding it', () => {
    const read = normalizeProjectFolders({ folders: [folder('a', long), folder('b', long)], membership: {} });
    expect(read.folders[1]!.name).toHaveLength(FOLDER_NAME_MAX_LENGTH);
    expect(read.folders[1]!.name.endsWith(' (2)')).toBe(true);
  });
});

describe('moving into a folder that no longer exists', () => {
  it('changes nothing', () => {
    expect(moveProjects(TWO, ['p1'], 'deleted')).toBe(TWO);
  });
});
