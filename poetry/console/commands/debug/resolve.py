from cleo import argument
from cleo import option

from ..init import InitCommand


class DebugResolveCommand(InitCommand):

    name = "resolve"
    description = "Debugs dependency resolution."

    arguments = [
        argument("package", "The packages to resolve.", optional=True, multiple=True)
    ]
    options = [
        option(
            "extras",
            "E",
            "Extras to activate for the dependency.",
            flag=False,
            multiple=True,
        ),
        option("python", None, "Python version(s) to use for resolution.", flag=False),
        option("tree", None, "Display the dependency tree."),
        option("install", None, "Show what would be installed for the current system."),
    ]

    loggers = ["poetry.repositories.pypi_repository"]

    def handle(self):
        from poetry.io.null_io import NullIO
        from poetry.packages import ProjectPackage
        from poetry.puzzle import Solver
        from poetry.repositories.pool import Pool
        from poetry.repositories.repository import Repository
        from poetry.utils.env import EnvManager

        packages = self.argument("package")

        if not packages:
            package = self.poetry.package
        else:
            # Using current pool for determine_requirements()
            self._pool = self.poetry.pool

            package = ProjectPackage(
                self.poetry.package.name, self.poetry.package.version
            )

            # Silencing output
            is_quiet = self.io.output.is_quiet()
            if not is_quiet:
                self.io.output.set_quiet(True)

            requirements = self._determine_requirements(packages)

            if not is_quiet:
                self.io.output.set_quiet(False)

            for constraint in requirements:
                name = constraint.pop("name")
                dep = package.add_dependency(name, constraint)
                extras = []
                for extra in self.option("extras"):
                    if " " in extra:
                        extras += [e.strip() for e in extra.split(" ")]
                    else:
                        extras.append(extra)

                for ex in extras:
                    dep.extras.append(ex)

        package.python_versions = self.option("python") or (
            self.poetry.package.python_versions
        )

        pool = self.poetry.pool

        solver = Solver(package, pool, Repository(), Repository(), self._io)

        ops = solver.solve()

        self.line("")
        self.line("Resolution results:")
        self.line("")

        if self.option("tree"):
            show_command = self.application.find("show")
            show_command.init_styles(self.io)

            packages = [op.package for op in ops]
            repo = Repository(packages)

            requires = package.requires + package.dev_requires
            for pkg in repo.packages:
                for require in requires:
                    if pkg.name == require.name:
                        show_command.display_package_tree(self.io, pkg, repo)
                        break

            return 0

        table = self.table([], style="borderless")
        rows = []

        if self.option("install"):
            env = EnvManager(self.poetry).get()
            current_python_version = ".".join(str(v) for v in env.version_info)
            pool = Pool()
            locked_repository = Repository()
            for op in ops:
                locked_repository.add_package(op.package)

            pool.add_repository(locked_repository)

            with package.with_python_versions(current_python_version):
                solver = Solver(package, pool, Repository(), Repository(), NullIO())
                ops = solver.solve()

        for op in ops:
            pkg = op.package
            row = [
                "<c1>{}</c1>".format(pkg.name),
                "<b>{}</b>".format(pkg.version),
                "",
            ]

            if not pkg.marker.is_any():
                row[2] = str(pkg.marker)

            rows.append(row)

        table.set_rows(rows)
        table.render(self.io)
