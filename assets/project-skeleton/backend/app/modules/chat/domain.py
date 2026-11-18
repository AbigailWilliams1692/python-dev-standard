################################################################################
# @Project: ai-assistant
# @File Path: backend/app/modules/chat/domain.py
# @Description: Conversation aggregate, value objects and domain invariants
# @Creation Date: 2026-11-18
# @Last Update: 2026-11-18
################################################################################

################################################################################
# Import Libraries
################################################################################
# Standard Libraries
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import ClassVar, Final

# Local Modules
from app.core.error_codes import ErrorCode
from app.core.errors import ConflictError, NotFoundError, ValidationError

################################################################################
# Module Constants
################################################################################
# 标题长度上限与数据库列宽保持一致，避免校验通过但落库失败
MAX_TITLE_LENGTH: Final[int] = 120


################################################################################
# Module Functions
################################################################################
def sanitize_content(content: str, *, max_chars: int) -> str:
    """
    Trim and validate one message body before it reaches the aggregate.

    :param content: Raw text supplied by the caller.
    :param max_chars: Hard upper bound enforced before any storage call.
    :return: Trimmed body that is safe to persist.
    :raises ValidationError: If the body is blank or longer than ``max_chars``.
    """
    # 去空白后再判空，避免只含空格的输入绕过校验
    cleaned = content.strip()
    if not cleaned:
        raise ValidationError("message content must not be blank")
    if len(cleaned) > max_chars:
        raise ValidationError(
            f"message content exceeds {max_chars} characters",
            detail={"length": len(cleaned), "max_chars": max_chars},
        )
    return cleaned


def normalize_title(title: str) -> str:
    """
    Trim a session title and enforce its length bound.

    :param title: Raw title supplied by the caller.
    :return: Trimmed title within :data:`MAX_TITLE_LENGTH` characters.
    :raises ValidationError: If the title is blank or too long.
    """
    cleaned = title.strip()
    if not cleaned:
        raise ValidationError("title must not be blank")
    if len(cleaned) > MAX_TITLE_LENGTH:
        raise ValidationError(f"title exceeds {MAX_TITLE_LENGTH} characters")
    return cleaned


def _require_text(value: str, field_name: str) -> None:
    """
    Ensure an identifier like field carries visible characters.

    :param value: Candidate value to inspect.
    :param field_name: Field name reported in the error message.
    :raises ValidationError: If the value is blank after trimming.
    """
    if not value.strip():
        raise ValidationError(f"{field_name} must not be blank")


def _require_aware(moment: datetime, field_name: str) -> None:
    """
    Reject naive timestamps, which silently mean local time on the server.

    :param moment: Timestamp to inspect.
    :param field_name: Field name reported in the error message.
    :raises ValidationError: If the timestamp carries no timezone.
    """
    if moment.tzinfo is None:
        raise ValidationError(f"{field_name} must be timezone aware")


################################################################################
# Module Classes
################################################################################
class ChatSessionNotFoundError(NotFoundError):
    """
    Report a session that does not exist or is not visible to the caller.

    Both cases share one error on purpose: distinguishing them would let a
    caller enumerate other users' session identifiers.
    """

    default_code: ClassVar[ErrorCode] = ErrorCode.CHAT_SESSION_NOT_FOUND


class ChatTurnLimitExceededError(ConflictError):
    """
    Report that a session has no room for another user turn.
    """

    default_code: ClassVar[ErrorCode] = ErrorCode.CHAT_TURN_LIMIT_EXCEEDED


class MessageRole(str, Enum):
    """
    Enumerate the author of a single conversation turn.

    Only user and assistant turns are stored; system prompts are assembled by
    the adapter so that a prompt change never rewrites stored history.
    """

    USER = "user"
    ASSISTANT = "assistant"


@dataclass(frozen=True, slots=True)
class ChatMessage:
    """
    Represent one immutable turn inside a session.

    :param role: Author of the message.
    :param content: Non blank body, already trimmed by the service.
    :param created_at: UTC timestamp of creation.
    """

    role: MessageRole
    content: str
    created_at: datetime

    def __post_init__(self) -> None:
        """
        Enforce the value object invariants.

        :raises ValidationError: If the body is blank or the clock is naive.
        """
        _require_text(self.content, "content")
        _require_aware(self.created_at, "created_at")


