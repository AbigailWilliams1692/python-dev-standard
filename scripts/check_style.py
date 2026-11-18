################################################################################
# @Project: ai-assistant
# @File Path: .workbuddy/skills/python-dev-standard/scripts/
#             check_style.py
# @Description: Static checker enforcing the project python
#               style contract
# @Creation Date: 2026-10-26
# @Last Update: 2026-10-26
################################################################################

################################################################################
# Import Libraries
################################################################################
# Standard Libraries
from __future__ import annotations

import argparse
import ast
import re
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

################################################################################
# Module Constants
################################################################################
# 分隔线与 banner 的固定列宽，全项目唯一来源
SEPARATOR_TEXT: Final[str] = "#" * 80
MAX_LINE_LENGTH: Final[int] = 88
BANNER_FIELDS: Final[tuple[str, ...]] = (
    "Project",
    "File Path",
    "Description",
    "Creation Date",
    "Last Update",
)
BANNER_DATE_FIELDS: Final[frozenset[str]] = frozenset({"Creation Date", "Last Update"})

# 模块级区块的固定顺序，用于校验乱序
SECTION_ORDER: Final[tuple[str, ...]] = (
    "Import Libraries",
    "Module Constants",
    "Type Aliases",
    "Module Logger",
    "Module Functions",
    "Module Classes",
    "Script Entry Point",
)
CLASS_SECTION_TITLES: Final[frozenset[str]] = frozenset(
    {
        "Class Attributes",
        "Constructor Method",
        "Default Methods",
        "Core Instance Methods",
        "Utility Methods",
        "Helper Methods",
        "Serialization Methods",
        "Validation Methods",
        "Async Lifecycle Methods",
    }
)

# import 三分组的子标题，允许紧跟在 Import Libraries 分隔线之后
IMPORT_GROUP_TITLES: Final[frozenset[str]] = frozenset(
    {"Standard Libraries", "Third-Party Libraries", "Local Modules"}
)

# banner 的字段行与续行形态，续行需对齐到字段值的起始列
BANNER_FIELD_LINE_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"^# @(\w[\w ]*?): (.*)$"
)
BANNER_CONTINUATION_PATTERN: Final[re.Pattern[str]] = re.compile(r"^#( +)(\S.*)$")
MAX_BANNER_LINES: Final[int] = 40

# 命名与文档的正则约束
DATE_PATTERN: Final[re.Pattern[str]] = re.compile(r"^\d{4}-\d{2}-\d{2}$")
SECTION_TITLE_PATTERN: Final[re.Pattern[str]] = re.compile(r"^[A-Z][A-Za-z0-9 ]*$")
FUNC_NAME_PATTERN: Final[re.Pattern[str]] = re.compile(r"^_*[a-z][a-z0-9_]*$")
# 类名允许单下划线前缀，用于模块私有实现类
CLASS_NAME_PATTERN: Final[re.Pattern[str]] = re.compile(r"^_*[A-Z][A-Za-z0-9]*$")
CONST_NAME_PATTERN: Final[re.Pattern[str]] = re.compile(r"^_*[A-Z][A-Z0-9_]*$")
PARAM_FIELD_PATTERN: Final[re.Pattern[str]] = re.compile(r":param\s+([^:\n]+):")

# 模块级小写名字白名单：日志器、FastAPI 路由对象、包导出清单
# 这三类名字由框架或语言约定固定，改名会破坏生态习惯
MODULE_NAME_ALLOWLIST: Final[frozenset[str]] = frozenset(
    {
        "logger",
        "router",
        "__all__",
        # 打包生态固定名，库的版本单一真源必须用它，改名下游就取不到
        "__version__",
    }
)
SKIP_DIRS: Final[frozenset[str]] = frozenset(
    {
        ".git",
        ".venv",
        "venv",
        "__pycache__",
        "node_modules",
        ".mypy_cache",
        ".ruff_cache",
    }
)

