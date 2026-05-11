---
name: postgres
description: PostgreSQL-specific patterns: MVCC, index types, partitioning, JSONB, CTEs, and query tuning.
---

# PostgreSQL Reference

## When to Load
Load when the project uses PostgreSQL (signal: `pg`, `psycopg2`, `postgres:` in docker-compose, `DATABASE_URL` with `postgres://`, `prisma` with `postgresql` provider).

## CLI Connection

```bash
psql "$DATABASE_URL"
# or with individual vars:
PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "${DB_PORT:-5432}" -U "$DB_USER" -d "$DB_NAME"
# Supabase local dev:
psql "postgresql://postgres:postgres@localhost:54322/postgres"
```

Key inspection commands:
```bash
psql -c "\d+ table_name"          # table structure + storage info
psql -c "EXPLAIN (ANALYZE, BUFFERS) SELECT ..."
psql -c "SELECT * FROM pg_stat_user_tables ORDER BY n_dead_tup DESC;"
psql -c "SELECT * FROM pg_stat_activity WHERE state = 'active';"
```

## MVCC & Transaction Isolation

| Isolation level | Default | Prevents |
|-----------------|---------|---------|
| Read Committed | ✅ PostgreSQL default | Dirty reads |
| Repeatable Read | — | Non-repeatable reads |
| Serializable | — | Phantom reads |

- Row versions (tuples) are never overwritten; old versions cleaned by `VACUUM`
- Long-running transactions prevent VACUUM from reclaiming dead tuples → table bloat
- Monitor with: `SELECT relname, n_dead_tup FROM pg_stat_user_tables ORDER BY n_dead_tup DESC`

## Index Types

| Type | Use when |
|------|----------|
| B-tree (default) | Equality and range queries on orderable types |
| GIN | Full-text search; JSONB containment (`@>`); array overlap |
| GiST | Geometric types; range types; nearest-neighbour |
| BRIN | Append-only large tables with sequential correlation (e.g., time series) |
| Hash | Equality-only; rarely preferred over B-tree |
| Partial | Index a subset of rows: `CREATE INDEX ON orders(user_id) WHERE status = 'active'` |

## JSONB vs JSON

- Use `jsonb` (binary storage, indexable, operators) over `json` (text storage, preserved order)
- GIN index on `jsonb`: `CREATE INDEX ON table USING GIN (col)` for `@>` and `?` operators
- Avoid storing deeply nested structures; flatten frequently queried keys into columns

## Partitioning

| Type | Best for |
|------|----------|
| Range | Time series (partition by month/year) |
| List | Enum-like values (region, status) |
| Hash | Even distribution without natural range |

Use `pg_partman` for automated range partition creation. Always include the partition key in queries to enable partition pruning.

## CTEs and Query Planning

- CTEs are **optimization fences** in Postgres < 12; in >= 12, the planner inlines non-recursive CTEs by default
- Force inlining: `WITH MATERIALIZED` (>= 12) or `NOT MATERIALIZED`
- `EXPLAIN (ANALYZE, BUFFERS)` is mandatory before merging slow queries
- Key stats: `Seq Scan` on large tables, `Rows Removed by Filter`, high `Buffers hit/read` ratio

## Common Gotchas

| Gotcha | Fix |
|--------|-----|
| `LIKE '%term%'` can't use B-tree | Use `pg_trgm` extension + GIN index |
| `OFFSET n` scans all preceding rows | Use keyset pagination: `WHERE id > :last_id` |
| `COUNT(*)` is expensive on large tables | Use `pg_stat_user_tables.n_live_tup` for estimates |
| `CURRENT_TIMESTAMP` vs `NOW()` | Same within a transaction; `clock_timestamp()` changes mid-transaction |
| UUID as PK causes index fragmentation | Use `gen_random_uuid()` (UUIDv4) or UUIDv7 for sequential behaviour |

## Extensions Worth Knowing

| Extension | Purpose |
|-----------|---------|
| `pg_trgm` | Trigram similarity for fuzzy search and LIKE index |
| `pgcrypto` | `gen_random_uuid()`, encryption functions |
| `uuid-ossp` | Alternative UUID generation |
| `pg_stat_statements` | Track slow query statistics |
| `timescaledb` | Time-series optimizations |
| `PostGIS` | Spatial data and geospatial queries |
