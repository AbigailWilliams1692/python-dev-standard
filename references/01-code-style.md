# 01 · Python 代码风格规范（Code Style）

> 本文件是「AI 助理」项目的代码风格唯一事实源（Single Source of Truth）。  
> 基线：PEP 8 + Google Python Style Guide；在此之上叠加本项目的强约束。  
> 约定级别：**MUST**（违反即不合格，Review 直接打回）/ **SHOULD**（默认遵守，偏离需注释说明理由）/ **MAY**（可选）。

**适用范围**：`backend/`、`scripts/`、`tests/` 下全部 `.py` 文件，以及任何以 Python 交付的脚本、工具、迁移文件。

---

## 0. 十条铁律（先记这个）

| #  | 铁律                                                       |
| -- | -------------------------------------------------------- |
| 1  | 标识符全部使用英文单词，**禁止拼音、禁止中英混拼、禁止无意义缩写**                      |
| 2  | 每个 `.py` 文件首部必须有 80 列 banner，五个字段一个不能少；字段值超长时按 80 列换行对齐  |
| 3  | 文件按 Import → Constants → Functions/Classes 分区，分隔线一律 80 列 |
| 4  | 每个函数 / 类必须有 reST docstring，首行只写 `"""`，描述从第二行开始，含参数、返回、异常 |
| 5  | 每个参数与返回值必须标注类型，确实无法确定用 `Any` 并注明原因                       |
| 6  | 函数体内按逻辑分块，每块前写一行注释说明在做什么                                 |
| 7  | 类内部固定区块顺序，区块用 80 列分隔线切开                                  |
| 8  | 禁裸 `except`、禁吞异常、禁 `import *`、禁可变默认参数                    |
| 9  | 禁硬编码密钥 / 连接串 / 口令，一律走环境变量或配置                             |
| 10 | 交付前必须通过 `ruff` + `mypy` + `scripts/check_style.py` 三道检查  |

---

## 1. 文件骨架（File Skeleton）

### 1.1 banner（MUST）

每个 `.py` 文件第 1 行起必须是如下结构，上下边界均为**恰好 80 个 `#`**：

```python
################################################################################
# @Project: ai-assistant
# @File Path: backend/app/services/user_service.py
# @Description: User CRUD business logic and permission checks
# @Creation Date: 2026-10-26
# @Last Update: 2026-10-26
################################################################################
```

**字段值超长时必须换行**，续行以 `#` 开头，并用空格把文字对齐到该字段值的起始列：

```python
################################################################################
# @Project: ai-assistant
# @File Path: .workbuddy/skills/python-dev-standard/assets/
#             module_template.py
# @Description: Reference module demonstrating every
#               mandatory code style rule
# @Creation Date: 2026-10-26
# @Last Update: 2026-10-26
################################################################################
```

对齐列的算法：字段值从 `# @Field: ` 之后开始。`@File Path` 的前缀是 14 列，值从第 15 列开始，  
续行就写 `#` + 13 个空格；`@Description` 的前缀是 16 列，续行写 `#` + 15 个空格。  
换行后**每一行都不得超过 80 列**，续行不再重复字段名。

字段规则：

| 字段               | 取值规则                                     |
| ---------------- | ---------------------------------------- |
| `@Project`       | 与 `pyproject.toml` 的 `name` 一致，小写短横线风格   |
| `@File Path`     | **相对项目根目录**的 POSIX 路径（用 `/`），不用盘符、不用绝对路径 |
| `@Description`   | 一句话英文描述，说明该模块**职责**而非实现细节；超长换行，不缩略    |
| `@Creation Date` | 首次创建日期，格式 `YYYY-MM-DD`，创建后不再修改           |
| `@Last Update`   | 最近一次实质修改日期，格式 `YYYY-MM-DD`，每次改动同步更新      |

补充约束：

- **MUST** banner 内任何一行都不得超过 80 列；字段值超长时按 1.1 的规则换行，不得压缩字段名、不得省略内容。
- **MUST** 列顺序固定，不得增删字段、不得改变字段名拼写（含冒号后的单空格）。
- **MUST** 若为可执行脚本（含 `if __name__ == "__main__":`），shebang 放在 banner **之上**第 1 行：
  ```python
  #!/usr/bin/env python3
  ##############################################################################
  # @Project: ai-assistant
  ...
  ```
