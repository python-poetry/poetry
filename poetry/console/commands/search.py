from cleo import argument

from .command import Command


class SearchCommand(Command):

    name = "search"
    description = "Searches for packages on remote repositories."

    arguments = [argument("name", "The package names to search for.", multiple=True)]

    def handle(self):
        packages = self.argument("name")
        for name in packages:
            results = self.poetry.pool.search(name)
            for result in results:
                self.line("")
                name = "<info>{}</>".format(result.name)

                name += " (<comment>{}</>)".format(result.version)

                self.line(name)

                if result.description:
                    self.line(" {}".format(result.description))
