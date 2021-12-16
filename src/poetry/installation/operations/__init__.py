from typing import Union

from poetry.installation.operations.install import Install
from poetry.installation.operations.uninstall import Uninstall
from poetry.installation.operations.update import Update


OperationTypes = Union[Install, Uninstall, Update]
