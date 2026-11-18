################################################################################
# @Project: mylib
# @File Path: src/mylib/models.py
# @Description: Immutable value objects exposed by the library, plus the
#               parsing and ordering rules that keep them trustworthy.
# @Creation Date: 2026-11-18
# @Last Update: 2026-11-18
################################################################################

################################################################################
# Import Libraries
################################################################################
# Standard Libraries
from __future__ import annotations

import re
from dataclasses import dataclass
from functools import total_ordering
from typing import Final

# Local Modules
from mylib.errors import InvalidVersionError

################################################################################
# Module Constants
################################################################################
# 只解析 主.次.修订 三段；预发布与构建元数据允许存在但不参与排序，
# 因为排序语义依赖它们时，跨生态的版本号规则并不一致
_VERSION_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"^(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)"
    r"(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$"
)


################################################################################
# Module Classes
################################################################################
@total_ordering
@dataclass(frozen=True, slots=True)
class Version:
    """
    Represent a semantic version as three non-negative integers.

    Instances are immutable and hashable, so they work as dictionary keys and
    set members. Ordering follows the numeric tuple, which is what callers
    mean by "newer" in the vast majority of cases.

    :param major: Major version, raised when the public API breaks.
    :param minor: Minor version, raised on backwards compatible additions.
    :param patch: Patch version, raised on backwards compatible fixes.
    :raises InvalidVersionError: If any component is negative.
    """

    ############################################################################
    # Constructor Method
    ############################################################################
    major: int
    minor: int
    patch: int

    def __post_init__(self) -> None:
        """
        Reject negative components right after construction.

        :raises InvalidVersionError: If any component is negative.
        """
        # 三个字段共用一条规则，合并判断后一次性报出，避免只报第一位
        if self.major < 0 or self.minor < 0 or self.patch < 0:
            raise InvalidVersionError(
                f"version components must be non-negative, "
                f"got {self.major}.{self.minor}.{self.patch}"
            )

    ############################################################################
    # Default Methods
    ############################################################################
    def __str__(self) -> str:
        """
        Render the version in the canonical three-part form.

        :return: Text such as ``"1.2.3"``.
        """
        # 输出永远补全三段，避免 1.2 与 1.2.0 在同一日志里看起来不同版本
        return f"{self.major}.{self.minor}.{self.patch}"

    def __lt__(self, other: object) -> bool:
        """
        Compare two versions by their numeric tuple.

        :param other: Candidate to compare against.
        :return: ``True`` when this version precedes ``other``.
        """
        # 与不可比较的类型返回 NotImplemented，让 Python 有机会尝试反向比较
        if not isinstance(other, Version):
            return NotImplemented

        # 逐段比较，任一段分出大小即结束
        return self._sort_key < other._sort_key

    ############################################################################
    # Utility Methods
    ############################################################################
    @classmethod
    def parse(cls, text: str) -> Version:
        """
        Build a version from its textual form.

        :param text: Version text such as ``"1.2.3"`` or ``"1.2.3-rc.1"``.
        :return: Parsed version instance.
        :raises InvalidVersionError: If the text is not a valid version.
        """
        # 先去掉两端空白，用户从配置文件读来的值常带换行
        match = _VERSION_PATTERN.match(text.strip())
        if match is None:
            raise InvalidVersionError(f"not a valid version string: {text!r}")

        # 正则已保证三段都是纯数字，直接转换不会失败
        return cls(
            major=int(match.group("major")),
            minor=int(match.group("minor")),
            patch=int(match.group("patch")),
        )

    @property
    def as_tuple(self) -> tuple[int, int, int]:
        """
        Expose the components as a plain tuple.

        :return: ``(major, minor, patch)``.
        """
        # 供调用方做集合去重或写进自定义格式，不必依赖排序键
        return (self.major, self.minor, self.patch)

    ############################################################################
    # Helper Methods
    ############################################################################
    @property
    def _sort_key(self) -> tuple[int, int, int]:
        """
        Produce the comparison key shared by every ordering method.

        :return: Tuple used by :meth:`__lt__`.
        """
        # 单一来源，避免 __lt__ 与未来新增的比较方法各写一套字段顺序
        return (self.major, self.minor, self.patch)
