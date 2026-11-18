################################################################################
# @Project: ai-assistant
# @File Path: backend/app/infrastructure/persistence/
#             in_memory_chat_repository.py
# @Description: In-process chat repository used for development and tests
# @Creation Date: 2026-11-18
# @Last Update: 2026-11-18
################################################################################

################################################################################
# Import Libraries
################################################################################
# Standard Libraries
from __future__ import annotations

import asyncio
from copy import deepcopy

# Local Modules
from app.core.errors import ConflictError, ValidationError
from app.modules.chat.domain import ChatSession, ChatSessionNotFoundError


################################################################################
# Module Classes
################################################################################
class InMemoryChatSessionRepository:
    """
    Keep sessions in process memory behind the repository port.

    Reads return deep copies, so a caller cannot mutate stored state through a
    stale reference. This store is deliberately minimal: no durability, no
    cross process coordination, no query language. It exists so the use cases
    can be exercised end to end without infrastructure.
    """

    ############################################################################
    # Constructor Method
    ############################################################################
    def __init__(self) -> None:
        """
        Create an empty store guarded by an asynchronous lock.
        """
        self._sessions: dict[str, ChatSession] = {}
        self._lock = asyncio.Lock()

    ############################################################################
    # Core Instance Methods
    ############################################################################
    async def add(self, session: ChatSession) -> None:
        """
        Store a newly created session.

        :param session: Aggregate to store, whose identifier must be unused.
        :raises ConflictError: If the identifier already exists.
        """
        async with self._lock:
            if session.session_id in self._sessions:
                raise ConflictError(
                    "chat session already exists",
                    detail={"session_id": session.session_id},
                )
            self._sessions[session.session_id] = deepcopy(session)

    async def get(self, session_id: str) -> ChatSession | None:
        """
        Load one session by identifier.

        :param session_id: Identifier of the session to load.
        :return: Detached copy of the aggregate, or ``None`` when absent.
        """
        async with self._lock:
            stored = self._sessions.get(session_id)
            return deepcopy(stored) if stored is not None else None

    async def save(self, session: ChatSession, *, expected_version: int) -> None:
        """
        Persist an existing session under optimistic concurrency control.

        :param session: Aggregate carrying the new state and the new version.
        :param expected_version: Version the caller read before mutating.
        :raises ChatSessionNotFoundError: If the session disappeared.
        :raises ConflictError: If the stored version no longer matches.
        """
        async with self._lock:
            stored = self._sessions.get(session.session_id)
            if stored is None:
                raise ChatSessionNotFoundError(
                    "chat session not found",
                    detail={"session_id": session.session_id},
                )

            # 版本不一致说明另一个请求已写入，宁可失败也不覆盖
            if stored.version != expected_version:
                raise ConflictError(
                    "chat session was modified concurrently",
                    detail={
                        "session_id": session.session_id,
                        "expected_version": expected_version,
                        "stored_version": stored.version,
                    },
                )
            self._sessions[session.session_id] = deepcopy(session)

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
        :param cursor: Offset encoded as decimal text, or ``None`` for page one.
        :return: Page of sessions and the cursor of the next page, if any.
        :raises ValidationError: If the cursor is not a decimal offset.
        """
        async with self._lock:
            offset = self._parse_cursor(cursor)
            owned = [
                item for item in self._sessions.values() if item.owner_id == owner_id
            ]

            # 按最近更新排序，与「最近会话」的产品语义一致
            owned.sort(key=lambda item: item.updated_at, reverse=True)
            page = owned[offset : offset + limit]
            next_cursor = str(offset + limit) if offset + limit < len(owned) else None
            return [deepcopy(item) for item in page], next_cursor

    ############################################################################
    # Helper Methods
    ############################################################################
    @staticmethod
    def _parse_cursor(cursor: str | None) -> int:
        """
        Convert an opaque page token into an offset.

        :param cursor: Token produced by a previous call, or ``None``.
        :return: Non negative offset into the ordered result set.
        :raises ValidationError: If the token is not a decimal offset.
        """
        if cursor is None:
            return 0
        try:
            offset = int(cursor)
        except ValueError as exc:
            raise ValidationError("cursor is not a valid page token") from exc
        if offset < 0:
            raise ValidationError("cursor must not be negative")
        return offset
