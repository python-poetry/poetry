---
title: "FAQ"
draft: false
type: docs
layout: single

menu:
  docs:
    weight: 110
---

# FAQ

### Why is the dependency resolution process slow?

While the dependency resolver at the heart of Poetry is highly optimized and
should be fast enough for most cases, with certain sets of dependencies
it can take time to find a valid solution.

This is due to the fact that not all libraries on PyPI have properly declared their metadata
and, as such, they are not available via the PyPI JSON API. At this point, Poetry has no choice
but to download the packages and inspect them to get the necessary information. This is an expensive
operation, both in bandwidth and time, which is why it seems this is a long process.

At the moment there is no way around it.

{{% note %}}
Once Poetry has cached the releases' information, the dependency resolution process
will be much faster.
{{% /note %}}

### Why are unbound version constraints a bad idea?

A version constraint without an upper bound such as `*` or `>=3.4` will allow updates to any future version of the dependency.
This includes major versions breaking backward compatibility.

Once a release of your package is published, you cannot tweak its dependencies anymore in case a dependency breaks BC
– you have to do a new release but the previous one stays broken.

The only good alternative is to define an upper bound on your constraints,
which you can increase in a new release after testing that your package is compatible
with the new major version of your dependency.

For example instead of using `>=3.4` you should use `^3.4` which allows all versions `<4.0`.
The `^` operator works very well with libraries following [semantic versioning](https://semver.org).

### Is tox supported?

**Yes**. By using the [isolated builds](https://tox.readthedocs.io/en/latest/config.html#conf-isolated_build) `tox` provides,
you can use it in combination with the PEP 517 compliant build system provided by Poetry.

So, in your `pyproject.toml` file, add this section if it does not already exist:

```toml
[build-system]
requires = ["poetry-core>=1.0.0"]
build-backend = "poetry.core.masonry.api"
```

`tox` can be configured in multiple ways. It depends on what should be the code under test and which dependencies
should be installed.

#### Usecase #1
```ini
[tox]
isolated_build = true

[testenv]
deps =
    pytest
commands =
    pytest tests/ --import-mode importlib
```

`tox` will create an `sdist` package of the project and uses `pip` to install it in a fresh environment.
Thus, dependencies are resolved by `pip`.

#### Usecase #2
```ini
[tox]
isolated_build = true

[testenv]
allowlist_externals = poetry
commands_pre =
    poetry install --no-root --sync
commands =
    poetry run pytest tests/ --import-mode importlib
```

`tox` will create an `sdist` package of the project and uses `pip` to install it in a fresh environment.
Thus, dependencies are resolved by `pip` in the first place. But afterwards we run Poetry,
 which will install the locked dependencies into the environment.

#### Usecase #3
```ini
[tox]
isolated_build = true

[testenv]
skip_install = true
allowlist_externals = poetry
commands_pre =
    poetry install
commands =
    poetry run pytest tests/ --import-mode importlib
```

`tox` will not do any install. Poetry installs all the dependencies and the current package an editable mode.
Thus, tests are running against the local files and not the built and installed package.

### I don't want Poetry to manage my virtual environments. Can I disable it?

While Poetry automatically creates virtual environments to always work isolated
from the global Python installation, there are valid reasons why it's not necessary
and is an overhead, like when working with containers.

In this case, you can disable this feature by setting the `virtualenvs.create` setting to `false`:

```bash
poetry config virtualenvs.create false
```

### Why is Poetry telling me that the current project's Python requirement is not compatible with one or more packages' Python requirements?

Unlike `pip`, Poetry doesn't resolve for just the Python in the current environment. Instead it makes sure that a dependency
is resolvable within the given Python version range in `pyproject.toml`.

Assume you have the following `pyproject.toml`:

```toml
[tool.poetry.dependencies]
python = "^3.7"
```

This means your project aims to be compatible with any Python version >=3.7,<4.0. Whenever you try to add a dependency
whose Python requirement doesn't match the whole range Poetry will tell you this, e.g.:

```
The current project's Python requirement (>=3.7.0,<4.0.0) is not compatible with some of the required packages Python requirement:
    - scipy requires Python >=3.7,<3.11, so it will not be satisfied for Python >=3.11,<4.0.0
```

Usually you will want to match the Python requirement of your project with the upper bound of the failing dependency.
Alternative you can tell Poetry to install this dependency [only for a specific range of Python versions]({{< relref "dependency-specification#multiple-constraints-dependencies" >}}),
if you know that it's not needed in all versions.


### Why does Poetry enforce PEP 440 versions?

This is done so to be compliant with the broader Python ecosystem.

For example, if Poetry builds a distribution for a project that uses a version that is not valid according to
[PEP 440](https://peps.python.org/pep-0440), third party tools will be unable to parse the version correctly.


### Poetry busts my Docker cache because it requires me to COPY my source files in before installing 3rd party dependencies

By default running `poetry install ...` requires you to have your source files present (both the "root" package and any `path` dependencies you might have).
This interacts poorly with Docker's caching mechanisms because any change to the source file will make any layers (subsequent commands in your Dockerfile) re-run.
For example, you might have a Dockerfile that looks something like this:

```text
FROM python
COPY pyproject.toml poetry.lock .
COPY src/ ./src
RUN pip install poetry && poetry install --no-dev
```

The `RUN` instruction will always re-run, which forces all 3rd party dependencies (likely the slowest step out of these) to re-run if you changed any files in `src/`.

To avoid this cache busting you can split this into two steps:

1. Install 3rd party dependencies.
2. Copy over your source code and install just the source code.

This might look something like this:

```text
FROM python
COPY pyproject.toml poetry.lock .
RUN pip install poetry && poetry install --no-root --no-path
COPY src/ ./src
RUN poetry install --no-dev
```

The two key options we are using here are `--no-root` (skips installing the project source) and `--no-path` (skips installing any local path dependencies, you can skip this if you don't have any).
[More information on the options available for `poetry install`]({{< relref "cli#install" >}}).
