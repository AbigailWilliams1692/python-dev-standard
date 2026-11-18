################################################################################
# @Project: ai-assistant
# @File Path: .workbuddy/skills/python-dev-standard/scripts/new_module.py
# @Description: Scaffold a compliant business domain from the project skeleton
# @Creation Date: 2026-11-18
# @Last Update: 2026-11-18
################################################################################

################################################################################
# Import Libraries
################################################################################
# Standard Libraries
from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path
from string import Template
from typing import Final

################################################################################
# Module Constants
################################################################################
SECTION_WIDTH: Final[int] = 80
INNER_WIDTH: Final[int] = 76
SEPARATOR: Final[str] = "#" * SECTION_WIDTH
INNER_SEPARATOR: Final[str] = "    " + "#" * INNER_WIDTH

# 域名只允许小写字母、数字与下划线，禁止拼音与保留字冲突
DOMAIN_PATTERN: Final[re.Pattern[str]] = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")
RESERVED_DOMAINS: Final[frozenset[str]] = frozenset(
    {"core", "modules", "infrastructure", "shared", "tests", "app", "main"}
)

TEMPLATE_DOMAIN: Final[Template] = Template(
    '''${SEP}
# @Project: ai-assistant
# @File Path: backend/app/modules/${domain}/domain.py
# @Description: Domain model and invariants of the ${domain} aggregate
# @Creation Date: ${date}
# @Last Update: ${date}
${SEP}

${SEP}
# Import Libraries
${SEP}
# Standard Libraries
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import ClassVar

# Local Modules
from app.core.error_codes import ErrorCode
from app.core.errors import NotFoundError, ValidationError

${SEP}
# Module Constants
${SEP}
MAX_TITLE_LENGTH: int = 120


${SEP}
# Module Functions
${SEP}
def normalize_title(title: str) -> str:
    """
    Trim a title and reject blank or oversized values.

    :param title: Raw title supplied by the caller.
    :return: Trimmed title within :data:`MAX_TITLE_LENGTH` characters.
    :raises ValidationError: If the title is blank or too long.
    """
    # 先去掉首尾空白，再判断是否为空，避免纯空格标题落库
    cleaned = title.strip()
    if not cleaned:
        raise ValidationError("title must not be blank")
    if len(cleaned) > MAX_TITLE_LENGTH:
        raise ValidationError(f"title exceeds {MAX_TITLE_LENGTH} characters")
    return cleaned


def _require_aware(moment: datetime, field_name: str) -> None:
    """
    Reject naive timestamps, which silently mean server local time.

    :param moment: Timestamp to inspect.
    :param field_name: Field name reported in the error message.
    :raises ValidationError: If the timestamp carries no timezone.
    """
    if moment.tzinfo is None:
        raise ValidationError(f"{field_name} must be timezone aware")


${SEP}
# Module Classes
${SEP}
class ${Entity}NotFoundError(NotFoundError):
    """
    Report a ${domain} that does not exist or is not visible to the caller.

    Missing and foreign records share one error on purpose: distinguishing
    them would let a caller enumerate other users' identifiers.
    """

    default_code: ClassVar[ErrorCode] = ErrorCode.${ENTITY}_NOT_FOUND


@dataclass(slots=True)
class ${Entity}:
    """
    Represent one ${domain} owned by a single user.

    :param ${domain}_id: Stable identifier created by the repository.
    :param owner_id: Identity of the user allowed to read and modify it.
    :param title: Human readable label, never blank.
    :param created_at: UTC timestamp of creation.
    :param updated_at: UTC timestamp of the last modification.
    :param version: Optimistic concurrency token, incremented on save.
    """

    ${domain}_id: str
    owner_id: str
    title: str
    created_at: datetime
    updated_at: datetime
    version: int = 1

    def rename(self, title: str, *, now: datetime) -> None:
        """
        Replace the title and bump the modification time.

        :param title: New title supplied by the caller.
        :param now: Clock reading used as the modification time.
        :raises ValidationError: If the title is blank or the clock is naive.
        """
        # 写入前统一校验，保证不变量只在领域层维护一份
        self.title = normalize_title(title)
        _require_aware(now, "now")
        self.updated_at = now
        self.version += 1
'''
)

