---
name: python-dev-standard
version: 0.2.0
description: 本项目 Python 开发规范的唯一入口。当需要编写、修改、评审任何 .py 文件，新建项目或目录，判断该用服务型还是库型结构，设计后端分层与接口，做技术选型，或检查代码是否合规时加载。覆盖 banner/分区/docstring/命名等代码风格（PEP 8 + Google Style + 项目自定义），以及模块划分、分层架构、前后端契约、安全与测试等工程规范；提供两套可运行骨架（HTTP 服务型 / 纯 Python package 型，后者含 src layout、py.typed、__all__ 公共契约）。关键词：Python、PEP8、代码风格、docstring、banner、命名规范、模块设计、分层架构、高内聚低耦合、Code Review、代码评审、规范检查、交接文档、ADR、架构决策、开发记录、handover、库、package、pip、SDK、CLI、src layout、py.typed、打包发布。
---

# Python 开发规范（项目级）

本 Skill 是「AI 助理」项目 Python 代码与架构的**强制规范**。所有交付的 Python 代码必须满足这里的约束，Review 时按此判定。

## 第 0 步：先判断项目形态

同一套代码风格，两套骨架。**选错骨架的代价大于写错任何单个函数**：
在库里塞 `main.py`，会得到一套没有请求的"分层"，`service.py` 退化成什么都往里塞的巨型类；
在服务里用 src layout，会得到一个没人 `import`、却要部署的包。

按顺序问四个问题，第一个命中即停：

| # | 判据 | 命中 → |
| --- | --- | --- |
| 1 | 有请求从外面进来吗？（HTTP / WebSocket / 队列消费者） | **服务型** |
| 2 | 会被别的 Python 代码 `import` 吗？ | **库型** |
| 3 | 只有命令行入口？ | **库型 + `cli.py` 薄壳**（05 第 4 节） |
| 4 | 库和 API 都要？ | **拆两个包**：库做内核，服务做外壳 |

| 形态 | 骨架 | 常驻指令 | 关键差异 |
| --- | --- | --- | --- |
| 服务型 | `assets/project-skeleton/` | 它自带的 `AGENTS.md` | 四层结构、DI 装配、HTTP 契约、`docs/ux.md` |
| 库型 / CLI | `assets/package-skeleton/` | 它自带的 `AGENTS.md` | `src/` layout、`py.typed`、`__all__` 契约、`CHANGELOG` 必填 |
| 数据管道 | 库型骨架裁剪（05 第 5 节） | 同上 | 幂等与断点续跑优先于分层 |

判据模糊时看**交付形态**：要跑成常驻进程 → 服务型；要 `pip install` 进别人的环境 → 库型。
仍然拿不准就问用户，不要猜——猜错要重建整个目录结构。

两套骨架的 `AGENTS.md` 内容不同，**不要混用**：库型那份明确写了「不要读 02 的分层章节」，
因为分层假设「有请求从外面进来」，而库没有。

## 何时必须加载

| 场景 | 必读文件 |
| --- | --- |
| 写 / 改任何 `.py` 文件 | `references/01-code-style.md` |
| 新建目录、拆模块、定分层、加业务域 | `references/02-engineering-design.md` |
| 涉及接口契约、前后端联调 | `references/02-engineering-design.md` 第 6–7 节 |
| 写异常处理、日志、鉴权、DB 访问 | `references/03-quality-and-process.md` |
| 写测试、配 CI、提交代码 | `references/03-quality-and-process.md` |
| 做技术选型 / 架构决策 | `references/02-engineering-design.md` + 写 ADR |
| 写 / 更新 `docs/` 交接文档、交接给下一个 Agent 或人类 | `references/04-documentation.md` |
| 判断该用哪套骨架（服务 / 库 / CLI / 数据管道） | 见本文「第 0 步」+ `references/05-project-archetypes.md` |
| 从零搭服务型工程、或不确定某文件该放哪一层 | 直接看 `assets/project-skeleton/` 的目录与代码 |
| 从零搭库型 / CLI 工程、或不确定 `src` 里怎么分模块 | 直接看 `assets/package-skeleton/` 的目录与代码 |
| 新增一个业务域 | `scripts/new_module.py` + `references/02` 第 19 节 |

**渐进加载**：先读本文件（已含红线与检查清单），再按上表只读命中的 1–2 份 reference，不要一次性全读。

## 十条红线（违反即不合格）

