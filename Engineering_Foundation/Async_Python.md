
# Async

## What?
- Async programming lets your program **do other useful work** while **waiting** for slow things (network, disk I/O, timers…).

---

# Asyncio

## What?
- Python’s built-in library for writing concurrent code
- Uses the **async/await** syntax
- Runs on a **single thread** using an **Event Loop**

## Why?
- Threads are expensive and hard to debug (race conditions, locks)
- Processes are even heavier
- Async is lightweight → thousands of concurrent tasks can live on one thread

```python
import asyncio

async def say_hello():                      # coroutine
    print("Hello")
    await asyncio.sleep(1)                  # non-blocking sleep
    print("World")

async def main():
    await say_hello()

asyncio.run(main())                         # creates the event loop
```

## Notes
- `async def` creates a **coroutine** (not a normal function)
- `await` pauses the coroutine and gives control back to the event loop
- Always start with `asyncio.run(main())` — it creates the event loop for you

---

# Tasks – Running Coroutines Concurrently

## What?
- A **Task** is a coroutine that is scheduled to run on the event loop
- Creating a Task **starts it immediately**

## Why?
- Tasks let many coroutines run **“at the same time”**

## How to use?

```python
import asyncio

async def worker(name, delay):
    print(f"{name} started")
    await asyncio.sleep(delay)
    print(f"{name} finished")
    return f"{name} result"

async def main():
    t1 = asyncio.create_task(worker("A", 2))
    t2 = asyncio.create_task(worker("B", 1))

    result1 = await t1
    result2 = await t2

    print(result1, result2)

asyncio.run(main())
```

---

# gather

## What?
- Runs many awaitables concurrently and returns their results as a list (in the same order)

## Why?
- Cleaner than manually creating and awaiting many Tasks

## How to use?

```python
import asyncio

async def worker(name, delay):
    print(f"{name} started")
    await asyncio.sleep(delay)
    print(f"{name} finished")
    return f"{name} result"

async def main():
    results = await asyncio.gather(
        worker("A", 2),
        worker("B", 1),
        worker("C", 3)
    )
    print(results)

asyncio.run(main())
```

## Rule of thumb
- Use **gather** when you just want “run all of these and give me the answers”
- Use **manual create_task** when you need finer control (cancel one, wait for the first one that finishes, etc.)

> **Important behaviour**  
> By default `gather` is **fail-fast**: if one coroutine raises an exception, `gather` raises immediately (the other coroutines keep running in the background).  
> Use `return_exceptions=True` if you want all results (or the exceptions themselves).

---

# Semaphore

## What?
- Limits how many things can run at the same time
- Useful when you have 1000 tasks but only want 10 running concurrently (API rate limits, DB connections…)

## Why?
- Without a limit you can overwhelm the network, the remote server, or your own machine

## How to use?

```python
import asyncio

async def limited_worker(sem, name):
    async with sem:          # acquire → do work → release
        print(f"{name} got the slot")
        await asyncio.sleep(1)
        print(f"{name} released the slot")

async def main():
    sem = asyncio.Semaphore(3)   # only 3 at a time

    tasks = [limited_worker(sem, f"W{i}") for i in range(10)]
    await asyncio.gather(*tasks)

asyncio.run(main())
```

- Always use `async with sem:` — it is exception-safe

---

# Timeouts

## What?
- Cancel a coroutine if it takes longer than a given time

## Why?
- Network calls or external services can hang forever. Timeouts keep your program responsive.

## How to use?

```python
import asyncio

async def slow_operation():
    await asyncio.sleep(5)
    return "done"

async def main():
    try:
        result = await asyncio.wait_for(slow_operation(), timeout=2.0)
        print(result)
    except asyncio.TimeoutError:
        print("Timed out!")

asyncio.run(main())
```

**Python 3.11+ nicer version:**

```python
async with asyncio.timeout(2.0):
    result = await slow_operation()
```

---

# Conclusion – Quick Comparison Table

| Concept          | Purpose                                      | When to use                                      | Key behaviour                                      |
|------------------|----------------------------------------------|--------------------------------------------------|----------------------------------------------------|
| **One coroutine**    | Just run async code                      | Almost never (no concurrency benefit)            | Same speed as normal code                          |
| **Task**             | Start a coroutine immediately            | Need control over individual coroutines          | Starts right away, you await later                 |
| **gather**           | Run many + collect all results           | “Just run these and give me the answers”         | Fail-fast by default (`return_exceptions=True` to change) |
| **Semaphore**        | Limit concurrent execution               | Rate limiting, connection pools                  | Only N tasks run at the same time                  |
| **Timeout**          | Cancel if too slow                       | Network calls, external APIs                     | Raises `TimeoutError` and cancels the coroutine    |

**Golden rule**  
Start with `gather` + `Semaphore` + timeouts.  
Only drop down to manual `create_task` when you need more control.