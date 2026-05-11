---
name: database-production
description: Production DB — zero-downtime migrations, pooling, backup, retention.
---

## Zero-Downtime Migrations

Schema changes on live tables require backward-compatible sequencing. Never issue a blocking `ALTER TABLE` directly on a large production table.

### Safe change sequence

| Change | Safe approach |
|--------|--------------|
| Add a nullable column | `ALTER TABLE … ADD COLUMN` — non-blocking in Postgres 11+ |
| Add a NOT NULL column | Add as nullable → backfill → add `DEFAULT` → add `NOT NULL` constraint |
| Rename a column | Add new column → dual-write both → migrate reads → drop old column |
| Add an index | `CREATE INDEX CONCURRENTLY` — never without `CONCURRENTLY` in production |
| Drop a column | Remove app references first → deploy → then drop |
| Change a column type | Add new column → backfill → swap application code → drop old column |

### Lock-free pattern for large tables (shadow table)

```sql
-- 1. Create shadow table with new schema
CREATE TABLE orders_new (LIKE orders INCLUDING ALL);
ALTER TABLE orders_new ADD COLUMN status_v2 text;

-- 2. Backfill in batches (avoid full-table lock)
INSERT INTO orders_new SELECT *, status::text FROM orders WHERE id BETWEEN 1 AND 10000;

-- 3. Sync ongoing writes with a trigger during cutover window
-- 4. Rename atomically
BEGIN;
ALTER TABLE orders RENAME TO orders_old;
ALTER TABLE orders_new RENAME TO orders;
COMMIT;
```

### Migration versioning tools

| Tool | Ecosystem | File format |
|------|-----------|------------|
| **Flyway** | JVM, any | `V1.0__description.sql` |
| **Liquibase** | JVM, any | `changelog.xml` or `.sql` |
| **Alembic** | Python / SQLAlchemy | `versions/xxxx_description.py` |
| **golang-migrate** | Go, any | `000001_description.up.sql` |
| **Supabase migrations** | Supabase | `supabase/migrations/YYYYMMDDHHMMSS_description.sql` |

**Rules for all tools:**
- Forward-only by default. Rollback migrations only when they are tested and the rollback is faster than a hotfix.
- Migration files are immutable after they run in any non-dev environment.
- Run migrations in CI before deploying application code.

---

## Connection Pooling

Direct connections are expensive. Always place a pooler between the application and the database in production.

### PgBouncer modes

| Mode | How it works | Best for |
|------|-------------|---------|
| **Session** | Connection held for the client's lifetime | Apps that use session-level features (SET, advisory locks, prepared statements) |
| **Transaction** | Connection returned to pool after each transaction | Stateless APIs — the default for most web apps |
| **Statement** | Connection returned after each statement | Rare; requires all queries to be auto-commit |

**Key config parameters:**
```ini
max_client_conn = 1000       # total clients PgBouncer will accept
default_pool_size = 20       # connections per user/db pair to Postgres
reserve_pool_size = 5        # extra connections for burst
pool_mode = transaction
server_idle_timeout = 600
```

### Managed proxies

| Service | When to use |
|---------|------------|
| **AWS RDS Proxy** | RDS/Aurora — handles failover automatically; use when Lambda or ECS tasks create many short-lived connections |
| **Cloud SQL Auth Proxy** | GCP Cloud SQL — IAM-based auth, no password in connection string; run as a sidecar |
| **Azure AD auth + connection pooling** | Azure SQL — use built-in retry policies |

**Pool sizing formula:** `pool_size = (num_cores * 2) + effective_spindle_count`. For SSDs, `effective_spindle_count = 1`. Start conservative; grow with evidence.

---

## Replication and Read Replicas

### Physical vs. logical replication

| Type | What it copies | Use case |
|------|---------------|---------|
| **Physical (streaming)** | Entire cluster byte-by-byte | HA standby, failover |
| **Logical** | Selected tables/rows (change stream) | Cross-version upgrades, selective replication, CDC |

### Replica lag — what to monitor

```sql
-- On the primary (Postgres)
SELECT client_addr, state, sent_lsn, write_lsn, flush_lsn, replay_lsn,
       (sent_lsn - replay_lsn) AS replication_lag_bytes
FROM pg_stat_replication;

-- On the replica
SELECT now() - pg_last_xact_replay_timestamp() AS replica_lag_seconds;
```

Alert threshold: lag > 30 s for OLTP replicas; tune per workload.

### Routing reads to replicas

