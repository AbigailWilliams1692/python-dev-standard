# 03 · 质量、安全与流程规范（Quality & Process）

> 前两份文件管「长什么样」和「怎么切分」，本文件管「怎么保证它对、它安全、它可维护」。  
> 适用于所有 Python 代码、配置、脚本与提交。

---

## 1. 类型系统的纵深用法

### 1.1 类型标注的三个层级

| 层级  | 目的        | 手段                             |
| --- | --------- | ------------------------------ |
| 静态层 | 写代码时发现错误  | `mypy --strict` / pyright      |
| 边界层 | 运行时校验外部输入 | Pydantic / 显式校验                |
| 语义层 | 让非法状态不可表达 | `Literal`、`Enum`、`NewType`、值对象 |

**关键认知**：类型标注不替代运行时校验。来自 HTTP、消息队列、文件的 `dict` / `json` **MUST** 先经 Pydantic 校验再使用。

### 1.2 让非法状态不可表达的写法

```python
from enum import StrEnum
from typing import NewType

UserId = NewType("UserId", int)  # 防止把任意 int 当 id 传入
OrderNo = NewType("OrderNo", str)


class OrderStatus(StrEnum):
    """
    Lifecycle states of an order.
    """

    DRAFT = "draft"
    PAID = "paid"
    SHIPPED = "shipped"


def ship(order_id: UserId, status: OrderStatus) -> None:
    """
    ...
    """
```

### 1.3 边界校验模板

```python
from pydantic import BaseModel, Field, field_validator


class CreateChatRequest(BaseModel):
    """
    Payload for creating a chat session.
    """

    title: str = Field(min_length=1, max_length=120)
    model: str = Field(default="gpt-4o-mini", max_length=64)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str) -> str:
        """
        Trim surrounding whitespace and reject blank titles.
        """
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("title must not be blank")
        return cleaned
```

规则：

- 数值必须有上下界（`ge` / `le`），字符串必须有长度限制，列表必须有元素上限。
- 禁止把 `dict[str, Any]` 作为接口入参一路传到底层。
- 校验失败的信息要能让调用方定位字段，不能只说「参数错误」。

---

## 2. 异常处理规范

### 2.1 四条硬规则

1. **MUST** 捕获具体异常类型；`except Exception` 仅允许出现在最外层兜底（全局异常处理器 / 任务调度器），且必须记录完整堆栈。
2. **MUST NOT** 空 `except` 块；至少 `logger.exception(...)` 并决定「重抛 / 转换 / 降级」三选一。
3. **MUST** 异常转换用 `raise NewError(...) from exc` 保留链；禁止 `raise NewError(...)` 裸抛丢失现场。
4. **MUST NOT** 用异常做正常控制流（如用 `KeyError` 判断 key 存在）。

### 2.2 分层异常语义

| 层              | 可抛出的异常                                   | 禁止                            |
| -------------- | ---------------------------------------- | ----------------------------- |
| Domain         | 领域异常（`InsufficientQuotaError`）           | 框架异常、IO 异常                    |
| Infrastructure | 转换为领域/应用异常的原始异常，或 `ExternalServiceError` | 把 `httpx.ConnectError` 直接冒到上层 |
| Application    | 业务异常 + 转为 `ExternalServiceError`         | `HTTPException`               |
| Interface      | 由 handler 统一映射为响应                        | 业务判断                          |

### 2.3 重试与降级的正确位置

```python
# 仅对可重试错误（429/5xx/超时）做指数退避，业务错误不重试
async def call_with_retry(
    operation: Callable[[], Awaitable[T]], *, attempts: int = 3
) -> T:
    """
    Execute an async operation with exponential backoff on transient errors.
    """
    for attempt in range(1, attempts + 1):
        try:
            return await operation()
        except (TimeoutError, TransientUpstreamError) as exc:
            if attempt == attempts:
                raise ExternalServiceError("upstream unavailable") from exc
            await asyncio.sleep(2**attempt * 0.1)
    raise AssertionError("unreachable")
```

