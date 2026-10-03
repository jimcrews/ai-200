from fastapi import APIRouter

from openai_api.dependencies import SettingsDep

router = APIRouter()


@router.get("/health", tags=["health"])
async def health(settings: SettingsDep) -> dict[str, str]:
    return {"status": "ok", "environment": settings.environment}
