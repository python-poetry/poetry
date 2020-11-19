from cleo import option

from poetry.console.commands.command import Command
from poetry.exporter.requirements_txt import RequirementsTxtExporter


class RequirementsTxtExportCommand(Command):

    name = "requirements.txt"
    description = "Exports the lock as a requirements.txt file."

    options = [
        # The --output option should be global, however due to a testing limitation we keep this
        # per format sub-command for now
        option("output", "o", "The name of the output file.", flag=False),
        option("without-hashes", None, "Exclude hashes from the exported file."),
        option("dev", None, "Include development dependencies."),
        option(
            "extras",
            "E",
            "Extra sets of dependencies to include.",
            flag=False,
            multiple=True,
        ),
        option("with-credentials", None, "Include credentials for extra indices."),
        option(
            "format",
            "f",
            "Format to export to. Currently, only requirements.txt is supported. (Deprecated)",
            flag=False,
            default=name,
        ),
    ]

    def handle(self):
        output = self.option("output")

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

        exporter = RequirementsTxtExporter(self.poetry)
        exporter.export(
            self.poetry.file.parent,
            output or self.io,
            with_hashes=not self.option("without-hashes"),
            dev=self.option("dev"),
            extras=self.option("extras"),
            with_credentials=self.option("with-credentials"),
        )
