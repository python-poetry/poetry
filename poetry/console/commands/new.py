from pathlib import Path

from poetry.layouts import layout

from .command import Command


class NewCommand(Command):
    """
    Creates a new Python project at <path>

    new
        { path : The path to create the project at. }
        { --name : Set the resulting package name. }
    """

    def handle(self):
        layout_ = layout('standard')

        path = Path.cwd() / Path(self.argument('path'))
        name = self.option('name')
        if not name:
            name = path.name

        if path.exists():
            if list(path.glob('*')):
                # Directory is not empty. Aborting.
                raise RuntimeError(
                    'Destination <fg=yellow;bg=red>{}</>'
                    'exists and is not empty'.format(
                        path
                    )
                )

        readme_format = 'rst'

        layout_ = layout_(name, '0.1.0', readme_format=readme_format)
        layout_.create(path)

        self.line(
            'Created package <info>{}</> in <fg=blue>{}</>'
            .format(name, path.relative_to(Path.cwd()))
        )