# 拼音词表用于启发式检测，命中即提示（不保证完备，可能误报）
# 只收多音节词：单音节如 li/ci/qi 会与短英文单词撞车，误报率高，一律不入表
PINYIN_WORDS: Final[frozenset[str]] = frozenset(
    {
        # 数据与处理
        "shuju",
        "chuli",
        "huoqu",
        "baocun",
        "shanchu",
        "gengxin",
        "chaxun",
        "pici",
        "tongji",
        "shengcheng",
        "huancun",
        "suoyin",
        "fasong",
        "jieshou",
        "liebiao",
        "ziduan",
        "xinxi",
        "wendang",
        # 结构与配置
        "canshu",
        "fanhui",
        "peizhi",
        "mokuai",
        "jiekou",
        "lujing",
        "wenjian",
        "mingcheng",
        "gongneng",
        "qingqiu",
        "xiangying",
        # 用户与业务
        "yonghu",
        "shangpin",
        "jiage",
        "shuliang",
        "dingdan",
        "dingyue",
        "shenfen",
        "quanxian",
        "zhanghao",
        "denglu",
        "zhuce",
        "mima",
        # 会话与消息
        "huihua",
        "xiaoxi",
        "duihua",
        "huifu",
        "tuisong",
        "tongzhi",
        # 流程与状态
        "liucheng",
        "zhuangtai",
        "jieduan",
        "renwu",
        "diaodu",
        "wancheng",
        "zhixing",
        "diaoyong",
        "panduan",
        "jilu",
        "tishi",
        # 质量与测试
        "ceshi",
        "duanyan",
        "jiaoyan",
        "jiancha",
        "fugai",
        "yanzheng",
        # 异常与日志
        "cuowu",
        "yichang",
        "shibai",
        "chenggong",
        "rizhi",
        # 部署与运维
        "bushu",
        "huanjing",
        "chongshi",
        "chaoshi",
        "lianjie",
        "shengji",
    }
)


################################################################################
# Module Functions
################################################################################
def collect_python_files(targets: Sequence[Path]) -> list[Path]:
    """
    Expand the given targets into a sorted list of python files.

    :param targets: Files or directories to scan, expanded recursively.
    :return: Deduplicated python files, hidden and vendor directories skipped.
    :raises FileNotFoundError: If a target path does not exist.
    """
    # 先校验所有目标存在，避免静默漏扫
    for target in targets:
        if not target.exists():
            raise FileNotFoundError(f"target not found: {target}")

    # 文件直接收下，目录递归展开并剔除缓存目录
    collected: dict[Path, None] = {}
    for target in targets:
        if target.is_file():
            if target.suffix == ".py":
                collected[target.resolve()] = None
            continue
        for candidate in target.rglob("*.py"):
            if SKIP_DIRS.intersection(candidate.parts):
                continue
            collected[candidate.resolve()] = None

    # 排序保证报告输出稳定，便于 CI diff
    return sorted(collected)


