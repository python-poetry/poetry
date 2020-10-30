from typing import TYPE_CHECKING

from cleo import Command as BaseCommand


if TYPE_CHECKING:
    from poetry.poetry import Poetry  # noqa


class Command(BaseCommand):

    loggers = []

    @property
    def poetry(self):  # type: () -> "Poetry"
        return self.application.poetry

    def reset_poetry(self):  # type: () -> None
        self.application.reset_poetry()
