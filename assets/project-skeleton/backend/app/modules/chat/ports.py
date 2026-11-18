################################################################################
# @Project: ai-assistant
# @File Path: backend/app/modules/chat/ports.py
# @Description: Ports the chat domain requires from storage and model vendors
# @Creation Date: 2026-11-18
# @Last Update: 2026-11-18
################################################################################

################################################################################
# Import Libraries
################################################################################
# Standard Libraries
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

# Local Modules
from app.modules.chat.domain import ChatMessage, ChatSession


################################################################################
# Module Classes
################################################################################
@dataclass(frozen=True, slots=True)
class LlmCompletion:
    """
    Carry one completion together with the usage needed for cost tracking.

    :param text: Generated answer, already stripped of vendor wrappers.
    :param prompt_tokens: Tokens billed for the request side.
    :param completion_tokens: Tokens billed for the response side.
    """

    text: str
    prompt_tokens: int
    completion_tokens: int


class LlmPort(Protocol):
    """
    Describe the model capability the application needs, not a vendor SDK.

    Business code depends on this protocol only, so switching vendor is a new
    adapter plus one factory line, and tests can inject a deterministic fake
    without touching the network.
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
        Produce one completion for the given conversation.

        :param messages: Ordered history, oldest first, never empty.
        :param model: Model name requested by the session.
        :return: Completion text together with token usage.
        :raises ExternalServiceError: If the provider fails after all retries.
        """
        ...


class ChatSessionRepository(Protocol):
    """
    Describe the persistence operations the chat service needs.

    Implementations translate between the aggregate and a concrete store. The
    protocol deliberately exposes no query builder, so business code cannot
    leak storage details upward.
    """

    ############################################################################
    # Core Instance Methods
    ############################################################################
    async def add(self, session: ChatSession) -> None:
        """
        Persist a newly created session.

        :param session: Aggregate to store, whose identifier must be unused.
        :raises ConflictError: If the identifier already exists.
        """
        ...

    async def get(self, session_id: str) -> ChatSession | None:
        """
        Load one session by identifier.

        :param session_id: Identifier of the session to load.
        :return: The stored aggregate, or ``None`` when it does not exist.
        """
        ...

    async def save(self, session: ChatSession, *, expected_version: int) -> None:
        """
        Persist an existing session under optimistic concurrency control.

        :param session: Aggregate carrying the new state and the new version.
        :param expected_version: Version the caller read before mutating.
        :raises ConflictError: If the stored version no longer matches.
        """
        ...

    async def list_by_owner(
        self,
        owner_id: str,
        *,
        limit: int,
        cursor: str | None,
    ) -> tuple[list[ChatSession], str | None]:
        """
        List sessions of one owner, newest first.

        :param owner_id: Identity whose sessions are requested.
        :param limit: Maximum number of sessions to return.
        :param cursor: Opaque continuation token from a previous page.
        :return: Page of sessions and the cursor of the next page, if any.
        """
        ...
