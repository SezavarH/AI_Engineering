# FastAPI

## Simple definition

- FastAPI is a modern Python web framework 
- that lets you build fast, reliable APIs with very little code, automatic documentation, and built-in data checking.
- API: application programming interfaces — ways for programs to talk to each other over the internet 

- Automatic OpenAPI docs: 
    - FastAPI generates interactive Swagger UI and ReDoc pages so anyone can try the API without writing code.
- ASGI: 
    - Asynchronous Server Gateway Interface — the modern standard that lets FastAPI handle many requests at the same time efficiently (unlike the older WSGI used by Flask).

## code example

```python

from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def home():
    return {"message": "Welcome home"}

# Run: uvicorn main:app --reload
```

# REST

## Simple definition

- REST is a set of design rules for building web APIs 
- so that clients and servers can talk to each other in a simple, predictable, and scalable way using standard HTTP methods and resource-based URLs.

## Analogy

- REST is like a well-organized library: every book (resource) has a clear address (URL), you use standard actions (GET to read, POST to add, PUT to update, DELETE to remove), 
- and the librarian never remembers who you are between visits (stateless).

### Sub-concepts

- **Resources**. Everything is a noun (users, items, predictions). Each has a unique URL, e.g. /users/42.
- **HTTP methods as verbs.** GET = retrieve, POST = create, PUT/PATCH = update, DELETE = remove.
- **Stateless.** Every request contains all the information the server needs; the server does not keep client session data.
- **Representation.** Data is usually sent as JSON (a simple text format for structured data).
- **Uniform interface.** Clients only need to know the URLs and HTTP methods; no special protocols.

### Comparison / alternatives

- GraphQL: clients ask for exactly the fields they need in one request; more flexible but more complex.
- RPC / gRPC: procedure-call style (call a function remotely); faster for internal services but less human-readable.
- REST is the default for public web APIs because it is simple and cache-friendly.

## MindMap

```text
REST
├── Resources (nouns + URLs)
├── HTTP methods (verbs)
├── Stateless communication
├── JSON representations
└── vs GraphQL / gRPC
```

# Dependency Injection

## Simple definition

- Dependency Injection (DI) is a design pattern where an object receives the things it needs (its “dependencies”) 
- from the outside instead of creating them itself. 
- This makes code easier to test, reuse, and change.
- In FastAPI. FastAPI has a built-in DI system using the **Depends** function. You declare what you need; FastAPI creates and injects it for you (and can even cache it).

## Analogy

- Instead of a chef growing their own vegetables, raising their own chickens, and forging their own knives, 
- a kitchen manager hands the chef everything needed for the dish. The chef just cooks.

## Code example

```python
def create_login(username: str, password:str):
    return {"username":username, "password":password}

@app.get("/users/add")
def add_user(account=Depends(create_login)):
    return {"user": account}
```
# Validation

## Simple definition

- Validation is the process of checking that incoming data is the right shape, type, and content before your code tries to use it 
- catching bad data early so the rest of the system stays safe and predictable.

## Analogy

- Validation is the security guard at a concert who checks tickets, IDs, and bag size before letting anyone inside. 
- Without the guard, chaos (or security holes) happens later.

## Code example

```python
from fastapi import FastAPI
from pydantic import BaseModel, Field

class Item(BaseModel):
    name: str = Field(..., min_length= 1)       # required, non-empty
    price: float = Field(..., gt=0)             # must be > 0
    is_offer: bool = False

@app.post("/items/")
def create_item(item: Item):
    return{"message": "item created", "item":item}
```

## MindMap

```
Validation
├── Why we need it
├── Pydantic models
├── Automatic in FastAPI
├── Error responses (422)
└── Custom rules
```

# SSE (Server-Sent Events)

## Simple definition

- Server-Sent Events (SSE) is a simple web technology that lets a server push a continuous stream of text messages to a browser (or client) over a normal HTTP connection, without the client having to keep asking for updates.

## Analogy

- SSE is like a live radio station: the station (server) keeps broadcasting news; your radio (client) just stays tuned. 
- You don’t have to call the station every few seconds asking “anything new?”

## Sub-concepts

- One-way push. Server → client only.
- Built on HTTP. Uses a long-lived GET request with **Content-Type: text/event-stream.**
- Automatic reconnection. Browsers reconnect automatically if the connection drops.
- In FastAPI. You stream the special event format using StreamingResponse (or the higher-level EventSourceResponse from libraries).

## Code example

```python
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
import asyncio

app = FastAPI()

async def event_generator():
    for i in range(5):
        yield f"data: number {i}"
        await asyncio.sleep(1)

@app.get("/events")
async def sse_endpoint():
    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

## Comparison / alternatives

- WebSockets: two-way communication, more powerful, but more complex and heavier.
- Long polling: client keeps asking; wasteful and higher latency.
- SSE is the simplest choice when the server only needs to push updates (notifications, live scores, token streams).

```text
SSE
├── One-way server push
├── HTTP + text/event-stream
├── Simple message format
├── Auto-reconnect
└── vs WebSockets / long polling
```

# Conclusion

```text
FastAPI (the framework)
├── Built to make REST APIs easy
│   └── REST (the architectural style)
│       ├── Resources + HTTP methods
│       └── Stateless design
├── Dependency Injection (clean, testable code)
│   └── Depends() wires services into routes
├── Validation (safe data)
│   └── Pydantic models automatically check every request
├── Streaming (progressive responses)
│   └── StreamingResponse for large or live data
└── SSE (specialized streaming)
    └── text/event-stream on top of StreamingResponse
        └── Ideal for AI token streams & live updates
```
