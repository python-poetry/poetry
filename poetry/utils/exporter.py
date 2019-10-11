from typing import Union

from clikit.api.io import IO

from poetry.packages.directory_dependency import DirectoryDependency
from poetry.packages.file_dependency import FileDependency
from poetry.packages.url_dependency import URLDependency
from poetry.packages.vcs_dependency import VCSDependency
from poetry.poetry import Poetry
from poetry.utils._compat import Path
from poetry.utils._compat import decode


class Exporter(object):
    """
    Exporter class to export a lock file to alternative formats.
    """

    ACCEPTED_FORMATS = ("requirements.txt",)
    ALLOWED_HASH_ALGORITHMS = ("sha256", "sha384", "sha512")

    def __init__(self, poetry):  # type: (Poetry) -> None
        self._poetry = poetry

    def export(
        self,
        fmt,
        cwd,
        output,
        with_hashes=True,
        dev=False,
        extras=None,
        with_credentials=False,
    ):  # type: (str, Path, Union[IO, str], bool, bool, bool) -> None
        if fmt not in self.ACCEPTED_FORMATS:
            raise ValueError("Invalid export format: {}".format(fmt))

        getattr(self, "_export_{}".format(fmt.replace(".", "_")))(
            cwd,
            output,
            with_hashes=with_hashes,
            dev=dev,
            extras=extras,
            with_credentials=with_credentials,
        )

    def _export_requirements_txt(
        self,
        cwd,
        output,
        with_hashes=True,
        dev=False,
        extras=None,
        with_credentials=False,
    ):  # type: (Path, Union[IO, str], bool, bool, bool) -> None
        indexes = []
        content = ""

        # Generate a list of package names we have opted into via `extras`
        extras_set = frozenset(extras or ())
        extra_package_names = set()
        if extras:
            for extra_name, extra_packages in self._poetry.locker.lock_data.get(
                "extras", {}
            ).items():
                if extra_name in extras_set:
                    extra_package_names.update(extra_packages)

        for package in sorted(
            self._poetry.locker.locked_repository(dev).packages, key=lambda p: p.name
        ):
            # If a package is optional and we haven't opted in to it, continue
            if package.optional and package.name not in extra_package_names:
                continue

            if package.source_type == "git":
                dependency = VCSDependency(
                    package.name,
                    package.source_type,
                    package.source_url,
                    package.source_reference,
                )
                dependency.marker = package.marker
                line = "-e git+{}@{}#egg={}".format(
                    package.source_url, package.source_reference, package.name
                )
            elif package.source_type in ["directory", "file", "url"]:
                if package.source_type == "file":
                    dependency = FileDependency(package.name, Path(package.source_url))
                elif package.source_type == "directory":
                    dependency = DirectoryDependency(
                        package.name, Path(package.source_url)
                    )
                else:
                    dependency = URLDependency(package.name, package.source_url)

                dependency.marker = package.marker

                line = "{}".format(package.source_url)
                if package.develop:
                    line = "-e " + line
            else:
                dependency = package.to_dependency()
                line = "{}=={}".format(package.name, package.version)

            requirement = dependency.to_pep_508()
            if ";" in requirement:
                line += "; {}".format(requirement.split(";")[1].strip())

            if package.source_type == "legacy" and package.source_url:
                indexes.append(package.source_url)

            if package.files and with_hashes:
                hashes = []
                for f in package.files:
                    h = f["hash"]
                    algorithm = "sha256"
                    if ":" in h:
                        algorithm, h = h.split(":")

                        if algorithm not in self.ALLOWED_HASH_ALGORITHMS:
                            continue

                    hashes.append("{}:{}".format(algorithm, h))

                if hashes:
                    line += " \\\n"
                    for i, h in enumerate(hashes):
                        line += "    --hash={}{}".format(
                            h, " \\\n" if i < len(hashes) - 1 else ""
                        )

            line += "\n"
            content += line

        if indexes:
            # If we have extra indexes, we add them to the begin
            # of the output
            indexes_header = ""
            for index in indexes:
                repository = [
                    r
                    for r in self._poetry.pool.repositories
                    if r.url == index.rstrip("/")
                ][0]
                if (
                    self._poetry.pool.has_default()
                    and repository is self._poetry.pool.repositories[0]
                ):
                    url = (
                        repository.authenticated_url
                        if with_credentials
                        else repository.url
                    )
                    indexes_header = "--index-url {}\n".format(url)
                    continue

                url = (
                    repository.authenticated_url if with_credentials else repository.url
                )
                indexes_header += "--extra-index-url {}\n".format(url)

            content = indexes_header + "\n" + content

        self._output(content, cwd, output)

    def _output(
        self, content, cwd, output
    ):  # type: (str, Path, Union[IO, str]) -> None
        decoded = decode(content)
        try:
            output.write(decoded)
        except AttributeError:
            filepath = cwd / output
            with filepath.open("w", encoding="utf-8") as f:
                f.write(decoded)
