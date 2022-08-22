import os
import tempfile

from subprocess import CalledProcessError

from clikit.api.io import IO

from poetry.core.pyproject.toml import PyProjectTOML
from poetry.repositories.pool import Pool
from poetry.utils._compat import encode
from poetry.utils.env import Env
from poetry.utils.helpers import safe_rmtree

from .base_installer import BaseInstaller


try:
    import urllib.parse as urlparse
except ImportError:
    import urlparse


class PipInstaller(BaseInstaller):
    def __init__(self, env, io, pool):  # type: (Env, IO, Pool) -> None
        self._env = env
        self._io = io
        self._pool = pool

    def install(self, package, update=False):
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
            parsed = urlparse.urlparse(package.source_url)
            if parsed.scheme == "http":
                self._io.error(
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

    def update(self, package, target):
        if package.source_type != target.source_type:
            # If the source type has changed, we remove the current
            # package to avoid perpetual updates in some cases
            self.remove(package)

        self.install(target, update=True)

    def remove(self, package):
        try:
            self.run("uninstall", package.name, "-y")
        except CalledProcessError as e:
            if "not installed" in str(e):
                return

            raise

        # This is a workaround for https://github.com/pypa/pip/issues/4176
        nspkg_pth_file = self._env.site_packages.path / "{}-nspkg.pth".format(
            package.name
        )
        if nspkg_pth_file.exists():
            nspkg_pth_file.unlink()

        # If we have a VCS package, remove its source directory
        if package.source_type == "git":
            src_dir = self._env.path / "src" / package.name
            if src_dir.exists():
                safe_rmtree(str(src_dir))

    def run(self, *args, **kwargs):  # type: (...) -> str
        return self._env.run_pip(*args, **kwargs)

    def requirement(self, package, formatted=False):
        if formatted and not package.source_type:
            req = "{}=={}".format(package.name, package.version)
            for f in package.files:
                hash_type = "sha256"
                h = f["hash"]
                if ":" in h:
                    hash_type, h = h.split(":")

                req += " --hash {}:{}".format(hash_type, h)

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
            return "{}#egg={}".format(package.source_url, package.name)

        return "{}=={}".format(package.name, package.version)

    def create_temporary_requirement(self, package):
        fd, name = tempfile.mkstemp(
            "reqs.txt", "{}-{}".format(package.name, package.version)
        )

        try:
            os.write(fd, encode(self.requirement(package, formatted=True)))
        finally:
            os.close(fd)

        return name

    def install_directory(self, package):
        from poetry.factory import Factory
        from poetry.io.null_io import NullIO

        if package.root_dir:
            req = (package.root_dir / package.source_url).as_posix()
        else:
            req = os.path.realpath(package.source_url)

        args = ["install", "--no-deps", "-U"]

        pyproject = PyProjectTOML(os.path.join(req, "pyproject.toml"))

        if pyproject.is_poetry_project():
            # Even if there is a build system specified
            # some versions of pip (< 19.0.0) don't understand it
            # so we need to check the version of pip to know
            # if we can rely on the build system
            legacy_pip = self._env.pip_version < self._env.pip_version.__class__(
                19, 0, 0
            )

            try:
                package_poetry = Factory().create_poetry(pyproject.file.path.parent)
            except RuntimeError:
                package_poetry = None

            if package_poetry is not None:
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
                            args.append("-e")

                        args.append(req)

                        return self.run(*args)

        if package.develop:
            args.append("-e")

        args.append(req)

        return self.run(*args)

    def install_git(self, package):
        from poetry.core.packages import Package
        from poetry.core.vcs import Git

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
