---
name: mongodb
description: MongoDB patterns: schema design, indexes, aggregation pipeline, sharding, and Atlas.
---

# MongoDB Reference

## When to Load
Load when the project uses MongoDB (signal: `mongoose`, `mongodb`, `mongo:` in docker-compose, `MONGODB_URI`).

## CLI Connection

```bash
mongosh "$MONGO_URI"
# or with individual vars:
mongosh "mongodb://$DB_USER:$DB_PASSWORD@$DB_HOST:${DB_PORT:-27017}/$DB_NAME"
# Atlas:
mongosh "mongodb+srv://$DB_USER:$DB_PASSWORD@$ATLAS_CLUSTER/$DB_NAME"
```

Key inspection commands:
```js
db.stats()                                  // database size and counts
db.collection.stats()                       // collection storage details
db.collection.explain("executionStats").find({...})  // query plan
db.currentOp({ active: true })              // running operations
db.collection.getIndexes()                  // list all indexes
```

## Schema Design Principles

| Decision | Embed | Reference |
|----------|-------|-----------|
| Data is always accessed together | yes | — |
| Data grows unboundedly (comments on a post) | — | yes |
| Data is shared across many documents | — | yes |
| Max document size | — | 16 MB limit; embed only bounded sub-arrays |

**Rule of thumb**: embed for one-to-few; reference for one-to-many or many-to-many.

## Indexes

| Type | Use when |
|------|----------|
| Single-field | Filter or sort on one field |
| Compound | Multi-field queries; field order matches query selectivity |
| Multikey | Index array values; MongoDB creates one entry per array element |
| Text | Full-text search (`$text`); use Atlas Search for production |
| 2dsphere | Geospatial queries (`$near`, `$geoWithin`) |
| Partial | `partialFilterExpression` to index a subset of documents |
| Sparse | Skip documents where the field is absent |
| TTL | Auto-delete documents after a duration: `expireAfterSeconds` |

Always run `explain("executionStats")` to verify `IXSCAN` (not `COLLSCAN`).

## Aggregation Pipeline

Prefer aggregation over MapReduce (deprecated in 5.0+):
- `$match` → `$group` → `$sort` → `$limit` (always filter early, sort late)
- `$lookup` for joins (use only for occasional aggregations; not for hot paths)
- `$unwind` before `$group` when working with arrays
- `allowDiskUse: true` for large aggregations that exceed 100 MB memory limit

## Write Concerns & Read Preferences

| Concern | Guarantee |
|---------|-----------|
| `w: 1` (default) | Acknowledged by primary |
| `w: "majority"` | Acknowledged by majority of replica set members |
| `j: true` | Written to journal before acknowledgement |

For financial or critical data: use `w: "majority", j: true`.

Read preferences: `primary` (default, strong consistency), `primaryPreferred`, `secondary` (eventual consistency, lower load on primary).

## Sharding

- Shard key choice is critical and cannot be changed after collection creation
- Good shard key: high cardinality, even distribution, frequently in queries
- Bad shard key: low cardinality (e.g., boolean), monotonically increasing (e.g., timestamp → hotspot)
- Use hashed shard key for even distribution when range queries are rare

## Transactions

Available since MongoDB 4.0 (replica sets) and 4.2 (sharded clusters):
- Use sparingly; multi-document transactions have performance overhead
- Keep transactions short; avoid user interactions inside a transaction
- Prefer single-document atomic operations where possible

## Atlas-Specific

| Feature | Use when |
|---------|----------|
| Atlas Search | Full-text, fuzzy, autocomplete (Lucene-backed) |
| Atlas Triggers | React to DB events without polling |
| Atlas Data API | HTTP access without MongoDB driver |
| Online Archive | Auto-tier cold data to S3 |

## Common Gotchas

| Gotcha | Fix |
|--------|-----|
| `findOne` returns `null` not an exception | Always check for null before accessing fields |
| `_id` is an ObjectId, not a string | Serialize with `.toString()`; never compare `==` to a string |
| Unbounded array growth | Use `$push` with `$slice` or move to a separate collection |
| Schema-less does not mean schema-free | Use Mongoose validators or JSON Schema validation |
| Large `$in` arrays cause slow index scans | Cap `$in` lists; consider `$lookup` + `$match` |