- **MUST NOT** 再写模块级 docstring（`"""..."""`）。banner 的 `@Description` 已承担该职责，重复属于冗余。对应地在 lint 配置中忽略 `D100`。
- **MUST** banner 与之后第一个分区之间空 **1 行**。

### 1.2 模块分区与顺序（MUST）

分区顺序固定，缺项可省略但不得乱序：

```
banner
  ↓
Import Libraries            ← 必选（最少也要有空行占位说明）
  ↓
Module Constants            ← 有常量才写
  ↓
Type Aliases / Enums        ← 有才写（TypedDict、Literal 别名、Enum）
  ↓
Module-level Logger / Config 实例   ← 有才写
  ↓
Functions / Classes         ← 主体
  ↓
if __name__ == "__main__":  ← 仅脚本
```

分隔线写法（**Level 1**，模块级，顶格）：

```python
################################################################################
# Import Libraries
################################################################################
```

规则：

- **MUST** 分隔线为 80 个 `#`，不得多也不得少（编辑器可用标尺对齐）。
- **MUST** 标题行格式为 `# ` + 英文标题（首字母大写，多个单词用空格），不写中文标题。
- **MUST** 区块标题使用下表固定英文名，便于机器校验与全局搜索：

| 区块   | 固定标题                 |
| ---- | -------------------- |
| 导入   | `Import Libraries`   |
| 常量   | `Module Constants`   |
| 类型别名 | `Type Aliases`       |
| 日志器  | `Module Logger`      |
| 函数集合 | `Module Functions`   |
| 类定义  | `Module Classes`     |
| 入口   | `Script Entry Point` |

- **MUST NOT** 为了"看起来整齐"堆叠空区块或空注释；是否拆分模块看**职责是否单一**，本规范不设行数上限。

---

## 2. 命名规范（Naming）

### 2.1 词源规则（MUST）

- **MUST** 只用英文单词或业界公认缩写（`id`、`url`、`http`、`api`、`db`、`llm`、`json`）。
- **MUST NOT** 使用拼音或拼音缩写：`yonghu`、`huoqu`、`shuju_list`、`chuli()` 全部禁止。
- **MUST NOT** 使用无意义缩写：`usr`、`mgr`、`tmp2`、`d1`、`val`（局部短生命周期变量除外，见 2.4）。
- **MUST NOT** 使用类型后缀：`user_dict`、`UserClass`、`name_string`。类型由标注表达，不写进名字。
- **SHOULD** 用业务语义命名而非技术语义：`pending_orders` 优于 `data_list2`。

### 2.2 各元素命名法

| 元素      | 风格                                     | 示例                                        |
| ------- | -------------------------------------- | ----------------------------------------- |
| 模块 / 包  | `snake_case`，短、全小写                     | `user_service.py`、`rate_limiter/`         |
| 类       | `PascalCase`                           | `UserRepository`、`LlmProvider`            |
| 异常类     | `PascalCase` + `Error` 后缀              | `QuotaExceededError`                      |
| 函数 / 方法 | `snake_case`，动词开头                      | `fetch_user_profile()`                    |
| 变量 / 参数 | `snake_case`                           | `retry_count`                             |
| 常量      | `UPPER_SNAKE_CASE`                     | `MAX_RETRY_ATTEMPTS`                      |
| 模块私有    | 单下划线前缀                                 | `_load_cache()`、`_DEFAULT_TIMEOUT`        |
| 类私有属性   | 单下划线前缀                                 | `self._session`                           |
| 类型变量    | `PascalCase`，协变加 `_co`                 | `T`、`ItemT`、`T_co`                        |
| 布尔值     | `is_` / `has_` / `can_` / `should_` 前缀 | `is_active`、`has_permission`              |
| 集合      | 复数名词                                   | `active_users`、`error_codes`              |
| 字典      | 语义化 + `_by_` 后缀表达索引含义                  | `users_by_id`                             |
| 测试函数    | `test_` + 被测行为 + 预期                    | `test_fetch_user_raises_when_not_found()` |

### 2.3 必须避免的名字

```python
# 禁止：遮蔽内置 / 标准库
list = [...]  # 用 items
id = 1  # 用 user_id
type = "admin"  # 用 account_type
input = raw  # 用 raw_input
format = "json"  # 用 output_format
next = node  # 用 next_node

# 禁止：单字母（除循环下标 i/j/k、坐标 x/y、泛型 T、数学上下文）
u = get_user()  # 用 user

# 禁止：拼音
yonghu_mingcheng = "Tom"  # 用 user_name
```

