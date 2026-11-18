################################################################################
# @Project: mylib
# @File Path: src/mylib/__init__.py
# @Description: Public surface of the library. Anything absent from
#               __all__ is an implementation detail and may change
#               without a major release.
# @Creation Date: 2026-11-18
# @Last Update: 2026-11-18
################################################################################

################################################################################
# Import Libraries
################################################################################
# Local Modules
from mylib._version import __version__
from mylib.compat import is_compatible_with
from mylib.errors import InvalidVersionError, MyLibError
from mylib.models import Version

################################################################################
# Module Constants
################################################################################
# 导出面即契约：不在此列的名字随时可能改名，下游不应直接 import
__all__ = [
    "InvalidVersionError",
    "MyLibError",
    "Version",
    "__version__",
    "is_compatible_with",
]
