from .env_command import EnvCommand


class DevelopCommand(EnvCommand):
    """
    Installs the current project in development mode. (<error>Deprecated</error>)

    develop
    """

    help = """\
The <info>develop</> command is deprecated. Please use <info>install</info> instead.
"""

    def handle(self):
        self.line("<warning>develop is deprecated use install instead.</warning>")
        self.line("")

        return self.call("install")