1. 标识符全英文，**禁拼音**；类 `PascalCase`、函数/变量 `snake_case`、常量 `UPPER_SNAKE_CASE`。
2. 每个 `.py` 首部有 80 列 banner，字段固定为 `Project / File Path / Description / Creation Date / Last Update`；字段值超长时换行并**对齐到该字段值的起始列**，banner 内每行都不得超过 80 列。
3. 文件分区固定：Import → Module Constants → Type Aliases → Module Logger → Module Functions → Module Classes → Script Entry Point，每条分隔线恰好 80 列；import 三分组分别以 `# Standard Libraries`、`# Third-Party Libraries`、`# Local Modules` 引导（该组有内容才写）。
4. 每个函数 / 类有 **reStructuredText** docstring：**首行只写 `"""`**，描述另起一行，然后 `:param`（一个都不能漏）→ `:return` → `:raises`。
5. 每个参数与返回值都有类型标注，确实无法确定用 `Any` 并加注释说明原因。
6. 函数体按逻辑分块，每个逻辑块前写一行注释，直接以 `# ` 开头，不加任何标签前缀。
7. 类内部区块顺序固定：`Class Attributes` → `Constructor Method` → `Default Methods` → `Core Instance Methods` → `Utility Methods` → `Helper Methods`。
8. 禁裸 `except`、禁吞异常、禁 `import *`、禁可变默认参数、禁 `shell=True` 拼命令、禁 f-string 拼 SQL。
9. 禁硬编码密钥 / 连接串 / 口令；禁 `print` 当日志；禁返回 ORM 实体给接口层。
10. 代码必须落在正确的层：`domain` 不依赖框架，`router` 不碰 SQL，`service` 不写查询语句。

### 文档红线（同样不合格）

- 改结构 / 接口 / 实体 / 用户可见行为，必须**同 PR** 更新 `docs/` 对应文件（矩阵见 04 第 4 节）。
- `docs/dev-log.md` 必须新增一条，六项齐全：变更、为什么、影响面、验证、文档、遗留。
- 文档与代码冲突时**以代码为准**当场修正文档，禁止「改代码迁就过期文档」。
- 禁止「待补充」「后续完善」占位；未解决的问题进 `docs/tech-debt.md`。

## 工作流

**开工前**
- 判断任务属于「纯代码」还是「涉及结构」：涉及结构先给方案（对照 02 的分层矩阵与目录基线）再动手。
- 定位代码该放哪一层、哪个业务域。拿不准时先问，不要猜。

**写代码时**
- 新建单个文件：复制 `assets/module_template.py`。
- 新建工程：先按「第 0 步」判断形态——服务型对照 `assets/project-skeleton/`，库型对照 `assets/package-skeleton/`。
- 新增业务域（**仅服务型**）：用 `scripts/new_module.py` 生成，不要手抄 chat 目录。
- 每个函数先写 docstring 草案，再写实现——参数漏了立刻能发现。
- 新增外部依赖前先确认：能否用标准库、是否已停止维护、License 是否兼容。

**交付前（必须全绿）**

服务型：

```bash
# 1. 项目自定义规范（banner / 分区 / 命名 / docstring / 类型 / 行宽）
python .workbuddy/skills/python-dev-standard/scripts/check_style.py backend/
# 2. 分层依赖（domain 不进框架、core 不被业务依赖、跨域不越界）
python .workbuddy/skills/python-dev-standard/scripts/check_architecture.py backend
# 3. 格式与 Lint
ruff format --check . && ruff check .
# 4. 类型
mypy backend/app
# 5. 测试
pytest -q
```

库型 / CLI：

```bash
# 1. 项目自定义规范（同上，扫描 src 与 tests）
python .workbuddy/skills/python-dev-standard/scripts/check_style.py src tests
# 2. 格式与 Lint
ruff format --check . && ruff check .
# 3. 类型
mypy
# 4. 测试
pytest -q
# 5. 构建与元数据（库独有：装不上等于没发布）
python -m build && python -m twine check dist/*
```

库型**不跑** `check_architecture.py`：它检查的是四层边界，库里没有四层，跑了只会制造假规则。
库型多出的第 5 步不可省——`py.typed` 没进 wheel、或装完 import 不到，静态检查一个都发现不了。
逐条对照 `references/03-quality-and-process.md` 第 11 节的「交付前总清单」，
以及 `references/04-documentation.md` 第 8 节的「交付前自检（文档部分）」。

## 工具分工（不要重复造轮子）

| 关注点 | 由谁负责 |
| --- | --- |
| banner、分区、80 列分隔线、reST docstring、`:param` 覆盖、类型标注存在性、拼音命名、行宽 | `scripts/check_style.py` |
| import 排序、格式、常见 bug 模式（B 系列）、安全规则（S 系列） | `ruff` |
| 类型正确性（而非「有没有写」） | `mypy --strict` |
| 分层是否越界、循环依赖、契约一致性 | 人工评审 + 02 第 2.2 节矩阵 |

`check_style.py` 只做 AST 与文本层面的**可判定**检查，不做类型推断，也不替代 Lint。

## 允许的合法偏离

规范不是教条。偏离必须满足三个条件，缺一不可：

1. 在代码处写注释说明**为什么**偏离（如 `# 该函数需保持与第三方回调签名一致`）；
2. 不影响可读性与安全性；
3. 涉及架构层面的偏离，写进 `docs/adr/`。

`check_style.py` 的 `WARN` 级问题（拼音启发式、模块级变量命名）允许带理由忽略；`ERROR` 级不允许。

