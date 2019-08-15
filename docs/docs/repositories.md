# Repositories

## Using the PyPI repository

By default, Poetry is configured to use the [PyPI](https://pypi.org) repository,
for package installation and publishing.

So, when you add dependencies to your project, Poetry will assume they are available
on PyPI.

This represents most cases and will likely be enough for most users.


## Using a private repository

However, at times, you may need to keep your package private while still being
able to share it with your teammates. In this case, you will need to use a private
repository.

### Adding a repository

Adding a new repository is easy with the `config` command.

```bash
poetry config repositories.foo https://foo.bar/simple/
```

This will set the url for repository `foo` to `https://foo.bar/simple/`.

### Configuring credentials

If you want to store your credentials for a specific repository, you can do so easily:

```bash
poetry config http-basic.foo username password
```

If you do not specify the password you will be prompted to write it.

!!!note

    To publish to PyPI, you can set your credentials for the repository
    named `pypi`:

    ```bash
    poetry config http-basic.pypi username password
    ```

You can also specify the username and password when using the `publish` command
with the `--username` and `--password` options.

### Install dependencies from a private repository

Now that you can publish to your private repository, you need to be able to
install dependencies from it.

For that, you have to edit your `pyproject.toml` file, like so

```toml
[[tool.poetry.source]]
name = "foo"
url = "https://foo.bar/simple/"
```

From now on, Poetry will also look for packages in your private repository.

If your private repository requires HTTP Basic Auth be sure to add the username and
password to your `http-basic` config using the example above (be sure to use the
same name that is in the `tool.poetry.source` section). Poetry will use these values
to authenticate to your private repository when downloading or looking for packages.
