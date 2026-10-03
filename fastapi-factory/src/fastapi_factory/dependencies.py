from typing import Annotated

from fastapi import Depends, Request

from fastapi_factory.config import Settings


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


SettingsDep = Annotated[Settings, Depends(get_settings)]
