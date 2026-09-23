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

### Concepts

**What is SSE (Server-Sent Events)?**
A one-way streaming protocol over plain HTTP. The server keeps the connection open and pushes text chunks to the client. Each chunk is an **event**:

```
event: start
data: {"count": 3}

data: {"url": "https://example.com/", "ok": true, "status": 200, "error": null}

event: done
data: {}

```

**Rules of the format:**
- Each line is `field: value`.
- A **blank line** (`\n\n`) ends one event.
- `data:` is the payload; `event:` optionally names the event type.
- It's just text — `Content-Type: text/event-stream` is the only magic.

**What is an async generator?**
A function with `yield` instead of `return`, declared `async def`. It produces values **one at a time**, pausing between them. FastAPI's `StreamingResponse` consumes it, forwarding each yielded string to the client.

```python
async def event_stream():
    yield "data: hello\n\n"
    yield "data: world\n\n"
```

**What is `asyncio.TaskGroup`?**
A modern (Python 3.11+) context manager that runs a set of tasks together and guarantees cleanup:

```python
async with asyncio.TaskGroup() as tg:
    tg.create_task(worker(...))
    tg.create_task(worker(...))
# <- all tasks are done here
```

If any task raises, the rest are cancelled. If the block exits normally, every task has completed.

**What is `asyncio.Queue`?**
An async FIFO. Producers `await q.put(item)`; consumers `await q.get()`. Perfect for "workers push results, the generator pulls them out".

### The Pattern: Workers + Queue + TaskGroup

The generator needs to do two things **at the same time**:
1. Run N worker tasks (each calls `check_url`).
2. Yield results as they arrive.

The trick: spawn the workers inside a `TaskGroup`, have each push its result into a queue, and have the generator pull from the queue in a loop.

```python
async def check_many_stream(urls, concurrency=5, per_url_timeout=2.0):
    semaphore = asyncio.Semaphore(concurrency)
    queue: asyncio.Queue[dict] = asyncio.Queue()

    async def worker(client, url):
        result = await check_url(client, url, semaphore, per_url_timeout)
        await queue.put(result)          # push, don't return

    async with httpx.AsyncClient() as client:
        async with asyncio.TaskGroup() as tg:
            for url in urls:
                tg.create_task(worker(client, url))

            # Pull exactly len(urls) results out, yielding each.
            for _ in range(len(urls)):
                yield await queue.get()
        # TaskGroup waits here for all workers to finish.
```

**Why exactly `len(urls)` pulls?** Because we know how many results to expect. After that many, the loop ends, the `TaskGroup` block exits cleanly, and the generator returns.

**Why is yielding inside the `async with` OK?** The `TaskGroup` context stays open while we yield, keeping the workers alive.

**Ordering:** `queue.get()` returns results in completion order, not input order. That's the point of streaming — you want the fast ones first.

### The Generator Function (for `async_core.py`)

```python
async def check_many_stream(
    urls: list[str],
    concurrency: int = 5,
    per_url_timeout: float = 2.0,
):
    """
    Async generator yielding result dicts as they complete.
    Must yield every result exactly once, then finish.
    """
    semaphore = asyncio.Semaphore(concurrency)
    queue: asyncio.Queue[dict] = asyncio.Queue()

    async def worker(client: httpx.AsyncClient, url: str) -> None:
        result = await check_url(client, url, semaphore, per_url_timeout)
        await queue.put(result)

    async with httpx.AsyncClient() as client:
        async with asyncio.TaskGroup() as tg:
            for url in urls:
                tg.create_task(worker(client, url))

            for _ in range(len(urls)):
                yield await queue.get()
```

Key points, matching the requirements:
- ✅ **Shared `AsyncClient`** — one instance, used by all workers.
- ✅ **Reuses `check_url`** — no HTTP logic duplicated here.
- ✅ **`TaskGroup`** — one task per URL, joined on exit.
- ✅ **`asyncio.Queue`** — workers push, generator pulls.
- ✅ **Yields while tasks run** — first yield happens as soon as the first URL completes.
- ✅ **No blocking calls** — only `await` on async primitives.

### The Endpoint (for `app.py`)

Add imports:

```python
from fastapi.responses import StreamingResponse
import json

from async_core import check_many, check_many_stream
```

Then:

```python
@app.post("/check/stream")
async def check_urls_stream(
    payload: CheckRequest,
    config: CheckerConfig = Depends(get_checker_config),
):
    urls = [str(u) for u in payload.urls]

    async def event_stream():
        yield f'event: start\ndata: {{"count": {len(urls)}}}\n\n'

        async for result in check_many_stream(
            urls,
            concurrency=config.concurrency,
            per_url_timeout=config.per_url_timeout,
        ):
            yield f"data: {json.dumps(result)}\n\n"

        yield 'event: done\ndata: {}\n\n'

    return StreamingResponse(event_stream(), media_type="text/event-stream")
```