TEMPLATE_PORTS: Final[Template] = Template(
    '''${SEP}
# @Project: ai-assistant
# @File Path: backend/app/modules/${domain}/ports.py
# @Description: Ports the ${domain} domain needs from the outside world
# @Creation Date: ${date}
# @Last Update: ${date}
${SEP}

${SEP}
# Import Libraries
${SEP}
# Standard Libraries
from __future__ import annotations

from typing import Protocol

# Local Modules
from app.modules.${domain}.domain import ${Entity}


${SEP}
# Module Classes
${SEP}
class ${Entity}Repository(Protocol):
    """
    Describe the persistence operations the ${domain} service relies on.

    The service depends on this protocol instead of a concrete store, so
    swapping memory for a database never touches business rules.
    """

    async def add(self, entity: ${Entity}) -> None:
        """
        Persist a newly created aggregate.

        :param entity: Aggregate to store, never already present.
        :return: ``None``, the entity is stored as given.
        """
        ...

    async def get(self, ${domain}_id: str) -> ${Entity} | None:
        """
        Return one aggregate by identifier.

        :param ${domain}_id: Identifier of the requested aggregate.
        :return: The aggregate, or ``None`` when no record matches.
        """
        ...

    async def save(self, entity: ${Entity}, *, expected_version: int) -> None:
        """
        Replace an aggregate only when the stored version still matches.

        :param entity: Aggregate carrying the new state and bumped version.
        :param expected_version: Version the caller read before modifying.
        :return: ``None``, the aggregate is stored with its new version.
        :raises ConflictError: If another writer changed it first.
        """
        ...

    async def list_by_owner(self, owner_id: str, *, limit: int) -> list[${Entity}]:
        """
        Return the owner's aggregates, newest first.

        :param owner_id: Identity whose aggregates are requested.
        :param limit: Maximum number of records to return.
        :return: Aggregates ordered by modification time descending.
        """
        ...
'''
)

TEMPLATE_SERVICE: Final[Template] = Template(
    '''${SEP}
# @Project: ai-assistant
# @File Path: backend/app/modules/${domain}/service.py
# @Description: Application service orchestrating the ${domain} use cases
# @Creation Date: ${date}
# @Last Update: ${date}
${SEP}

${SEP}
# Import Libraries
${SEP}
# Standard Libraries
from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from uuid import uuid4

# Local Modules
from app.core.errors import ValidationError
from app.modules.${domain}.domain import (
    ${Entity},
    ${Entity}NotFoundError,
    normalize_title,
)
from app.modules.${domain}.ports import ${Entity}Repository

${SEP}
# Module Constants
${SEP}
MAX_PAGE_SIZE: int = 100


${SEP}
# Module Functions
${SEP}
def _utc_now() -> datetime:
    """
    Read the clock in UTC with an explicit timezone.

    :return: Current timezone aware UTC timestamp.
    """
    return datetime.now(timezone.utc)


def _require_owner(owner_id: str) -> str:
    """
    Reject a blank identity before it reaches the repository.

    :param owner_id: Identity resolved by the interface layer.
    :return: The same identity, guaranteed non blank.
    :raises ValidationError: If the identity is blank.
    """
    if not owner_id.strip():
        raise ValidationError("owner_id must not be blank")
    return owner_id


${SEP}
# Module Classes
${SEP}
class ${Entity}Service:
    """
    Implement the ${domain} use cases on top of the repository port.

    :param repository: Storage port, injected by the container.
    :param clock: Clock used for creation and modification times.
    """

    def __init__(
        self,
        repository: ${Entity}Repository,
        *,
        clock: Callable[[], datetime] = _utc_now,
    ) -> None:
        """
        Store the collaborators required by every use case.

        :param repository: Storage port backing this service.
        :param clock: Callable returning the current UTC time.
        :return: ``None``, the instance is ready for use.
        """
        self._repository = repository
        self._clock = clock

    async def create(self, *, owner_id: str, title: str) -> ${Entity}:
        """
        Create an aggregate owned by the caller.

        :param owner_id: Identity resolved by the interface layer.
        :param title: Human readable label of the new aggregate.
        :return: The persisted aggregate with its initial version.
        :raises ValidationError: If the identity or title is blank.
        """
        # 先完成全部校验再写入，避免半成品落库
        owner = _require_owner(owner_id)
        cleaned = normalize_title(title)
        now = self._clock()
        entity = ${Entity}(
            ${domain}_id=uuid4().hex,
            owner_id=owner,
            title=cleaned,
            created_at=now,
            updated_at=now,
        )
        await self._repository.add(entity)
        return entity

    async def get(self, *, ${domain}_id: str, owner_id: str) -> ${Entity}:
        """
        Return one aggregate visible to the caller.

        :param ${domain}_id: Identifier of the requested aggregate.
        :param owner_id: Identity resolved by the interface layer.
        :return: The aggregate owned by the caller.
        :raises ${Entity}NotFoundError: If missing or owned by someone else.
        """
        found = await self._repository.get(${domain}_id)
        # 不存在与越权返回同一个错误，避免被用来枚举他人资源
        if found is None or found.owner_id != owner_id:
            raise ${Entity}NotFoundError("${domain} not found")
        return found

    async def list_for_owner(
        self,
        *,
        owner_id: str,
        limit: int = 20,
    ) -> list[${Entity}]:
        """
        Return the caller's aggregates, newest first.

        :param owner_id: Identity resolved by the interface layer.
        :param limit: Maximum number of records, clamped to a hard bound.
        :return: Aggregates owned by the caller.
        :raises ValidationError: If the identity is blank or limit is invalid.
        """
        owner = _require_owner(owner_id)
        if limit < 1 or limit > MAX_PAGE_SIZE:
            raise ValidationError(f"limit must be between 1 and {MAX_PAGE_SIZE}")
        return await self._repository.list_by_owner(owner, limit=limit)

    async def rename(
        self,
        *,
        ${domain}_id: str,
        owner_id: str,
        title: str,
    ) -> ${Entity}:
        """
        Rename an aggregate owned by the caller.

        :param ${domain}_id: Identifier of the target aggregate.
        :param owner_id: Identity resolved by the interface layer.
        :param title: New title supplied by the caller.
        :return: The updated aggregate with a bumped version.
        :raises ${Entity}NotFoundError: If missing or owned by someone else.
        :raises ConflictError: If another writer modified it first.
        """
        entity = await self.get(${domain}_id=${domain}_id, owner_id=owner_id)
        previous_version = entity.version
        entity.rename(title, now=self._clock())
        await self._repository.save(entity, expected_version=previous_version)
        return entity
'''
)

