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
        option("why", "w", "Show why the package is required."),
    ]

    help = """The show command displays detailed information about a package, or
lists all packages available."""

    colors = ["cyan", "yellow", "green", "magenta", "blue"]

    def handle(self):
        from clikit.utils.terminal import Terminal
        from poetry.repositories.installed_repository import InstalledRepository
        from poetry.core.semver import Version

        package = self.argument("package")

        if self.option("tree"):
            self.init_styles(self.io)

        if self.option("outdated"):
            self._args.set_option("latest", True)

        include_dev = not self.option("no-dev")
        locked_repo = self.poetry.locker.locked_repository(include_dev)

        # Show tree view if requested
        if self.option("tree") and not package:
            requires = self.poetry.package.requires + self.poetry.package.dev_requires
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

        if package:
            pkg = None
            for locked in locked_packages:
                if package.lower() == locked.name:
                    pkg = locked
                    break

            if not pkg:
                raise ValueError("Package {} not found".format(package))

            if self.option("why"):
                self.io.write_line(
                    "Determining why <c1>{pkg_name}</c1> is installed.".format(
                        pkg_name=pkg.name
                    )
                )
                self.io.write_line("")

            if self.option("tree"):
                if self.option("why"):
                    self.display_package_why(self.io, pkg, locked_repo)
                else:
                    self.display_package_tree(self.io, pkg, locked_repo)

                return 0

            if not self.option("why"):
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
            else:
                locked_packages = self._detect_why([pkg], locked_repo)

                # No need to display the package itself
                locked_packages = locked_packages[1:]

                # test whether this is a direct dependency
                if package in [e.name for e in self.poetry.package.requires]:
                    self.io.write_line(
                        "The package is a dependency of the main project (via the <b>dependencies</b> section)."
                    )
                for locked_package in locked_packages:
                    self.io.write_line(
                        "The package is required by <c1>{}</c1> (<b>{}</b>).".format(
                            locked_package.name, locked_package.version,
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
        skipped = []

        python = Version.parse(".".join([str(i) for i in self.env.version_info[:3]]))

        # Computing widths
        for locked in locked_packages:
            python_constraint = locked.python_constraint
            if not python_constraint.allows(python) or not self.env.is_valid_for_marker(
                locked.marker
            ):
                skipped.append(locked)

                if not show_all:
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
                        version_length, len(locked.full_pretty_version)
                    )
                    latest_length = max(latest_length, len(latest.full_pretty_version))
            else:
                name_length = max(name_length, current_length)
                version_length = max(version_length, len(locked.full_pretty_version))

        write_version = name_length + version_length + 3 <= width
        write_latest = name_length + version_length + latest_length + 3 <= width
        write_description = name_length + version_length + latest_length + 24 <= width

        for locked in locked_packages:
            color = "cyan"
            name = locked.pretty_name
            install_marker = ""
            if locked in skipped:
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
                    locked.full_pretty_version, version_length
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
                        color, latest.full_pretty_version, latest_length
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

    def display_package_why(self, io, package, installed_repo):
        package_name = package.name
        super_packages = self._detect_why([package], installed_repo)
        for package in super_packages:
            self.display_package_tree(
                io,
                package,
                installed_repo,
                only_packages=super_packages,
                highlighted_packages=[package_name],
            )

    def _detect_why(self, unprocessed, installed_repo):
        result = []
        while unprocessed:
            child = unprocessed.pop(0)
            for parent in installed_repo.packages:
                for dependency in parent.requires:
                    if dependency.accepts(child):
                        if parent not in result:
                            unprocessed.append(parent)
                for dependency in parent.requires_extras:
                    if dependency.accepts(child):
                        if parent not in result:
                            unprocessed.append(parent)

            if child not in result:
                result.append(child)
        return result

    def display_package_tree(
        self, io, package, installed_repo, only_packages=None, highlighted_packages=[]
    ):
        io.write("<c1>{}</c1>".format(package.pretty_name))
        description = ""
        if package.description:
            description = " " + package.description

        io.write_line(" <b>{}</b>{}".format(package.pretty_version, description))

        dependencies = package.requires
        dependencies = sorted(dependencies, key=lambda x: x.name)
        dependencies = (
            [e for e in dependencies if any(e.accepts(p) for p in only_packages)]
            if only_packages
            else dependencies
        )
        tree_bar = "├"
        j = 0
        total = len(dependencies)
        for dependency in dependencies:
            j += 1
            if j == total:
                tree_bar = "└"

            level = 1
            color = self.colors[level]
            high_start = "<high>" if dependency.name in highlighted_packages else ""
            high_end = "</high>" if high_start else ""
            high_color = "_high" if high_start else ""
            info = "{tree_bar}── <{color}{high_color}>{name}</{color}{high_color}> {high_start}{constraint}{high_end}".format(
                tree_bar=tree_bar,
                color=color,
                high_color=high_color,
                high_start=high_start,
                high_end=high_end,
                name=dependency.name,
                constraint=dependency.pretty_constraint,
            )
            self._write_tree_line(io, info)

            tree_bar = tree_bar.replace("└", " ")
            packages_in_tree = [package.name, dependency.name]

            self._display_tree(
                io,
                dependency,
                installed_repo,
                packages_in_tree,
                tree_bar,
                level + 1,
                only_packages,
                highlighted_packages,
            )

    def _display_tree(
        self,
        io,
        dependency,
        installed_repo,
        packages_in_tree,
        previous_tree_bar="├",
        level=1,
        only_packages=None,
        highlighted_packages=[],
    ):
        previous_tree_bar = previous_tree_bar.replace("├", "│")

        dependencies = []
        for package in installed_repo.packages:
            if package.name == dependency.name:
                dependencies = package.requires

                break

        dependencies = sorted(dependencies, key=lambda x: x.name)
        dependencies = (
            [e for e in dependencies if any(e.accepts(p) for p in only_packages)]
            if only_packages
            else dependencies
        )
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

            high_start = "<high>" if dependency.name in highlighted_packages else ""
            high_end = "</high>" if high_start else ""
            high_color = "_high" if high_start else ""
            info = "{tree_bar}── <{color}{high_color}>{name}</{color}{high_color}> {high_start}{constraint}{high_end} {warn}".format(
                tree_bar=tree_bar,
                color=color,
                high_color=high_color,
                high_start=high_start,
                high_end=high_end,
                name=dependency.name,
                constraint=dependency.pretty_constraint,
                warn=circular_warn,
            )
            self._write_tree_line(io, info)

            tree_bar = tree_bar.replace("└", " ")

            if dependency.name not in current_tree:
                current_tree.append(dependency.name)

                self._display_tree(
                    io,
                    dependency,
                    installed_repo,
                    current_tree,
                    tree_bar,
                    level + 1,
                    only_packages,
                    highlighted_packages,
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
            style_high = Style(color + "_high").fg(color)
            style_high.bold()
            io.output.formatter.add_style(style)
            io.error_output.formatter.add_style(style)
            io.output.formatter.add_style(style_high)
            io.error_output.formatter.add_style(style_high)

        high_style = Style("high").bold()
        io.output.formatter.add_style(high_style)
        io.error_output.formatter.add_style(high_style)

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