- 重试**必须**有上限 + 退避 + 抖动；禁止紧密循环重试。
- 非幂等操作**禁止**自动重试（或用幂等键保护）。
- 重试层级只允许一处（不要在 adapter 和 service 里各重试一次，导致 9 次调用）。

---

## 3. 日志规范

### 3.1 结构

- **MUST** 生产环境输出 JSON（便于采集），开发环境可用可读格式。
- **MUST** 每条日志携带 `trace_id`（通过 `contextvars` 注入，避免逐层传参）。
- **MUST** 用 `%s` 惰性参数化，禁止 f-string 预格式化（否则禁用级别下仍付字符串拼接成本，且不利于脱敏）。

### 3.2 级别使用

| 级别       | 使用场景        | 示例               |
| -------- | ----------- | ---------------- |
| DEBUG    | 开发排查、变量快照   | 查询参数、缓存 key      |
| INFO     | 关键业务节点、状态迁移 | 会话创建、任务完成、用量统计   |
| WARNING  | 可恢复异常、降级、重试 | 缓存失效降级查库、重试第 2 次 |
| ERROR    | 需人工介入的失败    | 第三方持续失败、数据不一致    |
| CRITICAL | 服务不可用       | 数据库连接池耗尽、配置缺失    |

### 3.3 脱敏（MUST）

以下字段**禁止**进入日志、异常消息、响应体：

```
password / passwd / secret / token / api_key / authorization
cookie / session_id / 完整手机号 / 身份证号 / 银行卡号 / 完整邮箱（可保留域名）
```

实现方式：统一 `MaskingFilter` 在 handler 层按 key 名脱敏（`token=***`、`phone=138****8000`），而不是靠每个开发者记得。

```python
SENSITIVE_KEYS: frozenset[str] = frozenset(
    {"password", "token", "api_key", "authorization"}
)
```

- 异常堆栈可能包含请求体，**MUST** 在上报前过一遍脱敏。
- **MUST NOT** `logger.info(f"user={user}")` 打印整个 ORM 对象（可能含敏感字段）。

---

## 4. 安全规范

### 4.1 OWASP 对应清单

| 风险         | Python 侧要求                                                          |
| ---------- | ------------------------------------------------------------------- |
| 注入         | SQL 只用参数化/ORM；`subprocess` 用列表参数 + `shell=False`；模板渲染关闭自动转义豁免       |
| 认证失效       | 密码用 `argon2` / `bcrypt`（禁止 md5/sha1/裸 sha256）；JWT 校验签名+过期+受众；会话可撤销  |
| 越权（IDOR）   | 每个查询必须带 `owner_id` / `tenant_id` 条件，**禁止**只按资源 id 查；权限校验在 service 层 |
| 敏感数据泄露     | 密钥走环境变量；HTTPS 强制；响应按 DTO 白名单输出，禁止直接序列化 ORM                          |
| XXE / 反序列化 | 禁用 `pickle`/`yaml.load`（用 `safe_load`）处理外部数据；XML 解析禁用外部实体           |
| SSRF       | 用户提供的 URL 必须白名单域名或校验解析后 IP 不在内网段                                    |
| 文件上传       | 校验扩展名 + MIME + magic number + 大小上限；存储用随机文件名；禁止落到可执行目录               |
| 依赖漏洞       | `pip-audit` 入 CI；高危 CVE 阻断合入                                        |
| 日志与错误泄露    | 生产不返回堆栈；错误信息不含内部路径与 SQL                                             |

### 4.2 密钥管理

- **MUST NOT** 代码、测试、示例、注释、Dockerfile、CI 配置里出现真实密钥。
- `.env` 入 `.gitignore`；仓库只放 `.env.example`（占位值）。
- 一旦误提交：**立即轮换**（视为已泄露），而不是仅删 commit。
- 生产环境用密钥管理服务或平台注入的环境变量，不落磁盘明文。

### 4.3 鉴权实现要点

