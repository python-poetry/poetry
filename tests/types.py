from typing import TYPE_CHECKING
from typing import Optional

from tests.compat import Protocol


if TYPE_CHECKING:
    from cleo.testers.command_tester import CommandTester

    from poetry.installation import Installer
    from poetry.installation.executor import Executor
    from poetry.poetry import Poetry
    from poetry.utils.env import Env


class CommandTesterFactory(Protocol):
    def __call__(
        self,
        command: str,
        poetry: Optional["Poetry"] = None,
        installer: Optional["Installer"] = None,
        executor: Optional["Executor"] = None,
        environment: Optional["Env"] = None,
    ) -> "CommandTester":
        ...
