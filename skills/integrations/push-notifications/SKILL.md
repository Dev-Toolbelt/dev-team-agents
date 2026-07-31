---
name: push-notifications
description: Web Push — service worker, VAPID, permission UX, subscriptions, browser support, security.
---

## Decision Table — What to Load

| Task | Load |
|------|------|
| Cross-browser support, Safari quirks, iOS PWA, framework integration | `references/browser-compatibility.md` |
| SW registration, permission flow, subscribing, push/click event handlers | `references/service-worker.md` |
| VAPID key generation, subscription storage, expiry, server-side sending | `references/subscription-management.md` |

Load only the reference(s) relevant to the current task.

---

## Core Rules (apply without loading references)

- **HTTPS required** — service workers do not register on plain HTTP (`localhost` is the only exception)
- **Never request permission on page load** — always tie the prompt to an explicit user action
- **`userVisibleOnly: true`** is mandatory in `pushManager.subscribe()` — Chrome rejects without it
- **VAPID private key is server-side only** — never in the frontend bundle
- **iOS push = PWA only** — does not work in the Safari browser tab; show "Add to Home Screen" first
- **Delete 410/404 subscriptions immediately** — they are permanently invalid
- **Design for `title` + `body` + `icon` only** — `actions`, `image`, `badge`, `vibrate` are progressive enhancement

---

## Prerequisites

1. HTTPS (or `localhost`)
2. Registered and active service worker
3. VAPID key pair generated and stored (`npx web-push generate-vapid-keys`)

---

## Quick-Start Flow

1. Register SW on app load (do not prompt yet)
2. On user action → check `Notification.permission` → show double opt-in UI → call `Notification.requestPermission()`
3. On grant → `pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: <vapid-public> })`
4. POST subscription object to backend → store per authenticated user
5. SW handles `push` event → `showNotification()`
6. SW handles `notificationclick` → focus or open the target URL
7. SW handles `pushsubscriptionchange` → resubscribe and update backend
8. Backend: delete subscriptions on 410/404; retry on 429 with backoff

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

## Implementation Checklist

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
