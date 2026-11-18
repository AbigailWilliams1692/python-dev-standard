################################################################################
# @Project: ai-assistant
# @File Path: backend/tests/unit/test_chat_service.py
# @Description: Unit tests of the chat use cases with in-memory collaborators
# @Creation Date: 2026-11-18
# @Last Update: 2026-11-18
################################################################################

################################################################################
# Import Libraries
################################################################################
# Standard Libraries
from __future__ import annotations

from collections.abc import Sequence

# Third-Party Libraries
import pytest

# Local Modules
from app.core.errors import ConflictError, ExternalServiceError
from app.infrastructure.llm.fake_adapter import FakeLlmAdapter
from app.infrastructure.persistence.in_memory_chat_repository import (
    InMemoryChatSessionRepository,
)
from app.modules.chat.domain import (
    ChatMessage,
    ChatSessionNotFoundError,
    MessageRole,
)
from app.modules.chat.ports import LlmCompletion, LlmPort
from app.modules.chat.service import ChatService


################################################################################
# Module Functions
################################################################################
def _build_service(
    repository: InMemoryChatSessionRepository,
    llm: LlmPort | None = None,
) -> ChatService:
    """
    Assemble the service with deterministic collaborators.

    :param repository: Repository shared with the assertions of the test.
    :param llm: Optional model stub, defaults to the deterministic fake.
    :return: Service wired for a unit test.
    """
    return ChatService(
        repository,
        llm if llm is not None else FakeLlmAdapter(),
        default_model="gpt-4o-mini",
        max_turns=3,
        max_message_chars=100,
    )


async def test_send_message_appends_reply() -> None:
    """
    One send stores the user turn followed by the assistant turn.

    :return: ``None``, the assertions raise on failure.
    """
    repository = InMemoryChatSessionRepository()
    service = _build_service(repository)
    session = await service.create_session(owner_id="user-a", title="First chat")

    updated = await service.send_message(
        session_id=session.session_id,
        owner_id="user-a",
        content="  hello world  ",
    )

    roles = [item.role for item in updated.messages]
    assert roles == [MessageRole.USER, MessageRole.ASSISTANT]
    assert updated.messages[0].content == "hello world"
    assert updated.messages[1].content == "Echo: hello world"


async def test_failed_completion_keeps_user_turn() -> None:
    """
    A provider outage must not discard what the user already typed.

    :return: ``None``, the assertions raise on failure.
    """
    repository = InMemoryChatSessionRepository()
    service = _build_service(repository, _FailingLlm())
    session = await service.create_session(owner_id="user-a", title="First chat")

    with pytest.raises(ExternalServiceError):
        await service.send_message(
            session_id=session.session_id,
            owner_id="user-a",
            content="hello",
        )

    stored = await repository.get(session.session_id)
    assert stored is not None
    assert [item.role for item in stored.messages] == [MessageRole.USER]


async def test_foreign_session_is_reported_as_missing() -> None:
    """
    Another owner must not be able to tell an existing session from a ghost.

    :return: ``None``, the assertion raises on failure.
    """
    repository = InMemoryChatSessionRepository()
    service = _build_service(repository)
    session = await service.create_session(owner_id="user-a", title="First chat")

    with pytest.raises(ChatSessionNotFoundError):
        await service.get_session(session_id=session.session_id, owner_id="user-b")


async def test_stale_save_is_rejected() -> None:
    """
    Two writers reading the same version must not silently overwrite.

    :return: ``None``, the assertions raise on failure.
    """
    repository = InMemoryChatSessionRepository()
    service = _build_service(repository)
    session = await service.create_session(owner_id="user-a", title="First chat")

    first = await repository.get(session.session_id)
    second = await repository.get(session.session_id)
    assert first is not None
    assert second is not None

    first.version = 1
    await repository.save(first, expected_version=0)

    second.version = 1
    with pytest.raises(ConflictError):
        await repository.save(second, expected_version=0)


################################################################################
# Module Classes
################################################################################
class _FailingLlm:
    """
    Fail every completion so the test can inspect what was already persisted.
    """

    ############################################################################
    # Core Instance Methods
    ############################################################################
    async def complete(
        self,
        messages: Sequence[ChatMessage],
        *,
        model: str,
    ) -> LlmCompletion:
        """
        Raise instead of producing a reply.

        :param messages: Ordered history passed by the service.
        :param model: Model name passed by the service.
        :return: Never returns, the outage is always raised.
        :raises ExternalServiceError: Always, simulating a provider outage.
        """
        raise ExternalServiceError("upstream unavailable")
