from .venv_command import VenvCommand


class RunCommand(VenvCommand):
    """
    Runs a command in the appropriate environment.

    run
        { args* : The command and arguments/options to run. }
    """

    def handle(self):
        args = self.argument('args')

        venv = self.venv

        return venv.execute(*args)

    def merge_application_definition(self, merge_args=True):
        if self._application is None \
                or (self._application_definition_merged
                    and (self._application_definition_merged_with_args or not merge_args)):
            return

        if merge_args:
            current_arguments = self._definition.get_arguments()
            self._definition.set_arguments(self._application.get_definition().get_arguments())
            self._definition.add_arguments(current_arguments)

        self._application_definition_merged = True
        if merge_args:
            self._application_definition_merged_with_args = True
