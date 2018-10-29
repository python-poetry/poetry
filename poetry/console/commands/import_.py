# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from poetry.layouts import layout
from .command import Command
from ...utils._compat import Path
from ...utils.toml_file import TomlFile


class ImportCommand(Command):
    """
    Create poetry project from existing files (<comment>setup.py</>, <comment>Pipfile</> ...)

    import
        {--from= : Config file to import}
        {--package-name= : Name of the package}
        {--package-version= : Version of the package}

    """

    def __init__(self):
        super(ImportCommand, self).__init__()

    def handle(self):
        from_file = self.get_from_file()
        if not from_file:
            return 1

        if from_file != "Pipfile":
            self.line("<error>Unsupported config file: {}".format(from_file))
            self.line("Feel free to open a bug report!")
            return 1

        return self.import_pipfile(from_file)

    def import_pipfile(self, pipfile):
        # When using Pipfile, there's no way to get name and version
        # so ask user to set them on the command line
        name = self.get_required_name()
        if not name:
            return 1

        version = self.get_required_version()
        if not version:
            return 1

        pyproject = Path("pyproject.toml")

        self.info("Importing from Pipfile")
        pipfile_data = TomlFile(pipfile).read()

        importer = PipfileImporter(name, version, pipfile_data)
        layout = importer.get_layout()

        contents = layout.generate_poetry_content()
        pyproject.write_text(contents)

        self.info("Generated: {}".format(pyproject))

    def get_from_file(self):
        from_file = self.option("from")
        if not from_file:
            self.line("<error>--from option is required</>")
            return

        file_path = Path(from_file)
        if not file_path.exists():
            self.line("<error>file: '{}' does not exist</>".format(from_file))
            return

        return from_file

    def get_required_name(self):
        name = self.option("package-name")
        if not name:
            self.line("<error>--package-name option is required</>")
        return name

    def get_required_version(self):
        version = self.option("package-version")
        if not version:
            self.line("<error>--package-version option is required</>")
        return version


class PipfileImporter:
    def __init__(self, name, version, pipfile_data):
        self.name = name
        self.version = version
        self.pipfile_data = pipfile_data

    def get_layout(self):
        dependencies = self.get_deps()
        dev_dependencies = self.get_dev_deps()
        python = self.get_required_python() or "*"
        return layout("standard")(
            self.name,
            self.version,
            python=python,
            dependencies=dependencies,
            dev_dependencies=dev_dependencies,
        )

    def get_required_python(self):
        pipfile_requires = self.pipfile_data.get("requires")
        if pipfile_requires:
            return pipfile_requires.get("python_version")

    def get_deps(self):
        return self._get_deps("packages")

    def get_dev_deps(self):
        return self._get_deps("dev-packages")

    def _get_deps(self, pipfile_name):
        deps = {}
        packages = self.pipfile_data.get(pipfile_name) or {}
        for name, version in packages.items():
            deps[name] = self.convert_version(version)

        return deps

    def convert_version(self, pipfile_version):
        if not isinstance(pipfile_version, dict):
            return pipfile_version

        if "git" not in pipfile_version:
            return pipfile_version

        return self.convert_git_version(pipfile_version)

    @classmethod
    def convert_git_version(cls, pipfile_version):
        poetry_version = {}
        poetry_version["git"] = pipfile_version["git"]

        poetry_version.update(pipfile_version)

        pipfile_ref = poetry_version.pop("ref", None)
        if pipfile_ref:
            poetry_version["rev"] = pipfile_ref

        poetry_version.pop("editable", None)

        return poetry_version
