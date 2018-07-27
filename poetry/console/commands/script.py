from .venv_command import VenvCommand


class ScriptCommand(VenvCommand):
    """
    Executes a script defined in <comment>pyproject.toml</comment>. (<error>Deprecated</error>)

    script
        { script-name : The name of the script to execute }
        { args?* : The command and arguments/options to pass to the script. }
    """

    help = """The <info>script</> command is deprecated. Please use <info>run</info> instead.
    """

    def handle(self):
        self.line("<warning>script is deprecated use run instead.</warning>")
        self.line("")

        script = self.argument("script-name")
        argv = [script] + self.argument("args")

        scripts = self.poetry.local_config.get("scripts")
        if not scripts:
            raise RuntimeError("No scripts defined in pyproject.toml")

        if script not in scripts:
            raise ValueError("Script {} is not defined".format(script))

        module, callable_ = scripts[script].split(":")

        src_in_sys_path = "sys.path.append('src'); " if self._module.is_in_src() else ""

        cmd = ["python", "-c"]

        cmd += [
            '"import sys; '
            "from importlib import import_module; "
            "sys.argv = {!r}; {}"
            "import_module('{}').{}()\"".format(
                argv, src_in_sys_path, module, callable_
            )
        ]

        self.venv.run(*cmd, shell=True, call=True)

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
