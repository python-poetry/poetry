from ..command import Command


class EnvInfoCommand(Command):
    """
    Display information about the current environment.

    info
        {--p|path : Only display the environment's path}
    """

    def handle(self):
        from poetry.utils.env import EnvManager

        poetry = self.poetry
        env = EnvManager(poetry.config).get(cwd=poetry.file.parent)

        if self.option("path"):
            if not env.is_venv():
                return 1

            self.write(str(env.path))

            return

        self._display_complete_info(env)

    def _display_complete_info(self, env):
        env_python_version = ".".join(str(s) for s in env.version_info[:3])
        self.line("")
        self.line("<b>Virtualenv</b>")
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
        self.line("\n".join(listing))

        self.line("")

        self.line("<b>System</b>")
        self.line(
            "\n".join(
                [
                    "<info>Platform</info>: <comment>{}</>".format(env.platform),
                    "<info>OS</info>:       <comment>{}</>".format(env.os),
                    "<info>Python</info>:   <comment>{}</>".format(env.base),
                ]
            )
        )
