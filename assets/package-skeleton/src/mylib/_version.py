################################################################################
# @Project: mylib
# @File Path: src/mylib/_version.py
# @Description: Single source of truth for the package version. The
#               build backend reads this value, so no other file may
#               repeat the literal.
# @Creation Date: 2026-11-18
# @Last Update: 2026-11-18
################################################################################

################################################################################
# Module Constants
################################################################################
# 版本只在这里改一次；pyproject 通过 setuptools.dynamic 读取，避免两处漂移
__version__ = "0.1.0"
