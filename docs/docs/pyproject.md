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

The readme file of the package. **Required**

The file can be either `README.rst` or `README.md`.

## homepage

An URL to the website of the project. **Optional**

## repository

An URL to the repository of the project. **Optional**

## documentation

An URL to the documentation of the project. **Optional**

## keywords

A list of keywords (max: 5) that the package is related to. **Optional**

## include and exclude

A list of patterns that will be included in the final package.

You can explicitly specify to Poetry that a set of globs should be ignored or included for the purposes of packaging.
The globs specified in the exclude field identify a set of files that are not included when a package is built.

If a VCS is being used for a package, the exclude field will be seeded with the VCS’ ignore settings (`.gitignore` for git for example).

```toml
[package]
# ...
include = ["package/**/*.py", "package/**/.c"]
```

```toml
exclude = ["package/excluded.py"]
```

### `dependencies` and `dev-dependencies`

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
