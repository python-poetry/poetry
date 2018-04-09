from cleo import Command as BaseCommand

from ..styles.poetry import PoetryStyle


class Command(BaseCommand):

    @property
    def poetry(self):
        return self.get_application().poetry

    def reset_poetry(self):  # type: () -> None
        self.get_application().reset_poetry()

    def run(self, i, o):  # type: () -> int
        """
        Initialize command.
        """
        self.input = i
        self.output = PoetryStyle(i, o)

        return super(BaseCommand, self).run(i, o)
