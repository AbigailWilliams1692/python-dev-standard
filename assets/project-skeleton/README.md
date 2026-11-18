# ai-assistant

> 由 `python-dev-standard` 技能提供的**参照工程**。它同时是一份可运行的样板：
> 拿不准某个文件该放哪一层、某段代码该怎么写时，看这里。
> 复制到自己的项目后，请把本段替换为项目的真实介绍。

## 这是什么

一个分层模块化单体的后端骨架，用「聊天」这一个业务域完整演示四层范式：

```
Interface (router) → Application (service) → Domain (domain) → Infrastructure (adapter)
```

依赖方向永远向内：`domain` 不 import 框架，`router` 不碰数据库，`service` 不写 SQL。
换数据库、换 LLM 供应商，只动 `infrastructure/` 一个目录。

## 快速开始

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
cp .env.example .env               # 按需填入真实配置

uvicorn app.main:app --reload --app-dir backend
```

启动后打开 `http://127.0.0.1:8000/docs` 查看自动生成的接口文档。

## 四道门

交付前必须全绿，CI 与 pre-commit 跑的是同一套：

```bash
python .workbuddy/skills/python-dev-standard/scripts/check_style.py backend/   # 规范
ruff format --check . && ruff check .                                           # 格式与 Lint
mypy                                                                            # 类型
pytest -q                                                                       # 测试
```

## 目录

```
backend/app/
  main.py            # 装配：中间件、异常处理、路由挂载
  container.py       # 依赖组装，唯一做 provider 分支的地方
  dependencies.py    # FastAPI 依赖提供者
  core/              # config / logging / errors / error_codes / middleware / health
  modules/chat/      # 业务域切片：domain / ports / service / schemas / router
  infrastructure/    # 适配器：内存仓储、fake 与 openai 两个 LLM 实现
backend/tests/       # unit + integration
docs/                # 交接文档：架构、数据流、实体、交互、开发记录、技术债、ADR
```

## 接入规范技能

规范不在本仓库内，通过 submodule 挂在 `.workbuddy/skills/` 下：

```bash
git submodule add <python-dev-standard 仓库地址> .workbuddy/skills/python-dev-standard
```

技能提供 `SKILL.md`（红线与路由）、`references/`（四份规范）、`scripts/check_style.py`（校验器）。
Agent 读 `AGENTS.md` 即可拿到常驻约束。

## 文档

| 文件 | 内容 |
| --- | --- |
| `docs/README.md` | 项目状态、能力清单、启动方式 |
| `docs/architecture.md` | 分层、模块清单、调用矩阵 |
| `docs/data-flow.md` | 主要数据流与失败处理 |
| `docs/entities.md` | 实体、不变量、状态机 |
| `docs/ux.md` | 终端用户交互与错误文案 |
| `docs/dev-log.md` | 每次变更的记录 |
| `docs/tech-debt.md` | 已知欠账 |
| `docs/adr/` | 架构决策记录 |

约定见技能内 `references/04-documentation.md`。

## 适用范围

本骨架面向**有 HTTP 接口的服务型项目**。如果要做的是纯 Python 库或 CLI 工具，
四层结构与 `main.py` / `container.py` 装配层并不适用，请改用库型骨架，
两者差异见技能内 `references/05-project-archetypes.md`。
