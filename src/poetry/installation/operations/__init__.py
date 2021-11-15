from typing import Union

from .install import Install
from .uninstall import Uninstall
from .update import Update


OperationTypes = Union[Install, Uninstall, Update]
