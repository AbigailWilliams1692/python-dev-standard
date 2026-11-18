################################################################################
# @Project: ai-assistant
# @File Path: .workbuddy/skills/python-dev-standard/tests/conftest.py
# @Description: Shared fixtures for the checker and scaffold test suites
# @Creation Date: 2026-11-18
# @Last Update: 2026-11-18
################################################################################

################################################################################
# Import Libraries
################################################################################
# Standard Libraries
from __future__ import annotations

import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Final

# Third-Party Libraries
import pytest

################################################################################
# Module Constants
################################################################################
SKILL_ROOT: Final[Path] = Path(__file__).resolve().parent.parent
SCRIPTS_DIR: Final[Path] = SKILL_ROOT / "scripts"
SKELETON_DIR: Final[Path] = SKILL_ROOT / "assets" / "project-skeleton"

# 样例用行列表拼装：直接写字面量会让检查器把样例里的分区线当成真分区
_SECTION: Final[str] = "#" * 80

# 合规基线：任何用例都以它为起点做最小破坏，避免多条规则互相污染
VALID_MODULE: Final[str] = "\n".join(
    (
        _SECTION,
        "# @Project: demo",
        "# @File Path: demo/sample.py",
        "# @Description: Sample module used by the checker tests",
        "# @Creation Date: 2026-11-18",
        "# @Last Update: 2026-11-18",
        _SECTION,
        "",
        _SECTION,
        "# Import Libraries",
        _SECTION,
        "# Standard Libraries",
        "from __future__ import annotations",
        "",
        "",
        _SECTION,
        "# Module Constants",
        _SECTION,
        "LIMIT: int = 10",
        "",
        "",
        _SECTION,
        "# Module Functions",
        _SECTION,
        "def double(value: int) -> int:",
        '    """',
        "    Double a number.",
        "",
        "    :param value: Number to double.",
        "    :return: Twice the input value.",
        '    """',
        "    # 直接返回乘积，整个函数只有一个逻辑块",
        "    return value * 2",
        "",
    )
)


################################################################################
# Module Functions
################################################################################
def _run_script(
    script: Path,
    arguments: list[str],
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    """
    Execute one skill script and capture its output.

    :param script: Absolute path of the script to run.
    :param arguments: Command line arguments excluding the program name.
    :param cwd: Working directory, defaults to the current one.
    :return: Completed process carrying stdout, stderr and the exit code.
    """
    return subprocess.run(  # noqa: S603
        [sys.executable, str(script), *arguments],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=None if cwd is None else str(cwd),
        check=False,
    )


@pytest.fixture(name="skill_root")
def skill_root_fixture() -> Path:
    """
    Expose the skill root directory to the tests.

    :return: Absolute path of the skill package.
    """
    return SKILL_ROOT


@pytest.fixture(name="valid_module")
def valid_module_fixture() -> str:
    """
    Expose the compliant baseline module to the tests.

    :return: Source text that must pass every style rule.
    """
    return VALID_MODULE


@pytest.fixture(name="check_style")
def check_style_fixture(
    tmp_path: Path,
) -> Callable[..., subprocess.CompletedProcess[str]]:
    """
    Provide a runner that checks one source string with ``check_style.py``.

    :param tmp_path: Per test directory where the sample file is written.
    :return: Callable accepting source text and extra flags.
    """

    def _run(source: str, *extra: str) -> subprocess.CompletedProcess[str]:
        """
        Write the sample and run the style checker over its directory.

        :param source: Python source to validate.
        :param extra: Additional command line flags such as ``--strict``.
        :return: Completed process of the checker.
        """
        target = tmp_path / "sample.py"
        target.write_text(source, encoding="utf-8")
        return _run_script(SCRIPTS_DIR / "check_style.py", [str(tmp_path), *extra])

    return _run


@pytest.fixture(name="run_style_on_path")
def run_style_on_path_fixture() -> Callable[[Path], subprocess.CompletedProcess[str]]:
    """
    Provide a runner that checks an existing path instead of a sample.

    :return: Callable accepting a file or directory to validate.
    """

    def _run(target: Path) -> subprocess.CompletedProcess[str]:
        """
        Run the style checker over one existing target.

        :param target: File or directory to validate.
        :return: Completed process of the checker.
        """
        return _run_script(SCRIPTS_DIR / "check_style.py", [str(target)])

    return _run


@pytest.fixture(name="run_arch")
def run_arch_fixture() -> Callable[..., subprocess.CompletedProcess[str]]:
    """
    Provide a runner for the architecture checker.

    :return: Callable accepting arguments and an optional working directory.
    """

    def _run(
        *arguments: str,
        cwd: Path | None = None,
    ) -> subprocess.CompletedProcess[str]:
        """
        Run the architecture checker with the given arguments.

        :param arguments: Command line arguments such as a target directory.
        :param cwd: Working directory, defaults to the current one.
        :return: Completed process of the checker.
        """
        return _run_script(
            SCRIPTS_DIR / "check_architecture.py", list(arguments), cwd=cwd
        )

    return _run
