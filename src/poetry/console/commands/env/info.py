from typing import TYPE_CHECKING
from typing import Optional

from cleo.helpers import option

from poetry.console.commands.command import Command


if TYPE_CHECKING:
    from poetry.utils.env import Env


class EnvInfoCommand(Command):

    name = "env info"
    description = "Displays information about the current environment."

    options = [option("path", "p", "Only display the environment's path.")]

    def handle(self) -> Optional[int]:
        from poetry.utils.env import EnvManager

        env = EnvManager(self.poetry).get()

        if self.option("path"):
            if not env.is_venv():
                return 1

            self.line(str(env.path))

            return None

        self._display_complete_info(env)
        return None

    def _display_complete_info(self, env: "Env") -> None:
        env_python_version = ".".join(str(s) for s in env.version_info[:3])
        self.line("")
        self.line("<b>Virtualenv</b>")
        listing = [
            f"<info>Python</info>:         <comment>{env_python_version}</>",
            f"<info>Implementation</info>: <comment>{env.python_implementation}</>",
            f"<info>Path</info>:           <comment>{env.path if env.is_venv() else 'NA'}</>",
            f"<info>Executable</info>:     <comment>{env.python if env.is_venv() else 'NA'}</>",
        ]
        if env.is_venv():
            listing.append(
                f"<info>Valid</info>:          <{'comment' if env.is_sane() else 'error'}>{env.is_sane()}</>"
            )
        self.line("\n".join(listing))

        self.line("")

        system_env = env.parent_env
        python = ".".join(str(v) for v in system_env.version_info[:3])
        self.line("<b>System</b>")
        self.line(
            "\n".join(
                [
                    f"<info>Platform</info>:   <comment>{env.platform}</>",
                    f"<info>OS</info>:         <comment>{env.os}</>",
                    f"<info>Python</info>:     <comment>{python}</>",
                    f"<info>Path</info>:       <comment>{system_env.path}</>",
                    f"<info>Executable</info>: <comment>{system_env.python}</>",
                ]
            )
        )