**Notes:**
- `StreamingResponse(gen, media_type="text/event-stream")` — the only thing that makes this SSE from FastAPI's side.
- The dependency `config` is unchanged — same DI pattern as `/check`.
- `json.dumps(result)` — the dict from `check_url` serializes to a one-line JSON object.
- The `start` / `done` named events let the client distinguish "connection opened" from "actual result" from "stream finished".

### ⚠️ Common Bug: Missing Type Annotation

This will **not** work:

```python
@app.post("/check/stream")
async def check_urls_stream(payload, config=Depends(get_checker_config)):
    ...
```

Without `: CheckRequest`, FastAPI treats `payload` as a **query parameter**, not a JSON body. Swagger will show it in the URL as `?payload=...`, and your requests will fail with **422 Unprocessable Entity**.

**Fix:** always annotate Pydantic model parameters.

```python
async def check_urls_stream(
    payload: CheckRequest,          # <-- THIS
    config: CheckerConfig = Depends(get_checker_config),
):
```

After the fix, reload `/docs`: the `payload` query field disappears and a JSON body editor appears instead.

### Testing SSE

**Swagger `/docs` cannot show live streaming.** Swagger buffers the entire response and displays it all at once. It's still useful to:

- Confirm the endpoint exists.
- Confirm request body validation (422 on bad input).
- See the **final** accumulated SSE text.

**To see actual streaming, use `curl -N`:**

```bash
curl -N -X POST http://127.0.0.1:8000/check/stream \
  -H "Content-Type: application/json" \
  -d '{"urls": ["https://example.com", "https://httpbin.org/delay/3", "https://httpbin.org/status/404"]}'
```

- `-N` disables curl's own buffering — without it, curl also waits for everything before printing.
- Watch the events appear **one at a time**, in completion order (fast URLs first, slow URLs last).

Expected flow:

```
(t=0.0s)  event: start
          data: {"count": 3}

(t=0.3s)  data: {"url": "https://example.com/", "ok": true, "status": 200, "error": null}

(t=0.4s)  data: {"url": "https://httpbin.org/status/404", "ok": false, "status": 404, "error": null}

(t=3.0s)  data: {"url": "https://httpbin.org/delay/3", "ok": false, "status": null, "error": "timeout"}

(t=3.0s)  event: done
          data: {}
```

**Browser test (optional):** save as `test_sse.html` and open in a browser.

```html
<!DOCTYPE html>
<html>
<body>
  <button onclick="start()">Start streaming</button>
  <pre id="out"></pre>
  <script>
    async function start() {
      const out = document.getElementById("out");
      out.textContent = "";
      const res = await fetch("http://127.0.0.1:8000/check/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          urls: ["https://example.com", "https://httpbin.org/delay/3"]
        })
      });
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        out.textContent += decoder.decode(value);
      }
    }
  </script>
</body>
</html>
```

If the browser blocks the request with a CORS error, temporarily add CORS to `app.py` (learning only):

```python
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"])
```

### Mental Model Cheat Sheet

| Piece | What it does |
|---|---|
| `text/event-stream` | The media type that makes it SSE. |
| `data: ...\n\n` | One event; blank line terminates it. |
| `event: name` | Optional named event for the client to distinguish. |
| `StreamingResponse(gen, ...)` | FastAPI wrapper that consumes an async generator and streams it. |
| `async def ... yield` | Async generator — produces values lazily, pausable. |
| `asyncio.TaskGroup` | Spawns tasks, joins them all on exit, cancels siblings on error. |
| `asyncio.Queue` | Producer/consumer handoff; `put` / `get` are async. |

### Exercises

1. **Watch the timing.** Add a `print(time.monotonic(), result["url"])` right before `yield`. Run with a mix of fast and slow URLs. Confirm results come out in completion order.
2. **Browser client.** Use `test_sse.html` above; watch chunks appear incrementally.
3. **What if a worker crashes?** Temporarily replace `check_url(...)` with `raise RuntimeError("boom")` inside `worker`. Does the client see an error? Does the stream close? *(Hint: `TaskGroup` propagates the exception, closing the stream.)*
4. **Why is yielding inside the `TaskGroup` block safe?** Explain in your own words.
5. **Add a progress event.** Every time you yield a result, also yield `event: progress\ndata: {"done": N, "total": M}\n\n`.

---

## Step 4 — Dockerize + Docker Compose

Coming next.

---

## Step 5 — GitHub Actions CI Pipeline

Coming next.