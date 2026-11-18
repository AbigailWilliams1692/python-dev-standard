# 05 · 项目原型与骨架选型

> 状态：生效 ｜ 最后核对：2026-11-18 ｜ 对应提交：初始版本
>
> `assets/project-skeleton/` 只覆盖一类项目。这份文档回答：**别的类型怎么办，哪些能复用，哪些必须换。**
> 代码风格（01）与质量流程（03）与项目类型无关，永远适用；变的是**结构**。

---

## 1. 先分类，再选骨架

四类原型，判据是「谁调用你的代码」：

| 原型 | 调用方 | 典型产物 | 骨架 |
| --- | --- | --- | --- |
| **服务型** | 前端 / 其他服务，走 HTTP | REST API、BFF、内部微服务 | `assets/project-skeleton/` 直接可用 |
| **库型** | 其他 Python 代码，`import` | SDK、工具库、算法包 | 需裁剪，见第 3 节 |
| **CLI 型** | 终端用户，命令行 | 运维工具、代码生成器 | 库型 + 入口，见第 4 节 |
| **数据管道型** | 调度器，定时/事件触发 | ETL、报表、批处理 | 最轻，见第 5 节 |

判据如果模糊，看**交付形态**：要部署成常驻进程 → 服务型；要 `pip install` 进别人的环境 → 库型；两者都要 → 拆成两个包，库做内核、服务做外壳。

---

## 2. 复用矩阵

拿 `project-skeleton/` 往新项目上套之前，先看这张表。**✅ 直接抄，🔧 改路径/裁剪，❌ 不要抄。**

| 组成 | 服务型 | 库型 | CLI 型 | 数据管道 |
| --- | --- | --- | --- | --- |
| 01 代码风格（banner / 分区 / docstring / 命名） | ✅ | ✅ | ✅ | ✅ |
| `check_style.py` | ✅ | ✅ | ✅ | ✅ |
| `pyproject` 的 ruff / mypy / pytest 配置 | ✅ | 🔧 改 `src` | 🔧 | 🔧 |
| `.pre-commit-config.yaml` | ✅ | 🔧 改扫描目录 | 🔧 | 🔧 |
| CI 四道门结构 | ✅ | 🔧 加版本矩阵 | 🔧 | ✅ |
| 四层结构（interface/application/domain/infrastructure） | ✅ | ❌ | ❌ | ❌ |
| `domain.py` 不变量 + `ports.py` 协议 | ✅ | 🔧 只留核心模型 | ❌ | ❌ |
| `router.py` + `schemas.py`（HTTP 契约） | ✅ | ❌ | ❌ | ❌ |
| `container.py` / `dependencies.py`（DI 装配） | ✅ | ❌ 构造函数注入即可 | ❌ | ❌ |
| `main.py`（应用工厂 + 中间件） | ✅ | ❌ | ❌ | ❌ |
| 错误码体系（`http_status * 100 + 序号`） | ✅ | 🔧 去掉 HTTP 段 | 🔧 映射退出码 | 🔧 |
| `core/logging.py` 的 trace id | ✅ | ❌ 库不该配日志 | 🔧 只留格式化 | 🔧 |
| `core/config.py`（`BaseSettings`） | ✅ | 🔧 改为函数参数 | 🔧 | ✅ |
| `docs/` 七类文档 | ✅ | 🔧 见第 6 节 | 🔧 | 🔧 |
| `docs/ux.md`（终端用户旅程） | ✅ | ❌ 换成 API 文档 | ❌ 换成 `--help` 契约 | ❌ |
| `docs/data-flow.md`（HTTP 请求生命周期） | ✅ | 🔧 换成调用链 | 🔧 | 🔧 |
| `assets/module_template.py` | ✅ | ✅ | ✅ | ✅ |

粗算：**风格与工具链约 60% 可直接迁移，架构范式 40% 必须替换。**

---

## 3. 库型：为什么不能直接套服务型骨架

### 3.1 强行套会发生什么

四层结构的前提是「有一个请求从外面进来」。库没有请求，只有函数调用。硬套的后果很具体：

