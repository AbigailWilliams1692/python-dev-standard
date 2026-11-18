################################################################################
# @Project: ai-assistant
# @File Path: .workbuddy/skills/python-dev-standard/tests/test_new_module.py
# @Description: End to end tests of the business domain scaffold
# @Creation Date: 2026-11-18
# @Last Update: 2026-11-18
################################################################################

################################################################################
# Import Libraries
################################################################################
# Standard Libraries
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

# Third-Party Libraries
import pytest

################################################################################
# Module Constants
################################################################################
EXPECTED_FILES: tuple[str, ...] = (
    "backend/app/modules/order/__init__.py",
    "backend/app/modules/order/domain.py",
    "backend/app/modules/order/ports.py",
    "backend/app/modules/order/service.py",
    "backend/app/modules/order/schemas.py",
    "backend/app/modules/order/router.py",
    "backend/app/infrastructure/persistence/in_memory_order_repository.py",
    "backend/tests/unit/test_order_service.py",
)


################################################################################
# Module Functions
################################################################################
@pytest.fixture(name="project")
def project_fixture(tmp_path: Path, skill_root: Path) -> Path:
    """
    Copy the reference skeleton into a throwaway directory.

    :param tmp_path: Per test directory.
    :param skill_root: Absolute path of the skill package.
    :return: Root of the copied project.
    """
    destination = tmp_path / "project"
    shutil.copytree(skill_root / "assets" / "project-skeleton", destination)
    return destination


def _run_scaffold(
    skill_root: Path,
    project: Path,
    *arguments: str,
) -> subprocess.CompletedProcess[str]:
    """
    Invoke the scaffold inside the copied project.

    :param skill_root: Absolute path of the skill package.
    :param project: Root of the copied project.
    :param arguments: Command line arguments passed to the scaffold.
    :return: Completed process carrying the scaffold output.
    """
    return subprocess.run(  # noqa: S603
        [sys.executable, str(skill_root / "scripts" / "new_module.py"), *arguments],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=str(project),
        check=False,
    )


def test_scaffold_creates_every_file(skill_root: Path, project: Path) -> None:
    """
    Generate one domain and confirm the full file set exists.

    :param skill_root: Absolute path of the skill package.
    :param project: Root of the copied project.
    :return: ``None``, assertions raise on mismatch.
    """
    result = _run_scaffold(skill_root, project, "order")
    assert result.returncode == 0, result.stderr
    for relative in EXPECTED_FILES:
        assert (project / relative).is_file(), relative


def test_scaffold_wires_container_and_routes(skill_root: Path, project: Path) -> None:
    """
    Confirm the generated domain is reachable from the application.

    :param skill_root: Absolute path of the skill package.
    :param project: Root of the copied project.
    :return: ``None``, assertions raise on mismatch.
    """
    _run_scaffold(skill_root, project, "order")

    # 三处接线缺一不可：容器持有服务、依赖提供者暴露服务、工厂挂载路由
    container = (project / "backend/app/container.py").read_text(encoding="utf-8")
    assert "order_service" in container

    providers = (project / "backend/app/dependencies.py").read_text(encoding="utf-8")
    assert "def get_order_service" in providers

    factory = (project / "backend/app/main.py").read_text(encoding="utf-8")
    assert "order_router" in factory

    codes = (project / "backend/app/core/error_codes.py").read_text(encoding="utf-8")
    assert "ORDER_NOT_FOUND" in codes


def test_generated_domain_passes_style_check(skill_root: Path, project: Path) -> None:
    """
    Confirm the scaffold output needs no manual style fixes.

    :param skill_root: Absolute path of the skill package.
    :param project: Root of the copied project.
    :return: ``None``, assertions raise on mismatch.
    """
    _run_scaffold(skill_root, project, "order")
    result = subprocess.run(  # noqa: S603
        [
            sys.executable,
            str(skill_root / "scripts" / "check_style.py"),
            str(project / "backend"),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert result.returncode == 0, result.stdout


def test_existing_domain_is_not_overwritten(skill_root: Path, project: Path) -> None:
    """
    Refuse to overwrite an existing domain without an explicit flag.

    :param skill_root: Absolute path of the skill package.
    :param project: Root of the copied project.
    :return: ``None``, assertions raise on mismatch.
    """
    _run_scaffold(skill_root, project, "order")
    result = _run_scaffold(skill_root, project, "order")
    assert result.returncode == 1
    assert "use --force" in result.stderr


def test_invalid_domain_name_is_rejected(skill_root: Path, project: Path) -> None:
    """
    Reject names that are not snake case ascii identifiers.

    :param skill_root: Absolute path of the skill package.
    :param project: Root of the copied project.
    :return: ``None``, assertions raise on mismatch.
    """
    result = _run_scaffold(skill_root, project, "Order")
    assert result.returncode == 2
    assert "snake_case" in result.stderr
