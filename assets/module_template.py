################################################################################
# @Project: ai-assistant
# @File Path: backend/app/modules/example/example.py
# @Description: Reference module demonstrating every mandatory
#               code style rule; replace @File Path with the real
#               location when copying this file
# @Creation Date: 2026-10-26
# @Last Update: 2026-10-26
################################################################################

################################################################################
# Import Libraries
################################################################################
# Standard Libraries
from __future__ import annotations

import logging
from typing import Final

################################################################################
# Module Constants
################################################################################
# 额度下限与上限，用于入参边界校验，禁止在业务代码里重复出现字面量
MIN_QUOTA: Final[int] = 0
MAX_QUOTA: Final[int] = 1_000_000
DEFAULT_LIMIT: Final[int] = 1_000

################################################################################
# Module Logger
################################################################################
logger = logging.getLogger(__name__)


################################################################################
# Module Functions
################################################################################
def format_quota_badge(remaining: int) -> str:
    """
    Format a remaining quota value as a short display badge.

    :param remaining: Remaining quota in calls, must be non-negative.
    :return: Badge text such as ``"120 left"``.
    :raises ValueError: If ``remaining`` is negative.
    """
    # 校验入参边界，尽早失败避免负数流到展示层
    if remaining < MIN_QUOTA:
        raise ValueError(f"remaining must be >= {MIN_QUOTA}, got {remaining}")

    # 组装展示文案，数字与单位之间保持单一空格
    return f"{remaining} left"


################################################################################
# Module Classes
################################################################################
class QuotaService:
    """
    Enforce and track per-user call quota.

    The service is stateless with respect to storage: it receives the current
    quota from the caller and returns the consumed result, so it stays easy to
    unit test without any database or cache.

    :param default_limit: Fallback quota applied when a user has no record,
        must be within ``[MIN_QUOTA, MAX_QUOTA]``.
    :ivar _default_limit: Validated fallback quota for new users.
    """

    ############################################################################
    # Class Attributes
    ############################################################################
    QUOTA_UNIT: Final[str] = "call"

    ############################################################################
    # Constructor Method
    ############################################################################
    def __init__(self, default_limit: int = DEFAULT_LIMIT) -> None:
        """
        Initialize the service with a validated fallback quota.

        :param default_limit: Fallback quota for users without a record.
        :raises ValueError: If ``default_limit`` is outside the allowed range.
        """
        # 构造期完成校验，避免非法配置在运行期才暴露
        if not MIN_QUOTA <= default_limit <= MAX_QUOTA:
            raise ValueError(
                f"default_limit must be within [{MIN_QUOTA}, {MAX_QUOTA}], "
                f"got {default_limit}"
            )

        # 仅保存只读依赖，不在此处申请外部资源
        self._default_limit = default_limit

    ############################################################################
    # Default Methods
    ############################################################################
    def __repr__(self) -> str:
        """
        Return an unambiguous representation for debugging.

        :return: Representation containing the configured default limit.
        """
        return f"QuotaService(default_limit={self._default_limit!r})"

    ############################################################################
    # Core Instance Methods
    ############################################################################
    def can_consume(self, amount: int, *, used: int) -> bool:
        """
        Tell whether the requested amount fits into the remaining quota.

        :param amount: Number of units the caller wants to consume, positive.
        :param used: Units already consumed by the user, non-negative.
        :return: ``True`` when the remaining quota covers ``amount``.
        :raises ValueError: If ``amount`` or ``used`` is out of range.
        """
        # 校验两个数值入参，避免负数造成额度虚增
        self._validate_amount(amount)
        if used < MIN_QUOTA:
            raise ValueError(f"used must be >= {MIN_QUOTA}, got {used}")

        # 计算剩余额度并比较，边界取闭区间（正好用完视为可消费）
        remaining = self._default_limit - used
        return remaining >= amount

    def consume(self, amount: int, *, used: int) -> int:
        """
        Consume quota and return the remaining amount.

        :param amount: Number of units to consume, positive.
        :param used: Units already consumed by the user, non-negative.
        :return: Remaining quota after the consumption.
        :raises ValueError: If the amount is invalid or exceeds the remaining quota.
        """
        # 复用能力判断，保持单一校验入口
        if not self.can_consume(amount, used=used):
            raise ValueError(
                f"quota exceeded: requested={amount}, "
                f"remaining={self._default_limit - used}"
            )

        # 仅计算并返回结果，副作用（落库、计费）由上层用例负责
        remaining = self._default_limit - used - amount
        logger.info("quota consumed amount=%s remaining=%s", amount, remaining)
        return remaining

    ############################################################################
    # Utility Methods
    ############################################################################
    @staticmethod
    def build_badge(remaining: int) -> str:
        """
        Build the display badge for a remaining quota.

        :param remaining: Remaining quota in calls.
        :return: Badge text produced by :func:`format_quota_badge`.
        """
        # 委托模块级函数，避免展示逻辑在类内重复实现
        return format_quota_badge(remaining)

    ############################################################################
    # Helper Methods
    ############################################################################
    def _validate_amount(self, amount: int) -> None:
        """
        Validate a consume amount against the allowed range.

        :param amount: Number of units to validate, must be positive.
        :raises ValueError: If ``amount`` is not a positive integer.
        """
        # 同时拦截非正整数与超上限值，给出可定位的错误信息
        if amount <= MIN_QUOTA:
            raise ValueError(f"amount must be positive, got {amount}")
        if amount > MAX_QUOTA:
            raise ValueError(f"amount must be <= {MAX_QUOTA}, got {amount}")


################################################################################
# Script Entry Point
################################################################################
if __name__ == "__main__":
    # 本地手工验证入口，生产逻辑不得写在此处
    logging.basicConfig(level=logging.INFO)
    demo_service = QuotaService(default_limit=100)
    print(demo_service)
    print(demo_service.build_badge(demo_service.consume(30, used=0)))
