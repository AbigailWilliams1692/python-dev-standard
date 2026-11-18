# AGENTS.md · 库型项目开发约定

> 本文件是 Agent / IDE 的**常驻指令入口**，适用于「被别人的代码 `import`」的 Python 库。
> 服务型项目（有 HTTP 接口、要部署成常驻进程）请改用 `project-skeleton/AGENTS.md`，
> 两者的红线不同：库没有分层要求，但有公开 API 稳定性要求。
>
> 完整规范按需加载，本文件只保留必须常驻的红线与路由。

## 1. 规范位置与加载顺序

| 文件 | 内容 | 何时读 |
| --- | --- | --- |
| `.workbuddy/skills/python-dev-standard/SKILL.md` | 红线 + 路由 + 工作流 | 每次写 Python 前 |
| `.../references/01-code-style.md` | 命名、banner、分区、docstring、类结构 | 写 / 改任何 `.py` |
| `.../references/03-quality-and-process.md` | 类型、异常、安全、测试、Git、CI | 涉及质量与流程 |
| `.../references/04-documentation.md` | 交接文档模板，库型按 05 第 6 节精简 | 写 / 更新 `docs/` 时 |
| `.../references/05-project-archetypes.md` | 库型骨架的必备要素与裁剪清单 | 不确定某个结构该不该有 |
| `.../assets/module_template.py` | 单文件骨架（零依赖可运行） | 新建 `.py` 时复制 |
| `.../assets/package-skeleton/` | 本骨架，四道门 + 构建校验全绿 | 拿不准文件放哪时对照 |
| `docs/README.md` | 库当前状态、公共 API、安装方式 | 每次开工第一步 |
| `docs/dev-log.md` | 最近改了什么、为什么 | 动同一区域之前 |
| `CHANGELOG.md` | 面向使用者的变更记录 | 任何影响公共 API 的改动 |

**不要读 `02-engineering-design.md` 的分层章节**：四层结构（interface/application/domain/infrastructure）
假设「有请求从外面进来」，库没有请求，硬套会让 `service.py` 退化成什么都往里塞的巨型类。

冲突处理优先级：**用户当前明确指令 > 本文件 > SKILL.md > references**。

## 2. 十一条红线

1. 标识符全英文，禁拼音；类 `PascalCase`，函数与变量 `snake_case`，常量 `UPPER_SNAKE_CASE`。
2. 每个 `.py` 首部必须有 banner：上下各一条 80 个 `#` 的边界线，中间五个字段
   `@Project` / `@File Path` / `@Description` / `@Creation Date` / `@Last Update`。
   字段值超过 80 列时换行，续行用空格对齐到该字段值的起始列。
3. 分区顺序固定：`Import Libraries` → `Module Constants` → `Type Aliases` → `Module Logger` →
   `Module Functions` → `Module Classes` → `Script Entry Point`；分隔线恰好 80 列（类内为 4 空格 + 76 个 `#`）。
4. 每个函数 / 类必须有 reST docstring：**首行只写 `"""`**，描述从第二行开始，然后是
   `:param`（覆盖全部参数）→ `:return` → `:raises`。
5. 每个参数与返回值必须标注类型；无法确定用 `Any` 并注释原因。
6. 函数体内每个逻辑块前写一行注释，直接以 `# ` 开头，不加 `inline:` 之类的标签。
7. 类内区块固定：`Class Attributes` → `Constructor Method` → `Default Methods` →
   `Core Instance Methods` → `Utility Methods` → `Helper Methods`。
8. **公共 API 只能从 `__init__.py` 的 `__all__` 出去**。未列出的名字是内部实现，
   改动它们不算破坏性变更；反过来，`__all__` 里删名字就是主版本变更。
9. **代码必须落在 `src/<package>/`**，`py.typed` 必须存在且被 `package-data` 包含；
   版本号只在 `_version.py` 写一次。三条任一缺失，库就是坏的：
   - 无 src layout → 本地能 import、装完 import 不到；
   - 无 `py.typed` → 下游 mypy 静默忽略本库全部标注；
   - 版本两处写 → 必然漂移，`pip show` 与 `__version__` 对不上。
10. 禁止裸 `except`、吞异常、`import *`、可变默认参数、`shell=True` 拼接；
    禁止硬编码密钥；禁止 `print` 当日志；**禁止在库里 `logging.basicConfig()`** ——
    库不该决定宿主程序的日志配置。
11. 影响公共 API 的改动必须**同 PR** 更新 `CHANGELOG.md` 与 `docs/dev-log.md`。
    破坏性变更走弃用流程：先 `DeprecationWarning` 提示，至少留两个次版本。

## 3. 交付前必跑

```bash
python <skill>/scripts/check_style.py src tests    # 风格（banner / 分区 / docstring / 命名）
ruff format --check . && ruff check .              # 格式与静态检查
mypy                                               # 类型（strict）
pytest -q                                          # 测试

python -m build                                    # sdist + wheel
python -m twine check dist/*                       # 元数据校验
```

任何一条非 0 即不得交付。构建产物还要额外确认两件事：
**wheel 里含 `py.typed`**，且**从 wheel 安装后能 import**（CI 的 `package` job 已自动化）。

## 4. 目录基线

```
src/<package>/
  __init__.py      # 唯一公共出口，__all__ 即契约
  _version.py      # 版本单一真源，pyproject 动态读取
  py.typed         # PEP 561 标记，不能删
  errors.py        # 异常层次，不带 HTTP 语义
  models.py        # 值对象与不变量
  <capability>.py  # 按能力分模块，不按「层」分
tests/             # 只通过公开 API 测试
docs/              # README / architecture / dev-log / tech-debt
CHANGELOG.md       # 库必填，服务型项目可省
```

## 5. 给 Agent 的额外要求

- **先判断项目形态再动手**：如果这个仓库其实要对外提供 HTTP 接口，说明形态判断错了，
  应改用 `project-skeleton/`，而不是在库里塞 `main.py`。
- **先读文档再动手**：`docs/README.md` → `architecture.md` → `docs/dev-log.md` 最近 5 条 → `CHANGELOG.md`。
  已发布的接口行为都在里面，改错等于给下游埋雷。
- **公开面最小化**：新增一个 `__all__` 条目等于签一份长期契约。问自己：
  下游真的需要 import 它吗？能不能只用现有 API 组合出来？
- **不猜**：Python 版本下限、是否要支持 3.9、是否需要可选的 C 扩展，缺失时先问。
- **不留死代码**：注释掉的代码、未使用的导入、临时调试语句一律清除。
- **单实现的抽象不要加**：库里 `Protocol` / 抽象基类只在「确实有第二个实现或需要用户替换」时才建，
  否则是纯成本。
