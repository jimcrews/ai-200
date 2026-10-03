from fastapi import APIRouter

from fastapi_factory.dependencies import SettingsDep

router = APIRouter()


@router.get("/", tags=["root"])
async def root(settings: SettingsDep) -> dict[str, str]:
    return {
        "welcome": f"Welcome to {settings.app_name} running in {settings.environment}!"
    }
