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

# Step 4 — Docker + Docker Compose

**Goal:** make the app runnable anywhere with:

```bash
docker compose up --build
```

---

## Concepts

**Image vs container.** An image is a frozen filesystem + runtime recipe. A container is a running instance of that image. Build once, run many.

**Dockerfile.** A recipe to build an image. Read top to bottom; each `RUN`, `COPY`, `FROM` produces a layer.

**Multi-stage build.** Two `FROM` statements. Stage 1 (builder) installs dependencies into wheels. Stage 2 (final) copies only the wheels — no pip, no compilers, no cache. Keeps the final image small.

**`.dockerignore`.** Like `.gitignore` but for Docker. Prevents sending `.venv`, `__pycache__`, etc. into the image.

**Compose.** A YAML file describing what to run. `docker compose up` reads it and starts the services. Convenience for local dev, not production orchestration.

---

## Step 1 — Pin Dependencies

With the venv active:

```bash
pip freeze > requirements.txt
```

Pins every installed package and version so the Docker build installs exactly what you tested with.

---

## Step 2 — Environment-Driven Config

Update `get_checker_config` in `app.py` so the container can be configured without rebuilding:

```python
import os

@dataclass(frozen=True)
class CheckUrlsDependency:
    concurrency: int = 5
    per_url_timeout: float = 2.0


def get_checker_config() -> CheckUrlsDependency:
    return CheckUrlsDependency(
        concurrency=int(os.getenv("LINKPULSE_CONCURRENCY", "5")),
        per_url_timeout=float(os.getenv("LINKPULSE_TIMEOUT", "2.0")),
    )
```

Now the same image runs with different settings — change the env vars at run time.

---

## Step 3 — Dockerfile

Create a file named `Dockerfile` (no extension):

```dockerfile
# ---------- Stage 1: build wheels ----------
FROM python:3.12-slim AS builder

WORKDIR /app
COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt


# ---------- Stage 2: final runtime ----------
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY --from=builder /wheels /wheels
COPY requirements.txt .
RUN pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.txt \
    && rm -rf /wheels

RUN useradd --system --uid 10001 appuser

COPY app.py async_core.py ./

USER appuser
EXPOSE 8000

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Why these details matter:**

| Line | Reason |
|---|---|
| `AS builder` | Names the stage so a later `COPY --from=builder` can reference it. |
| `pip wheel ... /wheels` | Downloads and builds all dependencies into `.whl` files. |
| Second `FROM python:3.12-slim` | Starts a **fresh** image; nothing from stage 1 carries over unless copied. |
| `PYTHONUNBUFFERED=1` | Logs appear immediately in `docker logs`. |
| `PYTHONDONTWRITEBYTECODE=1` | No `.pyc` files inside the container. |
| `COPY --from=builder /wheels /wheels` | Brings only the wheels across. |
| `pip install --no-index --find-links=/wheels` | Installs from local wheels only — never hits PyPI. |
| `useradd ... appuser` + `USER appuser` | Container never runs as root. |
| `COPY app.py async_core.py ./` | Only the code we need. |
| `CMD [... "--host", "0.0.0.0" ...]` | Required — otherwise uvicorn binds to localhost inside the container and is unreachable from the host. |

**Why deps are copied before code:** Docker caches each layer. If only `app.py` changes, the deps layer stays cached, so rebuilds take seconds instead of minutes. Copy `requirements.txt` first, install, then copy code last.

---

## Step 4 — `.dockerignore`

Create `.dockerignore` next to the Dockerfile:

```
.venv
__pycache__
*.pyc
.git
*.md
.env
```

Keeps the build context small and prevents leaking local files.

---

## Step 5 — `docker-compose.yml`

Create `docker-compose.yml`:

```yaml
services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      LINKPULSE_CONCURRENCY: "5"
      LINKPULSE_TIMEOUT: "2.0"
