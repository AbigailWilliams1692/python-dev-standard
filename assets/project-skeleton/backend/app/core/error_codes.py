################################################################################
# @Project: ai-assistant
# @File Path: backend/app/core/error_codes.py
# @Description: Stable business error codes shared by API, logs and frontend
# @Creation Date: 2026-11-18
# @Last Update: 2026-11-18
################################################################################

################################################################################
# Import Libraries
################################################################################
# Standard Libraries
from __future__ import annotations

from enum import IntEnum


################################################################################
# Module Classes
################################################################################
class ErrorCode(IntEnum):
    """
    Enumerate every business failure once, in a single importable place.

    The numeric value follows ``http_status * 100 + sequence`` so the transport
    status can be derived instead of maintained twice. ``40401`` therefore
    means the first business failure that maps to HTTP 404.

    Frontend code switches on these numbers, so a value must never be reused
    for a different meaning after release; add a new member instead.
    """

    ############################################################################
    # Class Attributes
    ############################################################################
    VALIDATION_FAILED = 40001
    AUTHENTICATION_REQUIRED = 40101
    PERMISSION_DENIED = 40301
    NOT_FOUND = 40400
    CHAT_SESSION_NOT_FOUND = 40401
    CONFLICT = 40900
    CHAT_TURN_LIMIT_EXCEEDED = 40901
    RATE_LIMITED = 42901
    INTERNAL_ERROR = 50001
    CONFIGURATION_INVALID = 50002
    UPSTREAM_UNAVAILABLE = 50201
