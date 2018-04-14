import operator

from typing import Union

from .exceptions import InvalidVersion
from .legacy_version import LegacyVersion
from .version import Version


OP_EQ = operator.eq
OP_LT = operator.lt
OP_LE = operator.le
OP_GT = operator.gt
OP_GE = operator.ge
OP_NE = operator.ne

_trans_op = {
    '=': OP_EQ,
    '==': OP_EQ,
    '<': OP_LT,
    '<=': OP_LE,
    '>': OP_GT,
    '>=': OP_GE,
    '!=': OP_NE
}


def parse(version,      # type: str
          strict=False  # type: bool
          ):  # type:(...) -> Union[Version, LegacyVersion]
    """
    Parse the given version string and return either a :class:`Version` object
    or a LegacyVersion object depending on if the given version is
    a valid PEP 440 version or a legacy version.

    If strict=True only PEP 440 versions will be accepted.
    """
    try:
        return Version(version)
    except InvalidVersion:
        if strict:
            raise

        return LegacyVersion(version)


def version_compare(version1, version2, operator
                    ):  # type: (str, str, str) -> bool
    from poetry.semver.helpers import normalize_version

    if operator in _trans_op:
        operator = _trans_op[operator]
    elif operator in _trans_op.values():
        pass
    else:
        raise ValueError('Invalid operator')

    version1 = parse(version1)
    version2 = parse(version2)

    try:
        version1 = parse(normalize_version(str(version1)))
    except ValueError:
        pass

    try:
        version2 = parse(normalize_version(str(version2)))
    except ValueError:
        pass

    return operator(version1, version2)
