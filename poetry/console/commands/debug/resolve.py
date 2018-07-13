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
            requirements = self._determine_requirements(packages)
            requirements = self._format_requirements(requirements)

            # validate requirements format
            for constraint in requirements.values():
                parse_constraint(constraint)

            dependencies = []
            for name, constraint in requirements.items():
                dep = Dependency(name, constraint)
                extras = []
                for extra in self.option("extras"):
                    if " " in extra:
                        extras += [e.strip() for e in extra.split(" ")]
                    else:
                        extras.append(extra)

                for ex in extras:
                    dep.extras.append(ex)

                dependencies.append(dep)

            package = ProjectPackage(
                self.poetry.package.name, self.poetry.package.version
            )

            package.python_versions = (
                self.option("python") or self.poetry.package.python_versions
            )
            for dep in dependencies:
                package.requires.append(dep)

        solver = Solver(
            package, self.poetry.pool, Repository(), Repository(), self.output
        )

        ops = solver.solve()

        self.line("")
        self.line("Resolution results:")
        self.line("")

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
        if not requires:
            return []

        requires = self._parse_name_version_pairs(requires)
        result = []
        for requirement in requires:
            if "version" not in requirement:
                requirement["version"] = "*"

            result.append("{} {}".format(requirement["name"], requirement["version"]))

        return result

    def _parse_name_version_pairs(self, pairs):  # type: (list) -> list
        result = []

        for i in range(len(pairs)):
            pair = re.sub("^([^=: ]+)[=: ](.*)$", "\\1 \\2", pairs[i].strip())
            pair = pair.strip()

            if " " in pair:
                name, version = pair.split(" ", 2)
                result.append({"name": name, "version": version})
            else:
                result.append({"name": pair})

        return result

    def _format_requirements(self, requirements):  # type: (List[str]) -> dict
        requires = {}
        requirements = self._parse_name_version_pairs(requirements)
        for requirement in requirements:
            requires[requirement["name"]] = requirement["version"]

        return requires