def check_banner(
    path: Path,
    lines: Sequence[str],
    violations: list[Violation],
) -> None:
    """
    Validate the 80-column banner block, including wrapped field values.

    A field value may span several lines. Continuation lines start with ``#``
    followed by spaces that align the text to the field value column.

    :param path: Source file being checked.
    :param lines: File content split into lines without terminators.
    :param violations: Collector the findings are appended to.
    :return: ``None``, findings are written into ``violations``.
    """
    # 允许 shebang 占据首行，banner 紧随其后
    start = 1 if lines and lines[0].startswith("#!") else 0

    # 首行必须是 80 个 '#' 构成的边界线，否则视为 banner 缺失
    if start >= len(lines) or lines[start].rstrip() != SEPARATOR_TEXT:
        _report(
            violations,
            level="ERROR",
            path=path,
            line=start + 1,
            code="BANNER_MISSING",
            message="missing file banner at the top of the module",
        )
        return

    # 向下寻找收尾边界线，限定搜索范围避免扫描整个文件
    end = -1
    for index in range(start + 1, min(len(lines), start + MAX_BANNER_LINES)):
        if lines[index].rstrip() == SEPARATOR_TEXT:
            end = index
            break
    if end < 0:
        _report(
            violations,
            level="ERROR",
            path=path,
            line=start + 1,
            code="BANNER_UNCLOSED",
            message="banner is not closed by an 80-column separator",
        )
        return

    # 逐行解析字段与续行，同时校验每行不超过 80 列
    values: dict[str, str] = {}
    order: list[str] = []
    current = ""
    for index in range(start + 1, end):
        raw = lines[index].rstrip()
        if len(raw) > len(SEPARATOR_TEXT):
            _report(
                violations,
                level="ERROR",
                path=path,
                line=index + 1,
                code="BANNER_WIDTH",
                message=f"banner line exceeds 80 columns with {len(raw)}; wrap it",
            )

        field_match = BANNER_FIELD_LINE_PATTERN.match(raw)
        if field_match is not None:
            current = field_match.group(1)
            values[current] = field_match.group(2).strip()
            order.append(current)
            continue

        continuation = BANNER_CONTINUATION_PATTERN.match(raw)
        if continuation is not None and current:
            expected = len(current) + len("# @: ")
            actual = 1 + len(continuation.group(1))
            if actual != expected:
                _report(
                    violations,
                    level="ERROR",
                    path=path,
                    line=index + 1,
                    code="BANNER_ALIGN",
                    message=(
                        f"continuation of '{current}' must be indented to "
                        f"column {expected}, got {actual}"
                    ),
                )
            tail = continuation.group(2).strip()
            values[current] = f"{values[current]} {tail}".strip()
            continue

        _report(
            violations,
            level="ERROR",
            path=path,
            line=index + 1,
            code="BANNER_FORMAT",
            message=(
                "banner line must be '# @Field: value' or an aligned continuation"
            ),
        )

    # 字段顺序必须与规定一致；缺失、未知与错序分别报出
    if tuple(order) != BANNER_FIELDS:
        if set(order) == set(BANNER_FIELDS):
            _report(
                violations,
                level="ERROR",
                path=path,
                line=start + 1,
                code="BANNER_ORDER",
                message="banner fields are out of order",
            )
        else:
            for name in BANNER_FIELDS:
                if name not in values:
                    _report(
                        violations,
                        level="ERROR",
                        path=path,
                        line=start + 1,
                        code="BANNER_FIELD",
                        message=f"banner is missing field '@{name}'",
                    )
            for name in order:
                if name not in BANNER_FIELDS:
                    _report(
                        violations,
                        level="ERROR",
                        path=path,
                        line=start + 1,
                        code="BANNER_UNKNOWN",
                        message=f"banner has unregistered field '@{name}'",
                    )

    # 字段值不得为空，日期字段必须是 YYYY-MM-DD
    for name in BANNER_FIELDS:
        value = values.get(name)
        if value is None:
            continue
        if not value:
            _report(
                violations,
                level="ERROR",
                path=path,
                line=start + 1,
                code="BANNER_EMPTY",
                message=f"banner field '@{name}' must not be empty",
            )
        if name in BANNER_DATE_FIELDS and not DATE_PATTERN.match(value):
            _report(
                violations,
                level="ERROR",
                path=path,
                line=start + 1,
                code="BANNER_DATE",
                message=f"'@{name}' must use YYYY-MM-DD, got '{value}'",
            )


def check_separators(
    path: Path,
    lines: Sequence[str],
    violations: list[Violation],
) -> None:
    """
    Validate that every decorative separator renders to exactly 80 columns.

    :param path: Source file being checked.
    :param lines: File content split into lines without terminators.
    :param violations: Collector the findings are appended to.
    :return: ``None``, findings are written into ``violations``.
    """
    # 仅识别整行由 '#' 构成的分隔线，普通注释不参与
    for index, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped or set(stripped) != {"#"}:
            continue
        rendered = len(line.rstrip())
        if rendered != len(SEPARATOR_TEXT):
            _report(
                violations,
                level="ERROR",
                path=path,
                line=index,
                code="SEPARATOR_WIDTH",
                message=f"separator must render 80 columns, got {rendered}",
            )


