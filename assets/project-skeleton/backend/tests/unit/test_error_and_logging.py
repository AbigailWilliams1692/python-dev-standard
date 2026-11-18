################################################################################
# @Project: ai-assistant
# @File Path: backend/tests/unit/test_error_and_logging.py
# @Description: Unit tests for the error envelope, masking and trace context
# @Creation Date: 2026-11-18
# @Last Update: 2026-11-18
################################################################################

################################################################################
# Import Libraries
################################################################################
# Standard Libraries
from __future__ import annotations

# Local Modules
from app.core.error_codes import ErrorCode
from app.core.errors import AppError, NotFoundError, ValidationError
from app.core.logging import (
    get_trace_id,
    new_trace_id,
    redact,
    reset_trace_id,
    set_trace_id,
)


################################################################################
# Module Functions
################################################################################
def test_http_status_is_derived_from_code() -> None:
    """
    The transport status must never be maintained separately.

    :return: ``None``, the assertions raise on failure.
    """
    assert NotFoundError("gone").http_status == 404
    assert ValidationError("bad").http_status == 400
    assert AppError("boom").http_status == 500


def test_error_payload_hides_detail() -> None:
    """
    Internal context stays in logs and never reaches the response body.

    :return: ``None``, the assertions raise on failure.
    """
    error = ValidationError("bad input", detail={"sql": "select 1"})
    payload = error.to_payload("trace-1")

    assert payload == {
        "code": int(ErrorCode.VALIDATION_FAILED),
        "message": "bad input",
        "data": None,
        "trace_id": "trace-1",
    }


def test_redact_masks_credentials_and_identifiers() -> None:
    """
    Secrets, phone numbers and email addresses are masked in log text.

    :return: ``None``, the assertions raise on failure.
    """
    raw = (
        "login password=hunter2 token=abc.def phone=13812345678 mail=alice@example.com"
    )
    masked = redact(raw)

    assert "hunter2" not in masked
    assert "abc.def" not in masked
    assert "13812345678" not in masked
    assert "alice@example.com" not in masked
    assert "password=***" in masked


def test_trace_id_is_restored_after_reset() -> None:
    """
    The context variable must not leak between requests on a reused task.

    :return: ``None``, the assertions raise on failure.
    """
    assert get_trace_id() == "-"

    token = set_trace_id(new_trace_id())
    assert get_trace_id() != "-"

    reset_trace_id(token)
    assert get_trace_id() == "-"
