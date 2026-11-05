import { useRef, useState, type KeyboardEvent, type ReactElement, type ReactNode } from 'react';
import { Crosshair, Flame, Layers, ListTree, Maximize2, Minimize2, RotateCcw, Scan, ZoomIn, ZoomOut } from 'lucide-react';

import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Hint } from '@/components/ui/tooltip';
import { COLLAPSE_LEVELS, type CollapseLevel } from '../canvasModel.js';

// `nodrag nopan` keeps a press on the toolbar from reaching React Flow's pan handler.
const BUTTON_CLASS = 'nodrag nopan text-muted-foreground hover:text-foreground';
const PRESSED_CLASS = 'border-primary bg-primary/10 text-primary hover:text-primary';
const DISABLED_CLASS = 'aria-disabled:cursor-not-allowed aria-disabled:opacity-50';

export interface CanvasToolbarProps {
  readonly level: CollapseLevel;
  readonly onLevel: (level: CollapseLevel) => void;
  readonly onFitView: () => void;
  readonly onZoomIn: () => void;
  readonly onZoomOut: () => void;
  readonly focusOn: boolean;
  /** No agent is selected, so there is nothing to focus on. */
  readonly focusDisabled: boolean;
  readonly onFocus: () => void;
  readonly heatOn: boolean;
  readonly onHeat: () => void;
  readonly outlineOn: boolean;
  readonly onOutline: () => void;
  readonly fullScreen: boolean;
  readonly onFullScreen: () => void;
  readonly canReset: boolean;
  readonly onReset: () => void;
}

/** Where Tab lands in the toolbar, and how its arrow keys reach every button (WAI-ARIA toolbar). */
interface Roving {
  readonly active: string;
  readonly onFocus: (id: string) => void;
}

/**
 * One icon button. Its accessible name is `label`; the tooltip on the button itself says what it
 * does. A button that cannot act now is `aria-disabled` rather than `disabled`, so it stays
 * focusable and its tooltip still explains why; the same node serves both states.
 */
function ToolButton({
  id,
  roving,
  label,
  hint,
  pressed,
  disabled = false,
  onClick,
  children,
}: {
  id: string;
  roving: Roving;
  label: string;
  hint?: string;
  pressed?: boolean;
  disabled?: boolean;
  onClick: () => void;
  children: ReactNode;
}) {
  return (
    <Hint content={hint ?? label} side="right">
      <Button
        variant="outline"
        size="icon-sm"
        data-tool={id}
        tabIndex={roving.active === id ? 0 : -1}
        onFocus={() => roving.onFocus(id)}
        aria-label={label}
        aria-pressed={pressed}
        aria-disabled={disabled ? true : undefined}
        onClick={(event) => {
          if (disabled) {
            event.preventDefault();
            return;
          }
          onClick();
        }}
        className={`${BUTTON_CLASS} ${DISABLED_CLASS} ${pressed === true ? PRESSED_CLASS : ''}`}
      >
        {children}
      </Button>
    </Hint>
  );
}

function Divider(): ReactElement {
  return <span aria-hidden="true" className="mx-1 my-0.5 h-px bg-border" />;
}

/** Up and Down move between the buttons and wrap; Home and End jump to the first and the last. */
function moveFocus(event: KeyboardEvent<HTMLDivElement>) {
  // A control that handled the key itself (the Show trigger opens its menu on Down) keeps it.
  if (event.defaultPrevented) return;
  if (!['ArrowDown', 'ArrowUp', 'Home', 'End'].includes(event.key)) return;
  const buttons = Array.from(event.currentTarget.querySelectorAll<HTMLButtonElement>('button[data-tool]'));
  const at = buttons.indexOf(document.activeElement as HTMLButtonElement);
  if (at === -1) return;
  event.preventDefault();
  const last = buttons.length - 1;
  const next =
    event.key === 'Home' ? 0 : event.key === 'End' ? last : (at + (event.key === 'ArrowDown' ? 1 : -1) + buttons.length) % buttons.length;
  buttons[next]!.focus();
}

