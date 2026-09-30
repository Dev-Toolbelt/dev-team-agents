// @vitest-environment jsdom
/**
 * `Skills` manages files outside any project, so the render risks are the destructive ones:
 * a remove offered for a skill the framework owns, a remove that fires without its
 * confirmation, a confirmation that does not say where the folder goes, an install offered
 * while withheld, and a conflict that leaves the user with no way forward.
 */
import './setup.js';
import '@testing-library/jest-dom/vitest';

import { cleanup, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { Skills } from '../../src/renderer/screens/Skills.js';
import type { SkillInstallAnswer, SkillList, SkillRecord } from '../../src/shared/api.js';
import { environment, fail, fakeBridge, installBridge, ok } from './support.js';

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

function skill(overrides: Partial<SkillRecord> = {}): SkillRecord {
  return {
    name: 'alpha',
    description: 'Does alpha things',
    root: 'claude',
    root_path: '/home/u/.claude/skills',
    path: '/home/u/.claude/skills/alpha',
    providers: ['claude', 'opencode'],
    is_symlink: false,
    link_target: null,
    managed: false,
    status: 'ok',
    error: null,
    ...overrides,
  };
}

function list(skills: SkillRecord[], overrides: Partial<SkillList> = {}): SkillList {
  return {
    provider: 'all',
    roots: [
      { id: 'claude', path: '/home/u/.claude/skills', exists: true, providers: ['claude', 'opencode'], install_target_for: ['claude'] },
      { id: 'opencode', path: '/home/u/.config/opencode/skills', exists: false, providers: ['opencode'], install_target_for: ['opencode'] },
    ],
    skills,
    ...overrides,
  };
}

function mount(bridge: Parameters<typeof fakeBridge>[0], env = environment()) {
  installBridge(fakeBridge(bridge));
  return render(<Skills environment={env} />);
}

describe('Skills — the listing', () => {
  it('shows roots with an absent badge, and a row with its providers and flags', async () => {
    mount({
      listSkills: vi.fn(() =>
        Promise.resolve(
          ok(
            list([
              skill(),
              skill({ name: 'linked', is_symlink: true, link_target: '/src/linked' }),
              skill({ name: 'broken', status: 'malformed', error: 'no frontmatter' }),
              skill({ name: 'framework', managed: true }),
            ]),
          ),
        ),
      ),
    });

    await screen.findByRole('button', { name: 'alpha' });
    const rootLine = screen.getByText('/home/u/.config/opencode/skills').closest('li')!;
    expect(within(rootLine).getByText('absent')).toBeInTheDocument();
    expect(within(screen.getByText('/home/u/.claude/skills').closest('li')!).queryByText('absent')).not.toBeInTheDocument();

    const alphaRow = screen.getByRole('button', { name: 'alpha' }).closest('tr')!;
    expect(within(alphaRow).getByText('opencode')).toBeInTheDocument();
    expect(within(screen.getByRole('button', { name: 'linked' }).closest('tr')!).getByText('link')).toBeInTheDocument();
    expect(within(screen.getByRole('button', { name: 'broken' }).closest('tr')!).getByText('malformed')).toBeInTheDocument();
    expect(within(screen.getByRole('button', { name: 'framework' }).closest('tr')!).getByText('managed')).toBeInTheDocument();
  });

  it('re-runs the listing with the chosen provider', async () => {
    const user = userEvent.setup();
    const listSkills = vi.fn(() => Promise.resolve(ok(list([skill()]))));
    mount({ listSkills });
    await screen.findByRole('button', { name: 'alpha' });
    expect(listSkills).toHaveBeenLastCalledWith('all');

    await user.selectOptions(screen.getByRole('combobox', { name: /filter skills by provider/i }), 'codex');
    await vi.waitFor(() => expect(listSkills).toHaveBeenLastCalledWith('codex'));
  });

  it('states the CLI problem instead of an empty table', async () => {
    mount({ listSkills: vi.fn(() => Promise.resolve(fail('the CLI broke', { kind: 'environment' }))) });
    expect(await screen.findByText('the CLI broke')).toBeInTheDocument();
  });
});

describe('Skills — details', () => {
  it('opens skills show for the row and renders the body as text, not markup', async () => {
    const user = userEvent.setup();
    const showSkill = vi.fn(() =>
      Promise.resolve(ok({ ...skill(), body: '# Title <img src=x onerror=alert(1)>', files: ['SKILL.md', 'refs/a.md'], files_truncated: false })),
    );
    mount({ listSkills: vi.fn(() => Promise.resolve(ok(list([skill()])))), showSkill });

    await user.click(await screen.findByRole('button', { name: 'alpha' }));

    expect(await screen.findByText('refs/a.md')).toBeInTheDocument();
    expect(showSkill).toHaveBeenCalledWith('alpha', 'claude');
    const body = screen.getByText(/# Title/);
    expect(body.tagName).toBe('PRE');
    expect(document.querySelector('img')).toBeNull();
  });
});

describe('Skills — remove', () => {
  it('offers no remove for a managed skill', async () => {
    mount({ listSkills: vi.fn(() => Promise.resolve(ok(list([skill({ name: 'framework', managed: true })])))) });
    await screen.findByRole('button', { name: 'framework' });
    expect(screen.queryByRole('button', { name: /remove framework/i })).not.toBeInTheDocument();
  });

  it('does nothing until confirmed, says a folder is quarantined, and then shows where it went', async () => {
    const user = userEvent.setup();
    const removeSkill = vi.fn(() =>
      Promise.resolve(
        ok({ name: 'alpha', root: 'claude', path: '/p', providers: ['claude'], action: 'quarantined' as const, quarantined_to: '/store/quarantine/alpha-1', link_target: null }),
      ),
    );
    const listSkills = vi.fn(() => Promise.resolve(ok(list([skill()]))));
    mount({ listSkills, removeSkill });

    await user.click(await screen.findByRole('button', { name: /remove alpha from claude/i }));
    const dialog = await screen.findByRole('dialog');
    expect(within(dialog).getByText(/moved to the store's quarantine, not deleted/i)).toBeInTheDocument();
    expect(removeSkill).not.toHaveBeenCalled();

    await user.click(within(dialog).getByRole('button', { name: 'Remove' }));
    expect(removeSkill).toHaveBeenCalledWith({ name: 'alpha', root: 'claude' });
    expect(await within(dialog).findByText('/store/quarantine/alpha-1')).toBeInTheDocument();
    await vi.waitFor(() => expect(listSkills).toHaveBeenCalledTimes(2));
  });

  it('says a symlink is only unlinked', async () => {
    const user = userEvent.setup();
    mount({
      listSkills: vi.fn(() => Promise.resolve(ok(list([skill({ is_symlink: true, link_target: '/src/alpha' })])))),
    });
    await user.click(await screen.findByRole('button', { name: /remove alpha from claude/i }));
    expect(await screen.findByText(/only the link is removed/i)).toBeInTheDocument();
  });

  it('disables remove, with the reason, when the write is withheld', async () => {
    mount(
      { listSkills: vi.fn(() => Promise.resolve(ok(list([skill()])))) },
      environment({ withheld: [{ command: 'skills remove', reason: 'no declaration' }] }),
    );
    const button = await screen.findByRole('button', { name: /withheld: no declaration/i });
    expect(button).toBeDisabled();
  });
});

describe('Skills — install', () => {
  it('disables Install skill when `skills install` is withheld', async () => {
    mount(
      { listSkills: vi.fn(() => Promise.resolve(ok(list([])))) },
      environment({ withheld: [{ command: 'skills install', reason: 'no declaration' }] }),
    );
    expect(await screen.findByRole('button', { name: /install skill.*withheld/i })).toBeDisabled();
  });

  it('sends a source kind and the chosen providers and toggles — never a path', async () => {
    const user = userEvent.setup();
    const installSkill = vi.fn(
      (): Promise<SkillInstallAnswer> =>
        Promise.resolve({
          picked: true,
          source: '/picked/beta',
          result: ok({
            name: 'beta',
            description: null,
            source: '/picked/beta',
            linked: true,
            installed: [{ root: 'claude', path: '/home/u/.claude/skills/beta', providers: ['claude'], replaced: false, quarantined_to: null }],
            also_present: [],
          }),
        }),
    );
    const listSkills = vi.fn(() => Promise.resolve(ok(list([]))));
    mount({ listSkills, installSkill });

    await user.click(await screen.findByRole('button', { name: 'Install skill' }));
    const dialog = await screen.findByRole('dialog');
    await user.click(within(dialog).getByRole('checkbox', { name: 'Codex' }));
    await user.click(within(dialog).getByRole('checkbox', { name: /link instead of copy/i }));
    expect(within(dialog).getByRole('button', { name: /archive/i })).toBeDisabled();
    await user.click(within(dialog).getByRole('button', { name: 'Folder…' }));

    expect(installSkill).toHaveBeenCalledWith({ source: 'folder', providers: ['claude', 'codex'], replace: false, link: true });
    expect(await within(dialog).findByText('/home/u/.claude/skills/beta')).toBeInTheDocument();
    await vi.waitFor(() => expect(listSkills).toHaveBeenCalledTimes(2));
  });

  it('says nothing when the picker is dismissed', async () => {
    const user = userEvent.setup();
    mount({ listSkills: vi.fn(() => Promise.resolve(ok(list([])))) });
    await user.click(await screen.findByRole('button', { name: 'Install skill' }));
    const dialog = await screen.findByRole('dialog');
    await user.click(within(dialog).getByRole('button', { name: 'Folder…' }));
    expect(within(dialog).queryByRole('alert')).not.toBeInTheDocument();
    expect(within(dialog).queryByRole('status')).not.toBeInTheDocument();
  });

  it('on a conflict, shows the CLI error and retries the previous source with replace', async () => {
    const user = userEvent.setup();
    const installSkill = vi
      .fn<(request: Parameters<ReturnType<typeof fakeBridge>['installSkill']>[0]) => Promise<SkillInstallAnswer>>()
      .mockResolvedValueOnce({
        picked: true,
        source: '/picked/clash',
        result: fail('skill "clash" already exists', { kind: 'conflict', exitCode: 4, reason: 'exists' }),
      })
      .mockResolvedValueOnce({
        picked: true,
        source: '/picked/clash',
        result: ok({
          name: 'clash',
          description: null,
          source: '/picked/clash',
          linked: false,
          installed: [{ root: 'claude', path: '/home/u/.claude/skills/clash', providers: ['claude'], replaced: true, quarantined_to: '/store/q/clash' }],
          also_present: [],
        }),
      });
    mount({ listSkills: vi.fn(() => Promise.resolve(ok(list([])))), installSkill });

    await user.click(await screen.findByRole('button', { name: 'Install skill' }));
    const dialog = await screen.findByRole('dialog');
    await user.click(within(dialog).getByRole('button', { name: 'Folder…' }));
    expect(await within(dialog).findByText('skill "clash" already exists')).toBeInTheDocument();

    await user.click(within(dialog).getByRole('button', { name: /replace the existing skill and retry/i }));
    expect(installSkill).toHaveBeenLastCalledWith({ source: 'previous', providers: ['claude'], replace: true, link: false });
    expect(await within(dialog).findByText('/store/q/clash')).toBeInTheDocument();
  });

  it('offers no replace-and-retry when the conflict is a managed skill', async () => {
    const user = userEvent.setup();
    const installSkill = vi.fn(
      (): Promise<SkillInstallAnswer> =>
        Promise.resolve({
          picked: true,
          source: '/picked/unit',
          result: fail('unit is managed by dev-team-agents', { kind: 'conflict', exitCode: 4, reason: 'managed' }),
        }),
    );
    mount({ listSkills: vi.fn(() => Promise.resolve(ok(list([])))), installSkill });
    await user.click(await screen.findByRole('button', { name: 'Install skill' }));
    const dialog = await screen.findByRole('dialog');
    await user.click(within(dialog).getByRole('button', { name: 'Folder…' }));
    expect(await within(dialog).findByText('unit is managed by dev-team-agents')).toBeInTheDocument();
    expect(within(dialog).queryByRole('button', { name: /replace the existing skill and retry/i })).not.toBeInTheDocument();
  });

  it('warns when the same name already exists in another root a provider reads', async () => {
    const user = userEvent.setup();
    const installSkill = vi.fn(
      (): Promise<SkillInstallAnswer> =>
        Promise.resolve({
          picked: true,
          source: '/picked/dup',
          result: ok({
            name: 'dup',
            description: null,
            source: '/picked/dup',
            linked: false,
            installed: [{ root: 'claude', path: '/home/u/.claude/skills/dup', providers: ['claude', 'opencode'], replaced: false, quarantined_to: null }],
            also_present: [{ root: 'opencode', path: '/home/u/.config/opencode/skills/dup' }],
          }),
        }),
    );
    mount({ listSkills: vi.fn(() => Promise.resolve(ok(list([])))), installSkill });
    await user.click(await screen.findByRole('button', { name: 'Install skill' }));
    const dialog = await screen.findByRole('dialog');
    await user.click(within(dialog).getByRole('button', { name: 'Folder…' }));
    expect(await within(dialog).findByText(/will see two copies/)).toBeInTheDocument();
  });
});
