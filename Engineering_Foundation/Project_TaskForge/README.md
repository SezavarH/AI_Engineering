## Step 1 — Domain Models  
*(Typing + Pydantic + Clean OOP Foundations)*

### Goal
Create a pure, well-typed domain model layer for TaskForge with no database, no FastAPI, and no asyncio.

### Concrete Task
Create `taskforge/models.py` containing:

- `User` (id, email, name, created_at)
- `Project` (id, name, owner_id, created_at)
- `Task` (id, project_id, title, description, status, priority, assignee_id, created_at, started_at, completed_at)

Requirements:
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
Perfect for cross-field validation rules (e.g. “if status is DONE then completed_at must exist”).

**UUID vs int for IDs**  
UUIDs are preferred for public-facing identifiers because they are collision-resistant and safer when systems grow or data is merged.

**Foreign keys must not have defaults**  
`owner_id` and `project_id` reference existing objects. Giving them `default_factory=uuid.uuid4` would silently create random unrelated IDs.

### Common Mistakes & Corrections (from our session)

| Mistake | Why it was a problem | Correct approach |
|---------|----------------------|------------------|
| Used `int` for IDs | Inconsistent and less safe | Use `uuid.UUID` everywhere |
| Used `str` for timestamps | Loses type safety and timezone info | Use `datetime` with `timezone.utc` |
| Gave foreign keys default UUIDs | Creates invalid relationships | Foreign keys are required, no default |
| Forgot defaults on some `created_at` fields | Inconsistent object creation | Always provide `Field(default_factory=...)` |
| Used old Pydantic v1 validator style | Does not work in Pydantic v2 | Use `@model_validator(mode="after")` |
| Didn’t know `@property` | Couldn’t add domain behavior | Learn that `@property` makes methods look like attributes |

### Final Design Decisions
- All models are Pydantic `BaseModel` (we will later introduce a clearer separation between domain objects and API schemas if needed)
- Status and priority are strict Enums
- Domain rules live inside the model (not in the service layer)
- Models remain pure (no I/O, no framework dependencies)