### 2.4 长度与可读性

- 变量名长度与作用域成正比：循环体内可用 `i`、`item`；模块级常量必须完整表达含义。
- **MUST NOT** 用 `flag`、`data`、`info`、`temp`、`res`、`obj` 这类无信息量的名字（`data` 仅在纯数据处理函数的参数且 docstring 说明结构时可接受）。
- **SHOULD** 名字读出来是完整短语：`remaining_quota` 而非 `remain`。

---

## 3. 排版与格式（Layout）

### 3.1 基础参数

| 项目   | 规定                                             |
| ---- | ---------------------------------------------- |
| 缩进   | 4 空格，**禁止 Tab**                                |
| 行宽   | ≤ 88 字符（含注释与 docstring）；banner 与分区线固定 80 列，不占用这 88 列的余量 |
| 换行   | 优先用括号隐式续行，**禁止用反斜杠 `\` 续行**                    |
| 引号   | 统一双引号 `"`；字符串内含双引号时用单引号或转义                     |
| 编码   | UTF-8，文件内不写 `# -*- coding: utf-8 -*-`          |
| 文件末尾 | 恰好一个换行符，不留多余空行                                 |
| 行尾   | 禁止行尾空白                                         |

### 3.2 空行

- 模块级函数 / 类之间：**2 个空行**。
- 类内方法之间：**1 个空行**。
- 函数内部逻辑块之间：**1 个空行**。
- 分区标题前后：标题上方 1 空行（紧接上一区块内容时 2 空行）、标题下方 0 空行，直接跟内容。
- **MUST NOT** 连续出现 3 个及以上空行。

### 3.3 括号与逗号

```python
# 正确：调用参数每行一个，尾随逗号
result = compute_score(
    user_id=user_id,
    weights=weights,
    normalize=True,
)

# 正确：长条件用括号分行，运算符放行首
if user.is_active and user.quota > 0 and not user.is_locked:
    ...

# 禁止
if user.is_active and user.quota > 0:
    ...
```

### 3.4 集合字面量与推导式

```python
# 正确
ROLE_WEIGHTS: dict[str, float] = {"admin": 1.0, "member": 0.5}
ACTIVE_STATUSES: frozenset[str] = frozenset({"active", "trial"})

# 推导式超过一层嵌套时必须改写成循环，禁止三层推导式
```

---

## 4. 导入规范（Import）

### 4.1 三分组（MUST）

顺序固定：**标准库 → 第三方 PyPI → 本地项目模块**，每组以固定标题开头，组间空 1 行。组内规则：

1. `import xxx` 语句在前，`from xxx import yyy` 在后。
2. 各自按模块名字母序排列（大小写不敏感的 ASCII 序）。
3. 禁止相对导入跨层（见《02 · 工程设计规范》）；同包内允许 `from .` 但**不超过上一级**。
4. 组标题固定为 `# Standard Libraries` / `# Third-Party Libraries` / `# Local Modules`；**该组有内容才写这一行**，没有第三方依赖就不要保留空的组标题。

```python
################################################################################
# Import Libraries
################################################################################
# Standard Libraries
import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Final

# Third-Party Libraries
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

# Local Modules
from app.core.config import settings
from app.models.user import User
from app.repositories.user_repository import UserRepository
```

### 4.2 硬性要求

- **MUST NOT** `from module import *`。
- **MUST NOT** 在函数内部导入（循环依赖的唯一例外：在函数内导入并写注释 `# 延迟导入以避免循环依赖`）。
- **MUST NOT** 导入未使用的模块；`# noqa: F401` 仅允许出现在 `__init__.py` 的公共导出处，并配 `__all__`。
- **MUST** 只导入需要的名字，避免 `import os.path` 这类冗余层级写法（用 `from os import path` 或 `import os`）。
- **SHOULD** 单个文件导入超过 25 行时，说明职责过杂，考虑拆分。
- **MUST** `__init__.py` 必须显式声明 `__all__`，作为该包的公共 API 白名单。

---

## 5. 类型标注（Type Hints）

### 5.1 强制范围（MUST）

