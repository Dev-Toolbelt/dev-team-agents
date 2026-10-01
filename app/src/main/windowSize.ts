/**
 * The main window's opening and minimum size, from the screen it opens on.
 *
 * A fixed 1080×760 left most of a laptop screen unused and let the window shrink to 720×520,
 * where the kanban's four columns and the project table no longer fit. The window now opens
 * at most of the work area (the screen minus menu bar and dock), capped so a large monitor
 * does not get a wall-to-wall window, and never shrinks below a size the screens are laid
 * out for. Every figure is clamped to the work area, so a small display still gets a window
 * that fits on it.
 *
 * Pure, so a test can check it without a display.
 */
export interface WorkArea {
  readonly width: number;
  readonly height: number;
}

export interface WindowSize {
  readonly width: number;
  readonly height: number;
  readonly minWidth: number;
  readonly minHeight: number;
}

const WIDTH_SHARE = 0.85;
const HEIGHT_SHARE = 0.88;
const MAX_WIDTH = 1600;
const MAX_HEIGHT = 1000;
const MIN_WIDTH = 1024;
const MIN_HEIGHT = 680;

export function windowSize(workArea: WorkArea): WindowSize {
  const minWidth = Math.min(MIN_WIDTH, workArea.width);
  const minHeight = Math.min(MIN_HEIGHT, workArea.height);
  const width = Math.max(minWidth, Math.min(MAX_WIDTH, Math.round(workArea.width * WIDTH_SHARE)));
  const height = Math.max(minHeight, Math.min(MAX_HEIGHT, Math.round(workArea.height * HEIGHT_SHARE)));
  return { width, height, minWidth, minHeight };
}
