from .venv_command import VenvCommand
from shutil import rmtree


class EnvCommand(VenvCommand):
    """
    Shows information about the virtual environment.

    env
        { --p|path : Show the path to virtual environment. }
        { --python : Show the path to the python executable. }
        { --pip : Show the path to the pip executable. }
        { --rm : Remove the virtual environment. }
    """

    help = """The env command displays information about the virtual environment.
If it doesn't exist when the command is ran, it will be created."""

    def handle(self):
        path = self.venv.venv

        if self.option("path"):
            self.info(path)

        elif self.option("python"):
            self.info(self.venv.python)

        elif self.option("pip"):
            self.info(self.venv.pip)

        elif self.option("rm"):
            self.line("Removing virtual environment at <info>{}</>".format(path))
            rmtree(path, ignore_errors=True)

        else:
            version = ".".join(str(s) for s in self.venv.version_info[:3])
            impl = self.venv.python_implementation
            self.line("<info>Virtualenv path</>: <comment>{}</>".format(path))
            self.line("<info>Python version</>: <comment>{}</>".format(version))
            self.line("<info>Implementation</>: <comment>{}</>".format(impl))