- 所有函数 / 方法的**每个参数**与**返回值**必须标注类型，无一例外。
- 类属性、模块常量、`dataclass` 字段必须标注。
- 无法确定具体类型时用 `Any`，并在同行或上一行写注释说明原因；`Any` 属技术债，Review 时会被要求收敛。

```python
from typing import Any


def normalize_payload(payload: Any) -> dict[str, Any]:
    """
    ...
    """

    # 上游事件体结构由外部系统定义且未提供 schema，暂用 Any 承接
```

### 5.2 写法约定

```python
from collections.abc import Callable, Iterable, Mapping, Sequence
from typing import Any, Final, Literal, Protocol, TypedDict, TypeVar

T = TypeVar("T")


# 容器一律用内置泛型（PEP 585）
def aggregate(scores: list[float]) -> dict[str, float]: ...


# 可选值用 | None（PEP 604），不用 Optional
def find_user(user_id: int) -> User | None: ...


# 只读入参用抽象类型，接收面放宽
def sum_scores(scores: Iterable[float]) -> float: ...


# 有限取值用 Literal
LogLevel = Literal["debug", "info", "warning", "error"]


# 结构化字典用 TypedDict
class UserPatch(TypedDict, total=False):
    nickname: str
    avatar_url: str


# 结构化行为用 Protocol（优先于抽象基类，降低耦合）
class SupportsEmbedding(Protocol):
    def embed(self, text: str) -> list[float]: ...


# 常量标注 Final
DEFAULT_TIMEOUT_SECONDS: Final[int] = 30
```

### 5.3 版本兼容表

| 写法                               | 最低版本 | 3.9 可用性                                |
| -------------------------------- | ---- | -------------------------------------- |
| `list[int]`、`dict[str, int]`     | 3.9  | ✅ 可用                                   |
| `X \| None`（注解位置）                | 3.10 | 需 `from __future__ import annotations` |
| `X \| None`（运行时求值，如 Pydantic 模型） | 3.10 | 需 future import 且库支持                   |
| `match` 语句                       | 3.10 | ❌ 不可用                                  |
| `Self`                           | 3.11 | 用 `TypeVar` 替代                         |

项目目标运行时为 **Python 3.10+**，新增文件默认使用现代语法；若需兼容 3.9，在文件导入区首行加：

```python
from __future__ import annotations
```

---

## 6. Docstring 规范（reStructuredText）

### 6.1 通用要求（MUST）

- 每个类、每个函数 / 方法（含 `__init__`，见 6.4）必须有 docstring。
- 格式统一为 **reST（Sphinx 风格）**，禁止混用 Google 的 `Args:` / `Returns:` 分节写法。
- **首行只写 `"""`，描述从第二行开始**；结尾的 `"""` 单独占一行。首行永远是定界符，注释块的起止位置因此整齐可扫。
- 描述用祈使句说明职责，句末加句号。
- 描述与各字段之间空 1 行；字段顺序固定：描述 → `:param` → `:return` / `:rtype` → `:raises`。
- docstring 正文与字段说明**中英文皆可**，按可读性选择；只有字段标记（`:param:`、`:raises:`）和类型名必须是英文 ASCII——这是 reST 语法要求，与语言偏好无关。

### 6.2 字段模板

```
:param <name>: <说明>
:type <name>: <类型>            # 当类型已在签名中标注时可省略 :type
:return: <返回内容说明>
:rtype: <返回类型>              # 已有返回注解时可省略
:raises <ExceptionType>: <触发条件>
```

> 类型已在签名中显式标注的前提下，`:type` 与 `:rtype` **可省略**，但 `:param` / `:return` / `:raises` 不可省。本项目的默认做法：**省略 `:type`、保留 `:rtype` 仅当返回注解为 `Any` 或复杂泛型时**。

### 6.3 函数 docstring 完整示例

```python
def fetch_user_summary(
    user_id: int,
    *,
    include_orders: bool = False,
    max_orders: int = 20,
) -> UserSummary:
    """
    Fetch the aggregated summary of a single user.

    Read-through cache: returns the cached summary when it is still fresh,
    otherwise queries the database and refreshes the cache entry.

    :param user_id: Primary key of the target user, must be positive.
    :param include_orders: Whether to attach the latest orders to the result.
    :param max_orders: Maximum number of orders to attach, capped at 100.
    :return: Aggregated user summary with optional order list.
    :raises ValueError: If ``user_id`` is not positive or ``max_orders`` is
        outside the range ``[1, 100]``.
    :raises UserNotFoundError: If no user matches the given ``user_id``.
    :raises DatabaseConnectionError: If the database is unreachable after
        all retry attempts are exhausted.
    """
```


