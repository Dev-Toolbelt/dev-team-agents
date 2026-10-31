# Lazy Animation Runtime Boot on WebKit

Reference for `frontend-patterns` § Deferred Runtime Boot & Failsafes. Read it when scroll or entrance animations do not run in Safari (macOS or iOS) while Chrome and Firefox are fine, or when building a lazily loaded animation runtime behind a failsafe.

## Symptom

- Safari only: animations never start; content stays static (or hidden until the failsafe releases it)
- No console error
- `<html>` carries the failure marker (e.g. `motion-failed`) after a few seconds

## Root Cause

| # | Fact | Effect |
|---|------|--------|
| 1 | The animation runtime (GSAP + ScrollTrigger + Lenis, or similar) is a lazy chunk fetched by dynamic `import()` that only **starts after `window.load`** | Download time is added on top of the `load` time |
| 2 | WebKit **holds `load` (observed ~2.5 s; varies by version and network)** when the page has a `<video>` with a WebM/AV1 `<source>`, **even with `preload="none"`** | `load` fires late on Safari only |
| 3 | An inline failsafe marks the page failed after ~3 s without animations and releases the content. The marker is permanent | No retry ever happens |
| 4 | Late `load` + chunk download (worse on mobile networks) exceeds 3 s | The failsafe wins the race; animations stay off |

Names below (`motion-on`, `motion-failed`, `./index`, `initMotion`) are illustrative — adapt them. `motion-on` is set by the inline `<head>` script, which also owns the `prefers-reduced-motion` check.

## Diagnosis — Confirm Before Changing Anything

Report each item; if the cause differs, stop and report instead of applying the fix below.

| Look for | Question |
|----------|----------|
| Runtime import site | Which event triggers the `import()`: `load`, `DOMContentLoaded`, `requestIdleCallback`, `client:idle`, …? |
| Failsafe | Is there a timer/class/flag that disables motion? What is its delay? Is the marker permanent? |
| Media | Any `<video>` with a WebM/AV1/OGG `<source>`, or other media that can hold `load`? |
| Initial hidden state | How CSS hides animated elements (e.g. `html.motion-on:not(.motion-failed) .reveal { opacity: 0 }`) |

## Fix — Three Parts, All Required

### A) Start the download early; gate only the initialization