def check_line_length(
    path: Path,
    lines: Sequence[str],
    violations: list[Violation],
) -> None:
    """
    Reject source lines wider than the agreed column limit.

    :param path: Source file being checked.
    :param lines: File content split into lines without terminators.
    :param violations: Collector the findings are appended to.
    :return: ``None``, findings are written into ``violations``.
    """
    # 按字符计宽，中文字符同样记 1 列，与主流编辑器配置一致
    for index, line in enumerate(lines, start=1):
        if len(line) > MAX_LINE_LENGTH:
            _report(
                violations,
                level="ERROR",
                path=path,
                line=index,
                code="LINE_WIDTH",
                message=f"line exceeds {MAX_LINE_LENGTH} columns, got {len(line)}",
            )


def check_sections(
    path: Path,
    lines: Sequence[str],
    violations: list[Violation],
    *,
    has_import: bool = True,
) -> None:
    """
    Validate module and class section titles, their order and their borders.

    :param path: Source file being checked.
    :param lines: File content split into lines without terminators.
    :param violations: Collector the findings are appended to.
    :param has_import: Whether the module contains any import statement.
    :return: ``None``, findings are written into ``violations``.
    """
    # 区块标题定义为「紧跟 80 列分隔线的 Title Case 注释行」
    found: list[tuple[int, int, str]] = []
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped.startswith("# ") or stripped.count("#") != 1:
            continue
        if index == 0 or not _is_separator(lines[index - 1]):
            continue
        title = stripped[2:].strip()
        if not SECTION_TITLE_PATTERN.match(title):
            continue
        indent = len(line) - len(line.lstrip(" "))
        found.append((index, indent, title))

    # 模块级必须存在 Import Libraries 区块，但只有真的写了 import 才要求，
    # 否则一个只放常量的模块被迫留一个空区块，属于噪音而非规范
    module_titles = [title for _, indent, title in found if indent == 0]
    if has_import and "Import Libraries" not in module_titles:
        _report(
            violations,
            level="ERROR",
            path=path,
            line=1,
            code="SECTION_MISSING",
            message="module must declare an 'Import Libraries' section",
        )

    # 模块级标题必须登记在 SECTION_ORDER 且顺序递增
    last_order = -1
    for index, indent, title in found:
        if indent != 0:
            continue
        if title not in SECTION_ORDER:
            if title in IMPORT_GROUP_TITLES:
                continue
            _report(
                violations,
                level="WARN",
                path=path,
                line=index + 1,
                code="SECTION_UNKNOWN",
                message=f"section '{title}' is not registered in SECTION_ORDER",
            )
            continue
        current = SECTION_ORDER.index(title)
        if current < last_order:
            _report(
                violations,
                level="ERROR",
                path=path,
                line=index + 1,
                code="SECTION_ORDER",
                message=f"section '{title}' is out of order",
            )
        last_order = max(last_order, current)

    # 类内标题必须登记在 CLASS_SECTION_TITLES，防止自造区块名
    for index, indent, title in found:
        if indent == 0:
            continue
        if title not in CLASS_SECTION_TITLES:
            _report(
                violations,
                level="WARN",
                path=path,
                line=index + 1,
                code="SECTION_UNKNOWN",
                message=(
                    f"class section '{title}' is not registered in CLASS_SECTION_TITLES"
                ),
            )


def check_ast(path: Path, tree: ast.Module, violations: list[Violation]) -> None:
    """
    Run naming, annotation, docstring and import checks over a module AST.

    :param path: Source file being checked.
    :param tree: Parsed abstract syntax tree of the module.
    :param violations: Collector the findings are appended to.
    :return: ``None``, findings are written into ``violations``.
    """
    # 逐节点分发，顶层只关心函数、类、导入与模块级常量
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            _check_function(node, path, violations)
        elif isinstance(node, ast.ClassDef):
            _check_class(node, path, violations)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            _check_import(node, path, violations)
        elif isinstance(node, ast.Assign):
            _check_module_assignment(node, path, violations)
        elif isinstance(node, ast.AnnAssign):
            _check_annotated_assignment(node, path, violations)

    # 全树扫描裸 except，必须替换为具体异常类型
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler) and node.type is None:
            _report(
                violations,
                level="ERROR",
                path=path,
                line=node.lineno,
                code="EXCEPT_BARE",
                message="bare 'except:' is forbidden, catch a specific exception",
            )