要求细则：

- 每个参数都要有一条 `:param`，**不得遗漏**，顺序与签名一致。
- `*` 之后的仅关键字参数同样要写。
- 可能抛出的异常全部列出，包括有意向上抛的业务异常；不要写 `:raises Exception:` 这种无意义条目。
- 长说明按 88 列折行，续行缩进与 `:param xxx:` 的描述起始列对齐（4 空格即可）。
- 不写显而易见的废话（`:param user_id: the user id`），要说明**约束与语义**（必须为正、单位、取值范围、None 的含义）。

### 6.4 类 docstring

类 docstring 用 `:param:` 描述构造参数，用 `:ivar:` 描述实例属性：

```python
class UserRepository:
    """
    Persistence gateway for user entities.

    All write methods participate in the caller's transaction; this class
    never commits on its own.

    :param session: Request-scoped async database session.
    :param cache: Optional cache client, disabled when ``None``.
    :ivar _session: Underlying async session, never exposed to callers.
    :ivar _cache: Cache client or ``None`` when caching is disabled.
    """
```

- `__init__` 逻辑简单（仅赋值）时可省略自身 docstring；一旦包含校验、资源申请、副作用，**必须**写。
- **MUST NOT** 在 docstring 里写变更历史（由 Git 承担）、作者名（由 Git 承担）。

---

## 7. 函数内部分块注释（Block Comments）

### 7.1 分块规则（MUST）

函数体按逻辑阶段切块，每块前写一行注释，说明**这一块在做什么、为什么**。常见阶段：

```
1. 参数校验 / 前置断言
2. 状态准备（组装查询、构造上下文）
3. 核心处理（计算 / 调用下游）
4. 结果组装 / 转换
5. 副作用（写库、发消息、写缓存）
6. 返回
```

### 7.2 格式

```python
# 校验入参边界，尽早失败避免无效查询
if user_id <= 0:
    raise ValueError(f"user_id must be positive, got {user_id}")

# 命中缓存则直接返回，省去一次数据库往返
cached = await self._cache.get(cache_key)
if cached is not None:
    return UserSummary.model_validate_json(cached)
```

规则：

- **MUST** 注释以 `# ` 开头（`#` + 一个半角空格），**不加任何前缀标签**——不写 `# inline:`、`# NOTE:`、`# Step 1:` 之类。
- **MUST** 每块注释只描述一个阶段，不写"循环开始""赋值"这类无信息量内容。
- **MUST NOT** 用块注释替代 docstring，也不要在代码行末尾堆叠注释。
- **SHOULD** 单个函数 ≤ 50 行、≤ 5 个逻辑块；超出说明职责过重，应拆分。

### 7.3 注释通用规范

- 注释解释 **Why**，代码本身表达 **What**；禁止把代码翻译成中文注释。
- 中文注释使用中文标点，中英文之间加空格：`# 校验 user_id 是否为正数`。
- 注释与被注释代码同缩进，位于其上方一行。
- 临时方案必须写 `# TODO(owner, YYYY-MM-DD): 说明` 或 `# FIXME(owner): 说明`，owner 为 GitHub 用户名或姓名拼音首字母以外的英文代号。
- 禁止提交被注释掉的死代码。

---

## 8. 类结构规范（Class Layout）

### 8.1 区块顺序（MUST）

类体内固定顺序，用 **Level 2 分隔线**（4 空格缩进 + 76 个 `#`，渲染总宽 80 列）：

```python
class UserService:
    """
    ...
    """

    ############################################################################
    # Class Attributes
    ############################################################################
    MAX_PAGE_SIZE: Final[int] = 100

    ############################################################################
    # Constructor Method
    ############################################################################
    def __init__(self, repository: UserRepository) -> None:
        self._repository = repository

    ############################################################################
    # Default Methods
    ############################################################################
    def __repr__(self) -> str:
        return f"UserService(repository={self._repository!r})"

    ############################################################################
    # Core Instance Methods
    ############################################################################
    def get_summary(self, user_id: int) -> UserSummary:
        """
        ...
        """

    ############################################################################
    # Utility Methods
    ############################################################################
    @staticmethod
    def build_cache_key(user_id: int) -> str:
        """
        ...
        """

    ############################################################################
    # Helper Methods
    ############################################################################
    def _validate_user_id(self, user_id: int) -> None:
        """
        ...
        """
```

