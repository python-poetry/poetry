import os
import sys

from ..command import Command


class DebugInfoCommand(Command):
    """
    Shows debug information.

    info
    """

    def handle(self):
        from ....utils.env import Env

        poetry = self.poetry
        env = Env.get(poetry.file.parent)

        poetry_python_version = ".".join(str(s) for s in sys.version_info[:3])

        self.line("")
        self.line("<b>Poetry</b>")
        self.line("")
        self.line("<info>Version</info>: <comment>{}</>".format(poetry.VERSION))
        self.line("<info>Python</info>:  <comment>{}</>".format(poetry_python_version))

        self.line("")

        env_python_version = ".".join(str(s) for s in env.version_info[:3])
        self.line("<b>Virtualenv</b>")
        self.line("")
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

        for line in listing:
            self.line(line)

        self.line("")

        self.line("<b>System</b>")
        self.line("")
        listing = [
            "<info>Platform</info>: <comment>{}</>".format(sys.platform),
            "<info>OS</info>:       <comment>{}</>".format(os.name),
            "<info>Python</info>:   <comment>{}</>".format(env.base),
        ]

        for line in listing:
            self.line(line)

        self.line("")
