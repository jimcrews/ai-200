from fastapi import APIRouter

from fastapi_factory.models.schemas import MessageRequest, MessageResponse

router = APIRouter()


@router.post("/echo", tags=["echo"])
async def echo(request: MessageRequest) -> MessageResponse:
    """Echo your message back multiple times"""
    echoed_message = " ".join([request.message] * request.repeat_count)

    return MessageResponse(
        original=request.message,
        echoed=echoed_message,
        word_count=len(echoed_message.split()),
    )