TEMPLATE_SCHEMAS: Final[Template] = Template(
    '''${SEP}
# @Project: ai-assistant
# @File Path: backend/app/modules/${domain}/schemas.py
# @Description: Request and response contracts of the ${domain} HTTP interface
# @Creation Date: ${date}
# @Last Update: ${date}
${SEP}

${SEP}
# Import Libraries
${SEP}
# Standard Libraries
from __future__ import annotations

from datetime import datetime

# Third-Party Libraries
from pydantic import BaseModel, ConfigDict, Field, field_validator

# Local Modules
from app.modules.${domain}.domain import ${Entity}

${SEP}
# Module Constants
${SEP}
# 请求体绝对上限，真正的业务上限由领域层收口
ABSOLUTE_TITLE_LIMIT: int = 500


${SEP}
# Module Classes
${SEP}
class Create${Entity}Request(BaseModel):
    """
    Capture the body of a create request.

    :param title: Label of the aggregate, trimmed before use.
    """

    title: str = Field(min_length=1, max_length=ABSOLUTE_TITLE_LIMIT)

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str) -> str:
        """
        Remove surrounding whitespace before the domain sees the value.

        :param value: Raw title from the request body.
        :return: Trimmed title.
        """
        return value.strip()


class Rename${Entity}Request(BaseModel):
    """
    Capture the body of a rename request.

    :param title: New label of the aggregate, trimmed before use.
    """

    title: str = Field(min_length=1, max_length=ABSOLUTE_TITLE_LIMIT)

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str) -> str:
        """
        Remove surrounding whitespace before the domain sees the value.

        :param value: Raw title from the request body.
        :return: Trimmed title.
        """
        return value.strip()


class ${Entity}View(BaseModel):
    """
    Expose one aggregate to the client.

    :param ${domain}_id: Stable identifier of the aggregate.
    :param title: Human readable label.
    :param created_at: UTC timestamp of creation.
    :param updated_at: UTC timestamp of the last modification.
    :param version: Optimistic concurrency token.
    """

    model_config = ConfigDict(frozen=True)

    ${domain}_id: str
    title: str
    created_at: datetime
    updated_at: datetime
    version: int

    @classmethod
    def from_domain(cls, entity: ${Entity}) -> ${Entity}View:
        """
        Build the response model from a domain aggregate.

        :param entity: Aggregate returned by the service.
        :return: View carrying only the fields the client may see.
        """
        return cls(
            ${domain}_id=entity.${domain}_id,
            title=entity.title,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            version=entity.version,
        )


class ${Entity}List(BaseModel):
    """
    Carry one page of aggregates.

    :param items: Aggregates of the current page.
    """

    model_config = ConfigDict(frozen=True)

    items: list[${Entity}View]
'''
)

