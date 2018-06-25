from .command import Command


class NewCommand(Command):
    """
    Creates a new Python project at <path>

    new
        { path : The path to create the project at. }
        { --name= : Set the resulting package name. }
        { --src : Use the src layout for the project. }
    """

    def handle(self):
        from poetry.layouts import layout
        from poetry.utils._compat import Path
        from poetry.vcs.git import GitConfig

        if self.option("src"):
            layout_ = layout("src")
        else:
            layout_ = layout("standard")

        path = Path.cwd() / Path(self.argument("path"))
        name = self.option("name")
        if not name:
            name = path.name

        if path.exists():
            if list(path.glob("*")):
                # Directory is not empty. Aborting.
                raise RuntimeError(
                    "Destination <fg=yellow>{}</> "
                    "exists and is not empty".format(path)
                )

        readme_format = "rst"

        config = GitConfig()
        author = None
        if config.get("user.name"):
            author = config["user.name"]
            author_email = config.get("user.email")
            if author_email:
                author += " <{}>".format(author_email)

        layout_ = layout_(name, "0.1.0", author=author, readme_format=readme_format)
        layout_.create(path)

        self.line(
            "Created package <info>{}</> in <fg=blue>{}</>".format(
                name, path.relative_to(Path.cwd())
            )
        )
