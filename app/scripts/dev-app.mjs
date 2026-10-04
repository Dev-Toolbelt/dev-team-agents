/**
 * Launch the app against the Vite dev server, with no extra dependency.
 *
 * Run `npm run dev:renderer` in one terminal and this in another. Deliberately not a
 * single script with a process manager: that would mean adding `concurrently` to a
 * repository that is otherwise python and bash, for a convenience two terminals provide.
 */
import { spawn, spawnSync } from 'node:child_process';

const origin = process.env.DEVTEAM_APP_DEV_SERVER ?? 'http://localhost:5173';

const build = spawn('npm', ['run', 'build:node'], { stdio: 'inherit', shell: false });
build.on('close', (code) => {
  if (code !== 0) process.exit(code ?? 1);
  // Never fails the launch: see the script's header.
  spawnSync(process.execPath, ['scripts/brand-dev-electron.mjs'], { stdio: 'inherit' });
  const electron = spawn(process.platform === 'win32' ? 'npx.cmd' : 'npx', ['electron', '.'], {
    stdio: 'inherit',
    shell: false,
    env: { ...process.env, DEVTEAM_APP_DEV_SERVER: origin },
  });
  electron.on('close', (electronCode) => process.exit(electronCode ?? 0));
});
