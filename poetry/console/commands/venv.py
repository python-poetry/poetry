from .command import Command


class VenvCommand(Command):
    """
    Print venv path
    """
    def __init__(self):
        super(VenvCommand, self).__init__('venv')

    def handle(self):
        from ...utils.env import Env

        poetry = self.poetry
        env = Env.get(cwd=poetry.file.parent)
        self.line(str(env.path))
