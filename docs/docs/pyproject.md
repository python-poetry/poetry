# The `pyproject.toml` file

The `tool.poetry` section of the `pyproject.toml` file is composed of multiple sections.

## name

The name of the package. **Required**

## version

The version of the package. **Required**

This should follow [semantic versioning](http://semver.org/). However it will not be enforced and you remain
free to follow another specification.

## description

A short description of the package. **Required**

## license

The license of the package.

The recommended notation for the most common licenses is (alphabetical):

* Apache-2.0
* BSD-2-Clause
* BSD-3-Clause
* BSD-4-Clause
* GPL-2.0
* GPL-2.0+
* GPL-3.0
* GPL-3.0+
* LGPL-2.1
* LGPL-2.1+
* LGPL-3.0
* LGPL-3.0+
* MIT

Optional, but it is highly recommended to supply this.
More identifiers are listed at the [SPDX Open Source License Registry](https://www.spdx.org/licenses/).

## authors

The authors of the package. This is a list of authors and should contain at least one author.

Authors must be in the form `name <email>`.

## readme

The readme file of the package. **Optional**

The file can be either `README.rst` or `README.md`.

## homepage

An URL to the website of the project. **Optional**

## repository

An URL to the repository of the project. **Optional**

## documentation

An URL to the documentation of the project. **Optional**

## keywords

A list of keywords (max: 5) that the package is related to. **Optional**

## classifiers

A list of PyPI [trove classifiers](https://pypi.org/classifiers/) that describe the project. **Optional**

```toml
[tool.poetry]
# ...
classifiers = [
    "Topic :: Software Development :: Build Tools",
    "Topic :: Software Development :: Libraries :: Python Modules"
]
```

!!!note

    Note that Python classifiers are still automatically added for you and are determined by your `python` requirement.

    The `license` property will also set the License classifier automatically.

## packages

A list of packages and modules to include in the final distribution.

If your project structure differs from the standard one supported by `poetry`,
you can specify the packages you want to include in the final distribution.

```toml
[tool.poetry]
# ...
packages = [
    { include = "mypackage" },
    { include = "extra_package/**/*.py" },
]
```

If your package is stored inside a "source" directory, you must specify it:

```toml
[tool.poetry]
# ...
packages = [
    { include = "mypackage", from = "lib" },
]
```

!!!note

    Using `packages` disables the package auto-detection feature meaning you have to
    **explicitly** specify the "default" package.

    For instance, if you have a package named `my_package` and you want to also include
    another package named `extra_package`, you will need to specify `my_package` explicitly:

    ```toml
    packages = [
        { include = "mypackage" },
        { include = "extra_package" },
    ]
    ```

!!!note

    Poetry is clever enough to detect Python subpackages.

    Thus, you only have to specify the directory where your root package resides.

## include and exclude

A list of patterns that will be included in the final package.

You can explicitly specify to Poetry that a set of globs should be ignored or included for the purposes of packaging.
The globs specified in the exclude field identify a set of files that are not included when a package is built.

If a VCS is being used for a package, the exclude field will be seeded with the VCS’ ignore settings (`.gitignore` for git for example).

```toml
[tool.poetry]
# ...
include = ["CHANGELOG.md"]
```

```toml
exclude = ["my_package/excluded.py"]
```

## `dependencies` and `dev-dependencies`

Poetry is configured to look for dependencies on [PyPi](https://pypi.org) by default.
Only the name and a version string are required in this case.

```toml
[tool.poetry.dependencies]
requests = "^2.13.0"
```

If you want to use a private repository, you can add it to your `pyproject.toml` file, like so:

```toml
[[tool.poetry.source]]
name = 'private'
url = 'http://example.com/simple'
```

!!!note

    Be aware that declaring the python version for which your package
    is compatible is mandatory:

    ```toml
    [tool.poetry.dependencies]
    python = "^3.6"
    ```

## `scripts`

This section describe the scripts or executable that will be installed when installing the package

```toml
[tool.poetry.scripts]
poetry = 'poetry:console.run'
```

Here, we will have the `poetry` script installed which will execute `console.run` in the `poetry` package.

## `extras`

Poetry supports extras to allow expression of:

* optional dependencies, which enhance a package, but are not required; and
* clusters of optional dependencies.

```toml
[tool.poetry]
name = "awesome"

[tool.poetry.dependencies]
# These packages are mandatory and form the core of this package’s distribution.
mandatory = "^1.0"

# A list of all of the optional dependencies, some of which are included in the
# below `extras`. They can be opted into by apps.
psycopg2 = { version = "^2.7", optional = true }
mysqlclient = { version = "^1.3", optional = true }

[tool.poetry.extras]
mysql = ["mysqlclient"]
pgsql = ["psycopg2"]
```

When installing packages, you can specify extras by using the `-E|--extras` option:

```bash
poetry install --extras "mysql pgsql"
poetry install -E mysql -E pgsql
```

## `plugins`

Poetry supports arbitrary plugins which work similarly to
[setuptools entry points](http://setuptools.readthedocs.io/en/latest/setuptools.html).
To match the example in the setuptools documentation, you would use the following:

```toml
[tool.poetry.plugins] # Optional super table

[tool.poetry.plugins."blogtool.parsers"]
".rst" = "some_module:SomeClass"
```

## Poetry and PEP-517

[PEP-517](https://www.python.org/dev/peps/pep-0517/) introduces a standard way
to define alternative build systems to build a Python project.

Poetry is compliant with PEP-517 so if you use Poetry to manage your Python
project you should reference it in the `build-system` section of the `pyproject.toml`
file like so:

```toml
[build-system]
requires = ["poetry>=0.12"]
build-backend = "poetry.masonry.api"
```

!!!note

    When using the `new` or `init` command this section will be automatically added.
