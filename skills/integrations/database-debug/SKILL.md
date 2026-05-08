---
name: database-debug
description: DB debug — slow queries, index inspection, lock detection. PostgreSQL, MySQL, Redis, MongoDB.
---

# Database Debug Toolkit

## PostgreSQL

**Execution plan**
```sql
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT) <your query>;
```

**Sequential scans on large tables** (signals missing indexes)
```sql
SELECT relname, seq_scan, idx_scan, n_live_tup
FROM pg_stat_user_tables
ORDER BY seq_scan DESC;
```

**Unused indexes** (candidates for removal)
```sql
SELECT indexrelname, idx_scan
FROM pg_stat_user_indexes
WHERE idx_scan = 0 AND indexrelname NOT LIKE 'pg_%';
```

**Active locks and blocking queries**
```sql
SELECT pid, state, wait_event_type, wait_event, left(query, 100) AS query
FROM pg_stat_activity
WHERE wait_event IS NOT NULL;
```

**Table and index sizes**
```sql
SELECT relname, pg_size_pretty(pg_total_relation_size(oid)) AS total_size
FROM pg_class WHERE relkind = 'r'
ORDER BY pg_total_relation_size(oid) DESC LIMIT 20;
```

**Top slow queries** (requires `pg_stat_statements` extension)
```sql
SELECT query, calls, mean_exec_time, total_exec_time
FROM pg_stat_statements
ORDER BY mean_exec_time DESC LIMIT 10;
```

**Missing foreign key indexes**
```sql
SELECT conrelid::regclass AS table, a.attname AS column
FROM pg_constraint c
JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = ANY(c.conkey)
WHERE c.contype = 'f'
  AND NOT EXISTS (
    SELECT 1 FROM pg_index i
    WHERE i.indrelid = c.conrelid AND a.attnum = ANY(i.indkey)
  );
```

**Bloat check** (dead tuples — signals need for VACUUM)
```sql
SELECT relname, n_dead_tup, n_live_tup,
  round(100 * n_dead_tup::numeric / nullif(n_live_tup + n_dead_tup, 0), 1) AS dead_pct
FROM pg_stat_user_tables
WHERE n_live_tup > 0
ORDER BY dead_pct DESC;
```

---

## MySQL / MariaDB

**Execution plan**
```sql
EXPLAIN FORMAT=JSON <your query>;
EXPLAIN ANALYZE <your query>;  -- MySQL 8.0+
```

**Index inspection**
```sql
SHOW INDEX FROM <table>;
SHOW TABLE STATUS LIKE '<table>';
```

**Top slow queries** (via Performance Schema)
```sql
SELECT digest_text, count_star, avg_timer_wait / 1e12 AS avg_sec
FROM performance_schema.events_statements_summary_by_digest
ORDER BY sum_timer_wait DESC LIMIT 10;
```

**Active connections and locks**
```sql
SHOW PROCESSLIST;
SELECT * FROM information_schema.INNODB_LOCKS;
SELECT * FROM information_schema.INNODB_LOCK_WAITS;
```

**Table sizes**
```sql
SELECT table_name,
  round(data_length / 1024 / 1024, 2) AS data_mb,
  round(index_length / 1024 / 1024, 2) AS index_mb
FROM information_schema.tables
WHERE table_schema = DATABASE()
ORDER BY data_length + index_length DESC;
```

---

## SQLite

**Execution plan**
```sql
EXPLAIN QUERY PLAN <your query>;
```

**Index list**
```sql
PRAGMA index_list('<table>');
PRAGMA index_info('<index_name>');
```

**Table info**
```sql
PRAGMA table_info('<table>');
PRAGMA integrity_check;
```

---

## MongoDB

**Query analysis**
```javascript
db.collection.find({ field: value }).explain("executionStats")
```

**Index inspection**
```javascript
db.collection.getIndexes()
db.collection.aggregate([{ $indexStats: {} }])
```

**Collection stats**
```javascript
db.runCommand({ collStats: "collection" })
db.runCommand({ dbStats: 1 })
```

**Slow operations** (requires profiler enabled)
```javascript
db.setProfilingLevel(1, { slowms: 100 })
db.system.profile.find().sort({ ts: -1 }).limit(10)
```

---

## Redis

```bash
redis-cli INFO memory          # memory usage and fragmentation
redis-cli INFO stats           # command stats, hit/miss rates
redis-cli INFO clients         # connected clients
redis-cli --bigkeys            # find largest keys by memory
redis-cli --hotkeys            # find most-accessed keys (requires maxmemory-policy allkeys-lfu)
redis-cli MONITOR              # live command stream — use briefly, high CPU overhead
redis-cli SLOWLOG GET 10       # last 10 slow commands
redis-cli LATENCY HISTORY event
```

**Key pattern inspection**
```bash
redis-cli --scan --pattern "prefix:*" | wc -l  # count keys matching pattern
redis-cli OBJECT ENCODING <key>                 # storage encoding
redis-cli OBJECT IDLETIME <key>                 # seconds since last access
redis-cli MEMORY USAGE <key>                    # bytes consumed by a key
```
