# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import toml

from poetry.poetry import Poetry
from poetry.utils._compat import Path


fixtures_dir = Path(__file__).parent / 'fixtures'


def test_poetry():
    poetry = Poetry.create(str(fixtures_dir / 'sample_project'))

    package = poetry.package

    assert package.name == 'my-package'
    assert package.version == '1.2.3'
    assert package.description == 'Some description.'
    assert package.authors == ['Sébastien Eustace <sebastien@eustace.io>']
    assert package.license.id == 'MIT'
    assert str(package.readme.relative_to(fixtures_dir)) == "sample_project/README.rst"
    assert package.homepage == 'https://poetry.eustace.io'
    assert package.repository_url == 'https://github.com/sdispater/poetry'
    assert package.keywords == ["packaging", "dependency", "poetry"]

    assert package.python_versions == '~2.7 || ^3.6'
    assert str(package.python_constraint) == '>= 2.7.0.0, < 2.8.0.0 || >= 3.6.0.0, < 4.0.0.0'

    dependencies = {}
    for dep in package.requires:
        dependencies[dep.name] = dep

    cleo = dependencies['cleo']
    assert cleo.pretty_constraint == '^0.6'
    assert not cleo.is_optional()

    pendulum = dependencies['pendulum']
    assert pendulum.pretty_constraint == 'branch 2.0'
    assert pendulum.is_vcs()
    assert pendulum.vcs == 'git'
    assert pendulum.branch == '2.0'
    assert pendulum.source == 'https://github.com/sdispater/pendulum.git'
    assert pendulum.allows_prereleases()

    requests = dependencies['requests']
    assert requests.pretty_constraint == '^2.18'
    assert not requests.is_vcs()
    assert not requests.allows_prereleases()
    assert requests.is_optional()
    assert requests.extras == ['security']

    pathlib2 = dependencies['pathlib2']
    assert pathlib2.pretty_constraint == '^2.2'
    assert pathlib2.python_versions == '~2.7'
    assert not pathlib2.is_optional()

    demo = dependencies['demo']
    assert demo.is_file()
    assert not demo.is_vcs()
    assert demo.name == 'demo'
    assert demo.pretty_constraint == '0.1.0'

    assert 'db' in package.extras

    classifiers = package.classifiers

    assert classifiers == [
        "Topic :: Software Development :: Build Tools",
        "Topic :: Software Development :: Libraries :: Python Modules"
    ]

    assert package.all_classifiers == [
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Topic :: Software Development :: Build Tools",
        "Topic :: Software Development :: Libraries :: Python Modules"
    ]


def test_check():
    complete = fixtures_dir / 'complete.toml'
    with complete.open() as f:
        content = toml.loads(f.read())['tool']['poetry']

    assert Poetry.check(content)