- Route read-only queries (reports, exports, analytics) to replica by separate connection string.
- Never route writes to a replica — they will fail or silently buffer.
- Add retry logic for reads: if replica lag exceeds SLA, fall back to primary.

---

## Table Partitioning

Use partitioning when a table exceeds ~50 M rows or when you need fast partition-level operations (drops, archiving).

### Strategy selection

| Strategy | Partition key | Best for |
|----------|--------------|---------|
| **Range** | Date, timestamp, sequential ID | Time-series, logs, events |
| **Hash** | Any high-cardinality column | Distributing writes evenly (no clear range) |
| **List** | Low-cardinality categorical column | Region, status, tenant (small count) |

### PostgreSQL declarative partitioning

```sql
CREATE TABLE events (
    id          bigserial,
    created_at  timestamptz NOT NULL,
    payload     jsonb
) PARTITION BY RANGE (created_at);

CREATE TABLE events_2025_q1 PARTITION OF events
    FOR VALUES FROM ('2025-01-01') TO ('2025-04-01');
```

**Index strategy:** indexes on partitioned tables must be created on the parent; Postgres replicates them to all partitions.

**Pruning:** `WHERE created_at BETWEEN …` allows Postgres to skip irrelevant partitions. Always filter on the partition key.

---

## Backup and Recovery

### Target metrics first

| Metric | Definition | Typical targets |
|--------|-----------|----------------|
| **RPO** (Recovery Point Objective) | Maximum acceptable data loss | 1 min for OLTP, 24 h for analytics |
| **RTO** (Recovery Time Objective) | Maximum acceptable downtime | 15 min for critical, 4 h for non-critical |

### PostgreSQL

- **WAL archiving** → enables point-in-time recovery (PITR). Configure `archive_command` to ship WAL segments to durable storage (S3, GCS).
- **Logical backups** (`pg_dump`) → portable, cross-version. Suitable for small-to-medium databases. Not a substitute for WAL archiving at scale.
- **Physical backups** (`pg_basebackup`, pgBackRest, Barman) → fast restore, PITR-capable. Use for large databases.

**Verify backups.** Restore to a staging environment on a schedule (weekly minimum). A backup you haven't tested is not a backup.

### Managed cloud backups

| Service | Backup | PITR |
|---------|--------|------|
| AWS RDS / Aurora | Automated daily snapshots + WAL | Yes, up to 35 days |
| GCP Cloud SQL | Automated snapshots | Yes |
| Supabase | Daily backups (Pro+), PITR on Enterprise | Yes (Enterprise) |

---

## Data Retention and Archiving

### Retention policy by data class

| Class | Example | Retention | Action |
|-------|---------|-----------|--------|
| Transactional | Orders, payments | 7 years (financial) | Archive to cold storage |
| User activity logs | Page views, events | 90 days | Delete or aggregate |
| Audit trail | Permission changes | 2–7 years | Archive, immutable |
| Temporary | Sessions, OTP codes | TTL (hours) | Delete on expiry |

### Archiving pattern

1. Move cold rows to an archive table or export to S3/GCS parquet.
2. Delete from the live table using batched deletes to avoid long locks.
3. If using partitioning, drop old partitions instead of `DELETE` — much faster.

```sql
-- Batched delete (avoids table-level lock)
DELETE FROM events WHERE created_at < now() - interval '90 days'
  AND id IN (SELECT id FROM events WHERE created_at < now() - interval '90 days' LIMIT 1000);
```

### Compliance-driven deletion (GDPR / CCPA)

- Hard-delete PII on request; soft-deletes are not sufficient.
- Log the deletion event in an audit table (without the PII itself).
- Use encrypted columns or separate tables for PII to simplify deletion scope.

---

## Seed Data vs. Test Fixtures

| | Seed data | Test fixtures |
|--|-----------|--------------|
| **Purpose** | Initialize application state (reference tables, system users, config) | Provide known state for a specific test |
| **Scope** | Environment-wide | Test-scoped, isolated per test |
| **Idempotency** | Required — safe to run multiple times | Reset between tests |
| **Location** | `db/seeds/` or `seeds/` | `tests/fixtures/` or factory helpers |
| **In CI** | Run once after migrations | Reset per test suite or test |

**Seed script rules:**
- Use `INSERT … ON CONFLICT DO NOTHING` or `UPSERT` — never plain `INSERT` for seed data.
- Never depend on auto-increment IDs from seeds — use known UUIDs or slugs as stable references.
- Keep seeds minimal: only what the application cannot function without.
