import { describe, expect, it } from 'vitest';

import type { ToolRecord, ToolsReport } from '../src/shared/api.js';
import { summarizeTools } from '../src/shared/toolsSummary.js';

const tool = (name: string, status: ToolRecord['status'], reason: string | null = null): ToolRecord => ({
  name,
  version: null,
  purpose: '',
  status,
  method: null,
  path: null,
  reason,
});
const report = (tools: ToolRecord[], extra: Partial<ToolsReport> = {}): ToolsReport => ({
  bin_dir: '/b',
  platform: 'linux',
  skipped_all: null,
  on_path: true,
  tools,
  ...extra,
});

describe('summarizeTools (ADR-0060)', () => {
  it('is quiet when everything was already there, or the install was switched off', () => {
    expect(summarizeTools(report([tool('jq', 'present')]))).toEqual({ kind: 'quiet' });
    expect(summarizeTools(report([], { skipped_all: 'DEVTEAM_SKIP_TOOLS=1' }))).toEqual({ kind: 'quiet' });
  });

  it('names what was installed, and the PATH fix when the bin directory is off it', () => {
    expect(summarizeTools(report([tool('jq', 'installed'), tool('rg', 'installed')]))).toEqual({
      kind: 'installed',
      title: 'Installed helper tools: jq, rg.',
    });
    expect(summarizeTools(report([tool('jq', 'installed')], { on_path: false }))).toMatchObject({
      kind: 'installed',
      title: expect.stringContaining('Add /b to your PATH'),
    });
  });

  it('reports a failure with its reason even when other tools were installed', () => {
    const outcome = summarizeTools(report([tool('jq', 'installed'), tool('semgrep', 'failed', 'offline')]));
    expect(outcome).toEqual({
      kind: 'problem',
      title: '1 helper tool could not be installed',
      detail: 'semgrep (failed): offline',
    });
  });

  it('reports skipped tools as a problem too', () => {
    expect(summarizeTools(report([tool('a', 'skipped', 'no asset'), tool('b', 'skipped')]))).toMatchObject({
      kind: 'problem',
      title: '2 helper tools were skipped',
    });
  });
});