def render_report(violations: Sequence[Violation]) -> str:
    """
    Render violations as a stable, grouped text report.

    :param violations: All findings collected across scanned files.
    :return: Report text ready to be written to stdout.
    """
    # 按文件与行号排序，保证同一份代码输出结果完全一致
    ordered = sorted(
        violations,
        key=lambda item: (str(item.path), item.line, item.code),
    )
    errors = [item for item in ordered if item.level == "ERROR"]
    warnings = [item for item in ordered if item.level == "WARN"]

    # 单行一条，前缀固定宽度便于机器解析与肉眼扫读
    rows = [
        f"[{item.level:<5}] {_relative(item.path)}:{item.line}  "
        f"{item.code}  {item.message}"
        for item in errors + warnings
    ]
    rows.append("")
    rows.append(f"ERROR {len(errors)} 项，WARN {len(warnings)} 项")
    return "\n".join(rows)


def main(argv: Sequence[str] | None = None) -> int:
    """
    Run the style checker over the given paths.

    :param argv: Command line arguments excluding the program name.
    :return: ``0`` when no error is found, ``1`` otherwise.
    :raises SystemExit: Never raised directly; argparse may raise on bad usage.
    """
    # 解析命令行，默认扫描当前工作目录
    parser = argparse.ArgumentParser(description="Check project python style contract")
    parser.add_argument("paths", nargs="*", default=["."], help="files or directories")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="treat warnings as errors",
    )
    args = parser.parse_args(argv)

    # 展开目标文件，跳过不存在的路径并给出明确提示
    targets = [Path(item) for item in args.paths]
    try:
        files = collect_python_files(targets)
    except FileNotFoundError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1

    # 逐文件检查，IO 与语法错误单独归类，不影响其余文件
    violations: list[Violation] = []
    for file_path in files:
        violations.extend(check_file(file_path))

    # 输出报告并按门禁语义决定退出码
    print(render_report(violations))
    has_error = any(item.level == "ERROR" for item in violations)
    has_warn = any(item.level == "WARN" for item in violations)
    if has_error or (args.strict and has_warn):
        return 1
    return 0


def check_file(path: Path) -> list[Violation]:
    """
    Check a single python file against every implemented rule.

    :param path: Absolute path of the file to check.
    :return: All violations found in this file, possibly empty.
    """
    violations: list[Violation] = []

    # 读取源码，编码或权限问题直接记为一条错误后跳过
    try:
        source = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        _report(
            violations,
            level="ERROR",
            path=path,
            line=0,
            code="READ_FAILED",
            message=f"cannot read file: {exc}",
        )
        return violations
    lines = source.splitlines()

    # 只有真的出现 import 语句才强制 Import 区块，纯常量模块不必留空区块
    has_import = any(
        re.match(r"^\s*(?:import|from)\s", line) is not None for line in lines
    )

    # 先做纯文本层面的 banner、分隔线、行宽与区块检查
    check_banner(path, lines, violations)
    check_separators(path, lines, violations)
    check_line_length(path, lines, violations)
    check_sections(path, lines, violations, has_import=has_import)

    # 再做语法树层面的命名、标注与 docstring 检查
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as exc:
        _report(
            violations,
            level="ERROR",
            path=path,
            line=exc.lineno or 0,
            code="SYNTAX",
            message=f"syntax error: {exc.msg}",
        )
        return violations
    check_ast(path, tree, violations)
    return violations


