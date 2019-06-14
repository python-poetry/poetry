from cleo import argument
from cleo import option

from .command import Command


class SearchCommand(Command):

    name = "search"
    description = "Searches for packages on remote repositories."

    arguments = [argument("tokens", "The tokens to search for.", multiple=True)]
    options = [option("only-name", "N", "Search only in name.")]

    def handle(self):
        from poetry.repositories.pypi_repository import PyPiRepository

        flags = PyPiRepository.SEARCH_FULLTEXT
        if self.option("only-name"):
            flags = PyPiRepository.SEARCH_NAME

        results = PyPiRepository().search(self.argument("tokens"), flags)

        for result in results:
            self.line("")
            name = "<info>{}</>".format(result.name)

            name += " (<comment>{}</>)".format(result.version)

            self.line(name)

            if result.description:
                self.line(" {}".format(result.description))
