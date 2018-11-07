import re

from pyparsing import ParseException, ParseResults, stringStart, stringEnd

from pyparsing import ZeroOrMore, Group, Forward, QuotedString
from pyparsing import Literal as L  # noqa

from typing import Any
from typing import Dict
from typing import Iterator
from typing import List


class InvalidMarker(ValueError):
    """
    An invalid marker was found, users should refer to PEP 508.
    """


class UndefinedComparison(ValueError):
    """
    An invalid operation was attempted on a value that doesn't support it.
    """


class UndefinedEnvironmentName(ValueError):
    """
    A name was attempted to be used that does not exist inside of the
    environment.
    """


class Node(object):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return str(self.value)

    def __repr__(self):
        return "<{0}({1!r})>".format(self.__class__.__name__, str(self))

    def serialize(self):
        raise NotImplementedError


class Variable(Node):
    def serialize(self):
        return str(self)


class Value(Node):
    def serialize(self):
        return '"{0}"'.format(self)


class Op(Node):
    def serialize(self):
        return str(self)


VARIABLE = (
    L("implementation_version")
    | L("platform_python_implementation")
    | L("implementation_name")
    | L("python_full_version")
    | L("platform_release")
    | L("platform_version")
    | L("platform_machine")
    | L("platform_system")
    | L("python_version")
    | L("sys_platform")
    | L("os_name")
    | L("os.name")
    | L("sys.platform")  # PEP-345
    | L("platform.version")  # PEP-345
    | L("platform.machine")  # PEP-345
    | L("platform.python_implementation")  # PEP-345
    | L("python_implementation")  # PEP-345
    | L("extra")  # undocumented setuptools legacy
)
ALIASES = {
    "os.name": "os_name",
    "sys.platform": "sys_platform",
    "platform.version": "platform_version",
    "platform.machine": "platform_machine",
    "platform.python_implementation": "platform_python_implementation",
    "python_implementation": "platform_python_implementation",
}
VARIABLE.setParseAction(lambda s, l, t: Variable(ALIASES.get(t[0], t[0])))

VERSION_CMP = (
    L("===") | L("==") | L(">=") | L("<=") | L("!=") | L("~=") | L(">") | L("<")
)

MARKER_OP = VERSION_CMP | L("not in") | L("in")
MARKER_OP.setParseAction(lambda s, l, t: Op(t[0]))

MARKER_VALUE = QuotedString("'") | QuotedString('"')
MARKER_VALUE.setParseAction(lambda s, l, t: Value(t[0]))

BOOLOP = L("and") | L("or")

MARKER_VAR = VARIABLE | MARKER_VALUE

MARKER_ITEM = Group(MARKER_VAR + MARKER_OP + MARKER_VAR)
MARKER_ITEM.setParseAction(lambda s, l, t: tuple(t[0]))

LPAREN = L("(").suppress()
RPAREN = L(")").suppress()

MARKER_EXPR = Forward()
MARKER_ATOM = MARKER_ITEM | Group(LPAREN + MARKER_EXPR + RPAREN)
MARKER_EXPR << MARKER_ATOM + ZeroOrMore(BOOLOP + MARKER_EXPR)

MARKER = stringStart + MARKER_EXPR + stringEnd


_undefined = object()


def _coerce_parse_result(results):
    if isinstance(results, ParseResults):
        return [_coerce_parse_result(i) for i in results]
    else:
        return results


def _format_marker(marker, first=True):
    assert isinstance(marker, (list, tuple, str))

    # Sometimes we have a structure like [[...]] which is a single item list
    # where the single item is itself it's own list. In that case we want skip
    # the rest of this function so that we don't get extraneous () on the
    # outside.
    if (
        isinstance(marker, list)
        and len(marker) == 1
        and isinstance(marker[0], (list, tuple))
    ):
        return _format_marker(marker[0])

    if isinstance(marker, list):
        inner = (_format_marker(m, first=False) for m in marker)
        if first:
            return " ".join(inner)
        else:
            return "(" + " ".join(inner) + ")"
    elif isinstance(marker, tuple):
        return " ".join([m.serialize() for m in marker])
    else:
        return marker


class BaseMarker(object):
    def intersect(self, other):  # type: (BaseMarker) -> BaseMarker
        raise NotImplementedError()

    def union(self, other):  # type: (BaseMarker) -> BaseMarker
        raise NotImplementedError()

    def is_any(self):  # type: () -> bool
        return False

    def is_empty(self):  # type: () -> bool
        return False

    def validate(self, environment):  # type: (Dict[str, Any]) -> bool
        raise NotImplementedError()

    def without_extras(self):  # type: () -> BaseMarker
        raise NotImplementedError()

    def __repr__(self):
        return "<{} {}>".format(self.__class__.__name__, str(self))


