from __future__ import annotations

from typing import TYPE_CHECKING

from poetry.core.packages.package import Package

from poetry.installation.chooser import Chooser


if TYPE_CHECKING:
    from poetry.repositories.repository_pool import RepositoryPool
    from poetry.utils.env import MockEnv


def test_chooser_no_links_found_error(env: MockEnv, pool: RepositoryPool) -> None:
    chooser = Chooser(pool, env)
    package = Package(
        "demo",
        "0.1.0",
        source_type="legacy",
        source_reference="foo",
        source_url="https://legacy.foo.bar/simple/",
    )

    unsupported_wheels = {"demo-0.1.0-py3-none-any.whl"}
    error = chooser._no_links_found_error(
        package=package,
        links_seen=4,
        wheels_skipped=3,
        sdists_skipped=1,
        unsupported_wheels=unsupported_wheels,
    )
    assert (
        error.get_text(debug=True, strip=True)
        == f"""\
Unable to find installation candidates for {package.name} ({package.version})

This is likely not a Poetry issue.

  - 4 candidate(s) were identified for the package
  - 3 wheel(s) were skipped due to your installer.no-binary policy
  - 1 source distribution(s) were skipped due to your installer.only-binary policy
  - 1 wheel(s) were skipped as your project's environment does not support the identified abi tags

The following wheel(s) were skipped as the current project environment does not support them due to abi compatibility \
issues.

  - {"  -".join(unsupported_wheels)}

If you would like to see the supported tags in your project environment, you can execute the following command:

    poetry debug tags

Solutions:
Make sure the lockfile is up-to-date. You can try one of the following;

    1. Regenerate lockfile: poetry lock --no-cache --regenerate
    2. Update package     : poetry update --no-cache {package.name}

If any of those solutions worked, you will have to clear your caches using (poetry cache clear --all .).

If neither works, please first check to verify that the {package.name} has published wheels available from your configured \
source ({package.source_reference}) that are compatible with your environment- ie. operating system, architecture \
(x86_64, arm64 etc.), python interpreter.\
"""
    )

    assert (
        error.get_text(debug=False, strip=True)
        == f"""\
Unable to find installation candidates for {package.name} ({package.version})

This is likely not a Poetry issue.

  - 4 candidate(s) were identified for the package
  - 3 wheel(s) were skipped due to your installer.no-binary policy
  - 1 source distribution(s) were skipped due to your installer.only-binary policy
  - 1 wheel(s) were skipped as your project's environment does not support the identified abi tags

Solutions:
Make sure the lockfile is up-to-date. You can try one of the following;

    1. Regenerate lockfile: poetry lock --no-cache --regenerate
    2. Update package     : poetry update --no-cache {package.name}

If any of those solutions worked, you will have to clear your caches using (poetry cache clear --all .).

If neither works, please first check to verify that the {package.name} has published wheels available from your configured \
source ({package.source_reference}) that are compatible with your environment- ie. operating system, architecture \
(x86_64, arm64 etc.), python interpreter.

You can also run your poetry command with -v to see more information.\
"""
    )
