# mylib · 交接文档入口

> 状态：初始骨架 ｜ 最后核对：2026-11-18 ｜ 对应提交：初始版本

## 这个库是什么

提供不可变的语义化版本值对象，以及基于它的兼容性判断。

**它明确不是**：不是服务，没有 HTTP 接口；不读环境变量；不配置日志；不依赖任何第三方运行时库。

## 当前能力

| 能力 | 状态 | 入口 |
| --- | --- | --- |
| 解析 `1.2.3` 形式版本 | ✅ 可用 | `Version.parse()` |
| 按数值比较与排序 | ✅ 可用 | `Version.__lt__` / `sorted()` |
| 作为字典键与集合成员 | ✅ 可用 | `frozen=True` + dataclass 生成的 `__eq__` |
| 语义化兼容性判断 | ✅ 可用 | `is_compatible_with()` |
| 预发布版本参与排序 | ⛔ 未实现 | 见 `tech-debt.md` #1 |
| 命令行入口 | ⛔ 未实现 | 需要时按 `05` 第 4 节加 `cli.py` + `[project.scripts]` |

## 开发命令

```bash
pip install -e ".[dev]"

ruff format --check . && ruff check .    # 格式与 lint
mypy                                     # 类型（strict）
pytest -q                                # 测试

python -m build                          # 构建
python -m twine check dist/*             # 发布前元数据校验
python -m venv /tmp/smoke && /tmp/smoke/bin/pip install dist/*.whl   # 装机验证
```

## 目录导航

```
src/mylib/      库源码，src layout
tests/          只通过公开 API 测试
docs/           本目录，四份交接文档
```

## 文档索引

| 文件 | 内容 | 什么时候读 |
| --- | --- | --- |
| 本文件 | 状态、能力、命令 | 每次开工第一步 |
| `architecture.md` | 模块职责、依赖方向、关键决策 | 决定代码放哪个模块 |
| `dev-log.md` | 变更记录（六字段） | 动同一区域之前 |
| `tech-debt.md` | 已知欠账与取舍 | 想「顺手修一下」之前 |
| `../CHANGELOG.md` | 面向使用者的变更 | 任何影响公共 API 的改动 |
| `../README.md` | 面向使用者的说明 | 新增功能后同步 |

## 最近三次变更

| 日期 | 变更 |
| --- | --- |
| 2026-11-18 | 建立库型骨架：`Version` 值对象、兼容性判断、五道门全绿 |
| 2026-11-18 | 补 CI 多版本矩阵、构建校验与装机冒烟测试 |
| 2026-11-18 | 补 `docs/` 四份精简交接文档 |

## 已知限制

- 预发布与构建元数据（`-rc.1`、`+build.5`）会被解析但不参与比较，见 `tech-debt.md` #1。
- `0.x` 阶段的兼容判断要求次版本号完全一致，这是刻意设计，不是 bug。
- 没有 CLI，也没有发布到 PyPI 的流水线。
