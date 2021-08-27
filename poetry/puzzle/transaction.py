from typing import TYPE_CHECKING
from typing import List
from typing import Optional
from typing import Tuple


if TYPE_CHECKING:
    from poetry.core.packages.package import Package
    from poetry.installation.operations import OperationTypes


class Transaction:
    def __init__(
        self,
        current_packages: List["Package"],
        result_packages: List[Tuple["Package", int]],
        installed_packages: Optional[List["Package"]] = None,
        root_package: Optional["Package"] = None,
    ) -> None:
        self._current_packages = current_packages
        self._result_packages = result_packages

        if installed_packages is None:
            installed_packages = []

        self._installed_packages = installed_packages
        self._root_package = root_package

    def calculate_operations(
        self, with_uninstalls: bool = True, synchronize: bool = False
    ) -> List["OperationTypes"]:
        from poetry.installation.operations.install import Install
        from poetry.installation.operations.uninstall import Uninstall
        from poetry.installation.operations.update import Update

        operations = []

        for result_package, priority in self._result_packages:
            installed = False

            for installed_package in self._installed_packages:
                if result_package.name == installed_package.name:
                    installed = True

                    if result_package.version != installed_package.version:
                        operations.append(
                            Update(installed_package, result_package, priority=priority)
                        )
                    elif (
                        installed_package.source_type
                        or result_package.source_type != "legacy"
                    ) and not result_package.is_same_package_as(installed_package):
                        operations.append(
                            Update(installed_package, result_package, priority=priority)
                        )
                    else:
                        operations.append(
                            Install(result_package).skip("Already installed")
                        )

                    break

            if not installed:
                operations.append(Install(result_package, priority=priority))

        if with_uninstalls:
            for current_package in self._current_packages:
                found = False
                for result_package, _ in self._result_packages:
                    if current_package.name == result_package.name:
                        found = True

                        break

                if not found:
                    for installed_package in self._installed_packages:
                        if installed_package.name == current_package.name:
                            operations.append(Uninstall(current_package))

            if synchronize:
                current_package_names = {
                    current_package.name for current_package in self._current_packages
                }
                # We preserve pip/setuptools/wheel when not managed by poetry, this is done
                # to avoid externally managed virtual environments causing unnecessary
                # removals.
                preserved_package_names = {
                    "pip",
                    "setuptools",
                    "wheel",
                } - current_package_names

                for installed_package in self._installed_packages:
                    if (
                        self._root_package
                        and installed_package.name == self._root_package.name
                    ):
                        continue

                    if installed_package.name in preserved_package_names:
                        continue

                    if installed_package.name not in current_package_names:
                        operations.append(Uninstall(installed_package))

        return sorted(
            operations,
            key=lambda o: (
                -o.priority,
                o.package.name,
                o.package.version,
            ),
        )
