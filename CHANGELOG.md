# Changelog

格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，版本号遵循语义化版本。

**为什么规范也要记变更**：规则一改，已经按旧版写好的项目就会集体亮红灯。
使用者需要知道"哪条规则变了、我要改什么"，而不只是"版本号变大了"。

## [Unreleased]

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
