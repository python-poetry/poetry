from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from poetry.core.version.markers import BaseMarker


@dataclass
class TransitivePackageInfo:
    depth: int  # max depth in the dependency tree
    groups: set[str]
    markers: dict[str, BaseMarker]  # group -> marker
