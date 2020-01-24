from cleo import argument

from .command import Command


class SearchCommand(Command):

    name = "search"
    description = "Searches for packages on remote repositories."

    arguments = [argument("tokens", "The tokens to search for.", multiple=True)]

    def handle(self):
        from poetry.repositories.pypi_repository import PyPiRepository

        results = PyPiRepository().search(self.argument("tokens"))

        for result in results:
            self.line("")
            name = "<info>{}</>".format(result.name)

            name += " (<comment>{}</>)".format(result.version)

            self.line(name)

            if result.description:
                self.line(" {}".format(result.description))
