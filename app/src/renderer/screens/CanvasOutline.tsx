import { useEffect, useMemo, useRef, useState, type KeyboardEvent } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';

import type { OutlineItem } from '../canvasModel.js';

interface Row {
  readonly item: OutlineItem;
  readonly level: number;
  readonly parent: string | null;
  readonly setSize: number;
  readonly position: number;
}

function flatten(items: readonly OutlineItem[], closed: ReadonlySet<string>): Row[] {
  const rows: Row[] = [];
  const walk = (list: readonly OutlineItem[], level: number, parent: string | null) => {
    list.forEach((item, index) => {
      rows.push({ item, level, parent, setSize: list.length, position: index + 1 });
      if (item.children.length > 0 && !closed.has(item.id)) walk(item.children, level + 1, item.id);
    });
  };
  walk(items, 1, null);
  return rows;
}

const KIND_WORD: Readonly<Record<OutlineItem['kind'], string>> = { session: 'Session', turn: 'Turn', node: '' };

/**
 * The canvas as an accessible tree (WAI-ARIA tree pattern, flat markup with `aria-level`): the
 * same hierarchy, reachable without a pointer. Arrow keys move, open and close; Home and End
 * jump; Enter or Space selects the item on the canvas. One tab stop (roving `tabindex`).
 */
export function CanvasOutline({
  items,
  selectedId,
  onSelect,
}: {
  items: readonly OutlineItem[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  const [closed, setClosed] = useState<ReadonlySet<string>>(() => new Set());
  const rows = useMemo(() => flatten(items, closed), [items, closed]);
  const [focusedId, setFocusedId] = useState<string | null>(null);
  const refs = useRef(new Map<string, HTMLLIElement>());
  const moved = useRef(false);

  const current = rows.find((row) => row.item.id === focusedId) ?? rows.find((row) => row.item.id === selectedId) ?? rows[0];

  useEffect(() => {
    if (!moved.current || current === undefined) return;
    moved.current = false;
    refs.current.get(current.item.id)?.focus();
  }, [current]);

  if (rows.length === 0) return <p className="p-3 text-sm text-muted-foreground">Nothing to list.</p>;

  const focus = (id: string | undefined) => {
    if (id === undefined) return;
    moved.current = true;
    setFocusedId(id);
  };
  const setOpen = (id: string, open: boolean) =>
    setClosed((was) => {
      const next = new Set(was);
      if (open) next.delete(id);
      else next.add(id);
      return next;
    });

  const onKeyDown = (event: KeyboardEvent<HTMLUListElement>) => {
    if (current === undefined) return;
    const at = rows.indexOf(current);
    const hasChildren = current.item.children.length > 0;
    const open = hasChildren && !closed.has(current.item.id);
    let handled = true;
    switch (event.key) {
      case 'ArrowDown':
        focus(rows[at + 1]?.item.id);
        break;
      case 'ArrowUp':
        focus(rows[at - 1]?.item.id);
        break;
      case 'Home':
        focus(rows[0]?.item.id);
        break;
      case 'End':
        focus(rows[rows.length - 1]?.item.id);
        break;
      case 'ArrowRight':
        if (hasChildren && !open) setOpen(current.item.id, true);
        else if (open) focus(rows[at + 1]?.item.id);
        break;
      case 'ArrowLeft':
        if (open) setOpen(current.item.id, false);
        else if (current.parent !== null) focus(current.parent);
        break;
      case 'Enter':
      case ' ':
        onSelect(current.item.id);
        break;
      default:
        handled = false;
    }
    if (handled) {
      event.preventDefault();
      event.stopPropagation();
    }
  };

  return (
    <ul role="tree" aria-label="Canvas outline" className="space-y-px p-2 text-sm" onKeyDown={onKeyDown}>
      {rows.map((row) => {
        const { item } = row;
        const hasChildren = item.children.length > 0;
        const open = hasChildren && !closed.has(item.id);
        const selected = item.id === selectedId;
        const word = KIND_WORD[item.kind];
        return (
          <li
            key={item.id}
            ref={(element) => {
              if (element === null) refs.current.delete(item.id);
              else refs.current.set(item.id, element);
            }}
            role="treeitem"
            aria-level={row.level}
            aria-setsize={row.setSize}
            aria-posinset={row.position}
            aria-expanded={hasChildren ? open : undefined}
            aria-selected={selected}
            aria-label={word !== '' ? `${word}: ${item.label}` : item.label}
            tabIndex={item.id === current?.item.id ? 0 : -1}
            onClick={() => {
              setFocusedId(item.id);
              onSelect(item.id);
            }}
            onFocus={() => setFocusedId(item.id)}
            style={{ paddingLeft: `${(row.level - 1) * 14 + 4}px` }}
            className={`flex cursor-default items-center gap-1 rounded-sm py-1 pr-2 outline-hidden focus-visible:ring-[3px] focus-visible:ring-ring/50 ${
              selected ? 'bg-accent font-medium text-accent-foreground' : 'hover:bg-accent/60'
            }`}
          >
            {hasChildren ? (
              <span
                aria-hidden="true"
                onClick={(event) => {
                  event.stopPropagation();
                  setOpen(item.id, !open);
                }}
                className="inline-flex shrink-0 text-muted-foreground"
              >
                {open ? <ChevronDown className="size-3.5" /> : <ChevronRight className="size-3.5" />}
              </span>
            ) : (
              <span aria-hidden="true" className="inline-block size-3.5 shrink-0" />
            )}
            <span className="min-w-0 truncate" title={item.label}>
              {word !== '' ? <span className="text-muted-foreground">{word}: </span> : null}
              {item.label}
            </span>
          </li>
        );
      })}
    </ul>
  );
}