固定标题与含义：

| 顺序 | 区块标题 | 内容 |
| --- | --- | --- |
| 0 | （类 docstring） | 必填，见 6.4 |
| 1 | `Class Attributes` | 类常量、类型标注、`ClassVar`；无则省略整块 |
| 2 | `Constructor Method` | `__init__` / `__post_init__` / 类方法构造器 |
| 3 | `Default Methods` | `__repr__`、`__eq__`、`__hash__`、`__len__`、`__enter__` 等 dunder |
| 4 | `Core Instance Methods` | 该类对外的核心业务能力 |
| 5 | `Utility Methods` | `@staticmethod` / `@property` / 与实例状态无关的辅助能力 |
| 6 | `Helper Methods` | `_` 前缀的私有实现细节，仅供本类内部调用 |
| 7 | 按功能扩展区块 | 如 `Serialization Methods`、`Validation Methods`、`Async Lifecycle Methods`，命名同样用英文 `Pascal Case` 短语 + `Methods` |

补充约束：

- **MUST** 无内容的区块整块删除，不留空标题。
- **MUST** 区块标题顺序不可调换；扩展区块统一放在 `Helper Methods` 之后，或紧邻其服务的核心方法之后并保持语义邻近。
- **MUST** 单个类 ≤ 400 行、≤ 12 个公开方法；超出即拆分为多个协作类（组合优于继承）。
- **SHOULD** 类只做一件事。出现 `and` 才能描述类职责时，说明该拆了。

### 8.2 属性与访问控制

- 实例属性一律在 `__init__` 中初始化，禁止在方法里首次赋值产生隐式属性。
- 对外只读属性用 `@property`，不暴露 `self._x`。
- 需要外部写入的用显式 `set_xxx()` 或 `dataclass`；不要在 `@property` 里做 IO。
- `@dataclass` 用于纯数据载体；有行为与依赖注入的用普通类。
- 优先组合 / `Protocol` 注入，继承层级 **≤ 2 层**。

---

## 9. 语言级反模式禁止清单

以下写法 Review 阶段一律按 P1 处理：

| 反模式 | 禁止原因 | 正确写法 |
| --- | --- | --- |
| `def f(x, items=[])` | 默认值全局共享 | `items: list[str] \| None = None`，函数内 `items = items or []` |
| `except:` / `except Exception: pass` | 吞掉真实错误与 `KeyboardInterrupt` | 捕获具体异常，记录日志后处理或重抛 |
| `import *` | 命名空间污染、静态检查失效 | 显式导入或 `__all__` |
| `os.system()` / `shell=True` 拼接 | 命令注入 | `subprocess.run([...], shell=False, check=True)` |
| f-string 拼 SQL | SQL 注入 | 参数化查询 / ORM |
| `print()` 作为日志 | 无级别、无上下文、不可采集 | `logger.info(...)` |
| `assert` 做入参校验 | `-O` 下被移除 | 显式 `raise ValueError(...)` |
| 裸 `open()` 不关闭 | 句柄泄漏 | `with open(...) as f:` |
| 循环内 `+` 拼字符串 | O(n²) | `"".join(parts)` 或 `io.StringIO` |
| 循环内发起 IO / 查询 | N+1 | 批量查询、预加载、提到循环外 |
| `time.sleep()` 在 `async def` 中 | 阻塞事件循环 | `await asyncio.sleep()` / `asyncio.to_thread()` |
| 用 `is` 比较值 | 身份比较，小整数缓存是实现细节 | 值比较用 `==`，`None` 用 `is` |
| 可变对象作默认类属性 | 所有实例共享 | 在 `__init__` 中初始化 |
| 魔法数字散落 | 语义丢失、改一处漏三处 | 提取为具名常量 |
| `pickle.loads()` 处理外部数据 | 任意代码执行 | `json` + Pydantic 校验 |
| 全局可变单例持有请求状态 | 并发串数据 | 请求级作用域 / 依赖注入 |

---

