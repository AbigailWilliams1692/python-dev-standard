################################################################################
# @Project: mylib
# @File Path: tests/test_models.py
# @Description: Pin the invariants and ordering rules of the Version
#               value object. Every test names the behaviour it
#               protects, not the method.
# @Creation Date: 2026-11-18
# @Last Update: 2026-11-18
################################################################################

################################################################################
# Import Libraries
################################################################################
# Standard Libraries
from __future__ import annotations

from dataclasses import FrozenInstanceError

# Third-Party Libraries
import pytest

# Local Modules
from mylib import InvalidVersionError, Version


################################################################################
# Module Functions
################################################################################
def test_parse_reads_three_numeric_components() -> None:
    """
    Parse the canonical three part form into its components.

    :return: ``None``, assertions raise on mismatch.
    """
    parsed = Version.parse("1.2.3")
    assert parsed.as_tuple == (1, 2, 3)


def test_parse_accepts_prerelease_and_build_suffix() -> None:
    """
    Accept suffixes without letting them affect the numeric components.

    :return: ``None``, assertions raise on mismatch.
    """
    # 预发布与构建元数据都不参与排序，解析后应得到与纯数字版本相同的组件
    assert Version.parse("2.0.0-rc.1+build.5").as_tuple == (2, 0, 0)


@pytest.mark.parametrize(
    "text",
    ["", "1", "1.2", "1.2.3.4", "v1.2.3", "1.2.x", "  ", "1..3"],
)
def test_parse_rejects_malformed_text(text: str) -> None:
    """
    Reject anything that is not exactly three numeric components.

    :param text: Candidate string that must be refused.
    :return: ``None``, assertions raise on mismatch.
    """
    with pytest.raises(InvalidVersionError):
        Version.parse(text)


def test_negative_component_is_rejected_at_construction() -> None:
    """
    Refuse negative components even when callers bypass :meth:`Version.parse`.

    :return: ``None``, assertions raise on mismatch.
    """
    # 直接构造也要拦住，否则 parse 的校验形同虚设
    with pytest.raises(InvalidVersionError):
        Version(major=-1, minor=0, patch=0)


def test_versions_order_by_numeric_tuple() -> None:
    """
    Order versions by numeric tuple rather than by string comparison.

    :return: ``None``, assertions raise on mismatch.
    """
    # 字符串比较会把 1.10.0 排在 1.9.0 前面，这正是要防的回归
    ordered = sorted(
        [Version.parse("1.10.0"), Version.parse("1.9.0"), Version.parse("1.2.0")]
    )
    assert [str(item) for item in ordered] == ["1.2.0", "1.9.0", "1.10.0"]


def test_equal_versions_hash_equal() -> None:
    """
    Keep the hash consistent with equality so versions work as dict keys.

    :return: ``None``, assertions raise on mismatch.
    """
    # 值对象必须可哈希且相等即同哈希，否则按版本做缓存的代码会静默错乱
    assert Version.parse("1.2.3") == Version(1, 2, 3)
    assert hash(Version.parse("1.2.3")) == hash(Version(1, 2, 3))
    assert len({Version.parse("1.2.3"), Version(1, 2, 3)}) == 1


def test_version_is_immutable() -> None:
    """
    Prevent mutation after construction, since versions are shared as keys.

    :return: ``None``, assertions raise on mismatch.
    """
    version = Version.parse("1.2.3")

    # 冻结的 dataclass 必须拒绝赋值，这是值对象的核心承诺
    with pytest.raises(FrozenInstanceError):
        version.major = 9  # type: ignore[misc]


def test_str_always_renders_three_components() -> None:
    """
    Render three components so logs never confuse 1.2 with 1.2.0.

    :return: ``None``, assertions raise on mismatch.
    """
    assert str(Version(1, 2, 0)) == "1.2.0"
    assert str(Version(0, 0, 1)) == "0.0.1"
