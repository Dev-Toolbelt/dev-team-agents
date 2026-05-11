---
name: design-patterns
description: Design patterns — KISS, YAGNI, DRY, SOLID, GoF, DDD reference.
---

# Design Patterns

## Pragmatic Engineering Principles

These principles apply at every layer of the stack, independent of language or framework.

| Principle | Rule | Violated when... |
|-----------|------|------------------|
| **KISS** — Keep It Simple | Prefer the simplest solution that correctly solves the problem | A simpler approach exists but a more complex one was chosen without justification |
| **YAGNI** — You Aren't Gonna Need It | Don't build features, abstractions, or generalization until they are actually needed | Code is written for a hypothetical future requirement that doesn't exist yet |
| **DRY** — Don't Repeat Yourself | Every piece of knowledge has a single, authoritative representation | Logic, validation rules, or configuration are duplicated across two or more places |

### KISS — Observable violations
- Multiple layers of indirection for a straight-line operation
- Abstract base classes or interfaces with a single implementation
- Configuration system for a value that never changes
- Helper utilities that wrap a single built-in function call

### YAGNI — Observable violations
- Methods, parameters, or flags added "for future use"
- Generic or pluggable architecture for a system with one known use case
- Premature abstraction before a second consumer exists
- Feature flags or extension points with no current users

### DRY — Observable violations
- Copy-pasted logic across two or more files
- Identical validation rules defined independently per endpoint or form
- Hardcoded values (strings, numbers, URLs) repeated in multiple places
- Parallel data structures that must be kept manually in sync

---

## SOLID Principles

| Principle | Rule |
|-----------|------|
| **S** — Single Responsibility | A class/module has one reason to change |
| **O** — Open/Closed | Open for extension, closed for modification |
| **L** — Liskov Substitution | Subtypes must be substitutable for their base types |
| **I** — Interface Segregation | Clients should not depend on interfaces they don't use |
| **D** — Dependency Inversion | Depend on abstractions, not concretions |

---

## Creational Patterns

### Factory Method
Creates objects without specifying the exact class. Use when the creation logic may vary or is complex.
```
Creator → factoryMethod() → Product
```

### Abstract Factory
Creates families of related objects. Use when the system needs to be independent of how products are created.

### Builder
Constructs complex objects step by step. Use when an object has many optional parameters or construction phases.

### Singleton
Ensures a class has only one instance. Use sparingly — prefer dependency injection. Avoid in testable code.

---

## Structural Patterns

### Adapter
Converts an interface into another that clients expect. Use for integrating incompatible interfaces (e.g., third-party SDKs).

### Decorator
Adds responsibilities to objects dynamically. Prefer over subclassing for feature composition.

### Facade
Provides a simplified interface to a complex subsystem. Use to hide complexity from callers.

### Repository
Abstracts data access behind an interface. Decouples business logic from persistence technology.

### Proxy
Controls access to an object (lazy loading, caching, access control, logging).

---

## Behavioral Patterns

### Strategy
Defines a family of algorithms and makes them interchangeable. Use when behavior varies and should be swappable at runtime.

### Observer
Defines a one-to-many dependency so that when one object changes state, its dependents are notified. Use for event-driven systems.

### Command
Encapsulates a request as an object. Enables undo, queuing, and logging of operations.

### Chain of Responsibility
Passes a request through a chain of handlers. Use for pipelines (middleware, validation chains).

### Template Method
Defines the skeleton of an algorithm, deferring steps to subclasses. Use when multiple implementations share a common process.

---

## Domain-Driven Patterns

### Value Object
Immutable object defined by its attributes, not identity. Use for things like Money, Email, Address.

### Entity
Object with a unique identity that persists over time. Has a lifecycle (create, update, delete).

### Aggregate
Cluster of entities and value objects treated as a unit. Defines a consistency boundary.

### Service
Stateless operation that doesn't naturally belong to an entity or value object.

### Repository (DDD)
Provides collection-like access to aggregates. Hides storage details.

---

## Anti-Patterns to Avoid

| Anti-Pattern | Problem |
|-------------|---------|
| God Object | One class knows too much / does too much |
| Spaghetti Code | Unstructured, hard-to-follow control flow |
| Magic Numbers | Unnamed numeric literals — use named constants |
| Premature Optimization | Optimizing before profiling proves a bottleneck |
| Cargo Cult | Copying patterns without understanding why |
| Anemic Domain Model | Entities with no behavior — just getters/setters |

---

## Choosing a Pattern

1. Identify the problem: creation? structure? behavior?
2. Check if the pattern fits the context, not just the structure
3. Prefer the simplest solution — patterns add complexity
4. Document the choice in an ADR if it's non-obvious