TEMPLATE_ROUTER: Final[Template] = Template(
    '''${SEP}
# @Project: ai-assistant
# @File Path: backend/app/modules/${domain}/router.py
# @Description: HTTP endpoints of the ${domain} domain
# @Creation Date: ${date}
# @Last Update: ${date}
${SEP}

${SEP}
# Import Libraries
${SEP}
# Standard Libraries
from __future__ import annotations

from typing import Annotated

# Third-Party Libraries
from fastapi import APIRouter, Depends, Query

# Local Modules
from app.core.logging import get_trace_id
from app.core.schemas import Envelope
from app.dependencies import get_current_user_id, get_${domain}_service
from app.modules.${domain}.schemas import (
    Create${Entity}Request,
    ${Entity}List,
    ${Entity}View,
    Rename${Entity}Request,
)
from app.modules.${domain}.service import ${Entity}Service

${SEP}
# Module Constants
${SEP}
# 路由对象由 main 统一挂载；检查器已将该框架约定名加入白名单
router = APIRouter(prefix="/${domain}s", tags=["${domain}"])


${SEP}
# Module Functions
${SEP}
@router.post("", status_code=201)
async def create_${domain}(
    payload: Create${Entity}Request,
    service: Annotated[${Entity}Service, Depends(get_${domain}_service)],
    owner_id: Annotated[str, Depends(get_current_user_id)],
) -> Envelope[${Entity}View]:
    """
    Create an aggregate owned by the caller.

    :param payload: Validated request body carrying the title.
    :param service: Domain service injected by the framework.
    :param owner_id: Identity resolved from the request.
    :return: Envelope carrying the created aggregate.
    """
    entity = await service.create(owner_id=owner_id, title=payload.title)
    return Envelope[${Entity}View](
        data=${Entity}View.from_domain(entity),
        trace_id=get_trace_id(),
    )


@router.get("")
async def list_${domain}s(
    service: Annotated[${Entity}Service, Depends(get_${domain}_service)],
    owner_id: Annotated[str, Depends(get_current_user_id)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> Envelope[${Entity}List]:
    """
    List the caller's aggregates, newest first.

    :param service: Domain service injected by the framework.
    :param owner_id: Identity resolved from the request.
    :param limit: Requested page size, bounded by the query contract.
    :return: Envelope carrying one page of aggregates.
    """
    entities = await service.list_for_owner(owner_id=owner_id, limit=limit)
    page = ${Entity}List(
        items=[${Entity}View.from_domain(item) for item in entities],
    )
    return Envelope[${Entity}List](data=page, trace_id=get_trace_id())


@router.get("/{${domain}_id}")
async def get_${domain}(
    ${domain}_id: str,
    service: Annotated[${Entity}Service, Depends(get_${domain}_service)],
    owner_id: Annotated[str, Depends(get_current_user_id)],
) -> Envelope[${Entity}View]:
    """
    Return one aggregate owned by the caller.

    :param ${domain}_id: Identifier of the requested aggregate.
    :param service: Domain service injected by the framework.
    :param owner_id: Identity resolved from the request.
    :return: Envelope carrying the aggregate.
    """
    entity = await service.get(${domain}_id=${domain}_id, owner_id=owner_id)
    return Envelope[${Entity}View](
        data=${Entity}View.from_domain(entity),
        trace_id=get_trace_id(),
    )


@router.patch("/{${domain}_id}")
async def rename_${domain}(
    ${domain}_id: str,
    payload: Rename${Entity}Request,
    service: Annotated[${Entity}Service, Depends(get_${domain}_service)],
    owner_id: Annotated[str, Depends(get_current_user_id)],
) -> Envelope[${Entity}View]:
    """
    Rename an aggregate owned by the caller.

    :param ${domain}_id: Identifier of the target aggregate.
    :param payload: Validated request body carrying the new title.
    :param service: Domain service injected by the framework.
    :param owner_id: Identity resolved from the request.
    :return: Envelope carrying the updated aggregate.
    """
    entity = await service.rename(
        ${domain}_id=${domain}_id,
        owner_id=owner_id,
        title=payload.title,
    )
    return Envelope[${Entity}View](
        data=${Entity}View.from_domain(entity),
        trace_id=get_trace_id(),
    )
'''
)

