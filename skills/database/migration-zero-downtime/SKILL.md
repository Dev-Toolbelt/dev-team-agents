---
name: migration-zero-downtime
description: Zero-downtime migrations — expand/contract and rollback.
---

## Core Rule

Every migration must be **forward-compatible** with the current application version and **backward-compatible** with the previous one. At no point during a deploy may a running app instance encounter a schema it cannot handle.

---

## Expand/Contract Pattern

Three separate deploys; never combine phases.

| Phase | What you deploy | What you do in the DB |
|---|---|---|
| **1 — Expand** | Current app (unchanged) | Add new column/table (nullable or with default) |
| **2 — Dual-write** | Updated app that writes to both old and new | Backfill existing rows; validate data in new shape |
| **3 — Contract** | App that reads/writes only new column | Drop old column/table |

- Never jump from Phase 1 to Phase 3 in one deploy.
- The gap between phases can be hours, days, or a sprint — whatever the rollback window requires.

---

## Safe vs Unsafe Operations

### Safe (can run without downtime)

| Operation | Notes |
|---|---|
| `ADD COLUMN` nullable | Must have no `NOT NULL` without a default |
| `ADD COLUMN` with `DEFAULT` | Postgres 11+: instant metadata change, no rewrite |
| `CREATE TABLE` | Always safe |
| `CREATE INDEX CONCURRENTLY` | Does not block reads or writes (Postgres) |
| `ADD FOREIGN KEY NOT VALID` | Skips full table scan; validate separately |

### Unsafe (cause locks or break running app)

| Operation | Risk |
|---|---|
| `ADD COLUMN NOT NULL` without default (pre-PG 11) | Full table rewrite, exclusive lock |
| `DROP COLUMN` | Running app may still SELECT or INSERT it |
| `RENAME COLUMN` | Breaks all app queries referencing old name |
| `CHANGE` data type | May require full table rewrite; queries may fail |
| `DROP TABLE` | Any app version referencing it fails immediately |

---

## Large Table Migrations

- **Batch updates**: update in chunks of ~1 000 rows per transaction; add a small sleep between batches to reduce lock pressure.
- **MySQL / MariaDB**: use `pt-online-schema-change` (Percona Toolkit) or `gh-ost` (GitHub) for `ALTER TABLE` on live tables.
- **Postgres**: use `pg_repack` to reclaim space or reorder rows without an exclusive lock; use `ALTER TABLE … SET DEFAULT` + background backfill instead of a single large `UPDATE`.
- Never run a single `UPDATE` touching millions of rows in one transaction.

---

## Index Creation

- **Postgres**: always use `CREATE INDEX CONCURRENTLY`; standard `CREATE INDEX` takes an exclusive lock.
- **MySQL**: `ALTER TABLE … ADD INDEX` is online by default in InnoDB (MySQL 5.6+), but verify with `ALGORITHM=INPLACE, LOCK=NONE`.
- Never create an index on a large live table without verifying the non-blocking path first.

---

## Rollback Strategy

- Every migration file must have a working `down` migration.
- **Test `down` in CI** before merging — not just `up`.
- For destructive operations (`DROP COLUMN`, `DROP TABLE`): take a snapshot or export the data before running the migration; store it somewhere recoverable for at least one release cycle.
- For data-type changes: keep the old column alongside the new one until the contract phase.

---

## Feature Flags

Gate new-schema app code behind a feature flag:

1. Deploy Phase 1 (Expand) with flag **off** — app ignores new column entirely.
2. Run migration to add new column.
3. Enable flag in staging; validate.
4. Enable flag in production.
5. Once stable, remove the flag and proceed to Phase 2 (Dual-write).

This decouples schema changes from behavior changes and allows instant rollback without a schema rollback.
