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
should be fast enough for most cases, sometimes, with some specific set of dependencies,
it can take time to find a valid solution.

This is due to the fact that not all libraries on PyPI have properly declared their metadata
and, as such, they are not available via the PyPI JSON API. At this point, Poetry has no choice
but downloading the packages and inspect them to get the necessary information. This is an expensive
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

And use a `tox.ini` configuration file similar to this:

```INI
[tox]
isolated_build = true
envlist = py27, py36

[testenv]
allowlist_externals = poetry
commands =
    poetry install -v
    poetry run pytest tests/
```

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
is resolvable within the given Python version range in the `pyproject.toml`.

Assume you have this is in the `pyproject.toml`:

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

Usually, you will want to match the Python requirement of your project with the upper bounds of the failing dependency.
Alternative you can tell Poetry to install this dependency [only for a specific range of Python versions](/docs/dependency-specification/#multiple-constraints-dependencies),
if you know that it's not needed in all versions.
