> 状态：可用（dev）｜最后核对：2026-11-18｜对应提交：未提交

# AI 助理（ai-assistant）

面向个人知识工作的对话式助手后端。当前形态是**可运行的四层架构样板**：一个 chat 业务域跑通
`router → service → domain ← adapter` 全链路，供后续业务域复制。

## 现在能做什么

| 能力 | 状态 | 入口 | 备注 |
| --- | --- | --- | --- |
| 健康检查 | ✅ 可用 | `GET /health` | 无依赖，供探针使用 |
| 创建会话 | ✅ 可用 | `POST /api/v1/chat/sessions` | 标题去空白，模型可覆盖 |
| 列出会话 | ✅ 可用 | `GET /api/v1/chat/sessions` | 游标分页，`limit ≤ 100` |
| 查看会话 | ✅ 可用 | `GET /api/v1/chat/sessions/{id}` | 越权按不存在处理 |
| 发送消息并生成回复 | ✅ 可用 | `POST /api/v1/chat/sessions/{id}/messages` | 默认 fake 模型，可切真实供应商 |
| 真实模型接入 | 🚧 未验证 | `AI_ASSISTANT_LLM_PROVIDER=openai` | 需供应商密钥，未做真实联调 |
| 数据持久化 | ⛔ 停用 | — | 当前为内存仓储，重启即丢 |

## 怎么跑起来

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[dev]"      # Windows
# source .venv/bin/activate && pip install -e ".[dev]"  # macOS / Linux
cp .env.example .env
uvicorn app.main:create_app --factory --reload
```

冒烟验证：

```bash
curl -s localhost:8000/health
curl -s -X POST localhost:8000/api/v1/chat/sessions \
  -H "Content-Type: application/json" -H "X-User-Id: u-1" \
  -d '{"title":"first chat"}'
```

## 目录导航

| 路径 | 内容 |
| --- | --- |
| `backend/app/core/` | 配置、日志、异常、错误码、追踪中间件 |
| `backend/app/modules/chat/` | 会话域四层样板（domain / ports / service / router / schemas） |
| `backend/app/infrastructure/` | 仓储与模型适配器实现 |
| `backend/tests/` | 单元测试（domain / service）与接口测试 |
| `docs/` | 交接文档，从 `architecture.md` 读起 |
| `.workbuddy/skills/python-dev-standard/` | 开发规范与校验器 |

## 文档索引

- [架构](architecture.md)｜[数据流](data-flow.md)｜[实体模型](entities.md)
- [用户交互](ux.md)｜[开发记录](dev-log.md)｜[技术债](tech-debt.md)
- [ADR-0001 分层模块化单体](adr/0001-four-layer-modular-monolith.md)
- [ADR-0002 端口与适配器](adr/0002-ports-and-adapters.md)

## 最近三次变更

1. **2026-11-18** `feat(chat)` 会话域四层样板 + `docs(standard)` 交接文档规范落地 —— 见 [dev-log](dev-log.md#2026-11-18--featchat-会话域四层样板)
2. **2026-11-16** `chore(style)` 规范列宽 60 → 80，全仓分隔线归一
3. **2026-10-26** `docs(standard)` 建立代码风格、工程设计、质量流程三份规范

## 已知限制

- 仓储是内存实现，进程退出即丢数据（见 [tech-debt](tech-debt.md) #1）。
- 消息接口无幂等键，客户端重试会产生两轮对话（#2）。
- 身份取自 `X-User-Id` 头且未做校验，仅可用于本地开发（#3）。
- 前端未实现，`ux.md` 描述的是已约定的交互契约，不是现有界面。
- 未上线，暂无 `runbook.md`。
