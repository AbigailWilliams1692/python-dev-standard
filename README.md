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

## 安装

作为项目级技能放入 `.workbuddy/skills/`：

```bash
# 方式一：子模块（推荐，可跟随上游升级）
git submodule add <本仓库地址> .workbuddy/skills/python-dev-standard

# 方式二：直接复制
cp -r python-dev-standard <你的项目>/.workbuddy/skills/
```

然后把 `assets/project-skeleton/AGENTS.md` 复制到项目根目录——它是 Agent 的常驻入口。

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
│   ├── module_template.py        单文件骨架
│   └── project-skeleton/         完整参照工程，五道门全绿的样板
├── scripts/                 # 只放要执行的代码
│   ├── check_style.py
│   ├── check_architecture.py
│   └── new_module.py
└── tests/                   # 验证这三个脚本本身
```

## 适用范围

`project-skeleton/` 面向**有 HTTP 接口的服务型项目**。要做纯 Python 库、CLI 工具或数据管道，
四层结构与 DI 装配层并不适用——差异与裁剪清单见 `references/05-project-archetypes.md`。

代码风格（01）与质量流程（03）与项目类型无关，任何 Python 项目都适用。

## 自检

本仓库自己也遵守这套规范：

```bash
python scripts/check_style.py scripts/ tests/
python scripts/check_architecture.py assets/project-skeleton/backend
pytest tests/ -q
```

- 三个脚本自身通过 `check_style.py`（0 ERROR / 0 WARN）。
- `assets/project-skeleton/` 通过 `check_style` / `check_architecture` / `ruff` / `mypy` / `pytest`。
- `tests/` 覆盖两个检查器的每条规则（正样本 + 反样本），防止规则被改坏后静默失效。

## 版本

见 [CHANGELOG.md](CHANGELOG.md)。规范改动会影响已采纳的项目，因此规则变更一律记入变更日志。

## 许可

[MIT](LICENSE)
