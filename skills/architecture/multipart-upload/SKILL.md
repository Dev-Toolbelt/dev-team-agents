---
name: multipart-upload
description: Multipart/chunked file upload — pre-signed URLs, chunk management, progress tracking, retry logic, and storage config for backend, frontend, and devops.
---

# Multipart Upload

Use when uploading files > 5 MB or when upload reliability and progress feedback matter.

---

## When to Apply

| Signal | Action |
|--------|--------|
| File input expected to handle large files (images, video, docs, exports) | Apply this skill |
| S3 / R2 / GCS / Azure Blob storage detected | Apply this skill |
| Upload progress bar or resumable upload required | Apply this skill |
| `multipart`, `presigned`, `chunk` anywhere in the codebase | Apply this skill |

---

## Backend

### Pre-signed URL Flow (recommended — no binary through your server)

```
Client → POST /uploads/initiate       → { uploadId, key }
Client → POST /uploads/presign-chunk  → { presignedUrl, partNumber }
Client → PUT presignedUrl (chunk)     → ETag from S3
Client → POST /uploads/complete       → { url } (final assembled file)
Client → POST /uploads/abort          → cleanup on failure
```

**Initiate endpoint**
- Generate a unique `key` (UUID + original extension, never user-controlled)
- Validate file type via MIME sniff and extension allowlist — never trust `Content-Type` header alone
- Validate file size limit before issuing `uploadId`
- Store pending upload record in DB (`upload_id`, `key`, `user_id`, `status: pending`, `expires_at`)

**Pre-sign chunk endpoint**
- Verify `uploadId` belongs to the requesting user (ownership check)
- Part numbers start at 1; max 10 000 parts per S3 multipart upload
- Pre-signed URL TTL: 15–60 minutes per chunk

**Complete endpoint**
- Receive `[{ partNumber, ETag }]` array from client
- Call storage `completeMultipartUpload` with parts list
- Verify assembled file size matches declared size
- Update DB record: `status: complete`, `url`
- Return final CDN/storage URL

**Abort endpoint**
- Call storage `abortMultipartUpload`
- Delete DB record
- Schedule orphan cleanup job (uploads never completed after `expires_at`)

### Direct upload (small files only, < 5 MB)
Use a single pre-signed PUT URL — skip multipart entirely.

### Security rules
- Never expose the storage bucket name or region in the pre-signed URL path to client error messages
- Set CORS on the bucket to allow PUT from your domain only
- Store files under `private/` prefix; serve via CDN with signed cookies — never public bucket URLs
- Scan uploaded files with an async virus/malware scanner before marking `status: available`
- Enforce per-user and per-organization quotas at the initiate step

---

## Frontend

### Chunk strategy
```ts
const CHUNK_SIZE = 10 * 1024 * 1024  // 10 MB — adjust to latency/reliability trade-off

async function uploadFile(file: File) {
  const totalChunks = Math.ceil(file.size / CHUNK_SIZE)
  const { uploadId, key } = await api.initiateUpload({ filename: file.name, size: file.size })

  const parts: { partNumber: number; ETag: string }[] = []

  for (let i = 0; i < totalChunks; i++) {
    const chunk = file.slice(i * CHUNK_SIZE, (i + 1) * CHUNK_SIZE)
    const { presignedUrl } = await api.presignChunk({ uploadId, partNumber: i + 1 })

    const res = await fetch(presignedUrl, { method: 'PUT', body: chunk })
    parts.push({ partNumber: i + 1, ETag: res.headers.get('ETag')! })

    onProgress(Math.round(((i + 1) / totalChunks) * 100))
  }

  return api.completeUpload({ uploadId, key, parts })
}
```

### Progress tracking
- Track per-chunk progress via `XMLHttpRequest.upload.onprogress` for granular reporting
- Aggregate: `(completedChunks / totalChunks) * 100` for a simple bar
- Show bytes transferred and estimated time remaining for large files

### Retry logic
- On chunk failure: retry the failed chunk up to 3 times with exponential backoff (1s, 2s, 4s)
- On network loss: pause the queue; resume from the last successful chunk when reconnected
- On fatal failure (server error, quota exceeded): call abort endpoint, clear state, show user error

### UX rules
- Show upload progress bar from the moment upload starts — not after all chunks complete
- Disable the submit/confirm button while upload is in flight
- Provide a cancel button that calls the abort endpoint
- On page unload during upload: call abort via `navigator.sendBeacon` to clean up server-side

---

## DevOps

### AWS S3
```yaml
# Bucket CORS for multipart upload
CorsConfiguration:
  CorsRules:
    - AllowedOrigins: ["https://yourdomain.com"]
      AllowedMethods: [PUT, GET]
      AllowedHeaders: ["*"]
      ExposeHeaders: [ETag]
      MaxAgeSeconds: 3600
```

- Enable bucket versioning for compliance use cases
- Set lifecycle rule to abort incomplete multipart uploads after 24h:
  ```json
  { "AbortIncompleteMultipartUpload": { "DaysAfterInitiation": 1 } }
  ```
- Use S3 Transfer Acceleration for geographically distributed users

### Cloudflare R2
- R2 supports S3-compatible multipart API — same flow applies
- No egress fees; use for public-read CDN assets
- Set `AllowedMethods: [PUT]` in CORS — R2 does not require `ExposeHeaders: [ETag]` explicitly

### GCS / Azure Blob
- GCS: use signed URLs with `resumable` upload type for files > 5 MB
- Azure Blob: use Block Blob with `stageBlock` / `commitBlockList` — analogous to S3 parts

### Environment variables (always use secret manager — never hardcode)
```
STORAGE_BUCKET=
STORAGE_REGION=
STORAGE_PRESIGN_EXPIRY_SECONDS=900
UPLOAD_MAX_BYTES=524288000   # 500 MB
UPLOAD_ALLOWED_TYPES=image/jpeg,image/png,application/pdf
```
