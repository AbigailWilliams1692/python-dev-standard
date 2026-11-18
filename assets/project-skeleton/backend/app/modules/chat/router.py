################################################################################
# @Project: ai-assistant
# @File Path: backend/app/modules/chat/router.py
# @Description: HTTP endpoints of the chat domain: sessions and messages
# @Creation Date: 2026-11-18
# @Last Update: 2026-11-18
################################################################################

################################################################################
# Import Libraries
################################################################################
# Standard Libraries
from __future__ import annotations

from typing import Annotated

# Third-Party Libraries
from fastapi import APIRouter, Depends, Query

# Local Modules
from app.core.logging import get_trace_id
from app.core.schemas import Envelope
from app.dependencies import get_chat_service, get_current_user_id
from app.modules.chat.schemas import (
    ChatSessionPage,
    ChatSessionView,
    CreateSessionRequest,
    SendMessageRequest,
)
from app.modules.chat.service import ChatService

################################################################################
# Module Constants
################################################################################
# 路由对象由 main 统一挂载；检查器已将该框架约定名加入白名单
router = APIRouter(prefix="/chat", tags=["chat"])


################################################################################
# Module Functions
################################################################################
@router.post("/sessions", status_code=201)
async def create_session(
    payload: CreateSessionRequest,
    service: Annotated[ChatService, Depends(get_chat_service)],
    owner_id: Annotated[str, Depends(get_current_user_id)],
) -> Envelope[ChatSessionView]:
    """
    Create an empty conversation owned by the caller.

    :param payload: Validated request body with the title and model.
    :param service: Chat service injected by the framework.
    :param owner_id: Identity resolved from the request.
    :return: Envelope carrying the created session.
    """
    session = await service.create_session(
        owner_id=owner_id,
        title=payload.title,
        model=payload.model,
    )
    return Envelope[ChatSessionView](
        data=ChatSessionView.from_domain(session),
        trace_id=get_trace_id(),
    )


@router.get("/sessions")
async def list_sessions(
    service: Annotated[ChatService, Depends(get_chat_service)],
    owner_id: Annotated[str, Depends(get_current_user_id)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    cursor: Annotated[str | None, Query(max_length=64)] = None,
) -> Envelope[ChatSessionPage]:
    """
    List the caller's sessions, newest first.

    :param service: Chat service injected by the framework.
    :param owner_id: Identity resolved from the request.
    :param limit: Requested page size, bounded by the query contract.
    :param cursor: Opaque continuation token from a previous page.
    :return: Envelope carrying one page of sessions.
    """
    sessions, next_cursor = await service.list_sessions(
        owner_id=owner_id,
        limit=limit,
        cursor=cursor,
    )
    page = ChatSessionPage(
        items=[ChatSessionView.from_domain(item) for item in sessions],
        next_cursor=next_cursor,
    )
    return Envelope[ChatSessionPage](data=page, trace_id=get_trace_id())


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: str,
    service: Annotated[ChatService, Depends(get_chat_service)],
    owner_id: Annotated[str, Depends(get_current_user_id)],
) -> Envelope[ChatSessionView]:
    """
    Return one session owned by the caller.

    :param session_id: Identifier of the requested session.
    :param service: Chat service injected by the framework.
    :param owner_id: Identity resolved from the request.
    :return: Envelope carrying the session and its turns.
    """
    session = await service.get_session(session_id=session_id, owner_id=owner_id)
    return Envelope[ChatSessionView](
        data=ChatSessionView.from_domain(session),
        trace_id=get_trace_id(),
    )


@router.post("/sessions/{session_id}/messages")
async def send_message(
    session_id: str,
    payload: SendMessageRequest,
    service: Annotated[ChatService, Depends(get_chat_service)],
    owner_id: Annotated[str, Depends(get_current_user_id)],
) -> Envelope[ChatSessionView]:
    """
    Append a user turn and return the session with the model reply.

    :param session_id: Identifier of the target session.
    :param payload: Validated request body carrying the message.
    :param service: Chat service injected by the framework.
    :param owner_id: Identity resolved from the request.
    :return: Envelope carrying the updated session.
    """
    session = await service.send_message(
        session_id=session_id,
        owner_id=owner_id,
        content=payload.content,
    )
    return Envelope[ChatSessionView](
        data=ChatSessionView.from_domain(session),
        trace_id=get_trace_id(),
    )
