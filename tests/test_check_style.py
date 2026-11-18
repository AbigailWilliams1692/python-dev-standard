################################################################################
# @Project: ai-assistant
# @File Path: .workbuddy/skills/python-dev-standard/tests/test_check_style.py
# @Description: Regression tests pinning every rule of check_style.py
# @Creation Date: 2026-11-18
# @Last Update: 2026-11-18
################################################################################

################################################################################
# Import Libraries
################################################################################
# Standard Libraries
from __future__ import annotations

import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import TypeAlias

################################################################################
# Module Constants
################################################################################
SEPARATOR: str = "#" * 80

################################################################################
# Type Aliases
################################################################################
STYLE_RUNNER: TypeAlias = Callable[..., subprocess.CompletedProcess[str]]


################################################################################
# Module Functions
################################################################################
def test_compliant_module_passes(check_style: STYLE_RUNNER, valid_module: str) -> None:
    """
    Accept a module written exactly to the standard.

    :param check_style: Runner writing the sample and invoking the checker.
    :param valid_module: Baseline source used by every case.
    :return: ``None``, assertions raise on mismatch.
    """
    result = check_style(valid_module)
    assert result.returncode == 0, result.stdout
    assert "ERROR 0 项" in result.stdout


def test_missing_banner_is_rejected(
    check_style: STYLE_RUNNER, valid_module: str
) -> None:
    """
    Reject a file whose banner block is absent.

    :param check_style: Runner writing the sample and invoking the checker.
    :param valid_module: Baseline source used by every case.
    :return: ``None``, assertions raise on mismatch.
    """
    # 真正缺失 banner 的文件直接从 import 开始，首行不是分隔线
    broken = "from __future__ import annotations\n\nVALUE: int = 1\n"
    result = check_style(broken)
    assert result.returncode == 1
    assert "BANNER_MISSING" in result.stdout


def test_separator_must_be_exactly_80_columns(
    check_style: STYLE_RUNNER, valid_module: str
) -> None:
    """
    Reject a section rule that is not 80 characters wide.

    :param check_style: Runner writing the sample and invoking the checker.
    :param valid_module: Baseline source used by every case.
    :return: ``None``, assertions raise on mismatch.
    """
    broken = valid_module.replace(SEPARATOR, "#" * 60, 1)
    result = check_style(broken)
    assert result.returncode == 1
    assert "SEPARATOR_WIDTH" in result.stdout


def test_docstring_must_open_on_its_own_line(
    check_style: STYLE_RUNNER, valid_module: str
) -> None:
    """
    Reject a docstring whose description starts on the delimiter line.

    :param check_style: Runner writing the sample and invoking the checker.
    :param valid_module: Baseline source used by every case.
    :return: ``None``, assertions raise on mismatch.
    """
    broken = valid_module.replace(
        '    """\n    Double a number.',
        '    """Double a number.',
    )
    result = check_style(broken)
    assert result.returncode == 1
    assert "DOC_FIRSTLINE" in result.stdout


def test_every_parameter_must_be_documented(
    check_style: STYLE_RUNNER, valid_module: str
) -> None:
    """
    Reject a function whose docstring omits one of its parameters.

    :param check_style: Runner writing the sample and invoking the checker.
    :param valid_module: Baseline source used by every case.
    :return: ``None``, assertions raise on mismatch.
    """
    broken = valid_module.replace("    :param value: Number to double.\n", "")
    result = check_style(broken)
    assert result.returncode == 1
    assert "DOC_PARAM_MISSING" in result.stdout


def test_parameter_annotation_is_mandatory(
    check_style: STYLE_RUNNER, valid_module: str
) -> None:
    """
    Reject a parameter declared without a type annotation.

    :param check_style: Runner writing the sample and invoking the checker.
    :param valid_module: Baseline source used by every case.
    :return: ``None``, assertions raise on mismatch.
    """
    broken = valid_module.replace(
        "def double(value: int) -> int:",
        "def double(value) -> int:",
    )
    result = check_style(broken)
    assert result.returncode == 1
    assert "TYPE_PARAM" in result.stdout


def test_bare_except_is_rejected(check_style: STYLE_RUNNER, valid_module: str) -> None:
    """
    Reject a bare ``except`` clause swallowing every failure.

    :param check_style: Runner writing the sample and invoking the checker.
    :param valid_module: Baseline source used by every case.
    :return: ``None``, assertions raise on mismatch.
    """
    replacement = (
        "    # 故意裸捕获，用于验证规则\n"
        "    try:\n        return value * 2\n    except:\n        return 0"
    )
    broken = valid_module.replace(
        "    # 直接返回乘积，整个函数只有一个逻辑块\n    return value * 2",
        replacement,
    )
    result = check_style(broken)
    assert result.returncode == 1
    assert "EXCEPT_BARE" in result.stdout


def test_star_import_is_rejected(check_style: STYLE_RUNNER, valid_module: str) -> None:
    """
    Reject a wildcard import that hides the real namespace.

    :param check_style: Runner writing the sample and invoking the checker.
    :param valid_module: Baseline source used by every case.
    :return: ``None``, assertions raise on mismatch.
    """
    broken = valid_module.replace(
        "from __future__ import annotations\n",
        "from __future__ import annotations\n\nfrom os.path import *\n",
    )
    result = check_style(broken)
    assert result.returncode == 1
    assert "IMPORT_STAR" in result.stdout


