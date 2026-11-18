################################################################################
# @Project: mylib
# @File Path: src/mylib/errors.py
# @Description: Exception hierarchy of the library. Errors carry no
#               HTTP status: a library must not assume it is called
#               from inside a web request.
# @Creation Date: 2026-11-18
# @Last Update: 2026-11-18
################################################################################

################################################################################
# Module Classes
################################################################################
class MyLibError(Exception):
    """
    Base class for every error this library raises.

    Downstream code catches this single type when it wants to handle library
    failures without swallowing unrelated bugs from its own code base.

    :param message: Human readable description of the failure.
    """


class InvalidVersionError(MyLibError, ValueError):
    """
    Report a value that cannot be interpreted as a version.

    Also inherits ``ValueError`` so that callers already guarding on
    ``ValueError`` keep working after they adopt this library.

    :param message: Human readable description of the failure.
    """
