# 开发记录

> 状态：生效 ｜ 最后核对：2026-11-18 ｜ 对应提交：初始版本

每条记录六项齐全：**变更 / 为什么 / 影响面 / 验证 / 文档 / 遗留**。
缺任何一项都视为不符合 `04-documentation.md` 的更新义务。

新增记录写在最上面。

---

## 2026-11-18 · feat: 建立库型骨架

**变更**
建立 `assets/package-skeleton/`：src layout、`Version` 值对象、`is_compatible_with()`、
异常层次、`py.typed`、四份精简文档、CI 多版本矩阵与构建校验。

**为什么**
技能原先只有服务型骨架（`project-skeleton/`）。`05-project-archetypes.md` 说明了库型要裁剪什么，
但只有文字没有可运行产物——Agent 拿到说明仍然要手抄，而手抄必然漏 `py.typed` 与 `__all__`。

**影响面**
只新增目录，不触碰 `project-skeleton/`。技能根 README 与 `SKILL.md` 的选型路由需同步补一条。

**验证**
```
check_style.py src tests   0 ERROR / 0 WARN
ruff check / format        全过
mypy --strict              5 个源文件无问题
pytest                     21 passed
python -m build            成功产出 sdist 与 wheel
twine check                双 PASSED
wheel 内容                 含 mylib/py.typed 与 dist-info/licenses/LICENSE
装机冒烟                   从 wheel 装到干净目录后 import 成功，版本 0.1.0
```

**文档**
本文件、`docs/README.md`、`docs/architecture.md`、`docs/tech-debt.md`、
`CHANGELOG.md`、`README.md`、`AGENTS.md`。

**遗留**
预发布版本不参与排序（tech-debt #1）；未建发布流水线（#3）；coverage 无阈值（#4）。

---

## 2026-11-18 · ci: 补构建校验与装机冒烟

**变更**
CI 拆成 `quality`（3.10–3.13 矩阵）与 `package`（构建 + 元数据 + py.typed 断言 + 装机冒烟）两个 job。

**为什么**
库最常见的两类事故，静态检查都发现不了：一是 `py.typed` 没进 wheel，下游类型全部失效；
二是「本地能 import、装完 import 不到」，因为没有真的从 wheel 装一次。

**影响面**
只影响 CI，不改运行时行为。

**验证**
本地等价执行：`python -m venv` 后从 `dist/*.whl` 安装、在 `/tmp` 下 import 成功。

**文档**
`docs/README.md` 命令段、本文件。

**遗留**
CI 尚未在 GitHub 上真实跑过，首次推送后需确认矩阵全绿。
