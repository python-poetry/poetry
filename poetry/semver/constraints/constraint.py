import operator

from pkg_resources import parse_version

from ..helpers import normalize_version
from .base_constraint import BaseConstraint


class Constraint(BaseConstraint):

    OP_EQ = operator.eq
    OP_LT = operator.lt
    OP_LE = operator.le
    OP_GT = operator.gt
    OP_GE = operator.ge
    OP_NE = operator.ne

    _trans_op_str = {
        '=': OP_EQ,
        '==': OP_EQ,
        '<': OP_LT,
        '<=': OP_LE,
        '>': OP_GT,
        '>=': OP_GE,
        '!=': OP_NE
    }

    _trans_op_int = {
        OP_EQ: '==',
        OP_LT: '<',
        OP_LE: '<=',
        OP_GT: '>',
        OP_GE: '>=',
        OP_NE: '!='
    }

    def __init__(self, operator: str, version: str):
        if operator not in self._trans_op_str:
            raise ValueError(
                f'Invalid operator "{operator}" given, '
                f'expected one of: {", ".join(self.supported_operators)}'
            )

        self._operator = self._trans_op_str[operator]
        self._version = version
        
    @property
    def supported_operators(self) -> list:
        return list(self._trans_op_str.keys())

    @property
    def operator(self):
        return self._operator

    @property
    def version(self) -> str:
        return self._version

    def matches(self, provider):
        if isinstance(provider, self.__class__):
            return self.match_specific(provider)

        # turn matching around to find a match
        return provider.matches(self)

    def version_compare(self, a: str, b: str, operator: str) -> bool:
        if operator not in self._trans_op_str:
            raise ValueError(
                f'Invalid operator "{operator}" given, '
                f'expected one of: {", ".join(self.supported_operators)}'
            )

        # If we can't normalize the version
        # we delegate to parse_version()
        try:
            a = normalize_version(a)
        except ValueError:
            pass

        try:
            b = normalize_version(b)
        except ValueError:
            pass

        return self._trans_op_str[operator](
            parse_version(a),
            parse_version(b)
        )

    def match_specific(self, provider: 'Constraint') -> bool:
        no_equal_op = self._trans_op_int[self._operator].replace('=', '')
        provider_no_equal_op = self._trans_op_int[provider.operator].replace('=', '')

        is_equal_op = self.OP_EQ is self._operator
        is_non_equal_op = self.OP_NE is self._operator
        is_provider_equal_op = self.OP_EQ is provider.operator
        is_provider_non_equal_op = self.OP_NE is provider.operator

        # '!=' operator is match when other operator
        # is not '==' operator or version is not match
        # these kinds of comparisons always have a solution
        if is_non_equal_op or is_provider_non_equal_op:
            return (not is_equal_op and not is_provider_equal_op
                    or self.version_compare(provider.version,
                                            self._version,
                                            '!='))

        # An example for the condition is <= 2.0 & < 1.0
        # These kinds of comparisons always have a solution
        if (self._operator is not self.OP_EQ
                and no_equal_op == provider_no_equal_op):
            return True

        if self.version_compare(
            provider.version,
            self.version,
            self._trans_op_int[self._operator]
        ):
            # special case, e.g. require >= 1.0 and provide < 1.0
            # 1.0 >= 1.0 but 1.0 is outside of the provided interval
            if (
                provider.version == self.version
                and self._trans_op_int[provider.operator] == provider_no_equal_op
                and self._trans_op_int[self.operator] != no_equal_op
            ):
                return False

            return True

        return False

    def __str__(self):
        return '{} {}'.format(
            self._trans_op_int[self._operator],
            self._version
        )

    def __repr__(self):
        return '<Constraint \'{}\'>'.format(str(self))