TEMPLATE_REPOSITORY: Final[Template] = Template(
    '''${SEP}
# @Project: ai-assistant
# @File Path: backend/app/infrastructure/persistence/in_memory_${domain}_repository.py
# @Description: In-memory ${domain} repository used by tests and local runs
# @Creation Date: ${date}
# @Last Update: ${date}
${SEP}

${SEP}
# Import Libraries
${SEP}
# Standard Libraries
from __future__ import annotations

import asyncio
from copy import deepcopy

# Local Modules
from app.core.errors import ConflictError
from app.modules.${domain}.domain import ${Entity}


${SEP}
# Module Classes
${SEP}
class InMemory${Entity}Repository:
    """
    Store aggregates in a dict guarded by an async lock.

    Reads and writes return copies so a caller can never mutate stored state
    by accident, which is the behaviour a real database gives for free.
    """

    def __init__(self) -> None:
        """
        Start with an empty store.

        :return: ``None``, the store is ready for use.
        """
        self._items: dict[str, ${Entity}] = {}
        self._lock = asyncio.Lock()

    async def add(self, entity: ${Entity}) -> None:
        """
        Persist a newly created aggregate.

        :param entity: Aggregate to store.
        :return: ``None``, the aggregate is stored as given.
        :raises ConflictError: If the identifier is already present.
        """
        async with self._lock:
            if entity.${domain}_id in self._items:
                raise ConflictError("${domain} already exists")
            self._items[entity.${domain}_id] = deepcopy(entity)

    async def get(self, ${domain}_id: str) -> ${Entity} | None:
        """
        Return one aggregate by identifier.

        :param ${domain}_id: Identifier of the requested aggregate.
        :return: A copy of the aggregate, or ``None`` when absent.
        """
        async with self._lock:
            stored = self._items.get(${domain}_id)
            return None if stored is None else deepcopy(stored)

    async def save(self, entity: ${Entity}, *, expected_version: int) -> None:
        """
        Replace an aggregate when its stored version still matches.

        :param entity: Aggregate carrying the new state and bumped version.
        :param expected_version: Version the caller read before modifying.
        :return: ``None``, the aggregate is stored with its new version.
        :raises ConflictError: If the stored version differs.
        """
        async with self._lock:
            stored = self._items.get(entity.${domain}_id)
            if stored is None:
                raise ConflictError("${domain} does not exist")
            if stored.version != expected_version:
                raise ConflictError("${domain} was modified by another request")
            self._items[entity.${domain}_id] = deepcopy(entity)

    async def list_by_owner(self, owner_id: str, *, limit: int) -> list[${Entity}]:
        """
        Return the owner's aggregates, newest first.

        :param owner_id: Identity whose aggregates are requested.
        :param limit: Maximum number of records to return.
        :return: Copies of the matching aggregates.
        """
        async with self._lock:
            owned = [item for item in self._items.values() if item.owner_id == owner_id]
            owned.sort(key=lambda item: item.updated_at, reverse=True)
            return [deepcopy(item) for item in owned[:limit]]
'''
)

TEMPLATE_INIT: Final[Template] = Template(
    """${SEP}
# @Project: ai-assistant
# @File Path: backend/app/modules/${domain}/__init__.py
# @Description: Public exports of the ${domain} domain
# @Creation Date: ${date}
# @Last Update: ${date}
${SEP}

${SEP}
# Import Libraries
${SEP}
# Local Modules
from app.modules.${domain}.domain import ${Entity}, ${Entity}NotFoundError
from app.modules.${domain}.service import ${Entity}Service

${SEP}
# Module Constants
${SEP}
__all__ = ["${Entity}", "${Entity}NotFoundError", "${Entity}Service"]
"""
)

TEMPLATE_TEST: Final[Template] = Template(
    '''${SEP}
# @Project: ai-assistant
# @File Path: backend/tests/unit/test_${domain}_service.py
# @Description: Unit tests of the ${domain} domain rules and service
# @Creation Date: ${date}
# @Last Update: ${date}
${SEP}

${SEP}
# Import Libraries
${SEP}
# Standard Libraries
from __future__ import annotations

from datetime import datetime

# Third-Party Libraries
import pytest

# Local Modules
from app.core.errors import ValidationError
from app.infrastructure.persistence.in_memory_${domain}_repository import (
    InMemory${Entity}Repository,
)
from app.modules.${domain}.domain import (
    ${Entity},
    ${Entity}NotFoundError,
    normalize_title,
)
from app.modules.${domain}.service import ${Entity}Service

${SEP}
# Module Constants
${SEP}
OWNER_ID: str = "user-a"
OTHER_OWNER_ID: str = "user-b"


${SEP}
# Module Functions
${SEP}
def _build_service() -> ${Entity}Service:
    """
    Create a service backed by a fresh in-memory repository.

    :return: Service ready for use inside a single test.
    """
    return ${Entity}Service(InMemory${Entity}Repository())


async def test_create_returns_entity_with_initial_version() -> None:
    """
    Create an aggregate and check the defaults the domain promises.

    :return: ``None``, assertions raise on mismatch.
    """
    service = _build_service()
    entity = await service.create(owner_id=OWNER_ID, title="  first  ")
    assert entity.title == "first"
    assert entity.version == 1


async def test_create_rejects_blank_title() -> None:
    """
    Reject a title made of whitespace only.

    :return: ``None``, assertions raise on mismatch.
    """
    service = _build_service()
    with pytest.raises(ValidationError):
        await service.create(owner_id=OWNER_ID, title="   ")


async def test_get_hides_foreign_aggregate() -> None:
    """
    Return not found instead of leaking another user's aggregate.

    :return: ``None``, assertions raise on mismatch.
    """
    service = _build_service()
    created = await service.create(owner_id=OWNER_ID, title="mine")
    with pytest.raises(${Entity}NotFoundError):
        await service.get(${domain}_id=created.${domain}_id, owner_id=OTHER_OWNER_ID)


async def test_rename_bumps_version() -> None:
    """
    Rename an aggregate and confirm the version increments once.

    :return: ``None``, assertions raise on mismatch.
    """
    service = _build_service()
    created = await service.create(owner_id=OWNER_ID, title="before")
    renamed = await service.rename(
        ${domain}_id=created.${domain}_id,
        owner_id=OWNER_ID,
        title="after",
    )
    assert renamed.title == "after"
    assert renamed.version == 2


def test_normalize_title_rejects_oversized_value() -> None:
    """
    Reject a title longer than the domain limit.

    :return: ``None``, assertions raise on mismatch.
    """
    with pytest.raises(ValidationError):
        normalize_title("x" * 200)


def test_entity_rejects_naive_clock() -> None:
    """
    Reject a naive timestamp when renaming.

    :return: ``None``, assertions raise on mismatch.
    """
    moment = datetime(2026, 1, 1)
    entity = ${Entity}(
        ${domain}_id="id-1",
        owner_id=OWNER_ID,
        title="valid",
        created_at=moment,
        updated_at=moment,
    )
    with pytest.raises(ValidationError):
        entity.rename("next", now=moment)
'''
)


