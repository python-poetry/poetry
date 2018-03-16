import toml

from pathlib import Path

from poetry import Poetry


fixtures_dir = Path(__file__).parent / 'fixtures'


def test_poetry():
    poetry = Poetry.create(str(fixtures_dir / 'sample_project'))

    package = poetry.package

    assert package.name == 'my-package'
    assert package.version == '1.2.3'
    assert package.description == 'Some description.'
    assert package.authors == ['Sébastien Eustace <sebastien@eustace.io>']
    assert package.license == 'MIT'
    assert package.readme == """My Package
==========
"""
    assert package.homepage == 'https://poetry.eustace.io'
    assert package.repository_url == 'https://github.com/sdispater/poetry'
    assert package.keywords == ["packaging", "dependency", "poetry"]

    assert package.python_versions == '~2.7 || ^3.6'
    assert str(package.python_constraint) == '>= 2.7.0.0, < 2.8.0.0 || >= 3.6.0.0, < 4.0.0.0'

    dependencies = package.requires
    cleo = dependencies[0]
    assert cleo.pretty_constraint == '^0.6'
    assert not cleo.is_optional()

    pendulum = dependencies[1]
    assert pendulum.pretty_constraint == 'branch 2.0'
    assert pendulum.is_vcs()
    assert pendulum.vcs == 'git'
    assert pendulum.branch == '2.0'
    assert pendulum.source == 'https://github.com/sdispater/pendulum.git'
    assert pendulum.allows_prereleases()

    requests = dependencies[2]
    assert requests.pretty_constraint == '^2.18'
    assert not requests.is_vcs()
    assert not requests.allows_prereleases()
    assert requests.is_optional()
    assert requests.extras == ['security']

    pathlib2 = dependencies[3]
    assert pathlib2.pretty_constraint == '^2.2'
    assert pathlib2.python_versions == '~2.7'
    assert not pathlib2.is_optional()

    assert 'db' in package.extras


def test_check():
    complete = fixtures_dir / 'complete.toml'
    content = toml.loads(complete.read_text())['tool']['poetry']

    assert Poetry.check(content)
