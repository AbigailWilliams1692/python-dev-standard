################################################################################
# @Project: ai-assistant
# @File Path: backend/app/modules/chat/service.py
# @Description: Chat use cases: ownership, turn limits and reply orchestration
# @Creation Date: 2026-11-18
# @Last Update: 2026-11-18
################################################################################

################################################################################
# Import Libraries
################################################################################
# Standard Libraries
from __future__ import annotations

import logging
import uuid
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Final

# Local Modules
from app.core.errors import ExternalServiceError, ValidationError
from app.modules.chat.domain import (
    ChatSession,
    ChatSessionNotFoundError,
    normalize_title,
    sanitize_content,
)
from app.modules.chat.ports import ChatSessionRepository, LlmPort

################################################################################
# Module Constants
################################################################################
# 单页上限与契约文档保持一致，防止调用方一次拉走整库
MAX_PAGE_SIZE: Final[int] = 100
MAX_MODEL_NAME_LENGTH: Final[int] = 64

################################################################################
# Module Logger
################################################################################
logger = logging.getLogger(__name__)


################################################################################
# Module Functions
################################################################################
def _utc_now() -> datetime:
    """
    Return the current instant as a timezone aware UTC datetime.

    :return: Current UTC timestamp.
    """
    return datetime.now(timezone.utc)


def _require_owner(owner_id: str) -> None:
    """
    Ensure a use case receives a usable caller identity.

    :param owner_id: Identity forwarded by the interface layer.
    :raises ValidationError: If the identity is blank.
    """
    if not owner_id.strip():
        raise ValidationError("owner_id must not be blank")


def _require_model(model: str) -> str:
    """
    Trim a model name and enforce its length bound.

    :param model: Model name supplied by the caller or by settings.
    :return: Trimmed model name ready for the adapter.
    :raises ValidationError: If the name is blank or too long.
    """
    cleaned = model.strip()
    if not cleaned:
        raise ValidationError("model must not be blank")
    if len(cleaned) > MAX_MODEL_NAME_LENGTH:
        raise ValidationError(f"model exceeds {MAX_MODEL_NAME_LENGTH} characters")
    return cleaned


