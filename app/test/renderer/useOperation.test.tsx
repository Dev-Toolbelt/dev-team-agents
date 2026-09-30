// @vitest-environment jsdom
/**
 * `useOperation` and `useAction` are the seam every screen stands on, so what they get
 * wrong is wrong everywhere: a result shown for a subject it was not produced for, a
 * reload that blanks the screen, an IPC rejection that leaves a button pending forever.
 */
import './setup.js';

import { act, renderHook, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { useAction, useOperation } from '../../src/renderer/useOperation.js';
import type { OperationResult } from '../../src/shared/api.js';
import { deferred, fail, ok } from './support.js';

describe('useOperation — deps', () => {
  it('drops the previous subject’s result the moment its deps change', async () => {
    const second = deferred<OperationResult<string>>();
    const operation = vi.fn((id: string) => (id === 'a' ? Promise.resolve(ok('result for a')) : second.promise));
    const { result, rerender } = renderHook(({ id }) => useOperation(() => operation(id), [id]), {
      initialProps: { id: 'a' },
    });
    await waitFor(() => expect(result.current.state.phase).toBe('done'));

    rerender({ id: 'b' });

    // The render that follows the change already shows nothing of A.
    expect(result.current.state.phase).toBe('loading');

    await act(() => {
      second.resolve(ok('result for b'));
      return Promise.resolve();
    });
    expect(result.current.state).toMatchObject({ phase: 'done', result: { data: 'result for b' } });
  });

  it('keeps the result on screen across a reload of the same deps, and flags it as refreshing', async () => {
    const again = deferred<OperationResult<string>>();
    const operation = vi
      .fn<() => Promise<OperationResult<string>>>()
      .mockResolvedValueOnce(ok('first'))
      .mockReturnValueOnce(again.promise);
    const { result } = renderHook(() => useOperation(() => operation(), []));
    await waitFor(() => expect(result.current.state.phase).toBe('done'));

    act(() => result.current.reload());

    expect(result.current.state).toMatchObject({ phase: 'done', result: { data: 'first' } });
    expect(result.current.refreshing).toBe(true);

    await act(() => {
      again.resolve(ok('second'));
      return Promise.resolve();
    });
    expect(result.current.state).toMatchObject({ result: { data: 'second' } });
    expect(result.current.refreshing).toBe(false);
  });

  it('ignores an answer that arrives after its deps were replaced', async () => {
    const slow = deferred<OperationResult<string>>();
    const operation = vi.fn((id: string) => (id === 'a' ? slow.promise : Promise.resolve(ok('result for b'))));
    const { result, rerender } = renderHook(({ id }) => useOperation(() => operation(id), [id]), {
      initialProps: { id: 'a' },
    });
    rerender({ id: 'b' });
    await waitFor(() => expect(result.current.state.phase).toBe('done'));

    await act(() => {
      slow.resolve(ok('late result for a'));
      return Promise.resolve();
    });

    expect(result.current.state).toMatchObject({ result: { data: 'result for b' } });
  });

  it('turns a rejected bridge call into an unavailable result', async () => {
    const { result } = renderHook(() => useOperation((): Promise<OperationResult<string>> => Promise.reject(new Error('handler gone')), []));

    await waitFor(() => expect(result.current.state.phase).toBe('done'));
    expect(result.current.state).toMatchObject({ result: { ok: false, kind: 'unavailable' } });
  });
});

describe('useAction — rejection', () => {
  it('ends in an unavailable result instead of staying pending', async () => {
    const { result } = renderHook(() => useAction((): Promise<OperationResult<string>> => Promise.reject(new Error('handler gone'))));

    let returned: OperationResult<string> | undefined;
    await act(async () => {
      returned = await result.current.run();
    });

    expect(returned).toMatchObject({ ok: false, kind: 'unavailable' });
    expect(result.current.state).toMatchObject({ phase: 'done', result: { ok: false, kind: 'unavailable' } });
  });

  it('treats an action that throws before returning a promise like a rejection', async () => {
    const { result } = renderHook(() =>
      useAction((): Promise<OperationResult<string>> => {
        throw new Error('thrown synchronously');
      }),
    );

    await act(async () => {
      await result.current.run();
    });

    expect(result.current.state).toMatchObject({ phase: 'done', result: { ok: false, kind: 'unavailable' } });
  });

  it('lets an action whose result is not an OperationResult choose its own fallback', async () => {
    const { result } = renderHook(() =>
      useAction(
        (): Promise<{ chosen: boolean }> => Promise.reject(new Error('no picker')),
        () => ({ chosen: false }),
      ),
    );

    await act(async () => {
      await result.current.run();
    });

    expect(result.current.state).toEqual({ phase: 'done', result: { chosen: false } });
  });

  it('passes a resolved failure through untouched', async () => {
    const { result } = renderHook(() => useAction(() => Promise.resolve(fail('refused', { kind: 'refused' }))));
    await act(async () => {
      await result.current.run();
    });
    expect(result.current.state).toMatchObject({ result: { kind: 'refused', message: 'refused' } });
  });
});
