# Libraries

This chapter will tell you how to make your library installable through Poetry.

## Every project is a package

As soon as you have a `pyproject.toml` in a directory, that directory is a package.
However, to make it accessible to others you will need to package and publish it.


## Versioning

While Poetry does not enforce any convention regarding package versioning,
it **strongly** recommends to follow [semantic versioning](https://semver.org).

This has many advantages for the end users and allows them to set appropriate
[version constraints](/docs/versions/).

## Lock file

For your library, you may commit the `poetry.lock` file if you want to.
This can help your team to always test against the same dependency versions.
However, this lock file will not have any effect on other projects that depend on it.
It only has an effect on the main project.

If you do not want to commit the lock file and you are using git, add it to the `.gitignore`.

## Packaging

Before you can actually publish your library, you will need to package it.

```bash
poetry build
```

This command will package your library in two different formats: `sdist` which is
the source format, and `wheel` which is a `compiled` package.

Once that's done you are ready to publish your library

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

This will package and publish the library to PyPI, at the condition that you are a registered user
and you have [configured your credentials](/docs/repositories/#adding-credentials) properly.

!!!note

    The `publish` command does not execute `build` by default.

    If you want to build and publish your packages together,
    just pass the `--build` option.

Once this is done, your library will be available to anyone.


## Publishing to a private repository

Sometimes, you may want to keep your library private but also being accessible to your team.

In this case, you will need to use a private repository.

In order to publish to a private repository, you will need to add it to your
global list of repositories. See [Adding a repository](/docs/repositories/#adding-a-repository)
for more information.

Once this is done, you can actually publish to it like so:

```bash
poetry publish -r my-repository
```