/** The canvas controls: a vertical strip of icon buttons in the canvas's top-left corner. */
export function CanvasToolbar(props: CanvasToolbarProps) {
  const levelLabel = COLLAPSE_LEVELS.find((each) => each.value === props.level)?.label ?? props.level;
  const [active, setActive] = useState('fit');
  const roving: Roving = { active, onFocus: setActive };

  // The menu hands focus back to its trigger on close; that focus must not raise the trigger's
  // tooltip, or the next Esc would only close the tooltip.
  const [showHint, setShowHint] = useState(false);
  const showTrigger = useRef<HTMLButtonElement>(null);
  const returning = useRef(false);
  const interactedOutside = useRef(false);

  return (
    <div
      role="toolbar"
      aria-label="Canvas controls"
      aria-orientation="vertical"
      onKeyDown={moveFocus}
      className="nodrag nopan flex flex-col gap-1 rounded-lg border bg-card/95 p-1 shadow-sm backdrop-blur-sm"
    >
      <ToolButton id="fit" roving={roving} label="Fit view" onClick={props.onFitView}>
        <Scan aria-hidden="true" />
      </ToolButton>
      <ToolButton id="zoom-in" roving={roving} label="Zoom in" onClick={props.onZoomIn}>
        <ZoomIn aria-hidden="true" />
      </ToolButton>
      <ToolButton id="zoom-out" roving={roving} label="Zoom out" onClick={props.onZoomOut}>
        <ZoomOut aria-hidden="true" />
      </ToolButton>
      <Divider />
      <DropdownMenu>
        <Hint
          content={`Show: ${levelLabel}`}
          side="right"
          open={showHint}
          onOpenChange={(open) => {
            if (!open || !returning.current) setShowHint(open);
          }}
        >
          <DropdownMenuTrigger asChild>
            <Button
              ref={showTrigger}
              variant="outline"
              size="icon-sm"
              data-tool="show"
              tabIndex={active === 'show' ? 0 : -1}
              onFocus={() => setActive('show')}
              aria-label={`Show: ${levelLabel}`}
              className={BUTTON_CLASS}
            >
              <Layers aria-hidden="true" />
            </Button>
          </DropdownMenuTrigger>
        </Hint>
        <DropdownMenuContent
          side="right"
          align="start"
          className="nodrag nopan"
          onInteractOutside={(event) => {
            // As Radix does for a modal menu: only a right-click (or ctrl+left-click) outside keeps
            // focus where the user clicked; any other dismissal returns focus to the Show button.
            const original = event.detail.originalEvent;
            const button = 'button' in original ? original.button : -1;
            const ctrlKey = 'ctrlKey' in original && original.ctrlKey;
            interactedOutside.current = button === 2 || (button === 0 && ctrlKey);
          }}
          onCloseAutoFocus={(event) => {
            event.preventDefault();
            if (!interactedOutside.current) {
              returning.current = true;
              showTrigger.current?.focus();
              returning.current = false;
            }
            interactedOutside.current = false;
          }}
        >
          <DropdownMenuLabel>Show</DropdownMenuLabel>
          <DropdownMenuRadioGroup value={props.level} onValueChange={(value) => props.onLevel(value as CollapseLevel)}>
            {COLLAPSE_LEVELS.map((each) => (
              <DropdownMenuRadioItem key={each.value} value={each.value}>
                {each.label}
              </DropdownMenuRadioItem>
            ))}
          </DropdownMenuRadioGroup>
        </DropdownMenuContent>
      </DropdownMenu>
      <ToolButton
        id="focus"
        roving={roving}
        label="Focus"
        hint={props.focusDisabled ? 'Focus: select an agent to focus on it' : 'Focus: dim everything outside the selected agent’s line'}
        pressed={props.focusOn}
        disabled={props.focusDisabled}
        onClick={props.onFocus}
      >
        <Crosshair aria-hidden="true" />
      </ToolButton>
      <ToolButton
        id="heat"
        roving={roving}
        label="Token heatmap"
        hint="Token heatmap: shade agents by the tokens of their subtree"
        pressed={props.heatOn}
        onClick={props.onHeat}
      >
        <Flame aria-hidden="true" />
      </ToolButton>
      <Divider />
      <ToolButton
        id="outline"
        roving={roving}
        label="Outline"
        hint="Outline: the canvas as a keyboard-navigable list"
        pressed={props.outlineOn}
        onClick={props.onOutline}
      >
        <ListTree aria-hidden="true" />
      </ToolButton>
      <ToolButton id="full-screen" roving={roving} label={props.fullScreen ? 'Exit full screen' : 'Full screen'} onClick={props.onFullScreen}>
        {props.fullScreen ? <Minimize2 aria-hidden="true" /> : <Maximize2 aria-hidden="true" />}
      </ToolButton>
      <Divider />
      <ToolButton
        id="reset"
        roving={roving}
        label="Reset layout"
        hint="Reset layout: put every moved node back"
        disabled={!props.canReset}
        onClick={props.onReset}
      >
        <RotateCcw aria-hidden="true" />
      </ToolButton>
    </div>
  );
}
