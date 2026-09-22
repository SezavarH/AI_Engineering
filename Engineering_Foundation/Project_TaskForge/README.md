# TaskForge — Step-by-Step README

## Step 1 — Domain Models
*(Typing + Pydantic + Clean OOP Foundations)*

### Goal
Create a pure, well-typed domain model layer for TaskForge with no database, no FastAPI, and no asyncio.

### Concrete Task
Create `taskforge/models.py` containing:

- `User` (id, email, name, created_at)
- `Project` (id, name, owner_id, created_at)
- `Task` (id, project_id, title, description, status, priority, assignee_id, created_at, started_at, completed_at)

### Requirements
- Use `UUID` for all identifiers
- Use timezone-aware `datetime` for all timestamps
- Use `Enum` for `TaskStatus` and `TaskPriority`
- Make foreign keys (`owner_id`, `project_id`) required (no defaults)
- Make optional fields truly optional (`assignee_id`, `started_at`, `completed_at`)
- Give `created_at` a sensible UTC default via `Field(default_factory=...)`
- Add rich domain behavior:
  - `Task.is_open` → `@property`
  - `Task.duration` → `@property` (returns seconds as `float` or `None`)
  - A `model_validator` that prevents a task from being marked `DONE` without a `completed_at`

### Key Concepts Learned

**`@property`**  
Turns a method into something that looks and feels like a normal attribute.  
Instead of writing `task.is_open()`, you write `task.is_open`.  
Useful for derived/computed values that belong to the object.

**Pydantic `model_validator(mode="after")`**  
Runs after the model has been fully constructed.  
Perfect for cross-field validation rules (e.g. "if status is DONE then completed_at must exist").

**UUID vs int for IDs**  
UUIDs are preferred for public-facing identifiers because they are collision-resistant and safer when systems grow or data is merged.

**Foreign keys must not have defaults**  
`owner_id` and `project_id` reference existing objects. Giving them `default_factory=uuid.uuid4` would silently create random unrelated IDs.

### Common Mistakes & Corrections

| Mistake | Why it was a problem | Correct approach |
|---------|----------------------|------------------|
| Used `int` for IDs | Inconsistent and less safe | Use `uuid.UUID` everywhere |
| Used `str` for timestamps | Loses type safety and timezone info | Use `datetime` with `timezone.utc` |
| Gave foreign keys default UUIDs | Creates invalid relationships | Foreign keys are required, no default |
| Forgot defaults on some `created_at` fields | Inconsistent object creation | Always provide `Field(default_factory=...)` |
| Used old Pydantic v1 validator style | Does not work in Pydantic v2 | Use `@model_validator(mode="after")` |
| Didn't know `@property` | Couldn't add domain behavior | Learn that `@property` makes methods look like attributes |

### Final Design Decisions
- All models are Pydantic `BaseModel` (we will later introduce a clearer separation between domain objects and API schemas if needed)
- Status and priority are strict Enums
- Domain rules live inside the model (not in the service layer)
- Models remain pure (no I/O, no framework dependencies)

---

## Step 2 — Service Layer (Clean OOP)

### Goal
Create a clean service layer that owns the business logic and currently uses an in-memory store.  
This layer will later talk to a real repository and contain the async concurrency patterns.

### Concrete Task
Create `taskforge/services.py` with a `TaskService` class that implements:

- `create_task(...)`
- `get_task(...)`
- `list_tasks(...)`
- `start_task(...)`
- `complete_task(...)`

### Requirements
- Use a normal Python class (not a Pydantic model or dataclass)
- Initialize the in-memory store inside `__init__`:
  ```python
  self._tasks: dict[UUID, Task] = {}
  ```

---

## Step 3 — First Real Async (Controlled Concurrency)

### Goal
Add the ability to process multiple tasks concurrently while limiting the number of tasks that run at the same time.

### Concrete Task
Add this method to `TaskService`:

```python
async def process_tasks(
    self,
    task_ids: list[UUID],
    max_concurrent: int = 3,
) -> list[Task]:
```

