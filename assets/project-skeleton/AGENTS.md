# AGENTS.md · AI 助理项目开发约定

> 本文件是 Agent / IDE 的**常驻指令入口**。任何在本仓库生成、修改、评审 Python 代码的行为，都受本文件与
> `.workbuddy/skills/python-dev-standard/` 下规范的约束。
> 完整规范按需加载，本文件只保留必须常驻的红线与路由。

## 1. 规范位置与加载顺序

| 文件 | 内容 | 何时读 |
| --- | --- | --- |
| `.workbuddy/skills/python-dev-standard/SKILL.md` | 红线 + 路由 + 工作流 | 每次写 Python 前 |
| `.../references/01-code-style.md` | 命名、banner、分区、docstring、类结构 | 写 / 改任何 `.py` |
| `.../references/02-engineering-design.md` | 分层、模块划分、设计模式、前后端契约 | 涉及结构 / 接口 / 选型 |
| `.../references/03-quality-and-process.md` | 类型、异常、日志、安全、测试、Git、CI | 涉及质量与流程 |
| `.../references/04-documentation.md` | 交接文档：目录地图、七类模板、更新义务矩阵 | 写 / 更新 `docs/` 时 |
| `.../assets/module_template.py` | 单文件骨架（零依赖可运行） | 新建 `.py` 时复制 |
| `.../assets/project-skeleton/` | 完整参照工程，四道门全绿的样板 | 拿不准某文件该放哪一层时对照 |
| `docs/README.md` | 项目当前状态、能力清单、启动方式 | 每次开工第一步 |
| `docs/architecture.md` | 分层、模块清单、ADR 索引 | 定位改动该落在哪一层 |
| `docs/dev-log.md` | 最近改了什么、为什么 | 动同一区域之前 |

冲突处理优先级：**用户当前明确指令 > 本文件 > SKILL.md > references**。若用户要求违反安全红线（硬编码密钥、拼接 SQL、吞异常），先说明风险再执行。

## 2. 十一条红线

1. 标识符全英文，禁拼音；类 `PascalCase`，函数与变量 `snake_case`，常量 `UPPER_SNAKE_CASE`。
2. 每个 `.py` 首部必须有 banner：上下各一条 80 个 `#` 的边界线，中间五个字段
   `@Project` / `@File Path` / `@Description` / `@Creation Date` / `@Last Update`。
   字段值超过 80 列时换行，续行用空格对齐到该字段值的起始列（如 `@File Path` 对齐到第 15 列）。
3. 分区顺序固定：`Import Libraries` → `Module Constants` → `Type Aliases` → `Module Logger` →
   `Module Functions` → `Module Classes` → `Script Entry Point`；分隔线恰好 80 列（类内为 4 空格 + 76 个 `#`）。
   import 三分组分别用 `# Standard Libraries` / `# Third-Party Libraries` / `# Local Modules` 引导，有内容才写。
4. 每个函数 / 类必须有 reST docstring：**首行只写 `"""`**，描述从第二行开始，然后是
   `:param`（覆盖全部参数）→ `:return` → `:raises`。
5. 每个参数与返回值必须标注类型；无法确定用 `Any` 并注释原因。
6. 函数体内每个逻辑块前写一行注释，直接以 `# ` 开头，不加 `inline:` 之类的标签。
7. 类内区块固定：`Class Attributes` → `Constructor Method` → `Default Methods` →
   `Core Instance Methods` → `Utility Methods` → `Helper Methods`。
8. 禁止裸 `except`、吞异常、`import *`、可变默认参数、`shell=True` 拼接、f-string 拼 SQL。
9. 禁止硬编码密钥与凭据；禁止 `print` 当日志；禁止接口层返回 ORM 实体。
10. 遵守分层：`domain` 不依赖框架，`router` 不碰数据库，`service` 不写查询，`repository` 不做业务判断。
11. 改动结构、接口、实体或用户可见行为时，必须**同 PR** 更新 `docs/` 对应文件，并在 `docs/dev-log.md`
    记一条（变更 / 为什么 / 影响面 / 验证 / 文档 / 遗留）。文档缺失与测试失败同等对待。

## 3. 交付前必跑

```bash
python .workbuddy/skills/python-dev-standard/scripts/check_style.py backend/ scripts/
ruff format --check . && ruff check .
mypy backend/app
pytest -q
```

`check_style.py` 退出码非 0 即不合规，不得交付。规范细节与豁免条件见 `SKILL.md`「允许的合法偏离」。

文档门禁（无脚本，按清单自查）：对照 `04-documentation.md` 第 4 节，确认本次改动涉及的文档已更新，`dev-log.md` 已加条目，受影响文档的「最后核对」已刷新。

## 4. 目录基线

```
backend/app/
  main.py          # 装配：路由、中间件、异常处理
  core/            # config、logging、errors、security
  modules/<domain>/  # router / service / repository / schemas / domain
  infrastructure/  # db、llm、cache、queue
  shared/          # 跨域小工具（禁止万能 utils）
frontend/src/      # app / pages / features / components / lib / stores
docs/              # README / architecture / data-flow / entities / ux / dev-log / tech-debt
docs/adr/          # 架构决策记录 NNNN-kebab-title.md
```

## 5. 给 Agent 的额外要求

- **先读文档再动手**：`docs/README.md` → `architecture.md` → 相关 `data-flow.md` / `entities.md` →
  `dev-log.md` 最近 5 条 → 相关 ADR。先例与已否决方案都在里面，重来一遍是浪费。
- **先看清再动手**：改文件前先读目标文件与相邻模块，沿用既有的命名、分层与错误处理风格，不引入第二套范式。
- **模板优先**：新建 `.py` 从 `assets/module_template.py` 复制，新建业务域对照 `assets/project-skeleton/backend/app/modules/chat/`，不要凭印象拼结构。
- **不猜**：Python 版本、运行环境、接口契约、预期输入输出缺失时先问，不假设补全。
- **不静默降级**：无法完成或存在未解决错误时如实说明，不假报成功。
- **不留死代码**：注释掉的代码、未使用的导入、临时调试语句一律清除。
