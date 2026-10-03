/**
 * Every word the first-run screens show, in one place (ADR-0030 section 3).
 *
 * The first run never mentions how the framework keeps its records: no talk of binding a
 * folder, of a layout, of a store, or of preference layers. Those are the framework's own
 * vocabulary, and a new user needs none of it to get a first result. `test/onboarding.test.ts`
 * walks this object and fails when one of those words appears, so a later edit cannot
 * reintroduce them without a test saying so. Text that comes from the CLI (a finding's
 * message, a command's description) is shown as the CLI wrote it and is not covered here.
 *
 * Keep every user-visible string of `onboarding/` in this file. English only, like the rest of
 * the app outside the account screens.
 */

export const COPY = {
  title: 'Get started',
  lead: 'A few quick steps and your first result is on the screen. There is nothing to read first.',
  progressLabel: 'Progress',
  stepWord: (index: number, total: number) => `Step ${index} of ${total}`,
  steps: {
    cli: 'Install',
    signin: 'Sign in',
    machine: 'This computer',
    folder: 'Folder',
    confirm: 'Confirm',
    start: 'First task',
  },

  cli: {
    heading: 'Install the devteam tool',
    body: 'This app works through a small command line tool. Installing it takes about a minute.',
    install: 'Install the CLI',
    installing: 'Installing the CLI…',
    lookAgain: 'Look again',
    foundAfter: 'The app has not found it yet: choose Look again, or restart the app.',
    copy: 'Copy command',
    copied: 'Copied',
    copyFailed: 'Select the command above and copy it by hand.',
  },

  machine: {
    heading: 'Checking this computer',
    checking: 'Looking at what is installed…',
    allGood: 'Everything needed is here.',
    problems: 'A few things need attention before you continue.',
    fix: 'Fix',
    fixing: 'Fixing…',
    fixLabel: (message: string) => `Fix: ${message}`,
    fixed: 'Fixed. Checking again…',
    installCommand: 'To install it, run this in a terminal:',
    copy: 'Copy command',
    recheck: 'Check again',
    continueAnyway: 'Continue anyway',
    continue: 'Continue',
    failed: 'The check could not be completed.',
    notAutomatic: 'This one is not fixed automatically.',
  },

  folder: {
    heading: 'Choose your project folder',
    body: 'Pick the folder you want to work in. The app looks at what is inside and suggests the rest.',
    choose: 'Choose a folder',
    looking: 'Looking at the folder…',
    changeFolder: 'Choose a different folder',
  },

  confirm: {
    heading: 'Does this look right?',
    body: 'This is what the app found. Change anything that is wrong.',
    folder: 'Folder',
    provider: 'AI coding tool',
    providerInstalled: (name: string) => `${name} (installed)`,
    providerMissing: (name: string) => `${name} (not installed)`,
    noProvider: 'No AI coding tool was found on this computer. Pick the one you plan to install.',
    stack: 'Main technology',
    stackUnknown: 'Not recognised',
    projectType: 'This project is',
    lowConfidence: 'This is a best guess, so check it.',
    reasonsLabel: 'Why',
    looksRight: 'Looks right',
    back: 'Back',
  },

  types: {
    new: 'A new project',
    unfinished: 'A project I am still building',
    maintenance: 'An existing project I maintain',
  },

  start: {
    heading: 'Start your first task',
    body: 'The first task only reads your project and writes a report. It cannot change your files.',
    noTask: 'There is no first task to suggest for this tool yet. You can still start working in it.',
    startButton: 'Start first task',
    starting: 'Setting things up…',
    back: 'Back',
  },

  done: {
    heading: 'You are all set',
    opened: 'Your first task is open in a terminal window.',
    notOpened: 'The terminal did not open on its own. Copy the command below and run it in a terminal.',
    noTerminalTask: 'Open your AI coding tool in the folder to begin.',
    copyHeading: 'Run it yourself',
    copy: 'Copy command',
    openAgain: 'Open it again',
    commandsHeading: 'Five commands to try next',
    commandsHint: 'Type one of these in your AI coding tool.',
    finish: 'Finish',
    advanced: 'More options are under Advanced settings, in the tabs that appear next.',
  },

  copyDone: 'Copied',
  copyFailed: 'Select the text and copy it by hand.',
} as const;

/** Every string under `COPY`, functions called with a sample argument, for the wording test. */
export function allCopy(value: unknown = COPY): string[] {
  if (typeof value === 'string') return [value];
  if (typeof value === 'function') return [String((value as (...args: unknown[]) => unknown)('sample', 2))];
  if (value !== null && typeof value === 'object') return Object.values(value).flatMap((entry) => allCopy(entry));
  return [];
}
