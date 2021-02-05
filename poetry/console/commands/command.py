from typing import TYPE_CHECKING

from cleo.commands.command import Command as BaseCommand


if TYPE_CHECKING:
    from poetry.console.application import Application
    from poetry.poetry import Poetry


class Command(BaseCommand):
    loggers = []

    @property
    def poetry(self) -> "Poetry":
        return self.get_application().poetry

    def get_application(self) -> "Application":
        return self.application

    def reset_poetry(self) -> None:
        self.get_application().reset_poetry()
