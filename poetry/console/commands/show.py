from .command import Command


class ShowCommand(Command):
    """
    Shows information about packages.

    show
        { package? : Package to inspect. }
        { version? : Version to inspect. }
    """

    help = """The show command displays detailed information about a package, or
lists all packages available."""
