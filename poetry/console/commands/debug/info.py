import sys

from clikit.args import StringArgs

from ..command import Command


class DebugInfoCommand(Command):

    name = "info"
    description = "Shows debug information."

    def handle(self):
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
        args = StringArgs("")
        command = self.application.get_command("env").get_sub_command("info")

        return command.run(args, self._io)
