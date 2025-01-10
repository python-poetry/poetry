from __future__ import annotations

import logging
from typing import Iterator
from pathlib import Path

from cachecontrol.controller import logger as cache_control_logger
from poetry.core.packages.package import Package
from poetry.core.packages.utils.link import Link
from poetry.repositories.repository import Repository
from poetry.inspection.info import PackageInfo
from poetry.core.packages.utils.utils import path_to_url

cache_control_logger.setLevel(logging.ERROR)

logger = logging.getLogger(__name__)


class LocalPathRepository(Repository):
    def __init__(self, name: str, path: str) -> None:
        self._path = Path(path)
        if not self._path.is_dir():
            raise ValueError(f"Path {self._path} is not a directory")
        
        super().__init__(name, self._list_packages_in_path())

    @property
    def path(self) -> str:
        return self._path
    
    def _list_packages_in_path(self) -> Iterator[Package]:
        for file_path in self._path.iterdir():
            try:
                yield PackageInfo.from_path(path=file_path).to_package(root_dir=file_path)
            except Exception:
                continue

    def find_links_for_package(self, package: Package) -> list[Link]:
        return [Link(path_to_url(package.source_type))]