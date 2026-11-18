################################################################################
# @Project: ai-assistant
# @File Path: backend/app/main.py
# @Description: Application factory wiring routers, middleware and handlers
# @Creation Date: 2026-11-18
# @Last Update: 2026-11-18
################################################################################

################################################################################
# Import Libraries
################################################################################
# Standard Libraries
from __future__ import annotations

import logging
from typing import Final

# Third-Party Libraries
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

# Local Modules
from app.container import build_container
from app.core.config import Settings, get_settings
from app.core.errors import AppError, InternalError, ValidationError
from app.core.health import router as health_router
from app.core.logging import configure_logging, get_trace_id
from app.core.middleware import trace_middleware
from app.modules.chat.router import router as chat_router

################################################################################
# Module Constants
################################################################################
API_VERSION: Final[str] = "0.1.0"
API_PREFIX: Final[str] = "/api/v1"

################################################################################
# Module Logger
################################################################################
logger = logging.getLogger(__name__)


################################################################################
# Module Functions
################################################################################
async def app_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Map a known application failure onto the shared error envelope.

    Unknown exception types are forwarded to the fallback handler so a defect
    never leaks a stack trace to the client.

    :param request: Request that triggered the failure.
    :param exc: Exception raised anywhere below the interface layer.
    :return: JSON response with the matching status and business code.
    """
    if not isinstance(exc, AppError):
        return await unhandled_error_handler(request, exc)

    # 可预期的业务失败记 WARNING，堆栈仅在需要时追加
    logger.warning(
        "application_error code=%s method=%s path=%s message=%s",
        int(exc.code),
        request.method,
        request.url.path,
        exc.message,
    )
    return JSONResponse(
        status_code=exc.http_status,
        content=exc.to_payload(get_trace_id()),
    )


async def validation_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Convert a request validation failure into the shared envelope.

    :param request: Request whose body or query failed validation.
    :param exc: Validation error raised by the framework.
    :return: JSON response with status 400 and the first failure located.
    """
    if not isinstance(exc, RequestValidationError):
        return await unhandled_error_handler(request, exc)

    # 只回传第一条错误的位置与原因，避免把整份 schema 暴露给调用方
    errors = exc.errors()
    if errors:
        first = errors[0]
        location = ".".join(str(part) for part in first.get("loc", ()))
        message = f"{location}: {first.get('msg', 'invalid request')}"
    else:
        message = "invalid request"

    logger.info(
        "request_validation_failed path=%s detail=%s",
        request.url.path,
        message,
    )
    failure = ValidationError(message, detail={"errors": errors})
    return JSONResponse(
        status_code=failure.http_status,
        content=failure.to_payload(get_trace_id()),
    )


async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Hide internal details behind a generic failure while logging the cause.

    :param request: Request that triggered the defect.
    :param exc: Unexpected exception, logged with its full stack.
    :return: JSON response with status 500 and no internal context.
    """
    # 堆栈只进日志，响应体永远不包含路径、SQL 或配置
    logger.error(
        "unhandled_error method=%s path=%s",
        request.method,
        request.url.path,
        exc_info=exc,
    )
    failure = InternalError("internal server error")
    return JSONResponse(
        status_code=failure.http_status,
        content=failure.to_payload(get_trace_id()),
    )


def create_app(settings: Settings | None = None) -> FastAPI:
    """
    Build the application from explicit settings or from the environment.

    Passing settings makes the factory usable in tests without touching the
    process environment, which is why configuration is a parameter here
    instead of a module level singleton.

    :param settings: Optional configuration, defaults to the environment.
    :return: Fully wired application instance.
    """
    resolved = settings if settings is not None else get_settings()
    configure_logging(level=resolved.log_level, json_output=resolved.log_json)

    # 容器只装配一次，请求期只做查表，不再构造依赖
    application = FastAPI(title=resolved.app_name, version=API_VERSION)
    application.state.container = build_container(resolved)

    # 中间件先装追踪，异常处理器随后接管业务失败
    application.middleware("http")(trace_middleware)
    application.add_exception_handler(AppError, app_error_handler)
    application.add_exception_handler(RequestValidationError, validation_error_handler)
    application.add_exception_handler(Exception, unhandled_error_handler)

    application.include_router(health_router)
    application.include_router(chat_router, prefix=API_PREFIX)
    logger.info(
        "application_ready env=%s version=%s",
        resolved.app_env.value,
        API_VERSION,
    )
    return application
