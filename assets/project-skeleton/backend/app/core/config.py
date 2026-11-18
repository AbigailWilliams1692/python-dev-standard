################################################################################
# @Project: ai-assistant
# @File Path: backend/app/core/config.py
# @Description: Typed runtime configuration read once from the environment
# @Creation Date: 2026-11-18
# @Last Update: 2026-11-18
################################################################################

################################################################################
# Import Libraries
################################################################################
# Standard Libraries
from __future__ import annotations

from enum import Enum
from functools import lru_cache

# Third-Party Libraries
from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Local Modules
from app.core.errors import ConfigurationError


################################################################################
# Module Functions
################################################################################
@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Return the process wide settings singleton.

    Settings reads the environment on first use; the cache keeps every later
    call free while still failing fast on an invalid configuration.

    :return: Settings parsed from the environment on the first call.
    """
    # 解析失败直接向上抛，由启动流程决定是否退出进程
    return Settings()


################################################################################
# Module Classes
################################################################################
class AppEnvironment(str, Enum):
    """
    Enumerate the deployment environments the process can run in.

    The value is compared against ``AppEnvironment`` members only, never
    against raw strings, so a typo fails at import time instead of at runtime.
    """

    DEV = "dev"
    TEST = "test"
    PROD = "prod"


class LlmProvider(str, Enum):
    """
    Enumerate the supported language model backends.

    ``FAKE`` keeps the service runnable without any vendor account, which is
    what makes the sample and the test suite deterministic.
    """

    FAKE = "fake"
    OPENAI = "openai"


class Settings(BaseSettings):
    """
    Hold every runtime knob in one immutable, validated object.

    Unknown variables are rejected so a misspelled environment variable cannot
    be silently ignored. Validation runs once at startup: a configuration that
    cannot work must fail the process immediately, not at 3 a.m. on the first
    request.

    :param app_name: Service name used by logs and the OpenAPI document.
    :param app_env: Deployment environment the process believes it runs in.
    :param log_level: Root logger level, such as ``INFO`` or ``DEBUG``.
    :param log_json: Whether to emit JSON lines instead of readable text.
    :param llm_provider: Selected language model backend.
    :param llm_api_key: Vendor credential, empty when the fake backend is used.
    :param llm_base_url: Base URL of the vendor HTTP API.
    :param llm_timeout_seconds: Per call timeout applied by the adapter.
    :param llm_max_retries: Extra attempts after a retryable upstream failure.
    :param chat_default_model: Model applied when the caller omits one.
    :param chat_max_turns: Maximum number of user turns per session.
    :param chat_max_message_chars: Maximum accepted length of one message.
    """

    ############################################################################
    # Class Attributes
    ############################################################################
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="AI_ASSISTANT_",
        extra="forbid",
        frozen=True,
    )

    # 业务配置项：全部带类型与默认值，密钥用 SecretStr 避免被日志打印
    app_name: str = Field(default="ai-assistant", min_length=1, max_length=64)
    app_env: AppEnvironment = AppEnvironment.DEV
    log_level: str = Field(default="INFO", max_length=16)
    log_json: bool = True

    llm_provider: LlmProvider = LlmProvider.FAKE
    llm_api_key: SecretStr = SecretStr("")
    llm_base_url: str = Field(
        default="https://api.openai.com/v1",
        max_length=256,
    )
    llm_timeout_seconds: float = Field(default=30.0, gt=0, le=300)
    llm_max_retries: int = Field(default=2, ge=0, le=10)

    chat_default_model: str = Field(default="gpt-4o-mini", max_length=64)
    chat_max_turns: int = Field(default=40, ge=1, le=500)
    chat_max_message_chars: int = Field(default=8_000, ge=1, le=100_000)

    ############################################################################
    # Validation Methods
    ############################################################################
    @model_validator(mode="after")
    def require_runtime_credentials(self) -> Settings:
        """
        Reject combinations that would fail on the first real request.

        :return: The validated settings instance, unchanged.
        :raises ConfigurationError: If a required value is missing or unsafe.
        """
        # 真实供应商必须有密钥，否则启动即失败，不留到运行期
        if self.llm_provider is LlmProvider.OPENAI and not (
            self.llm_api_key.get_secret_value().strip()
        ):
            raise ConfigurationError("llm_api_key is required when llm_provider=openai")

        # 生产环境必须输出结构化日志，否则无法被采集与告警
        if self.app_env is AppEnvironment.PROD and not self.log_json:
            raise ConfigurationError("log_json must stay enabled in production")
        return self
