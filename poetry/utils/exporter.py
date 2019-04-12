import sys

from poetry.packages.locker import Locker
from poetry.utils._compat import Path
from poetry.utils._compat import decode


class Exporter(object):
    """
    Exporter class to export a lock file to alternative formats.
    """

    ACCEPTED_FORMATS = ("requirements.txt",)

    def __init__(self, lock):  # type: (Locker) -> None
        self._lock = lock

    def export(
        self, fmt, cwd, output=None, with_hashes=True, dev=False
    ):  # type: (str, Path, str, bool, bool) -> None
        if fmt not in self.ACCEPTED_FORMATS:
            raise ValueError("Invalid export format: {}".format(fmt))

        getattr(self, "_export_{}".format(fmt.replace(".", "_")))(
            cwd, output, with_hashes=with_hashes, dev=dev
        )

    def _export_requirements_txt(
        self, cwd, output=None, with_hashes=True, dev=False
    ):  # type: (Path, str, bool, bool) -> None
        content = ""

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

                if package.source_type == "legacy" and package.source_url:
                    line += " \\\n"
                    line += "    --index-url {}".format(package.source_url)

                if package.hashes and with_hashes:
                    line += " \\\n"
                    for i, h in enumerate(package.hashes):
                        line += "    --hash=sha256:{}{}".format(
                            h, " \\\n" if i < len(package.hashes) - 1 else ""
                        )

            line += "\n"
            content += line

        self._output(content, cwd, output)

    def _output(self, content, cwd, output=None):  # type: (str, Path, str) -> None
        decoded = decode(content)
        if output is not None:
            filepath = cwd / output
            with filepath.open("w", encoding="utf-8") as f:
                f.write(decoded)
        else:
            sys.stdout.write(decoded)
