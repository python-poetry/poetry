import pytest

from cleo.testers import CommandTester

from poetry.console import Application
from poetry.factory import Factory
from poetry.poetry import Poetry
from poetry.utils._compat import Path  # noqa


@pytest.fixture
def command(app, poetry):  # type: (Application, Poetry) -> CommandTester
    command = app.find("new")
    command._pool = poetry.pool
    return CommandTester(command)


def verify_project_directory(path, package_name, package_path, include_from=None):
    package_path = Path(package_path)
    assert path.is_dir()

    pyproject = path / "pyproject.toml"
    assert pyproject.is_file()

    init_file = path / package_path / "__init__.py"
    assert init_file.is_file()

    tests_init_file = path / "tests" / "__init__.py"
    assert tests_init_file.is_file()

    poetry = Factory().create_poetry(cwd=path)
    assert poetry.package.name == package_name

    if include_from:
        package_include = {
            "include": package_path.relative_to(include_from).parts[0],
            "from": include_from,
        }
    else:
        package_include = {"include": package_path.parts[0]}

    packages = poetry.local_config.get("packages")

    if not packages:
        assert poetry.local_config.get("name") == package_include.get("include")
    else:
        assert len(packages) == 1
        assert packages[0] == package_include


@pytest.mark.parametrize(
    "options,directory,package_name,package_path,include_from",
    [
        ([], "package", "package", "package", None),
        (["--src"], "package", "package", "src/package", "src"),
        (
            ["--name namespace.package"],
            "namespace-package",
            "namespace-package",
            "namespace/package",
            None,
        ),
        (
            ["--src", "--name namespace.package"],
            "namespace-package",
            "namespace-package",
            "src/namespace/package",
            "src",
        ),
        (
            ["--name namespace.package_a"],
            "namespace-package_a",
            "namespace-package-a",
            "namespace/package_a",
            None,
        ),
        (
            ["--src", "--name namespace.package_a"],
            "namespace-package_a",
            "namespace-package-a",
            "src/namespace/package_a",
            "src",
        ),
        (
            ["--name namespace_package"],
            "namespace-package",
            "namespace-package",
            "namespace_package",
            None,
        ),
        (
            ["--name namespace_package", "--src"],
            "namespace-package",
            "namespace-package",
            "src/namespace_package",
            "src",
        ),
        (
            ["--name namespace.package"],
            "package",
            "namespace-package",
            "namespace/package",
            None,
        ),
        (
            ["--name namespace.package", "--src"],
            "package",
            "namespace-package",
            "src/namespace/package",
            "src",
        ),
        (
            ["--name namespace.package"],
            "package",
            "namespace-package",
            "namespace/package",
            None,
        ),
        (
            ["--name namespace.package", "--src"],
            "package",
            "namespace-package",
            "src/namespace/package",
            "src",
        ),
        ([], "namespace_package", "namespace-package", "namespace_package", None),
        (
            ["--src", "--name namespace_package"],
            "namespace_package",
            "namespace-package",
            "src/namespace_package",
            "src",
        ),
    ],
)
def test_command_new(
    options, directory, package_name, package_path, include_from, command, tmp_dir
):
    path = Path(tmp_dir) / directory
    options.append(path.as_posix())
    command.execute(" ".join(options))
    verify_project_directory(path, package_name, package_path, include_from)