### Requirements
- Limit concurrency with `asyncio.Semaphore`
- For each task:
  1. Call `start_task`
  2. Simulate work with `await asyncio.sleep(...)`
  3. Call `complete_task`
- Use `asyncio.gather` (or `TaskGroup`) to run the tasks concurrently
- Decide on an error strategy (fail-fast or continue-on-error) and document it

### Key Concepts Learned

**`asyncio.Semaphore`**  
A concurrency primitive that limits how many coroutines can run a critical section at the same time.

**`asyncio.gather`**  
Runs multiple awaitables concurrently and collects their results.  
By default it fails fast; use `return_exceptions=True` if you want to continue on errors.

**Structured concurrency**  
Prefer patterns that make the lifetime of tasks clear and avoid "fire-and-forget" tasks that can be silently lost.

### Common Mistakes & Corrections

| Mistake | Why it was a problem | Correct approach |
|---------|----------------------|------------------|
| Wrong method/parameter names (`process_task`, `task_id`) | Confusing and error-prone | Use clear plural names: `process_tasks` + `task_ids` |
| Variable shadowing | Hard to read and easy to introduce bugs | Use different names for the list and the loop variable |
| Missing explicit error strategy | Unclear behavior on failure | Document whether you fail-fast or continue |

---

## Step 4 — Manual Test of the Async Method

### Goal
Verify that the concurrent processing works correctly before moving to FastAPI.

### Concrete Task
Create a temporary script (`test_async.py`) that:

1. Instantiates `TaskService`
2. Creates 6–10 tasks
3. Calls `await service.process_tasks(..., max_concurrent=3)`
4. Prints the results (id, status, timestamps, duration)

### What We Observed
- The first 3 tasks started at almost the same timestamp → semaphore correctly limited concurrency.
- As tasks finished, new ones started.
- All tasks reached `DONE` status successfully.

This confirmed that both the state transitions and the concurrency control are working.

---

## Step 5 — FastAPI Basics (Endpoints + Dependency Injection)

### Goal
Expose the domain and service layers over HTTP using FastAPI, with dependency injection providing the `TaskService` instance.

### Concrete Task
Create `taskforge/main.py` with:

- A FastAPI application
- Dependency injection to provide the `TaskService`
- A request schema (`TaskCreate`) — placed in `models.py` or a new `schemas.py`

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/tasks` | Create a new task |
| `GET` | `/tasks/{task_id}` | Get a single task |
| `GET` | `/tasks` | List tasks (optional `project_id` query param) |
| `POST` | `/tasks/{task_id}/start` | Start a task |
| `POST` | `/tasks/{task_id}/complete` | Complete a task |

### Requirements
- Return proper HTTP status codes:
  - `201` on creation
  - `404` when a task is not found
  - `400` for invalid state transitions

### Key Concepts Learned

**Dependency Injection with `Depends`**  
FastAPI's `Depends` lets you declare what a route needs (e.g. a `TaskService`) without instantiating it inside the route. This keeps handlers thin and makes testing easier.

**Request schemas vs domain models**  
`TaskCreate` describes what the client is allowed to send. It is intentionally narrower than the full `Task` domain model, which includes server-generated fields like `id`, `created_at`, and `status`.

**HTTP status codes as domain signals**  
Mapping domain outcomes to status codes (`404` for not found, `400` for invalid transitions) keeps the API predictable and RESTful.

### Common Mistakes & Corrections

| Mistake | Why it was a problem | Correct approach |
|---------|----------------------|------------------|
| Instantiating `TaskService` inside each route | Loses shared state; no single in-memory store | Use `Depends` with a module-level singleton or `lru_cache` provider |
| Reusing the domain `Task` model as the request body | Clients could set `id`, `created_at`, `status` | Create a dedicated `TaskCreate` schema |
| Returning raw exceptions instead of HTTP errors | Leaks internals; inconsistent responses | Raise `HTTPException` with appropriate status codes |
| Forgetting `201` for creation | Defaults to `200`, misleading clients | Pass `status_code=201` to the route decorator |
| Not validating `project_id` query param type | Accepts garbage input | Type it as `UUID | None` in the route signature |