```python
# 资源级权限校验必须在 service 层，且以「当前用户」为查询条件之一
async def get_chat_session(session_id: int, current_user: User) -> ChatSession:
    """
        Return a chat session owned by ``current_user``.

    :raises PermissionDeniedError: If the session belongs to another user.
    """
    session = await self._repository.find_by_id(session_id)
    if session is None:
        raise NotFoundError("chat session not found")
    if session.owner_id != current_user.id:
        # 不暴露资源存在性：越权与不存在返回同一个错误，只记审计日志
        logger.warning(
            "cross-tenant access blocked user_id=%s session_id=%s",
            current_user.id,
            session_id,
        )
        raise NotFoundError("chat session not found")
    return session
```

- **MUST** 先判存在再判归属，但对外错误信息不得区分「不存在」与「无权限」（避免枚举探测）。
  实现上二者返回**同一个错误码**（通常按「不存在」处理）；`PermissionDeniedError` 留给
  「身份已验证、但操作本身被禁止」的场景（如普通用户调用管理接口）。
- **MUST** 敏感操作（删除、导出、改密）写审计日志：操作者、目标、时间、结果、IP。

### 4.4 输入与输出

- 所有外部输入视为不可信：长度、类型、范围、枚举、格式全部校验。
- 输出走 DTO 白名单（`response_model`），**禁止**返回 ORM 实体（会泄露字段并触发懒加载）。
- 富文本 / Markdown 渲染必须做 XSS 过滤（前端 `DOMPurify` 或后端白名单渲染）。
- 请求体大小、文件大小、分页大小必须有硬上限，防止内存打爆。

---

## 5. 性能红线

| 项      | 红线                           | 检查手段                     |
| ------ | ---------------------------- | ------------------------ |
| N+1 查询 | 列表接口查询次数不随条目数线性增长            | SQL 日志计数                 |
| 循环内 IO | 禁止在循环内做 DB/HTTP/文件操作         | Code Review              |
| 全量加载   | 大结果集必须分页/流式                  | 代码审查 + 压测                |
| 索引     | 高频查询条件必须有索引                  | `EXPLAIN`                |
| 缓存     | 热点读必须走缓存，且防穿透/击穿/雪崩          | 命中率指标                    |
| 异步阻塞   | `async` 中无同步阻塞调用             | `asyncio.debug` + Review |
| 内存     | 禁止无界缓存、无界队列、无界 `list` 累积     | `tracemalloc` / 压测       |
| 序列化    | 大对象避免重复 `model_dump()` / 深拷贝 | profiler                 |

**优化纪律**：先测量（`cProfile` / `py-spy` / `EXPLAIN`）再动手，**禁止**凭直觉优化；每次优化必须给出前后对比数据（QPS、P99、内存峰值）。

---

## 6. 测试规范

### 6.1 目录与命名

```
tests/
├── conftest.py            # 全局 fixture
├── unit/                  # 纯逻辑，无 IO
│   └── modules/chat/test_quota_service.py
├── integration/           # 带 DB / fake 外部
└── e2e/
```

- 文件名 `test_<被测模块>.py`；函数名 `test_<行为>_<条件>`，如 `test_fetch_user_raises_when_not_found`。
- **MUST** 一个测试只断言一个行为；断言消息要能说明失败原因。

### 6.2 fixture 规范

```python
import pytest
from collections.abc import AsyncIterator
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    """
    Provide a transactional session rolled back after each test.
    """
    async with session_factory() as session:
        async with session.begin():
            yield session
            await session.rollback()
```

- **MUST** 测试间零共享状态：数据库用事务回滚或独立 schema，禁止依赖执行顺序。
- **MUST** 外部依赖用 fake / 契约替身，不在单测里打真实 LLM 或真实支付。
- **MUST NOT** fixture 里做重量级全局初始化（拖慢整个套件）；用 `scope="session"` 显式声明并说明理由。

### 6.3 参数化与边界

```python
@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("0", 0),
        (" 12 ", 12),
        ("-3", -3),
    ],
)
def test_parse_int_accepts_valid_input(raw: str, expected: int) -> None:
    """
    ...
    """


@pytest.mark.parametrize("raw", ["", "abc", "1.5", None])
def test_parse_int_rejects_invalid_input(raw: str | None) -> None:
    """
    ...
    """
```

必测的边界：空、`None`、0、负数、超大值、超长字符串、Unicode/emoji、时区跨越、并发重复提交。

