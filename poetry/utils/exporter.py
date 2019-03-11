import requests

from poetry.packages.locker import Locker
from poetry.repositories import Pool
from poetry.repositories.auth import NetrcAuth
from poetry.repositories.legacy_repository import LegacyRepository
from poetry.utils._compat import Path
from poetry.utils._compat import decode


class Exporter(object):
    """
    Exporter class to export a lock file to alternative formats.
    """

    ACCEPTED_FORMATS = ("requirements.txt",)

    def __init__(self, lock, pool):  # type: (Locker, Pool) -> None
        self._lock = lock
        self._pool = pool

    def export(
        self, fmt, cwd, with_hashes=True, dev=False
    ):  # type: (str, Path, bool, bool) -> None
        if fmt not in self.ACCEPTED_FORMATS:
            raise ValueError("Invalid export format: {}".format(fmt))

        getattr(self, "_export_{}".format(fmt.replace(".", "_")))(
            cwd, with_hashes=with_hashes, dev=dev
        )

    @staticmethod
    def _format_repositories(repositories):
        formatted_repos = set()
        for repo in repositories:
            if isinstance(repo, LegacyRepository) and repo.auth:
                auth = NetrcAuth.from_auth(repo.auth)
                r = auth(requests.Request("GET", repo.url))
                formatted_repos.add(r.url)
            else:
                formatted_repos.add(repo.url)
        return formatted_repos

    def _export_requirements_txt(
        self, cwd, with_hashes=True, dev=False
    ):  # type: (Path, bool, bool) -> None
        filepath = cwd / "requirements.txt"

        repositories = Exporter._format_repositories(self._pool.repositories)
        content = "".join(
            sorted(["--extra-index-url {}\n".format(url) for url in repositories])
        )

        for package in sorted(
            self._lock.locked_repository(dev).packages, key=lambda p: p.name
        ):
            if package.source_type == "git":
                line = "-e git+{}@{}#egg={}".format(
                    package.source_url, package.source_reference, package.name
                )
            elif package.source_type in ["directory", "file"]:
                line = ""
                if package.develop:
                    line += "-e "

                line += package.source_url
            else:
                line = "{}=={}".format(package.name, package.version.text)

                if package.hashes and with_hashes:
                    line += " \\\n"
                    for i, h in enumerate(package.hashes):
                        line += "    --hash=sha256:{}{}".format(
                            h, " \\\n" if i < len(package.hashes) - 1 else ""
                        )

            line += "\n"
            content += line

        with filepath.open("w", encoding="utf-8") as f:
            f.write(decode(content))
