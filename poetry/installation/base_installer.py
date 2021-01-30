from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from poetry.core.packages import Package  # noqa


class BaseInstaller:
    def install(self, package):  # type: ("Package") -> None
        raise NotImplementedError

    def update(self, source, target):  # type: ("Package", "Package") -> None
        raise NotImplementedError

    def remove(self, package):  # type: ("Package") -> None
        raise NotImplementedError
