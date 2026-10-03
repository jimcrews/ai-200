from fastapi import FastAPI

from schemas import MessageRequest

# Create FastAPI app
app = FastAPI(
    title="Hello World API",
    description="A simple API to learn FastAPI fundamentals",
    version="1.0.0",
)


# Simple GET endpoint
@app.get("/")
async def root():
    return {"message": "Hello World"}


# POST with request body
@app.post("/echo")
async def echo(request: MessageRequest):
    """Echo your message back multiple times"""
    return {
        "original": request.message,
        "echoed": " ".join([request.message] * request.repeat_count),
    }


# Health check (introduction to probes)
@app.get("/health")
async def health():
    return {"status": "alive"}
