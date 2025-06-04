from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from poetry.core.version.markers import BaseMarker
from poetry.core.version.markers import EmptyMarker


if TYPE_CHECKING:
    from collections.abc import Iterable

    from packaging.utils import NormalizedName


@dataclass
class TransitivePackageInfo:
    depth: int  # max depth in the dependency tree
    groups: set[NormalizedName]
    markers: dict[NormalizedName, BaseMarker]  # group -> marker

    def get_marker(self, groups: Iterable[NormalizedName]) -> BaseMarker:
        marker: BaseMarker = EmptyMarker()
        for group in groups:
            if group_marker := self.markers.get(group):
                marker = marker.union(group_marker)
        return marker
