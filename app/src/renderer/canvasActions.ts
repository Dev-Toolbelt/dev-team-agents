/**
 * The canvas's extension point for node actions (stop, re-run, open terminal… later). Out of the
 * MVP's scope, so nothing is registered: `actionsFor` returns no action for any node today, and
 * the node renders its toolbar slot only when it does. Registering or removing a provider bumps
 * `version`, which the nodes subscribe to, so a provider added after the canvas drew shows at once.
 */
import type { GraphNode, ProjectId } from '../shared/api.js';

export interface CanvasActionContext {
  readonly projectId: ProjectId;
  /** The top session the node is drawn in. */
  readonly sessionId: string;
  /** The board record the node's task belongs to (a child session's, when folded in); null when none. */
  readonly recordId: string | null;
}

export interface CanvasAction {
  /** Stable id, unique per node. */
  readonly id: string;
  /** The button's visible text and accessible name. */
  readonly label: string;
  readonly run: (node: GraphNode, context: CanvasActionContext) => void | Promise<void>;
  /** When true the button shows but cannot be pressed. */
  readonly disabled?: boolean;
}

export type CanvasActionProvider = (node: GraphNode) => readonly CanvasAction[];

const providers: CanvasActionProvider[] = [];
const listeners = new Set<() => void>();
let version = 0;

function changed(): void {
  version += 1;
  for (const listener of listeners) listener();
}

export const canvasActions = {
  /** Adds a provider; returns the function that removes it again. */
  register(provider: CanvasActionProvider): () => void {
    providers.push(provider);
    changed();
    return () => {
      const at = providers.indexOf(provider);
      if (at === -1) return;
      providers.splice(at, 1);
      changed();
    };
  },
  actionsFor(node: GraphNode): readonly CanvasAction[] {
    return providers.flatMap((provider) => provider(node));
  },
  /** For `useSyncExternalStore`: called whenever the set of providers changes. */
  subscribe: (listener: () => void): (() => void) => {
    listeners.add(listener);
    return () => {
      listeners.delete(listener);
    };
  },
  /** A number that changes whenever the set of providers does. */
  version: (): number => version,
};
