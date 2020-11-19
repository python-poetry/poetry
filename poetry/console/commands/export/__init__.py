from poetry.console.commands.command import Command
from poetry.console.commands.export.requirements_txt import RequirementsTxtExportCommand


class ExportCommand(Command):

    name = "export"
    description = "Exports the lock file to alternative formats."
    # TODO: Fix cleo command tester to allow for testing top-level command option inheritance
    options = []
    commands = [RequirementsTxtExportCommand()]

    def handle(self):
        return self.call("help", self._config.name)
