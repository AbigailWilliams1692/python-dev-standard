################################################################################
# @Project: ai-assistant
# @File Path: backend/app/core/logging.py
# @Description: Structured logging with trace correlation and secret masking
# @Creation Date: 2026-11-18
# @Last Update: 2026-11-18
################################################################################

################################################################################
# Import Libraries
################################################################################
# Standard Libraries
from __future__ import annotations

import json
import logging
import re
import sys
import uuid
from contextvars import ContextVar, Token
from datetime import datetime, timezone
from typing import Any, Final

################################################################################
# Module Constants
################################################################################
# 请求级追踪号，由中间件写入，日志与响应头共用同一份
_TRACE_ID: ContextVar[str] = ContextVar("trace_id", default="-")
TRACE_HEADER: Final[str] = "X-Trace-Id"

# 这些库默认逐请求打 INFO，业务日志会被淹没，统一压到 WARNING
NOISY_LOGGERS: Final[tuple[str, ...]] = ("httpx", "httpcore")

# 需要脱敏的字段名，覆盖配置、鉴权与会话三类凭据
SENSITIVE_KEYS: Final[tuple[str, ...]] = (
    "password",
    "passwd",
    "secret",
    "token",
    "api_key",
    "apikey",
    "authorization",
    "cookie",
)

# 三类模式按「显式赋值 -> 手机号 -> 邮箱」顺序替换，避免互相破坏
_SECRET_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"(?i)\b(" + "|".join(SENSITIVE_KEYS) + r")\b(\s*[=:]\s*)([^\s,;&\"'}]+)"
)
_PHONE_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"(?<!\d)(1[3-9]\d)\d{4}(\d{4})(?!\d)"
)
_EMAIL_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"(?<![\w.])([\w.+-])[\w.+-]*(@[\w-]+(?:\.[\w-]+)+)"
)

################################################################################
# Module Logger
################################################################################
logger = logging.getLogger(__name__)


################################################################################
# Module Functions
################################################################################
def get_trace_id() -> str:
    """
    Return the trace id bound to the current execution context.

    :return: Active trace id, or ``"-"`` outside a request.
    """
    return _TRACE_ID.get()


def set_trace_id(value: str) -> Token[str]:
    """
    Bind a trace id to the current context and return the reset token.

    :param value: Identifier propagated to every log line of the request.
    :return: Token that restores the previous value when reset.
    """
    return _TRACE_ID.set(value)


def reset_trace_id(token: Token[str]) -> None:
    """
    Restore the trace id that was active before :func:`set_trace_id`.

    :param token: Token returned by the matching ``set_trace_id`` call.
    """
    # 必须由 finally 调用，否则异常路径会把上下文泄漏给下一个任务
    _TRACE_ID.reset(token)


def new_trace_id() -> str:
    """
    Generate a trace id for an inbound request that carries none.

    :return: 128 bit identifier rendered as 32 hexadecimal characters.
    """
    return uuid.uuid4().hex


def redact(text: str) -> str:
    """
    Mask credentials and personal identifiers inside free form text.

    Masking happens at the handler boundary rather than at every call site,
    because a rule that depends on human discipline is eventually violated.

    :param text: Rendered log line or exception message.
    :return: Text with sensitive fragments replaced by asterisks.
    """
    # 先处理 key=value 形式的凭据，保留字段名以便定位问题
    masked = _SECRET_PATTERN.sub(
        lambda match: f"{match.group(1)}{match.group(2)}***",
        text,
    )

    # 再处理手机号与邮箱，只保留可识别的首尾片段
    masked = _PHONE_PATTERN.sub(r"\1****\2", masked)
    return _EMAIL_PATTERN.sub(r"\1***\2", masked)


def configure_logging(*, level: str, json_output: bool) -> None:
    """
    Install exactly one stdout handler on the root logger.

    The existing handler list is cleared first, so calling the application
    factory repeatedly in tests does not duplicate every line.

    :param level: Root level name such as ``INFO`` or ``DEBUG``.
    :param json_output: Emit JSON lines when true, readable text otherwise.
    :raises ValueError: If ``level`` is not a known logging level name.
    """
    # 解析级别名，未知值必须显式失败而不是静默退化为 WARNING
    resolved = logging.getLevelName(level.upper())
    if not isinstance(resolved, int):
        raise ValueError(f"unknown log level: {level}")

    # 重建 handler，保证进程内只有一条输出通路
    root = logging.getLogger()
    for handler in list(root.handlers):
        root.removeHandler(handler)

    stream = logging.StreamHandler(stream=sys.stdout)
    stream.setFormatter(_JsonFormatter() if json_output else _TextFormatter())
    root.addHandler(stream)
    root.setLevel(resolved)

    # 第三方传输层日志只保留告警以上，避免每条请求两行噪声
    for name in NOISY_LOGGERS:
        logging.getLogger(name).setLevel(logging.WARNING)


def _utc_timestamp(created: float) -> str:
    """
    Render a record creation time as UTC ISO 8601 with milliseconds.

    :param created: Seconds since the epoch, taken from the log record.
    :return: Timestamp such as ``2026-11-18T08:00:00.123Z``.
    """
    moment = datetime.fromtimestamp(created, tz=timezone.utc)
    return moment.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


################################################################################
# Module Classes
################################################################################
class _JsonFormatter(logging.Formatter):
    """
    Render each record as one JSON object per line.

    The field set is fixed on purpose: log shippers and dashboards depend on
    stable keys, so extra context belongs in the message, not in ad hoc keys.
    """

    ############################################################################
    # Core Instance Methods
    ############################################################################
    def format(self, record: logging.LogRecord) -> str:
        """
        Serialise one record with the shared field set.

        :param record: Record produced by the logging framework.
        :return: Single line JSON document with secrets already masked.
        """
        payload: dict[str, Any] = {
            "timestamp": _utc_timestamp(record.created),
            "level": record.levelname,
            "logger": record.name,
            "trace_id": get_trace_id(),
            "message": record.getMessage(),
        }

        # 堆栈作为独立字段承载，避免多行日志打断 JSON 解析
        if record.exc_info is not None:
            payload["exception"] = self.formatException(record.exc_info)
        return redact(json.dumps(payload, ensure_ascii=False))


class _TextFormatter(logging.Formatter):
    """
    Render each record as a compact line for local development.
    """

    ############################################################################
    # Core Instance Methods
    ############################################################################
    def format(self, record: logging.LogRecord) -> str:
        """
        Build a readable line that still carries the trace id.

        :param record: Record produced by the logging framework.
        :return: Single line text with secrets already masked.
        """
        timestamp = _utc_timestamp(record.created)[11:23]
        line = (
            f"{timestamp} {record.levelname:<8} {record.name} "
            f"[{get_trace_id()}] {record.getMessage()}"
        )

        # 异常堆栈追加在换行之后，开发环境可读性优先
        if record.exc_info is not None:
            line = f"{line}\n{self.formatException(record.exc_info)}"
        return redact(line)
