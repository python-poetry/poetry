from ..helpers import add_to_repo
from ..helpers import check_solver_result


def test_dependency_does_not_match_root_python_constraint(root, provider, repo):
    root.python_versions = "^3.6"
    root.add_dependency("foo", "*")

    add_to_repo(repo, "foo", "1.0.0", python="<3.5")

    error = """The current project must support the following Python versions: ^3.6

Because no versions of foo match !=1.0.0
 and foo (1.0.0) requires Python <3.5, foo is forbidden.
So, because myapp depends on foo (*), version solving failed."""

    check_solver_result(root, provider, error=error)
