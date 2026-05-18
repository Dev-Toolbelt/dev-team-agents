# Push Notifications — Service Worker Setup & Event Handling

## Service Worker Registration

Register as early as possible in the app lifecycle, but defer the push subscription prompt to an explicit user action.

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

**`userVisibleOnly: true`** is mandatory — Chrome rejects subscriptions without it.

---

## Handling Push Events (in `sw.js`)

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

## Click Handling (in `sw.js`)

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
