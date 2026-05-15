---
name: database-multitenancy
description: Multi-tenancy DB — RLS, schema-per-tenant, database-per-tenant.
---

## Choosing a Multi-Tenancy Strategy

| Strategy | Isolation | Migration complexity | Cost | Best for |
|----------|-----------|---------------------|------|---------|
| **Row-Level Security (RLS)** | Logical (DB-enforced) | Single schema | Low | SaaS with many tenants, PostgreSQL-native stacks |
| **Schema-per-tenant** | Strong (namespace) | Multiplies with tenant count | Medium | ≤ a few hundred tenants, data residency requirements |
| **Database-per-tenant** | Maximum | Highest (separate infra) | High | Regulated industries (HIPAA, SOC 2), contractual isolation |

**Default recommendation:** start with RLS. Move to schema-per-tenant only when tenant count or compliance demands it. Never add database-per-tenant complexity speculatively.

## Detection Signals

| Signal | Multi-tenancy indicator |
|--------|------------------------|
| `tenant_id` column in schema | RLS or shared-schema approach |
| Multiple schemas with identical structure | Schema-per-tenant |
| Multiple databases with identical structure | Database-per-tenant |
| `app.tenant_id` in SQL or ORM config | RLS with session variable |
| PgBouncer in transaction mode | RLS with `SET LOCAL` required |

## Quick Rules

- Always use `FORCE ROW LEVEL SECURITY` — not just `ENABLE` — so the table owner is also subject to policies.
- Use `SET LOCAL app.tenant_id` inside transactions, never at session level, when connection pooling is present.
- Include `tenant_id` as the **leading column** in all composite indexes on multi-tenant tables.
- Never trust `user_metadata` for access control in Supabase — use `app_metadata` only.

## Load on Demand

| When | Load |
|------|------|
| Implementing RLS, schema-per-tenant, database-per-tenant, or pgvector with multi-tenancy | `references/tenant-isolation.md` |
