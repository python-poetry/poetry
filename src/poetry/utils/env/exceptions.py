from __future__ import annotations

from typing import TYPE_CHECKING

from poetry.utils._compat import decode


if TYPE_CHECKING:
    from subprocess import CalledProcessError


class EnvError(Exception):
    pass


class IncorrectEnvError(EnvError):
    def __init__(self, env_name: str) -> None:
        message = f"Env {env_name} doesn't belong to this project."
        super().__init__(message)


class EnvCommandError(EnvError):
    def __init__(self, e: CalledProcessError, input: str | None = None) -> None:
        self.e = e

        message_parts = [
            f"Command {e.cmd} errored with the following return code {e.returncode}"
        ]
        if e.output:
            message_parts.append(f"Output:\n{decode(e.output)}")
        if e.stderr:
            message_parts.append(f"Error output:\n{decode(e.stderr)}")
        if input:
            message_parts.append(f"Input:\n{input}")
        super().__init__("\n\n".join(message_parts))


class PythonVersionNotFound(EnvError):
    def __init__(self, expected: str) -> None:
        super().__init__(f"Could not find the python executable {expected}")


class NoCompatiblePythonVersionFound(EnvError):
    def __init__(self, expected: str, given: str | None = None) -> None:
        if given:
            message = (
                f"The specified Python version ({given}) "
                f"is not supported by the project ({expected}).\n"
                "Please choose a compatible version "
                "or loosen the python constraint specified "
                "in the pyproject.toml file."
            )
        else:
            message = (
                "Poetry was unable to find a compatible version. "
                "If you have one, you can explicitly use it "
                'via the "env use" command.'
            )

        super().__init__(message)


class InvalidCurrentPythonVersionError(EnvError):
    def __init__(self, expected: str, given: str) -> None:
        message = (
            f"Current Python version ({given}) "
            f"is not allowed by the project ({expected}).\n"
            'Please change python executable via the "env use" command.'
        )

        super().__init__(message)
