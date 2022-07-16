from __future__ import annotations

from typing import TYPE_CHECKING

from cleo.helpers import argument

from poetry.console.commands.env_command import EnvCommand


if TYPE_CHECKING:
    from poetry.core.masonry.utils.module import Module


class RunCommand(EnvCommand):
    name = "run"
    description = "Runs a command in the appropriate environment."

    arguments = [
        argument("args", "The command and arguments/options to run.", multiple=True)
    ]

    def handle(self) -> int:
        args = self.argument("args")
        script = args[0]
        scripts = self.poetry.local_config.get("scripts")

        if scripts and script in scripts:
            return self.run_script(scripts[script], args)

        try:
            return self.env.execute(*args)
        except FileNotFoundError:
            self.line_error(f"<error>Command not found: <c1>{script}</c1></error>")
            return 1

    @property
    def _module(self) -> Module:
        from poetry.core.masonry.utils.module import Module

        poetry = self.poetry
        package = poetry.package
        path = poetry.file.parent
        module = Module(package.name, path.as_posix(), package.packages)

        return module

    def run_script(self, script: str | dict[str, str], args: str) -> int:
        if isinstance(script, dict):
            script = script["callable"]

        module, callable_ = script.split(":")

        src_in_sys_path = "sys.path.append('src'); " if self._module.is_in_src() else ""

        cmd = ["python", "-c"]

        cmd += [
            "import sys; "
            "from importlib import import_module; "
            f"sys.argv = {args!r}; {src_in_sys_path}"
            f"import_module('{module}').{callable_}()"
        ]

        return self.env.execute(*cmd)
