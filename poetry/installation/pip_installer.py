import os
import tempfile

from subprocess import CalledProcessError

from poetry.utils.helpers import get_http_basic_auth


try:
    import urllib.parse as urlparse
except ImportError:
    import urlparse

from poetry.utils._compat import encode
from poetry.utils.venv import Venv

from .base_installer import BaseInstaller


class PipInstaller(BaseInstaller):
    def __init__(self, venv, io):  # type: (Venv, ...) -> None
        self._venv = venv
        self._io = io

    def install(self, package, update=False):
        args = ["install", "--no-deps"]

        if package.source_type == "legacy" and package.source_url:
            parsed = urlparse.urlparse(package.source_url)
            if parsed.scheme == "http":
                self._io.write_error(
                    "    <warning>Installing from unsecure host: {}</warning>".format(
                        parsed.netloc
                    )
                )
                args += ["--trusted-host", parsed.netloc]

            auth = get_http_basic_auth(package.source_reference)
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
        return self._venv.run("pip", *args, **kwargs)

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
