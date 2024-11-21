---
title: "Building extension modules"
draft: false
type: docs
layout: single

menu:
  docs:
    weight: 125
---

# Building Extension Modules

{{% warning %}}
While this feature has been around since almost the beginning of the Poetry project and has needed minimal changes,
it is still considered unstable. You can participate in the discussions about stabilizing this feature
[here](https://github.com/python-poetry/poetry/issues/2740).

And as always, your contributions towards the goal of improving this feature are also welcome.
{{% /warning %}}

Poetry allows a project developer to introduce support for, build and distribute native extensions within their project.
In order to achieve this, at the highest level, the following steps are required.

{{< steps >}}
{{< step >}}
**Add Build Dependencies**

The build dependencies, in this context, refer to those Python packages that are required in order to successfully execute
your build script. Common examples include `cython`, `meson`, `maturin`, `setuptools` etc., depending on how your
extension is built.

{{% note %}}
You must assume that only Python built-ins are available by default in a build environment. This means, if you need
even packages like `setuptools`, it must be explicitly declared.
{{% /note %}}

The necessary build dependencies must be added to the `build-system.requires` section of your `pyproject.toml` file.

```toml
[build-system]
requires = ["poetry-core", "setuptools", "cython"]
build-backend = "poetry.core.masonry.api"
```

{{% note %}}
It is recommended that you consider specifying version constraints to all entries in `build-system.requires` in order to
avoid surprises if one of the packages introduce a breaking change. For example, you can set `cython` to
`cython>=3.0.11,<4.0.0` to ensure no major version upgrades are used.
{{% /note %}}

{{% note %}}
If you wish to develop the build script within your project's virtual environment, then you must also add the
dependencies to your project explicitly to a dependency group - the name of which is not important.

```sh
poetry add --group=build setuptools cython
```
{{% /note %}}

{{< /step >}}

{{< step >}}
**Add Build Script**

The build script can be a free-form Python script that uses any dependency specified in the previous step. This can be
named as needed, but **must** be located within the project root directory (or a subdirectory) and also **must**
be included in your source distribution. You can see the [example snippets section]({{< relref "#example-snippets" >}})
for inspiration.

{{% note %}}
The build script is always executed from the project root. And it is expected to move files around to their destinations
as expected by Poetry as per your `pyproject.toml` file.
{{% /note %}}

```toml
[tool.poetry.build]
script = "relative/path/to/build-extension.py"
```

{{% note %}}
The name of the build script is arbitrary. Common practice has been to name it `build.py`, however this is not
mandatory. You **should** consider [using a subdirectory]({{< relref "#can-i-store-the-build-script-in-a-subdirectory" >}})
if feasible.
{{% /note %}}

{{< /step >}}

{{< step >}}
**Specify Distribution Files**

{{% warning %}}
The following is an example, and should not be considered as complete.
{{% /warning %}}

```toml
[tool.poetry]
...
include = [
    { path = "package/**/*.so", format = "wheel" },
]
```

The key takeaway here should be the following. You can refer to the [`pyproject.toml`]({{< relref "pyproject#exclude-and-include" >}})
documentation for information on each of the relevant sections.

1. Include your build outputs in your wheel.
2. Exclude your build inputs from your wheel.
3. Include your build inputs to your source distribution.

{{< /step >}}

{{< /steps >}}

## Example Snippets

### Cython

{{< tabs tabTotal="3" tabID1="cython-pyproject" tabName1="pyproject.toml" tabID2="cython-build-script" tabName2="build-extension.py" tabID3="cython-src-tree" tabName3="Source Tree">}}

{{< tab tabID="cython-pyproject" >}}

```toml
[build-system]
requires = ["poetry-core", "cython", "setuptools"]
build-backend = "poetry.core.masonry.api"

[tool.poetry]
...
packages = [
    { include = "package", from = "src"},
]
include = [
    { path = "src/package/**/*.so", format = "wheel" },
]

[tool.poetry.build]
script = "scripts/build-extension.py"
```

{{< /tab >}}

{{< tab tabID="cython-build-script" >}}

```py
from __future__ import annotations

import os
import shutil

from pathlib import Path

from Cython.Build import cythonize
from setuptools import Distribution
from setuptools import Extension
from setuptools.command.build_ext import build_ext


COMPILE_ARGS = ["-march=native", "-O3", "-msse", "-msse2", "-mfma", "-mfpmath=sse"]
LINK_ARGS = []
INCLUDE_DIRS = []
LIBRARIES = ["m"]


def build() -> None:
    extensions = [
        Extension(
            "*",
            ["src/package/*.pyx"],
            extra_compile_args=COMPILE_ARGS,
            extra_link_args=LINK_ARGS,
            include_dirs=INCLUDE_DIRS,
            libraries=LIBRARIES,
        )
    ]
    ext_modules = cythonize(
        extensions,
        include_path=INCLUDE_DIRS,
        compiler_directives={"binding": True, "language_level": 3},
    )

    distribution = Distribution({
        "name": "package",
        "ext_modules": ext_modules
    })

    cmd = build_ext(distribution)
    cmd.ensure_finalized()
    cmd.run()

    # Copy built extensions back to the project
    for output in cmd.get_outputs():
        output = Path(output)
        relative_extension = Path("src") / output.relative_to(cmd.build_lib)

        shutil.copyfile(output, relative_extension)
        mode = os.stat(relative_extension).st_mode
        mode |= (mode & 0o444) >> 2
        os.chmod(relative_extension, mode)


if __name__ == "__main__":
    build()
```

{{< /tab >}}

{{< tab tabID="cython-src-tree" >}}

```
scripts/
└── build-extension.py
src/
└── package
    ├── example.pyx
    └── __init__.py
```

{{< /tab >}}

{{< /tabs >}}

### Meson

{{< tabs tabTotal="2" tabID1="meson-pyproject" tabName1="pyproject.toml" tabID2="meson-build-script" tabName2="build-extension.py">}}

{{< tab tabID="meson-pyproject" >}}

```toml
[tool.poetry.build]
script = "build-extension.py"

[build-system]
requires = ["poetry-core", "meson"]
build-backend = "poetry.core.masonry.api"
```

{{< /tab >}}

{{< tab tabID="meson-build-script" >}}

```py
from __future__ import annotations

import subprocess

from pathlib import Path


def meson(*args):
    subprocess.call(["meson", *args])


def build():
    build_dir = Path(__file__).parent.joinpath("build")
    build_dir.mkdir(parents=True, exist_ok=True)

    meson("setup", build_dir.as_posix())
    meson("compile", "-C", build_dir.as_posix())
    meson("install", "-C", build_dir.as_posix())


if __name__ == "__main__":
    build()
```

{{< /tab >}}

{{< /tabs >}}

### Maturin

{{< tabs tabTotal="2" tabID1="maturin-pyproject" tabName1="pyproject.toml" tabID2="maturin-build-script" tabName2="build-extension.py">}}

{{< tab tabID="maturin-pyproject" >}}

```toml
[tool.poetry.build]
script = "build-extension.py"

[build-system]
requires = ["poetry-core", "maturin"]
build-backend = "poetry.core.masonry.api"
```

{{< /tab >}}

{{< tab tabID="maturin-build-script" >}}

```py
import os
import shlex
import shutil
import subprocess
import zipfile

from pathlib import Path


def maturin(*args):
    subprocess.call(["maturin", *list(args)])


def build():
    build_dir = Path(__file__).parent.joinpath("build")
    build_dir.mkdir(parents=True, exist_ok=True)

    wheels_dir = Path(__file__).parent.joinpath("target/wheels")
    if wheels_dir.exists():
        shutil.rmtree(wheels_dir)

    cargo_args = []
    if os.getenv("MATURIN_BUILD_ARGS"):
        cargo_args = shlex.split(os.getenv("MATURIN_BUILD_ARGS", ""))

    maturin("build", "-r", *cargo_args)

    # We won't use the wheel built by maturin directly since
    # we want Poetry to build it but, we need to retrieve the
    # compiled extensions from the maturin wheel.
    wheel = next(iter(wheels_dir.glob("*.whl")))
    with zipfile.ZipFile(wheel.as_posix()) as whl:
        whl.extractall(wheels_dir.as_posix())

        for extension in wheels_dir.rglob("**/*.so"):
            shutil.copyfile(extension, Path(__file__).parent.joinpath(extension.name))

    shutil.rmtree(wheels_dir)


if __name__ == "__main__":
    build()
```

{{< /tab >}}

{{< /tabs >}}

## FAQ
### When is my build script executed?
If your project uses a build script, it is run implicitly in the following scenarios.

1. When `poetry install` is run, it is executed prior to installing the project's root package.
2. When `poetry build` is run, it is executed prior to building distributions.
3. When a PEP 517 build is triggered from source or sdist by another build frontend.

### How does Poetry ensure my build script's dependencies are met?
Prior to executing the build script, Poetry creates a temporary virtual environment with your project's active Python
version and then installs all dependencies specified under `build-system.requires` into this environment. It should be
noted that no packages will be present in this environment at the time of creation.

### Can I store the build script in a subdirectory?
Yes you can. If storing the script in a subdirectory, your `pyproject.toml` might look something like this.

```toml
[tool.poetry]
...
packages = [
    { include = "package", from = "src"}
]
include = [
    { path = "src/package/**/*.so", format = "wheel" },
]

[tool.poetry.build]
script = "scripts/build-extension.py"
```