def _check_function(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    path: Path,
    violations: list[Violation],
) -> None:
    """
    Validate naming, annotations and docstring of one function or method.

    :param node: Function or async function node to inspect.
    :param path: Source file being checked.
    :param violations: Collector the findings are appended to.
    :return: ``None``, findings are written into ``violations``.
    """
    # 函数名必须 snake_case，禁止拼音
    if not FUNC_NAME_PATTERN.match(node.name):
        _report(
            violations,
            level="ERROR",
            path=path,
            line=node.lineno,
            code="NAME_FUNC",
            message=f"function '{node.name}' must use snake_case",
        )
    _check_pinyin(node.name, path, node.lineno, violations)

    # 收集全部形参，self 与 cls 不参与标注与文档校验
    arguments = [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]
    if node.args.vararg is not None:
        arguments.append(node.args.vararg)
    if node.args.kwarg is not None:
        arguments.append(node.args.kwarg)
    checked = [item for item in arguments if item.arg not in {"self", "cls"}]

    # 每个形参必须有类型标注，缺失即报错
    for item in checked:
        if item.annotation is None:
            _report(
                violations,
                level="ERROR",
                path=path,
                line=node.lineno,
                code="TYPE_PARAM",
                message=(
                    f"parameter '{item.arg}' of '{node.name}' lacks a type annotation"
                ),
            )
    if node.returns is None:
        _report(
            violations,
            level="ERROR",
            path=path,
            line=node.lineno,
            code="TYPE_RETURN",
            message=f"function '{node.name}' lacks a return type annotation",
        )

    # __init__ 仅在纯赋值时可省略 docstring，其余一律必须有
    docstring = ast.get_docstring(node, clean=False)
    if docstring is None:
        if node.name != "__init__":
            _report(
                violations,
                level="ERROR",
                path=path,
                line=node.lineno,
                code="DOC_MISSING",
                message=f"function '{node.name}' lacks a docstring",
            )
        return

    # 首行必须只保留定界符，描述另起一行
    _check_docstring_open(docstring, node.name, node.lineno, path, violations)

    # docstring 中的 :param 必须与形参一一对应，不得遗漏或多余
    documented = {
        _param_name(match.group(1)) for match in PARAM_FIELD_PATTERN.finditer(docstring)
    }
    declared = {item.arg for item in checked}
    for missing in sorted(declared - documented):
        _report(
            violations,
            level="ERROR",
            path=path,
            line=node.lineno,
            code="DOC_PARAM_MISSING",
            message=f"docstring of '{node.name}' misses ':param {missing}:'",
        )
    for extra in sorted(documented - declared):
        _report(
            violations,
            level="WARN",
            path=path,
            line=node.lineno,
            code="DOC_PARAM_UNKNOWN",
            message=f"docstring of '{node.name}' documents unknown param '{extra}'",
        )

    # 有返回值的函数必须写 :return:，None 返回不强制
    documents_return = ":return:" in docstring or ":returns:" in docstring
    returns_value = node.returns is not None and not _returns_none(node.returns)
    if returns_value and not documents_return:
        _report(
            violations,
            level="ERROR",
            path=path,
            line=node.lineno,
            code="DOC_RETURN",
            message=f"docstring of '{node.name}' misses ':return:'",
        )


def _check_class(node: ast.ClassDef, path: Path, violations: list[Violation]) -> None:
    """
    Validate naming, docstring and member methods of one class.

    :param node: Class definition node to inspect.
    :param path: Source file being checked.
    :param violations: Collector the findings are appended to.
    :return: ``None``, findings are written into ``violations``.
    """
    # 类名必须 PascalCase，禁止拼音
    if not CLASS_NAME_PATTERN.match(node.name):
        _report(
            violations,
            level="ERROR",
            path=path,
            line=node.lineno,
            code="NAME_CLASS",
            message=f"class '{node.name}' must use PascalCase",
        )
    _check_pinyin(node.name, path, node.lineno, violations)

    # 类必须有 docstring，用 :param: 与 :ivar: 描述构造与属性
    class_docstring = ast.get_docstring(node, clean=False)
    if class_docstring is None:
        _report(
            violations,
            level="ERROR",
            path=path,
            line=node.lineno,
            code="DOC_CLASS",
            message=f"class '{node.name}' lacks a docstring",
        )
    else:
        _check_docstring_open(class_docstring, node.name, node.lineno, path, violations)

    # 递归检查类内方法，保持与顶层函数同一套规则
    for item in node.body:
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
            _check_function(item, path, violations)


