################################################################################
# @Project: ai-assistant
# @File Path: backend/app/core/middleware.py
# @Description: Request middleware binding a trace id and timing each call
# @Creation Date: 2026-11-18
# @Last Update: 2026-11-18
################################################################################

################################################################################
# Import Libraries
################################################################################
# Standard Libraries
from __future__ import annotations

import logging
import time

# Third-Party Libraries
from fastapi import Request, Response
from starlette.middleware.base import RequestResponseEndpoint

# Local Modules
from app.core.logging import TRACE_HEADER, new_trace_id, reset_trace_id, set_trace_id

################################################################################
# Module Logger
################################################################################
logger = logging.getLogger(__name__)


################################################################################
# Module Functions
################################################################################
async def trace_middleware(
    request: Request,
    call_next: RequestResponseEndpoint,
) -> Response:
    """
    Correlate one request with its logs and echo the id back to the caller.

    An inbound ``X-Trace-Id`` is trusted and reused so a gateway can stitch
    spans together; otherwise a fresh id is generated. The context variable is
    reset in ``finally`` so a reused worker thread cannot leak the id into an
    unrelated request.

    :param request: Inbound HTTP request being handled.
    :param call_next: Callback that runs the remaining middleware chain.
    :return: Response of the downstream handler with the trace header set.
    :raises Exception: Any error raised downstream is re-raised unchanged.
    """
    incoming = request.headers.get(TRACE_HEADER)
    trace_id = incoming if incoming else new_trace_id()
    token = set_trace_id(trace_id)
    started = time.perf_counter()

    try:
        response = await call_next(request)
    except Exception:
        # 异常也要记录耗时，否则最难排查的路径恰好没有数据
        elapsed_ms = (time.perf_counter() - started) * 1_000
        logger.exception(
            "http_request_failed method=%s path=%s duration_ms=%.1f",
            request.method,
            request.url.path,
            elapsed_ms,
        )
        raise
    else:
        elapsed_ms = (time.perf_counter() - started) * 1_000
        response.headers[TRACE_HEADER] = trace_id
        logger.info(
            "http_request method=%s path=%s status=%s duration_ms=%.1f",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
        )
        return response
    finally:
        reset_trace_id(token)
