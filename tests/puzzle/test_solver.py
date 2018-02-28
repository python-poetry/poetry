import pytest

from cleo.outputs.null_output import NullOutput
from cleo.styles import OutputStyle

from poetry.repositories.installed_repository import InstalledRepository
from poetry.repositories.repository import Repository
from poetry.puzzle import Solver
from poetry.puzzle.exceptions import SolverProblemError

from tests.helpers import get_dependency
from tests.helpers import get_package


@pytest.fixture()
def io():
    return OutputStyle(NullOutput())


@pytest.fixture()
def installed():
    return InstalledRepository()


@pytest.fixture()
def solver(installed, io):
    return Solver(installed, io)


@pytest.fixture()
def repo():
    return Repository()


def check_solver_result(ops, expected):
    result = []
    for op in ops:
        if 'update' == op.job_type:
            result.append({
                'job': 'update',
                'from': op.initial_package,
                'to': op.target_package
            })
        else:
            job = 'install'
            if op.job_type == 'uninstall':
                job = 'remove'

            result.append({
                'job': job,
                'package': op.package
            })

    assert result == expected


def test_solver_install_single(solver, repo):
    package_a = get_package('A', '1.0')
    repo.add_package(package_a)

    ops = solver.solve([get_dependency('A')], repo)

    check_solver_result(ops, [
        {'job': 'install', 'package': package_a}
    ])


def test_solver_remove_if_not_installed(solver, repo, installed):
    package_a = get_package('A', '1.0')
    installed.add_package(package_a)

    ops = solver.solve([], repo)

    check_solver_result(ops, [
        {'job': 'remove', 'package': package_a}
    ])


def test_install_non_existing_package_fail(solver, repo):
    package_a = get_package('A', '1.0')
    repo.add_package(package_a)

    with pytest.raises(SolverProblemError) as e:
        solver.solve([get_dependency('B', '1')], repo)


def test_solver_with_deps(solver, repo):
    package_a = get_package('A', '1.0')
    package_b = get_package('B', '1.0')
    new_package_b = get_package('B', '1.1')

    repo.add_package(package_a)
    repo.add_package(package_b)
    repo.add_package(new_package_b)

    package_a.requires.append(get_dependency('B', '<1.1'))

    ops = solver.solve([get_dependency('a')], repo)

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

    ops = solver.solve([get_dependency('a')], repo)

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

    ops = solver.solve(request, repo)

    check_solver_result(ops, [
        {'job': 'install', 'package': package_c},
        {'job': 'install', 'package': package_b},
        {'job': 'install', 'package': package_a},
    ])


def test_install_installed(solver, repo, installed):
    installed.add_package(get_package('A', '1.0'))
    repo.add_package(get_package('A', '1.0'))

    request = [
        get_dependency('A'),
    ]

    ops = solver.solve(request, repo)

    check_solver_result(ops, [])


def test_update_installed(solver, repo, installed):
    installed.add_package(get_package('A', '1.0'))

    package_a = get_package('A', '1.0')
    new_package_a = get_package('A', '1.1')
    repo.add_package(package_a)
    repo.add_package(new_package_a)

    request = [
        get_dependency('A'),
    ]

    ops = solver.solve(request, repo)

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

    ops = solver.solve(request, repo, fixed=[get_dependency('A', '1.0')])

    check_solver_result(ops, [])


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

    ops = solver.solve(request, repo)

    check_solver_result(ops, [
        {'job': 'install', 'package': package_c},
        {'job': 'install', 'package': package_b},
        {'job': 'install', 'package': package_a},
    ])

    assert package_c.category == 'dev'
    assert package_b.category == 'dev'
    assert package_a.category == 'main'