def _check_import(
    node: ast.Import | ast.ImportFrom,
    path: Path,
    violations: list[Violation],
) -> None:
    """
    Reject wildcard imports and validate import grouping order.

    :param node: Import or import-from node to inspect.
    :param path: Source file being checked.
    :param violations: Collector the findings are appended to.
    :return: ``None``, findings are written into ``violations``.
    """
    # 禁止 import *，它会破坏静态检查与命名空间
    if isinstance(node, ast.ImportFrom) and any(
        alias.name == "*" for alias in node.names
    ):
        _report(
            violations,
            level="ERROR",
            path=path,
            line=node.lineno,
            code="IMPORT_STAR",
            message="wildcard import is forbidden",
        )


def _check_module_assignment(
    node: ast.Assign,
    path: Path,
    violations: list[Violation],
) -> None:
    """
    Require upper snake case for module level constants.

    :param node: Assignment node at module level.
    :param path: Source file being checked.
    :param violations: Collector the findings are appended to.
    :return: ``None``, findings are written into ``violations``.
    """
    # 只检查简单名字赋值，解包与下标赋值不在此范围
    for target in node.targets:
        if not isinstance(target, ast.Name):
            continue
        _check_constant_name(target.id, target.lineno, path, violations)


def _check_annotated_assignment(
    node: ast.AnnAssign,
    path: Path,
    violations: list[Violation],
) -> None:
    """
    Require upper snake case for annotated module level names.

    :param node: Annotated assignment node at module level.
    :param path: Source file being checked.
    :param violations: Collector the findings are appended to.
    :return: ``None``, findings are written into ``violations``.
    """
    # 仅处理模块级简单名字，类内字段由类自身语义决定
    if isinstance(node.target, ast.Name):
        _check_constant_name(node.target.id, node.target.lineno, path, violations)


def _check_constant_name(
    name: str,
    line: int,
    path: Path,
    violations: list[Violation],
) -> None:
    """
    Validate that a module level name follows the constant convention.

    :param name: Identifier being validated.
    :param line: One-based line number of the assignment.
    :param path: Source file being checked.
    :param violations: Collector the findings are appended to.
    :return: ``None``, findings are written into ``violations``.
    """
    # 常量名同样要做拼音检查，避免 YONGHU_ID 这类写法漏网
    _check_pinyin(name, path, line, violations)

    # 日志器等约定俗成的模块级小写名字允许豁免
    if name in MODULE_NAME_ALLOWLIST or CONST_NAME_PATTERN.match(name):
        return
    _report(
        violations,
        level="WARN",
        path=path,
        line=line,
        code="NAME_MODULE",
        message=(
            f"module level name '{name}' should be UPPER_SNAKE_CASE "
            "or moved to local scope"
        ),
    )


def _check_pinyin(
    name: str,
    path: Path,
    line: int,
    violations: list[Violation],
) -> None:
    """
    Report identifiers that look like pinyin instead of English words.

    :param name: Identifier being validated.
    :param path: Source file being checked.
    :param line: One-based line number of the definition.
    :param violations: Collector the findings are appended to.
    :return: ``None``, findings are written into ``violations``.
    """
    # 按下划线与大小写切词，任何一段命中拼音词表即提示
    for part in re.split(r"[_\W]+", name):
        for token in re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?![a-z])", part):
            if token.lower() in PINYIN_WORDS:
                _report(
                    violations,
                    level="WARN",
                    path=path,
                    line=line,
                    code="NAME_PINYIN",
                    message=f"identifier '{name}' looks like pinyin, use English words",
                )
                return


