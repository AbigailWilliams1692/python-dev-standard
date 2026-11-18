################################################################################
# @Project: ai-assistant
# @File Path: backend/tests/unit/test_chat_domain.py
# @Description: Unit tests pinning the invariants of the chat aggregate
# @Creation Date: 2026-11-18
# @Last Update: 2026-11-18
################################################################################

################################################################################
# Import Libraries
################################################################################
# Standard Libraries
from __future__ import annotations

from datetime import datetime, timedelta, timezone

# Third-Party Libraries
import pytest

# Local Modules
from app.core.errors import ValidationError
from app.modules.chat.domain import (
    ChatMessage,
    ChatSession,
    ChatTurnLimitExceededError,
    MessageRole,
    sanitize_content,
)

################################################################################
# Module Constants
################################################################################
CREATED_AT = datetime(2026, 11, 18, 8, 0, tzinfo=timezone.utc)


################################################################################
# Module Functions
################################################################################
def _build_session(*, title: str = "First chat") -> ChatSession:
    """
    Build a valid session so each test only states its own deviation.

    :param title: Display title applied to the session.
    :return: Aggregate ready for mutation.
    """
    return ChatSession(
        session_id="a" * 32,
        owner_id="user-a",
        title=title,
        model="gpt-4o-mini",
        created_at=CREATED_AT,
        updated_at=CREATED_AT,
    )


def test_chat_message_rejects_blank_content() -> None:
    """
    A message made of spaces must never enter the aggregate.

    :return: ``None``, the assertion raises on failure.
    """
    with pytest.raises(ValidationError, match="content must not be blank"):
        ChatMessage(role=MessageRole.USER, content="   ", created_at=CREATED_AT)


def test_session_trims_title_on_construction() -> None:
    """
    Surrounding whitespace must not survive into stored state.

    :return: ``None``, the assertion raises on failure.
    """
    session = _build_session(title="  First chat  ")
    assert session.title == "First chat"


def test_session_rejects_naive_timestamps() -> None:
    """
    A naive timestamp means local server time and must be refused.

    :return: ``None``, the assertion raises on failure.
    """
    with pytest.raises(ValidationError, match="timezone aware"):
        ChatSession(
            session_id="a" * 32,
            owner_id="user-a",
            title="First chat",
            model="gpt-4o-mini",
            created_at=datetime(2026, 11, 18, 8, 0),
            updated_at=datetime(2026, 11, 18, 8, 0),
        )


def test_turn_limit_is_enforced_before_append() -> None:
    """
    Exceeding the limit raises and leaves the message list untouched.

    :return: ``None``, the assertions raise on failure.
    """
    session = _build_session()
    session.add_user_message("hello", now=CREATED_AT, max_turns=1)

    later = CREATED_AT + timedelta(seconds=1)
    with pytest.raises(ChatTurnLimitExceededError):
        session.add_user_message("again", now=later, max_turns=1)
    assert session.user_turn_count == 1


def test_sanitize_content_rejects_oversized_body() -> None:
    """
    The configured character bound is a hard limit, not a suggestion.

    :return: ``None``, the assertion raises on failure.
    """
    with pytest.raises(ValidationError, match="exceeds"):
        sanitize_content("x" * 11, max_chars=10)
