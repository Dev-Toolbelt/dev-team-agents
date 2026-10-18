# Push Notifications — Browser Compatibility

## Prerequisites

Web Push requires:
- **HTTPS** (or `localhost` for development) — service workers do not register on plain HTTP
- A registered and active **service worker**
- Browser support (see table below)

## Cross-Browser Support Matrix

| Browser | Desktop | Mobile | Notes |
|---------|---------|--------|-------|
| Chrome 50+ | ✅ Full | ✅ Android | Uses FCM relay; VAPID supported since Chrome 52 |
| Edge 17+ | ✅ Full | ✅ Android | Same engine as Chrome; FCM relay |
| Firefox 44+ | ✅ Full | ✅ Android | VAPID direct (no FCM relay); `applicationServerKey` required since FF 72 |
| Safari macOS 16+ | ✅ Full | — | Web Push via APNS; requires `push_server_url` in manifest |
| Safari iOS 16.4+ | — | ✅ **PWA only** | Only works when installed to home screen; not in Safari browser tab |
| Samsung Internet 4+ | ✅ | ✅ | FCM relay; same API as Chrome |
| Opera | ✅ | ✅ | Chromium-based; same as Chrome |
| Brave | ✅ | ✅ | Uses Chromium stack; FCM relay (can be blocked by shields — warn user) |

## Safari-Specific Requirements

**macOS Safari 16+:**
- Add `push_server_url` to `manifest.json` pointing to your VAPID push endpoint
- Safari validates the manifest before allowing subscription — missing field = silent failure
- Notification icon must be declared in manifest `icons` array

**iOS Safari 16.4+ (PWA only):**
- User must add the app to the home screen (`Add to Home Screen`) — push does not work in the Safari browser tab
- Detect: `window.navigator.standalone === true` (iOS) or `display-mode: standalone` (CSS)
- Show an explicit "Add to Home Screen" prompt with instructions **before** requesting push permission
- Silent failure if permission is requested before the app is installed — no error, no prompt

## Feature Detection & Graceful Degradation

Always detect before using:

```js
const pushSupported =
  'serviceWorker' in navigator &&
  'PushManager' in window &&
  'Notification' in window;

// iOS PWA-only check
const isIOSPWA =
  /iP(hone|ad|od)/.test(navigator.userAgent) &&
  window.navigator.standalone === true;

if (!pushSupported) {
  // Hide push opt-in UI entirely — do not show a broken prompt
}

if (/iP(hone|ad|od)/.test(navigator.userAgent) && !window.navigator.standalone) {
  // Show "Add to Home Screen" instructions before offering push
}
```

## Framework Integration

| Stack | Recommended approach |
|-------|---------------------|
| Next.js (App Router) | Register SW via `next-pwa` or custom `public/sw.js`; use `NEXT_PUBLIC_VAPID_PUBLIC_KEY` |
| Vite + React/Vue | `vite-plugin-pwa` (Workbox); inject SW with `injectManifest` strategy; access VAPID via `VITE_*` |
| Angular | `@angular/service-worker` handles SW; push handled via `SwPush` service |
| Nuxt 3 | `@vite-pwa/nuxt`; `useWebNotification` composable for permission |
| SvelteKit | Manual `static/sw.js`; no official PWA plugin — use `vite-plugin-pwa` |
