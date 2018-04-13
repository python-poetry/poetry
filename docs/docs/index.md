# Introduction

Poetry is a tool for dependency management and packaging in Python.
It allows you to declare the libraries your project depends on and it will manage (install/update) them for you.


## System requirements

Poetry requires Python 2.7 or 3.4+. It is multi-platform and the goal is to make it work equally well
on Windows, Linux and OSX.


## Installation

Poetry provides a custom installer that will install `poetry` isolated
from the rest of your system by vendorizing its dependencies. This is the
recommended way of installing `poetry`.

```bash
curl -sSL https://raw.githubusercontent.com/sdispater/poetry/master/get-poetry.py | python
```

Alternatively, you can download the `get-poetry.py` file and execute it separately.

If you want to install prerelease versions, you can do so by passing `--preview` to `get-poetry.py`:

```bash
python get-poetry.py --preview
```

Similarly, if you want to install a specific version, you can use `--version`:

```bash
python get-poetry.py --version 0.7.0
```

!!!note

    Using `pip` to install `poetry` is also possible.
    
    ```bash
    pip install --user poetry
    ``` 
    
    Be aware, however, that it will also install poetry's dependencies
    which might cause conflicts.


## Updating `poetry`

Updating poetry to the latest stable version is as simple as calling the `self:update` command.

```bash
poetry self:update
```

If you want to install prerelease versions, you can use the `--preview` option.

```bash
poetry self:update --preview
```

And finally, if you want to install a spcific version you can pass it as an argument
to `self:update`.

```bash
poetry self:update 0.8.0
```
