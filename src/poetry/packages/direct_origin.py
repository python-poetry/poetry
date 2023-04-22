from __future__ import annotations

import functools
import os
import tempfile
import urllib.parse

from pathlib import Path
from typing import TYPE_CHECKING

from poetry.inspection.info import PackageInfo
from poetry.inspection.info import PackageInfoError
from poetry.utils.helpers import download_file
from poetry.utils.helpers import get_file_hash
from poetry.vcs.git import Git


if TYPE_CHECKING:
    from poetry.core.packages.package import Package


@functools.lru_cache(maxsize=None)
def _get_package_from_git(
    url: str,
    branch: str | None = None,
    tag: str | None = None,
    rev: str | None = None,
    subdirectory: str | None = None,
    source_root: Path | None = None,
) -> Package:
    source = Git.clone(
        url=url,
        source_root=source_root,
        branch=branch,
        tag=tag,
        revision=rev,
        clean=False,
    )
    revision = Git.get_revision(source)

    path = Path(source.path)
    if subdirectory:
        path = path.joinpath(subdirectory)

    package = DirectOrigin.get_package_from_directory(path)
    package._source_type = "git"
    package._source_url = url
    package._source_reference = rev or tag or branch or "HEAD"
    package._source_resolved_reference = revision
    package._source_subdirectory = subdirectory

    return package


class DirectOrigin:
    @classmethod
    def get_package_from_file(cls, file_path: Path) -> Package:
        try:
            package = PackageInfo.from_path(path=file_path).to_package(
                root_dir=file_path
            )
        except PackageInfoError:
            raise RuntimeError(
                f"Unable to determine package info from path: {file_path}"
            )

        return package

    @classmethod
    def get_package_from_directory(cls, directory: Path) -> Package:
        return PackageInfo.from_directory(path=directory).to_package(root_dir=directory)

    @classmethod
    def get_package_from_url(cls, url: str) -> Package:
        file_name = os.path.basename(urllib.parse.urlparse(url).path)
        with tempfile.TemporaryDirectory() as temp_dir:
            dest = Path(temp_dir) / file_name
            download_file(url, dest)
            package = cls.get_package_from_file(dest)

            package.files = [
                {"file": file_name, "hash": "sha256:" + get_file_hash(dest)}
            ]

        package._source_type = "url"
        package._source_url = url

        return package

    @staticmethod
    def get_package_from_vcs(
        vcs: str,
        url: str,
        branch: str | None = None,
        tag: str | None = None,
        rev: str | None = None,
        subdirectory: str | None = None,
        source_root: Path | None = None,
    ) -> Package:
        if vcs != "git":
            raise ValueError(f"Unsupported VCS dependency {vcs}")

        return _get_package_from_git(
            url=url,
            branch=branch,
            tag=tag,
            rev=rev,
            subdirectory=subdirectory,
            source_root=source_root,
        )
