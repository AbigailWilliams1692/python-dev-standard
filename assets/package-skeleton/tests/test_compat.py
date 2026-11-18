################################################################################
# @Project: mylib
# @File Path: tests/test_compat.py
# @Description: Pin the compatibility rules, including the deliberate 0.x
#               exception where the minor number must match exactly.
# @Creation Date: 2026-11-18
# @Last Update: 2026-11-18
################################################################################

################################################################################
# Import Libraries
################################################################################
# Standard Libraries
from __future__ import annotations

# Third-Party Libraries
import pytest

# Local Modules
from mylib import Version, is_compatible_with


################################################################################
# Module Functions
################################################################################
@pytest.mark.parametrize(
    ("installed", "required", "expected"),
    [
        ("1.4.0", "1.2.0", True),
        ("1.2.0", "1.2.0", True),
        ("1.1.9", "1.2.0", False),
        ("2.0.0", "1.9.0", False),
        ("0.9.3", "0.9.0", True),
        ("0.10.0", "0.9.0", False),
    ],
)
def test_compatibility_matrix(installed: str, required: str, expected: bool) -> None:
    """
    Check the compatibility decision for a representative matrix.

    :param installed: Version present in the environment.
    :param required: Version the caller asks for.
    :param expected: Expected decision.
    :return: ``None``, assertions raise on mismatch.
    """
    result = is_compatible_with(Version.parse(installed), Version.parse(required))
    assert result is expected
