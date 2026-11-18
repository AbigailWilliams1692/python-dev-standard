################################################################################
# @Project: ai-assistant
# @File Path: backend/app/infrastructure/llm/fake_adapter.py
# @Description: Deterministic offline adapter used by dev runs and test suites
# @Creation Date: 2026-11-18
# @Last Update: 2026-11-18
################################################################################

################################################################################
# Import Libraries
################################################################################
# Standard Libraries
from __future__ import annotations

from collections.abc import Sequence

# Local Modules
from app.core.errors import ExternalServiceError
from app.modules.chat.domain import ChatMessage, MessageRole
from app.modules.chat.ports import LlmCompletion


################################################################################
# Module Classes
################################################################################
class FakeLlmAdapter:
    """
    Produce deterministic replies without touching the network.

    Tests must never call a real model: it is slow, costs money and is not
    reproducible. This adapter is the default in development and test, and the
    only one exercised by the sample test suite.
    """

    ############################################################################
    # Constructor Method
    ############################################################################
    def __init__(self, *, prefix: str = "Echo:") -> None:
        """
        Store the prefix applied to every generated reply.

        :param prefix: Text prepended to the echoed user message.
        """
        self._prefix = prefix

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
        Echo the latest user turn so the flow stays observable.

        :param messages: Ordered history, oldest first, never empty.
        :param model: Model name requested by the session; the fake ignores it.
        :return: Deterministic completion with estimated token counts.
        :raises ExternalServiceError: If the history has no user turn.
        """
        # 取最后一条用户消息作为回显内容，符合真实模型的输入语义
        last_user = next(
            (item for item in reversed(messages) if item.role is MessageRole.USER),
            None,
        )
        if last_user is None:
            raise ExternalServiceError("conversation has no user turn")

        text = f"{self._prefix} {last_user.content}"
        prompt_tokens = sum(len(item.content.split()) for item in messages)
        return LlmCompletion(
            text=text,
            prompt_tokens=prompt_tokens,
            completion_tokens=len(text.split()),
        )
