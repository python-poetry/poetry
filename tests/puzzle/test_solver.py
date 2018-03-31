import pytest

from cleo.outputs.null_output import NullOutput
from cleo.styles import OutputStyle

from poetry.packages import Package
from poetry.repositories.installed_repository import InstalledRepository
from poetry.repositories.pool import Pool
from poetry.repositories.repository import Repository
from poetry.puzzle import Solver
from poetry.puzzle.exceptions import SolverProblemError

from tests.helpers import get_dependency
from tests.helpers import get_package


@pytest.fixture()
def io():
    return OutputStyle(NullOutput())


@pytest.fixture()
def package():
    return Package('root', '1.0')


@pytest.fixture()
def installed():
    return InstalledRepository()


@pytest.fixture()
def locked():
    return Repository()


@pytest.fixture()
def repo():
    return Repository()


@pytest.fixture()
def pool(repo):
    return Pool([repo])


@pytest.fixture()
def solver(package, pool, installed, locked, io):
    return Solver(package, pool, installed, locked, io)


def check_solver_result(ops, expected):
    for e in expected:
        if 'skipped' not in e:
            e['skipped'] = False

    result = []
    for op in ops:
        if 'update' == op.job_type:
            result.append({
                'job': 'update',
                'from': op.initial_package,
                'to': op.target_package,
                'skipped': op.skipped
            })
        else:
            job = 'install'
            if op.job_type == 'uninstall':
                job = 'remove'

            result.append({
                'job': job,
                'package': op.package,
                'skipped': op.skipped
            })

    assert result == expected


def test_solver_install_single(solver, repo):
    package_a = get_package('A', '1.0')
    repo.add_package(package_a)

    ops = solver.solve([get_dependency('A')])

    check_solver_result(ops, [
        {'job': 'install', 'package': package_a}
    ])


def test_solver_remove_if_no_longer_locked(solver, locked, installed):
    package_a = get_package('A', '1.0')
    installed.add_package(package_a)
    locked.add_package(package_a)

    ops = solver.solve([])

    check_solver_result(ops, [
        {'job': 'remove', 'package': package_a}
    ])


def test_remove_non_installed(solver, repo, locked):
    package_a = get_package('A', '1.0')
    locked.add_package(package_a)

    repo.add_package(package_a)

    request = []

    ops = solver.solve(request)

    check_solver_result(ops, [
        {'job': 'remove', 'package': package_a, 'skipped': True},
    ])


def test_install_non_existing_package_fail(solver, repo):
    package_a = get_package('A', '1.0')
    repo.add_package(package_a)

    with pytest.raises(SolverProblemError):
        solver.solve([get_dependency('B', '1')])


def test_solver_with_deps(solver, repo):
    package_a = get_package('A', '1.0')
    package_b = get_package('B', '1.0')
    new_package_b = get_package('B', '1.1')

    repo.add_package(package_a)
    repo.add_package(package_b)
    repo.add_package(new_package_b)

    package_a.requires.append(get_dependency('B', '<1.1'))

    ops = solver.solve([get_dependency('a')])

    check_solver_result(ops, [
        {'job': 'install', 'package': package_b},
        {'job': 'install', 'package': package_a},
    ])


def test_install_honours_not_equal(solver, repo):
    package_a = get_package('A', '1.0')
    package_b = get_package('B', '1.0')
    new_package_b11 = get_package('B', '1.1')
    new_package_b12 = get_package('B', '1.2')
    new_package_b13 = get_package('B', '1.3')

    repo.add_package(package_a)
    repo.add_package(package_b)
    repo.add_package(new_package_b11)
    repo.add_package(new_package_b12)
    repo.add_package(new_package_b13)

    package_a.requires.append(get_dependency('B', '<=1.3,!=1.3,!=1.2'))

    ops = solver.solve([get_dependency('a')])

    check_solver_result(ops, [
        {'job': 'install', 'package': new_package_b11},
        {'job': 'install', 'package': package_a},
    ])


def test_install_with_deps_in_order(solver, repo):
    package_a = get_package('A', '1.0')
    package_b = get_package('B', '1.0')
    package_c = get_package('C', '1.0')
    repo.add_package(package_a)
    repo.add_package(package_b)
    repo.add_package(package_c)

    package_b.requires.append(get_dependency('A', '>=1.0'))
    package_b.requires.append(get_dependency('C', '>=1.0'))

    package_c.requires.append(get_dependency('A', '>=1.0'))

    request = [
        get_dependency('A'),
        get_dependency('B'),
        get_dependency('C'),
    ]

    ops = solver.solve(request)

    check_solver_result(ops, [
        {'job': 'install', 'package': package_a},
        {'job': 'install', 'package': package_b},
        {'job': 'install', 'package': package_c},
    ])


