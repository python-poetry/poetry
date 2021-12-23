import itertools
import urllib.parse

from typing import TYPE_CHECKING
from typing import Optional
from typing import Sequence
from typing import Union

from poetry.core.packages.utils.utils import path_to_url

from poetry.utils._compat import decode


if TYPE_CHECKING:
    from pathlib import Path

    from cleo.io.io import IO

    from poetry.poetry import Poetry


class Exporter:
    """
    Exporter class to export a lock file to alternative formats.
    """

    FORMAT_REQUIREMENTS_TXT = "requirements.txt"
    #: The names of the supported export formats.
    ACCEPTED_FORMATS = (FORMAT_REQUIREMENTS_TXT,)
    ALLOWED_HASH_ALGORITHMS = ("sha256", "sha384", "sha512")

    def __init__(self, poetry: "Poetry") -> None:
        self._poetry = poetry

    def export(
        self,
        fmt: str,
        cwd: "Path",
        output: Union["IO", str],
        with_hashes: bool = True,
        dev: bool = False,
        extras: Optional[Union[bool, Sequence[str]]] = None,
        with_credentials: bool = False,
        with_urls: bool = True,
    ) -> None:
        if fmt not in self.ACCEPTED_FORMATS:
            raise ValueError(f"Invalid export format: {fmt}")

        getattr(self, "_export_" + fmt.replace(".", "_"))(
            cwd,
            output,
            with_hashes=with_hashes,
            dev=dev,
            extras=extras,
            with_credentials=with_credentials,
            with_urls=with_urls,
        )

    def _export_requirements_txt(
        self,
        cwd: "Path",
        output: Union["IO", str],
        with_hashes: bool = True,
        dev: bool = False,
        extras: Optional[Union[bool, Sequence[str]]] = None,
        with_credentials: bool = False,
        with_urls: bool = True,
    ) -> None:
        indexes = set()
        content = ""
        dependency_lines = set()

        for package, groups in itertools.groupby(
            self._poetry.locker.get_project_dependency_packages(
                project_requires=self._poetry.package.all_requires,
                dev=dev,
                extras=extras,
            ),
            lambda dependency_package: dependency_package.package,
        ):
            line = ""
            dependency_packages = list(groups)
            dependency = dependency_packages[0].dependency
            marker = dependency.marker
            for dep_package in dependency_packages[1:]:
                marker = marker.union(dep_package.dependency.marker)
            dependency.marker = marker

            if package.develop:
                line += "-e "

            requirement = dependency.to_pep_508(with_extras=False)
            is_direct_local_reference = (
                dependency.is_file() or dependency.is_directory()
            )
            is_direct_remote_reference = dependency.is_vcs() or dependency.is_url()

            if is_direct_remote_reference:
                line = requirement
            elif is_direct_local_reference:
                dependency_uri = path_to_url(dependency.source_url)
                line = f"{dependency.name} @ {dependency_uri}"
            else:
                line = f"{package.name}=={package.version}"

            if not is_direct_remote_reference and ";" in requirement:
                markers = requirement.split(";", 1)[1].strip()
                if markers:
                    line += f" ; {markers}"

            if (
                not is_direct_remote_reference
                and not is_direct_local_reference
                and package.source_url
            ):
                indexes.add(package.source_url)

            if package.files and with_hashes:
                hashes = []
                for f in package.files:
                    h = f["hash"]
                    algorithm = "sha256"
                    if ":" in h:
                        algorithm, h = h.split(":")

                        if algorithm not in self.ALLOWED_HASH_ALGORITHMS:
                            continue

                    hashes.append(f"{algorithm}:{h}")

                if hashes:
                    sep = " \\\n"
                    line += sep + sep.join(f"    --hash={h}" for h in hashes)
            dependency_lines.add(line)

        content += "\n".join(sorted(dependency_lines))
        content += "\n"

        if indexes and with_urls:
            # If we have extra indexes, we add them to the beginning of the output
            indexes_header = ""
            for index in sorted(indexes):
                repositories = [
                    r
                    for r in self._poetry.pool.repositories
                    if r.url == index.rstrip("/")
                ]
                if not repositories:
                    continue
                repository = repositories[0]
                if (
                    self._poetry.pool.has_default()
                    and repository is self._poetry.pool.repositories[0]
                ):
                    url = (
                        repository.authenticated_url
                        if with_credentials
                        else repository.url
                    )
                    indexes_header = f"--index-url {url}\n"
                    continue

                url = (
                    repository.authenticated_url if with_credentials else repository.url
                )
                parsed_url = urllib.parse.urlsplit(url)
                if parsed_url.scheme == "http":
                    indexes_header += f"--trusted-host {parsed_url.netloc}\n"
                indexes_header += f"--extra-index-url {url}\n"

            content = indexes_header + "\n" + content

        self._output(content, cwd, output)

    def _output(self, content: str, cwd: "Path", output: Union["IO", str]) -> None:
        decoded = decode(content)
        try:
            output.write(decoded)
        except AttributeError:
            filepath = cwd / output
            with filepath.open("w", encoding="utf-8") as f:
                f.write(decoded)
