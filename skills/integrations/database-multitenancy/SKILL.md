---
name: database-multitenancy
description: Multi-tenancy patterns for database isolation (RLS, schema-per-tenant, database-per-tenant) and vector search with pgvector for AI/RAG applications.
---

## Choosing a Multi-Tenancy Strategy

| Strategy | Isolation | Migration complexity | Cost | Best for |
|----------|-----------|---------------------|------|---------|
| **Row-Level Security (RLS)** | Logical (DB-enforced) | Single schema | Low | SaaS with many tenants, PostgreSQL-native stacks |
| **Schema-per-tenant** | Strong (namespace) | Multiplies with tenant count | Medium | ≤ a few hundred tenants, data residency requirements |
| **Database-per-tenant** | Maximum | Highest (separate infra) | High | Regulated industries (HIPAA, SOC 2), contractual isolation |

**Default recommendation:** start with RLS. Move to schema-per-tenant only when tenant count or compliance demands it. Never add database-per-tenant complexity speculatively.

---

## Row-Level Security (RLS)

### Core pattern

```sql
-- 1. Enable RLS on every tenant-scoped table
ALTER TABLE orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE orders FORCE ROW LEVEL SECURITY;  -- applies to table owner too

-- 2. Create a policy using the current tenant context
CREATE POLICY tenant_isolation ON orders
    USING (tenant_id = current_setting('app.tenant_id')::uuid);

-- 3. Set the tenant context at the start of every request
SET LOCAL app.tenant_id = '<tenant-uuid>';
```

### Setting tenant context

Set `app.tenant_id` (or equivalent) **within the transaction**, not at session level, to prevent context leaking across pooled connections.

```sql
BEGIN;
SET LOCAL app.tenant_id = '3fa85f64-5717-4562-b3fc-2c963f66afa6';
-- all queries in this transaction see only this tenant's rows
SELECT * FROM orders;
COMMIT;
```

With PgBouncer in **transaction mode**, `SET LOCAL` is the only safe option — session-level `SET` is lost when the connection returns to the pool.

### Supabase RLS

Detection: `supabase/` directory or `SUPABASE_URL` env var.

```sql
-- Use auth.uid() for authenticated users
CREATE POLICY "users see their own rows" ON profiles
    FOR SELECT USING (user_id = auth.uid());

-- Use JWT claims for tenant context
CREATE POLICY "tenant isolation" ON documents
    FOR ALL USING (
        tenant_id = (auth.jwt() -> 'app_metadata' ->> 'tenant_id')::uuid
    );
```

**Rules:**
- Every table exposed via PostgREST must have RLS enabled — app-level checks alone are insufficient.
- Never trust `user_metadata` for access control (user-controlled). Use `app_metadata` only.
- Test policies by `SET ROLE authenticated; SET LOCAL request.jwt.claims = '…';` before deploying.

### Common RLS mistakes

| Mistake | Consequence | Fix |
|---------|-------------|-----|
| `ENABLE ROW LEVEL SECURITY` without `FORCE` | Table owner bypasses policies | Always add `FORCE ROW LEVEL SECURITY` |
| `SET app.tenant_id` at session level with connection pooling | Tenant context leaks to next request | Use `SET LOCAL` inside transaction |
| Missing policy for `INSERT` | Tenant can insert into another tenant's data | Add `WITH CHECK` clause for write policies |
| Forgetting `SECURITY DEFINER` functions | Function runs as caller, bypassing RLS | Audit all `SECURITY DEFINER` functions |

---

## Schema-per-Tenant

### Structure

```
postgres database
├── tenant_abc (schema)
│   ├── users
│   ├── orders
│   └── products
├── tenant_xyz (schema)
│   ├── users
│   ├── orders
│   └── products
└── shared (schema)
    └── plans, features, system_config
```

### Search path configuration

```sql
-- Set per connection/session
SET search_path TO tenant_abc, shared, public;

-- Or per role
ALTER ROLE app_user SET search_path TO tenant_abc, shared, public;
```

### Migration strategy

- Run migrations against each tenant schema individually. Use a migration runner that supports schema iteration.
- Keep a manifest of tenant schemas in a `shared.tenants` table.
- Test migrations against a representative sample of tenant schemas in CI.