- Start `import()` **immediately** when the module runs (module scripts are deferred, so this is effectively `DOMContentLoaded`)
- Attach `.catch()` at creation so an early rejection is never unhandled; on failure apply the failure marker at once. `fail` may run twice on a rejection (early catch + `start`'s catch) — harmless, keep both
- Only `initMotion()` (main-thread setup) waits, for **whichever comes first**:
  - `window.load` → run inside `requestIdleCallback` (timeout ~1500 ms; fallback `setTimeout` ~200 ms)
  - a cap of **800 ms after `DOMContentLoaded`** → run **immediately**, since `load` is already late
- Guard against double execution (`started` flag + `clearTimeout` of the cap)
- Handle every `document.readyState`: `complete` (schedule now), `interactive` (arm the cap now), `loading` (arm it on `DOMContentLoaded`)
- If motion is not enabled (e.g. `prefers-reduced-motion`), do not download the chunk
- Do not initialize after the failsafe fired (content is already released), and have `initMotion()` signal success to the failsafe (clear its timer or set a ready marker) so the two never both act

```ts
const IDLE_TIMEOUT_MS = 1500;
export const FALLBACK_DELAY_MS = 200;
export const BOOT_CAP_MS = 800;

export function bootMotion(): void {
  const root = document.documentElement;
  if (!root.classList.contains("motion-on")) return;

  const fail = () => root.classList.add("motion-failed");

  const chunk = import("./index");
  chunk.catch(fail);
  const start = () => {
    if (root.classList.contains("motion-failed")) return;
    chunk.then((module) => module.initMotion()).catch(fail);
  };

  let started = false;
  let capTimer = 0;
  const schedule = (immediate = false) => {
    if (started) return;
    started = true;
    window.clearTimeout(capTimer);
    if (immediate) {
      start();
      return;
    }
    if (typeof window.requestIdleCallback === "function") {
      window.requestIdleCallback(start, { timeout: IDLE_TIMEOUT_MS });
    } else {
      window.setTimeout(start, FALLBACK_DELAY_MS);
    }
  };

  if (document.readyState === "complete") {
    schedule();
    return;
  }
  window.addEventListener("load", () => schedule(), { once: true });
  const armCap = () => {
    capTimer = window.setTimeout(() => schedule(true), BOOT_CAP_MS);
  };
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", armCap, { once: true });
  } else {
    armCap();
  }
}
```

### B) Keep WebM/AV1 sources out of the initial load

- Render WebM/AV1 sources **without `src`**: `<source data-src="..." type="video/webm">`. Keep the MP4 `<source>` normal as the universal fallback
- Below-the-fold poster → `data-poster` instead of `poster`, so it does not compete with the hero
- After `load` (listeners are attached only then), hydrate the deferred sources **once**, on the first of:
  - the video nears the viewport (`IntersectionObserver`, `rootMargin: "1500px 0px"`; without `IntersectionObserver`, hydrate directly)
  - play intent: `pointerdown` / `keydown` on the section (capture), or the video's `play` event
- On hydration: create real `<source>` elements and insert them **before** the first normal source so capable browsers still prefer WebM/AV1; remove the placeholders, apply the poster, and call `video.load()` **only if** playback has not started (`video.paused && video.currentTime === 0`)

```ts
const NEAR_VIEWPORT_MARGIN = "1500px 0px";

export function hydrateVideoSources(scene: HTMLElement, video: HTMLVideoElement): void {
  const deferred = Array.from(video.querySelectorAll<HTMLSourceElement>("source[data-src]"));
  const poster = video.dataset.poster;
  if (deferred.length === 0 && !poster) return;

  let done = false;
  let observer: IntersectionObserver | undefined;

  const hydrate = () => {
    if (done) return;
    done = true;
    observer?.disconnect();
    const anchor = video.querySelector("source:not([data-src])");
    if (poster && !video.getAttribute("poster")) video.poster = poster;
    for (const placeholder of deferred) {
      const src = placeholder.dataset.src;
      if (!src) continue;
      const source = document.createElement("source");
      source.type = placeholder.type;
      source.src = src;
      video.insertBefore(source, anchor);
      placeholder.remove();
    }
    if (video.paused && video.currentTime === 0) video.load();
  };

  const watchViewport = () => {
    if (done) return;
    scene.addEventListener("pointerdown", hydrate, { capture: true, once: true });
    scene.addEventListener("keydown", hydrate, { capture: true, once: true });
    video.addEventListener("play", hydrate, { once: true });
    if (typeof IntersectionObserver !== "function") {
      hydrate();
      return;
    }
    observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) hydrate();
      },
      { rootMargin: NEAR_VIEWPORT_MARGIN },
    );
    observer.observe(scene);
  };

  if (document.readyState === "complete") watchViewport();
  else window.addEventListener("load", watchViewport, { once: true });
}
```

### C) Keep the failsafe as it is

- **Never** raise the failsafe delay or remove it — it guarantees content is never left hidden. The fix is motion booting before it, not the failsafe waiting longer
- The failsafe lives in an inline `<head>` script, independent of the animation module

## Anti-patterns — Do Not Use

| Anti-pattern | Why it fails |
|--------------|--------------|
| Deferring the **download** to "`load` OR `DOMContentLoaded` + a delay" | On slow mobile networks the download still starts too late and the failsafe wins. The download must start at `DOMContentLoaded`; only initialization may wait |
| `preload="none"` on the `<video>` | WebKit still holds `load` because of the WebM/AV1 `<source>` |

## Tests

Use the project's runner (e.g. Vitest + jsdom) with fake timers and a mocked `document.readyState`.

| Unit | Case |
|------|------|
| Loader | No `motion-on` → nothing is imported |
| Loader | `import()` starts immediately, before `load` and before the cap |
| Loader | `load` before the cap → `initMotion` runs via `requestIdleCallback`; via `setTimeout` when it is absent |
| Loader | Cap before `load` → `initMotion` runs immediately, exactly once (a later `load` does not run it again) |
| Loader | `readyState` `complete` / `interactive` / `loading` each take the right path |
| Loader | Rejected import → `motion-failed` applied |
| Video | Hydration happens exactly once |
| Video | Hydrated sources keep their order and land before the MP4 source (use two deferred sources) |
| Video | `load()` is not called on a video that already started |
| Video | Works without `IntersectionObserver` |
| Video | No hydration before `load`, even on play intent |
| Loader | Failsafe already fired → `initMotion` is not called |

## Manual Verification

- Safari macOS and iOS (or Simulator): animations run; in Network, the animation chunk starts near `DOMContentLoaded`; `<html>` never gets `motion-failed`
- "Slow 4G" throttling: animations still start before 3 s
- `prefers-reduced-motion: reduce`: the chunk is not downloaded and content shows in its final state
- Video plays on Safari (MP4) and on Chrome (WebM/AV1, after hydration)
- Lighthouse Performance / LCP does not regress

## Record the Decision

Note it in the project's architecture docs or wiki so the failsafe is not "fixed" by lengthening it later: WebKit holds `load` because of the WebM/AV1 `<source>`, and the motion boot was losing the race against the failsafe.