def _check_docstring_open(
    docstring: str,
    owner: str,
    line: int,
    path: Path,
    violations: list[Violation],
) -> None:
    """
    Require the docstring to open with a bare delimiter line.

    ``ast.get_docstring`` keeps the raw layout, so a compliant docstring
    starts with a newline because its first line holds only the triple quote.

    :param docstring: Raw docstring text returned by :func:`ast.get_docstring`.
    :param owner: Name of the function or class owning the docstring.
    :param line: One-based line number of the definition.
    :param path: Source file being checked.
    :param violations: Collector the findings are appended to.
    :return: ``None``, findings are written into ``violations``.
    """
    # 首字符是换行，说明 '"""' 独立成行、描述从第二行开始
    if not docstring.startswith("\n"):
        _report(
            violations,
            level="ERROR",
            path=path,
            line=line,
            code="DOC_FIRSTLINE",
            message=(
                f"docstring of '{owner}' must leave the first line as a bare "
                "delimiter and start the description on the second line"
            ),
        )


def _is_separator(line: str) -> bool:
    """
    Tell whether a line is an 80-column separator made of '#' characters.

    :param line: Single source line without its terminator.
    :return: ``True`` when the line renders exactly 80 columns of '#'.
    """
    # 允许 4 空格缩进，但渲染后的总宽必须恰好 80 列
    stripped = line.strip()
    return bool(stripped) and set(stripped) == {"#"} and len(line.rstrip()) == 80


def _param_name(raw: str) -> str:
    """
    Extract the parameter name from a reST param field body.

    :param raw: Text between ``:param`` and the closing colon, e.g. ``int user_id``.
    :return: The trailing identifier, e.g. ``user_id``.
    """
    # reST 允许 ':param int user_id:' 写法，取最后一个词作为名字
    tokens = raw.strip().split()
    return tokens[-1] if tokens else ""


def _returns_none(annotation: ast.expr) -> bool:
    """
    Tell whether a return annotation denotes ``None``.

    :param annotation: Return annotation expression of a function.
    :return: ``True`` when the annotation is the ``None`` constant.
    """
    # 仅识别 '-> None' 这一种显式写法
    return isinstance(annotation, ast.Constant) and annotation.value is None


def _report(
    violations: list[Violation],
    *,
    level: str,
    path: Path,
    line: int,
    code: str,
    message: str,
) -> None:
    """
    Append one violation to the collector.

    :param violations: Collector list that receives the violation.
    :param level: Severity, either ``ERROR`` or ``WARN``.
    :param path: Source file the violation belongs to.
    :param line: One-based line number, ``0`` when unknown.
    :param code: Stable short code describing the rule.
    :param message: Human readable explanation.
    :return: ``None``, the violation is appended in place.
    """
    # 统一构造入口，保证字段完整且不可变
    violations.append(
        Violation(level=level, path=path, line=line, code=code, message=message)
    )


def _relative(path: Path) -> str:
    """
    Render a path relative to the current working directory when possible.

    :param path: Path to render.
    :return: Relative POSIX path, falling back to the absolute path.
    """
    # 报告里用相对路径更短，也便于 CI 日志定位
    try:
        return path.relative_to(Path.cwd()).as_posix()
    except ValueError:
        return path.as_posix()


################################################################################
# Module Classes
################################################################################
@dataclass(frozen=True)
class Violation:
    """
    A single style violation detected in one source file.

    :param level: Severity, either ``ERROR`` or ``WARN``.
    :param path: Source file the violation belongs to.
    :param line: One-based line number, ``0`` when not line specific.
    :param code: Stable short code used for filtering and reporting.
    :param message: Human readable explanation of the violation.
    """

    ############################################################################
    # Class Attributes
    ############################################################################
    level: str
    path: Path
    line: int
    code: str
    message: str


################################################################################
# Script Entry Point
################################################################################
if __name__ == "__main__":
    # UTF-8 输出，避免 Windows 控制台因中文报告抛编码异常
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
