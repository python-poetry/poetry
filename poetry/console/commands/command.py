from cleo import Command as BaseCommand


class Command(BaseCommand):

    loggers = []

    @property
    def poetry(self):
        return self.application.poetry

    def reset_poetry(self):  # type: () -> None
        self.application.reset_poetry()
