from poetry.utils.exporter import Exporter

from .command import Command


class ExportCommand(Command):
    """
    Exports the lock file to alternative formats.

    export
        {--f|format= : Format to export to.}
        {--without-hashes : Exclude hashes from the exported file.}
        {--dev : Include development dependencies.}
    """

    def handle(self):
        fmt = self.option("format")

        if fmt not in Exporter.ACCEPTED_FORMATS:
            raise ValueError("Invalid export format: {}".format(fmt))

        locker = self.poetry.locker
        if not locker.is_locked():
            self.line("<comment>The lock file does not exist. Locking.</comment>")
            options = []
            if self.io.is_debug():
                options.append(("-vvv", None))
            elif self.io.is_very_verbose():
                options.append(("-vv", None))
            elif self.io.is_verbose():
                options.append(("-v", None))

            self.call("lock", options)

        if not locker.is_fresh():
            self.line(
                "<warning>"
                "Warning: The lock file is not up to date with "
                "the latest changes in pyproject.toml. "
                "You may be getting outdated dependencies. "
                "Run update to update them."
                "</warning>"
            )

        exporter = Exporter(self.poetry.locker)
        exporter.export(
            fmt,
            self.poetry.file.parent,
            with_hashes=not self.option("without-hashes"),
            dev=self.option("dev"),
        )
