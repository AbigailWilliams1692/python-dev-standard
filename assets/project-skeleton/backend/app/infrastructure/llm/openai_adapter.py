################################################################################
# @Project: ai-assistant
# @File Path: backend/app/infrastructure/llm/openai_adapter.py
# @Description: LLM port implementation over the OpenAI compatible HTTP API
# @Creation Date: 2026-11-18
# @Last Update: 2026-11-18
################################################################################

################################################################################
# Import Libraries
################################################################################
# Standard Libraries
from __future__ import annotations

import asyncio
import random
from collections.abc import Sequence
from typing import Any, Final

# Third-Party Libraries
import httpx

# Local Modules
from app.core.errors import ConfigurationError, ExternalServiceError
from app.modules.chat.domain import ChatMessage
from app.modules.chat.ports import LlmCompletion

################################################################################
# Module Constants
################################################################################
# 仅这几类状态码值得重试，其余 4xx 重试只会浪费额度
RETRYABLE_STATUS: Final[frozenset[int]] = frozenset({429, 500, 502, 503, 504})
BACKOFF_BASE_SECONDS: Final[float] = 0.2
BACKOFF_MAX_SECONDS: Final[float] = 5.0


################################################################################
# Module Classes
################################################################################
class OpenAiAdapter:
    """
    Implement :class:`LlmPort` over the chat completions HTTP API.

    Timeout, bounded retry and backoff live here and nowhere else: retrying in
    both the adapter and the service would multiply billable calls. The
    credential is held as a plain string on purpose, because it must be sent
    in a header; it is simply never logged or returned.

    :param api_key: Vendor credential, must not be blank.
    :param base_url: Base URL of the compatible endpoint.
    :param timeout_seconds: Timeout applied to each individual attempt.
    :param max_retries: Extra attempts after a retryable failure.
    :param client: Optional shared HTTP client, injected by tests.
    """

    ############################################################################
    # Constructor Method
    ############################################################################
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        timeout_seconds: float,
        max_retries: int,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        """
        Validate the credential and derive the completion endpoint.

        :param api_key: Vendor credential, must not be blank.
        :param base_url: Base URL of the compatible endpoint.
        :param timeout_seconds: Timeout applied to each individual attempt.
        :param max_retries: Extra attempts after a retryable failure.
        :param client: Optional shared HTTP client, injected by tests.
        :raises ConfigurationError: If the credential is blank.
        """
        if not api_key.strip():
            raise ConfigurationError("openai adapter requires a non blank api key")

        # 去掉尾部斜杠，避免拼出双斜杠的路径
        self._url = f"{base_url.rstrip('/')}/chat/completions"
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds
        self._max_retries = max(0, max_retries)
        self._client = client

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
        Request one completion and translate the response into domain terms.

        :param messages: Ordered history, oldest first, never empty.
        :param model: Model name requested by the session.
        :return: Completion text together with token usage.
        :raises ExternalServiceError: If the provider fails after all retries
            or returns a body that cannot be interpreted.
        """
        payload = self._build_payload(messages, model)
        response = await self._send(payload)
        return self._decode(response)

    ############################################################################
    # Helper Methods
    ############################################################################
    @staticmethod
    def _build_payload(
        messages: Sequence[ChatMessage],
        model: str,
    ) -> dict[str, Any]:
        """
        Translate domain messages into the vendor request body.

        :param messages: Ordered history, oldest first.
        :param model: Model name requested by the session.
        :return: JSON serialisable request body.
        """
        return {
            "model": model,
            "temperature": 0.7,
            "messages": [
                {"role": item.role.value, "content": item.content} for item in messages
            ],
        }

    async def _send(self, payload: dict[str, Any]) -> httpx.Response:
        """
        Post the payload, reusing the injected client when there is one.

        :param payload: JSON serialisable request body.
        :return: Response with a status below 400.
        :raises ExternalServiceError: If every attempt fails.
        """
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        # 未注入客户端时按次创建，确保连接与超时随请求一起释放
        if self._client is not None:
            return await self._post_with_retry(self._client, payload, headers)
        async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
            return await self._post_with_retry(client, payload, headers)

    async def _post_with_retry(
        self,
        client: httpx.AsyncClient,
        payload: dict[str, Any],
        headers: dict[str, str],
    ) -> httpx.Response:
        """
        Perform the POST with bounded exponential backoff.

        :param client: HTTP client used for every attempt.
        :param payload: JSON serialisable request body.
        :param headers: Request headers including the credential.
        :return: Response with a status below 400.
        :raises ExternalServiceError: If all attempts fail or the status is
            not retryable.
        """
        attempts = self._max_retries + 1
        last_failure = "no attempt executed"

        for attempt in range(attempts):
            try:
                response = await client.post(
                    self._url,
                    json=payload,
                    headers=headers,
                )
            except httpx.HTTPError as exc:
                last_failure = f"{type(exc).__name__}: {exc}"
            else:
                if response.status_code < 400:
                    return response
                if response.status_code not in RETRYABLE_STATUS:
                    raise ExternalServiceError(
                        "upstream rejected the request",
                        detail={"status": response.status_code},
                    )
                last_failure = f"status={response.status_code}"

            # 最后一次失败后不再 sleep，避免无意义的收尾等待
            if attempt + 1 < attempts:
                await asyncio.sleep(self._backoff_seconds(attempt))

        raise ExternalServiceError(
            "upstream unavailable after retries",
            detail={"attempts": attempts, "last_failure": last_failure},
        )

    @staticmethod
    def _backoff_seconds(attempt: int) -> float:
        """
        Compute the exponential delay with jitter for one retry.

        :param attempt: Zero based index of the attempt that just failed.
        :return: Delay in seconds, capped by ``BACKOFF_MAX_SECONDS``.
        """
        base = min(BACKOFF_BASE_SECONDS * 2.0**attempt, BACKOFF_MAX_SECONDS)
        # 抖动只用于打散并发重试，不承担任何安全职责
        return base + random.uniform(0, 0.1)  # noqa: S311

    @staticmethod
    def _decode(response: httpx.Response) -> LlmCompletion:
        """
        Extract the answer and the usage from a vendor response.

        :param response: Successful HTTP response.
        :return: Completion text together with token usage.
        :raises ExternalServiceError: If the body does not match the contract.
        """
        try:
            data: Any = response.json()
        except ValueError as exc:
            raise ExternalServiceError("upstream returned invalid json") from exc
        if not isinstance(data, dict):
            raise ExternalServiceError("upstream returned a non object body")

        # 逐层校验结构，绝不把 Any 直接传进业务层
        choices = data.get("choices")
        if not isinstance(choices, list) or not choices:
            raise ExternalServiceError("upstream returned no choices")

        first = choices[0]
        message = first.get("message") if isinstance(first, dict) else None
        text = message.get("content") if isinstance(message, dict) else None
        if not isinstance(text, str) or not text.strip():
            raise ExternalServiceError("upstream returned no text content")

        usage = data.get("usage")
        prompt_tokens = 0
        completion_tokens = 0
        if isinstance(usage, dict):
            prompt_tokens = int(usage.get("prompt_tokens") or 0)
            completion_tokens = int(usage.get("completion_tokens") or 0)

        return LlmCompletion(
            text=text.strip(),
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )
