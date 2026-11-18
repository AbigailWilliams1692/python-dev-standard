# 02 · 模块设计与工程架构规范（Engineering Design）

> 本文件定义「AI 助理」项目在**模块划分、依赖方向、设计模式、前后端边界**上的强制性约束。
> 目标可一句话概括：**让改动只发生在应该发生的地方**——新增一个 LLM 供应商只改一个文件，修改一个接口不影响业务逻辑，删除一个功能不留孤儿代码。

约定级别：**MUST** / **SHOULD** / **MAY**，含义同《01 · 代码风格规范》。

---

## 1. 设计目标与可判定标准

「高内聚、低耦合」不是口号，落地为下面 6 条**可检查**的判据：

| # | 判据 | 检查方式 | 不合格信号 |
| --- | --- | --- | --- |
| 1 | 依赖单向 | 画模块依赖图，无反向箭头 | service 导入 router、domain 导入 fastapi |
| 2 | 跨层不跳跃 | 调用链只经过相邻层 | router 直接操作 `session.execute()` |
| 3 | 接口即边界 | 跨模块只依赖对方 `__init__.py` 的公共 API | 直接 `from app.x.internal.helper import _foo` |
| 4 | 变更局部化 | 新增同类实现不改已有文件 | 加一个供应商要改 5 个 `if provider == ...` |
| 5 | 可独立测试 | 核心逻辑不启动 Web 框架即可测 | 业务函数必须先起 HTTP 服务才能跑 |
| 6 | 无循环依赖 | `import` 图是 DAG | A 导入 B，B 导入 A，靠函数内延迟导入续命 |

**核心原则优先级**（冲突时按此排序）：

```
正确性 > 可测试性 > 可读性 > 可扩展性 > 性能 > 简洁性
```

不要为「将来可能的三次扩容」预付抽象成本；也不要因为「现在只有一种实现」就硬编码（判断标准：会不会有第二种实现、会不会被替换）。

---

## 2. 分层架构（MUST）

### 2.1 四层模型

```
┌──────────────────────────────────────────────────────┐
│  Interface 层（api / routers / schemas / middleware）  │  HTTP / CLI / 消息入口
│  只做：协议转换、入参校验、鉴权、响应组装、状态码       │
└───────────────────────┬──────────────────────────────┘
                        │ 只依赖 ↓
┌───────────────────────▼──────────────────────────────┐
│  Application 层（services / use_cases）               │ 编排：事务、权限、跨域协作
│  只做：业务规则、流程编排、事务边界、领域事件发布       │
└───────────────────────┬──────────────────────────────┘
                        │ 只依赖 ↓
┌───────────────────────▼──────────────────────────────┐
│  Domain 层（domain / entities / value_objects）        │ 纯 Python，零框架依赖
│  只做：实体、值对象、领域异常、领域服务、业务不变量     │
└───────────────────────▲──────────────────────────────┘
                        │ 实现 ↓ 定义的接口（依赖倒置）
┌───────────────────────┴──────────────────────────────┐
│  Infrastructure 层（repositories / clients / llm）     │ DB、缓存、HTTP、LLM、消息队列
│  只做：技术细节实现，把外部世界翻译成领域概念           │
└──────────────────────────────────────────────────────┘
```

### 2.2 调用许可矩阵

| 调用方 ↓ / 被调方 → | Interface | Application | Domain | Infrastructure |
| --- | --- | --- | --- | --- |
| Interface | — | ✅ | ✅（只读用实体/DTO） | ❌ |
| Application | ❌ | 同层谨慎 | ✅ | ✅（仅通过接口） |
| Domain | ❌ | ❌ | ✅ | ❌ |
| Infrastructure | ❌ | ❌ | ✅（实现其接口） | ✅ |

违反表中 ❌ 即为 P1 架构缺陷。

**关键推论**：

- `domain/` **MUST NOT** 出现 `fastapi`、`sqlalchemy`、`pydantic`（`dataclass` 可用）、`httpx` 等任何框架 import。领域层可脱离整个技术栈单测。
- `api/` 层 **MUST NOT** 直接使用 `AsyncSession`、`httpx.AsyncClient`、Redis 客户端。
- `repositories/` **MUST NOT** 包含业务判断（如「VIP 才能退款」），只能做数据存取与查询组装。

### 2.3 依赖倒置的落地写法

Application 层定义端口（`Protocol`），Infrastructure 层提供实现，入口处注入：

```python
# application/ports/llm_port.py
from typing import Protocol


class LlmPort(Protocol):
    """
    Port describing the capabilities the application needs from an LLM.
    """

    async def complete(self, prompt: str, *, model: str) -> str:
        """
        Return the model completion for a single prompt.
        """


# infrastructure/llm/openai_adapter.py
class OpenAiAdapter:
    """
    Adapter implementing :class:`LlmPort` on top of the OpenAI SDK.
    """

    async def complete(self, prompt: str, *, model: str) -> str:
        """
        ...
        """


# api/deps.py
def get_llm() -> LlmPort:
    """
    Provide the configured LLM adapter as a port implementation.
    """
    return OpenAiAdapter(api_key=settings.openai_api_key)
```

好处：换供应商 = 新增 adapter + 改一行工厂；测试 = 传一个 fake 实现，不起网络。

### 2.4 分层判断速查

写代码前问自己三个问题：

1. 这段代码**知道 HTTP 吗**？知道 → Interface 层。
2. 这段代码**知道数据库 / 第三方 API 吗**？知道 → Infrastructure 层。
3. 剩下的是**业务规则** → Application（编排）或 Domain（不变量）。

---

## 3. 模块划分（Modularization）

### 3.1 按业务能力切分，不按技术类型平铺（MUST）

```
❌ 反模式：按技术分层平铺，一个业务改动横跨 6 个目录
app/
  models/       user.py, order.py, chat.py ...
  services/     user_service.py, order_service.py ...
  schemas/      user.py, order.py ...

✅ 推荐：顶层按业务域（bounded context），域内再分层
app/
  modules/
    chat/                 # 会话域
      __init__.py         # 公共 API 白名单
      router.py
      service.py
      repository.py
      schemas.py
      domain.py
    knowledge/            # 知识库 / RAG 域
    billing/              # 计费与配额域
```

判定标准：**一个新需求的 PR，改动应集中在 1–2 个目录内**。若一次需求横跨 5 个目录，说明切分维度错了。

### 3.2 模块边界规则

- **MUST** 每个模块有 `__init__.py` 且声明 `__all__`，作为唯一对外入口。
- **MUST** 跨模块引用只允许 `from app.modules.chat import ChatService`，禁止深入内部文件（`from app.modules.chat.service import ChatService` 属越界）。
- **MUST NOT** 模块之间双向依赖。需要双向通信时：
  - 上策：抽到第三个模块（共享内核），双向都依赖它；
  - 中策：由 Application 层编排两个模块；
  - 下策：领域事件解耦（见 3.4）。
- **MUST NOT** 出现「工具模块黑洞」：`utils.py` / `common.py` / `helpers.py` 超过 200 行即必须按职责拆分（`text_normalizer.py`、`retry_policy.py`）。禁止出现 `utils/utils.py`。
- **MUST NOT** 以行数作为拆分的依据；判断标准是「职责是否单一」。本规范不设文件行数上限。

### 3.3 循环依赖的处理顺序

1. 优先**重构**：把共用部分下沉到更底层模块（推荐）。
2. 其次**依赖倒置**：一方依赖 `Protocol`，实现放另一方。
3. 最后才允许函数内延迟导入，且必须注释原因；这是技术债，登记入 `docs/tech-debt.md`。

### 3.4 跨模块通信的三种手段

| 手段 | 适用 | 代价 |
| --- | --- | --- |
| 直接调用公共 API | 同步、强一致、调用方需要结果 | 引入编译期依赖 |
| 领域事件（in-process） | 一对多、调用方不关心结果 | 调试链路变长 |
| 消息队列 | 跨进程、需削峰/重试 | 运维成本、最终一致 |

**MUST** 默认用直接调用；仅当「副作用的失败不应影响主流程」时才引入事件/队列。

---

## 4. 内聚与耦合的具体手法

### 4.1 提升内聚

- **单一职责**：类名能用一句话说完，不出现 `and`。
- **信息专家原则**：数据在谁手里，行为就放谁那里。`Order.calculate_total()` 优于 `OrderCalculator.calculate(order)`（除非计算依赖外部定价服务）。
- **避免贫血模型**：领域对象只有 getter/setter 而所有逻辑堆在 service，是典型的低内聚。

### 4.2 降低耦合

| 手法 | 做法 | 收益 |
| --- | --- | --- |
| 依赖注入 | 依赖通过构造参数传入，不在内部 `new` | 可替换、可测试 |
| 面向接口 | 依赖 `Protocol` 而非具体类 | 实现可替换 |
| 参数对象 | 超过 3 个参数改传 `dataclass` / Pydantic 模型 | 签名稳定、易扩展 |
| 迪米特法则 | 只调直接朋友的公开方法，不链式穿透 `a.b().c().d()` | 减少知识扩散 |
| 配置外置 | 数值、开关、地址走配置 | 不改代码即可调参 |
| 稳定依赖原则 | 被依赖多的模块必须稳定（少变） | 降低变更涟漪 |

### 4.3 什么时候该抽象

只在以下条件**同时**满足时引入接口/基类：

1. 存在或将明确存在 ≥ 2 个实现（或测试需要 fake）；
2. 该边界会跨越进程/网络/第三方；
3. 抽象后调用方不再需要知道实现细节。

否则就是过度设计。**「只有一个实现的抽象」是负债**。

---

## 5. 后端设计模式（Backend Patterns）

### 5.1 分层内各模式的固定用法

| 模式 | 位置 | 职责边界 | 禁止 |
| --- | --- | --- | --- |
| Router / Controller | `api/` | 解析请求 → 调 service → 组装响应 | 写业务分支、碰数据库 |
| DTO / Schema | `schemas/` | 请求/响应结构与校验 | 承载业务逻辑 |
| Service | `services/` | 用例编排、事务、权限校验 | 拼 SQL、返回 ORM 对象 |
| Repository | `repositories/` | 查询组装、持久化映射 | 业务判断、提交事务 |
| Unit of Work | `core/uow.py` | 事务边界与多仓储一致性 | 长事务、跨请求持有 |
| Adapter | `infrastructure/` | 第三方/LLM/存储的防腐层 | 泄露第三方 DTO 到上层 |
| Strategy | `services/strategies/` | 多算法可替换（分块、检索、重排） | 用 `if type ==` 分支代替 |
| Factory | `*/factory.py` | 按配置/名称创建实现 | 在业务代码里 `if provider ==` |
| Middleware | `api/middleware/` | 横切关注点（trace、限流、CORS） | 写业务逻辑 |
| Observer / Event | `core/events.py` | 副作用解耦（审计、通知） | 用事件做核心流程 |

### 5.2 统一响应与错误码（MUST）

所有接口返回同一信封，前端只写一次解析逻辑：

```python
# 成功
{"code": 0, "message": "ok", "data": {...}, "trace_id": "..."}
# 失败（HTTP 状态码同时正确设置，不搞 200 包一切）
{"code": 40301, "message": "quota exceeded", "data": null, "trace_id": "..."}
```

错误码规则：`HTTP 状态码 * 100 + 业务序号`，如 `40401` = 404 类错误的第 1 个业务场景。错误码常量集中定义在 `core/error_codes.py`，禁止散落魔法数字。

### 5.3 异常体系（MUST）

```
AppError（基类，含 code / message / http_status / detail）
├── ValidationError        400xx
├── AuthenticationError    401xx
├── PermissionDeniedError  403xx
├── NotFoundError          404xx
├── ConflictError          409xx
├── RateLimitError         429xx
├── ExternalServiceError   502xx   ← LLM/第三方失败统一走这里
└── InternalError          500xx
```

- Service / Domain 只抛业务异常，**不抛** `HTTPException`（那是 Interface 层的语言）。
- Interface 层用统一 exception handler 把 `AppError` 映射为响应；未捕获异常兜底为 `InternalError` 并记录完整堆栈。
- 禁止用返回值 `None` / `False` 表达失败；失败必须有异常或显式 `Result`。

### 5.4 LLM 应用特有约束（本项目重点）

AI 助理的核心不确定性来自模型，必须做防腐与降级：

1. **模型调用统一走 Adapter**：业务代码不得直接 import `openai` / `anthropic` / `dashscope`。统一入参（messages、温度、最大 token）与出参（文本、用量、finish_reason）。
2. **超时 + 重试 + 熔断**：LLM 调用必须显式设超时（默认 30s，流式另计）、指数退避重试（仅对 429/5xx）、连续失败熔断降级。
3. **Token 与成本可观测**：每次调用记录 `model / prompt_tokens / completion_tokens / latency_ms / trace_id`，写入日志或指标表。
4. **提示词外置**：prompt 放 `prompts/*.md` 或常量模块，禁止在业务逻辑里拼长字符串；改动 prompt 视为逻辑变更，需评审。
5. **流式输出**：SSE 生成器内不得做长事务；客户端断连必须取消上游请求（`asyncio.CancelledError` 处理），避免白付 token。
6. **工具调用安全**：Agent 可调用的工具必须有白名单、参数 schema 校验、超时与副作用隔离；危险操作（写库、发消息、执行命令）需人工确认或权限门控。
7. **幂等与重放**：对话生成接口用 `request_id` 幂等，避免前端重试导致重复计费。
8. **RAG 分层**：`chunking → embedding → retrieval → rerank → generation` 各自独立可替换，用 Strategy 注册；不要在 `chat_service.py` 里内联全部逻辑。

### 5.5 分页、过滤、排序（MUST）

- 列表接口必须分页：`limit` 上限 100，默认 20；大数据量用游标分页（`cursor`）而非深 `offset`。
- 统一返回：`{"items": [...], "total": 123, "page": 1, "size": 20}` 或游标版 `{"items": [...], "next_cursor": "..."}`。
- 排序字段必须白名单映射到列，禁止把用户输入直接拼进 `order_by`。

### 5.6 幂等与并发

- 写接口涉及支付/额度/外部调用时必须支持 `Idempotency-Key`（Redis 记录 24h）。
- 并发修改用乐观锁（`version` 字段）或 `SELECT ... FOR UPDATE`，**禁止**「先查后改」裸奔。
- 任何「读-改-写」都要在事务内完成，并明确隔离级别。

---

## 6. 前端设计模式（Frontend Patterns）

> 技术栈基线：React 18 + TypeScript + Vite（Vue 3 + TS 同理，对应关系见 6.4）。

### 6.1 目录分层（MUST）

```
src/
  app/            # 应用装配：路由、providers、全局样式
  pages/          # 路由级页面，只做组合，不写业务细节
  features/       # 业务功能域（与后端模块一一对应）
    chat/
      components/     # 该域私有组件
      hooks/          # 该域数据与状态 hooks
      api.ts          # 该域接口调用
      types.ts        # 该域类型（由 OpenAPI 生成）
  components/     # 跨域通用 UI（无业务语义：Button、Modal、Table）
  lib/            # 无 UI 的通用能力（http、format、storage）
  stores/         # 全局状态（仅放真正全局的东西）
```

规则：

- **MUST** `components/` 里的组件不得 import 任何 `features/`（通用层不能依赖业务层）。
- **MUST** `pages/` 只做「取数 + 布局 + 传 props」，不做数据转换逻辑（放 hooks）。
- **MUST NOT** 出现超过 300 行的组件文件，拆分为容器 + 展示组件。

### 6.2 状态分层（MUST）

| 状态类型 | 归属 | 工具 |
| --- | --- | --- |
| 服务端状态（列表、详情、会话） | 数据请求层 | TanStack Query / SWR |
| 表单状态 | 组件内或表单库 | React Hook Form / 受控 state |
| 跨页 UI 状态（主题、侧栏、当前会话 id） | 全局 store | Zustand / Pinia |
| 局部 UI 状态 | 组件内 | `useState` |

**MUST NOT** 把服务端数据复制进全局 store 再手动同步——这是双写不一致的头号来源。

### 6.3 请求层封装（MUST）

```ts
// lib/http.ts —— 唯一出口，统一处理鉴权、错误码、trace
export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...authHeader(), ...init?.headers },
  });
  const body = await res.json();
  if (!res.ok || body.code !== 0) {
    throw new ApiError(body.code, body.message, body.trace_id);
  }
  return body.data as T;
}
```

- 组件 **MUST NOT** 直接 `fetch`，一律走 `features/*/api.ts` → `lib/http.ts`。
- 每个请求必须有 `AbortController`，组件卸载即取消。
- 错误统一在 hooks 层转成 UI 状态，不在 JSX 里 `try/catch`。

### 6.4 React / Vue 对应关系

| 关注点 | React | Vue 3 |
| --- | --- | --- |
| 组合逻辑 | 自定义 Hook | Composable (`useXxx`) |
| 状态 | Zustand | Pinia |
| 数据请求 | TanStack Query | TanStack Query / VueQuery |
| 表单 | React Hook Form | vee-validate |
| 插槽/组合 | `children` / props | slot |

### 6.5 性能红线

- 列表 > 100 项必须虚拟滚动。
- `useEffect` 依赖必须完整，禁止用空依赖掩盖逻辑错误。
- 大组件用 `React.lazy` + `Suspense` 按路由切分。
- 图片懒加载 + 明确宽高，避免布局抖动。

---

## 7. 前后端契约（Contract-First，MUST）

1. **OpenAPI 是唯一事实源**：后端 FastAPI 自动生成 `/openapi.json`，前端类型由它生成，**禁止手写重复的接口类型**。
   ```bash
   npx openapi-typescript http://localhost:8000/openapi.json -o src/features/api-types.ts
   ```
2. **字段命名统一**：JSON 一律 `snake_case`（与 Python 侧一致），前端由生成器处理，不做运行时转换。
3. **时间统一 UTC ISO 8601**：`2026-10-26T00:00:00Z`，展示层本地化。
4. **金额用整数最小单位**（分），禁止浮点；或统一字符串定点。
5. **枚举值双向同步**：后端 Enum 为源，前端由生成器产出联合类型。
6. **破坏性变更必须升版本**：路径带 `/api/v1`，字段只增不删；删除需先标记 `deprecated` 并保留一个版本周期。
7. **契约变更流程**：改 schema → 生成前端类型 → 前端编译报错驱动修改 → 联调。编译器是第一道集成测试。

---

## 8. 完整项目结构基线

```
ai-assistant/
├── AGENTS.md                     # Agent / IDE 入口规范（本套规范的指针）
├── README.md
├── pyproject.toml                # 依赖、工具链配置
├── uv.lock
├── .env.example                  # 仅示例，真实 .env 不入库
├── docker-compose.yml
├── docs/
│   ├── adr/                      # 架构决策记录 0001-xxx.md
│   ├── tech-debt.md
│   └── api.md
├── backend/
│   ├── app/
│   │   ├── main.py               # 应用装配：路由、中间件、异常处理
│   │   ├── core/                 # 跨域基础设施
│   │   │   ├── config.py         # pydantic-settings
│   │   │   ├── logging.py
│   │   │   ├── errors.py
│   │   │   ├── error_codes.py
│   │   │   └── security.py
│   │   ├── modules/              # 业务域（见 3.1）
│   │   │   ├── chat/
│   │   │   ├── knowledge/
│   │   │   └── billing/
│   │   ├── infrastructure/       # 实现层：db、llm、cache、queue
│   │   │   ├── db/
│   │   │   ├── llm/
│   │   │   └── cache/
│   │   └── shared/               # 跨域的小工具（严守 3.2 反黑洞规则）
│   ├── migrations/               # Alembic
│   └── tests/
│       ├── unit/                 # 纯逻辑，无 IO
│       ├── integration/          # 带 DB / 外部 fake
│       └── e2e/
├── frontend/
│   └── src/                      # 见 6.1
└── scripts/
    ├── check_style.py
    └── gen_openapi_types.sh
```

---

## 9. 配置与环境（12-Factor）

```python
# core/config.py
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Runtime configuration loaded from environment variables.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="forbid")

    app_env: str = "dev"
    database_url: str
    redis_url: str
    llm_provider: str = "openai"
    llm_api_key: str
    llm_timeout_seconds: int = 30
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    """
    Return the process-wide settings singleton.
    """
    return Settings()
```

规则：

- **MUST** 配置项集中声明，带类型与默认值；`extra="forbid"` 防止拼错环境变量被静默忽略。
- **MUST** 密钥、token、连接串只从环境变量读，`.env` 入 `.gitignore`，仓库只放 `.env.example`。
- **MUST** 启动时校验必需配置，缺失即 fail-fast 退出，不要跑起来才在半夜报错。
- **MUST** 环境差异（dev/test/prod）通过配置表达，代码里禁止 `if env == "prod"` 散落分支；确需分支时集中在 `core/config.py`。
- **SHOULD** 提供 `get_settings()` 单例并配合 `lru_cache`，避免每请求重复解析。

---

## 10. 数据访问与事务

- **ORM 优先**，禁止字符串拼 SQL；必须写原生 SQL 时用参数绑定，并在 PR 说明原因。
- **查询在 Repository**，Service 不出现 `select()`。
- **事务边界在 Service**（用例层），Repository 不自提交。一次用例 = 一个事务。
- **禁止在事务内做网络 IO**（调 LLM、发消息），否则长事务锁表。
- **防 N+1**：关联查询用 `selectinload` / `joinedload`；循环内禁止触发懒加载。
- **迁移必须可回滚**：每个 Alembic revision 实现 `upgrade` 与 `downgrade`；禁止在迁移里写业务逻辑。
- **软删除与唯一索引冲突**：用 `deleted_at IS NULL` 的部分唯一索引，避免删除后无法重建同名记录。
- **时间字段统一 `timestamptz`**，应用层一律用 UTC aware datetime。

---

## 11. 异步与并发边界

| 场景 | 正确做法 |
| --- | --- |
| IO 密集且库支持异步 | `async def` + `await` |
| 只有同步库（如某些 SDK） | `await asyncio.to_thread(fn, ...)` |
| CPU 密集（分词、向量计算） | `ProcessPoolExecutor` 或放到独立 worker |
| 批量调用下游 | `asyncio.gather` + `Semaphore` 限制并发 |
| 后台任务 | 轻量用 `BackgroundTasks`，可靠投递用队列 |

红线：

- `async def` 中 **MUST NOT** 出现 `time.sleep`、`requests.*`、同步 DB 驱动、大文件同步读写。
- `asyncio.gather` **MUST** 配并发上限（默认 ≤ 10），否则第三方限流直接打爆。
- **MUST NOT** 在全局变量里持有跨请求可变状态（多 worker 下不一致）。
- 取消与超时：所有外部调用必须有超时；`CancelledError` 不得被 `except Exception` 吞掉后继续执行。

---

## 12. 可观测性（Observability）

三件套的最低要求：

1. **结构化日志**：JSON 格式，必含 `timestamp / level / logger / trace_id / user_id / message`，禁止多行堆栈散落（异常用字段承载）。
2. **链路追踪**：请求入口生成 `trace_id`（或透传 `X-Trace-Id`），贯穿 service → repository → LLM adapter，日志与响应体都带上。
3. **指标**：至少覆盖 QPS、P50/P95/P99 延迟、错误率、LLM token 消耗与成本、缓存命中率。

日志级别约定：`DEBUG` 开发排查、`INFO` 关键业务节点、`WARNING` 可恢复异常、`ERROR` 需人工介入、`CRITICAL` 服务不可用。**禁止**在循环里打 `INFO`。

---

## 13. 依赖与构建

- **MUST** 用 `pyproject.toml` 声明依赖，`uv`（或 poetry）锁定，锁文件入库。
- **MUST** 区分运行时依赖与开发依赖（`[project.optional-dependencies].dev`）。
- **MUST** 依赖方向与分层一致：`core` 不依赖 `modules`，`domain` 不依赖任何第三方框架包。
- **MUST** 新增依赖前评估：维护活跃度、License、体积、是否有已知 CVE、能否用标准库替代。
- **SHOULD** 依赖数量保持克制；每季度跑一次 `pip-audit` 与 `pip list --outdated`。
- **MUST NOT** 引入已停止维护或存在未修复高危 CVE 的包。

---

## 14. 测试策略

| 层级 | 占比 | 范围 | 依赖 |
| --- | --- | --- | --- |
| 单元测试 | ~70% | domain、纯函数、service（mock 端口） | 无 IO |
| 集成测试 | ~25% | repository、router + 测试数据库 | 容器化 DB / fake 外部服务 |
| 端到端 | ~5% | 关键用户路径 | 完整环境 |

规则：

- 核心业务逻辑覆盖率 ≥ 80%，`domain/` 与 `services/` 为强制项。
- 每个 bug 修复必须先补一个能复现的失败用例，再修。
- 测试不得依赖执行顺序、真实外网、共享可变数据库状态。
- 外部服务一律用 fake/契约测试，不在单测里打真实 LLM（成本 + 不确定性）。

---

## 15. 演进与技术债

- **ADR（架构决策记录）**：任何影响多模块的决策（选型、分层调整、协议变更）写 `docs/adr/NNNN-title.md`，含背景、候选方案、决策、后果。**改架构不写 ADR 视为不合规**。
- **技术债登记**：`docs/tech-debt.md` 表格化（位置 / 影响 / 触发条件 / 偿还计划），禁止只存在于某人的记忆里。
- **废弃流程**：标记 `@deprecated` + 日志告警 + 文档说明，至少保留一个版本周期再删。
- **重构纪律**：重构与功能变更分开提交；重构前必须有测试护栏。

---

## 16. 架构评审清单（PR 必查）

- [ ] 新代码落在正确的层，无跨层调用（对照 2.2 矩阵）
- [ ] `domain/` 无框架依赖
- [ ] 跨模块引用走 `__init__.py` 公共 API，无深度导入
- [ ] 无新增循环依赖（含延迟导入绕过）
- [ ] 新增实现是否走工厂/注册表，而非新增 `if provider ==`
- [ ] 配置项集中在 `Settings`，无硬编码地址/密钥/阈值
- [ ] 事务边界在 service，事务内无网络 IO
- [ ] 外部调用有超时、重试、并发上限
- [ ] 接口契约变更已同步 OpenAPI 与前端类型，未做破坏性删除
- [ ] 错误走统一异常体系与错误码，未返回 `None` 表达失败
- [ ] 关键路径有测试，覆盖率未下降
- [ ] 影响架构的决策已写 ADR

---

## 17. 常见架构反模式（对照自查）

| 反模式 | 症状 | 修法 |
| --- | --- | --- |
| 万能 Service | 一个 `service.py` 2000 行，什么都做 | 按用例拆分为多个 service，或引入领域对象 |
| 贫血模型 | 实体只有字段，逻辑全在 service | 把不变量与状态转换移入实体 |
| 分层漏勺 | Router 里直接写 SQL | 下沉到 repository |
| 工具黑洞 | `utils.py` 无限膨胀 | 按职责拆分 |
| 抽象成瘾 | 每个类都有接口 + 工厂 + 单实现 | 删除多余抽象，直接依赖具体类 |
| 配置散落 | `if env == "prod"` 出现在 10 个文件 | 收敛到 Settings |
| 双写状态 | DB 与缓存分别写、无失效策略 | 单一写入源 + cache-aside |
| 隐式依赖 | 函数内部 `import` 全局单例 | 显式构造注入 |
| 事件滥用 | 简单调用也发事件，链路难追 | 默认直接调用 |
| 契约漂移 | 前端手写类型、与后端不一致 | OpenAPI 生成 |

---

## 18. 落地顺序建议（新项目）

1. 先定目录骨架与分层（第 8 节）——**第一天就要定，后改成本最高**。
2. 再定 `Settings`、日志、异常体系、统一响应（这三样是所有模块的地基）。
3. 然后实现第一个业务域，跑通「router → service → repository → adapter」全链路，作为范式样板。
4. 补测试骨架与 CI 门禁（ruff / mypy / pytest / check_style）。
5. 之后再复制范式扩展业务域；**每个新域必须与样板结构一致**，差异要写 ADR。

---

## 19. 新增一个业务域的标准动作

**不要手抄 chat 目录。** 手抄的失败率很高：漏 `ports.py`、忘在 router 挂 `Envelope`、
忘在 `container` 注册、忘加错误码，每一项都要等到运行时才炸。用脚手架生成，再改业务。

### 19.1 十步

```bash
# 1. 生成骨架：8 个文件 + 4 处自动接线（container / dependencies / main / error_codes）
python .workbuddy/skills/python-dev-standard/scripts/new_module.py order

# 2. 立刻验证起点是绿的，此时任何红灯都是环境问题而不是业务问题
python .workbuddy/skills/python-dev-standard/scripts/check_style.py backend/
python .workbuddy/skills/python-dev-standard/scripts/check_architecture.py backend
ruff format --check . && ruff check . && mypy && pytest -q

# 3~7. 依次改五层，顺序固定：模型 → 端口 → 用例 → 契约 → 路由
#      先改模型，是因为后面四层都围着它转；反过来做会返工。

# 8. 补测试：不变量、越权、并发冲突，三个方向各至少一条
# 9. 重跑第 2 步的全部命令
# 10. 更新 docs/：architecture.md 的模块表、entities.md、data-flow.md、dev-log.md
```

`--dry-run` 只打印不写盘，`--force` 允许覆盖，域名必须是 snake_case 英文（拼音与保留字会被拒）。

### 19.2 脚手架自动产出的内容

| 产出 | 文件 | 说明 |
| --- | --- | --- |
| 领域模型 | `app/modules/<domain>/domain.py` | 实体 + 不变量 + 领域异常 |
| 端口 | `app/modules/<domain>/ports.py` | `<Entity>Repository` 协议，含乐观锁签名 |
| 用例 | `app/modules/<domain>/service.py` | create / get / list / rename，越权统一 404 |
| 契约 | `app/modules/<domain>/schemas.py` | 请求、响应、分页视图 |
| 路由 | `app/modules/<domain>/router.py` | 4 个端点，统一 `Envelope` 包装 |
| 适配器 | `app/infrastructure/persistence/in_memory_<domain>_repository.py` | 带锁与深拷贝的内存实现 |
| 导出 | `app/modules/<domain>/__init__.py` | `__all__` 明确公共面 |
| 测试 | `backend/tests/unit/test_<domain>_service.py` | 6 条用例，覆盖不变量与越权 |
| 接线 | `container.py` / `dependencies.py` / `main.py` / `error_codes.py` | 自动插入并保持 import 有序 |

生成物**零改动即可通过五道门**（`check_style` / `check_architecture` / `ruff` / `mypy` / `pytest`）。
这一点是刻意的：起点必须是绿的，否则业务改动与格式改动混在一起，review 时无法分辨。

### 19.3 生成后必须手工改的四处

脚手架只能给形状，语义必须自己填：

1. **实体字段**——`title` / `created_at` / `version` 是通用占位。真实域通常要状态枚举、
   金额用 `Decimal` 而不是 `float`、时间字段区分「创建」「生效」「过期」。
2. **仓储方法**——`list_by_owner` 的排序键与过滤条件。脚手架按 `updated_at` 倒序，
   真实业务可能是「按截止时间正序 + 只取未完成」。
3. **错误码语义**——`<DOMAIN>_NOT_FOUND` 只覆盖了「不存在」。业务冲突（重复下单、
   状态不允许流转）需要新的 `409xx` 码，并同步 `docs/ux.md` 的文案表。
4. **文档**——`architecture.md` 的模块表、`entities.md` 的不变量与状态机、
   `data-flow.md` 的新数据流、`dev-log.md` 的条目。**同 PR 完成，不许留到下一轮。**

### 19.4 不该做的事

| 反模式 | 为什么不行 |
| --- | --- |
| 保留 chat 的 LLM 依赖 | 新域大多不需要模型调用，多余的端口会让 service 构造函数越滚越大 |
| 「以后可能用到」就先加端口 | 单实现的抽象是纯成本，等真有第二个实现再加 |
| 跨域 `from app.modules.other.service import X` | 绕过契约。`check_architecture.py` 会拦，正解是走对方的 `ports` 或提公共能力到 `core` |
| 在 router 里写业务判断 | 分支一旦进路由，就无法被单元测试覆盖，也无法被其他入口复用 |
| 生成后不跑架构检查 | 分层是唯一无法靠肉眼稳定守住的规则，必须机器兜底 |

### 19.5 完成判定

- [ ] 五道门全绿，包括 `check_architecture.py`。
- [ ] 越权访问返回「不存在」而不是「无权限」，且没有泄露资源存在性。
- [ ] 并发写有乐观锁保护，冲突返回 `409`。
- [ ] 列表接口有上界（`limit <= MAX_PAGE_SIZE`），不会一次拉全表。
- [ ] `docs/` 四份文档与 `dev-log.md` 已在同一 PR 更新。
- [ ] 没有把新域的任何内部实现暴露到 `__init__.py` 的 `__all__` 之外。