### 6.4 覆盖率与门禁

- 核心逻辑（`domain/`、`services/`）≥ 80%，整体 ≥ 70%。
- 覆盖率下降的 PR 不得合入（CI 比较基线）。
- **禁止**为凑覆盖率写无断言的测试（`assert True`）。

### 6.5 测试反模式

| 反模式            | 问题                |
| -------------- | ----------------- |
| 测试依赖真实外网       | 不稳定、慢、有费用         |
| 一个测试断言 10 件事   | 失败无法定位            |
| mock 到内部实现细节   | 重构即碎，测试变成实现副本     |
| 只测 happy path  | 边界 bug 全部漏网       |
| `sleep` 等待异步结果 | 慢且偶发失败，应轮询条件或注入时钟 |

---

## 7. 依赖与供应链

- `pyproject.toml` 为唯一依赖声明处，禁止散落 `requirements.txt`（如有需要由工具导出）。
- 锁定文件（`uv.lock` / `poetry.lock`）必须入库。
- CI 每周跑 `pip-audit`；高危 CVE 阻断发布。
- 新增依赖需在 PR 描述中回答：解决什么问题、为何不用标准库、License、维护状态、包体积。
- **MUST NOT** 从非官方源安装包；私有源需配置凭证但不得写入仓库。

---

## 8. Git 与协作

### 8.1 提交信息（Conventional Commits）

```
<type>(<scope>): <subject>

<body 可选：为什么这么改>

<footer 可选：BREAKING CHANGE / refs>
```

`type` 取值：`feat` `fix` `refactor` `perf` `test` `docs` `build` `ci` `chore` `style`。  
`scope` 用模块名：`chat`、`billing`、`knowledge`。

示例：

```
feat(chat): add streaming response with cancellation support

Cancel upstream LLM request when the client disconnects to avoid
paying for tokens nobody reads.

Refs: #128
```

规则：

- 一个提交做一件事；重构与功能变更**必须**分开。
- 禁止 `update`、`fix bug`、`修改` 这类无信息量的 subject。
- subject ≤ 72 字符，英文，祈使句，结尾不加句号。

### 8.2 分支与合并

- 主干 `main` 始终可发布；功能分支 `feat/<scope>-<short-desc>`。
- 合并前必须：CI 全绿 + 至少 1 人 Review + 无未解决评论。
- 禁止直接 push 到 `main`；禁止 `--force` 推送到共享分支。
- PR 粒度：≤ 400 行改动（不含生成代码与测试数据）；超出需拆。

### 8.3 PR 描述模板

```markdown
## 变更内容
- 一句话说明做了什么

## 为什么
- 解决的问题 / 关联 issue

## 影响面
- [ ] 数据库迁移（如有，附 downgrade 方案）
- [ ] 接口契约变更（已同步前端类型）
- [ ] 配置项新增（已更新 .env.example）
- [ ] 依赖新增（已说明理由）

## 自测
- [ ] 单测 / 集成测试通过
- [ ] ruff / mypy / check_style 通过
- [ ] 手动验证路径：...
```

### 8.4 Code Review 分级

| 级别    | 含义               | 处理        |
| ----- | ---------------- | --------- |
| P0 阻断 | 安全漏洞、数据丢失、明确逻辑错误 | 必须改完才能合   |
| P1 严重 | 性能瓶颈、异常未处理、架构越界  | 强烈建议本次改   |
| P2 建议 | 可维护性、命名、重复代码     | 可另开 issue |
| P3 提示 | 风格细节、微优化         | 可选        |

输出格式：

```
### [P1] 循环内发起数据库查询导致 N+1
- 位置：app/modules/chat/service.py:88
- 问题：for 循环里逐条调用 repository.find_by_id
- 影响：会话 50 条消息即产生 50 次查询，P99 从 120ms 涨到 900ms
- 建议：改为 find_by_ids(ids) 批量查询，再在内存做映射
```

---

## 9. 文档要求

