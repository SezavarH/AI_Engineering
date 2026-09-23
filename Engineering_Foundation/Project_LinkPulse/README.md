# LinkPulse

A small FastAPI service that accepts a list of URLs and checks them concurrently.

---

## Project Overview

**Core flow:**
```
POST /check with { "urls": [...] }
  → service fetches URLs concurrently with a concurrency limit and per-request timeout
  → returns JSON statuses
```

**Upgrades along the way:**
- Stream progress over SSE
- Containerize with Docker / Compose
- Add GitHub Actions CI

**Why this project fits the layers:**

| Layer | What you practice |
|---|---|
| Async Python | coroutines, `asyncio.gather`, `Semaphore`, timeouts, task lifecycle |
| FastAPI | request validation, dependency injection, background-friendly endpoints, SSE streaming |
| Docker | reproducible runtime, multi-stage image, Compose for local orchestration |
| CI/CD | lint → test → build image in GitHub Actions |

**Roadmap:**
1. **Async URL checker core** ← we start here
2. Wrap it in FastAPI with validation + dependency injection
3. Add SSE streaming progress endpoint
4. Dockerize + Docker Compose
5. GitHub Actions CI pipeline

---

## Step 1 — Async URL Checker Core

### Requirements

- Use **one shared** `httpx.AsyncClient` for all requests.
- Use `asyncio.Semaphore(concurrency)` to cap concurrent requests.
- Use `asyncio.wait_for(..., timeout)` or `httpx.Timeout` so slow URLs cannot hang the batch.
- Use `asyncio.gather(...)` to run all checks and collect results.
- Catch expected errors: timeout, DNS/connection errors, invalid URL, HTTP status errors if you treat 4xx/5xx as failures.
  - **Decision:** `ok = 200 <= status < 400`.
- Preserve input order in the returned list if possible; `gather` naturally helps with that.

### Concepts

**What is `async` / `await`?**
Normally, Python runs code line-by-line and **waits** for each operation to finish. When you fetch a URL, your program sits idle for ~200 ms doing nothing.

With `async`, Python can **pause** a task while waiting and run other tasks meanwhile. That's the whole point of `check_many` — while URL #1 is waiting for a response, URL #2 can start.

**What is a `Semaphore`?**
Think of it like a **bouncer at a club with N wristbands**. Only N tasks can be "inside" (making requests) at once. When one leaves, the next one enters.

```python
sem = asyncio.Semaphore(5)  # 5 wristbands
```

**What is `gather`?**
`asyncio.gather(*tasks)` runs all the tasks **concurrently** and returns their results **in the same order** you passed them in. That's why "preserve input order" is free.

**What is `httpx.AsyncClient`?**
It's like `requests`, but async. One client can be shared by all tasks (it manages a connection pool — more efficient than creating one per request).

### `check_url` — check ONE URL

```python
async def check_url(
    client: httpx.AsyncClient,
    url: str,
    semaphore: asyncio.Semaphore,
    timeout: float = 2.0,
) -> dict:
    """Return {"url": ..., "ok": bool, "status": int|None, "error": str|None}."""

    async with semaphore:
        try:
            resp = await asyncio.wait_for(client.get(url), timeout=timeout)
            status = resp.status_code
            return {
                "url": url,
                "ok": 200 <= status < 400,
                "status": status,
                "error": None,
            }
        except asyncio.TimeoutError:
            return {"url": url, "ok": False, "status": None, "error": "timeout"}
        except httpx.HTTPError as e:
            return {"url": url, "ok": False, "status": None, "error": str(e)}
        except Exception as e:
            return {"url": url, "ok": False, "status": None, "error": str(e)}
```

**Why `asyncio.wait_for`?**
It cancels the request if it takes too long. `httpx.Timeout` also works, but `wait_for` is a hard guarantee at the asyncio level.

```python
resp = await asyncio.wait_for(   # wrap with hard timeout
    client.get(url),
    timeout=timeout,
)
```

**Why `httpx.HTTPError`?**
That's the base exception class for httpx. DNS failure, connection refused, invalid URL, protocol errors — all inherit from it. So one `except` catches them all.

**Why return a dict instead of raising?**
Because `gather` by default propagates exceptions and kills the whole batch. We want one bad URL to not break the others.

### `check_many` — check MANY URLs concurrently

```python
async def check_many(
    urls: list[str],
    concurrency: int = 5,
    per_url_timeout: float = 2.0,
) -> list[dict]:
    """Fetch all URLs concurrently, but no more than `concurrency` at once."""

    semaphore = asyncio.Semaphore(concurrency)
    async with httpx.AsyncClient() as client:
        tasks = [check_url(client, u, semaphore, per_url_timeout) for u in urls]
        return await asyncio.gather(*tasks)
```

Key details:
- **One `AsyncClient`** for all requests → reuse connections, faster.
- **`async with`** ensures the client is closed cleanly.
- **`gather(*tasks)`** runs them all in parallel (but the semaphore limits how many are actively making requests).
- Results come back **in the same order** as `urls`.

