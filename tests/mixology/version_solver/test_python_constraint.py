from poetry.factory import Factory

from ..helpers import add_to_repo
from ..helpers import check_solver_result


def test_dependency_does_not_match_root_python_constraint(root, provider, repo):
    provider.set_package_python_versions("^3.6")
    root.add_dependency(Factory.create_dependency("foo", "*"))

    add_to_repo(repo, "foo", "1.0.0", python="<3.5")

    error = """The current project's Python requirement (>=3.6,<4.0) \
is not compatible with some of the required packages Python requirement:
  - foo requires Python <3.5, so it will not be satisfied for Python >=3.6,<4.0

Because no versions of foo match !=1.0.0
 and foo (1.0.0) requires Python <3.5, foo is forbidden.
So, because myapp depends on foo (*), version solving failed."""

    check_solver_result(root, provider, error=error)
