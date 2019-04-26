# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from poetry.io import NullIO
from poetry.masonry.builders import EditableBuilder
from poetry.poetry import Poetry
from poetry.utils._compat import Path
from poetry.utils.env import MockEnv

fixtures_dir = Path(__file__).parent / "fixtures"


def test_build_pure_python_package(tmp_dir):
    tmp_dir = Path(tmp_dir)
    env = MockEnv(path=tmp_dir)
    env.site_packages.mkdir(parents=True)
    module_path = fixtures_dir / "complete"

    builder = EditableBuilder(Poetry.create(module_path), env, NullIO())
    builder._path = tmp_dir
    builder.build()

    egg_info = tmp_dir / "my_package.egg-info"

    assert egg_info.exists()

    entry_points = """\
[console_scripts]
extra-script=my_package.extra:main[time]
my-2nd-script=my_package:main2
my-script=my_package:main

"""
    pkg_info = """\
Metadata-Version: 2.1
Name: my-package
Version: 1.2.3
Summary: Some description.
Home-page: https://poetry.eustace.io/
License: MIT
Keywords: packaging,dependency,poetry
Author: Sébastien Eustace
Author-email: sebastien@eustace.io
Requires-Python: >=3.6,<4.0
Classifier: License :: OSI Approved :: MIT License
Classifier: Programming Language :: Python :: 3
Classifier: Programming Language :: Python :: 3.6
Classifier: Programming Language :: Python :: 3.7
Classifier: Topic :: Software Development :: Build Tools
Classifier: Topic :: Software Development :: Libraries :: Python Modules
Provides-Extra: time
Requires-Dist: cachy[msgpack] (>=0.2.0,<0.3.0)
Requires-Dist: cleo (>=0.6,<0.7)
Requires-Dist: pendulum (>=1.4,<2.0); extra == "time"
Project-URL: Documentation, https://poetry.eustace.io/docs
Project-URL: Repository, https://github.com/sdispater/poetry
Description-Content-Type: text/x-rst

My Package
==========

"""

    requires = """\
cachy[msgpack] (>=0.2.0,<0.3.0)
cleo (>=0.6,<0.7)
pendulum (>=1.4,<2.0)
"""

    with egg_info.joinpath("entry_points.txt").open(encoding="utf-8") as f:
        assert entry_points == f.read()

    with egg_info.joinpath("PKG-INFO").open(encoding="utf-8") as f:
        assert pkg_info == f.read()

    with egg_info.joinpath("requires.txt").open(encoding="utf-8") as f:
        assert requires == f.read()

    egg_link = env.site_packages / "my-package.egg-link"

    with egg_link.open(encoding="utf-8") as f:
        assert str(module_path) + "\n." == f.read()

    easy_install = env.site_packages / "easy-install.pth"

    with easy_install.open(encoding="utf-8") as f:
        assert str(module_path) + "\n" in f.readlines()


def test_build_should_delegate_to_pip_for_non_pure_python_packages(tmp_dir, mocker):
    move = mocker.patch("shutil.move")
    tmp_dir = Path(tmp_dir)
    env = MockEnv(path=tmp_dir, pip_version="18.1", execute=False)
    env.site_packages.mkdir(parents=True)
    module_path = fixtures_dir / "extended"

    builder = EditableBuilder(Poetry.create(module_path), env, NullIO())
    builder.build()

    expected = [["python", "-m", "pip", "install", "-e", str(module_path)]]
    assert expected == env.executed

    assert 0 == move.call_count


def test_build_should_temporarily_remove_the_pyproject_file(tmp_dir, mocker):
    move = mocker.patch("shutil.move")
    tmp_dir = Path(tmp_dir)
    env = MockEnv(path=tmp_dir, pip_version="19.1", execute=False)
    env.site_packages.mkdir(parents=True)
    module_path = fixtures_dir / "extended"

    builder = EditableBuilder(Poetry.create(module_path), env, NullIO())
    builder.build()

    expected = [["python", "-m", "pip", "install", "-e", str(module_path)]]
    assert expected == env.executed

    assert 2 == move.call_count

    expected_calls = [
        mocker.call(
            str(module_path / "pyproject.toml"), str(module_path / "pyproject.tmp")
        ),
        mocker.call(
            str(module_path / "pyproject.tmp"), str(module_path / "pyproject.toml")
        ),
    ]

    assert expected_calls == move.call_args_list
