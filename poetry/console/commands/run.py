from .env_command import EnvCommand


class RunCommand(EnvCommand):
    """
    Runs a command in the appropriate environment.

    run
        { args* : The command and arguments/options to run. }
    """

    def handle(self):
        args = self.argument("args")
        script = args[0]
        scripts = self.poetry.local_config.get("scripts")

        if scripts and script in scripts:
            return self.run_script(scripts[script], args)

        return self.env.execute(*args)

    def run_script(self, script, args):
        if isinstance(script, dict):
            script = script["callable"]

        module, callable_ = script.split(":")

        src_in_sys_path = "sys.path.append('src'); " if self._module.is_in_src() else ""

        cmd = ["python", "-c"]

        cmd += [
            '"import sys; '
            "from importlib import import_module; "
            "sys.argv = {!r}; {}"
            "import_module('{}').{}()\"".format(
                args, src_in_sys_path, module, callable_
            )
        ]

        return self.env.run(*cmd, shell=True, call=True)

    @property
    def _module(self):
        from ...masonry.utils.module import Module

        poetry = self.poetry
        package = poetry.package
        path = poetry.file.parent
        module = Module(package.name, path.as_posix())
        return module

    def merge_application_definition(self, merge_args=True):
        if self._application is None or (
            self._application_definition_merged
            and (self._application_definition_merged_with_args or not merge_args)
        ):
            return

        if merge_args:
            current_arguments = self._definition.get_arguments()
            self._definition.set_arguments(
                self._application.get_definition().get_arguments()
            )
            self._definition.add_arguments(current_arguments)

        self._application_definition_merged = True
        if merge_args:
            self._application_definition_merged_with_args = True
