import re

from .constraint import Constraint


class WilcardConstraint(Constraint):
    def __init__(self, constraint):  # type: (str) -> None
        m = re.match(
            "^(!= ?|==)?v?(\d+)(?:\.(\d+))?(?:\.(\d+))?(?:\.[xX*])+$", constraint
        )
        if not m:
            raise ValueError("Invalid value for wildcard constraint")

        if not m.group(1):
            operator = "=="
        else:
            operator = m.group(1).strip()

        super(WilcardConstraint, self).__init__(
            operator, ".".join([g if g else "*" for g in m.groups()[1:]])
        )

        if m.group(4):
            position = 2
        elif m.group(3):
            position = 1
        else:
            position = 0

        from ..version_parser import VersionParser

        parser = VersionParser()
        groups = m.groups()[1:]
        low_version = parser._manipulate_version_string(groups, position)
        high_version = parser._manipulate_version_string(groups, position, 1)

        if operator == "!=":
            if low_version == "0.0.0.0":
                self._constraint = Constraint(">=", high_version)
            else:
                self._constraint = parser.parse_constraints(
                    "<{} || >={}".format(low_version, high_version)
                )
        else:
            if low_version == "0.0.0.0":
                self._constraint = Constraint("<", high_version)
            else:
                self._constraint = parser.parse_constraints(
                    ">={},<{}".format(low_version, high_version)
                )

    @property
    def supported_operators(self):
        return ["!=", "=="]

    @property
    def constraint(self):
        return self._constraint

    def matches(self, provider):  # type: (Constraint) -> bool
        if isinstance(provider, self.__class__):
            return self._constraint.matches(provider.constraint)

        return provider.matches(self._constraint)

    def __str__(self):
        op = ""
        if self.string_operator == "!=":
            op = "!= "

        return "{}{}".format(op, self._version)
