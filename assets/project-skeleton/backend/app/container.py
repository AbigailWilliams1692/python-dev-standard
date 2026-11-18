################################################################################
# @Project: ai-assistant
# @File Path: backend/app/container.py
# @Description: Assemble ports and services once per process at startup
# @Creation Date: 2026-11-18
# @Last Update: 2026-11-18
################################################################################

################################################################################
# Import Libraries
################################################################################
# Standard Libraries
from __future__ import annotations

from dataclasses import dataclass

# Local Modules
from app.core.config import LlmProvider, Settings
from app.infrastructure.llm.fake_adapter import FakeLlmAdapter
from app.infrastructure.llm.openai_adapter import OpenAiAdapter
from app.infrastructure.persistence.in_memory_chat_repository import (
    InMemoryChatSessionRepository,
)
from app.modules.chat.ports import LlmPort
from app.modules.chat.service import ChatService


################################################################################
# Module Functions
################################################################################
def build_container(settings: Settings) -> Container:
    """
    Wire adapters into services for one process lifetime.

    This is the only place that knows which concrete adapter is active. Every
    other module receives a port, so swapping storage or vendor never touches
    business code.

    :param settings: Validated configuration of the running process.
    :return: Container holding the singletons shared by all requests.
    """
    repository = InMemoryChatSessionRepository()
    service = ChatService(
        repository,
        _build_llm(settings),
        default_model=settings.chat_default_model,
        max_turns=settings.chat_max_turns,
        max_message_chars=settings.chat_max_message_chars,
    )
    return Container(settings=settings, chat_service=service)


def _build_llm(settings: Settings) -> LlmPort:
    """
    Select the model adapter requested by configuration.

    :param settings: Validated configuration of the running process.
    :return: Adapter implementing the language model port.
    :raises ConfigurationError: If the selected provider lacks credentials.
    """
    # 工厂是唯一允许出现供应商分支的地方，业务代码不得复制这段判断
    if settings.llm_provider is LlmProvider.FAKE:
        return FakeLlmAdapter()
    return OpenAiAdapter(
        api_key=settings.llm_api_key.get_secret_value(),
        base_url=settings.llm_base_url,
        timeout_seconds=settings.llm_timeout_seconds,
        max_retries=settings.llm_max_retries,
    )


################################################################################
# Module Classes
################################################################################
@dataclass(frozen=True, slots=True)
class Container:
    """
    Hold the process wide singletons created at startup.

    :param settings: Validated configuration of the running process.
    :param chat_service: Service shared by every chat request.
    """

    settings: Settings
    chat_service: ChatService
