from __future__ import annotations

from typing import TYPE_CHECKING

from poetry.core.constraints.version import parse_constraint

from poetry.mixology.incompatibility_cause import ConflictCause
from poetry.mixology.incompatibility_cause import PythonCause


if TYPE_CHECKING:
    from poetry.mixology.incompatibility import Incompatibility


class SolveFailure(Exception):
    def __init__(self, incompatibility: Incompatibility) -> None:
        self._incompatibility = incompatibility

    @property
    def message(self) -> str:
        return str(self)

    def __str__(self) -> str:
        return _Writer(self._incompatibility).write()


class _Writer:
    def __init__(self, root: Incompatibility) -> None:
        self._root = root
        self._derivations: dict[Incompatibility, int] = {}
        self._lines: list[tuple[str, int | None]] = []
        self._line_numbers: dict[Incompatibility, int] = {}

        self._count_derivations(self._root)

    def write(self) -> str:
        buffer = []

        required_python_version_notification = False
        for incompatibility in self._root.external_incompatibilities:
            if isinstance(incompatibility.cause, PythonCause):
                if not required_python_version_notification:
                    buffer.append(
                        "The current project's supported Python range"
                        f" ({incompatibility.cause.root_python_version}) is not"
                        " compatible with some of the required packages Python"
                        " requirement:"
                    )
                    required_python_version_notification = True

                root_constraint = parse_constraint(
                    incompatibility.cause.root_python_version
                )
                constraint = parse_constraint(incompatibility.cause.python_version)
                buffer.append(
                    f"  - {incompatibility.terms[0].dependency.name} requires Python"
                    f" {incompatibility.cause.python_version}, so it will not be"
                    f" satisfied for Python {root_constraint.difference(constraint)}"
                )

        if required_python_version_notification:
            buffer.append("")

        if isinstance(self._root.cause, ConflictCause):
            self._visit(self._root)
        else:
            self._write(self._root, f"Because {self._root}, version solving failed.")

        padding = (
            0
            if not self._line_numbers
            else len(f"({list(self._line_numbers.values())[-1]}) ")
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
                message = f"({number})".ljust(padding) + message
            else:
                message = " " * padding + message

            buffer.append(message)

        return "\n".join(buffer)

    def _write(
        self, incompatibility: Incompatibility, message: str, numbered: bool = False
    ) -> None:
        if numbered:
            number = len(self._line_numbers) + 1
            self._line_numbers[incompatibility] = number
            self._lines.append((message, number))
        else:
            self._lines.append((message, None))

    def _visit(
        self,
        incompatibility: Incompatibility,
        conclusion: bool = False,
    ) -> None:
        numbered = conclusion or self._derivations[incompatibility] > 1
        conjunction = "So," if conclusion or incompatibility == self._root else "And"
        incompatibility_string = str(incompatibility)

        cause = incompatibility.cause
        assert isinstance(cause, ConflictCause)

        if isinstance(cause.conflict.cause, ConflictCause) and isinstance(
            cause.other.cause, ConflictCause
        ):
            conflict_line = self._line_numbers.get(cause.conflict)
            other_line = self._line_numbers.get(cause.other)

            if conflict_line is not None and other_line is not None:
                reason = cause.conflict.and_to_string(
                    cause.other, conflict_line, other_line
                )
                self._write(
                    incompatibility,
                    f"Because {reason}, {incompatibility_string}.",
                    numbered=numbered,
                )
            elif conflict_line is not None or other_line is not None:
                if conflict_line is not None:
                    with_line = cause.conflict
                    without_line = cause.other
                    line = conflict_line
                elif other_line is not None:
                    with_line = cause.other
                    without_line = cause.conflict
                    line = other_line

                self._visit(without_line)
                self._write(
                    incompatibility,
                    f"{conjunction} because {with_line!s} ({line}),"
                    f" {incompatibility_string}.",
                    numbered=numbered,
                )
            else:
                single_line_conflict = self._is_single_line(cause.conflict.cause)
                single_line_other = self._is_single_line(cause.other.cause)

                if single_line_other or single_line_conflict:
                    first = cause.conflict if single_line_other else cause.other
                    second = cause.other if single_line_other else cause.conflict
                    self._visit(first)
                    self._visit(second)
                    self._write(
                        incompatibility,
                        f"Thus, {incompatibility_string}.",
                        numbered=numbered,
                    )
                else:
                    self._visit(cause.conflict, conclusion=True)
                    self._lines.append(("", None))

                    self._visit(cause.other)

                    self._write(
                        incompatibility,
                        f"{conjunction} because {cause.conflict!s}"
                        f" ({self._line_numbers[cause.conflict]}),"
                        f" {incompatibility_string}",
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
                reason = ext.and_to_string(derived, None, derived_line)
                self._write(
                    incompatibility,
                    f"Because {reason}, {incompatibility_string}.",
                    numbered=numbered,
                )
            elif self._is_collapsible(derived):
                derived_cause = derived.cause
                assert isinstance(derived_cause, ConflictCause)
                if isinstance(derived_cause.conflict.cause, ConflictCause):
                    collapsed_derived = derived_cause.conflict
                    collapsed_ext = derived_cause.other
                else:
                    collapsed_derived = derived_cause.other

                    collapsed_ext = derived_cause.conflict

                self._visit(collapsed_derived)
                reason = collapsed_ext.and_to_string(ext, None, None)
                self._write(
                    incompatibility,
                    f"{conjunction} because {reason}, {incompatibility_string}.",
                    numbered=numbered,
                )
            else:
                self._visit(derived)
                self._write(
                    incompatibility,
                    f"{conjunction} because {ext!s}, {incompatibility_string}.",
                    numbered=numbered,
                )
        else:
            reason = cause.conflict.and_to_string(cause.other, None, None)
            self._write(
                incompatibility,
                f"Because {reason}, {incompatibility_string}.",
                numbered=numbered,
            )

    def _is_collapsible(self, incompatibility: Incompatibility) -> bool:
        if self._derivations[incompatibility] > 1:
            return False

        cause = incompatibility.cause
        assert isinstance(cause, ConflictCause)
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

    def _is_single_line(self, cause: ConflictCause) -> bool:
        return not isinstance(cause.conflict.cause, ConflictCause) and not isinstance(
            cause.other.cause, ConflictCause
        )

    def _count_derivations(self, incompatibility: Incompatibility) -> None:
        if incompatibility in self._derivations:
            self._derivations[incompatibility] += 1
        else:
            self._derivations[incompatibility] = 1
            cause = incompatibility.cause
            if isinstance(cause, ConflictCause):
                self._count_derivations(cause.conflict)
                self._count_derivations(cause.other)
