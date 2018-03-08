from poetry.semver.constraints import MultiConstraint

from .builders import CompleteBuilder
from .builders import SdistBuilder
from .builders import WheelBuilder


class Builder:

    _FORMATS = {
        'sdist': SdistBuilder,
        'wheel': WheelBuilder,
        'all': CompleteBuilder
    }

    def __init__(self, poetry, io):
        self._poetry = poetry
        self._io = io

    def build(self, fmt: str):
        if fmt not in self._FORMATS:
            raise ValueError(f'Invalid format: {fmt}')

        self.check()

        builder = self._FORMATS[fmt](self._poetry, self._io)

        return builder.build()

    def check(self) -> None:
        package = self._poetry.package

        # Checking for disjunctive python versions
        if isinstance(package.python_constraint, MultiConstraint):
            if package.python_constraint.is_disjunctive():
                raise RuntimeError(
                    'Disjunctive python versions are not yet supported '
                    'when building packages. Rewrite your python requirements '
                    'in a conjunctive way.'
                )
