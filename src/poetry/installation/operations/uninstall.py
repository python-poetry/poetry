from __future__ import annotations

from typing import TYPE_CHECKING

from poetry.installation.operations.operation import Operation


if TYPE_CHECKING:
    from poetry.core.packages.package import Package


class Uninstall(Operation):
    def __init__(
        self,
        package: Package,
        reason: str | None = None,
        priority: float = float("inf"),
    ) -> None:
        super().__init__(reason, priority=priority)

        self._package = package

    @property
    def package(self) -> Package:
        return self._package

    @property
    def job_type(self) -> str:
        return "uninstall"

    @property
    def message_verb(self) -> str:
        return "Removed" if self.done else "Removing"

    def get_message(self) -> str:
        return (
            f"<{self._message_base_tag}>{self.message_verb}"
            f" <{self._message_package_color}>{self.package.name}"
            f"</{self._message_package_color}>"
            f" (<{self._message_color}>{self.package.full_pretty_version}</>)</>"
        )

    def __str__(self) -> str:
        return (
            f"{self.message_verb} "
            f"{self.package.pretty_name} ({self.format_version(self._package)})"
        )

    def __repr__(self) -> str:
        return (
            "<Uninstall"
            f" {self.package.pretty_name} ({self.format_version(self.package)})>"
        )
