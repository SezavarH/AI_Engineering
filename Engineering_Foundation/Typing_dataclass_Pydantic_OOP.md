# Typing (Type Hints), Dataclass, Pydantic & Composition — Notes

---

# Typing (Type Hints)

- Python is **dynamically typed**: types are determined at runtime
- Type hints are **optional annotations**
- They **do not enforce** anything at runtime (just for readability & tools)

---

# Dataclass

- Automatically generates `__init__`, `__repr__`, `__eq__`

### Old way (boilerplate)
```python
class User:
    def __init__(self, id: int, name: str):
        self.id = id
        self.name = name

    def __repr__(self):
        return f"User(id={self.id}, name={self.name})"

    def __eq__(self, other):
        if not isinstance(other, User):
            return NotImplemented
        return self.id == other.id and self.name == other.name
```

### With dataclass
```python
from dataclasses import dataclass

@dataclass
class User:
    id: int
    name: str
```

## Frozen and Slots

- `frozen=True` → **immutable** (cannot change fields after creation) + automatically hashable
- `slots=True` (Python 3.10+) → **less memory**, no `__dict__`

```python
@dataclass(frozen=True, slots=True)
class CacheKey:
    user_id: int
    resource: str
```

## Field

- A **field** is just a variable inside a dataclass
- It holds data for each object
- Think of a dataclass as a **form**, and each field is a **blank line** on that form

```python
@dataclass
class CacheKey:
    user_id: int      # <- field
    resource: str     # <- field
```

### `field()` — to customize a field
```python
from dataclasses import dataclass, field

@dataclass
class Person:
    name: str
    age: int
    hobbies: list = field(default_factory=list)
```

### Why `default_factory`?
- If you write `hobbies: list = []`, **all** persons would share the **same** list — a bug!
- `field(default_factory=list)` gives each person their **own** empty list.

---

# Pydantic

## What?
A tool that **checks and converts** your data automatically.

```python
from pydantic import BaseModel

class Person(BaseModel):
    name: str
    age: int

p = Person(name="Ahmad", age="29")   # ✅ works: "29" → 29
# p = Person(name="Ahmad", age="hello")  # ❌ Error: not a valid integer
```

## Why?
- Validates data
- Auto-converts types when possible
- Gives clear errors

## Pydantic vs Dataclass

| | `@dataclass` | Pydantic |
|---|---|---|
| Container | ✅ | ✅ |
| Validation | ❌ | ✅ |
| Type conversion | ❌ | ✅ |

---

## `field_validator`

- **Checking ONE box** on the form (e.g., name, age, …)
- Only looks at **one field** and asks: *"Is it okay?"*
- Must be a `@classmethod`

**Example:** check `age >= 18`
```python
from pydantic import BaseModel, field_validator

class GymMember(BaseModel):
    name: str
    age: int

    @field_validator("age")            # just one box: "is it okay?"
    @classmethod
    def check_age(cls, value):
        if value < 18:
            raise ValueError("Must be 18 or older")
        return value
```
It only cares about `age`. It doesn't know or care about `name`.

---

## `model_validator`

- **Checking the WHOLE form** (all boxes together)
- Operates on `self` (the whole model), not one field
- Must return `self`

**Example:** check that `password` and `confirm_pass` match
```python
from pydantic import BaseModel, model_validator

class SignUp(BaseModel):
    password: str
    confirm_pass: str

    @model_validator(mode="after")     # after all fields are validated, check whole form
    def check_passwords(self):
        if self.password != self.confirm_pass:
            raise ValueError("Passwords don't match")
        return self                    # must return self
```

### Quick comparison

| | `field_validator` | `model_validator` |
|---|---|---|
| Looks at | **One** field | **All** fields together |
| Says | "Is this field OK?" | "Do all fields fit together?" |

---

# Composition over Inheritance

- Instead of **"is-a"** (inheritance), use **"has-a"** (composition)

### Inheritance ("is-a")
```python
class Animal:
    def eat(self):
        pass

class Dog(Animal):     # Dog IS an Animal
    ...
```

### Composition ("has-a")
```python
class Engine:
    def start(self):
        print("Vroom")

class Car:
    def __init__(self):
        self.engine = Engine()   # Car HAS an Engine
```

**Why prefer composition?**
- More flexible — easy to swap parts
- Avoids deep, messy inheritance chains
- Easier to test and reuse

**Rule of thumb:** If you catch yourself thinking *"A is a B"*, but A only *uses* B's features → use composition.