from .env_command import EnvCommand


class ScriptCommand(EnvCommand):
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

        self.env.run(*cmd, shell=True, call=True)

    @property
    def _module(self):
        from ...masonry.utils.module import Module

        poetry = self.poetry
        package = poetry.package
        path = poetry.file.parent
        module = Module(package.name, path.as_posix())

        return module