```

| Line | Meaning |
|---|---|
| `services:` | Top-level key; one service called `app`. |
| `build: .` | Build the image from the current directory. |
| `ports: "8000:8000"` | Map host port 8000 → container port 8000. |
| `environment:` | Env vars passed into the container — these feed `os.getenv` in `get_checker_config`. |

Run:

```bash
docker compose up --build
```

Open **http://127.0.0.1:8000/docs**. Stop with `Ctrl+C` or `docker compose down` in another terminal.

---

## Mental Model Cheat Sheet

| Piece | What it does |
|---|---|
| `FROM` | Base image for a stage. |
| `WORKDIR` | Sets the working directory. |
| `COPY` | Copies files into the image. |
| `RUN` | Executes a shell command at build time. |
| `ENV` | Sets a permanent env var in the image. |
| `USER` | User the container runs as. |
| `CMD` | Command to run when the container starts. |
| `--from=builder` | Copy from a previous stage instead of the build context. |
| `docker compose up --build` | Build (if needed) and start all services. |
| `docker compose down` | Stop and remove containers. |

---

## Why This Sets Up Step 5

- CI will run the same `docker build` to verify the image still builds.
- Cache-friendly layering keeps CI fast.
- `LINKPULSE_*` env vars give CI a clean way to override config per environment.

---

# Step 5 — GitHub Actions CI Pipeline

Every push and PR runs **lint → test → build image** automatically on GitHub's servers. If anything fails, the PR shows a red ❌.

---

## Concepts

| Term | Meaning |
|---|---|
| **Workflow** | One YAML file describing a pipeline (lives in `.github/workflows/`). |
| **Trigger (`on:`)** | Events that start it (push, PR, manual). |
| **Job** | A unit of work. Runs on its own fresh VM. Jobs run **in parallel** by default. |
| **Step** | One command or action inside a job. Steps run **sequentially**. |
| **Runner** | The VM GitHub provides (`ubuntu-latest` by default). |
| **Action (`uses:`)** | A reusable step from the marketplace (e.g. `actions/checkout`). |
| **Matrix** | Run the same job with different configs (e.g. multiple Python versions). |

- **Lint** = read code without running it; flag style issues and common bugs. We use **ruff**.
- **Test** = run pytest against the FastAPI app in-process (no server). Real network calls are mocked so tests are fast and deterministic.
- **Build** = run the same `docker build` you ran locally. No image is pushed — CI is just verifying it builds.

---

## Step 1 — Add Test Dependencies

Append to `requirements.txt` (or a separate `requirements-dev.txt`):

```
pytest
pytest-asyncio
ruff
```

Install locally:

```bash
pip install pytest pytest-asyncio ruff
```

---

## Step 2 — Ruff Configuration

Create `ruff.toml` in the project root:

```toml
line-length = 100
target-version = "py312"

[lint]
select = ["E", "F", "I", "UP", "B"]
```

- `E` / `F` — pycodestyle + pyflakes (the classics)
- `I` — import sorting
- `UP` — pyupgrade (modernize syntax)
- `B` — bugbear (common mistakes)

Run locally before pushing:

```bash
ruff check .
ruff check . --fix     # auto-fix what's safe
```

---

## Step 3 — A Few Tests

Create `tests/test_app.py`. Tests run **in-process** via FastAPI's `TestClient` — no uvicorn needed, and `httpx.AsyncClient.get` is patched so no real network requests happen.

```python
from unittest.mock import AsyncMock, patch

import httpx
from fastapi.testclient import TestClient

from app import app

client = TestClient(app)


def _fake_response(url: str, status: int) -> httpx.Response:
    return httpx.Response(status_code=status, request=httpx.Request("GET", url))


