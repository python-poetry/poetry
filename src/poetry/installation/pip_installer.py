from __future__ import annotations

import contextlib
import os
import tempfile
import urllib.parse

from pathlib import Path
from subprocess import CalledProcessError
from typing import TYPE_CHECKING
from typing import Any

from poetry.core.constraints.version import Version
from poetry.core.pyproject.toml import PyProjectTOML

from poetry.installation.base_installer import BaseInstaller
from poetry.repositories.http_repository import HTTPRepository
from poetry.utils._compat import encode
from poetry.utils.helpers import remove_directory
from poetry.utils.pip import pip_install


if TYPE_CHECKING:
    from cleo.io.io import IO
    from poetry.core.masonry.builders.builder import Builder
    from poetry.core.packages.package import Package

    from poetry.repositories.repository_pool import RepositoryPool
    from poetry.utils.env import Env


class PipInstaller(BaseInstaller):
    def __init__(self, env: Env, io: IO, pool: RepositoryPool) -> None:
        self._env = env
        self._io = io
        self._pool = pool

    def install(self, package: Package, update: bool = False) -> None:
        if package.source_type == "directory":
            self.install_directory(package)

            return

        if package.source_type == "git":
            self.install_git(package)

            return

        args = ["install", "--no-deps", "--no-input"]

        if not package.is_direct_origin() and package.source_url:
            assert package.source_reference is not None
            repository = self._pool.repository(package.source_reference)
            parsed = urllib.parse.urlparse(package.source_url)
            if parsed.scheme == "http":
                assert parsed.hostname is not None
                self._io.write_error(
                    "    <warning>Installing from unsecure host:"
                    f" {parsed.hostname}</warning>"
                )
                args += ["--trusted-host", parsed.hostname]

            if isinstance(repository, HTTPRepository):
                certificates = repository.certificates

                if certificates.cert:
                    args += ["--cert", str(certificates.cert)]

                if parsed.scheme == "https" and not certificates.verify:
                    assert parsed.hostname is not None
                    args += ["--trusted-host", parsed.hostname]

                if certificates.client_cert:
                    args += ["--client-cert", str(certificates.client_cert)]

                index_url = repository.authenticated_url

                args += ["--index-url", index_url]

            if (
                self._pool.has_default()
                and repository.name != self._pool.repositories[0].name
            ):
                first_repository = self._pool.repositories[0]

                if isinstance(first_repository, HTTPRepository):
                    args += [
                        "--extra-index-url",
                        first_repository.authenticated_url,
                    ]

        if update:
            args.append("-U")

        req: str | list[str]
        if package.files and not package.source_url:
            # Format as a requirements.txt
            # We need to create a requirements.txt file
            # for each package in order to check hashes.
            # This is far from optimal but we do not have any
            # other choice since this is the only way for pip
            # to verify hashes.
            req = self.create_temporary_requirement(package)
            args += ["-r", req]

            try:
                self.run(*args)
            finally:
                os.unlink(req)
        else:
            req = self.requirement(package)
            if not isinstance(req, list):
                args.append(req)
            else:
                args += req

            self.run(*args)

    def update(self, package: Package, target: Package) -> None:
        if package.source_type != target.source_type:
            # If the source type has changed, we remove the current
            # package to avoid perpetual updates in some cases
            self.remove(package)

        self.install(target, update=True)

    def remove(self, package: Package) -> None:
        try:
            self.run("uninstall", package.name, "-y")
        except CalledProcessError as e:
            if "not installed" in str(e):
                return

            raise

        # This is a workaround for https://github.com/pypa/pip/issues/4176
        for nspkg_pth_file in self._env.site_packages.find_distribution_nspkg_pth_files(
            distribution_name=package.name
        ):
            nspkg_pth_file.unlink()

        # If we have a VCS package, remove its source directory
        if package.source_type == "git":
            src_dir = self._env.path / "src" / package.name
            if src_dir.exists():
                remove_directory(src_dir, force=True)

    def run(self, *args: Any, **kwargs: Any) -> int | str:
        return self._env.run_pip(*args, **kwargs)

    def requirement(self, package: Package, formatted: bool = False) -> str | list[str]:
        if formatted and not package.source_type:
            req = f"{package.name}=={package.version}"
            for f in package.files:
                hash_type = "sha256"
                h = f["hash"]
                if ":" in h:
                    hash_type, h = h.split(":")

                req += f" --hash {hash_type}:{h}"

            req += "\n"

            return req

        if package.source_type in ["file", "directory"]:
            assert package.source_url is not None
            if package.root_dir:
                req = (package.root_dir / package.source_url).as_posix()
            else:
                req = os.path.realpath(package.source_url)

            if package.develop and package.source_type == "directory":
                return ["-e", req]

            return req

        if package.source_type == "git":
            req = (
                f"git+{package.source_url}@{package.source_reference}"
                f"#egg={package.name}"
            )

            if package.source_subdirectory:
                req += f"&subdirectory={package.source_subdirectory}"

            if package.develop:
                return ["-e", req]

            return req

        if package.source_type == "url":
            return f"{package.source_url}#egg={package.name}"

        return f"{package.name}=={package.version}"

    def create_temporary_requirement(self, package: Package) -> str:
        fd, name = tempfile.mkstemp("reqs.txt", f"{package.name}-{package.version}")
        req = self.requirement(package, formatted=True)
        if isinstance(req, list):
            req = " ".join(req)

        try:
            os.write(fd, encode(req))
        finally:
            os.close(fd)

        return name

    def install_directory(self, package: Package) -> str | int:
        from cleo.io.null_io import NullIO

        from poetry.factory import Factory

        assert package.source_url is not None
        if package.root_dir:
            req = package.root_dir / package.source_url
        else:
            req = Path(package.source_url).resolve(strict=False)

        if package.source_subdirectory:
            req /= package.source_subdirectory

        pyproject = PyProjectTOML(os.path.join(req, "pyproject.toml"))

        package_poetry = None
        if pyproject.is_poetry_project():
            with contextlib.suppress(RuntimeError):
                package_poetry = Factory().create_poetry(pyproject.file.path.parent)

        if package_poetry is not None:
            # Even if there is a build system specified
            # some versions of pip (< 19.0.0) don't understand it
            # so we need to check the version of pip to know
            # if we can rely on the build system
            legacy_pip = self._env.pip_version < Version.from_parts(19, 0, 0)

            builder: Builder
            if package.develop and not package_poetry.package.build_script:
                from poetry.masonry.builders.editable import EditableBuilder

                # This is a Poetry package in editable mode
                # we can use the EditableBuilder without going through pip
                # to install it, unless it has a build script.
                builder = EditableBuilder(package_poetry, self._env, NullIO())
                builder.build()

                return 0
            elif legacy_pip or package_poetry.package.build_script:
                from poetry.core.masonry.builders.sdist import SdistBuilder

                # We need to rely on creating a temporary setup.py
                # file since the version of pip does not support
                # build-systems
                # We also need it for non-PEP-517 packages
                builder = SdistBuilder(package_poetry)

                with builder.setup_py():
                    return pip_install(
                        path=req,
                        environment=self._env,
                        upgrade=True,
                        editable=package.develop,
                    )

        return pip_install(
            path=req, environment=self._env, upgrade=True, editable=package.develop
        )

    def install_git(self, package: Package) -> None:
        from poetry.core.packages.package import Package

        from poetry.vcs.git import Git

        assert package.source_url is not None
        source = Git.clone(
            url=package.source_url,
            source_root=self._env.path / "src",
            revision=package.source_resolved_reference or package.source_reference,
        )

        # Now we just need to install from the source directory
        pkg = Package(
            name=package.name,
            version=package.version,
            source_type="directory",
            source_url=str(source.path),
            source_subdirectory=package.source_subdirectory,
            develop=package.develop,
        )

        self.install_directory(pkg)