- `service.py` 里出现「既做参数校验又做业务计算又拼返回值」的巨型类——因为没有 router 帮它分担；
- `ports.py` 里定义了一堆只有一个实现的 `Protocol`——依赖倒置在没有外部边界时是纯成本；
- `schemas.py` 变成「给内部函数传参用的 dataclass」，与 `domain.py` 职责重叠，两处改一处漏一处。

**判断标准**：如果一个抽象只有一种实现，且没有替换需求，它就不该存在。库的边界是公开 API，不是 HTTP 路由。

### 3.2 库型骨架的必备要素

服务型骨架里**完全没有**、但库必须有的东西：

| 要素 | 为什么必须有 | 怎么落 |
| --- | --- | --- |
| `src/` layout | 仓库根目录直接放包，会导致「本地能 import、装完 import 不到」——因为 cwd 进了 `sys.path`，测试永远是绿的 | `src/<package>/`，`pyproject` 配 `[tool.setuptools.packages.find] where = ["src"]` |
| `py.typed` | 没有它，`mypy` 会忽略你所有的类型标注（PEP 561） | 空文件放在包根，并 `[tool.setuptools.package-data]` 显式包含 |
| 公共 API 清单 | 下游会 `from pkg import *`，导出面不明确等于把内部实现变成契约 | `__init__.py` 里 `__all__ = [...]`，只导出稳定接口 |
| 版本单一真源 | `pyproject` 与 `__version__` 两处写版本必然漂移 | `__init__.py` 用 `importlib.metadata.version("pkg")` 读，`pyproject` 里 `dynamic = ["version"]` 或反之，只留一处 |
| 可选依赖分组 | 库不该强迫所有用户装全部依赖 | `[project.optional-dependencies]` 按功能分组，如 `pandas` / `cli` |
| 多版本测试矩阵 | 库跑在别人的环境里，只测一个 Python 版本等于没测 | CI matrix 覆盖 `requires-python` 的上下限，至少 3.10 与最新稳定版 |
| 弃用策略 | 下游升级是渐进的，直接删接口会炸 | `warnings.warn(..., DeprecationWarning, stacklevel=2)`，保留两个 minor 版本 |
| 构建产物校验 | 装不上等于没发布 | `python -m build` 后用 `twine check dist/*`，并在干净 venv 里 `pip install` 验证 |

### 3.3 从服务型骨架裁剪成库型：十步

```text
1. 删掉 backend/app/{main,container,dependencies}.py
2. 删掉 backend/app/infrastructure/（除非库真的要包一层外部服务）
3. 把 backend/app/modules/<domain>/domain.py 提为 src/<pkg>/models.py（只留纯模型与不变量）
4. service.py 里的公开函数平铺到 src/<pkg>/ 下按能力分模块，不保留「服务类」
5. schemas.py 与 domain.py 合并，去掉 pydantic（除非对外部输入做校验是核心价值）
6. core/errors.py 保留，但去掉 http_status，改为纯 error code + 继承层次
7. backend/ → src/<pkg>/，加 py.typed，pyproject 改 where = ["src"]
8. docs/ 按下节精简，新增 CHANGELOG.md（库的变更日志是契约的一部分）
9. CI 加版本矩阵，新增 build + twine check 步骤
10. 在 README 里写清「稳定性承诺」：哪些接口算公开、破坏性变更怎么通知
```

### 3.4 一个最小可用的库型 `pyproject`

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "mypkg"
dynamic = ["version"]
description = "一句话说清这个库解决什么问题"
requires-python = ">=3.10"
dependencies = []                      # 库的默认依赖应尽量为空

[project.optional-dependencies]
cli = ["typer>=0.12"]
dev = ["pytest>=8.0", "pytest-asyncio>=0.23", "ruff>=0.5", "mypy>=1.10", "build", "twine"]

[tool.setuptools.packages.find]
where = ["src"]

[tool.setuptools.package-data]
mypkg = ["py.typed"]

[tool.setuptools.dynamic]
version = { attr = "mypkg.__version__" }

