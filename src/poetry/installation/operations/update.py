from __future__ import annotations

from typing import TYPE_CHECKING

from poetry.installation.operations.operation import Operation


if TYPE_CHECKING:
    from typing import ClassVar

    from poetry.core.packages.package import Package


class Update(Operation):
    _message_source_operation_color: ClassVar[str] = "c2"

    def __init__(
        self,
        initial: Package,
        target: Package,
        reason: str | None = None,
        priority: int = 0,
    ) -> None:
        self._initial_package = initial
        self._target_package = target

        super().__init__(reason, priority=priority)

    @property
    def initial_package(self) -> Package:
        return self._initial_package

    @property
    def target_package(self) -> Package:
        return self._target_package

    @property
    def package(self) -> Package:
        return self._target_package

    @property
    def job_type(self) -> str:
        return "update"

    @property
    def message_verb(self) -> str:
        initial_version = self.initial_package.version
        target_version = self.target_package.version
        if target_version >= initial_version:
            return "Updated" if self.done else "Updating"
        return "Downgraded" if self.done else "Downgrading"

    def get_message(self) -> str:
        return (
            f"<{self._message_base_tag}>{self.message_verb}"
            f" <{self._message_package_color}>"
            f"{self.initial_package.name}</{self._message_package_color}> "
            f"(<{self._message_source_operation_color}>"
            f"{self.initial_package.full_pretty_version}"
            f"</{self._message_source_operation_color}> -> <{self._message_color}>"
            f"{self.target_package.full_pretty_version}</>)</>"
        )

    def __str__(self) -> str:
        initial_version = self.format_version(self.initial_package)
        target_version = self.format_version(self.target_package)
        return (
            f"{self.message_verb} {self.initial_package.pretty_name} "
            f"({initial_version}) to {self.target_package.pretty_name} "
            f"({target_version})"
        )

    def __repr__(self) -> str:
        initial_version = self.format_version(self.initial_package)
        target_version = self.format_version(self.target_package)
        return (
            f"<Update {self.initial_package.pretty_name} ({initial_version}) "
            f"to {self.target_package.pretty_name} ({target_version})>"
        )
