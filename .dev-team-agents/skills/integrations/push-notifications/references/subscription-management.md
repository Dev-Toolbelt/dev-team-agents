# Push Notifications — Subscription Management & Server-Side

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

## What to Store Per Subscription

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

---

## Subscription Expiry — `pushsubscriptionchange`

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
- Delete subscriptions that return HTTP 410 (Gone) or 404 from the push service — permanently invalid
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

## Libraries Per Language

| Language | Library |
|----------|---------|
| Node.js | `web-push` |
| Python | `pywebpush` |
| PHP | `minishlink/web-push` |
| Ruby | `webpush` gem |
| Go | `SherClockHolmes/webpush-go` |
| .NET | `Lib.Net.Http.WebPush` |