def test_install_installed(solver, repo, installed):
    package_a = get_package('A', '1.0')
    installed.add_package(package_a)
    repo.add_package(package_a)

    request = [
        get_dependency('A'),
    ]

    ops = solver.solve(request)

    check_solver_result(ops, [
        {'job': 'install', 'package': package_a, 'skipped': True},
    ])


def test_update_installed(solver, repo, installed):
    installed.add_package(get_package('A', '1.0'))

    package_a = get_package('A', '1.0')
    new_package_a = get_package('A', '1.1')
    repo.add_package(package_a)
    repo.add_package(new_package_a)

    request = [
        get_dependency('A'),
    ]

    ops = solver.solve(request)

    check_solver_result(ops, [
        {'job': 'update', 'from': package_a, 'to': new_package_a}
    ])


def test_update_with_fixed(solver, repo, installed):
    installed.add_package(get_package('A', '1.0'))

    package_a = get_package('A', '1.0')
    new_package_a = get_package('A', '1.1')
    repo.add_package(package_a)
    repo.add_package(new_package_a)

    request = [
        get_dependency('A'),
    ]

    ops = solver.solve(request, fixed=[get_dependency('A', '1.0')])

    check_solver_result(ops, [
        {'job': 'install', 'package': package_a, 'skipped': True},
    ])


def test_solver_sets_categories(solver, repo):
    package_a = get_package('A', '1.0')
    package_b = get_package('B', '1.0')
    package_c = get_package('C', '1.0')
    package_b.requires.append(get_dependency('C', '~1.0'))

    repo.add_package(package_a)
    repo.add_package(package_b)
    repo.add_package(package_c)

    request = [
        get_dependency('A'),
        get_dependency('B', category='dev')
    ]

    ops = solver.solve(request)

    check_solver_result(ops, [
        {'job': 'install', 'package': package_c},
        {'job': 'install', 'package': package_a},
        {'job': 'install', 'package': package_b},
    ])

    assert package_c.category == 'dev'
    assert package_b.category == 'dev'
    assert package_a.category == 'main'


def test_solver_respects_root_package_python_versions(solver, repo, package):
    package.python_versions = '^3.4'
    package_a = get_package('A', '1.0')
    package_b = get_package('B', '1.0')
    package_b.python_versions = '^3.6'
    package_c = get_package('C', '1.0')
    package_c.python_versions = '^3.6'
    package_c11 = get_package('C', '1.1')
    package_c11.python_versions = '~3.3'
    package_b.add_dependency('C', '^1.0')

    repo.add_package(package_a)
    repo.add_package(package_b)
    repo.add_package(package_c)
    repo.add_package(package_c11)

    request = [
        get_dependency('A'),
        get_dependency('B')
    ]

    ops = solver.solve(request)

    check_solver_result(ops, [
        {'job': 'install', 'package': package_c},
        {'job': 'install', 'package': package_a},
        {'job': 'install', 'package': package_b},
    ])


def test_solver_fails_if_mismatch_root_python_versions(solver, repo, package):
    package.python_versions = '^3.4'
    package_a = get_package('A', '1.0')
    package_b = get_package('B', '1.0')
    package_b.python_versions = '^3.6'
    package_c = get_package('C', '1.0')
    package_c.python_versions = '~3.3'
    package_b.add_dependency('C', '~1.0')

    repo.add_package(package_a)
    repo.add_package(package_b)
    repo.add_package(package_c)

    request = [
        get_dependency('A'),
        get_dependency('B')
    ]

    with pytest.raises(SolverProblemError):
        solver.solve(request)


def test_solver_solves_optional_and_compatible_packages(solver, repo, package):
    package.python_versions = '^3.4'
    package_a = get_package('A', '1.0')
    package_b = get_package('B', '1.0')
    package_b.python_versions = '^3.6'
    package_c = get_package('C', '1.0')
    package_c.python_versions = '^3.6'
    package_b.add_dependency('C', '^1.0')

    repo.add_package(package_a)
    repo.add_package(package_b)
    repo.add_package(package_c)

    dependency_a = get_dependency('A')
    dependency_a.python_versions = '~3.5'

    dependency_b = get_dependency('B', optional=True)
    request = [
        dependency_a,
        dependency_b
    ]

    ops = solver.solve(request)

    check_solver_result(ops, [
        {'job': 'install', 'package': package_c},
        {'job': 'install', 'package': package_a},
        {'job': 'install', 'package': package_b},
    ])


