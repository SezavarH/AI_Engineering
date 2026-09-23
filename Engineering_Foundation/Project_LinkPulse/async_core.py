import asyncio
import httpx


async def check_url(
    client: httpx.AsyncClient,
    url: str,
    semaphore: asyncio.Semaphore,
    timeout: float = 2.0,
) -> dict:
    """Return {"url": ..., "ok": bool, "status": int|None, "error": str|None}."""

    async with semaphore:
        try:
            resp = await client.get(url, timeout=timeout)
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


async def check_many_stream(urls, concurrency=5, per_url_timeout=2.0):
    semaphore = asyncio.Semaphore(concurrency)
    queue = asyncio.Queue()          # <-- mailbox

    async def worker(client, url):
        result = await check_url(client, url, semaphore, per_url_timeout)
        await queue.put(result)      # <-- drop result in mailbox

    async with httpx.AsyncClient() as client:
        async with asyncio.TaskGroup() as tg:
            for url in urls:
                tg.create_task(worker(client, url))   # start all workers

            # Meanwhile, pull results out as they appear
            for _ in range(len(urls)):
                result = await queue.get()            # <-- wait for next letter
                yield result                          # <-- hand it to the caller

if __name__ == "__main__":
    urls = [
        "https://example.com",
        "https://httpbin.org/status/404",
        "https://httpbin.org/delay/3",
        "https://this-domain-should-not-exist.invalid",
    ]
    results = asyncio.run(check_many(urls, concurrency=2, per_url_timeout=1.5))
    for r in results:
        print(r)