################################################################################
# Module Functions
################################################################################
def _pascal_case(domain: str) -> str:
    """
    Convert a snake case domain name into a class name.

    :param domain: Validated snake case domain name.
    :return: PascalCase form used for entities and errors.
    """
    return "".join(part.capitalize() for part in domain.split("_"))


def _template_values(domain: str) -> dict[str, str]:
    """
    Build the substitution table shared by every template.

    :param domain: Validated snake case domain name.
    :return: Mapping of placeholder names to replacement text.
    """
    entity = _pascal_case(domain)
    return {
        "SEP": SEPARATOR,
        "domain": domain,
        "Entity": entity,
        "ENTITY": domain.upper(),
        "date": datetime.now().strftime("%Y-%m-%d"),
    }


def _banner_break_point(value: str, width: int) -> int:
    """
    Pick the position where a long banner value wraps most naturally.

    :param value: Remaining banner value to split.
    :param width: Maximum characters that still fit on the current line.
    :return: Slice index, always between 1 and ``width``.
    """
    if len(value) <= width:
        return len(value)
    window = value[: width + 1]
    # 优先在空格、路径分隔符与下划线处断行，避免切断一个单词
    for separator in (" ", "/", "_"):
        found = window.rfind(separator)
        if found > 0:
            return found + 1
    return width


def _wrap_banner(text: str) -> str:
    """
    Continue banner values that would exceed the 80 column limit.

    :param text: Whole content of a rendered file.
    :return: Content whose banner lines all fit within 80 columns.
    """
    pattern = re.compile(r"^# (@[A-Za-z ]+?): (.*)$")
    output: list[str] = []
    for line in text.splitlines():
        match = pattern.match(line)
        if match is None or len(line) <= SECTION_WIDTH:
            output.append(line)
            continue
        # 续行保留 '#' 并用空格补齐到值的起始列，与首行值视觉对齐
        prefix = f"# {match.group(1)}: "
        remaining = match.group(2)
        width = SECTION_WIDTH - len(prefix)
        while remaining:
            cut = _banner_break_point(remaining, width)
            output.append(prefix + remaining[:cut])
            remaining = remaining[cut:]
            prefix = "# " + " " * (len(prefix) - 2)
    return "\n".join(output) + "\n"


def _render_all(domain: str, root: Path) -> dict[Path, str]:
    """
    Render every file of the new domain without touching the disk.

    :param domain: Validated snake case domain name.
    :param root: Backend directory that holds ``app`` and ``tests``.
    :return: Mapping of absolute path to file content.
    """
    # 模板与落盘位置一一对应，新增文件只需要在这张表里加一行
    values = _template_values(domain)
    module_dir = root / "app" / "modules" / domain
    plans: dict[Path, Template] = {
        module_dir / "__init__.py": TEMPLATE_INIT,
        module_dir / "domain.py": TEMPLATE_DOMAIN,
        module_dir / "ports.py": TEMPLATE_PORTS,
        module_dir / "service.py": TEMPLATE_SERVICE,
        module_dir / "schemas.py": TEMPLATE_SCHEMAS,
        module_dir / "router.py": TEMPLATE_ROUTER,
        root
        / "app"
        / "infrastructure"
        / "persistence"
        / f"in_memory_{domain}_repository.py": TEMPLATE_REPOSITORY,
        root / "tests" / "unit" / f"test_{domain}_service.py": TEMPLATE_TEST,
    }
    return {
        path: _wrap_banner(template.substitute(values))
        for path, template in plans.items()
    }


