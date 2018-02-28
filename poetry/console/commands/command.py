from cleo import Command as BaseCommand

from poetry.poetry import Poetry

from ..styles.poetry import PoetryStyle


class Command(BaseCommand):

    @property
    def poetry(self) -> Poetry:
        return self.get_application().poetry

    def reset_poetry(self) -> None:
        self.get_application().reset_poetry()

    def run(self, i, o) -> int:
        """
        Initialize command.
        """
        self.input = i
        self.output = PoetryStyle(i, o, self.get_application().venv)

        return super(BaseCommand, self).run(i, o)
