# Composition Root

The single place in the application where all object graphs are assembled. Every dependency binding (interface → concrete class, configuration → value) happens here and nowhere else.

## Why it matters

Without a Composition Root, dependency wiring leaks into services, controllers, and factories — making the object graph impossible to inspect, replace, or test. A well-defined Composition Root means:
- The rest of the codebase never calls `new ConcreteService()` directly
- Swapping an implementation (real → mock, v1 → v2) requires changing one file
- The full dependency tree is visible in one place

### Location rule

| Application type | Where the Composition Root lives |
|-----------------|----------------------------------|
| HTTP server | Entry point — `main`, `bootstrap`, `app`, `server` |
| CLI tool | Command entry point — `run`, `main`, `cmd/root` |
| Worker / daemon | Worker startup — `worker.start`, `consumer.run` |
| Serverless function | Handler initializer (outside the handler function) |
| Frontend SPA | App bootstrap — `main.tsx`, `app.module.ts`, `createApp()` |

**Rule**: the Composition Root is always as close to the process entry point as possible. It must NOT be inside a service, controller, or domain object.

### Agnostic structure (pseudocode)

```
// ── Composition Root (entry point) ──────────────────────

// 1. Build infrastructure
db         = Database.connect(env.DATABASE_URL)
cache      = Cache.connect(env.REDIS_URL)
mailer     = SmtpMailer(env.SMTP_HOST, env.SMTP_PORT)
storage    = S3Storage(env.BUCKET_NAME, env.REGION)

// 2. Build repositories (depend on infrastructure)
userRepo   = UserRepository(db)
orderRepo  = OrderRepository(db)

// 3. Build domain services (depend on repositories + infrastructure)
authService  = AuthService(userRepo, mailer)
orderService = OrderService(orderRepo, storage, cache)

// 4. Build controllers/handlers (depend on domain services)
authHandler  = AuthController(authService)
orderHandler = OrderController(orderService)

// 5. Register routes / wire the framework
app.register("/auth",  authHandler)
app.register("/orders", orderHandler)

app.listen(env.PORT)
```

## Anti-patterns

| Anti-pattern | Problem | Fix |
|---|---|---|
| `new` inside a service | Service controls its own dependencies — untestable | Inject via constructor |
| Service locator inside a class | Hidden dependency, hard to trace | Move wiring to Composition Root |
| DI container called from a service | `container.get(X)` inside business logic = service locator disguised | Only the Composition Root calls `container.get()` |
| Multiple Composition Roots | Object graph is split — inconsistent lifecycles | Merge into one; use modules/providers within it |
| Composition Root in a framework callback | Wiring inside a request handler or event listener | Move outside the hot path |

## Lifecycle management

Register each dependency with the correct lifecycle at the Composition Root:

| Lifecycle | When to use | Examples |
|-----------|-------------|---------|
| **Singleton** | One instance for the entire process lifetime | DB connection pool, config, logger |
| **Scoped** | One instance per request / unit of work | Repository, UoW, auth context |
| **Transient** | New instance every time | Stateless value objects, lightweight calculators |

**Rule**: never register a shorter-lived dependency into a longer-lived one (e.g., a scoped repo injected into a singleton service) — this creates a captive dependency that retains stale state.

## Composition Root vs DI container

A DI container (IoC container, service container) is a tool that automates object graph construction. The Composition Root is the concept — the single place where you configure that container. Both can coexist:

```
// Composition Root WITH a container
container.bind(UserRepository).toClass(SqlUserRepository).singleton()
container.bind(AuthService).toClass(AuthServiceImpl).scoped()
container.bind(Mailer).toClass(SmtpMailer).singleton()

// The container is resolved only here — never inside business code
app.use((req) => container.createScope().resolve(RequestHandler))
```

## When NOT to use a DI container

For small applications (< ~5 services), manual wiring at the Composition Root is simpler and more readable than configuring a container. Prefer a container when:
- The object graph is large (> ~10 dependencies)
- Lifecycle management (scoped per request) is needed automatically
- The framework already provides one (NestJS, Spring, Laravel, .NET)
