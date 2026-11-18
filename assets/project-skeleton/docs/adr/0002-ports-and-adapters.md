# ADR-0002 用端口与适配器隔离存储和模型供应商

> 状态：已采纳｜日期：2026-11-16｜决策者：项目所有者 + 开发 Agent｜关联：`modules/chat/ports.py`、`container.py`

## 背景

两件事一定会变：数据存哪里、模型用谁。当前没有数据库、没有供应商账号，但代码必须现在就能跑通、
以后又能直接换掉。同时测试不能依赖网络与付费接口。

## 决策

Application 层定义 `Protocol` 端口（`ChatSessionRepository`、`LlmPort`），
`infrastructure/` 提供实现，`container.py` 在启动时选择实现并注入。

- 领域与用例只依赖端口，不 import 任何 SDK 或驱动；
- 端口的返回值是领域对象（`LlmCompletion`），不是供应商 DTO；
- 供应商分支只允许出现在 `container._build_llm` 一处。

## 备选方案

| 方案 | 优点 | 代价 | 结论 |
| --- | --- | --- | --- |
| 直接调 SDK / 直接用 dict 存 | 代码最少 | 测试要打网络；换供应商改遍业务代码 | 不采纳 |
| 抽象基类 `ABC` + 继承 | 运行期可校验、可共享默认实现 | 强制继承，测试替身也要继承，耦合更紧 | 不采纳 |
| `Protocol` + 工厂 | 结构化类型，测试替身零依赖；静态可查 | 运行期不校验，需靠测试覆盖契约 | **采纳** |

## 后果

- 正面：单测注入 `FakeLlmAdapter` 与内存仓储，20 个测试 0.2 秒跑完、无网络；
  换供应商 = 新增 adapter + 改工厂一行；换存储同理。
- 负面：多一层间接，读代码要跳一次；`Protocol` 不做运行期检查，实现漏方法只能在调用时报错。
- 风险：适配器可能悄悄泄露供应商字段（例如把原始 JSON 塞进 `detail`）。
  触发条件：出现 `dict[str, Any]` 穿过端口时，必须改为显式值对象。

## 验证方式

- 单测中不存在对 `openai` / `httpx` 的依赖（`grep -r "httpx" backend/tests` 应为空）。
- 新增供应商时，diff 只应包含 `infrastructure/llm/` 与 `container.py`。
- 若某天出现两个以上适配器且分支超过 3 个，改为注册表（`dict[str, Factory]`）而非 if 链。

## 相关

- [ADR-0001 分层模块化单体](0001-four-layer-modular-monolith.md)
- 规范依据：`02-engineering-design.md` 第 2.3、4.2 节；`03-quality-and-process.md` 第 2.2 节
