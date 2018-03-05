from poetry.semver import statisfies
from poetry.version.version_selector import VersionSelector

from .command import Command


class ShowCommand(Command):
    """
    Shows information about packages.

    show
        { package? : Package to inspect. }
        { --t|tree : List the dependencies as a tree. }
        { --l|latest : Show the latest version. }
        { --o|outdated : Show the latest version
                         but only for packages that are outdated. }
    """

    help = """The show command displays detailed information about a package, or
lists all packages available."""

    colors = [
        'green',
        'yellow',
        'cyan',
        'magenta',
        'blue',
    ]

    def handle(self):
        package = self.argument('package')

        if self.option('tree'):
            self.init_styles()

        if self.option('outdated'):
            self.input.set_option('latest', True)

        installed_repo = self.poetry.locker.locked_repository(True)

        # Show tree view if requested
        if self.option('tree') and not package:
            requires = self.poetry.package.requires + self.poetry.package.dev_requires
            packages = installed_repo.packages
            for package in packages:
                for require in requires:
                    if package.name == require.name:
                        self.display_package_tree(package, installed_repo)
                        break

            return 0

        table = self.table(style='compact')
        table.get_style().set_vertical_border_char('')
        locked_packages = installed_repo.packages

        if package:
            pkg = None
            for locked in locked_packages:
                if package.lower() == locked.name:
                    pkg = locked
                    break

            if not pkg:
                raise ValueError(f'Package {package} not found')

            if self.option('tree'):
                self.display_package_tree(pkg, installed_repo)

                return 0

            rows = [
                ['<info>name</>', f' : <fg=cyan>{pkg.pretty_name}</>'],
                ['<info>version</>', f' : <comment>{pkg.pretty_version}</>'],
                ['<info>description</>', f' : {pkg.description}'],
            ]

            table.add_rows(rows)
            table.render()

            if pkg.requires:
                self.line('')
                self.line('<info>dependencies</info>')
                for dependency in pkg.requires:
                    self.line(f' - {dependency.pretty_name} '
                              f'<comment>{dependency.pretty_constraint}</>')

            return 0

        show_latest = self.option('latest')
        terminal = self.get_application().terminal
        width = terminal.width
        name_length = version_length = latest_length = 0
        latest_packages = {}
        # Computing widths
        for locked in locked_packages:
            name_length = max(name_length, len(locked.pretty_name))
            version_length = max(version_length, len(locked.full_pretty_version))
            if show_latest:
                latest = self.find_latest_package(locked)
                if not latest:
                    latest = locked

                latest_packages[locked.pretty_name] = latest
                latest_length = max(latest_length, len(latest.full_pretty_version))

        write_version = name_length + version_length + 3 <= width
        write_latest = name_length + version_length + latest_length + 3 <= width
        write_description = name_length + version_length + latest_length + 24 <= width

        for locked in locked_packages:
            line = f'<fg=cyan>{locked.pretty_name:{name_length}}</>'
            if write_version:
                line += f' {locked.full_pretty_version:{version_length}}'
            if show_latest and write_latest:
                latest = latest_packages[locked.pretty_name]

                update_status = self.get_update_status(latest, locked)
                color = 'green'
                if update_status == 'semver-safe-update':
                    color = 'red'
                elif update_status == 'update-possible':
                    color = 'yellow'

                line += f' <fg={color}>{latest.version:{latest_length}}</>'
                if self.option('outdated') and update_status == 'up-to-date':
                    continue

            if write_description:
                description = locked.description
                remaining = width - name_length - version_length - 4
                if show_latest:
                    remaining -= latest_length

                if len(locked.description) > remaining:
                    description = description[:remaining-3] + '...'

                line += ' ' + description

            self.line(line)

    def display_package_tree(self, package, installed_repo):
        self.write(f'<info>{package.pretty_name}</info>')
        self.line(f' {package.pretty_version} {package.description}')

        dependencies = package.requires
        dependencies = sorted(dependencies, key=lambda x: x.name)
        tree_bar = '├'
        j = 0
        total = len(dependencies)
        for dependency in dependencies:
            j += 1
            if j == total:
                tree_bar = '└'

            level = 1
            color = self.colors[level]
            info = f'{tree_bar}── <{color}>{dependency.name}</{color}> ' \
                   f'{dependency.pretty_constraint}'
            self._write_tree_line(info)

            tree_bar = tree_bar.replace('└', ' ')
            packages_in_tree = [package.name, dependency.name]

            self._display_tree(
                dependency, installed_repo, packages_in_tree,
                tree_bar, level + 1
            )

    def _display_tree(self,
                      dependency, installed_repo, packages_in_tree,
                      previous_tree_bar='├', level=1):
        previous_tree_bar = previous_tree_bar.replace('├', '│')

        dependencies = []
        for package in installed_repo.packages:
            if package.name == dependency.name:
                dependencies = package.requires

                break

        dependencies = sorted(dependencies, key=lambda x: x.name)
        tree_bar = previous_tree_bar + '   ├'
        i = 0
        total = len(dependencies)
        for dependency in dependencies:
            i += 1
            current_tree = packages_in_tree
            if i == total:
                tree_bar = previous_tree_bar + '   └'

            color_ident = level % len(self.colors)
            color = self.colors[color_ident]

            circular_warn = ''
            if dependency.name in current_tree:
                circular_warn = '(circular dependency aborted here)'

            info = f'{tree_bar}── <{color}>{dependency.name}</{color}> ' \
                   f'{dependency.pretty_constraint} {circular_warn}'
            self._write_tree_line(info)

            tree_bar = tree_bar.replace('└', ' ')

            if dependency.name not in current_tree:
                current_tree.append(dependency.name)

                self._display_tree(
                    dependency, installed_repo, current_tree,
                    tree_bar, level + 1
                )

    def _write_tree_line(self, line):
        if not self.output.is_decorated():
            line = line.replace('└', '`-')
            line = line.replace('├', '|-')
            line = line.replace('──', '-')
            line = line.replace('│', '|')

        self.line(line)

    def init_styles(self):
        for color in self.colors:
            self.set_style(color, color)

    def find_latest_package(self, package):
        # find the latest version allowed in this pool
        name = package.name
        selector = VersionSelector(self.poetry.pool)

        return selector.find_best_candidate(name, f'>={package.version}')

    def get_update_status(self, latest, package):
        if latest.full_pretty_version == package.full_pretty_version:
            return 'up-to-date'

        constraint = package.version

        if latest.version and statisfies(latest.version, constraint):
            # It needs an immediate semver-compliant upgrade
            return 'semver-safe-update'

        # it needs an upgrade but has potential BC breaks so is not urgent
        return 'update-possible'