def _split_import_statements(block: str) -> list[str]:
    """
    Split an import block into complete statements, joining parentheses.

    :param block: Text of one import section without its title line.
    :return: Import statements, comments and blank lines discarded.
    """
    statements: list[str] = []
    pending: list[str] = []
    depth = 0
    for raw in block.splitlines():
        line = raw.rstrip()
        if not pending and (not line.strip() or line.lstrip().startswith("#")):
            continue
        pending.append(line)
        depth += line.count("(") - line.count(")")
        if depth <= 0:
            statements.append("\n".join(pending))
            pending = []
            depth = 0
    if pending:
        statements.append("\n".join(pending))
    return statements


def _insert_imports(text: str, new_statements: list[str]) -> str:
    """
    Insert imports into the local modules block and keep it sorted.

    :param text: Whole content of the target source file.
    :param new_statements: Import statements to add.
    :return: Content with the statements merged in alphabetical order.
    :raises ValueError: If the file has no local modules block.
    """
    marker = "# Local Modules"
    marker_at = text.find(marker)
    if marker_at < 0:
        raise ValueError("local modules block not found")
    block_start = text.find("\n", marker_at) + 1
    block_end = text.find(SEPARATOR, block_start)
    if block_end < 0:
        block_end = len(text)

    # 只重排本地模块区，其余分区原样保留
    original = text[block_start:block_end]
    existing = _split_import_statements(original)
    merged = sorted({*existing, *new_statements})
    # 原块末尾的空行数由后续语句类型决定（def 要两行、赋值要一行），原样继承
    trailing = len(original) - len(original.rstrip("\n"))
    body = "\n".join(merged) + "\n" * max(trailing, 2)
    return text[:block_start] + body + text[block_end:]


def _wire_container(root: Path, domain: str, entity: str) -> None:
    """
    Register the new service and repository in the container.

    :param root: Backend directory that holds ``app``.
    :param domain: Validated snake case domain name.
    :param entity: PascalCase entity name.
    :return: ``None``, the file is rewritten in place.
    """
    path = root / "app" / "container.py"
    text = path.read_text(encoding="utf-8")

    imports = [
        "from app.infrastructure.persistence.in_memory_"
        f"{domain}_repository import (\n    InMemory{entity}Repository,\n)",
        f"from app.modules.{domain}.service import {entity}Service",
    ]
    text = _insert_imports(text, imports)

    # 构造段插在最终 return 之前，保持每个依赖只出现一次
    anchor = "    return Container(settings=settings, chat_service=service)"
    if anchor not in text:
        raise ValueError("container return statement not found")
    built = (
        f"    {domain}_repository = InMemory{entity}Repository()\n"
        f"    {domain}_service = {entity}Service({domain}_repository)\n"
        "    return Container(\n"
        "        settings=settings,\n"
        "        chat_service=service,\n"
        f"        {domain}_service={domain}_service,\n"
        "    )"
    )
    text = text.replace(anchor, built)

    # 容器字段与文档字符串同步补齐，否则 dataclass 构造会缺参数
    field_anchor = "    chat_service: ChatService\n"
    if field_anchor not in text:
        raise ValueError("container field not found")
    text = text.replace(
        field_anchor,
        field_anchor + f"    {domain}_service: {entity}Service\n",
    )
    doc_anchor = "    :param chat_service: Service shared by every chat request.\n"
    doc_note = f"    :param {domain}_service: Service for {domain} requests.\n"
    text = text.replace(doc_anchor, doc_anchor + doc_note)
    path.write_text(text, encoding="utf-8")


def _wire_dependencies(root: Path, domain: str, entity: str) -> None:
    """
    Add the FastAPI provider that exposes the new service.

    :param root: Backend directory that holds ``app``.
    :param domain: Validated snake case domain name.
    :param entity: PascalCase entity name.
    :return: ``None``, the file is rewritten in place.
    """
    path = root / "app" / "dependencies.py"
    text = path.read_text(encoding="utf-8")
    text = _insert_imports(
        text, [f"from app.modules.{domain}.service import {entity}Service"]
    )

    # 提供者追加在模块函数区末尾，与既有 provider 并列
    provider = (
        f"\n\n\ndef get_{domain}_service(request: Request) -> {entity}Service:\n"
        '    """\n'
        f"    Provide the {domain} service to the interface layer.\n"
        "\n"
        "    :param request: Request whose application holds the container.\n"
        f"    :return: Configured {domain} service instance.\n"
        '    """\n'
        f"    return get_container(request).{domain}_service\n"
    )
    path.write_text(text.rstrip("\n") + provider, encoding="utf-8")


