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