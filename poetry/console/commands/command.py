from cleo import Command as BaseCommand
from cleo.inputs import ListInput

from poetry.poetry import Poetry

from ..styles.poetry import PoetryStyle


class Command(BaseCommand):

    @property
    def poetry(self) -> Poetry:
        return self.get_application().poetry

    def reset_poetry(self) -> None:
        self.get_application().reset_poetry()

    def call(self, name, options=None):
        """
        Call another command.

        Fixing style being passed rather than an output
        """
        if options is None:
            options = []

        command = self.get_application().find(name)

        options = [('command', command.get_name())] + options

        return command.run(ListInput(options), self.output.output)

    def run(self, i, o) -> int:
        """
        Initialize command.
        """
        self.input = i
        self.output = PoetryStyle(i, o, self.get_application().venv)

        return super(BaseCommand, self).run(i, o)
