# 开发记录

> 一条记录 = 一个合并的 PR。倒序排列，最新在最上。格式见 `04-documentation.md` 3.7。

## 2026-11-18 · refactor(core): 上提响应信封，补幂等与限流，接入 CI

- **变更**：`Envelope` 从 `modules/chat/schemas.py` 上提到 `core/schemas.py`；
  新增 `core/idempotency.py`（端口 + 内存实现，带 TTL）与 `core/rate_limit.py`（令牌桶）；
  新增 6 条测试；新增 `.github/workflows/ci.yaml`（五道门）与 `.pre-commit-config.yaml`。
- **为什么**：`Envelope` 是所有域共用的响应契约，留在 chat 里会迫使新域跨域 import 或重复定义，
  两者都违反分层；幂等此前只登记在 tech-debt 里没有可复用实现，重试重复计费是真风险；
  四道门此前靠人工执行，没有流水线等于没有门禁。
- **影响面**：`core` 新增 3 个文件、`chat/schemas.py` 删除 1 个类、`chat/router.py` 改 import；
  测试 20 → 26；对接口路径与响应体无影响（信封形状不变）。
- **验证**：`check_style.py` 0 告警 / `check_architecture.py` 0 告警 / `ruff` 全过 /
  `mypy` 27 文件无问题 / `pytest` 26 passed。
- **文档**：`architecture.md` 的 core 描述、模块表、跨切面表；`tech-debt.md` #2 与 #5 状态更新；
  本条目。
- **遗留**：幂等实现未接 HTTP 层（#2 仍开放）；限流器未接入任何端点，需在确定配额后挂到发消息接口。

## 2026-11-18 · feat(chat): 会话域四层样板

- **变更**：新增 `core`（配置 / 日志 / 异常 / 错误码 / 追踪中间件 / 健康检查）与 `modules/chat`
  （domain / ports / service / schemas / router），新增内存仓储与 fake 模型适配器，
  新增 OpenAI 兼容适配器（未联调），新增 20 个测试。
- **为什么**：先立地基再扩业务。配置、日志、异常是所有模块的公共依赖，晚做会导致每个域自己发明一套；
  chat 作为第一个域必须做成可复制范式，否则后续每个域结构都不一样。
- **影响面**：接口（新增 4 个端点 + 健康检查）、配置（新增 12 个环境变量）、
  依赖（fastapi / uvicorn / pydantic-settings / httpx）。
- **验证**：`pytest -q` → 20 passed；`ruff check` / `ruff format --check` / `mypy` /
  `check_style.py` 全部 0 告警。
- **文档**：`architecture.md` 模块清单、`data-flow.md` DF-1~DF-3、`entities.md`、
  `ux.md` 错误码表、ADR-0001、ADR-0002。
- **遗留**：内存仓储无持久化（tech-debt #1）；消息接口无幂等（#2）；身份仅靠请求头（#3）。

## 2026-11-18 · docs(standard): 新增交接文档规范

- **变更**：新增 `references/04-documentation.md`，定义 `docs/` 目录地图、七类文档模板、
  更新义务矩阵与 Agent 收工清单；同步建立 `docs/` 实例文档。
- **为什么**：多模型 / 多 Agent 接力开发时，上下文断裂造成的返工成本高于编码本身；
  人类用户也需要一条 3 分钟接管项目的路径。
- **影响面**：无代码变更；`SKILL.md` 与 `AGENTS.md` 增加路由与红线。
- **验证**：文档内路径、命令、错误码与代码逐条核对；`check_style.py` 仍为 0 告警。
- **文档**：本次新增的全部 `docs/` 文件。
- **遗留**：`ux.md` 为契约稿，前端实现后需补截图与组件路径。

## 2026-11-16 · chore(style): 规范列宽 60 → 80

- **变更**：banner 边界线与分区线由 60 列改为 80 列；`check_style.py` 常量与提示同步；
  三份规范文档中的示例与文字同步；既有 `scripts/md_to_speech.py` 的分隔线批量归一。
- **为什么**：60 列在高分屏上留白过多，长描述频繁折行影响扫读。
- **影响面**：全部 `.py` 文件的分隔线；无行为变化。
- **验证**：`check_style.py` 对 `assets` / `scripts` / `backend` 均为 0 告警；模板可正常运行。
- **文档**：01 / 02 / 03 与 `AGENTS.md`、`SKILL.md` 的列宽说明。
- **遗留**：无。

## 2026-10-26 · docs(standard): 建立三份开发规范

- **变更**：新增 `01-code-style.md`、`02-engineering-design.md`、`03-quality-and-process.md`，
  以及 `assets/module_template.py`、`scripts/check_style.py`、根目录 `AGENTS.md`。
- **为什么**：AI 生成的代码风格漂移严重，需要可机检的硬约束，而不只是散文式建议。
- **影响面**：无业务代码；新增工具链与 CI 门禁约定。
- **验证**：校验器自检 0 告警；用反例样本验证 17 类违规可被拦下。
- **文档**：三份规范本身。
- **遗留**：拼音词表为启发式，存在漏判与误报（tech-debt #5）。
