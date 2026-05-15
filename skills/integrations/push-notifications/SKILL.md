---
name: push-notifications
description: Web Push Notifications — service worker setup, VAPID, cross-browser compatibility, permission UX, subscription management, payload display, and security.
---

## Prerequisites

Web Push requires:
- **HTTPS** (or `localhost` for development) — service workers do not register on plain HTTP
- A registered and active **service worker**
- Browser support (see compatibility table below)

---

## Cross-Browser Compatibility

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

### Safari-specific requirements

**macOS Safari 16+:**
- Add `push_server_url` to `manifest.json` pointing to your VAPID push endpoint
- Safari validates the manifest before allowing subscription — missing field = silent failure
- Notification icon must be declared in manifest `icons` array

**iOS Safari 16.4+ (PWA only):**
- User must add the app to the home screen (`Add to Home Screen`) — push does not work in the Safari browser tab
- Detect this scenario: `window.navigator.standalone === true` (iOS) or `display-mode: standalone` (CSS)
- Show an explicit "Add to Home Screen" prompt with instructions before requesting push permission
- Silent failure if permission is requested before the app is installed — no error, no prompt

---

## Service Worker Registration

Register the service worker as early as possible in the app lifecycle, but defer the push subscription prompt to an explicit user action.

```js
// app entry point
if ('serviceWorker' in navigator && 'PushManager' in window) {
  navigator.serviceWorker.register('/sw.js')
    .then(reg => console.log('SW registered:', reg.scope))
    .catch(err => console.error('SW registration failed:', err));
}
```

**Key rules:**
- Register from the root path (`/sw.js`) unless scoping is intentional — a SW at `/app/sw.js` only controls `/app/**`
- Wait for `navigator.serviceWorker.ready` before calling `pushManager.subscribe()`
- One SW per origin — do not register multiple conflicting workers

---

## VAPID Keys

VAPID (Voluntary Application Server Identification) authenticates your server to push services without a vendor-specific FCM server key.

**Generate once, store securely:**
```bash
# Node.js — web-push library
npx web-push generate-vapid-keys
```

Outputs:
```
Public Key:  BExxx...  (expose in frontend bundle — safe)
Private Key: xxx...    (server-side ONLY — never in frontend)
```

- `VAPID_PUBLIC_KEY` → injected as env var into the frontend build (`VITE_VAPID_PUBLIC_KEY`, `NEXT_PUBLIC_VAPID_PUBLIC_KEY`, etc.)
- `VAPID_PRIVATE_KEY` → server-side only; never in client bundle
- Subject: `mailto:you@example.com` — required for VAPID headers

---

## Requesting Permission

**Never request on page load.** Permission prompts shown without context are immediately denied by most users, and repeated denials permanently block the prompt in Chrome.

### Double opt-in pattern (recommended)

1. Show your own UI prompt explaining the value ("Get notified when your order ships")
2. Only call `Notification.requestPermission()` after the user clicks "Enable"

```js
async function requestPushPermission() {
  const permission = await Notification.requestPermission();
  if (permission === 'granted') {
    await subscribeToPush();
  } else if (permission === 'denied') {
    // permission permanently blocked — show instructions to re-enable via browser settings
    showPermissionDeniedGuidance();
  }
  // 'default' = dismissed without choosing — do not retry immediately
}
```

**Check before prompting:**
```js
if (Notification.permission === 'default') {
  // safe to prompt
} else if (Notification.permission === 'denied') {
  // cannot prompt again — link to browser settings instructions
}
```

---

## Subscribing to Push

```js
async function subscribeToPush() {
  const reg = await navigator.serviceWorker.ready;

  const subscription = await reg.pushManager.subscribe({
    userVisibleOnly: true, // required — must always show a notification on push
    applicationServerKey: urlBase64ToUint8Array(import.meta.env.VITE_VAPID_PUBLIC_KEY),
  });

  // Send subscription to your backend
  await fetch('/api/push/subscribe', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(subscription),
  });
}

// Helper — convert VAPID public key from base64 to Uint8Array
function urlBase64ToUint8Array(base64String) {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
  const rawData = atob(base64);
  return Uint8Array.from([...rawData].map(c => c.charCodeAt(0)));
}
```

**`userVisibleOnly: true`** is mandatory — Chrome rejects subscriptions without it; it guarantees that every server push results in a visible notification (no silent background pushes).

---

## Service Worker: Handling Push Events

In `sw.js`:

```js
self.addEventListener('push', event => {
  if (!event.data) return;

  const data = event.data.json(); // or event.data.text()

  event.waitUntil(
    self.registration.showNotification(data.title, {
      body: data.body,
      icon: data.icon || '/icons/icon-192.png',
      badge: data.badge || '/icons/badge-72.png',
      image: data.image,          // large image (Android, not iOS)
      data: { url: data.url },    // passed to notificationclick
      actions: data.actions || [], // up to 2 actions on Android/desktop
      tag: data.tag,              // replace existing notification with same tag
      requireInteraction: false,  // keep notification until user interacts (desktop only)
      vibrate: [200, 100, 200],   // Android only
      silent: false,
    })
  );
});
```

### `NotificationOptions` browser support