```bash
# Example: iterate schemas with psql
psql "$DATABASE_URL" -c "SELECT schema_name FROM information_schema.schemata WHERE schema_name LIKE 'tenant_%'" \
  | while read schema; do
      psql "$DATABASE_URL" -c "SET search_path TO $schema" -f migration.sql
    done
```

---

## Database-per-Tenant

Use only when contractual, regulatory, or security requirements mandate full infrastructure isolation.

**Operational requirements:**
- Automated provisioning (Terraform, Pulumi) for each tenant database.
- Centralized credentials management (AWS Secrets Manager, HashiCorp Vault).
- Monitoring and alerting per database — not just aggregate.
- Migration runner that enumerates and upgrades all tenant databases.

**Trade-offs:**
- Connection pool per database — N tenants × pool size connections to manage.
- Backup and PITR policy applies N times.
- Cross-tenant queries (aggregates, platform analytics) require ETL into a warehouse.

---

## Tenant-Scoped Indexes

Always include `tenant_id` as the **leading column** in composite indexes on multi-tenant tables.

```sql
-- Without tenant_id leading: scans all tenants' data
CREATE INDEX idx_orders_status ON orders (status);

-- Correct: tenant-first composite index
CREATE INDEX idx_orders_tenant_status ON orders (tenant_id, status);
CREATE INDEX idx_orders_tenant_created ON orders (tenant_id, created_at DESC);
```

---

## Vector Search with pgvector

### When to use pgvector vs. a dedicated vector database

| Scenario | Recommendation |
|----------|---------------|
| < 1 M vectors, existing Postgres stack | pgvector — zero additional infra |
| Metadata filtering alongside vector search | pgvector — SQL joins work natively |
| > 10 M vectors, < 50 ms p99 latency required | Dedicated DB (Pinecone, Weaviate, Qdrant) |
| Multi-modal or graph + vector | Dedicated DB |

### Setup

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE documents (
    id          bigserial PRIMARY KEY,
    tenant_id   uuid NOT NULL,
    content     text,
    embedding   vector(1536)   -- dimension must match the embedding model
);
```

### Index types

| Index | Algorithm | Build time | Query accuracy | Best for |
|-------|-----------|-----------|----------------|---------|
| **IVFFlat** | Inverted file | Fast | Approximate (tunable) | Up to ~5 M vectors |
| **HNSW** | Hierarchical NSW | Slower | Higher accuracy | Recommended for production |

```sql
-- HNSW index (preferred)
CREATE INDEX ON documents USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);

-- IVFFlat (faster build, lower accuracy)
CREATE INDEX ON documents USING ivfflat (embedding vector_l2_ops)
  WITH (lists = 100);
```

**`lists` for IVFFlat:** `sqrt(row_count)` as a starting point. Rebuild the index after significant data growth.

### Distance operators

| Operator | Distance metric | Use when |
|----------|----------------|---------|
| `<->` | L2 (Euclidean) | Raw embeddings, image similarity |
| `<=>` | Cosine | Text embeddings (OpenAI, Cohere, etc.) |
| `<#>` | Inner product | When vectors are normalized |

### Similarity search query

```sql
-- Find the 10 most similar documents to a query embedding, scoped to a tenant
SELECT id, content, 1 - (embedding <=> $1::vector) AS similarity
FROM documents
WHERE tenant_id = $2
ORDER BY embedding <=> $1::vector
LIMIT 10;
```

### Multi-tenant vector search

- Include `tenant_id` in the `WHERE` clause — pgvector does not enforce RLS on the index scan by default.
- Create a **partial index** per tenant for very high query volumes:

```sql
CREATE INDEX ON documents USING hnsw (embedding vector_cosine_ops)
  WHERE tenant_id = 'specific-tenant-uuid';
```

### Embedding model alignment

- The `vector(n)` dimension must match the embedding model's output dimension exactly.
- OpenAI `text-embedding-3-small`: 1536 dims. `text-embedding-3-large`: 3072 dims.
- Never mix embeddings from different models in the same column.
- Store the model name alongside embeddings to detect drift after model upgrades.

```sql
ALTER TABLE documents ADD COLUMN embedding_model text NOT NULL DEFAULT 'text-embedding-3-small';
```
