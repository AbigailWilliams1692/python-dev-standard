################################################################################
# @Project: ai-assistant
# @File Path: backend/app/core/rate_limit.py
# @Description: Token bucket limiter protecting expensive endpoints per caller
# @Creation Date: 2026-11-18
# @Last Update: 2026-11-18
################################################################################

################################################################################
# Import Libraries
################################################################################
# Standard Libraries
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone

################################################################################
# Module Constants
################################################################################
# 空闲超过该秒数的桶直接丢弃，避免按用户维度累积出无界容器
IDLE_EVICTION_SECONDS: float = 900.0


################################################################################
# Module Functions
################################################################################
def _utc_now() -> datetime:
    """
    Read the clock in UTC with an explicit timezone.

    :return: Current timezone aware UTC timestamp.
    """
    return datetime.now(timezone.utc)


################################################################################
# Module Classes
################################################################################
@dataclass(slots=True)
class _Bucket:
    """
    Track the remaining tokens and the moment they were last refilled.

    :param tokens: Tokens left after the most recent consumption.
    :param updated_at: Moment ``tokens`` was computed.
    """

    tokens: float
    updated_at: datetime


class TokenBucketLimiter:
    """
    Limit calls per key with a refilling token bucket.

    A bucket admits a short burst up to ``capacity`` and then settles at
    ``refill_per_second``, which is what a chat endpoint actually needs: a user
    pasting three messages at once is fine, a loop is not.

    The limiter keeps state in memory, so it protects one process. Behind
    several replicas the same class is used with a shared store or replaced by
    the gateway, but the call sites stay identical.

    :param capacity: Maximum burst size, that is the bucket volume.
    :param refill_per_second: Tokens restored per second of elapsed time.
    :param clock: Callable returning the current UTC time.
    """

    def __init__(
        self,
        *,
        capacity: int,
        refill_per_second: float,
        clock: Callable[[], datetime] = _utc_now,
    ) -> None:
        """
        Create an empty limiter.

        :param capacity: Maximum burst size, that is the bucket volume.
        :param refill_per_second: Tokens restored per second of elapsed time.
        :param clock: Callable returning the current UTC time.
        :return: ``None``, the limiter is ready for use.
        """
        if capacity < 1:
            raise ValueError("capacity must be at least 1")
        if refill_per_second <= 0:
            raise ValueError("refill_per_second must be positive")
        self._capacity = float(capacity)
        self._refill = refill_per_second
        self._clock = clock
        self._buckets: dict[str, _Bucket] = {}

    def allow(self, key: str, *, cost: float = 1.0) -> bool:
        """
        Consume tokens for one call and report whether it may proceed.

        :param key: Identity the limit applies to, typically the caller id.
        :param cost: Tokens this call consumes, defaults to one.
        :return: ``True`` when the call is admitted, ``False`` when throttled.
        """
        now = self._clock()
        bucket = self._buckets.get(key)
        if bucket is None:
            bucket = _Bucket(tokens=self._capacity, updated_at=now)
            self._buckets[key] = bucket

        # 先按流逝时间补币，再判断余额，顺序不能反
        elapsed = (now - bucket.updated_at).total_seconds()
        if elapsed > 0:
            bucket.tokens = min(self._capacity, bucket.tokens + elapsed * self._refill)
            bucket.updated_at = now

        self._evict_idle(now)

        if bucket.tokens < cost:
            return False
        bucket.tokens -= cost
        return True

    def _evict_idle(self, now: datetime) -> None:
        """
        Drop buckets that have been idle long enough to be full again.

        :param now: Current clock reading.
        :return: ``None``, the internal dict is pruned in place.
        """
        # 满桶等价于从未出现过，留着只会让字典随用户数线性增长
        stale = [
            key
            for key, bucket in self._buckets.items()
            if (now - bucket.updated_at).total_seconds() > IDLE_EVICTION_SECONDS
        ]
        for key in stale:
            del self._buckets[key]
