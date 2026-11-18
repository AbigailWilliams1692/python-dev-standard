################################################################################
# @Project: ai-assistant
# @File Path: backend/app/core/schemas.py
# @Description: Response envelope shared by every HTTP endpoint
# @Creation Date: 2026-11-18
# @Last Update: 2026-11-18
################################################################################

################################################################################
# Import Libraries
################################################################################
# Standard Libraries
from __future__ import annotations

from typing import Generic, TypeVar

# Third-Party Libraries
from pydantic import BaseModel

################################################################################
# Type Aliases
################################################################################
T = TypeVar("T")


################################################################################
# Module Classes
################################################################################
class Envelope(BaseModel, Generic[T]):
    """
    Wrap every successful response in one stable shape.

    A single envelope means the frontend writes one parser instead of one per
    endpoint, and ``trace_id`` lets a user report match a server log line.
    It lives in ``core`` rather than in a business domain because every domain
    returns it; placing it inside one module would force the others to import
    across domain boundaries.

    :param code: Business code, ``0`` on success.
    :param message: Short human readable status, ``ok`` on success.
    :param data: Payload of the endpoint, typed per route.
    :param trace_id: Correlation id echoed from the request.
    """

    code: int = 0
    message: str = "ok"
    data: T | None = None
    trace_id: str = ""
