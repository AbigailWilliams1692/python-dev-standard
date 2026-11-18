################################################################################
# @Project: ai-assistant
# @File Path: backend/app/modules/chat/schemas.py
# @Description: Request and response contracts of the chat HTTP interface
# @Creation Date: 2026-11-18
# @Last Update: 2026-11-18
################################################################################

################################################################################
# Import Libraries
################################################################################
# Standard Libraries
from __future__ import annotations

from datetime import datetime

# Third-Party Libraries
from pydantic import BaseModel, ConfigDict, Field, field_validator

# Local Modules
from app.modules.chat.domain import ChatSession, MessageRole

################################################################################
# Module Constants
################################################################################
# 请求体绝对上限，真正的业务上限由 Settings 决定并在服务层收口
ABSOLUTE_MESSAGE_LIMIT: int = 100_000


################################################################################
# Module Classes
################################################################################
class ChatMessageView(BaseModel):
    """
    Represent one conversation turn as returned to the client.

    :param role: Author of the message.
    :param content: Message body.
    :param created_at: UTC creation timestamp.
    """

    model_config = ConfigDict(frozen=True)

    role: MessageRole
    content: str
    created_at: datetime


class ChatSessionView(BaseModel):
    """
    Represent a session and its turns as returned to the client.

    :param session_id: Identifier of the session.
    :param title: Display title.
    :param model: Model applied to the session.
    :param messages: Ordered turns, oldest first.
    :param created_at: UTC creation timestamp.
    :param updated_at: UTC timestamp of the last change.
    """

    model_config = ConfigDict(frozen=True)

    session_id: str
    title: str
    model: str
    messages: list[ChatMessageView]
    created_at: datetime
    updated_at: datetime

    ############################################################################
    # Serialization Methods
    ############################################################################
    @classmethod
    def from_domain(cls, session: ChatSession) -> ChatSessionView:
        """
        Convert an aggregate into its transport representation.

        The mapping is explicit rather than attribute based so that adding a
        domain field never leaks it to the API by accident.

        :param session: Aggregate to convert.
        :return: Detached view safe to serialise.
        """
        return cls(
            session_id=session.session_id,
            title=session.title,
            model=session.model,
            messages=[
                ChatMessageView(
                    role=item.role,
                    content=item.content,
                    created_at=item.created_at,
                )
                for item in session.messages
            ],
            created_at=session.created_at,
            updated_at=session.updated_at,
        )


class ChatSessionPage(BaseModel):
    """
    Represent one page of sessions.

    :param items: Sessions of the current page, newest first.
    :param next_cursor: Token for the next page, ``None`` on the last page.
    """

    items: list[ChatSessionView]
    next_cursor: str | None = None


class CreateSessionRequest(BaseModel):
    """
    Describe the body accepted when creating a session.

    :param title: Display title, trimmed by the validator below.
    :param model: Optional model override for this session.
    """

    title: str = Field(min_length=1, max_length=120)
    model: str | None = Field(default=None, max_length=64)

    ############################################################################
    # Validation Methods
    ############################################################################
    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str) -> str:
        """
        Trim surrounding whitespace and reject blank titles.

        :param value: Raw title supplied by the client.
        :return: Trimmed title.
        :raises ValueError: If the title is empty after trimming.
        """
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("title must not be blank")
        return cleaned


class SendMessageRequest(BaseModel):
    """
    Describe the body accepted when sending a message.

    The bound here is an absolute guard against oversized payloads; the
    effective limit comes from settings and is enforced by the service, so a
    configuration change never requires a schema change.

    :param content: Message body, trimmed by the service before storage.
    """

    content: str = Field(min_length=1, max_length=ABSOLUTE_MESSAGE_LIMIT)
