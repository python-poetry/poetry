from __future__ import annotations

import logging

from typing import TYPE_CHECKING

from packaging.tags import Tag
from poetry.core.constraints.version import Version
from poetry.core.constraints.version import VersionRange

from poetry.utils.patterns import wheel_file_re


if TYPE_CHECKING:
    from poetry.core.constraints.version import VersionConstraint

    from poetry.utils.env import Env


logger = logging.getLogger(__name__)


class InvalidWheelName(Exception):
    pass


class Wheel:
    def __init__(self, filename: str) -> None:
        wheel_info = wheel_file_re.match(filename)
        if not wheel_info:
            raise InvalidWheelName(f"{filename} is not a valid wheel filename.")

        self.filename = filename
        self.name = wheel_info.group("name").replace("_", "-")
        self.version = wheel_info.group("ver").replace("_", "-")
        self.build_tag = wheel_info.group("build")
        self.pyversions = wheel_info.group("pyver").split(".")
        self.abis = wheel_info.group("abi").split(".")
        self.plats = wheel_info.group("plat").split(".")

        self.tags = {
            Tag(x, y, z) for x in self.pyversions for y in self.abis for z in self.plats
        }

    def get_minimum_supported_index(self, tags: list[Tag]) -> int | None:
        indexes = [tags.index(t) for t in self.tags if t in tags]

        return min(indexes) if indexes else None

    def is_supported_by_environment(self, env: Env) -> bool:
        return bool(set(env.supported_tags).intersection(self.tags))

    @staticmethod
    def _pyversion_to_constraint(pyversion: str) -> VersionConstraint:
        version = pyversion[2:]
        major = int(version[0])
        minor = int(version[1:]) if len(version) > 1 else None
        return VersionRange(
            min=Version.from_parts(major=major, minor=minor or 0, patch=0),
            max=Version.from_parts(
                major=(major + 1) if minor is None else major,
                minor=(minor + 1) if minor is not None else 0,
                patch=0,
            ),
            include_min=True,
            include_max=False,
        )

    def is_compatible_with_python(self, python: VersionConstraint) -> bool:
        for pyversion in self.pyversions:
            pyversion_constraint = self._pyversion_to_constraint(pyversion)
            if pyversion_constraint.allows_any(python):
                return True

        return False
