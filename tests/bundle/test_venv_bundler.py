import shutil
import sys

from pathlib import Path

import pytest

from cleo.formatters.style import Style
from cleo.io.buffered_io import BufferedIO

from poetry.bundle.venv_bundler import VenvBundler
from poetry.core.packages.package import Package
from poetry.factory import Factory
from poetry.repositories.pool import Pool
from poetry.repositories.repository import Repository


@pytest.fixture()
def io():
    io = BufferedIO()

    io.output.formatter.set_style("success", Style("green", options=["dark"]))
    io.output.formatter.set_style("warning", Style("yellow", options=["dark"]))

    return io


@pytest.fixture()
def poetry(config):
    poetry = Factory().create_poetry(
        Path(__file__).parent / "fixtures" / "simple_project"
    )
    poetry.set_config(config)

    pool = Pool()
    repository = Repository()
    repository.add_package(Package("foo", "1.0.0"))
    pool.add_repository(repository)
    poetry.set_pool(pool)

    return poetry


def test_bundler_should_build_a_new_venv_with_existing_python(
    io, tmp_dir, poetry, mocker
):
    shutil.rmtree(tmp_dir)
    mocker.patch("poetry.installation.executor.Executor._execute_operation")

    bundler = VenvBundler()

    assert bundler.bundle(poetry, io, Path(tmp_dir))

    expected = """\
  • Bundling simple-project (1.2.3) into {path}
  • Bundling simple-project (1.2.3) into {path}: Creating a virtual environment using Python {python_version}
  • Bundling simple-project (1.2.3) into {path}: Installing dependencies
  • Bundling simple-project (1.2.3) into {path}: Installing simple-project (1.2.3)
  • Bundled simple-project (1.2.3) into {path}
""".format(
        path=tmp_dir, python_version=".".join(str(v) for v in sys.version_info[:3])
    )
    assert expected == io.fetch_output()


def test_bundler_should_build_a_new_venv_with_given_executable(
    io, tmp_dir, poetry, mocker
):
    shutil.rmtree(tmp_dir)
    mocker.patch("poetry.installation.executor.Executor._execute_operation")

    bundler = VenvBundler()

    assert bundler.bundle(poetry, io, Path(tmp_dir), executable=sys.executable)

    expected = """\
  • Bundling simple-project (1.2.3) into {path}
  • Bundling simple-project (1.2.3) into {path}: Creating a virtual environment using Python {python_version}
  • Bundling simple-project (1.2.3) into {path}: Installing dependencies
  • Bundling simple-project (1.2.3) into {path}: Installing simple-project (1.2.3)
  • Bundled simple-project (1.2.3) into {path}
""".format(
        path=tmp_dir, python_version=".".join(str(v) for v in sys.version_info[:3])
    )
    assert expected == io.fetch_output()


def test_bundler_should_build_a_new_venv_if_existing_venv_is_incompatible(
    io, tmp_dir, poetry, mocker
):
    mocker.patch("poetry.installation.executor.Executor._execute_operation")

    bundler = VenvBundler()

    assert bundler.bundle(poetry, io, Path(tmp_dir))

    expected = """\
  • Bundling simple-project (1.2.3) into {path}
  • Bundling simple-project (1.2.3) into {path}: Removing existing virtual environment
  • Bundling simple-project (1.2.3) into {path}: Creating a virtual environment using Python {python_version}
  • Bundling simple-project (1.2.3) into {path}: Installing dependencies
  • Bundling simple-project (1.2.3) into {path}: Installing simple-project (1.2.3)
  • Bundled simple-project (1.2.3) into {path}
""".format(
        path=tmp_dir, python_version=".".join(str(v) for v in sys.version_info[:3])
    )
    assert expected == io.fetch_output()


