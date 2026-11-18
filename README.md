# python-dev-standard

一套**可执行**的 Python 工程规范：不是一堆"请遵循"的文档，而是能被机器检查的规则、能直接复制的骨架、能一条命令生成的模块。

面向 Vibe Coding 场景——多个模型/Agent 在不同时间片段里开发同一个项目时，靠人盯是守不住的，必须让不合规的代码**跑不过门禁**。

## 它解决什么问题

| 常见失败 | 这套规范的应对 |
| --- | --- |
| 每个 Agent 用不同风格写 docstring / 分区 / 命名 | 80 列 banner + 固定分区 + reST docstring，`check_style.py` 逐条判定 |
| 分层写成"目录分了但依赖乱穿" | `check_architecture.py` 用 AST 拦截 `domain → infra`、`core → modules` 等越界 |
| 新增模块靠手抄旧模块，每次都漏东西 | `new_module.py` 一条命令生成 8 个文件并自动接线，生成物零改动就过门禁 |
| 交接时没人知道为什么这么设计 | `04-documentation.md` 的七类模板 + **更新义务矩阵** + ADR |
| 文档写了没人更新，半年后全是假的 | 文档红线进 `AGENTS.md`，改结构却不动 `docs/` 视为不合格 |
| 把库硬套成服务，或把服务削成库 | 两套骨架 + 「第 0 步」可判定清单，形态选错要重建整个目录 |

## 两套骨架：先判断形态

同一套代码风格，两种工程结构。**选错骨架的代价大于写错任何单个函数。**

| 判据（按顺序问，第一个「是」即停） | 形态 | 骨架 |
| --- | --- | --- |
| 有请求从外面进来？（HTTP / WebSocket / 队列消费者） | 服务型 | `assets/project-skeleton/` |
| 会被别的 Python 代码 `import`？ | 库型 | `assets/package-skeleton/` |
| 只有命令行入口？ | CLI | `package-skeleton/` + `cli.py` 薄壳 |
| 都不像，一次运行读完就退出？ | 数据管道 | 裁剪 `package-skeleton/` |

| | 服务型骨架 | 库型骨架 |
| --- | --- | --- |
| 结构 | 四层 `backend/app/{core,modules,infrastructure}` | `src/<package>/` 平铺 |
| 契约 | `schemas.py` + 路由 | `__init__.py` 的 `__all__` |
| 门禁 | 5 道（含分层校验） | 4 道 + `build` + `twine check` |
| 测试 | 26 条 | 21 条 |
| 该形态独有的坑 | 分层越界 | `py.typed` 没进 wheel、装完 import 不到、版本两处漂移 |

两份骨架各带一份 `AGENTS.md`，**内容不同，不要混用**：库型那份明确写了「不要读 02 的分层章节」，
因为分层假设「有请求从外面进来」，而库没有。这两份是**模板**：复制到项目根后归该项目所有，
骨架里的原件不会被同步覆盖，项目对副本的任何修改也不回写骨架。

## 安装

作为项目级技能放入 `.workbuddy/skills/`：

```bash
# 方式一：子模块（推荐，可跟随上游升级）
git submodule add <本仓库地址> .workbuddy/skills/python-dev-standard

# 方式二：直接复制
cp -r python-dev-standard <你的项目>/.workbuddy/skills/
```

然后把**对应形态**骨架的 `AGENTS.md` 复制到项目根目录——它是 Agent 的常驻入口：

- 服务型 → `assets/project-skeleton/AGENTS.md`
- 库型 / CLI → `assets/package-skeleton/AGENTS.md`

## 三条命令

```bash
# 1. 检查代码风格（banner / 分区 / docstring / 命名 / 类型标注 / 行宽）
python .workbuddy/skills/python-dev-standard/scripts/check_style.py backend/

# 2. 检查分层依赖（domain 不依赖框架、core 不被业务反向依赖、跨域不越界）
python .workbuddy/skills/python-dev-standard/scripts/check_architecture.py backend

# 3. 生成一个新业务域（8 个文件 + container/dependencies/main/error_codes 自动接线）
python .workbuddy/skills/python-dev-standard/scripts/new_module.py order
```

三个脚本都只用标准库，退出码可直接进 CI。配合同项目的 `ruff` / `mypy` / `pytest` 构成五道门。

## 目录

```
.
├── SKILL.md                 # Agent 入口：红线 + 路由 + 工作流（129 行，渐进加载）
├── references/              # 只放规范文本
│   ├── 01-code-style.md          命名 / banner / 分区 / docstring / 类结构 / 反模式
│   ├── 02-engineering-design.md  分层 / 模块划分 / 设计模式 / 契约 / 新增业务域 SOP
│   ├── 03-quality-and-process.md 类型 / 异常 / 日志 / 安全 / 测试 / Git / CI
│   ├── 04-documentation.md       交接文档地图 / 七类模板 / 更新义务矩阵
│   └── 05-project-archetypes.md  服务 / 库 / CLI / 数据管道的骨架选型与裁剪
├── assets/                  # 会被复制进项目的产物
│   ├── module_template.py        单文件骨架，任何形态都适用
│   ├── project-skeleton/         服务型参照工程，五道门全绿
│   └── package-skeleton/         库型 / CLI 参照工程，四道门 + 构建校验全绿
├── scripts/                 # 只放要执行的代码
│   ├── check_style.py            风格校验器
│   ├── check_architecture.py     分层校验器（仅服务型）
│   ├── new_module.py             业务域脚手架（仅服务型）
└── tests/                   # 验证三个 Python 脚本本身
```

## 适用范围

- **服务型**（有 HTTP 接口）：`project-skeleton/` 直接可用。
- **库型 / CLI**（被 `import`，或只有命令行入口）：`package-skeleton/` 直接可用。
- **数据管道**：裁剪 `package-skeleton/`，核心质量属性是幂等与断点续跑，不是分层。

代码风格（01）与质量流程（03）与项目类型无关，任何 Python 项目都适用。
完整判据、复用矩阵与裁剪步骤见 `references/05-project-archetypes.md`。

## 自检

本仓库自己也遵守这套规范：

```bash
python scripts/check_style.py scripts/ tests/
python scripts/check_architecture.py assets/project-skeleton/backend
pytest tests/ -q

# 两份骨架各自的全量门禁
cd assets/project-skeleton && python ../../scripts/check_style.py backend
cd assets/package-skeleton && python ../../scripts/check_style.py src tests
```

- 三个脚本自身通过 `check_style.py`（0 ERROR / 0 WARN）。
- `assets/project-skeleton/` 通过 `check_style` / `check_architecture` / `ruff` / `mypy` / `pytest`（26 条）。
- `assets/package-skeleton/` 通过 `check_style` / `ruff` / `mypy` / `pytest`（21 条）/ `build` / `twine check`，
  且 wheel 含 `py.typed`、从 wheel 安装后可正常 import。
- `tests/` 覆盖两个检查器的每条规则（正样本 + 反样本），防止规则被改坏后静默失效。

## 版本

见 [CHANGELOG.md](CHANGELOG.md)。规范改动会影响已采纳的项目，因此规则变更一律记入变更日志。

## 许可

[MIT](LICENSE)