def test_constant_only_module_needs_no_import_section(
    check_style: STYLE_RUNNER, valid_module: str
) -> None:
    """
    Accept a module with no imports and therefore no Import section.

    :param check_style: Runner writing the sample and invoking the checker.
    :param valid_module: Baseline source used by every case.
    :return: ``None``, assertions raise on mismatch.
    """
    # 纯常量模块（如 _version.py）不该被迫留一个空分区，那是噪音不是规范
    banner = "".join(valid_module.splitlines(keepends=True)[:8])
    constants_only = (
        f"{banner}\n{SEPARATOR}\n# Module Constants\n{SEPARATOR}\nMAX_ITEMS: int = 10\n"
    )
    # 先证明样例真的不含 import，否则这条用例什么都没验证
    assert "from __future__" not in constants_only
    result = check_style(constants_only)
    assert "SECTION_MISSING" not in result.stdout
    assert result.returncode == 0, result.stdout


def test_import_without_import_section_is_rejected(
    check_style: STYLE_RUNNER, valid_module: str
) -> None:
    """
    Keep rejecting a module that imports code but declares no section.

    :param check_style: Runner writing the sample and invoking the checker.
    :param valid_module: Baseline source used by every case.
    :return: ``None``, assertions raise on mismatch.
    """
    # 放宽只针对「没有 import」的文件，删分区标题但保留 import 仍须报错
    header = f"{SEPARATOR}\n# Import Libraries\n{SEPARATOR}\n"
    broken = valid_module.replace(header, "")
    # 证明替换真的发生，且 import 语句仍在，否则不是这条规则在生效
    assert "# Import Libraries" not in broken
    assert "from __future__ import annotations" in broken
    result = check_style(broken)
    assert result.returncode == 1
    assert "SECTION_MISSING" in result.stdout


def test_dunder_version_is_an_allowed_module_name(
    check_style: STYLE_RUNNER, valid_module: str
) -> None:
    """
    Allow ``__version__`` although it violates the constant naming rule.

    :param check_style: Runner writing the sample and invoking the checker.
    :param valid_module: Baseline source used by every case.
    :return: ``None``, assertions raise on mismatch.
    """
    # 版本单一真源在打包生态里固定叫 __version__，改名下游就取不到
    broken = valid_module.replace(
        "LIMIT: int = 10",
        'LIMIT: int = 10\n__version__ = "0.1.0"',
    )
    # 证明样例真的带上了 __version__，否则用例会在原样通过的情况下空转
    assert '__version__ = "0.1.0"' in broken
    result = check_style(broken)
    assert "MODULE_VAR_NAME" not in result.stdout
    assert result.returncode == 0, result.stdout


def test_pinyin_name_warns_without_failing(
    check_style: STYLE_RUNNER, valid_module: str
) -> None:
    """
    Warn on a pinyin identifier while keeping the exit code clean.

    :param check_style: Runner writing the sample and invoking the checker.
    :param valid_module: Baseline source used by every case.
    :return: ``None``, assertions raise on mismatch.
    """
    broken = valid_module.replace(
        "def double(value: int) -> int:",
        "def huoqu_yonghu(value: int) -> int:",
    )
    result = check_style(broken)
    assert "NAME_PINYIN" in result.stdout
    assert result.returncode == 0


def test_strict_turns_warnings_into_failures(
    check_style: STYLE_RUNNER, valid_module: str
) -> None:
    """
    Make ``--strict`` fail the run when only warnings were found.

    :param check_style: Runner writing the sample and invoking the checker.
    :param valid_module: Baseline source used by every case.
    :return: ``None``, assertions raise on mismatch.
    """
    broken = valid_module.replace(
        "def double(value: int) -> int:",
        "def huoqu_yonghu(value: int) -> int:",
    )
    result = check_style(broken, "--strict")
    assert result.returncode == 1


def test_module_template_stays_clean(
    skill_root: Path,
    run_style_on_path: Callable[[Path], subprocess.CompletedProcess[str]],
) -> None:
    """
    Guard the shipped module template against future rule regressions.

    :param skill_root: Absolute path of the skill package.
    :param run_style_on_path: Runner validating an existing target.
    :return: ``None``, assertions raise on mismatch.
    """
    result = run_style_on_path(skill_root / "assets" / "module_template.py")
    assert result.returncode == 0, result.stdout


def test_skeleton_stays_clean(
    skill_root: Path,
    run_style_on_path: Callable[[Path], subprocess.CompletedProcess[str]],
) -> None:
    """
    Guard the shipped reference project against future rule regressions.

    :param skill_root: Absolute path of the skill package.
    :param run_style_on_path: Runner validating an existing target.
    :return: ``None``, assertions raise on mismatch.
    """
    result = run_style_on_path(skill_root / "assets" / "project-skeleton" / "backend")
    assert result.returncode == 0, result.stdout
