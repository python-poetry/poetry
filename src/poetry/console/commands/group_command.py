from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

from cleo.helpers import option
from packaging.utils import NormalizedName
from packaging.utils import canonicalize_name

from poetry.console.commands.command import Command
from poetry.console.exceptions import GroupNotFoundError


if TYPE_CHECKING:
    from cleo.io.inputs.option import Option
    from poetry.core.packages.project_package import ProjectPackage


class GroupCommand(Command):
    @staticmethod
    def _group_dependency_options() -> list[Option]:
        return [
            option(
                "without",
                None,
                "The dependency groups to ignore.",
                flag=False,
                multiple=True,
            ),
            option(
                "with",
                None,
                "The optional dependency groups to include.",
                flag=False,
                multiple=True,
            ),
            option(
                "only",
                None,
                "The only dependency groups to include.",
                flag=False,
                multiple=True,
            ),
        ]

    @property
    def non_optional_groups(self) -> set[str]:
        # TODO: this should move into poetry-core
        return {
            group.name
            for group in self.poetry.package._dependency_groups.values()
            if not group.is_optional()
        }

    @property
    def default_group(self) -> str | None:
        """
        The default group to use when no group is specified. This is useful
        for command that have the `--group` option, eg: add, remove.

        Can be overridden to adapt behavior.
        """
        return None

    @property
    def default_groups(self) -> set[str]:
        """
        The groups that are considered by the command by default.

        Can be overridden to adapt behavior.
        """
        return self.non_optional_groups

    @property
    def activated_groups(self) -> set[NormalizedName]:
        groups = {}

        for key in {"with", "without", "only"}:
            groups[key] = {
                group.strip()
                for groups in self.option(key, "")
                for group in groups.split(",")
            }

        if self.option("all-groups"):
            groups["with"] = self.poetry.package.dependency_group_names(
                include_optional=True
            )

        self._validate_group_options(groups)

        if groups["only"] and (groups["with"] or groups["without"]):
            self.line_error(
                "<warning>The `<fg=yellow;options=bold>--with</>` and "
                "`<fg=yellow;options=bold>--without</>` options are ignored when used"
                " along with the `<fg=yellow;options=bold>--only</>` option."
                "</warning>"
            )

        # Normalize after validating so that original names are printed
        # in case of an error.
        norm_groups = {
            key: {canonicalize_name(group) for group in key_groups}
            for key, key_groups in groups.items()
        }
        norm_default_groups = {canonicalize_name(name) for name in self.default_groups}

        return norm_groups["only"] or norm_default_groups.union(
            norm_groups["with"]
        ).difference(norm_groups["without"])

    def project_with_activated_groups_only(self) -> ProjectPackage:
        return self.poetry.package.with_dependency_groups(
            list(self.activated_groups), only=True
        )

    def _validate_group_options(self, group_options: dict[str, set[str]]) -> None:
        """
        Raises an error if it detects that a group is not part of pyproject.toml
        """
        invalid_options = defaultdict(set)
        for opt, groups in group_options.items():
            for group in groups:
                if not self.poetry.package.has_dependency_group(group):
                    invalid_options[group].add(opt)
        if invalid_options:
            message_parts = []
            for group in sorted(invalid_options):
                opts = ", ".join(
                    f"<fg=yellow;options=bold>--{opt}</>"
                    for opt in sorted(invalid_options[group])
                )
                message_parts.append(f"{group} (via {opts})")
            raise GroupNotFoundError(f"Group(s) not found: {', '.join(message_parts)}")