def test_solver_solves_while_respecting_root_platforms(solver, repo, package):
    package.platform = 'darwin'
    package_a = get_package('A', '1.0')
    package_b = get_package('B', '1.0')
    package_b.python_versions = '^3.6'
    package_c12 = get_package('C', '1.2')
    package_c12.platform = 'win32'
    package_c10 = get_package('C', '1.0')
    package_c10.platform = 'darwin'
    package_b.add_dependency('C', '^1.0')

    repo.add_package(package_a)
    repo.add_package(package_b)
    repo.add_package(package_c10)
    repo.add_package(package_c12)

    request = [
        get_dependency('A'),
        get_dependency('B')
    ]

    ops = solver.solve(request)

    check_solver_result(ops, [
        {'job': 'install', 'package': package_c10},
        {'job': 'install', 'package': package_a},
        {'job': 'install', 'package': package_b},
    ])


def test_solver_does_not_return_extras_if_not_requested(solver, repo):
    package_a = get_package('A', '1.0')
    package_b = get_package('B', '1.0')
    package_c = get_package('C', '1.0')

    package_b.extras = {
        'foo': [get_dependency('C', '^1.0')]
    }

    repo.add_package(package_a)
    repo.add_package(package_b)
    repo.add_package(package_c)

    dependency_a = get_dependency('A')
    dependency_b = get_dependency('B')
    request = [
        dependency_a,
        dependency_b
    ]

    ops = solver.solve(request)

    check_solver_result(ops, [
        {'job': 'install', 'package': package_a},
        {'job': 'install', 'package': package_b},
    ])


def test_solver_returns_extras_if_requested(solver, repo):
    package_a = get_package('A', '1.0')
    package_b = get_package('B', '1.0')
    package_c = get_package('C', '1.0')

    package_b.extras = {
        'foo': [get_dependency('C', '^1.0')]
    }

    repo.add_package(package_a)
    repo.add_package(package_b)
    repo.add_package(package_c)

    dependency_a = get_dependency('A')
    dependency_b = get_dependency('B')
    dependency_b.extras.append('foo')
    request = [
        dependency_a,
        dependency_b
    ]

    ops = solver.solve(request)

    check_solver_result(ops, [
        {'job': 'install', 'package': package_c},
        {'job': 'install', 'package': package_a},
        {'job': 'install', 'package': package_b},
    ])


def test_solver_returns_prereleases_if_requested(solver, repo):
    package_a = get_package('A', '1.0')
    package_b = get_package('B', '1.0')
    package_c = get_package('C', '1.0')
    package_c_dev = get_package('C', '1.1-beta.1')

    repo.add_package(package_a)
    repo.add_package(package_b)
    repo.add_package(package_c)
    repo.add_package(package_c_dev)

    dependency_a = get_dependency('A')
    dependency_b = get_dependency('B')
    dependency_c = get_dependency('C', allows_prereleases=True)
    request = [
        dependency_a,
        dependency_b,
        dependency_c
    ]

    ops = solver.solve(request)

    check_solver_result(ops, [
        {'job': 'install', 'package': package_a},
        {'job': 'install', 'package': package_b},
        {'job': 'install', 'package': package_c_dev},
    ])


def test_solver_does_not_return_prereleases_if_not_requested(solver, repo):
    package_a = get_package('A', '1.0')
    package_b = get_package('B', '1.0')
    package_c = get_package('C', '1.0')
    package_c_dev = get_package('C', '1.1-beta.1')

    repo.add_package(package_a)
    repo.add_package(package_b)
    repo.add_package(package_c)
    repo.add_package(package_c_dev)

    dependency_a = get_dependency('A')
    dependency_b = get_dependency('B')
    dependency_c = get_dependency('C')
    request = [
        dependency_a,
        dependency_b,
        dependency_c
    ]

    ops = solver.solve(request)

    check_solver_result(ops, [
        {'job': 'install', 'package': package_a},
        {'job': 'install', 'package': package_b},
        {'job': 'install', 'package': package_c},
    ])
