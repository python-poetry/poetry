from typing import Dict
from typing import List
from typing import Tuple

from .incompatibility import Incompatibility
from .incompatibility_cause import ConflictCause
from .incompatibility_cause import PythonCause


class SolveFailure(Exception):
    def __init__(self, incompatibility):  # type: (Incompatibility) -> None
        self._incompatibility = incompatibility

    @property
    def message(self):
        return str(self)

    def __str__(self):
        return _Writer(self._incompatibility).write()


class _Writer:
    def __init__(self, root):  # type: (Incompatibility) -> None
        self._root = root
        self._derivations = {}  # type: Dict[Incompatibility, int]
        self._lines = []  # type: List[Tuple[str, int]]
        self._line_numbers = {}  # type: Dict[Incompatibility, int]

        self._count_derivations(self._root)

    def write(self):
        buffer = []

        required_python_version_notification = False
        for incompatibility in self._root.external_incompatibilities:
            if isinstance(incompatibility.cause, PythonCause):
                if not required_python_version_notification:
                    buffer.append(
                        "The current project's Python requirement ({}) "
                        "is not compatible with some of the required "
                        "packages Python requirement:".format(
                            incompatibility.cause.root_python_version
                        )
                    )
                    required_python_version_notification = True

                buffer.append(
                    "  - {} requires Python {}".format(
                        incompatibility.terms[0].dependency.name,
                        incompatibility.cause.python_version,
                    )
                )

        if required_python_version_notification:
            buffer.append("")

        if isinstance(self._root.cause, ConflictCause):
            self._visit(self._root, {})
        else:
            self._write(
                self._root, "Because {}, version solving failed.".format(self._root)
            )

        padding = (
            0
            if not self._line_numbers
            else len("({}) ".format(list(self._line_numbers.values())[-1]))
        )

        last_was_empty = False
        for line in self._lines:
            message = line[0]
            if not message:
                if not last_was_empty:
                    buffer.append("")

                last_was_empty = True
                continue

            last_was_empty = False

            number = line[-1]
            if number is not None:
                message = "({})".format(number).ljust(padding) + message
            else:
                message = " " * padding + message

            buffer.append(message)

        return "\n".join(buffer)

    def _write(
        self, incompatibility, message, numbered=False
    ):  # type: (Incompatibility, str, bool) -> None
        if numbered:
            number = len(self._line_numbers) + 1
            self._line_numbers[incompatibility] = number
            self._lines.append((message, number))
        else:
            self._lines.append((message, None))

    def _visit(
        self, incompatibility, details_for_incompatibility, conclusion=False
    ):  # type: (Incompatibility, Dict, bool) -> None
        numbered = conclusion or self._derivations[incompatibility] > 1
        conjunction = "So," if conclusion or incompatibility == self._root else "And"
        incompatibility_string = str(incompatibility)

        cause = incompatibility.cause  # type: ConflictCause
        details_for_cause = {}
        if isinstance(cause.conflict.cause, ConflictCause) and isinstance(
            cause.other.cause, ConflictCause
        ):
            conflict_line = self._line_numbers.get(cause.conflict)
            other_line = self._line_numbers.get(cause.other)

            if conflict_line is not None and other_line is not None:
                self._write(
                    incompatibility,
                    "Because {}, {}.".format(
                        cause.conflict.and_to_string(
                            cause.other, details_for_cause, conflict_line, other_line
                        ),
                        incompatibility_string,
                    ),
                    numbered=numbered,
                )
            elif conflict_line is not None or other_line is not None:
                if conflict_line is not None:
                    with_line = cause.conflict
                    without_line = cause.other
                    line = conflict_line
                else:
                    with_line = cause.other
                    without_line = cause.conflict
                    line = other_line

                self._visit(without_line, details_for_cause)
                self._write(
                    incompatibility,
                    "{} because {} ({}), {}.".format(
                        conjunction, str(with_line), line, incompatibility_string
                    ),
                    numbered=numbered,
                )
            else:
                single_line_conflict = self._is_single_line(cause.conflict.cause)
                single_line_other = self._is_single_line(cause.other.cause)

                if single_line_other or single_line_conflict:
                    first = cause.conflict if single_line_other else cause.other
                    second = cause.other if single_line_other else cause.conflict
                    self._visit(first, details_for_cause)
                    self._visit(second, details_for_cause)
                    self._write(
                        incompatibility,
                        "Thus, {}.".format(incompatibility_string),
                        numbered=numbered,
                    )
                else:
                    self._visit(cause.conflict, {}, conclusion=True)
                    self._lines.append(("", None))

                    self._visit(cause.other, details_for_cause)

                    self._write(
                        incompatibility,
                        "{} because {} ({}), {}".format(
                            conjunction,
                            str(cause.conflict),
                            self._line_numbers[cause.conflict],
                            incompatibility_string,
                        ),
                        numbered=numbered,
                    )
        elif isinstance(cause.conflict.cause, ConflictCause) or isinstance(
            cause.other.cause, ConflictCause
        ):
            derived = (
                cause.conflict
                if isinstance(cause.conflict.cause, ConflictCause)
                else cause.other
            )
            ext = (
                cause.other
                if isinstance(cause.conflict.cause, ConflictCause)
                else cause.conflict
            )

            derived_line = self._line_numbers.get(derived)
            if derived_line is not None:
                self._write(
                    incompatibility,
                    "Because {}, {}.".format(
                        ext.and_to_string(
                            derived, details_for_cause, None, derived_line
                        ),
                        incompatibility_string,
                    ),
                    numbered=numbered,
                )
            elif self._is_collapsible(derived):
                derived_cause = derived.cause  # type: ConflictCause
                if isinstance(derived_cause.conflict.cause, ConflictCause):
                    collapsed_derived = derived_cause.conflict
                else:
                    collapsed_derived = derived_cause.other

                if isinstance(derived_cause.conflict.cause, ConflictCause):
                    collapsed_ext = derived_cause.other
                else:
                    collapsed_ext = derived_cause.conflict

                details_for_cause = {}

                self._visit(collapsed_derived, details_for_cause)
                self._write(
                    incompatibility,
                    "{} because {}, {}.".format(
                        conjunction,
                        collapsed_ext.and_to_string(ext, details_for_cause, None, None),
                        incompatibility_string,
                    ),
                    numbered=numbered,
                )
            else:
                self._visit(derived, details_for_cause)
                self._write(
                    incompatibility,
                    "{} because {}, {}.".format(
                        conjunction, str(ext), incompatibility_string
                    ),
                    numbered=numbered,
                )
        else:
            self._write(
                incompatibility,
                "Because {}, {}.".format(
                    cause.conflict.and_to_string(
                        cause.other, details_for_cause, None, None
                    ),
                    incompatibility_string,
                ),
                numbered=numbered,
            )

    def _is_collapsible(self, incompatibility):  # type: (Incompatibility) -> bool
        if self._derivations[incompatibility] > 1:
            return False

        cause = incompatibility.cause  # type: ConflictCause
        if isinstance(cause.conflict.cause, ConflictCause) and isinstance(
            cause.other.cause, ConflictCause
        ):
            return False

        if not isinstance(cause.conflict.cause, ConflictCause) and not isinstance(
            cause.other.cause, ConflictCause
        ):
            return False

        complex = (
            cause.conflict
            if isinstance(cause.conflict.cause, ConflictCause)
            else cause.other
        )

        return complex not in self._line_numbers

    def _is_single_line(self, cause):  # type: (ConflictCause) -> bool
        return not isinstance(cause.conflict.cause, ConflictCause) and not isinstance(
            cause.other.cause, ConflictCause
        )

    def _count_derivations(self, incompatibility):  # type: (Incompatibility) -> None
        if incompatibility in self._derivations:
            self._derivations[incompatibility] += 1
        else:
            self._derivations[incompatibility] = 1
            cause = incompatibility.cause
            if isinstance(cause, ConflictCause):
                self._count_derivations(cause.conflict)
                self._count_derivations(cause.other)