| 文档     | 位置                   | 何时必须写                  |
| ------ | -------------------- | ---------------------- |
| README | 根目录                  | 项目初始化；含启动步骤、环境变量表、目录说明 |
| ADR    | `docs/adr/NNNN-*.md` | 任何跨模块的技术决策             |
| 接口文档   | 由 OpenAPI 自动生成       | 随代码更新，不手写              |
| 技术债清单  | `docs/tech-debt.md`  | 每个已知妥协                 |
| 运维手册   | `docs/runbook.md`    | 上线前；含部署、回滚、常见故障处理      |

**禁止**写「注释式文档」：README 里贴大段代码、docstring 复述签名。

---

## 10. CI 门禁（MUST 全绿才可合入）

```yaml
# 质量门禁顺序：快 → 慢，失败尽早暴露
1. ruff format --check .          # 格式
2. ruff check .                   # Lint（含命名、docstring、安全规则）
3. mypy app/                      # 类型
4. python scripts/check_style.py  # 项目自定义规范（banner/分区/命名）
5. pytest --cov=app --cov-fail-under=70
6. pip-audit                      # 依赖漏洞
```


```

`pre-commit` 至少挂 1–3 与 4，把问题拦在提交前。

---

## 11. 交付前总清单（三份规范合并版）

### 结构
- [ ] 文件 banner 完整，路径/日期正确
- [ ] 分区顺序正确，分隔线 80 列
- [ ] 类内区块顺序正确，无空区块

### 风格
- [ ] 命名全英文，无拼音、无类型后缀、无遮蔽内置
- [ ] 所有函数/类有 reST docstring（描述 + param + return + raises）
- [ ] 所有参数与返回值有类型标注
- [ ] 函数体按逻辑分块，每块前有说明注释
- [ ] 无第 9 节列出的任一反模式

### 设计
- [ ] 代码在正确的层，无跨层调用
- [ ] 无新增循环依赖
- [ ] 可扩展点用工厂/策略，未新增 `if type ==`
- [ ] 配置集中在 Settings，无硬编码

### 正确性与安全
- [ ] 边界处理完整（空/None/极值/超长/并发）
- [ ] 异常具体捕获，未吞异常，转换保留异常链
- [ ] SQL 参数化，无命令拼接
- [ ] 无密钥硬编码，日志已脱敏
- [ ] 资源用 `with` / `finally` 释放
- [ ] 外部调用有超时 + 重试上限 + 并发上限

### 验证
- [ ] 新增/修改逻辑有测试，覆盖边界与异常路径
- [ ] 本地跑通 `ruff` / `mypy` / `pytest` / `check_style.py`
- [ ] PR 描述填写完整（含影响面与回滚方案）

---

## 12. 常见「看起来没问题」的隐患

| 隐患 | 为什么危险 | 正确做法 |
| --- | --- | --- |
| `datetime.now()` | 无时区，跨服务器不一致 | `datetime.now(timezone.utc)` |
| `float` 存金额 | 精度丢失 | 整数分 / `Decimal` |
| `len(x) == 0` | 非 Pythonic 且对自定义容器可能低效 | `if not x:` |
| `dict.get(k)` 后立刻用 | `None` 与「不存在」混淆 | `if k in d` 或 `sentinel` |
| 用 `str` 传枚举 | 拼错不报错 | `Enum` / `Literal` |
| 宽泛 `try` 包整段 | 掩盖真实缺陷 | 只包可能失败的最小语句 |
| 静默截断长文本 | 用户不知情、数据失真 | 校验长度并显式报错 |
| 缓存无 TTL | 脏数据永不过期 | 统一 TTL + 主动失效 |
| 时间戳做分页游标无唯一性 | 同秒数据丢失或重复 | 复合游标 `(created_at, id)` |
| 多 worker 内存缓存 | 状态不一致 | 用 Redis 或改为进程无关设计 |

---

## 13. 三条后续动作

1. **先跑通门禁**：把第 10 节的 6 条命令接进 CI，再开始写业务代码——规范才有牙齿。
2. **补一个范式样板**：选 `chat` 域完整实现一遍四层链路，作为后续复制模板。
3. **定期复查**：每两周跑一次 `ruff` / `mypy` / `pip-audit` 全量报告，把技术债登记进 `docs/tech-debt.md`。
```