class AnyMarker(BaseMarker):
    def intersect(self, other):
        return other

    def union(self, other):
        return self

    def is_any(self):
        return True

    def is_empty(self):  # type: () -> bool
        return False

    def validate(self, environment):
        return True

    def without_extras(self):
        return self

    def __str__(self):
        return ""

    def __repr__(self):
        return "<AnyMarker>"


class EmptyMarker(BaseMarker):
    def intersect(self, other):
        return self

    def union(self, other):
        return other

    def is_any(self):
        return False

    def is_empty(self):  # type: () -> bool
        return True

    def validate(self, environment):
        return False

    def without_extras(self):
        return self

    def __str__(self):
        return "<empty>"

    def __repr__(self):
        return "<EmptyMarker>"


class SingleMarker(BaseMarker):

    _CONSTRAINT_RE = re.compile(r"(?i)^(~=|!=|>=?|<=?|==?|in|not in)?\s*(.+)$")

    def __init__(self, name, constraint):
        from poetry.packages.constraints import (
            parse_constraint as parse_generic_constraint,
        )
        from poetry.semver import parse_constraint

        self._name = name
        self._constraint_string = str(constraint)

        # Extract operator and value
        m = self._CONSTRAINT_RE.match(self._constraint_string)
        self._operator = m.group(1)
        if self._operator is None:
            self._operator = "=="

        self._value = m.group(2)
        self._parser = parse_generic_constraint
        if self._name == "python_version":
            self._parser = parse_constraint

        if name == "python_version":
            if self._operator in {"in", "not in"}:
                versions = []
                for v in re.split("[ ,]+", self._value):
                    split = v.split(".")
                    if len(split) in [1, 2]:
                        split.append("*")
                        op = "" if self._operator == "in" else "!="
                    else:
                        op = "==" if self._operator == "in" else "!="

                    versions.append(op + ".".join(split))

                glue = ", "
                if self._operator == "in":
                    glue = " || "

                self._constraint = self._parser(glue.join(versions))
            else:
                self._constraint = self._parser(self._constraint_string)
        else:
            self._constraint = self._parser(self._constraint_string)

    @property
    def name(self):
        return self._name

    @property
    def constraint_string(self):
        if self._operator in {"in", "not in"}:
            return "{} {}".format(self._operator, self._value)

        return self._constraint_string

    @property
    def constraint(self):
        return self._constraint

    @property
    def operator(self):
        return self._operator

    @property
    def value(self):
        return self._value

    def intersect(self, other):
        if isinstance(other, SingleMarker):
            if other.name != self.name:
                return MultiMarker(self, other)

            if self == other:
                return self

            if self._operator in {"in", "not in"} or other.operator in {"in", "not in"}:
                return MultiMarker.of(self, other)

            new_constraint = self._constraint.intersect(other.constraint)
            if new_constraint.is_empty():
                return EmptyMarker()

            if new_constraint == self._constraint or new_constraint == other.constraint:
                return SingleMarker(self._name, new_constraint)

            return MultiMarker.of(self, other)

        return other.intersect(self)

    def union(self, other):
        if isinstance(other, SingleMarker):
            if self == other:
                return self

            return MarkerUnion(self, other)

        return other.union(self)

    def validate(self, environment):
        if environment is None:
            return True

        if self._name not in environment:
            return True

        return self._constraint.allows(self._parser(environment[self._name]))

    def without_extras(self):
        if self.name == "extra":
            return EmptyMarker()

        return self

    def __eq__(self, other):
        if not isinstance(other, SingleMarker):
            return False

        return self._name == other.name and self._constraint == other.constraint

    def __hash__(self):
        return hash((self._name, self._constraint_string))

    def __str__(self):
        return _format_marker(
            (Variable(self._name), Op(self._operator), Value(self._value))
        )


def _flatten_markers(
    markers, flatten_class
):  # type: (Iterator[BaseMarker], Any) -> List[BaseMarker]
    flattened = []

    for marker in markers:
        if isinstance(marker, flatten_class):
            flattened += _flatten_markers(marker.markers, flatten_class)
        else:
            flattened.append(marker)

    return flattened


