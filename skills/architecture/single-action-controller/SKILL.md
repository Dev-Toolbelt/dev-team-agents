---
name: single-action-controller
description: Mandatory Single Action Controller pattern — one controller class per HTTP action. Enforced for all backend controllers. Covers naming, structure, DI, routing, and review criteria.
---

# Single Action Controller Pattern

> **MANDATORY** — Every backend controller must follow this pattern. No exceptions unless the project's existing architecture explicitly pre-dates this rule and migration is out of scope.

---

## What It Is

One controller class handles exactly one HTTP action. No `index`, `store`, `show`, `update`, `destroy` methods in the same class. Each action gets its own file and class.

**Why:**
- Enforces SRP at the class level — a controller with 7 methods has 7 reasons to change
- Each controller has explicit, minimal dependencies injected into its constructor
- Testing is trivial — one input, one output, no shared state across methods
- File naming makes routing instantly readable

---

## Naming Convention

| HTTP Action | Class Name | File |
|-------------|-----------|------|
| `GET /orders` | `ListOrdersController` | `ListOrdersController.php` / `list_orders_controller.rb` / etc. |
| `POST /orders` | `CreateOrderController` | `CreateOrderController.php` |
| `GET /orders/{id}` | `ShowOrderController` | `ShowOrderController.php` |
| `PUT /orders/{id}` | `UpdateOrderController` | `UpdateOrderController.php` |
| `DELETE /orders/{id}` | `DeleteOrderController` | `DeleteOrderController.php` |
| `POST /orders/{id}/cancel` | `CancelOrderController` | `CancelOrderController.php` |

Pattern: `{Verb}{Resource}Controller` — verb is the business action, not the HTTP method.

---

## Structure

### One public method — the invokable

```php
// PHP (Laravel)
class CreateOrderController
{
    public function __construct(
        private readonly CreateOrderService $service,
        private readonly OrderRequest $request
    ) {}

    public function __invoke(Request $request): JsonResponse
    {
        $command = CreateOrderCommand::fromRequest($request);
        $order   = $this->service->execute($command);

        return response()->json(OrderResource::make($order), 201);
    }
}
```

```ts
// Node.js / NestJS
@Controller('orders')
export class CreateOrderController {
  constructor(private readonly service: CreateOrderService) {}

  @Post()
  async handle(@Body() dto: CreateOrderDto): Promise<OrderResponse> {
    return this.service.execute(dto)
  }
}
```

```python
# Python (Django / FastAPI)
class CreateOrderController:
    def __init__(self, service: CreateOrderService):
        self.service = service

    def __call__(self, request: Request) -> Response:
        command = CreateOrderCommand.from_request(request)
        order   = self.service.execute(command)
        return Response(OrderSchema.from_orm(order), status=201)
```

```go
// Go
type CreateOrderHandler struct {
    service CreateOrderService
}

func (h *CreateOrderHandler) ServeHTTP(w http.ResponseWriter, r *http.Request) {
    cmd, err := parseCreateOrderCommand(r)
    // ...
    order, err := h.service.Execute(r.Context(), cmd)
    // ...
    json.NewEncoder(w).Encode(order)
}
```

---

## Routing

Register each controller separately. Route names must mirror the controller name.

```php
// Laravel
Route::post('/orders',       CreateOrderController::class)->name('orders.create');
Route::get('/orders',        ListOrdersController::class)->name('orders.list');
Route::get('/orders/{id}',   ShowOrderController::class)->name('orders.show');
```

---

## Controller Responsibilities (ONLY these)

1. **Parse** the HTTP request into a typed command/DTO
2. **Delegate** to the service layer
3. **Transform** the result into an HTTP response

A controller must **never**:
- Contain business logic
- Query the database directly
- Handle authorization (use middleware/policies)
- Call multiple services and combine results (that is an orchestration service's job)

---

## Folder Structure

```
app/
  Http/
    Controllers/
      Orders/
        CreateOrderController.php
        ListOrdersController.php
        ShowOrderController.php
        UpdateOrderController.php
        DeleteOrderController.php
        CancelOrderController.php
      Users/
        CreateUserController.php
        ...
```

Group by domain/resource — never by HTTP method.

---

## Review Enforcement

When reviewing backend code, flag any controller that:

- `[BLOCKING]` Has more than one public action method
- `[BLOCKING]` Contains business logic (conditionals on domain state, calculations, DB queries)
- `[BLOCKING]` Instantiates its own dependencies (`new Service()` inside a method)
- `[SUGGESTION]` Name does not follow `{Verb}{Resource}Controller` pattern
- `[SUGGESTION]` Controller file is in a flat directory with no domain grouping

---

## Gotchas

- **CRUD resources**: resist the temptation to use framework resource controllers (`php artisan make:controller --resource`) — they produce multi-action controllers by default; generate individual files instead
- **Thin does not mean empty**: the controller still needs proper request parsing, DTO construction, and response formatting — it should be ~20–40 lines, not 5
- **Shared logic**: if two controllers share parsing logic (e.g., both accept `OrderFilter`), extract to a Request class or DTO factory — do not merge the controllers
