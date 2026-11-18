# mylib

> 这是一个**库型项目骨架**，用于演示与强制 Python 库的工程规范。
> 把 `mylib` 全局替换成你的包名，再删掉 `models.py` / `compat.py` 里的示例业务即可。

一句话说清这个库解决什么问题：**提供不可变的语义化版本值对象，以及基于它的兼容性判断。**

## 安装

```bash
pip install mylib
```

需要 Python 3.10 及以上。

## 快速开始

```python
from mylib import Version, is_compatible_with

current = Version.parse("1.4.2")
required = Version.parse("1.2.0")

print(current > required)                          # True
print(is_compatible_with(current, required))       # True
print(sorted([Version(1, 10, 0), Version(1, 9, 0)]))  # [1.9.0, 1.10.0]
```

## 公共 API

只有下列名字属于公开契约，其余都是实现细节，可能在次版本中变动。

| 名字 | 类型 | 说明 |
| --- | --- | --- |
| `Version` | 不可变值对象 | `parse()` 解析、`as_tuple` 取组件、支持比较与哈希 |
| `is_compatible_with` | 函数 | 按语义化版本判断已装版本是否满足要求 |
| `MyLibError` | 异常基类 | 捕获它即可处理本库所有错误 |
| `InvalidVersionError` | 异常 | 版本无法解析，同时继承 `ValueError` |
| `__version__` | 字符串 | 当前安装版本 |

## 稳定性承诺

- 遵循语义化版本：主版本变更才允许破坏性修改。
- 弃用流程：先 `DeprecationWarning` 提示，至少保留两个次版本后才移除。
- `0.x` 阶段不承诺兼容性，次版本号抬升即可能破坏。

## 开发

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

ruff format --check . && ruff check .   # 格式与静态检查
mypy                                    # 类型（strict）
pytest -q                               # 测试

python -m build                         # 构建 sdist 与 wheel
python -m twine check dist/*            # 校验发布元数据
```

### 规范门（可选但推荐）

```bash
# 把技能的规范校验器放到项目内，CI 才能真正执行风格门
cp <skill>/scripts/check_style.py scripts/check_style.py
python scripts/check_style.py src tests
```

## 目录结构

```
src/mylib/          # 源码，src layout 防止本地 cwd 遮蔽已安装版本
  __init__.py       # 唯一公共出口，__all__ 即契约
  _version.py       # 版本单一真源，pyproject 动态读取
  py.typed          # PEP 561 标记，缺了它 mypy 会忽略全部标注
  errors.py         # 异常层次，不带 HTTP 语义
  models.py         # 值对象与不变量
  compat.py         # 业务函数示例
tests/              # 只通过公开 API 测试，不碰私有实现
docs/               # 精简版交接文档
```

## 许可

MIT