## 10. 日志与异常的最小风格约束

详细规范见《03 · 质量与流程规范》，此处仅约束写法形态：

```python
# 模块级 logger 命名：固定 __name__
logger = logging.getLogger(__name__)

# 日志用惰性参数化，禁止 f-string 预拼接（便于采样与脱敏）
logger.info("fetch user summary user_id=%s cache_hit=%s", user_id, cache_hit)

# 记录异常用 exc_info，禁止 logger.error(str(exc))
try:
    await self._repository.save(user)
except IntegrityError as exc:
    logger.warning("duplicate user email=%s", user.email, exc_info=True)
    raise DuplicateEmailError(user.email) from exc
```

- **MUST** 重抛时用 `raise NewError(...) from exc` 保留异常链。
- **MUST NOT** 在日志里输出密码、token、完整手机号、身份证号、完整请求体。

---

## 11. 文档与注释语言

| 内容 | 语言 |
| --- | --- |
| 标识符、文件名、目录名、分区标题 | 英文 |
| docstring 正文与字段说明 | 中英文皆可；reST 字段标记与类型名必须英文 ASCII |
| 块注释（函数内分块） | 中英文皆可，同一文件内保持一致 |
| 提交信息 | 英文（Conventional Commits） |
| README / 设计文档 | 中文 |

> 语言选择不影响规范合规性，只要求**同一文件内风格统一**。若项目要接入 Sphinx，在 `conf.py` 设置 `language = 'zh_CN'` 即可正常处理中文断词与索引。

---

## 12. 交付前自检清单（Style 部分）

- [ ] banner 五字段齐全、日期格式正确、每行不超过 80 列（超长已换行对齐）
- [ ] 分区顺序正确、分隔线 80 列、标题用规定英文名
- [ ] import 三分组、组标题为 `# Standard Libraries` / `# Third-Party Libraries` / `# Local Modules`、组内有序、无 `import *`
- [ ] 所有标识符为英文单词，无拼音、无类型后缀、无单字母（合规例外除外）
- [ ] 所有函数/类有 reST docstring，首行只写 `"""`，`:param` 覆盖全部参数，`:raises` 覆盖全部异常
- [ ] 所有参数与返回值有类型标注，`Any` 处有原因注释
- [ ] 函数体按逻辑分块，每块前有一行说明注释
- [ ] 类区块顺序正确、无空区块
- [ ] 无第 9 节任一反模式
- [ ] `ruff check` / `ruff format --check` / `mypy` / `check_style.py` 全部通过

---

## 附录 A：可复制的最小合规模块

完整可运行版本见 `assets/module_template.py`（同时作为 `check_style.py` 的回归样本）。骨架：

```python
################################################################################
# @Project: ai-assistant
# @File Path: backend/app/services/quota_service.py
# @Description: Quota calculation and enforcement for LLM usage
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

# Third-Party Libraries
from pydantic import BaseModel

# Local Modules
from app.core.config import settings

################################################################################
# Module Constants
################################################################################
# 配额下限，避免负配额导致无限调用
MIN_QUOTA: Final[int] = 0

################################################################################
# Module Logger
################################################################################
logger = logging.getLogger(__name__)


################################################################################
# Module Classes
################################################################################
class QuotaService:
    """
    ...
    """

    ############################################################################
    # Class Attributes
    ############################################################################
    DEFAULT_LIMIT: Final[int] = 1000
```

## 附录 B：工具链配置基线

```toml
# pyproject.toml 片段
[tool.ruff]
line-length = 88
target-version = "py310"

[tool.ruff.lint]
select = ["E", "F", "W", "I", "N", "UP", "B", "C4", "SIM", "RET", "ANN", "D", "S"]
# D100：模块说明由 banner 承担，不写模块 docstring
# D212：本项目要求 docstring 摘要从第二行开始（与 D213 一致），故忽略 D212
# ANN401：Any 的使用另由 check_style.py 提示
ignore = ["D100", "D203", "D212", "ANN401"]

[tool.ruff.lint.pydocstyle]
convention = "pep257"

[tool.mypy]
python_version = "3.10"
strict = true
warn_unused_ignores = true
disallow_untyped_defs = true
```

> 注：`ruff` 与 `mypy` 的具体规则名随版本演进，落地时以当前安装版本的 `ruff rule --all` 输出为准（需核实）。
