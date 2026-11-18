################################################################################
# @Project: ai-assistant
# @File Path: backend/tests/unit/test_core_guards.py
# @Description: Unit tests of the rate limiter and the idempotency store
# @Creation Date: 2026-11-18
# @Last Update: 2026-11-18
################################################################################

################################################################################
# Import Libraries
################################################################################
# Standard Libraries
from __future__ import annotations

from datetime import datetime, timedelta, timezone

# Third-Party Libraries
import pytest

# Local Modules
from app.core.idempotency import InMemoryIdempotencyStore
from app.core.rate_limit import TokenBucketLimiter

################################################################################
# Module Constants
################################################################################
START: datetime = datetime(2026, 1, 1, tzinfo=timezone.utc)


################################################################################
# Module Functions
################################################################################
def test_limiter_admits_a_burst_then_throttles() -> None:
    """
    Admit calls up to the capacity and reject the next one.

    :return: ``None``, assertions raise on mismatch.
    """
    limiter = TokenBucketLimiter(capacity=3, refill_per_second=1.0)
    assert [limiter.allow("user-a") for _ in range(3)] == [True, True, True]
    assert limiter.allow("user-a") is False


def test_limiter_refills_over_time() -> None:
    """
    Restore tokens according to the configured refill rate.

    :return: ``None``, assertions raise on mismatch.
    """
    clock = FakeClock()
    limiter = TokenBucketLimiter(capacity=2, refill_per_second=1.0, clock=clock)
    assert limiter.allow("user-a") is True
    assert limiter.allow("user-a") is True
    assert limiter.allow("user-a") is False

    # 一个令牌大约一秒补回，稍多等一点避免浮点边界
    clock.advance(1.1)
    assert limiter.allow("user-a") is True


def test_limiter_isolates_keys() -> None:
    """
    Keep the buckets of different callers independent.

    :return: ``None``, assertions raise on mismatch.
    """
    limiter = TokenBucketLimiter(capacity=1, refill_per_second=1.0)
    assert limiter.allow("user-a") is True
    assert limiter.allow("user-a") is False
    assert limiter.allow("user-b") is True


def test_limiter_rejects_invalid_configuration() -> None:
    """
    Fail fast on a capacity or refill rate that cannot work.

    :return: ``None``, assertions raise on mismatch.
    """
    with pytest.raises(ValueError):
        TokenBucketLimiter(capacity=0, refill_per_second=1.0)
    with pytest.raises(ValueError):
        TokenBucketLimiter(capacity=1, refill_per_second=0.0)


async def test_idempotency_store_round_trip() -> None:
    """
    Replay the payload stored under a key.

    :return: ``None``, assertions raise on mismatch.
    """
    store = InMemoryIdempotencyStore()
    assert await store.get("key-1") is None

    await store.put("key-1", {"code": 0, "data": {"id": "x"}})
    record = await store.get("key-1")
    assert record is not None
    assert record.payload["data"] == {"id": "x"}


async def test_idempotency_store_expires_records() -> None:
    """
    Drop a record once its time to live has elapsed.

    :return: ``None``, assertions raise on mismatch.
    """
    clock = FakeClock()
    store = InMemoryIdempotencyStore(ttl_seconds=60, clock=clock)
    await store.put("key-1", {"code": 0})

    clock.advance(61)
    assert await store.get("key-1") is None


################################################################################
# Module Classes
################################################################################
class FakeClock:
    """
    Provide a manually advanced clock for deterministic time tests.

    Reading the real clock would make refill and expiry assertions flaky, so
    both collaborators accept a callable instead of calling ``datetime.now``.
    """

    def __init__(self) -> None:
        """
        Start at a fixed instant.

        :return: ``None``, the clock is ready for use.
        """
        self.now = START

    def __call__(self) -> datetime:
        """
        Return the current fake instant.

        :return: Frozen clock reading.
        """
        return self.now

    def advance(self, seconds: float) -> None:
        """
        Move the clock forward.

        :param seconds: Elapsed seconds to simulate.
        :return: ``None``, the internal instant is mutated.
        """
        self.now = self.now + timedelta(seconds=seconds)
