import os
import sys

from ..venv_command import VenvCommand


class DebugInfoCommand(VenvCommand):
    """
    Shows debug information.

    debug:info
    """

    def handle(self):
        poetry = self.poetry
        package = poetry.package
        venv = self.venv

        poetry_python_version = ".".join(str(s) for s in sys.version_info[:3])

        self.output.title("Poetry")
        self.output.listing(
            [
                "<info>Version</info>: <comment>{}</>".format(poetry.VERSION),
                "<info>Python</info>:  <comment>{}</>".format(poetry_python_version),
            ]
        )

        self.line("")

        venv_python_version = ".".join(str(s) for s in venv.version_info[:3])
        self.output.title("Virtualenv")
        self.output.listing(
            [
                "<info>Python</info>:         <comment>{}</>".format(
                    venv_python_version
                ),
                "<info>Implementation</info>: <comment>{}</>".format(
                    venv.python_implementation
                ),
                "<info>Path</info>:           <comment>{}</>".format(
                    venv.venv if venv.is_venv() else "NA"
                ),
            ]
        )

        self.line("")

        self.output.title("System")
        self.output.listing(
            [
                "<info>Platform</info>: <comment>{}</>".format(sys.platform),
                "<info>OS</info>:       <comment>{}</>".format(os.name),
            ]
        )

        self.line("")