---

## Step 2 — Wrap the Async Core in FastAPI

### Concepts

**What is FastAPI?**
A web framework. You define **routes** (URL + HTTP method) and their handler functions. FastAPI handles:

- Parsing the incoming JSON body
- Validating it against your schema
- Serializing your return value back to JSON
- Auto-generating OpenAPI docs at `/docs`

**What is Pydantic?**
A validation library. You describe the **shape** of your data with a class:

```python
class CheckRequest(BaseModel):
    urls: list[HttpUrl]
```

Pydantic then guarantees the body has a `urls` key, that it's a list, and that every item parses as a URL. If the client sends garbage, FastAPI automatically returns **422 Unprocessable Entity**.

**What is `HttpUrl`?**
A special Pydantic type. It's not `str` — it's a URL object. If parsing fails, validation fails. And `str()` conversion gives you the normalized URL back.

**What is Dependency Injection (`Depends`)?**
Instead of hard-coding config inside the endpoint, you declare **"I need a `CheckerConfig`"** and FastAPI calls a function that provides it:

```python
def get_checker_config() -> CheckerConfig:
    return CheckerConfig()

@app.post("/check")
async def check_urls(config: CheckerConfig = Depends(get_checker_config)):
    ...
```

Later you can swap the provider (env vars, test fakes) without touching the endpoint.

### Config + Models

```python
@dataclass(frozen=True)
class CheckerConfig:
    concurrency: int = 5
    per_url_timeout: float = 2.0
```
A tiny immutable config object. `frozen=True` means you can't mutate it after creation — safe to share.

```python
class CheckRequest(BaseModel):
    urls: list[HttpUrl] = Field(min_length=1, max_length=50)
```
- `list[HttpUrl]` → each element must be a valid URL.
- `Field(min_length=1, max_length=50)` → the list must have 1–50 items.

```python
class CheckResult(BaseModel):
    url: str
    ok: bool
    status: int | None = None
    error: str | None = None
```
The shape of each item in the response. Matches the dicts returned by `check_url` exactly.

### Endpoint

```python
@app.post("/check", response_model=list[CheckResult])
async def check_urls(
    payload: CheckRequest,
    config: CheckerConfig = Depends(get_checker_config),
):
    # HttpUrl -> str, because check_many works with plain strings
    urls = [str(u) for u in payload.urls]

    # Thin handler: delegate the real work to the async core
    results = await check_many(
        urls,
        concurrency=config.concurrency,
        per_url_timeout=config.per_url_timeout,
    )
    return results
```

**Why keep the endpoint thin?**
- Easy to test the core (`check_many`) without FastAPI.
- Easy to change the HTTP layer without touching logic.
- The same endpoint will later become an SSE stream in Step 3.

### Validation Behavior

`HttpUrl` normalizes URLs — `https://example.com` becomes `https://example.com/` in the response.

Invalid input (bad URL, empty list, more than 50 URLs) returns **422** with a body that pinpoints the failure:

```json
{
  "detail": [
    {
      "type": "url_parsing",
      "loc": ["body", "urls", 0],
      "msg": "Input should be a valid URL, relative URL without a base",
      "input": "not-a-url"
    }
  ]
}
```

That `loc` (`["body", "urls", 0]`) tells you *exactly* which item failed. That's Pydantic doing the work.

### Mental Model Cheat Sheet

| Piece | What it does |
|---|---|
| `FastAPI(title=...)` | Creates the app object. |
| `@app.post("/check")` | Registers a POST handler for `/check`. |
| `BaseModel` | Declares and validates a data shape. |
| `HttpUrl` | A validated URL type, not a string. |
| `Field(...)` | Adds constraints (min/max length, etc.). |
| `Depends(fn)` | "Call `fn` and give me its result." |
| `response_model=` | Serialize + filter the response; document it. |
| 422 | FastAPI's automatic validation error status. |

### Exercises

1. Add `"https://httpbin.org/delay/5"` to the request body. Does it take ~5 s or ~2 s? Why? *(Hint: `per_url_timeout=2.0` in the config.)*
2. Send 60 URLs. Confirm 422. Now change `max_length` to 100 and retry — what happens?
3. Add a new route `GET /health` returning `{"status": "ok"}`. What does `/docs` show?
4. Change `get_checker_config` to read `CONCURRENCY` from `os.environ`. Restart and verify `concurrency` takes effect.
5. Add a print of `payload` at the top of `check_urls`. What does FastAPI give you for `payload.urls[0]` — a `str` or an `HttpUrl`?

---

## Step 3 — Add SSE Streaming Progress Endpoint

Coming next: reuse `check_url` but yield each result as it finishes, over Server-Sent Events.

---

## Step 4 — Dockerize + Docker Compose

Coming next.

---

## Step 5 — GitHub Actions CI Pipeline

Coming next.