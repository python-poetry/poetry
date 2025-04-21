---
title: "Libraries"
draft: false
type: docs
layout: "docs"

menu:
  docs:
    weight: 20
---


# Libraries

This chapter will tell you how to make your library installable through Poetry.


## Versioning

Poetry requires [PEP 440](https://peps.python.org/pep-0440)-compliant versions for all projects.

While Poetry does not enforce any release convention, it used to encourage the use of
[semantic versioning](https://semver.org/) within the scope of
[PEP 440](https://peps.python.org/pep-0440/#semantic-versioning) and supports
[version constraints]({{< relref "dependency-specification/#caret-requirements" >}})
that are especially suitable for semver.

{{% note %}}

As an example, `1.0.0-hotfix.1` is not compatible with [PEP 440](https://peps.python.org/pep-0440). You can instead
choose to use `1.0.0-post1` or `1.0.0.post1`.

{{% /note %}}

## Lock file

For your library, you may commit the `poetry.lock` file if you want to.
This can help your team to always test against the same dependency versions.
However, this lock file will not have any effect on other projects that depend on it.
It only has an effect on the main project.

If you do not want to commit the lock file and you are using git, add it to the `.gitignore`.

## Packaging

Before you can actually publish your library, you will need to package it.

You need to define a build-system according to [PEP 517](https://peps.python.org/pep-0517/) in the `pyproject.toml` file:

```toml
[build-system]
requires = ["poetry-core>=2.0.0,<3.0.0"]
build-backend = "poetry.core.masonry.api"
```

Then you can package your library by running:

```bash
poetry build
```

This command will package your library in two different formats: `sdist` which is
the source format, and `wheel` which is a `compiled` package.

Poetry will automatically include some metadata files when building a package. When building
a `wheel`, the following files are included in the `.dist-info` directory:
- `LICENSE`
- `LICENSE.*`
- `COPYING`
- `COPYING.*`
- `LICENSES/**`

When building an `sdist`, the following files will be included in the root folder:
  - `LICENSE*`

### Alternative build backends

If you want to use a different build backend, you can specify it in the `pyproject.toml` file:

```toml
[build-system]
requires = ["maturin>=0.8.1,<0.9"]
build-backend = "maturin"
```

The `poetry build` command will then use the specified build backend to build your package in
an isolated environment. Ensure you have specified any additional settings according to the
documentation of the build backend you are using.


Once building is done, you are ready to publish your library.

## Publishing to PyPI

Alright, so now you can publish packages.

Poetry will publish to [PyPI](https://pypi.org) by default. Anything that is published to PyPI
is available automatically through Poetry. Since [pendulum](https://pypi.org/project/pendulum/)
is on PyPI we can depend on it without having to specify any additional repositories.

If we wanted to share `poetry-demo` with the Python community, we would publish on PyPI as well.
Doing so is really easy.

```bash
poetry publish
```

This will package and publish the library to PyPI, on the condition that you are a registered user
and you have [configured your credentials]({{< relref "repositories#configuring-credentials" >}}) properly.

{{% note %}}
The `publish` command does not execute `build` by default.

If you want to build and publish your packages together,
just pass the `--build` option.
{{% /note %}}

Once this is done, your library will be available to anyone.


## Publishing to a private repository

Sometimes, you may want to keep your library private but also be accessible to your team.

In this case, you will need to use a private repository.

In order to publish to a private repository, you will need to add it to your
global list of repositories. See [Adding a repository]({{< relref "repositories#adding-a-repository" >}})
for more information.

Once this is done, you can publish your package to the repository like so:

```bash
poetry publish -r my-repository
```
