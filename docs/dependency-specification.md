---
title: "Dependency specification"
draft: false
type: docs
layout: single

menu:
  docs:
    weight: 70
---

# Dependency specification

Dependencies for a project can be specified in various forms, which depend on the type
of the dependency and on the optional constraints that might be needed for it to be installed.

## `project.dependencies` and `tool.poetry.dependencies`

Prior Poetry 2.0, dependencies had to be declared in the `tool.poetry.dependencies`
section of the `pyproject.toml` file.

```toml
[tool.poetry.dependencies]
requests = "^2.13.0"
```

With Poetry 2.0, you should consider using the `project.dependencies` section instead.

```toml
[project]
# ...
dependencies = [
    "requests (>=2.23.0,<3.0.0)"
]
```

While dependencies in `tool.poetry.dependencies` are specified using toml tables,
dependencies in `project.dependencies` are specified as strings according
to [PEP 508](https://peps.python.org/pep-0508/).

In many cases, `tool.poetry.dependencies` can be replaced with `project.dependencies`.
However, there are some cases where you might still need to use `tool.poetry.dependencies`.
For example, if you want to define additional information that is not required for building
but only for locking (for example an explicit source), you can enrich dependency
information in the `tool.poetry` section.

```toml
[project]
# ...
dependencies = [
    "requests>=2.13.0",
]

[tool.poetry.dependencies]
requests = { source = "private-source" }
```

When both are specified, `project.dependencies` are used for metadata when building the project,
`tool.poetry.dependencies` is only used to enrich `project.dependencies` for locking.

Alternatively, you can add `dependencies` to `dynamic` and define your dependencies
completely in the `tool.poetry` section. Using only the `tool.poetry` section might
make sense in non-package mode when you will not build an sdist or a wheel.

```toml
[project]
# ...
dynamic = [ "dependencies" ]

[tool.poetry.dependencies]
requests = { version = ">=2.13.0", source = "private-source" }
```

{{% note %}}
Another use case for `tool.poetry.dependencies` are relative path dependencies
since `project.dependencies` only support absolute paths.
{{% /note %}}

{{% note %}}
Only main dependencies can be specified in the `project` section.
Other [Dependency groups]({{< relref "managing-dependencies#dependency-groups" >}})
must still be specified in the `tool.poetry` section.
{{% /note %}}

## Version constraints

### Compatible release requirements

**Compatible release requirements** specify a minimal version with the ability to update to later versions of the same level.
For example, if you specify a major, minor, and patch version, only patch-level changes are allowed.
If you only specify a major, and minor version, then minor- and patch-level changes are allowed.

`~=1.2.3` is an example of a compatible release requirement.

| Requirement | Versions allowed |
| ----------- | ---------------- |
| ~=1.2.3     | >=1.2.3 <1.3.0   |
| ~=1.2       | >=1.2.0 <2.0.0   |

### Wildcard requirements

**Wildcard requirements** allow for the latest (dependency dependent) version where the wildcard is positioned.

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

#### Multiple requirements

Multiple version requirements can also be separated with a comma, e.g. `>= 1.2, < 1.5`.

### Exact requirements

You can specify the exact version of a package.

`1.2.3` is an example of an exact version specification.

This will tell Poetry to install this version and this version only.
If other dependencies require a different version, the solver will ultimately fail and abort any install or update procedures.

Exact versions can also be specified with `==` according to [PEP 440](https://peps.python.org/pep-0440/).

`==1.2.3` is an example of this.

### Caret requirements

{{% warning %}}
Not supported in `project.dependencies`.

When using `poetry add` such constraints are automatically converted into an equivalent constraint.
{{% /warning %}}

**Caret requirements** allow [SemVer](https://semver.org/) compatible updates to a specified version. An update is allowed if the new version number does not modify the left-most non-zero digit in the major, minor, patch grouping. For instance, if we previously ran `poetry add requests@^2.13.0` and wanted to update the library and ran `poetry update requests`, poetry would update us to version `2.14.0` if it was available, but would not update us to `3.0.0`. If instead we had specified the version string as `^0.1.13`, poetry would update to `0.1.14` but not `0.2.0`. `0.0.x` is not considered compatible with any other version.

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

{{% warning %}}
Not supported in `project.dependencies`.

When using `poetry add` such constraints are automatically converted into an equivalent constraint.
{{% /warning %}}

**Tilde requirements** specify a minimal version with some ability to update.
If you specify a major, minor, and patch version or only a major and minor version, only patch-level changes are allowed.
If you only specify a major version, then minor- and patch-level changes are allowed.

`~1.2.3` is an example of a tilde requirement.

| Requirement | Versions allowed |
| ----------- | ---------------- |
| ~1.2.3      | >=1.2.3 <1.3.0   |
| ~1.2        | >=1.2.0 <1.3.0   |
| ~1          | >=1.0.0 <2.0.0   |

### Using the `@` operator

When adding dependencies via `poetry add`, you can use the `@` operator.
This is understood similarly to the `==` syntax, but also allows prefixing any
specifiers that are valid in `pyproject.toml`. For example:

```shell
poetry add "django@^4.0.0"
```

The above would translate to the following entry in `pyproject.toml`:

{{< tabs tabTotal="2" tabID1="at-project" tabID2="at-poetry" tabName1="[project]" tabName2="[tool.poetry]">}}

{{< tab tabID="at-project" >}}
```toml
[project]
# ...
dependencies = [
    "django (>=4.0.0,<5.0.0)",
]
```

{{< /tab >}}

{{< tab tabID="at-poetry" >}}
```toml
[tool.poetry.dependencies]
django = "^4.0.0"
```
{{< /tab >}}
{{< /tabs >}}

The special keyword `latest` is also understood by the `@` operator:
```shell
poetry add django@latest
```

The above would translate to the following entry in `pyproject.toml`, assuming the latest release of `django` is `5.1.3`:

{{< tabs tabTotal="2" tabID1="at-latest-project" tabID2="at-latest-poetry" tabName1="[project]" tabName2="[tool.poetry]">}}

{{< tab tabID="at-latest-project" >}}
```toml
[project]
# ...
dependencies = [
    "django (>=5.1.3,<6.0.0)",
]
```
{{< /tab >}}

{{< tab tabID="at-latest-poetry" >}}
```toml
[tool.poetry.dependencies]
django = "^5.1.3"
```
{{< /tab >}}
{{< /tabs >}}

#### Extras

Extras and `@` can be combined as one might expect (`package[extra]@version`):

```shell
poetry add django[bcrypt]@^4.0.0
```

## `git` dependencies

To depend on a library located in a `git` repository,
the minimum information you need to specify is the location of the repository:

{{< tabs tabTotal="2" tabID1="git-project" tabID2="git-poetry" tabName1="[project]" tabName2="[tool.poetry]">}}

{{< tab tabID="git-project" >}}
```toml
[project]
# ...
dependencies = [
    "requests @ git+https://github.com/requests/requests.git",
]
```
{{< /tab >}}

{{< tab tabID="git-poetry" >}}
In the `tool.poetry` section you use the `git` key:

```toml
[tool.poetry.dependencies]
requests = { git = "https://github.com/requests/requests.git" }
```

{{< /tab >}}
{{< /tabs >}}

Since we haven’t specified any other information,
Poetry assumes that we intend to use the latest commit on the `main` branch
to build our project.

You can explicit specify which branch, commit hash or tagged ref should be usd:

{{< tabs tabTotal="2" tabID1="git-rev-project" tabID2="git-rev-poetry" tabName1="[project]" tabName2="[tool.poetry]">}}

{{< tab tabID="git-rev-project" >}}
Append the information to the git url.

```toml
[project]
# ...
dependencies = [
    "requests @ git+https://github.com/requests/requests.git@next",
    "flask @ git+https://github.com/pallets/flask.git@38eb5d3b",
    "numpy @ git+https://github.com/numpy/numpy.git@v0.13.2",
]
```
{{< /tab >}}

{{< tab tabID="git-rev-poetry" >}}
Combine the `git` key with the `branch`, `rev` or `tag` key respectively.

```toml
[tool.poetry.dependencies]
# Get the latest revision on the branch named "next"
requests = { git = "https://github.com/kennethreitz/requests.git", branch = "next" }
# Get a revision by its commit hash
flask = { git = "https://github.com/pallets/flask.git", rev = "38eb5d3b" }
# Get a revision by its tag
numpy = { git = "https://github.com/numpy/numpy.git", tag = "v0.13.2" }
```
{{< /tab >}}
{{< /tabs >}}

It's possible to add a package that is located in a subdirectory of the VCS repository.

{{< tabs tabTotal="2" tabID1="git-subdir-project" tabID2="git-subdir-poetry" tabName1="[project]" tabName2="[tool.poetry]">}}

{{< tab tabID="git-subdir-project" >}}
Provide the subdirectory as a URL fragment similarly to what [pip](https://pip.pypa.io/en/stable/topics/vcs-support/#url-fragments) provides.
```toml
[project]
# ...
dependencies = [
    "subdir_package @ git+https://github.com/myorg/mypackage_with_subdirs.git#subdirectory=subdir"
]
```
{{< /tab >}}

{{< tab tabID="git-subdir-poetry" >}}
Use the `subdirectory` key in the `tool.poetry` section:

```toml
[tool.poetry.dependencies]
# Install a package named `subdir_package` from a folder called `subdir` within the repository
subdir_package = { git = "https://github.com/myorg/mypackage_with_subdirs.git", subdirectory = "subdir" }
```
{{< /tab >}}
{{< /tabs >}}

The corresponding `add` call looks like this:

```bash
poetry add "git+https://github.com/myorg/mypackage_with_subdirs.git#subdirectory=subdir"
```

To use an SSH connection, for example in the case of private repositories, use the following example syntax:

{{< tabs tabTotal="2" tabID1="git-ssh-project" tabID2="git-ssh-poetry" tabName1="[project]" tabName2="[tool.poetry]">}}

{{< tab tabID="git-ssh-project" >}}
```toml
[project]
# ...
dependencies = [
    "pendulum @ git+ssh://git@github.com/sdispater/pendulum.git"
]
```
{{< /tab >}}

{{< tab tabID="git-ssh-poetry" >}}
```toml
[tool.poetry.dependencies]
pendulum = { git = "git@github.com/sdispater/pendulum.git" }
```
{{< /tab >}}
{{< /tabs >}}

To use HTTP basic authentication with your git repositories, you can configure credentials similar to
how [repository credentials]({{< relref "repositories#configuring-credentials" >}}) are configured.

```bash
poetry config repositories.git-org-project https://github.com/org/project.git
poetry config http-basic.git-org-project username token
poetry add git+https://github.com/org/project.git
```

{{% note %}}
The default git client used is [Dulwich](https://www.dulwich.io/).

We fall back to legacy system git client implementation in cases where
[gitcredentials](https://git-scm.com/docs/gitcredentials) is used. This fallback will be removed in
a future release where `gitcredentials` helpers can be better supported natively.

In cases where you encounter issues with the default implementation, you may wish to
explicitly configure the use of the system git client via a shell subprocess call.

```bash
poetry config system-git-client true
```
{{% /note %}}

## `path` dependencies

{{< tabs tabTotal="2" tabID1="path-project" tabID2="path-poetry" tabName1="[project]" tabName2="[tool.poetry]">}}

{{< tab tabID="path-project" >}}
In the `project` section, you can only use absolute paths:

```toml
[project]
# ...
dependencies = [
    "my-package @ file:///absolute/path/to/my-package/dist/my-package-0.1.0.tar.gz"
]

```
{{< /tab >}}

{{< tab tabID="path-poetry" >}}
To depend on a library located in a local directory or file,
you can use the `path` property:

```toml
[tool.poetry.dependencies]
# directory
my-package = { path = "../my-package/", develop = true }

# file
my-package = { path = "../my-package/dist/my-package-0.1.0.tar.gz" }
```

To install directory path dependencies in editable mode use the `develop` keyword and set it to `true`.
{{< /tab >}}
{{< /tabs >}}

## `url` dependencies

`url` dependencies are libraries located on a remote archive.

{{< tabs tabTotal="2" tabID1="url-project" tabID2="url-poetry" tabName1="[project]" tabName2="[tool.poetry]">}}

{{< tab tabID="url-project" >}}
```toml
[project]
# ...
dependencies = [
    "my-package @ https://example.com/my-package-0.1.0.tar.gz"
]
```
{{< /tab >}}

{{< tab tabID="url-poetry" >}}
Use the `url` property.

```toml
[tool.poetry.dependencies]
# directory
my-package = { url = "https://example.com/my-package-0.1.0.tar.gz" }
```
{{< /tab >}}
{{< /tabs >}}

The corresponding `add` call is:

```bash
poetry add https://example.com/my-package-0.1.0.tar.gz
```

## Dependency `extras`

You can specify [PEP-508 Extras](https://www.python.org/dev/peps/pep-0508/#extras)
for a dependency as shown here.

{{< tabs tabTotal="2" tabID1="extras-project" tabID2="extras-poetry" tabName1="[project]" tabName2="[tool.poetry]">}}

{{< tab tabID="extras-project" >}}
```toml
[project]
# ...
dependencies = [
    "gunicorn[gevent] (>=20.1,<21.0)"
]
```
{{< /tab >}}

{{< tab tabID="extras-poetry" >}}
```toml
[tool.poetry.dependencies]
gunicorn = { version = "^20.1", extras = ["gevent"] }
```
{{< /tab >}}
{{< /tabs >}}

{{% note %}}
These activate extra defined for the dependency, to configure an optional dependency
for extras in your project refer to [`extras`]({{< relref "pyproject#extras" >}}).
{{% /note %}}

## `source` dependencies
{{% note %}}
It is not possible to define source dependencies in the `project` section.
{{% /note %}}

To depend on a package from an [alternate repository]({{< relref "repositories#installing-from-private-package-sources" >}}),
you can use the `source` property:

```toml
[[tool.poetry.source]]
name = "foo"
url = "https://foo.bar/simple/"
priority = "supplemental"

[tool.poetry.dependencies]
my-cool-package = { version = "*", source = "foo" }
```

with the corresponding `add` call:

```sh
poetry add my-cool-package --source foo
```

{{% note %}}
In this example, we expect `foo` to be configured correctly. See [using a private repository]({{< relref "repositories#installing-from-private-package-sources" >}})
for further information.
{{% /note %}}

## Python restricted dependencies

You can also specify that a dependency should be installed only for specific Python versions:

{{< tabs tabTotal="2" tabID1="python-restriction-project" tabID2="python-restriction-poetry" tabName1="[project]" tabName2="[tool.poetry]">}}

{{< tab tabID="python-restriction-project" >}}
```toml
[project]
# ...
dependencies = [
    "tomli (>=2.0.1,<3.0) ; python_version < '3.11'",
    "pathlib2 (>=2.2,<3.0) ; python_version >= '3.9' and python_version < '4.0'"
]
```
{{< /tab >}}

{{< tab tabID="python-restriction-poetry" >}}

```toml
[tool.poetry.dependencies]
tomli = { version = "^2.0.1", python = "<3.11" }
pathlib2 = { version = "^2.2", python = "^3.9" }
```
{{< /tab >}}
{{< /tabs >}}

## Using environment markers

If you need more complex install conditions for your dependencies,
Poetry supports [environment markers](https://www.python.org/dev/peps/pep-0508/#environment-markers):

{{< tabs tabTotal="2" tabID1="markers-project" tabID2="markers-poetry" tabName1="[project]" tabName2="[tool.poetry]">}}

{{< tab tabID="markers-project" >}}
```toml
[project]
# ...
dependencies = [
    "pathlib2 (>=2.2,<3.0) ; python_version <= '3.4' or sys_platform == 'win32'"
]
```
{{< /tab >}}

{{< tab tabID="markers-poetry" >}}
Use the `markers` property:

```toml
[tool.poetry.dependencies]
pathlib2 = { version = "^2.2", markers = "python_version <= '3.4' or sys_platform == 'win32'" }
```
{{< /tab >}}
{{< /tabs >}}

### `extra` environment marker

Poetry populates the `extra` marker with each of the selected extras of the root package.
For example, consider the following dependency:
```toml
[project.optional-dependencies]
paths = [
    "pathlib2 (>=2.2,<3.0) ; sys_platform == 'win32'"
]
```

`pathlib2` will be installed when you install your package with `--extras paths` on a `win32` machine.

#### Exclusive extras

Keep in mind that all combinations of possible extras available in your project need to be compatible with each other.
This means that in order to use differing or incompatible versions across different combinations, you need to make your
extra markers *exclusive*. For example, the following installs PyTorch from one source repository with CPU versions
when the `cuda` extra is *not* specified, while the other installs from another repository with a separate version set
for GPUs when the `cuda` extra *is* specified:

```toml
[project]
dependencies = [
    "torch (==2.3.1+cpu) ; extra != 'cuda'",
]

[project.optional-dependencies]
cuda = [
    "torch (==2.3.1+cu118)",
]

[tool.poetry.dependencies]
torch = [
    { markers = "extra != 'cuda'", source = "pytorch-cpu"},
    { markers = "extra == 'cuda'", source = "pytorch-cu118"},
 ]

[[tool.poetry.source]]
name = "pytorch-cpu"
url = "https://download.pytorch.org/whl/cpu"
priority = "explicit"

[[tool.poetry.source]]
name = "pytorch-cu118"
url = "https://download.pytorch.org/whl/cu118"
priority = "explicit"
```

For the CPU case, we have to specify `"extra != 'cuda'"` because the version specified is not compatible with the
GPU (`cuda`) version.

This same logic applies when you want either-or extras:

```toml
[project.optional-dependencies]
cuda = [
    "torch (==2.3.1+cu118) ; extra != 'cpu'",
]
cpu = [
    "torch (==2.3.1+cpu) ; extra != 'cuda'",
]

[tool.poetry.dependencies]
torch = [
    { markers = "extra == 'cpu' and extra != 'cuda'", source = "pytorch-cpu"},
    { markers = "extra == 'cuda' and extra != 'cpu'", source = "pytorch-cu118"},
 ]

[[tool.poetry.source]]
name = "pytorch-cpu"
url = "https://download.pytorch.org/whl/cpu"
priority = "explicit"

[[tool.poetry.source]]
name = "pytorch-cu118"
url = "https://download.pytorch.org/whl/cu118"
priority = "explicit"
```

## Multiple constraints dependencies

Sometimes, one of your dependency may have different version ranges depending
on the target Python versions.

Let's say you have a dependency on the package `foo` which is only compatible
with Python 3.6-3.7 up to version 1.9, and compatible with Python 3.8+ from version 2.0:
you would declare it like so:

{{< tabs tabTotal="2" tabID1="multiple-constraints-project" tabID2="multiple-constraints-poetry" tabName1="[project]" tabName2="[tool.poetry]">}}

{{< tab tabID="multiple-constraints-project" >}}
```toml
[project]
# ...
dependencies = [
    "foo (<=1.9) ; python_version >= '3.6' and python_version < '3.8'",
    "foo (>=2.0,<3.0) ; python_version >= '3.8'"
]
```
{{< /tab >}}

{{< tab tabID="multiple-constraints-poetry" >}}
```toml
[tool.poetry.dependencies]
foo = [
    {version = "<=1.9", python = ">=3.6,<3.8"},
    {version = "^2.0", python = ">=3.8"}
]
```
{{< /tab >}}
{{< /tabs >}}

{{% note %}}
The constraints **must** have different requirements (like `python`)
otherwise it will cause an error when resolving dependencies.
{{% /note %}}

### Combining git / url / path dependencies with source repositories

Direct origin (`git`/ `url`/ `path`) dependencies can satisfy the requirement of a dependency that
doesn't explicitly specify a source, even when mutually exclusive markers are used. For instance
in the following example the url package will also be a valid solution for the second requirement:
```toml
foo = [
    { platform = "darwin", url = "https://example.com/example-1.0-py3-none-any.whl" },
    { platform = "linux", version = "^1.0" },
]
```

Sometimes you may instead want to use a direct origin dependency for specific conditions
(i.e. a compiled package that is not available on PyPI for a certain platform/architecture) while
falling back on source repositories in other cases. In this case you should explicitly ask for your
dependency to be satisfied by another `source`. For example:
```toml
foo = [
    { platform = "darwin", url = "https://example.com/foo-1.0.0-py3-none-macosx_11_0_arm64.whl" },
    { platform = "linux", version = "^1.0", source = "pypi" },
]
```

## Expanded dependency specification syntax

In the case of more complex dependency specifications, you may find that you
end up with lines which are very long and difficult to read. In these cases,
you can shift from using "inline table" syntax, to the "standard table" syntax.

An example where this might be useful is the following:

```toml
[tool.poetry.group.dev.dependencies]
black = {version = "19.10b0", allow-prereleases = true, python = "^3.7", markers = "platform_python_implementation == 'CPython'"}
```

As a single line, this is a lot to digest. To make this a bit easier to
work with, you can do the following:

```toml
[tool.poetry.group.dev.dependencies.black]
version = "19.10b0"
allow-prereleases = true
python = "^3.7"
markers = "platform_python_implementation == 'CPython'"
```

The same information is still present, and ends up providing the exact
same specification. It's simply split into multiple, slightly more readable,
lines.

### Handling of pre-releases

Per default, Poetry will prefer stable releases and only choose a pre-release
if no stable release satisfies a version constraint. In some cases, this may result in
a solution containing pre-releases even if another solution without pre-releases exists.

If you want to disallow pre-releases for a specific dependency,
you can set `allow-prereleases` to `false`. In this case, dependency resolution will
fail if there is no solution without choosing a pre-release.

If you want to prefer the latest version of a dependency even if it is a pre-release,
you can set `allow-prereleases` to `true` so that Poetry makes no distinction
between stable and pre-release versions during dependency resolution.
