"""
This file defines the API endpoints for agent-related operations. The primary endpoint is `/run`,
which accepts a POST request with a JSON body containing a `prompt`. This endpoint processes the
prompt using the agent service, which interacts with the OpenAI client to generate a response.
The endpoint also includes error handling to manage cases where the agent architecture is down or
when there are issues communicating with the LLM engine.
"""

import logging

from fastapi import APIRouter, Request, Response, status
from openai import APIConnectionError, APIStatusError, AsyncOpenAI, RateLimitError

from openai_api.models.schemas import AgentRequest

logger = logging.getLogger("ai-agent")

router = APIRouter()


@router.post("/run")
async def run_agent_task(body: AgentRequest, response: Response, request: Request):
    """Execute prompt using AsyncOpenAI client attached to `app.state.openai_client`."""

    # This line of code demonstrates how to access the OpenAI client from the application state,
    # which was initialized during the startup phase in the lifespan context manager.
    client: AsyncOpenAI = getattr(request.app.state, "openai_client", None)

    settings = getattr(request.app.state, "settings", None)
    if client is None or settings is None:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {"error": "OpenAI client or settings not configured."}

    if not settings.llm_model_deployment_name:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "error": "Model deployment not configured. Set APP_LLM_MODEL_DEPLOYMENT_NAME."
        }

    try:
        completion = await client.chat.completions.create(
            model=settings.llm_model_deployment_name,
            messages=[
                {"role": "system", "content": "You are a compact Agent."},
                {"role": "user", "content": body.prompt},
            ],
        )

        return {
            "user_prompt": body.prompt,
            "agent_response": completion.choices[0].message.content,
        }

    except APIConnectionError as e:
        # Network failure or timeout reaching the LLM endpoint
        logger.error("Could not reach LLM engine: %s", e)
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"error": "Could not reach LLM engine.", "details": str(e)}

    except RateLimitError as e:
        logger.warning("LLM engine rate limit hit: %s", e)
        response.status_code = status.HTTP_429_TOO_MANY_REQUESTS
        return {"error": "LLM engine rate limit exceeded.", "details": str(e)}

    except APIStatusError as e:
        # Any other non-2xx response from the LLM endpoint (auth, bad request, 5xx, ...)
        logger.error("LLM engine returned %s: %s", e.status_code, e)
        response.status_code = status.HTTP_502_BAD_GATEWAY
        return {"error": "LLM engine returned an error.", "details": str(e)}
