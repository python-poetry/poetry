from cleo.testers import CommandTester

from tests.helpers import get_dependency
from tests.helpers import get_package


def test_add_no_constraint(app, repo, installer):
    command = app.find('add')
    tester = CommandTester(command)

    repo.add_package(get_package('cachy', '0.1.0'))
    repo.add_package(get_package('cachy', '0.2.0'))


    tester.execute([
        ('command', command.get_name()),
        ('name', ['cachy'])
    ])

    expected = """\
Using version ^0.2.0 for cachy

Updating dependencies
Resolving dependencies


Package operations: 1 install, 0 updates, 0 removals

Writing lock file

  - Installing cachy (0.2.0)
"""

    assert tester.get_display() == expected

    assert len(installer.installs) == 1


def test_add_constraint(app, repo, installer):
    command = app.find('add')
    tester = CommandTester(command)

    repo.add_package(get_package('cachy', '0.1.0'))
    repo.add_package(get_package('cachy', '0.2.0'))


    tester.execute([
        ('command', command.get_name()),
        ('name', ['cachy=0.1.0'])
    ])

    expected = """\

Updating dependencies
Resolving dependencies


Package operations: 1 install, 0 updates, 0 removals

Writing lock file

  - Installing cachy (0.1.0)
"""

    assert tester.get_display() == expected

    assert len(installer.installs) == 1


def test_add_constraint_dependencies(app, repo, installer):
    command = app.find('add')
    tester = CommandTester(command)

    cachy2 = get_package('cachy', '0.2.0')
    msgpack_dep = get_dependency('msgpack-python', '>=0.5 <0.6')
    cachy2.requires = [
        msgpack_dep,
    ]

    repo.add_package(get_package('cachy', '0.1.0'))
    repo.add_package(cachy2)
    repo.add_package(get_package('msgpack-python', '0.5.3'))

    tester.execute([
        ('command', command.get_name()),
        ('name', ['cachy=0.2.0'])
    ])

    expected = """\

Updating dependencies
Resolving dependencies


Package operations: 2 installs, 0 updates, 0 removals

Writing lock file

  - Installing msgpack-python (0.5.3)
  - Installing cachy (0.2.0)
"""

    assert tester.get_display() == expected

    assert len(installer.installs) == 2

