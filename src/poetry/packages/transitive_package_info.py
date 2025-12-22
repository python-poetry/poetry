from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from poetry.core.packages.dependency_group import MAIN_GROUP
from poetry.core.version.markers import BaseMarker
from poetry.core.version.markers import EmptyMarker


if TYPE_CHECKING:
    from collections.abc import Iterable

    from packaging.utils import NormalizedName


def group_sort_key(group: NormalizedName) -> tuple[bool, NormalizedName]:
    return group != MAIN_GROUP, group


@dataclass
class TransitivePackageInfo:
    depth: int  # max depth in the dependency tree
    groups: set[NormalizedName]
    markers: dict[NormalizedName, BaseMarker]  # group -> marker

    def get_marker(self, groups: Iterable[NormalizedName]) -> BaseMarker:
        marker: BaseMarker = EmptyMarker()
        for group in sorted(groups, key=group_sort_key):
            if group_marker := self.markers.get(group):
                marker = marker.union(group_marker)
        return marker
