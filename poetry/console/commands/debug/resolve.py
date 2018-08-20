import re

from typing import List

from ..command import Command


class DebugResolveCommand(Command):
    """
    Debugs dependency resolution.

    debug:resolve
        { package?* : packages to resolve. }
        { --E|extras=* : Extras to activate for the dependency. }
        { --python= : Python version(s) to use for resolution. }
        { --tree : Displays the dependency tree. }
    """

    _loggers = ["poetry.repositories.pypi_repository"]

    def handle(self):
        from poetry.packages import Dependency
        from poetry.packages import ProjectPackage
        from poetry.puzzle import Solver
        from poetry.repositories.repository import Repository
        from poetry.semver import parse_constraint

        packages = self.argument("package")

        if not packages:
            package = self.poetry.package
        else:
            package = ProjectPackage(
                self.poetry.package.name, self.poetry.package.version
            )
            requirements = self._format_requirements(packages)

            dependencies = []
            for name, constraint in requirements.items():
                dep = package.add_dependency(name, constraint)
                extras = []
                for extra in self.option("extras"):
                    if " " in extra:
                        extras += [e.strip() for e in extra.split(" ")]
                    else:
                        extras.append(extra)

                for ex in extras:
                    dep.extras.append(ex)

            package.python_versions = (
                self.option("python") or self.poetry.package.python_versions
            )

        solver = Solver(
            package, self.poetry.pool, Repository(), Repository(), self.output
        )

        ops = solver.solve()

        self.line("")
        self.line("Resolution results:")
        self.line("")

        if self.option("tree"):
            show_command = self.get_application().find("show")
            show_command.output = self.output
            show_command.init_styles()

            packages = [op.package for op in ops]
            repo = Repository(packages)

            requires = package.requires + package.dev_requires
            for pkg in repo.packages:
                for require in requires:
                    if pkg.name == require.name:
                        show_command.display_package_tree(pkg, repo)
                        break

            return 0

        for op in ops:
            package = op.package
            self.line(
                "  - <info>{}</info> (<comment>{}</comment>)".format(
                    package.name, package.version
                )
            )
            if package.requirements:
                for req_name, req_value in package.requirements.items():
                    self.line("    - {}: {}".format(req_name, req_value))

    def _determine_requirements(self, requires):  # type: (List[str]) -> List[str]
        from poetry.semver import parse_constraint

        if not requires:
            return []

        requires = self._parse_name_version_pairs(requires)
        result = []
        for requirement in requires:
            if "version" in requirement:
                parse_constraint(requirement["version"])

        return requires

    def _parse_name_version_pairs(self, pairs):  # type: (list) -> list
        result = []

        for i in range(len(pairs)):
            if pairs[i].startswith("git+https://"):
                url = pairs[i].lstrip("git+")
                rev = None
                if "@" in url:
                    url, rev = url.split("@")

                pair = {"name": url.split("/")[-1].rstrip(".git"), "git": url}
                if rev:
                    pair["rev"] = rev

                result.append(pair)

                continue

            pair = re.sub("^([^=: ]+)[=: ](.*)$", "\\1 \\2", pairs[i].strip())
            pair = pair.strip()

            if " " in pair:
                name, version = pair.split(" ", 2)
                result.append({"name": name, "version": version})
            else:
                result.append({"name": pair, "version": "*"})

        return result

    def _format_requirements(self, requirements):  # type: (List[str]) -> dict
        requires = {}
        requirements = self._determine_requirements(requirements)

        for requirement in requirements:
            name = requirement.pop("name")
            requires[name] = requirement

        return requires
