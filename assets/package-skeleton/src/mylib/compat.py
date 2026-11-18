################################################################################
# @Project: mylib
# @File Path: src/mylib/compat.py
# @Description: Compatibility rules built on the Version value object. This
#               module shows how a library exposes behaviour, not just data.
# @Creation Date: 2026-11-18
# @Last Update: 2026-11-18
################################################################################

################################################################################
# Import Libraries
################################################################################
# Local Modules
from mylib.models import Version


################################################################################
# Module Functions
################################################################################
def is_compatible_with(installed: Version, required: Version) -> bool:
    """
    Tell whether an installed version satisfies a requirement.

    Follows semantic versioning with one deliberate exception: a requirement
    in the ``0.x`` range is treated as unstable, so the minor number must match
    exactly. Before 1.0 the minor number is where breaking changes land.

    :param installed: Version currently present in the environment.
    :param required: Minimum version the caller needs.
    :return: ``True`` when ``installed`` satisfies ``required``.
    """
    # 0.x 阶段语义版本允许任意破坏性变更，因此要求主次版本完全一致
    if required.major == 0:
        return installed.major == 0 and installed.minor == required.minor

    # 1.0 之后只看主版本是否相同，且不低于要求的下限
    return installed.major == required.major and installed >= required
