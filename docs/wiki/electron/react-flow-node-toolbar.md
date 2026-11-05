# React Flow NodeToolbar: visible only when selected, and needs nodrag nopan

**Origin:** Canvas view (ADR-0063) node actions and tests | 2026-11-05
**Tags:** react flow, @xyflow/react, NodeToolbar, nodrag, nopan, d3-zoom, d3-drag, jsdom, userEvent, canvas

> `NodeToolbar` renders only while its node is selected, and its buttons need `nodrag nopan` on the toolbar or the mousedown reaches d3-zoom's pan handler.

---

## What it is

The canvas (`app/src/renderer/screens/CanvasNode.tsx`) shows node actions in an `@xyflow/react` 12.12.1 `NodeToolbar`. Two of its behaviors are not obvious from the component's name.

## How it works

| Behavior | Consequence |
|----------|-------------|
| The default `isVisible` follows node selection | The toolbar is absent from the DOM until the node is selected. A test must select the node first; clicking the node's treeitem in the canvas outline selects it |
| Pointer events inside the toolbar bubble to the pane | Without `nodrag nopan` on the toolbar, a button's mousedown starts d3-zoom panning and d3-drag |

## Gotchas

- In jsdom the missing classes surface as an unhandled `TypeError: Cannot read properties of null (reading 'document')` from d3-drag's `nodrag`, while every test still passes. Read the test output, not only the pass count.
- `userEvent.click` triggers the error because it sends mousedown; `fireEvent.click` does not, so a test written with `fireEvent` hides the bug.
- Put `nodrag nopan` on the toolbar element itself, so every current and future button inside it is covered.

## References

- `app/src/renderer/screens/CanvasNode.tsx`
- `app/test/renderer/canvas.test.tsx`
- `docs/development/adrs/0063-the-canvas-view-reads-a-cli-derived-task-graph-rendered-with-react-flow-and-a-deterministic-own-layout.md`
