import os
import tempfile
import urllib.parse

from pathlib import Path
from subprocess import CalledProcessError
from typing import TYPE_CHECKING
from typing import Any
from typing import Union

from cleo.io.io import IO

from poetry.core.pyproject.toml import PyProjectTOML
from poetry.installation.base_installer import BaseInstaller
from poetry.repositories.pool import Pool
from poetry.utils._compat import encode
from poetry.utils.env import Env
from poetry.utils.helpers import safe_rmtree
from poetry.utils.pip import pip_editable_install
from poetry.utils.pip import pip_install


if TYPE_CHECKING:
    from poetry.core.packages.package import Package


class PipInstaller(BaseInstaller):
    def __init__(self, env: Env, io: IO, pool: Pool) -> None:
        self._env = env
        self._io = io
        self._pool = pool

    def install(self, package: "Package", update: bool = False) -> None:
        if package.source_type == "directory":
            self.install_directory(package)

            return

        if package.source_type == "git":
            self.install_git(package)

            return

        args = ["install", "--no-deps"]

        if (
            package.source_type not in {"git", "directory", "file", "url"}
            and package.source_url
        ):
            repository = self._pool.repository(package.source_reference)
            parsed = urllib.parse.urlparse(package.source_url)
            if parsed.scheme == "http":
                self._io.write_error(
                    "    <warning>Installing from unsecure host: {}</warning>".format(
                        parsed.hostname
                    )
                )
                args += ["--trusted-host", parsed.hostname]

            if repository.cert:
                args += ["--cert", str(repository.cert)]

            if repository.client_cert:
                args += ["--client-cert", str(repository.client_cert)]

            index_url = repository.authenticated_url

            args += ["--index-url", index_url]
            if self._pool.has_default():
                if repository.name != self._pool.repositories[0].name:
                    args += [
                        "--extra-index-url",
                        self._pool.repositories[0].authenticated_url,
                    ]

        if update:
            args.append("-U")

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

    def update(self, package: "Package", target: "Package") -> None:
        if package.source_type != target.source_type:
            # If the source type has changed, we remove the current
            # package to avoid perpetual updates in some cases
            self.remove(package)

        self.install(target, update=True)

    def remove(self, package: "Package") -> None:
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
                safe_rmtree(str(src_dir))

    def run(self, *args: Any, **kwargs: Any) -> str:
        return self._env.run_pip(*args, **kwargs)

    def requirement(self, package: "Package", formatted: bool = False) -> str:
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
            if package.root_dir:
                req = (package.root_dir / package.source_url).as_posix()
            else:
                req = os.path.realpath(package.source_url)

            if package.develop and package.source_type == "directory":
                req = ["-e", req]

            return req

        if package.source_type == "git":
            req = "git+{}@{}#egg={}".format(
                package.source_url, package.source_reference, package.name
            )

            if package.develop:
                req = ["-e", req]

            return req

        if package.source_type == "url":
            return f"{package.source_url}#egg={package.name}"

        return f"{package.name}=={package.version}"

    def create_temporary_requirement(self, package: "Package") -> str:
        fd, name = tempfile.mkstemp("reqs.txt", f"{package.name}-{package.version}")

        try:
            os.write(fd, encode(self.requirement(package, formatted=True)))
        finally:
            os.close(fd)

        return name

    def install_directory(self, package: "Package") -> Union[str, int]:
        from cleo.io.null_io import NullIO

        from poetry.factory import Factory

        req: Path

        if package.root_dir:
            req = (package.root_dir / package.source_url).as_posix()
        else:
            req = Path(package.source_url).resolve(strict=False)

        pyproject = PyProjectTOML(os.path.join(req, "pyproject.toml"))

        if pyproject.is_poetry_project():
            # Even if there is a build system specified
            # some versions of pip (< 19.0.0) don't understand it
            # so we need to check the version of pip to know
            # if we can rely on the build system
            legacy_pip = self._env.pip_version < self._env.pip_version.__class__(
                19, 0, 0
            )
            package_poetry = Factory().create_poetry(pyproject.file.path.parent)

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
                    if package.develop:
                        return pip_editable_install(
                            directory=req, environment=self._env
                        )
                    return pip_install(
                        path=req, environment=self._env, deps=False, upgrade=True
                    )

        if package.develop:
            return pip_editable_install(directory=req, environment=self._env)
        return pip_install(path=req, environment=self._env, deps=False, upgrade=True)

    def install_git(self, package: "Package") -> None:
        from poetry.core.packages.package import Package
        from poetry.core.vcs.git import Git

        src_dir = self._env.path / "src" / package.name
        if src_dir.exists():
            safe_rmtree(str(src_dir))

        src_dir.parent.mkdir(exist_ok=True)

        git = Git()
        git.clone(package.source_url, src_dir)

        reference = package.source_resolved_reference
        if not reference:
            reference = package.source_reference

        git.checkout(reference, src_dir)

        # Now we just need to install from the source directory
        pkg = Package(package.name, package.version)
        pkg._source_type = "directory"
        pkg._source_url = str(src_dir)
        pkg.develop = package.develop

        self.install_directory(pkg)
