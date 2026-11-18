################################################################################
# @Project: ai-assistant
# @File Path: backend/app/dependencies.py
# @Description: FastAPI dependency providers reading the app level container
# @Creation Date: 2026-11-18
# @Last Update: 2026-11-18
################################################################################

################################################################################
# Import Libraries
################################################################################
# Standard Libraries
from __future__ import annotations

from typing import Annotated

# Third-Party Libraries
from fastapi import Header, Request

# Local Modules
from app.container import Container
from app.core.config import AppEnvironment
from app.core.errors import AuthenticationError, InternalError
from app.modules.chat.service import ChatService

################################################################################
# Module Constants
################################################################################
# 开发环境免登身份，仅用于本地调试，生产环境必须带真实身份头
DEV_OWNER_ID: str = "dev-user"


################################################################################
# Module Functions
################################################################################
def get_container(request: Request) -> Container:
    """
    Return the container assembled when the application started.

    :param request: Request whose application holds the container.
    :return: Process wide container with settings and services.
    :raises InternalError: If the factory never attached a container.
    """
    # 用 getattr 读取动态挂载的属性，缺失时给出可定位的错误
    container = getattr(request.app.state, "container", None)
    if not isinstance(container, Container):
        raise InternalError("application container is not configured")
    return container


def get_chat_service(request: Request) -> ChatService:
    """
    Provide the chat service to the interface layer.

    :param request: Request whose application holds the container.
    :return: Configured chat service instance.
    """
    return get_container(request).chat_service


def get_current_user_id(
    request: Request,
    x_user_id: Annotated[str | None, Header(alias="X-User-Id")] = None,
) -> str:
    """
    Resolve the caller identity from the request.

    A real deployment replaces this provider with token introspection; the
    contract stays the same, which is the point of isolating it here.

    :param request: Request whose application holds the settings.
    :param x_user_id: Identity header forwarded by the gateway.
    :return: Non blank identity of the caller.
    :raises AuthenticationError: If no identity is available outside dev.
    """
    if x_user_id is not None and x_user_id.strip():
        return x_user_id.strip()

    # 开发环境允许匿名调用，测试与生产必须显式携带身份
    settings = get_container(request).settings
    if settings.app_env is AppEnvironment.DEV:
        return DEV_OWNER_ID
    raise AuthenticationError("X-User-Id header is required")