[tool.mypy]
python_version = "3.10"
strict = true
mypy_path = "src"
files = ["src"]

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
asyncio_mode = "auto"
```

注意 `pythonpath = ["src"]`：测试靠它而不是靠 `pip install -e`，这样 CI 里少一步安装也能发现 import 错误。

---

## 4. CLI 型：库型 + 一层入口

CLI 是库的特例：核心逻辑仍是可 import 的函数，命令行只是**薄壳**。

- 入口用 `[project.scripts]` 声明，不要写 `if __name__ == "__main__"` 了事：

```toml
[project.scripts]
mytool = "mypkg.cli:main"
```

- `cli.py` 只做三件事：解析参数 → 调 `mypkg` 里的函数 → 把异常翻译成退出码。**业务逻辑一行都不许写在这里。**
- 退出码要有约定（`0` 成功、`1` 通用错误、`2` 用法错误），并写进 `--help`。
- 错误一律走 `stderr`，正常输出走 `stdout`，否则管道组合会坏。
- 长任务要有 `--verbose` / `--quiet` 与进度输出；能 Ctrl-C 中断的地方要捕获 `KeyboardInterrupt` 并清理。

对应地，`docs/ux.md` 的「用户旅程」换成 `--help` 输出快照——那才是 CLI 的真实契约。

---

## 5. 数据管道型：最轻

一次运行、读完就退出，没有接口也没有下游 import。只需要：

- `01` 风格 + `check_style.py` + ruff/mypy/pytest；
- 单一入口脚本 + `src/<pipeline>/` 放可测函数；
- **幂等与断点续跑**是这类项目的核心质量属性，比分层重要得多；
- 配置与路径全部外置（环境变量或参数），脚本里不出现绝对路径；
- `docs/` 只需要 `README.md` + `dev-log.md` + `tech-debt.md`，不需要 ADR（决策密度低）。

---

## 6. `docs/` 按原型精简

`04-documentation.md` 的七类模板是服务型的完整集。按原型裁剪：

| 文档 | 服务型 | 库型 | CLI 型 | 数据管道 |
| --- | --- | --- | --- | --- |
| `README.md` | ✅ | ✅ | ✅ | ✅ |
| `architecture.md` | ✅ | ✅ 简化 | ✅ 简化 | 🔧 可并入 README |
| `data-flow.md` | ✅ | 🔧 改调用链 | 🔧 | ❌ |
| `entities.md` | ✅ | ✅ 有模型就写 | ❌ | ❌ |
| `ux.md` | ✅ | ❌ → API 文档 | ❌ → `--help` | ❌ |
| `dev-log.md` | ✅ | ✅ | ✅ | ✅ |
| `tech-debt.md` | ✅ | ✅ | ✅ | ✅ |
| `adr/` | ✅ | ✅ | ✅ | 🔧 少而精 |
| `CHANGELOG.md` | 🔧 对外发布才要 | **✅ 必填** | ✅ | ❌ |

库型为什么 `CHANGELOG` 必填：下游按版本升级，破坏性变更必须能提前看到。服务型是对内演进，`dev-log.md` 就够。

---

## 7. 与 01–04 的关系

| 文档 | 与项目类型的关系 |
| --- | --- |
| `01-code-style.md` | **完全无关**。banner、分区、docstring、命名，写什么项目都一样。 |
| `02-engineering-design.md` | 分层部分只对服务型适用；端口与适配器、依赖倒置原则通用。 |
| `03-quality-and-process.md` | **基本无关**。类型、异常、安全、测试、CI 对所有原型都成立。 |
| `04-documentation.md` | 模板是服务型全集，按第 6 节裁剪。 |
| **本文** | 决定「用哪套结构」，是选型入口。 |

一句话：**风格与质量是常量，结构是变量。**

---

## 8. 自检

- [ ] 我能一句话说清这个项目是谁调用我的代码（前端 / 下游 import / 终端 / 调度器）。
- [ ] 我没有把服务型的四层结构硬塞进库或脚本。
- [ ] 如果是库：有 `src/` layout、`py.typed`、明确的 `__all__`、单一版本源。
- [ ] 如果是库：CI 覆盖了 `requires-python` 的上下限。
- [ ] 如果是 CLI：业务逻辑不在 `cli.py` 里，退出码有约定。
- [ ] 如果是管道：幂等与断点续跑有明确设计，脚本里没有绝对路径。
- [ ] `docs/` 的数量与原型匹配，没有为了「齐全」写空模板。
