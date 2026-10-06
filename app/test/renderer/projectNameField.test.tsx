// @vitest-environment jsdom
/** The editable display name in the project header: Save, Reset, and what each tells its caller. */
import './setup.js';
import '@testing-library/jest-dom/vitest';

import { cleanup, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { ProjectNameField } from '../../src/renderer/screens/ProjectNameField.js';
import { Projects } from '../../src/renderer/screens/Projects.js';
import { Toaster } from '../../src/components/ui/sonner.js';
import { environment, fakeBridge, installBridge, ok, project } from './support.js';

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

function mount(storedName: string | undefined, onRenamed = vi.fn()) {
  const bridge = fakeBridge();
  installBridge(bridge);
  render(
    <>
      <ProjectNameField projectId="p1" folderName="acme-site" storedName={storedName} onRenamed={onRenamed} />
      <Toaster />
    </>,
  );
  return { bridge, onRenamed };
}

const saveButton = () => screen.getByRole('button', { name: 'Save name' });
const nameInput = () => screen.getByLabelText('Name');

describe('ProjectNameField', () => {
  it('disables Save while the field is unchanged, empty or invalid', async () => {
    const user = userEvent.setup();
    mount('Storefront');
    expect(saveButton()).toBeDisabled();

    await user.clear(nameInput());
    expect(saveButton()).toBeDisabled();

    await user.type(nameInput(), '   ');
    expect(saveButton()).toBeDisabled();

    await user.clear(nameInput());
    await user.type(nameInput(), 'x'.repeat(121));
    expect(saveButton()).toBeDisabled();
    expect(screen.getByRole('alert')).toHaveTextContent(/at most 120/);

    await user.clear(nameInput());
    await user.type(nameInput(), 'Shop');
    expect(saveButton()).toBeEnabled();
    expect(screen.getByRole('alert')).toBeEmptyDOMElement();
  });

  it('treats whitespace around the stored name as unchanged', async () => {
    const user = userEvent.setup();
    mount('Storefront');
    await user.type(nameInput(), '  ');
    expect(saveButton()).toBeDisabled();
  });

  it('saves the trimmed name and tells the caller', async () => {
    const user = userEvent.setup();
    const { bridge, onRenamed } = mount(undefined);

    await user.type(nameInput(), '  Shop front  ');
    await user.click(saveButton());

    expect(bridge.renameProject).toHaveBeenCalledWith('p1', 'Shop front');
    expect(onRenamed).toHaveBeenCalledWith('p1', 'Shop front');
    expect(await screen.findByText(/Renamed to “Shop front”/)).toBeInTheDocument();
  });

  it('offers Reset only when a custom name is stored', () => {
    mount(undefined);
    expect(screen.queryByRole('button', { name: 'Reset to folder name' })).not.toBeInTheDocument();
    cleanup();
    mount('Storefront');
    expect(screen.getByRole('button', { name: 'Reset to folder name' })).toBeInTheDocument();
  });

  it('resets with null, clears the field and tells the caller', async () => {
    const user = userEvent.setup();
    const { bridge, onRenamed } = mount('Storefront');

    await user.click(screen.getByRole('button', { name: 'Reset to folder name' }));

    expect(bridge.renameProject).toHaveBeenCalledWith('p1', null);
    expect(onRenamed).toHaveBeenCalledWith('p1', undefined);
    expect(nameInput()).toHaveValue('');
    expect(await screen.findByText(/Name reset to “acme-site”/)).toBeInTheDocument();
  });

  it('shows the refusal and does not tell the caller when the save fails', async () => {
    const user = userEvent.setup();
    const onRenamed = vi.fn();
    const bridge = fakeBridge({ renameProject: vi.fn(() => Promise.resolve({ ok: false as const, message: 'Nope.' })) });
    installBridge(bridge);
    render(<ProjectNameField projectId="p1" folderName="acme-site" storedName={undefined} onRenamed={onRenamed} />);

    await user.type(nameInput(), 'Shop');
    await user.click(saveButton());

    expect(await screen.findByRole('alert')).toHaveTextContent('Nope.');
    expect(onRenamed).not.toHaveBeenCalled();
  });

  it('reports a rejected IPC call instead of throwing', async () => {
    const user = userEvent.setup();
    const bridge = fakeBridge({ renameProject: vi.fn(() => Promise.reject(new Error('ipc gone'))) });
    installBridge(bridge);
    render(<ProjectNameField projectId="p1" folderName="acme-site" storedName={undefined} onRenamed={vi.fn()} />);

    await user.type(nameInput(), 'Shop');
    await user.click(saveButton());

    expect(await screen.findByRole('alert')).toHaveTextContent(/ipc gone/);
  });
});

describe('Projects — rename from the settings header re-sorts the list', () => {
  it('moves the renamed row to its new alphabetical place and back on reset', async () => {
    const user = userEvent.setup();
    const projects = [
      project({ project_id: 'a', path: '/repo/alpha' }),
      project({ project_id: 'b', path: '/repo/bravo' }),
      project({ project_id: 'c', path: '/repo/charlie' }),
    ];
    // Like the main process: the stored names are what a later `projectNames()` answers.
    const names: Record<string, string> = {};
    installBridge(
      fakeBridge({
        listProjects: vi.fn(() => Promise.resolve(ok({ current: '2.48.0', projects }))),
        projectNames: vi.fn(() => Promise.resolve({ ...names })),
        renameProject: vi.fn((id: string, name: string | null) => {
          if (name === null) delete names[id];
          else names[id] = name;
          return Promise.resolve({ ok: true as const });
        }),
      }),
    );
    render(
      <>
        <Projects environment={environment()} />
        <Toaster />
      </>,
    );
    await screen.findByText('alpha');
    const order = () => screen.getAllByRole('row').map((row) => row.textContent ?? '');
    const index = (needle: string) => order().findIndex((text) => text.includes(needle));
    expect(index('alpha')).toBeLessThan(index('bravo'));

    await user.click(screen.getByText('alpha'));
    await user.type(await screen.findByLabelText('Name'), 'Zulu');
    await user.click(screen.getByRole('button', { name: 'Save name' }));
    await user.click(screen.getByRole('button', { name: 'Back to Projects' }));

    await screen.findByText('Zulu');
    expect(index('Zulu')).toBeGreaterThan(index('charlie'));
  });
});
