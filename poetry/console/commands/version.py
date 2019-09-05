import ast
import astor
from poetry.utils._compat import Path

from cleo import argument, option

from .command import Command


class TextFile:
    def __init__(self, path, current_version, next_version):
        self.path = Path(path).resolve()
        self.current_version = current_version
        self.next_version = next_version
        self.updated_text = None

    def __repr__(self):
        return "{}({}, {}, {})".format(
            self.__class__.__name__,
            str(self.path),
            self.current_version,
            self.next_version,
        )

    def __str__(self):
        return self.updated_text or ""

    @property
    def changed(self):
        return self.updated_text and (self.updated_text != self.text)

    @property
    def text(self):
        try:
            return self._text
        except AttributeError:
            pass
        self._text = self.path.read_text()
        return self._text

    @property
    def has_current_version(self):
        """Returns True if the current_version string is present
        in the contents of this file, otherwise False. This is a
        first approximation check to see if this file should be
        modified.
        """
        try:
            return self._has_current_version
        except AttributeError:
            pass
        self._has_current_version = self.current_version in self.text
        return self._has_current_version

    def update_version(self):
        """
        """
        new_text = self.text.replace(self.current_version, self.next_version)
        if self.text != new_text:
            self.updated_text = new_text

    def write(self, path=None):
        """Writes the updated version of the file to the specified path.
        If path is not given, the original path is used and the original
        contents are over-written. If the contents have not been updated,

        :param pathlib.Path path: optional
        """
        path = path or self.path
        if self.changed:
            path.write_text(str(self))


class PythonFile(TextFile):
    def __str__(self):
        return astor.to_source(self.tree)

    @property
    def updated_nodes(self):
        """Set of root ast.Nodes that represent modifications to the
        source code for the contents of this file.
        """
        try:
            return self._updated_nodes
        except AttributeError:
            pass
        self._updated_nodes = set()
        return self._updated_nodes

    @property
    def changed(self):
        return bool(self.updated_nodes)

    @property
    def tree(self):
        """Python abstract syntax tree for the contents of this file."""
        try:
            return self._tree
        except AttributeError:
            pass
        self._tree = astor.parse_file(self.path)
        return self._tree

    def _update_version_in_Str_node(self, node):
        """Helper method to update an ast.Str node's "s"
        field from current_version to next_version. Returns
        True if the change succeeds, otherwise False.

        :param ast.Node node:
        :return: bool
        """
        try:
            if node.s == self.current_version:
                node.s = self.next_version
                return True
        except AttributeError:
            pass
        return False

    def update_version(self):
        """Walks the python abstract syntax tree built from the contents of
        this file. It returns a set of ast.Nodes modified and will only walk
        the tree once (even if called multiple times).
        """

        if self.updated_nodes:
            return self.updated_nodes

        try:
            for node in ast.walk(self.tree):
                if isinstance(node, ast.Assign):
                    if self._update_version_in_Str_node(node.value):
                        self.updated_nodes.add(node)

                if isinstance(node, ast.Compare):
                    if self._update_version_in_Str_node(node.left):
                        self.updated_nodes.add(node)

                    for target in node.comparators:
                        if self._update_version_in_Str_node(target):
                            self.updated_nodes.add(node)

        except SyntaxError:
            pass

        return self.updated_nodes


class VersionCommand(Command):

    name = "version"
    description = (
        "Shows the version of the project or bumps it when a valid"
        "bump rule is provided."
    )

    arguments = [
        argument(
            "version",
            "The version number or the rule to update the version.",
            optional=True,
        )
    ]

    options = [
        option(
            "dry-run",
            "N",
            "List files that would be updated without making modifications.",
        )
    ]

    help = """\
The version command shows the current version of the project or bumps
the version of the project and writes the new version back to
<comment>pyproject.toml</> if a valid bump rule is provided. Additionally,
version strings are updated in python source, Markdown, ReStructured
Text, files with a .t*xt suffix and TOML files.

The new version should ideally be a valid semver string or a valid
bump rule: patch, minor, major, prepatch, preminor, premajor,
prerelease.  """

    RESERVED = {
        "major",
        "minor",
        "patch",
        "premajor",
        "preminor",
        "prepatch",
        "prerelease",
    }

    @property
    def current_version(self):
        return self.poetry.package.pretty_version

    @property
    def next_version(self):
        try:
            return self._next_version
        except AttributeError:
            pass
        rule = self.argument("version") or "patch"
        nv = self.increment_version(self.current_version, rule)
        self._next_version = nv.text
        return self._next_version

    @property
    def file_types(self):
        try:
            return self._file_types
        except AttributeError:
            pass
        self._file_types = {
            "*.[tT]*[mM][lL]": TextFile,
            "*.py": PythonFile,
            "*.[mM]*[dD]*": TextFile,
            "*.[rR][Ss][tT]": TextFile,
            "*.[tT]*[xX][tT]": TextFile,
        }
        return self._file_types

    @property
    def target_project_files(self):
        """A dictionary of project files that are identified as containing
        version strings.
        """

        try:
            return self._target_project_files
        except AttributeError:
            pass

        root_path = Path(self.poetry.package.root_dir).resolve()
        versions = (self.current_version, self.next_version)

        self._target_project_files = []

        for pattern, file_class in self.file_types.items():
            for path in root_path.rglob(pattern):
                if not path.is_file():
                    continue
                target = file_class(path, *versions)
                target.update_version()
                if target.changed:
                    self._target_project_files.append(target)

        return self._target_project_files

    def handle(self):
        version = self.argument("version")
        dryrun = self.option("dry-run")

        if not version:
            self.line(
                "Project (<comment>{}</>) version is <info>{}</>".format(
                    self.poetry.package.name, self.current_version
                )
            )
            return

        if dryrun:
            self.line(
                "Would bump version from <comment>{}</> to <info>{}</>".format(
                    self.current_version, self.next_version
                )
            )
            for project_file in self.target_project_files:
                msg = "Would modify <comment>{}</>".format(project_file.path)
                self.line(msg)
            self.line("Completed <info>dry-run</>, no files modified.")
            return

        self.line(
            "Bumping version from <comment>{}</> to <info>{}</>".format(
                self.current_version, self.next_version
            )
        )

        for project_file_to_update in self.target_project_files:
            self.line("Updating {}".format(project_file_to_update.path))
            project_file_to_update.write()

    def increment_version(self, version, rule):
        from poetry.semver import Version

        try:
            version = Version.parse(version)
        except ValueError:
            raise ValueError("The project's version doesn't seem to follow semver")

        if rule in {"major", "premajor"}:
            new = version.next_major
            if rule == "premajor":
                new = new.first_prerelease
        elif rule in {"minor", "preminor"}:
            new = version.next_minor
            if rule == "preminor":
                new = new.first_prerelease
        elif rule in {"patch", "prepatch"}:
            new = version.next_patch
            if rule == "prepatch":
                new = new.first_prerelease
        elif rule == "prerelease":
            if version.is_prerelease():
                pre = version.prerelease
                new_prerelease = int(pre[1]) + 1
                new = Version.parse(
                    "{}.{}.{}-{}".format(
                        version.major,
                        version.minor,
                        version.patch,
                        ".".join([pre[0], str(new_prerelease)]),
                    )
                )
            else:
                new = version.next_patch.first_prerelease
        else:
            new = Version.parse(rule)

        return new
