from pydantic import BaseModel


# POST /echo request body
class MessageRequest(BaseModel):
    message: str
    repeat_count: int = 1
