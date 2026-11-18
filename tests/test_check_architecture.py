################################################################################
# @Project: ai-assistant
# @File Path: .workbuddy/skills/python-dev-standard/tests/
#             test_check_architecture.py
# @Description: Regression tests pinning the layering rules of the checker
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
# Type Aliases
################################################################################
ARCH_RUNNER: TypeAlias = Callable[..., subprocess.CompletedProcess[str]]


################################################################################
# Module Functions
################################################################################
def _make_project(root: Path, module_source: str, *, target: str = "domain") -> Path:
    """
    Build a minimal application tree holding one business module.

    :param root: Temporary directory that becomes the project root.
    :param module_source: Source of the file placed inside the module.
    :param target: Layer file name inside the module, without suffix.
    :return: Path of the backend directory holding ``app``.
    """
    backend = root / "backend"
    module = backend / "app" / "modules" / "demo"
    module.mkdir(parents=True)
    (backend / "app" / "__init__.py").write_text("", encoding="utf-8")
    (backend / "app" / "modules" / "__init__.py").write_text("", encoding="utf-8")
    (module / "__init__.py").write_text("", encoding="utf-8")
    (module / f"{target}.py").write_text(module_source, encoding="utf-8")
    return backend


def test_reference_skeleton_is_clean(
    skill_root: Path,
    run_arch: ARCH_RUNNER,
) -> None:
    """
    Confirm the shipped reference project respects every layering rule.

    :param skill_root: Absolute path of the skill package.
    :param run_arch: Runner invoking the architecture checker.
    :return: ``None``, assertions raise on mismatch.
    """
    backend = skill_root / "assets" / "project-skeleton" / "backend"
    result = run_arch(str(backend))
    assert result.returncode == 0, result.stdout
    assert "ERROR 0 项" in result.stdout


def test_domain_must_not_import_framework(
    tmp_path: Path,
    run_arch: ARCH_RUNNER,
) -> None:
    """
    Reject a domain module that pulls in a web framework.

    :param tmp_path: Temporary directory used as the project root.
    :param run_arch: Runner invoking the architecture checker.
    :return: ``None``, assertions raise on mismatch.
    """
    backend = _make_project(tmp_path, "import fastapi\n")
    result = run_arch(str(backend))
    assert result.returncode == 1
    assert "LAYER_FRAMEWORK" in result.stdout


def test_domain_must_not_reach_infrastructure(
    tmp_path: Path,
    run_arch: ARCH_RUNNER,
) -> None:
    """
    Reject a domain module importing a concrete adapter.

    :param tmp_path: Temporary directory used as the project root.
    :param run_arch: Runner invoking the architecture checker.
    :return: ``None``, assertions raise on mismatch.
    """
    backend = _make_project(
        tmp_path,
        "from app.infrastructure.persistence import store\n",
    )
    result = run_arch(str(backend))
    assert result.returncode == 1
    assert "LAYER_INFRASTRUCTURE" in result.stdout


def test_core_must_not_import_business_module(
    tmp_path: Path,
    run_arch: ARCH_RUNNER,
) -> None:
    """
    Reject the core package depending on a business domain.

    :param tmp_path: Temporary directory used as the project root.
    :param run_arch: Runner invoking the architecture checker.
    :return: ``None``, assertions raise on mismatch.
    """
    backend = tmp_path / "backend"
    core = backend / "app" / "core"
    core.mkdir(parents=True)
    (backend / "app" / "__init__.py").write_text("", encoding="utf-8")
    (core / "__init__.py").write_text("", encoding="utf-8")
    (core / "helper.py").write_text(
        "from app.modules.demo.domain import Demo\n",
        encoding="utf-8",
    )
    result = run_arch(str(backend))
    assert result.returncode == 1
    assert "CORE_DEPENDENCY" in result.stdout


def test_cross_domain_service_import_is_rejected(
    tmp_path: Path,
    run_arch: ARCH_RUNNER,
) -> None:
    """
    Reject one domain reaching into another domain's service.

    :param tmp_path: Temporary directory used as the project root.
    :param run_arch: Runner invoking the architecture checker.
    :return: ``None``, assertions raise on mismatch.
    """
    backend = _make_project(
        tmp_path,
        "from app.modules.other.service import OtherService\n",
        target="router",
    )
    result = run_arch(str(backend))
    assert result.returncode == 1
    assert "CROSS_DOMAIN" in result.stdout


def test_missing_target_exits_with_configuration_error(
    tmp_path: Path,
    run_arch: ARCH_RUNNER,
) -> None:
    """
    Report a configuration error when the target directory does not exist.

    :param tmp_path: Temporary directory used as the project root.
    :param run_arch: Runner invoking the architecture checker.
    :return: ``None``, assertions raise on mismatch.
    """
    result = run_arch(str(tmp_path / "absent"))
    assert result.returncode == 2
