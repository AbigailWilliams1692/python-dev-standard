################################################################################
# @Project: ai-assistant
# @File Path: .workbuddy/skills/python-dev-standard/scripts/
#             check_architecture.py
# @Description: Enforce layering and cross domain import rules with plain AST
# @Creation Date: 2026-11-18
# @Last Update: 2026-11-18
################################################################################

################################################################################
# Import Libraries
################################################################################
# Standard Libraries
from __future__ import annotations

import argparse
import ast
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Final

################################################################################
# Module Constants
################################################################################
SKIP_DIRS: Final[frozenset[str]] = frozenset(
    {
        ".venv",
        "venv",
        "__pycache__",
        ".git",
        ".mypy_cache",
        ".ruff_cache",
        ".pytest_cache",
        "node_modules",
    }
)

# 领域层与端口层必须能脱离框架单独测试，这些包一律不许出现
FRAMEWORK_PACKAGES: Final[tuple[str, ...]] = (
    "fastapi",
    "starlette",
    "pydantic",
    "pydantic_settings",
    "sqlalchemy",
    "httpx",
    "requests",
    "redis",
    "celery",
    "uvicorn",
)

# 实现细节层：别的域只应通过 ports 或 domain 类型协作，不应直接抓这两个模块
IMPLEMENTATION_LAYERS: Final[frozenset[str]] = frozenset({"router", "service"})

# 只允许领域层与端口层引用的内核模块，其余 core 模块对它们关闭
CORE_ALLOWED_FOR_DOMAIN: Final[frozenset[str]] = frozenset(
    {"app.core.errors", "app.core.error_codes"}
)


################################################################################
# Module Functions
################################################################################
def _iter_python_files(root: Path) -> list[Path]:
    """
    Collect python files under the application package.

    :param root: Directory holding the ``app`` package.
    :return: Sorted python files, caches and vendor directories skipped.
    """
    app_dir = root / "app"
    if not app_dir.is_dir():
        return []
    collected: list[Path] = []
    for candidate in app_dir.rglob("*.py"):
        if SKIP_DIRS.intersection(candidate.parts):
            continue
        collected.append(candidate)
    return sorted(collected)


def _layer_of(relative: Path) -> tuple[str, str]:
    """
    Derive the architectural layer and owning domain of one file.

    :param relative: Path relative to the ``app`` package directory.
    :return: ``(layer, domain)``, domain is empty for non modular layers.
    """
    parts = relative.parts
    if parts[0] == "modules" and len(parts) >= 3:
        return Path(parts[2]).stem, parts[1]
    if parts[0] == "core":
        return "core", ""
    if parts[0] == "infrastructure":
        return "infrastructure", ""
    if parts[0] in {"main.py", "container.py", "dependencies.py"}:
        return "assembly", ""
    return "other", ""


def _resolve_import(node: ast.stmt, package: tuple[str, ...]) -> str:
    """
    Turn an import statement into an absolute dotted module name.

    :param node: Import or ImportFrom node.
    :param package: Package parts of the file holding the statement.
    :return: Absolute module name, empty when it cannot be resolved.
    """
    if isinstance(node, ast.Import):
        return node.names[0].name if node.names else ""
    if not isinstance(node, ast.ImportFrom):
        return ""

    # 相对导入按层级回退到父包，绝对导入直接拼接
    if node.level:
        keep = len(package) - (node.level - 1)
        base = package[:keep] if keep > 0 else ()
    else:
        base = ()
    prefix = ".".join(base)
    if node.module and prefix:
        return f"{prefix}.{node.module}"
    return node.module or prefix


def _imported_modules(tree: ast.AST, package: tuple[str, ...]) -> list[tuple[str, int]]:
    """
    List every module imported by a parsed file.

    :param tree: Parsed module.
    :param package: Package parts of the file being inspected.
    :return: Pairs of absolute module name and one based line number.
    """
    found: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            module = _resolve_import(node, package)
            if module:
                found.append((module, node.lineno))
    return found


def _matches(module: str, prefixes: Sequence[str]) -> str | None:
    """
    Return the first prefix that the module equals or starts with.

    :param module: Absolute module name being imported.
    :param prefixes: Candidate prefixes.
    :return: Matching prefix, or ``None`` when nothing matches.
    """
    for prefix in prefixes:
        if module == prefix or module.startswith(prefix + "."):
            return prefix
    return None


def _report(path: Path, line: int, code: str, message: str) -> None:
    """
    Print one violation in the shared report format.

    :param path: File holding the violation.
    :param line: One based line number of the import.
    :param code: Stable rule identifier used by CI greps.
    :param message: Human readable explanation.
    :return: ``None``, the line is written to stdout.
    """
    print(f"[ERROR] {path}:{line}  {code}  {message}")


def _check_framework_free(
    layer: str,
    path: Path,
    imports: Sequence[tuple[str, int]],
) -> list[str]:
    """
    Collect findings for imports a framework free layer must not have.

    :param layer: Layer name derived from the file path.
    :param path: File being inspected.
    :param imports: Imports of the file with their line numbers.
    :return: Findings collected as printable lines.
    """
    findings: list[str] = []
    if layer not in {"domain", "ports"}:
        return findings

    # 领域层与端口层必须能在没有 Web 框架的环境里跑，框架依赖一律报错
    for module, line in imports:
        hit = _matches(module, FRAMEWORK_PACKAGES)
        if hit is None:
            continue
        _report(
            path,
            line,
            "LAYER_FRAMEWORK",
            f"{layer} layer must not import framework package '{hit}'",
        )
        findings.append(f"{path}:{line}")
    return findings


