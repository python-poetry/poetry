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


def parse(version: str, strict: bool = False) -> Union[Version, LegacyVersion]:
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


def version_compare(version1: str, version2: str, operator) -> bool:
    if operator in _trans_op:
        operator = _trans_op[operator]
    elif operator in _trans_op.values():
        pass
    else:
        raise ValueError('Invalid operator')

    version1 = parse(version1)
    version2 = parse(version2)

    return operator(version1, version2)
