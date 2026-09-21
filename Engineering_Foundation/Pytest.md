# Test Pyramid

- The Test Pyramid is a strategy that says you should write many fast, focused unit tests at the bottom, fewer medium-speed integration tests in the middle, and only a small number of slow end-to-end tests at the top.

## Sub-concepts

- **Unit tests (the wide base)**. Test one small piece of code in isolation (a single function or class). They run in milliseconds and tell you exactly what broke.

- **Integration tests (the middle layer)**. Test how several pieces work together (for example, your API route + database + external service). They are slower but catch wiring problems.

- **End-to-end / UI tests (the tip)**. Test the whole system the way a real user would. Very slow, brittle, and expensive to maintain — use sparingly.

- **Why the shape matters**. Fast feedback is everything. If most of your tests are slow, developers stop running them and bugs slip through.

## Mind map

```text
Test Pyramid
├── Unit tests (wide base – fast & focused)
├── Integration tests (middle – real interactions)
├── End-to-end tests (tiny tip – full system)
└── Why the shape matters (speed + confidence)
```

# pytest

## Simple definition

- pytest is a popular Python testing framework that makes writing and running tests simple, readable, and powerful.

## Sub-concepts

- Test discovery. pytest automatically finds any file named test_*.py or *_test.py and any function starting with test_.

- Assertions. You just write normal Python assert statements. pytest gives clear failure messages.

- Fixtures. Reusable setup and teardown code (for example, creating a temporary database or a fake user). Declared with @pytest.fixture.

- Running tests. Simply type pytest in the terminal. You can filter by name, mark tests, run in parallel, etc.

- Plugins. Huge ecosystem (coverage, mocking helpers, async support, etc.).

## Code example

```python
# test_math.py

def add(a, b):
    return a + b

def test_add_pos_num():
    assert add(2, 3) == 5

def test_add_neg_num():
    assert add(-2, -3) == -5

# Run with: pytest
```

# Mock (Mocking)

## Simple definition

- Mocking means replacing a real object (database, API, file system, etc.) with a fake version that you control, 
- so you can test your code in isolation without depending on slow or unreliable external systems.

## Sub-concepts

- Why mock. Real dependencies are slow, flaky, expensive, or hard to set up in tests.
- What you can control. Return values, side effects, exceptions, call counts, and arguments received.
- unittest.mock (built into Python). The standard library tool. Mock, MagicMock, patch.
- pytest-mock plugin. Makes mocking even cleaner with a mocker fixture.
- When not to mock. Prefer real objects for integration tests; over-mocking can hide real bugs.

## Code example

```python
from unittest.mock import patch, MagicMock

def get_user_name(user_id, db):
    user = db.fetch(user_id)          # real DB call we want to avoid
    return user["name"]

def test_get_user_name():
    fake_db = MagicMock()                                               # fake db
    fake_db.fetch.return_value = {"name": "Alice"}                      # when ever a fetch called return this dict

    result = get_user_name(42, fake_db)                                 # call the db (fakedb) and use the fetch method

    assert result == "Alice"
    fake_db.fetch.assert_called_once_with(42)                           # ask Mock: did I call it only once?
```