def test_bundler_should_use_an_existing_venv_if_compatible(
    io, tmp_venv, poetry, mocker
):
    mocker.patch("poetry.installation.executor.Executor._execute_operation")

    bundler = VenvBundler()

    assert bundler.bundle(poetry, io, tmp_venv.path)

    expected = """\
  • Bundling simple-project (1.2.3) into {path}
  • Bundling simple-project (1.2.3) into {path}: Using existing virtual environment
  • Bundling simple-project (1.2.3) into {path}: Installing dependencies
  • Bundling simple-project (1.2.3) into {path}: Installing simple-project (1.2.3)
  • Bundled simple-project (1.2.3) into {path}
""".format(
        path=str(tmp_venv.path),
        python_version=".".join(str(v) for v in sys.version_info[:3]),
    )
    assert expected == io.fetch_output()


def test_bundler_should_remove_an_existing_venv_if_forced(io, tmp_venv, poetry, mocker):
    mocker.patch("poetry.installation.executor.Executor._execute_operation")

    bundler = VenvBundler()

    assert bundler.bundle(poetry, io, tmp_venv.path, remove=True)

    expected = """\
  • Bundling simple-project (1.2.3) into {path}
  • Bundling simple-project (1.2.3) into {path}: Removing existing virtual environment
  • Bundling simple-project (1.2.3) into {path}: Creating a virtual environment using Python {python_version}
  • Bundling simple-project (1.2.3) into {path}: Installing dependencies
  • Bundling simple-project (1.2.3) into {path}: Installing simple-project (1.2.3)
  • Bundled simple-project (1.2.3) into {path}
""".format(
        path=str(tmp_venv.path),
        python_version=".".join(str(v) for v in sys.version_info[:3]),
    )
    assert expected == io.fetch_output()


def test_bundler_should_fail_when_installation_fails(io, tmp_dir, poetry, mocker):
    mocker.patch(
        "poetry.installation.executor.Executor._do_execute_operation",
        side_effect=Exception(),
    )

    bundler = VenvBundler()

    assert not bundler.bundle(poetry, io, Path(tmp_dir))

    expected = """\
  • Bundling simple-project (1.2.3) into {path}
  • Bundling simple-project (1.2.3) into {path}: Removing existing virtual environment
  • Bundling simple-project (1.2.3) into {path}: Creating a virtual environment using Python {python_version}
  • Bundling simple-project (1.2.3) into {path}: Installing dependencies
  • Bundling simple-project (1.2.3) into {path}: Failed at step Installing dependencies
""".format(
        path=tmp_dir,
        python_version=".".join(str(v) for v in sys.version_info[:3]),
    )
    assert expected == io.fetch_output()


def test_bundler_should_display_a_warning_for_projects_with_no_module(
    io, tmp_venv, mocker, config
):
    poetry = Factory().create_poetry(
        Path(__file__).parent / "fixtures" / "simple_project_with_no_module"
    )
    poetry.set_config(config)

    pool = Pool()
    repository = Repository()
    repository.add_package(Package("foo", "1.0.0"))
    pool.add_repository(repository)
    poetry.set_pool(pool)

    mocker.patch("poetry.installation.executor.Executor._execute_operation")

    bundler = VenvBundler()

    assert bundler.bundle(poetry, io, tmp_venv.path, remove=True)

    expected = """\
  • Bundling simple-project (1.2.3) into {path}
  • Bundling simple-project (1.2.3) into {path}: Removing existing virtual environment
  • Bundling simple-project (1.2.3) into {path}: Creating a virtual environment using Python {python_version}
  • Bundling simple-project (1.2.3) into {path}: Installing dependencies
  • Bundling simple-project (1.2.3) into {path}: Installing simple-project (1.2.3)
  • Bundled simple-project (1.2.3) into {path}
  • The root package was not installed because no matching module or package was found.
""".format(
        path=str(tmp_venv.path),
        python_version=".".join(str(v) for v in sys.version_info[:3]),
    )
    assert expected == io.fetch_output()
