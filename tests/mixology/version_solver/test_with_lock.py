from poetry.factory import Factory

from ...helpers import get_package
from ..helpers import add_to_repo
from ..helpers import check_solver_result


def test_with_compatible_locked_dependencies(root, provider, repo):
    root.add_dependency(Factory.create_dependency("foo", "*"))

    add_to_repo(repo, "foo", "1.0.0", deps={"bar": "1.0.0"})
    add_to_repo(repo, "foo", "1.0.1", deps={"bar": "1.0.1"})
    add_to_repo(repo, "foo", "1.0.2", deps={"bar": "1.0.2"})
    add_to_repo(repo, "bar", "1.0.0")
    add_to_repo(repo, "bar", "1.0.1")
    add_to_repo(repo, "bar", "1.0.2")

    check_solver_result(
        root,
        provider,
        result={"foo": "1.0.1", "bar": "1.0.1"},
        locked={"foo": get_package("foo", "1.0.1"), "bar": get_package("bar", "1.0.1")},
    )


def test_with_incompatible_locked_dependencies(root, provider, repo):
    root.add_dependency(Factory.create_dependency("foo", ">1.0.1"))

    add_to_repo(repo, "foo", "1.0.0", deps={"bar": "1.0.0"})
    add_to_repo(repo, "foo", "1.0.1", deps={"bar": "1.0.1"})
    add_to_repo(repo, "foo", "1.0.2", deps={"bar": "1.0.2"})
    add_to_repo(repo, "bar", "1.0.0")
    add_to_repo(repo, "bar", "1.0.1")
    add_to_repo(repo, "bar", "1.0.2")

    check_solver_result(
        root,
        provider,
        result={"foo": "1.0.2", "bar": "1.0.2"},
        locked={"foo": get_package("foo", "1.0.1"), "bar": get_package("bar", "1.0.1")},
    )


def test_with_unrelated_locked_dependencies(root, provider, repo):
    root.add_dependency(Factory.create_dependency("foo", "*"))

    add_to_repo(repo, "foo", "1.0.0", deps={"bar": "1.0.0"})
    add_to_repo(repo, "foo", "1.0.1", deps={"bar": "1.0.1"})
    add_to_repo(repo, "foo", "1.0.2", deps={"bar": "1.0.2"})
    add_to_repo(repo, "bar", "1.0.0")
    add_to_repo(repo, "bar", "1.0.1")
    add_to_repo(repo, "bar", "1.0.2")
    add_to_repo(repo, "baz", "1.0.0")

    check_solver_result(
        root,
        provider,
        result={"foo": "1.0.2", "bar": "1.0.2"},
        locked={"baz": get_package("baz", "1.0.1")},
    )


def test_unlocks_dependencies_if_necessary_to_ensure_that_a_new_dependency_is_statisfied(
    root, provider, repo
):
    root.add_dependency(Factory.create_dependency("foo", "*"))
    root.add_dependency(Factory.create_dependency("newdep", "2.0.0"))

    add_to_repo(repo, "foo", "1.0.0", deps={"bar": "<2.0.0"})
    add_to_repo(repo, "bar", "1.0.0", deps={"baz": "<2.0.0"})
    add_to_repo(repo, "baz", "1.0.0", deps={"qux": "<2.0.0"})
    add_to_repo(repo, "qux", "1.0.0")
    add_to_repo(repo, "foo", "2.0.0", deps={"bar": "<3.0.0"})
    add_to_repo(repo, "bar", "2.0.0", deps={"baz": "<3.0.0"})
    add_to_repo(repo, "baz", "2.0.0", deps={"qux": "<3.0.0"})
    add_to_repo(repo, "qux", "2.0.0")
    add_to_repo(repo, "newdep", "2.0.0", deps={"baz": ">=1.5.0"})

    check_solver_result(
        root,
        provider,
        result={
            "foo": "2.0.0",
            "bar": "2.0.0",
            "baz": "2.0.0",
            "qux": "1.0.0",
            "newdep": "2.0.0",
        },
        locked={
            "foo": get_package("foo", "2.0.0"),
            "bar": get_package("bar", "1.0.0"),
            "baz": get_package("baz", "1.0.0"),
            "qux": get_package("qux", "1.0.0"),
        },
    )


def test_with_compatible_locked_dependencies_use_latest(root, provider, repo):
    root.add_dependency(Factory.create_dependency("foo", "*"))
    root.add_dependency(Factory.create_dependency("baz", "*"))

    add_to_repo(repo, "foo", "1.0.0", deps={"bar": "1.0.0"})
    add_to_repo(repo, "foo", "1.0.1", deps={"bar": "1.0.1"})
    add_to_repo(repo, "foo", "1.0.2", deps={"bar": "1.0.2"})
    add_to_repo(repo, "bar", "1.0.0")
    add_to_repo(repo, "bar", "1.0.1")
    add_to_repo(repo, "bar", "1.0.2")
    add_to_repo(repo, "baz", "1.0.0")
    add_to_repo(repo, "baz", "1.0.1")

    check_solver_result(
        root,
        provider,
        result={"foo": "1.0.2", "bar": "1.0.2", "baz": "1.0.0"},
        locked={
            "foo": get_package("foo", "1.0.1"),
            "bar": get_package("bar", "1.0.1"),
            "baz": get_package("baz", "1.0.0"),
        },
        use_latest=["foo"],
    )
