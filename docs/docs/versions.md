# Versions and constraints

Poetry recommends following [semantic versioning](https://semver.org) but will not enforce it.

## Version constraints

### Caret requirements

**Caret requirements** allow SemVer compatible updates to a specified version.
An update is allowed if the new version number does not modify the left-most non-zero digit in the major, minor, patch grouping.
In this case, if we ran `poetry update requests`, poetry would update us to version `2.14.0` if it was available,
but would not update us to `3.0.0`.
If instead we had specified the version string as `^0.1.13`, poetry would update to `0.1.14` but not `0.2.0`.
`0.0.x` is not considered compatible with any other version.

Here are some more examples of caret requirements and the versions that would be allowed with them:

| Requirement | Versions allowed |
| ----------- | ---------------- |
| ^1.2.3      | >=1.2.3 <2.0.0   |
| ^1.2        | >=1.2.0 <2.0.0   |
| ^1          | >=1.0.0 <2.0.0   |
| ^0.2.3      | >=0.2.3 <0.3.0   |
| ^0.0.3      | >=0.0.3 <0.0.4   |
| ^0.0        | >=0.0.0 <0.1.0   |
| ^0          | >=0.0.0 <1.0.0   |

### Tilde requirements

**Tilde requirements** specify a minimal version with some ability to update.
If you specify a major, minor, and patch version or only a major and minor version, only patch-level changes are allowed.
If you only specify a major version, then minor- and patch-level changes are allowed.

`~1.2.3` is an example of a tilde requirement.

| Requirement | Versions allowed |
| ----------- | ---------------- |
| ~1.2.3      | >=1.2.3 <1.3.0   |
| ~1.2        | >=1.2.0 <1.3.0   |
| ~1          | >=1.0.0 <2.0.0   |

### Wildcard requirements

**Wildcard requirements** allow for any version where the wildcard is positioned.

`*`, `1.*` and `1.2.*` are examples of wildcard requirements.

| Requirement | Versions allowed |
| ----------- | ---------------- |
| *           | >=0.0.0          |
| 1.*         | >=1.0.0 <2.0.0   |
| 1.2.*       | >=1.2.0 <1.3.0   |

### Inequality requirements

**Inequality requirements** allow manually specifying a version range or an exact version to depend on.

Here are some examples of inequality requirements:

```text
>= 1.2.0
> 1
< 2
!= 1.2.3
```

### Exact requirements

You can specify the exact version of a package.
This will tell Poetry to install this version and this version only.
If other dependencies require a different version, the solver will ultimately fail and abort any install or update procedures.

#### Multiple requirements

Multiple version requirements can also be separated with a comma, e.g. `>= 1.2, < 1.5`.

### `git` dependencies

To depend on a library located in a `git` repository,
the minimum information you need to specify is the location of the repository with the git key:

```toml
[tool.poetry.dependencies]
requests = { git = "https://github.com/requests/requests.git" }
```

Since we haven’t specified any other information,
Poetry assumes that we intend to use the latest commit on the `master` branch to build our project.
You can combine the `git` key with the `rev`, `tag`, or `branch` keys to specify something else.
Here's an example of specifying that you want to use the latest commit on a branch named `next`:

```toml
[tool.poetry.dependencies]
requests = { git = "https://github.com/kennethreitz/requests.git", branch = "next" }
```

### `path` dependencies

To depend on a library located in a local directory or file,
you can use the `path` property:

```toml
[tool.poetry.dependencies]
# directory
my-package = { path = "../my-package/" }

# file
my-package = { path = "../my-package/dist/my-package-0.1.0.tar.gz" }
```

!!!note

    You can install path dependencies in editable/development mode.
    Just pass `--develop my-package` (repeatable as much as you want) to
    the `install` command.


### Python restricted dependencies

You can also specify that a dependency should be installed only for specific Python versions:

```toml
[tool.poetry.dependencies]
pathlib2 = { version = "^2.2", python = "~2.7" }
```

```toml
[tool.poetry.dependencies]
pathlib2 = { version = "^2.2", python = ["~2.7", "^3.2"] }
```


### Multiple constraints dependencies

Sometimes, one of your dependency may have different version ranges depending
on the target Python versions.

Let's say you have a dependency on the package `foo` which is only compatible
with Python <3.0 up to version 1.9 and compatible with Python 3.4+ from version 2.0:
you would declare it like so:

```toml
[tool.poetry.dependencies]
foo = [
    {version = "<=1.9", python = "^2.7"},
    {version = "^2.0", python = "^3.4"}
]
```

!!!note

    The constraints **must** have different requirements (like `python`)
    otherwise it will cause an error when resolving dependencies.