################################################################################
# Module Classes
################################################################################
class ChatService:
    """
    Orchestrate the conversation use cases.

    The service owns the transaction like boundary (load, mutate, save), the
    ownership check and the turn limit. It never builds a query and never
    imports a vendor SDK: both arrive as ports, which is what keeps the layer
    testable without a database or a network.

    :param repository: Storage port used to load and persist aggregates.
    :param llm: Model port used to produce assistant replies.
    :param default_model: Model applied when the caller does not choose one.
    :param max_turns: Maximum number of user turns allowed per session.
    :param max_message_chars: Maximum accepted length of one message body.
    :param clock: Optional time source, injected by tests to freeze time.
    """

    ############################################################################
    # Constructor Method
    ############################################################################
    def __init__(
        self,
        repository: ChatSessionRepository,
        llm: LlmPort,
        *,
        default_model: str,
        max_turns: int,
        max_message_chars: int,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        """
        Store the injected ports and the policy limits.

        :param repository: Storage port used to load and persist aggregates.
        :param llm: Model port used to produce assistant replies.
        :param default_model: Model applied when the caller omits one.
        :param max_turns: Maximum number of user turns allowed per session.
        :param max_message_chars: Maximum accepted length of one message body.
        :param clock: Optional time source, defaults to the system UTC clock.
        """
        # 依赖全部由外部注入，构造函数内不申请任何资源
        self._repository = repository
        self._llm = llm
        self._default_model = _require_model(default_model)
        self._max_turns = max_turns
        self._max_message_chars = max_message_chars
        self._clock = clock if clock is not None else _utc_now

    ############################################################################
    # Core Instance Methods
    ############################################################################
    async def create_session(
        self,
        *,
        owner_id: str,
        title: str,
        model: str | None = None,
    ) -> ChatSession:
        """
        Create an empty session owned by the caller.

        :param owner_id: Identity forwarded by the interface layer.
        :param title: Display title supplied by the user.
        :param model: Optional model override, defaults to the configured one.
        :return: The persisted aggregate.
        :raises ValidationError: If the identity, title or model is invalid.
        """
        _require_owner(owner_id)
        now = self._clock()

        # 模型名与标题在进入聚合前先归一化，错误信息因此指向具体字段
        selected_model = model if model is not None else self._default_model
        resolved_model = _require_model(selected_model)
        session = ChatSession(
            session_id=uuid.uuid4().hex,
            owner_id=owner_id,
            title=normalize_title(title),
            model=resolved_model,
            created_at=now,
            updated_at=now,
        )
        await self._repository.add(session)
        logger.info(
            "chat_session_created session_id=%s owner_id=%s model=%s",
            session.session_id,
            owner_id,
            resolved_model,
        )
        return session

    async def list_sessions(
        self,
        *,
        owner_id: str,
        limit: int,
        cursor: str | None = None,
    ) -> tuple[list[ChatSession], str | None]:
        """
        List the caller's sessions, newest first.

        :param owner_id: Identity forwarded by the interface layer.
        :param limit: Requested page size, clamped to ``[1, MAX_PAGE_SIZE]``.
        :param cursor: Opaque continuation token from a previous page.
        :return: Page of sessions and the cursor of the next page, if any.
        :raises ValidationError: If the identity is blank.
        """
        _require_owner(owner_id)

        # 上限在服务层收口，避免越界分页拖垮存储
        bounded = max(1, min(limit, MAX_PAGE_SIZE))
        return await self._repository.list_by_owner(
            owner_id,
            limit=bounded,
            cursor=cursor,
        )

    async def get_session(self, *, session_id: str, owner_id: str) -> ChatSession:
        """
        Load one session after verifying that the caller owns it.

        A session owned by somebody else is reported exactly like a missing
        one, so the endpoint cannot be used to enumerate identifiers.

        :param session_id: Identifier of the requested session.
        :param owner_id: Identity forwarded by the interface layer.
        :return: The aggregate owned by the caller.
        :raises ChatSessionNotFoundError: If it is missing or owned by another user.
        """
        _require_owner(owner_id)
        session = await self._repository.get(session_id)
        if session is None:
            raise ChatSessionNotFoundError(
                "chat session not found",
                detail={"session_id": session_id},
            )

        # 归属校验失败按不存在处理，并在日志里留下审计线索
        if session.owner_id != owner_id:
            logger.warning(
                "chat_session_access_denied session_id=%s owner_id=%s",
                session_id,
                owner_id,
            )
            raise ChatSessionNotFoundError(
                "chat session not found",
                detail={"session_id": session_id},
            )
        return session

    async def send_message(
        self,
        *,
        session_id: str,
        owner_id: str,
        content: str,
    ) -> ChatSession:
        """
        Append a user turn, obtain a reply and persist both.

        The user turn is saved before the model is called: if the provider
        fails, the user's input is not lost and can be retried by the client.
        The assistant turn is saved only after a usable answer arrives.

        :param session_id: Identifier of the target session.
        :param owner_id: Identity forwarded by the interface layer.
        :param content: Raw message body supplied by the user.
        :return: The aggregate with both new turns applied.
        :raises ChatSessionNotFoundError: If the session is missing or foreign.
        :raises ChatTurnLimitExceededError: If the session is full.
        :raises ExternalServiceError: If the provider returns nothing usable.
        """
        session = await self.get_session(session_id=session_id, owner_id=owner_id)
        cleaned = sanitize_content(content, max_chars=self._max_message_chars)

        # 先落用户消息，供应商故障时输入不会丢
        session.add_user_message(
            cleaned,
            now=self._clock(),
            max_turns=self._max_turns,
        )
        await self._persist(session)

        # 模型调用不持有任何存储事务，避免长事务锁住会话
        completion = await self._llm.complete(session.messages, model=session.model)
        if not completion.text.strip():
            raise ExternalServiceError(
                "model returned an empty completion",
                detail={"session_id": session_id, "model": session.model},
            )

        logger.info(
            "llm_completion session_id=%s model=%s "
            "prompt_tokens=%s completion_tokens=%s",
            session_id,
            session.model,
            completion.prompt_tokens,
            completion.completion_tokens,
        )

        # 再落助手回复，保证历史里不出现没有回答的半个回合
        session.add_assistant_message(completion.text.strip(), now=self._clock())
        await self._persist(session)
        return session

    ############################################################################
    # Helper Methods
    ############################################################################
    async def _persist(self, session: ChatSession) -> None:
        """
        Save the aggregate while advancing its optimistic concurrency token.

        :param session: Aggregate whose in memory state must be persisted.
        :raises ConflictError: If another writer saved a newer version first.
        """
        expected = session.version
        session.version = expected + 1
        await self._repository.save(session, expected_version=expected)