@dataclass(slots=True)
class ChatSession:
    """
    Act as the aggregate root of the conversation domain.

    Every state change goes through a method, so the invariants (usable title,
    bounded content, turn limit, monotonic timestamps) hold regardless of
    which layer triggered the change. The service never touches ``messages``
    directly.

    :param session_id: 32 character hexadecimal identifier assigned at creation.
    :param owner_id: Identity of the user who owns the session.
    :param title: Display title, trimmed and bounded by ``MAX_TITLE_LENGTH``.
    :param model: Model name applied to every completion of this session.
    :param created_at: UTC creation timestamp.
    :param updated_at: UTC timestamp of the last accepted change.
    :param messages: Ordered turns, oldest first.
    :param version: Optimistic concurrency token, bumped on every save.
    """

    session_id: str
    owner_id: str
    title: str
    model: str
    created_at: datetime
    updated_at: datetime
    messages: list[ChatMessage] = field(default_factory=list)
    version: int = 0

    ############################################################################
    # Constructor Method
    ############################################################################
    def __post_init__(self) -> None:
        """
        Validate the aggregate state immediately after construction.

        :raises ValidationError: If an identifier is blank, a timestamp is
            naive, or the update time precedes the creation time.
        """
        _require_text(self.session_id, "session_id")
        _require_text(self.owner_id, "owner_id")
        _require_text(self.model, "model")
        _require_aware(self.created_at, "created_at")
        _require_aware(self.updated_at, "updated_at")
        self.title = normalize_title(self.title)

        # 时间必须单调，否则排序分页会把新会话排到末尾
        if self.updated_at < self.created_at:
            raise ValidationError("updated_at must not precede created_at")

    ############################################################################
    # Utility Methods
    ############################################################################
    @property
    def user_turn_count(self) -> int:
        """
        Count the turns authored by the user.

        :return: Number of stored messages whose role is ``USER``.
        """
        return sum(1 for item in self.messages if item.role is MessageRole.USER)

    ############################################################################
    # Core Instance Methods
    ############################################################################
    def add_user_message(
        self,
        content: str,
        *,
        now: datetime,
        max_turns: int,
    ) -> ChatMessage:
        """
        Append a user turn after enforcing the conversation limit.

        :param content: Sanitised body, non blank.
        :param now: UTC timestamp of the accepted turn.
        :param max_turns: Maximum number of user turns allowed per session.
        :return: The message appended to the aggregate.
        :raises ChatTurnLimitExceededError: If the limit would be exceeded.
        """
        # 先判额度再追加，失败时聚合状态保持不变
        if self.user_turn_count >= max_turns:
            raise ChatTurnLimitExceededError(
                f"session reached the limit of {max_turns} user turns",
                detail={"session_id": self.session_id, "max_turns": max_turns},
            )
        return self._append(MessageRole.USER, content, now)

    def add_assistant_message(self, content: str, *, now: datetime) -> ChatMessage:
        """
        Append an assistant turn produced by the model adapter.

        :param content: Sanitised completion text, non blank.
        :param now: UTC timestamp of the accepted turn.
        :return: The message appended to the aggregate.
        """
        return self._append(MessageRole.ASSISTANT, content, now)

    def touch(self, now: datetime) -> None:
        """
        Record that the aggregate changed at the given instant.

        :param now: UTC timestamp of the change.
        :raises ValidationError: If ``now`` moves the clock backwards.
        """
        if now < self.updated_at:
            raise ValidationError("updated_at must not move backwards")
        self.updated_at = now

    ############################################################################
    # Helper Methods
    ############################################################################
    def _append(
        self,
        role: MessageRole,
        content: str,
        now: datetime,
    ) -> ChatMessage:
        """
        Create, store and timestamp one turn.

        :param role: Author of the new message.
        :param content: Sanitised body, non blank.
        :param now: UTC timestamp of the accepted turn.
        :return: The message that was appended.
        """
        message = ChatMessage(role=role, content=content, created_at=now)
        self.messages.append(message)
        self.touch(now)
        return message