def _check_infrastructure_leak(
    layer: str,
    path: Path,
    imports: Sequence[tuple[str, int]],
) -> list[str]:
    """
    Collect findings for upper layers reaching into infrastructure.

    :param layer: Layer name derived from the file path.
    :param path: File being inspected.
    :param imports: Imports of the file with their line numbers.
    :return: Findings collected as printable lines.
    """
    findings: list[str] = []
    if layer not in {"domain", "ports", "service", "router"}:
        return findings

    # 依赖方向只能向内：上层通过端口取能力，不能直接抓适配器
    for module, line in imports:
        if not _matches(module, ["app.infrastructure"]):
            continue
        _report(
            path,
            line,
            "LAYER_INFRASTRUCTURE",
            f"{layer} layer must depend on a port, not on '{module}'",
        )
        findings.append(f"{path}:{line}")
    return findings


def _check_core_independence(
    layer: str,
    path: Path,
    imports: Sequence[tuple[str, int]],
) -> list[str]:
    """
    Collect findings for the core package importing business domains.

    :param layer: Layer name derived from the file path.
    :param path: File being inspected.
    :param imports: Imports of the file with their line numbers.
    :return: Findings collected as printable lines.
    """
    findings: list[str] = []
    if layer != "core":
        return findings

    # core 是所有域的地基，反向依赖会立刻形成环
    for module, line in imports:
        if not _matches(module, ["app.modules"]):
            continue
        _report(
            path,
            line,
            "CORE_DEPENDENCY",
            f"core must not import business module '{module}'",
        )
        findings.append(f"{path}:{line}")
    return findings


def _check_core_surface(
    layer: str,
    path: Path,
    imports: Sequence[tuple[str, int]],
) -> list[str]:
    """
    Collect findings for domain reaching into non essential core modules.

    :param layer: Layer name derived from the file path.
    :param path: File being inspected.
    :param imports: Imports of the file with their line numbers.
    :return: Findings collected as printable lines.
    """
    findings: list[str] = []
    if layer not in {"domain", "ports"}:
        return findings

    # 领域层只用错误体系，配置与日志属于应用层的职责
    for module, line in imports:
        if not _matches(module, ["app.core"]):
            continue
        if any(
            module == allowed or module.startswith(allowed + ".")
            for allowed in CORE_ALLOWED_FOR_DOMAIN
        ):
            continue
        _report(
            path,
            line,
            "CORE_SURFACE",
            f"{layer} layer may only use {sorted(CORE_ALLOWED_FOR_DOMAIN)}",
        )
        findings.append(f"{path}:{line}")
    return findings


def _check_cross_domain(
    layer: str,
    domain: str,
    path: Path,
    imports: Sequence[tuple[str, int]],
) -> list[str]:
    """
    Collect findings for one domain importing another domain's internals.

    :param layer: Layer name derived from the file path.
    :param domain: Domain owning the file, empty outside modules.
    :param path: File being inspected.
    :param imports: Imports of the file with their line numbers.
    :return: Findings collected as printable lines.
    """
    findings: list[str] = []
    if not domain:
        return findings

    # 跨域只能碰对方的 ports 或纯领域类型，抓 router/service 等于绕过契约
    for module, line in imports:
        parts = module.split(".")
        if len(parts) < 4 or parts[0] != "app" or parts[1] != "modules":
            continue
        target_domain, target_layer = parts[2], parts[3]
        if target_domain == domain or target_layer not in IMPLEMENTATION_LAYERS:
            continue
        _report(
            path,
            line,
            "CROSS_DOMAIN",
            f"'{domain}' must not import {target_layer} of '{target_domain}'",
        )
        findings.append(f"{path}:{line}")
    return findings


def check_file(root: Path, path: Path) -> list[str]:
    """
    Run every layering rule against one file.

    :param root: Directory holding the ``app`` package.
    :param path: File to inspect.
    :return: Findings collected as printable lines.
    """
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError as error:
        _report(path, error.lineno or 1, "SYNTAX", f"syntax error: {error.msg}")
        return [str(path)]

    relative = path.relative_to(root / "app")
    layer, domain = _layer_of(relative)
    package = ("app", *relative.parent.parts) if relative.parent.parts else ("app",)
    imports = _imported_modules(tree, package)

    # 每条规则独立收集，便于后续按需增删而不互相影响
    findings: list[str] = []
    findings += _check_framework_free(layer, path, imports)
    findings += _check_infrastructure_leak(layer, path, imports)
    findings += _check_core_independence(layer, path, imports)
    findings += _check_core_surface(layer, path, imports)
    findings += _check_cross_domain(layer, domain, path, imports)
    return findings


def _parse_args(argv: list[str]) -> argparse.Namespace:
    """
    Parse command line arguments.

    :param argv: Arguments without the program name.
    :return: Parsed namespace.
    """
    parser = argparse.ArgumentParser(
        prog="check_architecture.py",
        description="Enforce layering rules derived from the engineering standard.",
    )
    parser.add_argument(
        "targets",
        nargs="*",
        default=["backend"],
        help="backend directory holding app/ (default: backend)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """
    Run the architecture check over every target directory.

    :param argv: Arguments without the program name, defaults to ``sys.argv``.
    :return: ``0`` when clean, ``1`` when at least one violation was found.
    """
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    findings: list[str] = []

    # 逐个目标展开，任何目标不存在都视为配置错误
    for raw in args.targets:
        root = Path(raw).resolve()
        if not root.is_dir():
            print(f"error: target directory not found: {raw}", file=sys.stderr)
            return 2
        for path in _iter_python_files(root):
            findings += check_file(root, path)

    print()
    print(f"ERROR {len(findings)} 项，WARN 0 项")
    return 1 if findings else 0


################################################################################
# Script Entry Point
################################################################################
if __name__ == "__main__":
    raise SystemExit(main())
