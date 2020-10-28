# -*- coding: utf-8 -*-
from cleo import argument
from cleo import option

from .env_command import EnvCommand


class ShowCommand(EnvCommand):

    name = "show"
    description = "Shows information about packages."

    arguments = [argument("package", "The package to inspect", optional=True)]
    options = [
        option("no-dev", None, "Do not list the development dependencies."),
        option("tree", "t", "List the dependencies as a tree."),
        option("latest", "l", "Show the latest version."),
        option(
            "outdated",
            "o",
            "Show the latest version but only for packages that are outdated.",
        ),
        option(
            "all",
            "a",
            "Show all packages (even those not compatible with current system).",
        ),
    ]

    help = """The show command displays detailed information about a package, or
lists all packages available."""

    colors = ["cyan", "yellow", "green", "magenta", "blue"]

    def handle(self):
        from clikit.utils.terminal import Terminal

        from poetry.io.null_io import NullIO
        from poetry.puzzle.solver import Solver
        from poetry.repositories.installed_repository import InstalledRepository
        from poetry.repositories.pool import Pool
        from poetry.repositories.repository import Repository
        from poetry.utils.helpers import get_package_version_display_string

        package = self.argument("package")

        if self.option("tree"):
            self.init_styles(self.io)

        if self.option("outdated"):
            self._args.set_option("latest", True)

        include_dev = not self.option("no-dev")
        locked_repo = self.poetry.locker.locked_repository(True)

        # Show tree view if requested
        if self.option("tree") and not package:
            requires = self.poetry.package.requires
            if include_dev:
                requires += self.poetry.package.dev_requires
            packages = locked_repo.packages
            for package in packages:
                for require in requires:
                    if package.name == require.name:
                        self.display_package_tree(self._io, package, locked_repo)
                        break

            return 0

        table = self.table(style="compact")
        # table.style.line_vc_char = ""
        locked_packages = locked_repo.packages
        pool = Pool(ignore_repository_names=True)
        pool.add_repository(locked_repo)
        solver = Solver(
            self.poetry.package,
            pool=pool,
            installed=Repository(),
            locked=locked_repo,
            io=NullIO(),
        )
        solver.provider.load_deferred(False)
        with solver.use_environment(self.env):
            ops = solver.solve()

        required_locked_packages = set([op.package for op in ops if not op.skipped])

        if self.option("no-dev"):
            required_locked_packages = [
                p for p in locked_packages if p.category == "main"
            ]

        if package:
            pkg = None
            for locked in locked_packages:
                if package.lower() == locked.name:
                    pkg = locked
                    break

            if not pkg:
                raise ValueError("Package {} not found".format(package))

            if self.option("tree"):
                self.display_package_tree(self.io, pkg, locked_repo)

                return 0

            rows = [
                ["<info>name</>", " : <c1>{}</>".format(pkg.pretty_name)],
                ["<info>version</>", " : <b>{}</b>".format(pkg.pretty_version)],
                ["<info>description</>", " : {}".format(pkg.description)],
            ]

            table.add_rows(rows)
            table.render(self.io)

            if pkg.requires:
                self.line("")
                self.line("<info>dependencies</info>")
                for dependency in pkg.requires:
                    self.line(
                        " - <c1>{}</c1> <b>{}</b>".format(
                            dependency.pretty_name, dependency.pretty_constraint
                        )
                    )

            return 0

        show_latest = self.option("latest")
        show_all = self.option("all")
        terminal = Terminal()
        width = terminal.width
        name_length = version_length = latest_length = 0
        latest_packages = {}
        latest_statuses = {}
        installed_repo = InstalledRepository.load(self.env)

        # Computing widths
        for locked in locked_packages:
            if locked not in required_locked_packages and not show_all:
                continue

            current_length = len(locked.pretty_name)
            if not self._io.output.supports_ansi():
                installed_status = self.get_installed_status(locked, installed_repo)

                if installed_status == "not-installed":
                    current_length += 4

            if show_latest:
                latest = self.find_latest_package(locked, include_dev)
                if not latest:
                    latest = locked

                latest_packages[locked.pretty_name] = latest
                update_status = latest_statuses[
                    locked.pretty_name
                ] = self.get_update_status(latest, locked)

                if not self.option("outdated") or update_status != "up-to-date":
                    name_length = max(name_length, current_length)
                    version_length = max(
                        version_length,
                        len(
                            get_package_version_display_string(
                                locked, root=self.poetry.file.parent
                            )
                        ),
                    )
                    latest_length = max(
                        latest_length,
                        len(
                            get_package_version_display_string(
                                latest, root=self.poetry.file.parent
                            )
                        ),
                    )
            else:
                name_length = max(name_length, current_length)
                version_length = max(
                    version_length,
                    len(
                        get_package_version_display_string(
                            locked, root=self.poetry.file.parent
                        )
                    ),
                )

        write_version = name_length + version_length + 3 <= width
        write_latest = name_length + version_length + latest_length + 3 <= width
        write_description = name_length + version_length + latest_length + 24 <= width

        for locked in locked_packages:
            color = "cyan"
            name = locked.pretty_name
            install_marker = ""
            if locked not in required_locked_packages:
                if not show_all:
                    continue

                color = "black;options=bold"
            else:
                installed_status = self.get_installed_status(locked, installed_repo)
                if installed_status == "not-installed":
                    color = "red"

                    if not self._io.output.supports_ansi():
                        # Non installed in non decorated mode
                        install_marker = " (!)"

            if (
                show_latest
                and self.option("outdated")
                and latest_statuses[locked.pretty_name] == "up-to-date"
            ):
                continue

            line = "<fg={}>{:{}}{}</>".format(
                color, name, name_length - len(install_marker), install_marker
            )
            if write_version:
                line += " <b>{:{}}</b>".format(
                    get_package_version_display_string(
                        locked, root=self.poetry.file.parent
                    ),
                    version_length,
                )
            if show_latest:
                latest = latest_packages[locked.pretty_name]
                update_status = latest_statuses[locked.pretty_name]

                if write_latest:
                    color = "green"
                    if update_status == "semver-safe-update":
                        color = "red"
                    elif update_status == "update-possible":
                        color = "yellow"

                    line += " <fg={}>{:{}}</>".format(
                        color,
                        get_package_version_display_string(
                            latest, root=self.poetry.file.parent
                        ),
                        latest_length,
                    )

            if write_description:
                description = locked.description
                remaining = width - name_length - version_length - 4
                if show_latest:
                    remaining -= latest_length

                if len(locked.description) > remaining:
                    description = description[: remaining - 3] + "..."

                line += " " + description

            self.line(line)

    def display_package_tree(self, io, package, installed_repo):
        io.write("<c1>{}</c1>".format(package.pretty_name))
        description = ""
        if package.description:
            description = " " + package.description

        io.write_line(" <b>{}</b>{}".format(package.pretty_version, description))

        dependencies = package.requires
        dependencies = sorted(dependencies, key=lambda x: x.name)
        tree_bar = "├"
        j = 0
        total = len(dependencies)
        for dependency in dependencies:
            j += 1
            if j == total:
                tree_bar = "└"

            level = 1
            color = self.colors[level]
            info = "{tree_bar}── <{color}>{name}</{color}> {constraint}".format(
                tree_bar=tree_bar,
                color=color,
                name=dependency.name,
                constraint=dependency.pretty_constraint,
            )
            self._write_tree_line(io, info)

            tree_bar = tree_bar.replace("└", " ")
            packages_in_tree = [package.name, dependency.name]

            self._display_tree(
                io, dependency, installed_repo, packages_in_tree, tree_bar, level + 1
            )

    def _display_tree(
        self,
        io,
        dependency,
        installed_repo,
        packages_in_tree,
        previous_tree_bar="├",
        level=1,
    ):
        previous_tree_bar = previous_tree_bar.replace("├", "│")

        dependencies = []
        for package in installed_repo.packages:
            if package.name == dependency.name:
                dependencies = package.requires

                break

        dependencies = sorted(dependencies, key=lambda x: x.name)
        tree_bar = previous_tree_bar + "   ├"
        i = 0
        total = len(dependencies)
        for dependency in dependencies:
            i += 1
            current_tree = packages_in_tree
            if i == total:
                tree_bar = previous_tree_bar + "   └"

            color_ident = level % len(self.colors)
            color = self.colors[color_ident]

            circular_warn = ""
            if dependency.name in current_tree:
                circular_warn = "(circular dependency aborted here)"

            info = "{tree_bar}── <{color}>{name}</{color}> {constraint} {warn}".format(
                tree_bar=tree_bar,
                color=color,
                name=dependency.name,
                constraint=dependency.pretty_constraint,
                warn=circular_warn,
            )
            self._write_tree_line(io, info)

            tree_bar = tree_bar.replace("└", " ")

            if dependency.name not in current_tree:
                current_tree.append(dependency.name)

                self._display_tree(
                    io, dependency, installed_repo, current_tree, tree_bar, level + 1
                )

    def _write_tree_line(self, io, line):
        if not io.output.supports_ansi():
            line = line.replace("└", "`-")
            line = line.replace("├", "|-")
            line = line.replace("──", "-")
            line = line.replace("│", "|")

        io.write_line(line)

    def init_styles(self, io):
        from clikit.api.formatter import Style

        for color in self.colors:
            style = Style(color).fg(color)
            io.output.formatter.add_style(style)
            io.error_output.formatter.add_style(style)

    def find_latest_package(self, package, include_dev):
        from clikit.io import NullIO

        from poetry.puzzle.provider import Provider
        from poetry.version.version_selector import VersionSelector

        # find the latest version allowed in this pool
        if package.source_type in ("git", "file", "directory"):
            requires = self.poetry.package.requires
            if include_dev:
                requires = requires + self.poetry.package.dev_requires

            for dep in requires:
                if dep.name == package.name:
                    provider = Provider(self.poetry.package, self.poetry.pool, NullIO())

                    if dep.is_vcs():
                        return provider.search_for_vcs(dep)[0]
                    if dep.is_file():
                        return provider.search_for_file(dep)[0]
                    if dep.is_directory():
                        return provider.search_for_directory(dep)[0]

        name = package.name
        selector = VersionSelector(self.poetry.pool)

        return selector.find_best_candidate(name, ">={}".format(package.pretty_version))

    def get_update_status(self, latest, package):
        from poetry.core.semver import parse_constraint

        if latest.full_pretty_version == package.full_pretty_version:
            return "up-to-date"

        constraint = parse_constraint("^" + package.pretty_version)

        if latest.version and constraint.allows(latest.version):
            # It needs an immediate semver-compliant upgrade
            return "semver-safe-update"

        # it needs an upgrade but has potential BC breaks so is not urgent
        return "update-possible"

    def get_installed_status(self, locked, installed_repo):
        for package in installed_repo.packages:
            if locked.name == package.name:
                return "installed"

        return "not-installed"
