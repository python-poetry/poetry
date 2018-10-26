import os
import sys

from ..command import Command


class DebugInfoCommand(Command):
    """
    Shows debug information.

    debug:info
    """

    def handle(self):
        from ....utils.env import Env

        poetry = self.poetry
        env = Env.get(cwd=poetry.file.parent)

        poetry_python_version = ".".join(str(s) for s in sys.version_info[:3])

        self.output.title("Poetry")
        self.output.listing(
            [
                "<info>Version</info>: <comment>{}</>".format(poetry.VERSION),
                "<info>Python</info>:  <comment>{}</>".format(poetry_python_version),
            ]
        )

        self.line("")

        env_python_version = ".".join(str(s) for s in env.version_info[:3])
        self.output.title("Virtualenv")
        self.output.listing(
            [
                "<info>Python</info>:         <comment>{}</>".format(
                    env_python_version
                ),
                "<info>Implementation</info>: <comment>{}</>".format(
                    env.python_implementation
                ),
                "<info>Path</info>:           <comment>{}</>".format(
                    env.path if env.is_venv() else "NA"
                ),
            ]
        )

        self.line("")

        self.output.title("System")
        self.output.listing(
            [
                "<info>Platform</info>: <comment>{}</>".format(sys.platform),
                "<info>OS</info>:       <comment>{}</>".format(os.name),
                "<info>Python</info>:   <comment>{}</>".format(env.base),
            ]
        )

        self.line("")
