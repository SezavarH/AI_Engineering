from dataclasses import dataclass

from fastapi import Depends, FastAPI
from fastapi.responses import StreamingResponse

from pydantic import BaseModel, Field, HttpUrl

from async_core import check_many, check_many_stream
import json


app = FastAPI(title="LinkPulse")

# ---------- Config + Dependency ----------

## Requests as list of urls
class CheckRequest(BaseModel):
    urls: list[HttpUrl] = Field(min_length=1, max_length=50)

## Response in a proper format
class CheckResponse(BaseModel):
    url: str
    ok: bool
    status: int | None=None
    error: str | None = None

## Dependency to check urls
@dataclass(frozen=True)
class CheckUrlsDependency:
    concurrency: int = 5
    per_url_timeout: float = 2.0

def get_checker_config() -> CheckUrlsDependency:
    return CheckUrlsDependency()


# --------- Routes (endpoints) ----------
@app.post("/check", response_model=list[CheckResponse])
async def check_urls(request: CheckRequest, config: CheckUrlsDependency = Depends(get_checker_config)) -> list[CheckResponse]:

    urls = [str(u) for u in request.urls]

    return await check_many(
        urls,
        concurrency=config.concurrency,
        per_url_timeout=config.per_url_timeout,
    )

@app.post("/check/stream")
async def check_urls_stream(
    payload: CheckRequest,
    config: CheckUrlsDependency = Depends(get_checker_config),
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