class MultiMarker(BaseMarker):
    def __init__(self, *markers):
        self._markers = []

        markers = _flatten_markers(markers, MultiMarker)

        for m in markers:
            self._markers.append(m)

    @classmethod
    def of(cls, *markers):
        new_markers = []
        markers = _flatten_markers(markers, MultiMarker)

        for marker in markers:
            if marker in new_markers or marker.is_empty():
                continue

            if isinstance(marker, SingleMarker):
                intersected = False
                for i, mark in enumerate(new_markers):
                    if (
                        not isinstance(mark, SingleMarker)
                        or isinstance(mark, SingleMarker)
                        and mark.name != marker.name
                    ):
                        continue

                    intersection = mark.constraint.intersect(marker.constraint)
                    if intersection == mark.constraint:
                        intersected = True
                        break
                    elif intersection == marker.constraint:
                        new_markers[i] = marker
                        intersected = True
                        break
                    elif intersection.is_empty():
                        return EmptyMarker()

                if intersected:
                    continue

            new_markers.append(marker)

        if not new_markers:
            return EmptyMarker()

        return MultiMarker(*new_markers)

    @property
    def markers(self):
        return self._markers

    def intersect(self, other):
        if other.is_any():
            return self

        if other.is_empty():
            return other

        new_markers = self._markers + [other]

        return MultiMarker.of(*new_markers)

    def union(self, other):
        if isinstance(other, (SingleMarker, MultiMarker)):
            return MarkerUnion(self, other)

        return other.union(self)

    def validate(self, environment):
        for m in self._markers:
            if not m.validate(environment):
                return False

        return True

    def without_extras(self):
        new_markers = []

        for m in self._markers:
            marker = m.without_extras()

            if not marker.is_empty():
                new_markers.append(marker)

        return self.of(*new_markers)

    def __eq__(self, other):
        if not isinstance(other, MultiMarker):
            return False

        return set(self._markers) == set(other.markers)

    def __hash__(self):
        h = hash("multi")
        for m in self._markers:
            h |= hash(m)

        return h

    def __str__(self):
        elements = []
        for m in self._markers:
            if isinstance(m, SingleMarker):
                elements.append(str(m))
            elif isinstance(m, MultiMarker):
                elements.append(str(m))
            else:
                elements.append("({})".format(str(m)))

        return " and ".join(elements)


class MarkerUnion(BaseMarker):
    def __init__(self, *markers):
        self._markers = []

        markers = _flatten_markers(markers, MarkerUnion)

        for marker in markers:
            if marker in self._markers:
                continue

            if isinstance(marker, SingleMarker) and marker.name == "python_version":
                intersected = False
                for i, mark in enumerate(self._markers):
                    if (
                        not isinstance(mark, SingleMarker)
                        or isinstance(mark, SingleMarker)
                        and mark.name != marker.name
                    ):
                        continue

                    intersection = mark.constraint.union(marker.constraint)
                    if intersection == mark.constraint:
                        intersected = True
                        break
                    elif intersection == marker.constraint:
                        self._markers[i] = marker
                        intersected = True
                        break

                if intersected:
                    continue

            self._markers.append(marker)

    @property
    def markers(self):
        return self._markers

    def append(self, marker):
        if marker in self._markers:
            return

        self._markers.append(marker)

    def intersect(self, other):
        if other.is_any():
            return self

        if other.is_empty():
            return other

        new_markers = []
        if isinstance(other, (SingleMarker, MultiMarker)):
            for marker in self._markers:
                intersection = marker.intersect(other)

                if not intersection.is_empty():
                    new_markers.append(intersection)
        elif isinstance(other, MarkerUnion):
            for our_marker in self._markers:
                for their_marker in other.markers:
                    intersection = our_marker.intersect(their_marker)

                    if not intersection.is_empty():
                        new_markers.append(intersection)

        return MarkerUnion(*new_markers)

    def union(self, other):
        if other.is_any():
            return other

        if other.is_empty():
            return self

        new_markers = self._markers + [other]

        return MarkerUnion(*new_markers)

    def validate(self, environment):
        for m in self._markers:
            if m.validate(environment):
                return True

        return False

    def without_extras(self):
        new_markers = []

        for m in self._markers:
            marker = m.without_extras()

            if not marker.is_empty():
                new_markers.append(marker)

        return MarkerUnion(*new_markers)

    def __eq__(self, other):
        if not isinstance(other, MarkerUnion):
            return False

        return set(self._markers) == set(other.markers)

    def __hash__(self):
        h = hash("union")
        for m in self._markers:
            h |= hash(m)

        return h

    def __str__(self):
        return " or ".join(str(m) for m in self._markers)


def parse_marker(marker):
    if marker == "<empty>":
        return EmptyMarker()

    if not marker or marker == "*":
        return AnyMarker()

    markers = _coerce_parse_result(MARKER.parseString(marker))

    return _compact_markers(markers)


def _compact_markers(markers):
    groups = [MultiMarker()]

    for marker in markers:
        if isinstance(marker, list):
            groups[-1] = MultiMarker.of(groups[-1], _compact_markers(marker))
        elif isinstance(marker, tuple):
            lhs, op, rhs = marker

            if isinstance(lhs, Variable):
                name = lhs.value
                value = rhs.value
            else:
                value = lhs.value
                name = rhs.value

            groups[-1] = MultiMarker.of(
                groups[-1], SingleMarker(name, "{}{}".format(op, value))
            )
        else:
            if marker == "or":
                groups.append(MultiMarker())

    for i, group in enumerate(reversed(groups)):
        if group.is_empty():
            del groups[len(groups) - 1 - i]
            continue

        if isinstance(group, MultiMarker) and len(group.markers) == 1:
            groups[len(groups) - 1 - i] = group.markers[0]

    if not groups:
        return EmptyMarker()

    if len(groups) == 1:
        return groups[0]

    return MarkerUnion(*groups)
