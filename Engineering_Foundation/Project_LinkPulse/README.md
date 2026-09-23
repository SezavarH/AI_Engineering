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