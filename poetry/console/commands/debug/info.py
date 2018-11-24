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
        env = Env.get(poetry.file.parent)

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
        listing = [
            "<info>Python</info>:         <comment>{}</>".format(env_python_version),
            "<info>Implementation</info>: <comment>{}</>".format(
                env.python_implementation
            ),
            "<info>Path</info>:           <comment>{}</>".format(
                env.path if env.is_venv() else "NA"
            ),
        ]
        if env.is_venv():
            listing.append(
                "<info>Valid</info>:          <{tag}>{is_valid}</{tag}>".format(
                    tag="comment" if env.is_sane() else "error", is_valid=env.is_sane()
                )
            )
        self.output.listing(listing)

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
