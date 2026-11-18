################################################################################
# @Project: ai-assistant
# @File Path: backend/app/core/errors.py
# @Description: Application error hierarchy mapped to HTTP status and envelope
# @Creation Date: 2026-11-18
# @Last Update: 2026-11-18
################################################################################

################################################################################
# Import Libraries
################################################################################
# Standard Libraries
from __future__ import annotations

from collections.abc import Mapping
from typing import Any, ClassVar

# Local Modules
from app.core.error_codes import ErrorCode


################################################################################
# Module Classes
################################################################################
class AppError(Exception):
    """
    Serve as the single base class for every expected application failure.

    Subclasses only declare :attr:`default_code`. The HTTP status is derived
    from that code, so a business code and a transport status can never drift
    apart. Anything raised outside this hierarchy is treated as a defect and
    reported as ``InternalError`` by the interface layer.

    :param message: Description safe to return to the caller.
    :param code: Override for the class level default business code.
    :param detail: Structured context for logs, never returned verbatim.
    :ivar message: Description passed to the constructor.
    :ivar code: Effective business code of this instance.
    :ivar detail: Structured context attached at raise time.
    """

    ############################################################################
    # Class Attributes
    ############################################################################
    default_code: ClassVar[ErrorCode] = ErrorCode.INTERNAL_ERROR

    ############################################################################
    # Constructor Method
    ############################################################################
    def __init__(
        self,
        message: str,
        *,
        code: ErrorCode | None = None,
        detail: Mapping[str, Any] | None = None,
    ) -> None:
        """
        Store the description, the effective code and the structured context.

        :param message: Description safe to return to the caller.
        :param code: Override for the class level default business code.
        :param detail: Structured context for logs, never returned verbatim.
        """
        super().__init__(message)
        self.message = message
        self.code = code if code is not None else self.default_code
        self.detail: dict[str, Any] = dict(detail or {})

    ############################################################################
    # Utility Methods
    ############################################################################
    @property
    def http_status(self) -> int:
        """
        Derive the transport status from the business code.

        :return: Status encoded in the three leading digits of ``code``.
        """
        return int(self.code) // 100

    ############################################################################
    # Serialization Methods
    ############################################################################
    def to_payload(self, trace_id: str) -> dict[str, Any]:
        """
        Build the error envelope returned to the client.

        ``detail`` stays out of the payload on purpose: it may contain internal
        identifiers that help an attacker enumerate resources.

        :param trace_id: Correlation id of the current request.
        :return: Serialisable envelope carrying only public information.
        """
        return {
            "code": int(self.code),
            "message": self.message,
            "data": None,
            "trace_id": trace_id,
        }


class ValidationError(AppError):
    """
    Report caller input that violates a documented constraint.
    """

    default_code: ClassVar[ErrorCode] = ErrorCode.VALIDATION_FAILED


class AuthenticationError(AppError):
    """
    Report a request that carries no usable identity.
    """

    default_code: ClassVar[ErrorCode] = ErrorCode.AUTHENTICATION_REQUIRED


class PermissionDeniedError(AppError):
    """
    Report a caller that is known but not allowed to touch the resource.
    """

    default_code: ClassVar[ErrorCode] = ErrorCode.PERMISSION_DENIED


class NotFoundError(AppError):
    """
    Report a resource that does not exist for the current caller.
    """

    default_code: ClassVar[ErrorCode] = ErrorCode.NOT_FOUND


class ConflictError(AppError):
    """
    Report a state conflict such as a concurrent modification.
    """

    default_code: ClassVar[ErrorCode] = ErrorCode.CONFLICT


class RateLimitError(AppError):
    """
    Report that the caller exceeded an enforced quota.
    """

    default_code: ClassVar[ErrorCode] = ErrorCode.RATE_LIMITED


class ExternalServiceError(AppError):
    """
    Report a downstream failure the caller cannot fix by retrying blindly.
    """

    default_code: ClassVar[ErrorCode] = ErrorCode.UPSTREAM_UNAVAILABLE


class InternalError(AppError):
    """
    Report an unexpected defect that needs human investigation.
    """

    default_code: ClassVar[ErrorCode] = ErrorCode.INTERNAL_ERROR


class ConfigurationError(AppError):
    """
    Report an invalid runtime configuration detected at startup.
    """

    default_code: ClassVar[ErrorCode] = ErrorCode.CONFIGURATION_INVALID
