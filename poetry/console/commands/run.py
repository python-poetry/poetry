from typing import TYPE_CHECKING
from typing import Any
from typing import Union

from cleo.helpers import argument

from .env_command import EnvCommand


if TYPE_CHECKING:
    from poetry.core.masonry.utils.module import Module


class RunCommand(EnvCommand):

    name = "run"
    description = "Runs a command in the appropriate environment."

    arguments = [
        argument("args", "The command and arguments/options to run.", multiple=True)
    ]

    def handle(self) -> Any:
        args = self.argument("args")
        script = args[0]
        scripts = self.poetry.local_config.get("scripts")

        if scripts and script in scripts:
            return self.run_script(scripts[script], args)

        return self.env.execute(*args)

    @property
    def _module(self) -> "Module":
        from poetry.core.masonry.utils.module import Module

        poetry = self.poetry
        package = poetry.package
        path = poetry.file.parent
        module = Module(package.name, path.as_posix(), package.packages)

        return module

    def run_script(self, script: Union[str, dict], args: str) -> Any:
        if isinstance(script, dict):
            script = script["callable"]

        module, callable_ = script.split(":")

        src_in_sys_path = "sys.path.append('src'); " if self._module.is_in_src() else ""

        cmd = ["python", "-c"]

        cmd += [
            "import sys; "
            "from importlib import import_module; "
            "sys.argv = {!r}; {}"
            "import_module('{}').{}()".format(args, src_in_sys_path, module, callable_)
        ]

        return self.env.execute(*cmd)
