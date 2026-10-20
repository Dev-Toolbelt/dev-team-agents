import { useEffect, useRef, useState, type DragEvent, type KeyboardEvent } from 'react';
import { LayoutGrid, X } from 'lucide-react';

import { cn } from '@/lib/utils';

export interface BoardTab {
  readonly id: string;
  readonly name: string;
}

const DRAG_TYPE = 'application/x-devteam-board-tab';

/** Where a dragged tab would land: before or after the tab under the pointer. */
interface DropTarget {
  readonly id: string;
  readonly side: 'before' | 'after';
}

/**
 * The board's tab strip, read like a browser's: the overview first and fixed, then one tab per
 * open project kanban. Project tabs reorder by drag and drop or Ctrl/⌘+Shift+←/→, and close by
 * their × button, a middle click or Delete. Arrow keys move between tabs, Home and End jump.
 *
 * Panels are rendered by the caller with the ids from {@link tabId} and {@link panelId}.
 */
export function BoardTabs({
  tabs,
  active,
  onSelect,
  onClose,
  onMove,
}: {
  tabs: readonly BoardTab[];
  active: string | null;
  onSelect: (id: string | null) => void;
  onClose: (id: string) => void;
  onMove: (id: string, toIndex: number) => void;
}) {
  const buttons = useRef(new Map<string | null, HTMLButtonElement>());
  const dragged = useRef<string | null>(null);
  const [drop, setDrop] = useState<DropTarget | null>(null);
  // A close or move from the keyboard keeps focus in the strip, on the tab that is now on show.
  const focusAfterRender = useRef<string | null | undefined>(undefined);

  useEffect(() => {
    if (focusAfterRender.current === undefined) return;
    buttons.current.get(focusAfterRender.current)?.focus();
    focusAfterRender.current = undefined;
  });

  const ids: (string | null)[] = [null, ...tabs.map((each) => each.id)];

  function close(id: string, keepFocus: boolean) {
    if (keepFocus) {
      const index = tabs.findIndex((each) => each.id === id);
      const next = id === active ? (tabs[index + 1]?.id ?? tabs[index - 1]?.id ?? null) : active;
      focusAfterRender.current = next;
    }
    onClose(id);
  }

  function onKeyDown(event: KeyboardEvent<HTMLButtonElement>, id: string | null) {
    const index = ids.indexOf(id);
    const modifier = event.ctrlKey || event.metaKey;
    if (id !== null && modifier && event.shiftKey && (event.key === 'ArrowLeft' || event.key === 'ArrowRight')) {
      event.preventDefault();
      const position = index - 1;
      const target = event.key === 'ArrowLeft' ? position - 1 : position + 1;
      if (target >= 0 && target < tabs.length) {
        focusAfterRender.current = id;
        onMove(id, target);
      }
      return;
    }
    if (id !== null && event.key === 'Delete') {
      event.preventDefault();
      close(id, true);
      return;
    }
    let next: number | null = null;
    if (event.key === 'ArrowRight') next = (index + 1) % ids.length;
    else if (event.key === 'ArrowLeft') next = (index - 1 + ids.length) % ids.length;
    else if (event.key === 'Home') next = 0;
    else if (event.key === 'End') next = ids.length - 1;
    if (next === null) return;
    event.preventDefault();
    const target = ids[next] ?? null;
    buttons.current.get(target)?.focus();
    onSelect(target);
  }

  function onDragStart(event: DragEvent<HTMLDivElement>, id: string) {
    dragged.current = id;
    event.dataTransfer.effectAllowed = 'move';
    event.dataTransfer.setData(DRAG_TYPE, id);
    event.dataTransfer.setData('text/plain', tabs.find((each) => each.id === id)?.name ?? id);
  }

  function onDragOver(event: DragEvent<HTMLDivElement>, id: string) {
    if (dragged.current === null) return;
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
    const box = event.currentTarget.getBoundingClientRect();
    const side = event.clientX < box.left + box.width / 2 ? 'before' : 'after';
    if (drop?.id !== id || drop.side !== side) setDrop({ id, side });
  }

  function onDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    const source = dragged.current;
    const target = drop;
    endDrag();
    if (source === null || target === null || source === target.id) return;
    const rest = tabs.map((each) => each.id).filter((each) => each !== source);
    onMove(source, rest.indexOf(target.id) + (target.side === 'after' ? 1 : 0));
  }

  function endDrag() {
    dragged.current = null;
    setDrop(null);
  }

  function register(id: string | null) {
    return (element: HTMLButtonElement | null) => {
      if (element === null) buttons.current.delete(id);
      else buttons.current.set(id, element);
    };
  }

  return (
    <div role="tablist" aria-label="Board tabs" className="flex items-end gap-1 overflow-x-auto border-b">
      <button
        ref={register(null)}
        type="button"
        role="tab"
        id={tabId(null)}
        aria-selected={active === null}
        aria-controls={panelId(null)}
        tabIndex={active === null ? 0 : -1}
        onClick={() => onSelect(null)}
        onKeyDown={(event) => onKeyDown(event, null)}
        className={tabClass(active === null, 'px-3')}
      >
        <LayoutGrid className="size-4 shrink-0" aria-hidden="true" />
        Overview
      </button>
      {tabs.map((tab) => {
        const selected = tab.id === active;
        return (
          <div
            key={tab.id}
            draggable
            data-testid={`board-tab-${tab.id}`}
            data-drop={drop?.id === tab.id ? drop.side : undefined}
            onDragStart={(event) => onDragStart(event, tab.id)}
            onDragOver={(event) => onDragOver(event, tab.id)}
            onDragLeave={(event) => {
              // Crossing into the tab's own buttons is not leaving the tab.
              if (event.relatedTarget instanceof Node && event.currentTarget.contains(event.relatedTarget)) return;
              setDrop((each) => (each?.id === tab.id ? null : each));
            }}
            onDrop={onDrop}
            onDragEnd={endDrag}
            onMouseDown={(event) => {
              // The middle button would start the platform's autoscroll instead of closing.
              if (event.button === 1) event.preventDefault();
            }}
            onAuxClick={(event) => {
              if (event.button === 1) close(tab.id, false);
            }}
            className={cn(
              tabClass(selected, 'pr-1 pl-3'),
              'relative max-w-56 cursor-grab active:cursor-grabbing',
              drop?.id === tab.id && drop.side === 'before' && 'before:absolute before:inset-y-1 before:-left-0.5 before:w-0.5 before:rounded before:bg-primary',
              drop?.id === tab.id && drop.side === 'after' && 'after:absolute after:inset-y-1 after:-right-0.5 after:w-0.5 after:rounded after:bg-primary',
            )}
          >
            <button
              ref={register(tab.id)}
              type="button"
              role="tab"
              id={tabId(tab.id)}
              aria-selected={selected}
              aria-controls={panelId(tab.id)}
              aria-keyshortcuts="Delete Control+Shift+ArrowLeft Control+Shift+ArrowRight"
              tabIndex={selected ? 0 : -1}
              title={tab.name}
              onClick={() => onSelect(tab.id)}
              onKeyDown={(event) => onKeyDown(event, tab.id)}
              className="min-w-0 truncate text-left outline-hidden"
            >
              {tab.name}
            </button>
            {/* Hidden from assistive tech: a tablist holds only tabs, and Delete closes the focused tab. */}
            <button
              type="button"
              tabIndex={-1}
              aria-hidden="true"
              aria-label={`Close ${tab.name}`}
              title="Close tab"
              onClick={() => close(tab.id, false)}
              className="rounded p-0.5 text-muted-foreground hover:bg-muted hover:text-foreground"
            >
              <X className="size-3.5" aria-hidden="true" />
            </button>
          </div>
        );
      })}
    </div>
  );
}

// Project ids sit under their own prefix, so no project id can collide with the overview's.
export function tabId(id: string | null): string {
  return id === null ? 'board-tab-overview' : `board-tab-project-${id}`;
}

export function panelId(id: string | null): string {
  return id === null ? 'board-panel-overview' : `board-panel-project-${id}`;
}

function tabClass(selected: boolean, padding: string): string {
  return cn(
    'flex h-9 shrink-0 items-center gap-1.5 rounded-t-md border border-b-0 text-sm transition-colors select-none',
    'focus-within:ring-[3px] focus-within:ring-ring/50',
    padding,
    selected ? '-mb-px bg-background font-medium text-foreground' : 'border-transparent text-muted-foreground hover:bg-muted/60 hover:text-foreground',
  );
}
