# Migrating

This section covers how to migrate from other common worflows to using poetry.

## virtualenv/pip
If you used plain `virtualenv` in your project before, that probably means you have a `.venv` folder at the root of your project. In that case, all you need to do is to install requirements from your `requirements.txt` file with poetry. Poetry will use the `.venv` folder of your project.

## virtualenvwrapper/pip
If you used `virtualenvwrapper` then the path is the same as with `virtualenv` with an extra step of locating the folder in which your virtual environment is stored. An alternate route would be to (if needed) set a specific python version with pyenv and create a new virtual environment [with poetry](/basic-usage/).

## pipenv
Although they might look similar, there are many differences between `pipenv` and `poetry`.

One that commonly catches people offguard is an approach to the management of virtual environment. In `pipenv` you would set it with an extra argument during init process (`--python 3.6`), while poetry approach is to let you use other tools to set a python version that you need.

The current recommended approach is to use `pyenv` to set a version of python you need and to use `poetry` from that python version to initialize your project. For details, check out [documentation](/basic-usage/#using-a-specific-python-version) on that.