| Option | Chrome | Firefox | Safari | Notes |
|--------|--------|---------|--------|-------|
| `body` | ✅ | ✅ | ✅ | Always supported |
| `icon` | ✅ | ✅ | ✅ | PNG recommended |
| `badge` | ✅ | ❌ | ❌ | Android status bar icon |
| `image` | ✅ | ❌ | ❌ | Large hero image |
| `actions` | ✅ | ❌ | ❌ | Max 2; buttons below notification body |
| `vibrate` | ✅ Android | ❌ | ❌ | |
| `requireInteraction` | ✅ | ❌ | ❌ | Desktop only |
| `tag` | ✅ | ✅ | ✅ | Dedup/replace |
| `silent` | ✅ | ✅ | ❌ | |

Design notifications to be useful with only `title`, `body`, and `icon` — the rest is progressive enhancement.

---

## Service Worker: Click Handling

```js
self.addEventListener('notificationclick', event => {
  event.notification.close();

  const targetUrl = event.notification.data?.url || '/';

  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then(windowClients => {
      // Focus existing tab if already open
      const existing = windowClients.find(c => c.url === targetUrl && 'focus' in c);
      if (existing) return existing.focus();
      // Otherwise open new tab
      return clients.openWindow(targetUrl);
    })
  );
});
```

Handle action button clicks via `event.action`:
```js
self.addEventListener('notificationclick', event => {
  event.notification.close();
  if (event.action === 'view') {
    clients.openWindow(event.notification.data.url);
  } else if (event.action === 'dismiss') {
    // nothing — notification already closed above
  }
});
```

---

## Subscription Management (Backend Integration)

### What to store per subscription

```json
{
  "endpoint": "https://fcm.googleapis.com/fcm/send/...",
  "keys": {
    "p256dh": "...",
    "auth": "..."
  },
  "userId": "...",
  "createdAt": "...",
  "userAgent": "..."
}
```

### Subscription expiry — `pushsubscriptionchange`

Subscriptions expire silently or are rotated by the browser. Handle renewal:

```js
self.addEventListener('pushsubscriptionchange', event => {
  event.waitUntil(
    self.registration.pushManager.subscribe(event.oldSubscription.options)
      .then(newSubscription =>
        fetch('/api/push/resubscribe', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            old: event.oldSubscription,
            new: newSubscription,
          }),
        })
      )
  );
});
```

**Backend rules:**
- Delete subscriptions that return HTTP 410 (Gone) or 404 from the push service — they are permanently invalid
- Handle 429 (Too Many Requests) with exponential backoff
- Never assume a subscription stored today will still work next month

---

## Sending Push from the Server (Node.js)

```js
import webpush from 'web-push';

webpush.setVapidDetails(
  'mailto:your@email.com',
  process.env.VAPID_PUBLIC_KEY,
  process.env.VAPID_PRIVATE_KEY,
);

await webpush.sendNotification(
  subscription, // object from database
  JSON.stringify({
    title: 'Order shipped',
    body: 'Your order #1234 is on its way.',
    icon: '/icons/icon-192.png',
    url: '/orders/1234',
    tag: 'order-1234',
  }),
);
```

Libraries per language:
| Language | Library |
|----------|---------|
| Node.js | `web-push` |
| Python | `pywebpush` |
| PHP | `minishlink/web-push` |
| Ruby | `webpush` gem |
| Go | `SherClockHolmes/webpush-go` |
| .NET | `Lib.Net.Http.WebPush` |

---

## Framework Integration

| Stack | Recommended approach |
|-------|---------------------|
| Next.js (App Router) | Register SW via `next-pwa` or custom `public/sw.js`; use `NEXT_PUBLIC_VAPID_PUBLIC_KEY` |
| Vite + React/Vue | `vite-plugin-pwa` (Workbox); inject SW with `injectManifest` strategy; access VAPID via `VITE_*` |
| Angular | `@angular/service-worker` handles SW; push handled via `SwPush` service |
| Nuxt 3 | `@vite-pwa/nuxt`; `useWebNotification` composable for permission |
| SvelteKit | Manual `static/sw.js`; no official PWA plugin — use `vite-plugin-pwa` |

---

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

---

## Security Checklist

- [ ] VAPID private key is server-side only — never in the frontend bundle
- [ ] `applicationServerKey` (public) is safe to expose in the bundle
- [ ] Subscription endpoints stored with the authenticated user — never accessible cross-user
- [ ] Push payload is validated on the server before sending
- [ ] No PII in the push payload — notification body is visible on the lock screen
- [ ] Backend deletes 410 subscriptions immediately to avoid endpoint enumeration
- [ ] HTTPS enforced end-to-end (required by spec)

---

## Push Notifications Checklist (Done)

- [ ] Feature detection — push opt-in UI hidden when not supported
- [ ] iOS PWA detection — "Add to Home Screen" prompt shown before permission request on iOS
- [ ] Permission requested only on explicit user action (never on page load)
- [ ] `pushsubscriptionchange` event handled in SW
- [ ] Subscription sent to backend and stored per authenticated user
- [ ] `notificationclick` opens correct URL and focuses existing tab if open
- [ ] Notifications work without `actions`/`image` (progressive enhancement)
- [ ] Backend deletes 410/404 subscriptions
- [ ] VAPID private key not in frontend bundle
- [ ] Safari macOS: `push_server_url` in manifest
- [ ] iOS: push tested in installed PWA, not browser tab
- [ ] No PII in notification body or payload
