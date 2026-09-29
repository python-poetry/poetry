from __future__ import annotations

from typing import TYPE_CHECKING
from typing import ClassVar

from cleo.helpers import argument

from poetry.console.commands.env_command import EnvCommand
from poetry.utils._compat import WINDOWS


if TYPE_CHECKING:
    from cleo.io.inputs.argument import Argument
    from poetry.core.masonry.utils.module import Module


class RunCommand(EnvCommand):
    name = "run"
    description = "Runs a command in the appropriate environment."

    arguments: ClassVar[list[Argument]] = [
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
        path = poetry.file.path.parent
        module = Module(package.name, path.as_posix(), package.packages)

        return module

    def run_script(self, script: str | dict[str, str], args: list[str]) -> int:
        """Runs an entry point script defined in the section ``[tool.poetry.scripts]``.

        When a script exists in the venv bin folder, i.e. after ``poetry install``,
        then ``sys.argv[0]`` must be set to the full path of the executable, so
        ``poetry run foo`` and ``poetry shell``, ``foo`` have the same ``sys.argv[0]``
        that points to the full path.

        Otherwise (when an entry point script does not exist), ``sys.argv[0]`` is the
        script name only, i.e. ``poetry run foo`` has ``sys.argv == ['foo']``.
        """
        if isinstance(script, dict) and script.get("type") == "file":
            return self.run_file_script(script, args)

        for script_dir in self.env.script_dirs:
            script_path = script_dir / args[0]
            if WINDOWS:
                script_path = script_path.with_suffix(".cmd")
            if script_path.exists():
                args = [str(script_path), *args[1:]]
                break
        else:
            # If we reach this point, the script is not installed
            self._warning_not_installed_script(args[0])

        if isinstance(script, dict):
            # A script can also be specified as a table, either as a legacy
            # ``{callable = "module:callable"}`` entry or as a
            # ``{reference = "module:callable", type = "console"}`` entry.
            script = script.get("callable") or script["reference"]

        module, callable_ = script.split(":")

        src_in_sys_path = "sys.path.append('src'); " if self._module.is_in_src() else ""

        cmd = ["python", "-c"]

        cmd += [
            (
                "import sys; "
                "from importlib import import_module; "
                f"sys.argv = {args!r}; {src_in_sys_path}"
                f"sys.exit(import_module('{module}').{callable_}())"
            )
        ]

        return self.env.execute(*cmd)

    def run_file_script(self, script: dict[str, str], args: list[str]) -> int:
        """Runs a file script defined in the section ``[tool.poetry.scripts]``.

        Unlike entry points, file scripts (``type = "file"``) are copied to the
        environment's script directory as-is when the project is installed, so they
        are executed directly instead of being resolved to a ``module:callable`` pair.
        """
        script_name = args[0]

        for script_dir in self.env.script_dirs:
            candidates = [script_dir / script_name]
            if WINDOWS:
                candidates.append(script_dir / f"{script_name}.cmd")
            for script_path in candidates:
                if script_path.exists():
                    return self.env.execute(str(script_path), *args[1:])

        # If we reach this point, the script is not installed, so we fall back to
        # the script file referenced in the project.
        reference = script["reference"]
        script_path = self.poetry.file.path.parent / reference

        if not script_path.exists():
            self.line_error(f"<error>Command not found: <c1>{script_name}</c1></error>")
            return 1

        self._warning_not_installed_script(script_name)
        return self.env.execute(str(script_path), *args[1:])

    def _warning_not_installed_script(self, script: str) -> None:
        message = f"""\
Warning: '{script}' is an entry point defined in pyproject.toml, but it's not \
installed as a script. You may get improper `sys.argv[0]`.

The support to run uninstalled scripts will be removed in a future release.

Run `poetry install` to resolve and get rid of this message.
"""
        self.line_error(message, style="warning")
