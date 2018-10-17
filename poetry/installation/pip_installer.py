import os
import tempfile

from subprocess import CalledProcessError

from poetry.config import Config
from poetry.utils.helpers import get_http_basic_auth


try:
    import urllib.parse as urlparse
except ImportError:
    import urlparse

from poetry.utils._compat import encode
from poetry.utils.env import Env

from .base_installer import BaseInstaller


class PipInstaller(BaseInstaller):
    def __init__(self, env, io):  # type: (Env, ...) -> None
        self._env = env
        self._io = io

    def install(self, package, update=False):
        if package.source_type == "directory":
            self.install_directory(package, update=update)

            return

        if package.source_type == "git":
            self.install_git(package)

            return

        args = ["install", "--no-deps"]

        if package.source_type == "legacy" and package.source_url:
            parsed = urlparse.urlparse(package.source_url)
            if parsed.scheme == "http":
                self._io.write_error(
                    "    <warning>Installing from unsecure host: {}</warning>".format(
                        parsed.hostname
                    )
                )
                args += ["--trusted-host", parsed.hostname]

            auth = get_http_basic_auth(
                Config.create("auth.toml"), package.source_reference
            )
            if auth:
                index_url = "{scheme}://{username}:{password}@{netloc}{path}".format(
                    scheme=parsed.scheme,
                    username=auth[0],
                    password=auth[1],
                    netloc=parsed.netloc,
                    path=parsed.path,
                )
            else:
                index_url = package.source_url

            args += ["--index-url", index_url]

        if update:
            args.append("-U")

        if package.hashes and not package.source_type:
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

    def update(self, _, target):
        self.install(target, update=True)

    def remove(self, package):
        try:
            self.run("uninstall", package.name, "-y")
        except CalledProcessError as e:
            if "not installed" in str(e):
                return

            raise

    def run(self, *args, **kwargs):  # type: (...) -> str
        return self._env.run("pip", *args, **kwargs)

    def requirement(self, package, formatted=False):
        if formatted and not package.source_type:
            req = "{}=={}".format(package.name, package.version)
            for h in package.hashes:
                req += " --hash sha256:{}".format(h)

            req += "\n"

            return req

        if package.source_type in ["file", "directory"]:
            if package.root_dir:
                req = os.path.join(package.root_dir, package.source_url)
            else:
                req = os.path.realpath(package.source_url)

            if package.develop:
                req = ["-e", req]

            return req

        if package.source_type == "git":
            return "git+{}@{}#egg={}".format(
                package.source_url, package.source_reference, package.name
            )

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

    def install_directory(self, package, update=False):
        from poetry.io import NullIO
        from poetry.masonry.builder import SdistBuilder
        from poetry.poetry import Poetry
        from poetry.utils._compat import decode
        from poetry.utils.env import NullEnv
        from poetry.utils.toml_file import TomlFile

        if package.root_dir:
            req = os.path.join(package.root_dir, package.source_url)
        else:
            req = os.path.realpath(package.source_url)

        args = ["install", "--no-deps", "-U"]

        pyproject = TomlFile(os.path.join(req, "pyproject.toml"))

        has_poetry = False
        if pyproject.exists():
            pyproject_content = pyproject.read()
            has_poetry = (
                "tool" in pyproject_content and "poetry" in pyproject_content["tool"]
            )
            has_build_system = "build-system" in pyproject_content

        setup = os.path.join(req, "setup.py")
        has_setup = os.path.exists(setup)
        if not has_setup and has_poetry and (package.develop or not has_build_system):
            # We actually need to rely on creating a temporary setup.py
            # file since pip, as of this comment, does not support
            # build-system for editable packages
            # We also need it for non-PEP-517 packages
            builder = SdistBuilder(Poetry.create(pyproject.parent), NullEnv(), NullIO())

            with open(setup, "w") as f:
                f.write(decode(builder.build_setup()))

        if package.develop:
            args.append("-e")

        args.append(req)

        try:
            return self.run(*args)
        finally:
            if not has_setup and os.path.exists(setup):
                os.remove(setup)

    def install_git(self, package):
        from poetry.packages import Package
        from poetry.utils._compat import Path
        from poetry.utils.helpers import temporary_directory
        from poetry.vcs import Git

        with temporary_directory() as tmp_dir:
            tmp_dir = Path(tmp_dir)

            git = Git()
            git.clone(package.source_url, tmp_dir)
            git.checkout(package.source_reference, tmp_dir)

            # Now we just need to install from the temporary directory
            pkg = Package(package.name, package.version)
            pkg.source_type = "directory"
            pkg.source_url = str(tmp_dir)
            pkg.develop = False

            self.install_directory(pkg)
