"""
Pydantic models for request/response validation
"""

from pydantic import BaseModel


class MessageRequest(BaseModel):
    """Request model for echo endpoint"""

    message: str
    repeat_count: int = 1


class MessageResponse(BaseModel):
    """Response model for echo endpoint"""

    original: str
    echoed: str
    word_count: int