def _wire_main(root: Path, domain: str) -> None:
    """
    Mount the new router on the application factory.

    :param root: Backend directory that holds ``app``.
    :param domain: Validated snake case domain name.
    :return: ``None``, the file is rewritten in place.
    """
    path = root / "app" / "main.py"
    text = path.read_text(encoding="utf-8")
    text = _insert_imports(
        text, [f"from app.modules.{domain}.router import router as {domain}_router"]
    )

    anchor = "    application.include_router(chat_router, prefix=API_PREFIX)\n"
    if anchor not in text:
        raise ValueError("router mounting statement not found")
    text = text.replace(
        anchor,
        anchor
        + f"    application.include_router({domain}_router, prefix=API_PREFIX)\n",
    )
    path.write_text(text, encoding="utf-8")


def _wire_error_codes(root: Path, domain: str) -> None:
    """
    Allocate a 404 range error code for the new domain.

    :param root: Backend directory that holds ``app``.
    :param domain: Validated snake case domain name.
    :return: ``None``, the file is rewritten in place.
    :raises ValueError: If no 404 range member exists to anchor on.
    """
    path = root / "app" / "core" / "error_codes.py"
    text = path.read_text(encoding="utf-8")

    # 沿用 http_status * 100 + 序号 的编码规则，取当前 404 段最大序号加一
    matches = list(re.finditer(r"^    ([A-Z_]+) = 404(\d{2})$", text, re.MULTILINE))
    if not matches:
        raise ValueError("no 404 range error code found")
    last = matches[-1]
    sequence = max(int(match.group(2)) for match in matches) + 1
    if sequence > 99:
        raise ValueError("404 error code range exhausted")

    member = f"{domain.upper()}_NOT_FOUND"
    line = f"    {member} = 404{sequence:02d}\n"
    insert_at = last.end() + 1
    text = text[:insert_at] + line + text[insert_at:]
    path.write_text(text, encoding="utf-8")


def _write_files(plans: dict[Path, str], *, force: bool) -> None:
    """
    Write rendered files, refusing to overwrite unless forced.

    :param plans: Mapping of absolute path to content.
    :param force: Whether existing files may be replaced.
    :return: ``None``, files are created on disk.
    :raises FileExistsError: If a target exists and ``force`` is false.
    """
    for path in plans:
        if path.exists() and not force:
            raise FileExistsError(f"refusing to overwrite: {path}")

    # 先建目录再写文件，避免半途失败留下空目录树
    for path, content in plans.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def _parse_args(argv: list[str]) -> argparse.Namespace:
    """
    Parse command line arguments.

    :param argv: Arguments without the program name.
    :return: Parsed namespace.
    """
    parser = argparse.ArgumentParser(
        prog="new_module.py",
        description="Generate a compliant business domain for the project skeleton.",
    )
    parser.add_argument("domain", help="snake_case domain name, e.g. order")
    parser.add_argument(
        "--root",
        default="backend",
        help="backend directory holding app/ and tests/ (default: backend)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="overwrite existing files instead of aborting",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print the planned files without writing anything",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """
    Run the scaffold for one domain.

    :param argv: Arguments without the program name, defaults to ``sys.argv``.
    :return: Process exit code, ``0`` on success.
    :raises SystemExit: If the domain name or target layout is invalid.
    """
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    domain: str = args.domain
    root = Path(args.root).resolve()

    # 前置校验全部通过才动磁盘，避免生成一半
    if not DOMAIN_PATTERN.match(domain):
        print(f"error: '{domain}' is not snake_case ascii letters", file=sys.stderr)
        return 2
    if domain in RESERVED_DOMAINS:
        print(f"error: '{domain}' is a reserved name", file=sys.stderr)
        return 2
    if not (root / "app" / "main.py").is_file():
        print(f"error: no app/main.py under {root}", file=sys.stderr)
        return 2

    entity = _pascal_case(domain)
    plans = _render_all(domain, root)
    existing = [path for path in plans if path.exists()]
    if existing and not args.force:
        print("error: target exists, use --force:", file=sys.stderr)
        for path in existing:
            print(f"  {path}", file=sys.stderr)
        return 1

    if args.dry_run:
        for path in plans:
            print(f"would write: {path}")
        return 0

    _write_files(plans, force=args.force)
    _wire_error_codes(root, domain)
    _wire_container(root, domain, entity)
    _wire_dependencies(root, domain, entity)
    _wire_main(root, domain)

    print(f"domain '{domain}' created ({len(plans)} files)")
    for path in plans:
        print(f"  + {path.relative_to(root.parent)}")
    print()
    print("next steps:")
    print("  1. ruff check --fix . && ruff format .")
    print("  2. run the four gates: check_style.py / ruff / mypy / pytest")
    print("  3. update docs/ and add a dev-log entry (see 04-documentation)")
    return 0


################################################################################
# Script Entry Point
################################################################################
if __name__ == "__main__":
    raise SystemExit(main())
