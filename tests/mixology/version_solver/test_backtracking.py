from ..helpers import add_to_repo
from ..helpers import check_solver_result


def test_circular_dependency_on_older_version(root, provider, repo):
    root.add_dependency("a", ">=1.0.0")

    add_to_repo(repo, "a", "1.0.0")
    add_to_repo(repo, "a", "2.0.0", deps={"b": "1.0.0"})
    add_to_repo(repo, "b", "1.0.0", deps={"a": "1.0.0"})

    check_solver_result(root, provider, {"a": "1.0.0"}, tries=2)


def test_diamond_dependency_graph(root, provider, repo):
    root.add_dependency("a", "*")
    root.add_dependency("b", "*")

    add_to_repo(repo, "a", "2.0.0", deps={"c": "^1.0.0"})
    add_to_repo(repo, "a", "1.0.0")

    add_to_repo(repo, "b", "2.0.0", deps={"c": "^3.0.0"})
    add_to_repo(repo, "b", "1.0.0", deps={"c": "^2.0.0"})

    add_to_repo(repo, "c", "3.0.0")
    add_to_repo(repo, "c", "2.0.0")
    add_to_repo(repo, "c", "1.0.0")

    check_solver_result(root, provider, {"a": "1.0.0", "b": "2.0.0", "c": "3.0.0"})


def test_backjumps_after_partial_satisfier(root, provider, repo):
    # c 2.0.0 is incompatible with y 2.0.0 because it requires x 1.0.0, but that
    # requirement only exists because of both a and b. The solver should be able
    # to deduce c 2.0.0's incompatibility and select c 1.0.0 instead.
    root.add_dependency("c", "*")
    root.add_dependency("y", "^2.0.0")

    add_to_repo(repo, "a", "1.0.0", deps={"x": ">=1.0.0"})
    add_to_repo(repo, "b", "1.0.0", deps={"x": "<2.0.0"})

    add_to_repo(repo, "c", "1.0.0")
    add_to_repo(repo, "c", "2.0.0", deps={"a": "*", "b": "*"})

    add_to_repo(repo, "x", "0.0.0")
    add_to_repo(repo, "x", "1.0.0", deps={"y": "1.0.0"})
    add_to_repo(repo, "x", "2.0.0")

    add_to_repo(repo, "y", "1.0.0")
    add_to_repo(repo, "y", "2.0.0")

    check_solver_result(root, provider, {"c": "1.0.0", "y": "2.0.0"}, tries=2)
