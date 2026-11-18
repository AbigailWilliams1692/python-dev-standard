################################################################################
# @Project: ai-assistant
# @File Path: backend/app/core/idempotency.py
# @Description: Idempotency store keeping retried writes from duplicating
# @Creation Date: 2026-11-18
# @Last Update: 2026-11-18
################################################################################

################################################################################
# Import Libraries
################################################################################
# Standard Libraries
from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Protocol

################################################################################
# Module Constants
################################################################################
DEFAULT_TTL_SECONDS: int = 24 * 60 * 60


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
@dataclass(frozen=True, slots=True)
class IdempotencyRecord:
    """
    Hold the result of one request that already produced an effect.

    :param payload: Response body replayed to every retry of the same key.
    :param stored_at: Moment the record was written, used for expiry.
    """

    payload: dict[str, Any]
    stored_at: datetime


class IdempotencyStore(Protocol):
    """
    Describe the storage a route needs to replay a previous response.

    The port stays this small on purpose: callers only ever ask "did this key
    already run" and never need to inspect or mutate stored records.
    """

    async def get(self, key: str) -> IdempotencyRecord | None:
        """
        Return the record written for a key, if it is still fresh.

        :param key: Client supplied idempotency key.
        :return: Stored record, or ``None`` when absent or expired.
        """
        ...

    async def put(self, key: str, payload: dict[str, Any]) -> None:
        """
        Remember the response produced for a key.

        :param key: Client supplied idempotency key.
        :param payload: Response body to replay on the next retry.
        :return: ``None``, the record is stored with the current clock.
        """
        ...


class InMemoryIdempotencyStore:
    """
    Keep idempotency records in a dict bounded by a time to live.

    Suitable for a single process and for tests. A multi replica deployment
    swaps this for Redis with ``SET key value NX EX ttl`` behind the same port,
    which is why routes depend on :class:`IdempotencyStore` and never on this
    class.

    :param ttl_seconds: How long a record stays replayable.
    :param clock: Callable returning the current UTC time.
    """

    def __init__(
        self,
        *,
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
        clock: Callable[[], datetime] = _utc_now,
    ) -> None:
        """
        Prepare an empty store.

        :param ttl_seconds: How long a record stays replayable.
        :param clock: Callable returning the current UTC time.
        :return: ``None``, the store is ready for use.
        """
        self._ttl = timedelta(seconds=ttl_seconds)
        self._clock = clock
        self._records: dict[str, IdempotencyRecord] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> IdempotencyRecord | None:
        """
        Return the record written for a key, dropping it once expired.

        :param key: Client supplied idempotency key.
        :return: Stored record, or ``None`` when absent or expired.
        """
        async with self._lock:
            record = self._records.get(key)
            if record is None:
                return None
            # 过期记录当场清理，避免长时间运行后字典无界增长
            if self._clock() - record.stored_at > self._ttl:
                del self._records[key]
                return None
            return record

    async def put(self, key: str, payload: dict[str, Any]) -> None:
        """
        Remember the response produced for a key.

        :param key: Client supplied idempotency key.
        :param payload: Response body to replay on the next retry.
        :return: ``None``, the record is stored with the current clock.
        """
        async with self._lock:
            self._records[key] = IdempotencyRecord(
                payload=payload,
                stored_at=self._clock(),
            )