## 文件索引

```
.workbuddy/skills/python-dev-standard/
├── SKILL.md                          # 本文件：红线 + 路由 + 工作流
├── references/                       # 只放规范文本，不放可执行代码
│   ├── 01-code-style.md              # 代码风格：命名 / banner / 分区 / docstring / 类结构 / 反模式
│   ├── 02-engineering-design.md      # 工程设计：分层 / 模块划分 / 设计模式 / 契约 / 新增业务域 SOP
│   ├── 03-quality-and-process.md     # 质量流程：类型 / 异常 / 日志 / 安全 / 测试 / Git / CI
│   ├── 04-documentation.md           # 交接文档：docs 地图 / 七类模板 / 更新义务矩阵
│   └── 05-project-archetypes.md      # 项目原型：服务 / 库 / CLI / 数据管道的骨架选型
├── assets/                           # 可复制进项目的产物，不是给技能自己跑的
│   ├── module_template.py            # 单文件骨架，任何形态都适用
│   ├── project-skeleton/             # 服务型参照工程（五道门全绿）
│   │   ├── AGENTS.md                 # 服务型常驻指令 → 复制到项目根
│   │   ├── pyproject.toml            # ruff / mypy / pytest / 打包配置
│   │   ├── .env.example              # 环境变量清单（不含真实值）
│   │   ├── .github/workflows/ci.yaml # 五道门流水线
│   │   ├── .pre-commit-config.yaml   # 提交前同规则快检
│   │   ├── backend/                  # core 地基 + modules/chat 四层范式 + infrastructure 适配器
│   │   └── docs/                     # 9 份交接文档实例 + 2 份 ADR
│   └── package-skeleton/             # 库型 / CLI 参照工程（四道门 + 构建校验全绿）
│       ├── AGENTS.md                 # 库型常驻指令，红线与服务型不同
│       ├── pyproject.toml            # src layout / 动态版本 / extras 分组
│       ├── CHANGELOG.md              # 库必填，服务型可省
│       ├── src/mylib/                # __init__ 契约 + py.typed + 值对象 + 异常层次
│       ├── tests/                    # 只通过公开 API 测试
│       ├── .github/workflows/ci.yaml # 多版本矩阵 + 构建校验 + 装机冒烟
│       └── docs/                     # 精简四份（无 ux / entities / data-flow）
├── scripts/                          # 只放需要被执行的代码
│   ├── check_style.py                # 风格校验器，退出码可入 CI
│   ├── check_architecture.py         # 分层依赖校验器，仅服务型需要
│   └── new_module.py                 # 业务域脚手架，产物零改动过门禁
└── tests/                            # 验证上面三个 Python 脚本本身
```

## `assets/` 里三份参照物的分工

| 产物 | 解决什么问题 | 怎么用 |
| --- | --- | --- |
| `module_template.py` | 单个文件怎么写 | 新建 `.py` 时整体复制，替掉 banner 与函数体 |
| `project-skeleton/` | **服务型**工程怎么长 | 内容复制到项目根；改造现有项目时按目录对照补缺口 |
| `package-skeleton/` | **库型 / CLI** 工程怎么长 | 同上，但先读它的 `AGENTS.md`——红线与服务型不同 |

两份 skeleton 都是**可执行的真工程**，不是示意代码：

| | `project-skeleton/` | `package-skeleton/` |
| --- | --- | --- |
| 门禁 | 五道（含 `check_architecture.py`） | 四道 + `build` + `twine check` |
| 测试 | 26 条 | 21 条 |
| 额外验证 | — | wheel 含 `py.typed`、从 wheel 装后能 import |

**复制骨架后的第一件事**：

- 服务型：删掉 `backend/app/modules/chat/` 与对应测试，把 `docs/` 里 chat 相关内容替换成自己的领域。
- 库型：把 `mylib` 全局替换成包名，删掉 `models.py` / `compat.py` 里的示例业务，重写 `README.md` 与 `CHANGELOG.md`。

骨架是范式，不是业务。

## 两份 `AGENTS.md` 与项目根的关系

`assets/project-skeleton/AGENTS.md` 与 `assets/package-skeleton/AGENTS.md` 是**给新项目用的模板**：
它们属于各自骨架，只描述"这个形态的项目该怎么写"。新建项目时按形态复制一份到该项目根目录，
之后它由**那个项目**维护——骨架里的原件不随项目改动而变，项目里的副本也不回写骨架。

因此本技能不维护任何"工作区级 AGENTS.md"，也不提供同步机制：工作区根目录若有 `AGENTS.md`，
它写的是**本工作区自己的**加载规则与路由，与本技能内的两份模板互不影响、互不覆盖。

## 快速自检（贴在心里）

> 一眼扫过去，文件应该是「banner 开头 → 几道 80 列的分割线 → 每个函数头顶一段 `"""` 起行的 reST docstring → 函数体内几段中文块注释」。
> 如果看起来不像这个形状，就是不合规。
