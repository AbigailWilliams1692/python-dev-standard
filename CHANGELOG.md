# Changelog

格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，版本号遵循语义化版本。

**为什么规范也要记变更**：规则一改，已经按旧版写好的项目就会集体亮红灯。
使用者需要知道"哪条规则变了、我要改什么"，而不只是"版本号变大了"。

## [Unreleased]

### 移除

- **`scripts/setup-agents-link.sh` + `scripts/hooks/post-checkout`**：取消 `AGENTS.md`
  硬链接同步机制。骨架自带的 `AGENTS.md` 是「某个形态的项目该怎么写」的模板，拿它决定
  整个工作区的 `AGENTS.md` 属于职责错位；且硬链接会被 `checkout` / `pull` 打断，
  需要钩子修补，维护成本高于收益。工作区级 `AGENTS.md` 改为独立文件，
  只写**加载时机与入口路由**，不复述规范正文。
- **`SKILL.md` 的「维护本仓库：`AGENTS.md` 的单源硬链接」**：随上述改动删除，
  替换为「两份 `AGENTS.md` 与项目根的关系」，明确模板复制到项目后归该项目所有。

## [0.2.0] - 2026-11-18

### 新增

- **`assets/package-skeleton/`**：库型 / CLI 参照工程。`src/` layout、`py.typed`、
  `__all__` 公共契约、版本单一真源、无 HTTP 依赖的异常层次、21 条测试、
  多版本 CI 矩阵、构建与装机冒烟校验、精简四份交接文档。
- **`SKILL.md` 的「第 0 步：先判断项目形态」**：四问决策表，明确何时用服务型骨架、
  何时用库型骨架，并指出两份 `AGENTS.md` 不可混用的原因。
- **`05` 的可判定清单**：把「选哪个骨架」从判断题变成逐条回答题，并列出两种真实发生过的误判。

### 变更

- `check_style.py`：模块无 import 语句时不再强制要求 `Import Libraries` 分区。
  纯常量模块（如 `_version.py`）被迫留空分区属于噪音，不是规范。
  有 import 却缺分区仍然报 `SECTION_MISSING`。
- `check_style.py`：`__version__` 加入模块级名字白名单。它是打包生态的固定名，
  按 `UPPER_SNAKE_CASE` 要求改名会让下游取不到版本。
- `tests/` 由 23 条增至 26 条，覆盖上述两条规则变更，并加入防假通过断言。
- `05-project-archetypes.md`：库型由「需手工裁剪」改为「有现成骨架」，
  保留十步裁剪清单供改造已有仓库时使用。

## [0.1.0] - 2026-11-18

首个可用版本。

### 新增

- **代码风格规范**（`references/01-code-style.md`）：80 列 banner、固定分区顺序、
  reST docstring、类内区块、命名规则、10 条反模式。
- **工程设计规范**（`references/02-engineering-design.md`）：四层架构、模块划分、
  端口与适配器、前后端契约、可观测性、测试策略，以及新增业务域的十步 SOP。
- **质量与流程规范**（`references/03-quality-and-process.md`）：类型、异常体系、
  结构化日志、安全、测试分层、Git 与 CI 门禁。
- **交接文档规范**（`references/04-documentation.md`）：`docs/` 目录地图、七类模板、
  更新义务矩阵、防腐机制。
- **项目原型选型**（`references/05-project-archetypes.md`）：服务型 / 库型 / CLI 型 /
  数据管道的骨架差异与裁剪清单。
- **`scripts/check_style.py`**：31 条可判定规则的 AST 校验器，纯标准库。
- **`scripts/check_architecture.py`**：分层依赖与跨域引用校验，5 类规则。
- **`scripts/new_module.py`**：业务域脚手架，生成 8 个文件并自动接线，产物零改动过门禁。
- **`assets/module_template.py`**：单文件骨架，可直接运行。
- **`assets/project-skeleton/`**：完整参照工程（core 地基 + chat 域四层范式 + 适配器 +
  26 条测试 + 9 份交接文档 + 2 份 ADR），含 CI、pre-commit、README、CHANGELOG。
- **`tests/`**：23 条测试覆盖三个脚本，用正样本与反样本钉死每条规则。

### 变更

- 分区线与 banner 宽度由 60 列调整为 **80 列**（更符合实际编辑器的视觉习惯）。
  旧版文件需要把纯 `#` 行补齐到 80 列，`check_style.py` 会逐行报出。

### 修复

- `03` 中越权示例与「不区分不存在与无权限」规则自相矛盾：越权改为抛 `NotFoundError`。
- `04` 的自检清单补充文档元信息（状态 / 最后核对 / 对应提交）的刷新要求。

### 安全

- 规范明确禁止：硬编码凭据、裸 `except` 吞异常、`shell=True` 拼接、f-string 拼 SQL、
  `import *`、可变默认参数、接口层返回 ORM 实体。
