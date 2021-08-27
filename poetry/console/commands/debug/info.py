import sys

from ..command import Command


class DebugInfoCommand(Command):

    name = "debug info"
    description = "Shows debug information."

    def handle(self) -> int:
        poetry_python_version = ".".join(str(s) for s in sys.version_info[:3])

        self.line("")
        self.line("<b>Poetry</b>")
        self.line(
            "\n".join(
                [
                    "<info>Version</info>: <comment>{}</>".format(self.poetry.VERSION),
                    "<info>Python</info>:  <comment>{}</>".format(
                        poetry_python_version
                    ),
                ]
            )
        )
        command = self.application.get("env info")

        return command.run(self._io)
