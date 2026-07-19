from fastapi import FastAPI, Depends
from pydantic import BaseModel

app = FastAPI()

# ----------------------- Validation ------------------------
class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str
    token_used: int

# ---------------------- Dependecy  -----------------------
def validate_msg(request: ChatRequest):

    if len(request.message) == 0:
        raise Exception("Message shouldn't be empty")

    if len(request.message) > 100:
        raise Exception("Message is too long")

    return {"message": request.message, "length": len(request.message)}


# --------------------------------------------------------
# FastAPI executes validate_msg() first.
# If validation succeeds, chat() is executed.


@app.post("/chat", response_model = ChatResponse)
def chat(
    request: ChatRequest,
    msg: dict = Depends(validate_msg)               # dependency
):

    print(msg["length"])   # استفاده از خروجی Dependency

    response = f"you said : {msg['message']}"

    return ChatResponse(
        reply=response,
        token_used=len(msg["message"].split())
    )