@patch("httpx.AsyncClient.get", new_callable=AsyncMock)
def test_check_ok_and_fail(mock_get):
    async def side_effect(url, **kwargs):
        if url.endswith("ok"):
            return _fake_response(url, 200)
        return _fake_response(url, 404)

    mock_get.side_effect = side_effect

    resp = client.post("/check", json={"urls": ["https://example.com/ok", "https://example.com/bad"]})
    assert resp.status_code == 200
    body = resp.json()
    assert body[0]["ok"] is True
    assert body[0]["status"] == 200
    assert body[1]["ok"] is False
    assert body[1]["status"] == 404


def test_check_rejects_invalid_url():
    resp = client.post("/check", json={"urls": ["not-a-url"]})
    assert resp.status_code == 422


def test_check_rejects_empty_list():
    resp = client.post("/check", json={"urls": []})
    assert resp.status_code == 422
```

Run locally:

```bash
pytest -q
```

---

## Step 4 — The Workflow File

Create `.github/workflows/ci.yml`:

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip

      - name: Install ruff
        run: pip install ruff

      - name: Ruff check
        run: ruff check .

  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip

      - name: Install dependencies
        run: pip install -r requirements.txt pytest pytest-asyncio

      - name: Run tests
        run: pytest -q

  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Build Docker image
        run: docker build -t linkpulse:ci .
```

**Line-by-line:**

| Line | Meaning |
|---|---|
| `on: push: branches: [main]` | Run when someone pushes to `main`. |
| `on: pull_request:` | Also run on every PR from any branch. |
| `jobs:` | Three parallel jobs: `lint`, `test`, `build`. |
| `runs-on: ubuntu-latest` | GitHub gives each job a fresh Ubuntu VM. |
| `actions/checkout@v4` | Copies your repo into the VM. |
| `actions/setup-python@v5` + `cache: pip` | Installs Python; caches pip downloads between runs. |
| `ruff check .` | Fails the job (exit ≠ 0) on any lint issue. |
| `pytest -q` | Fails the job on any test failure. |
| `docker build -t linkpulse:ci .` | Verifies the Dockerfile still builds. Image is discarded. |

Jobs run in parallel, so total time = the slowest job, not the sum.

---

## Step 5 — Commit and Watch It Run

```bash
git add .github requirements.txt ruff.toml tests/
git commit -m "Add CI: lint, test, docker build"
git push
```

On GitHub → **Actions** tab → click the latest run → see the three jobs start in parallel with live logs. First run is slower (cold cache); subsequent runs are fast thanks to pip caching.

---

## Common Gotchas

- **Tests pass locally but fail in CI** → something is in your venv but not in `requirements.txt`. CI installs only what's listed.
- **`ruff check` fails on line length** → tune `line-length` in `ruff.toml` or wrap the lines.
- **Docker build slow in CI** → normal on first run. Later, switch to `docker/build-push-action` with `cache-from`/`cache-to`.
- **`pytest` can't find `app`** → run pytest from the repo root. If needed, add `pythonpath = .` to `pytest.ini`.
- **Workflow doesn't trigger** → verify the file is at exactly `.github/workflows/ci.yml`. YAML is whitespace-sensitive (2 spaces, no tabs).

---

## Mental Model Cheat Sheet

| Piece | What it does |
|---|---|
| `.github/workflows/ci.yml` | Where GitHub looks for pipelines. |
| `on:` | Events that trigger the workflow. |
| `jobs:` | Parallel units of work; each on its own VM. |
| `steps:` | Sequential commands inside one job. |
| `uses:` | Pull in a published action. |
| `run:` | Run a shell command. |
| `actions/checkout@v4` | Clone the repo into the runner. |
| `actions/setup-python@v5` | Install Python + cache pip. |
| Exit code ≠ 0 | Marks the step (and job) as failed. |

---

## What You Have Now

- ✅ Async core (`async_core.py`) — concurrent URL checking
- ✅ FastAPI layer (`app.py`) — `/check` + `/check/stream` with validation & DI
- ✅ SSE streaming — results arrive as they finish
- ✅ Docker + Compose — `docker compose up --build` runs anywhere
- ✅ GitHub Actions CI — every push/PR runs lint, tests, and a Docker build
