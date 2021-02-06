# This file is part of Poetry
# https://github.com/python-poetry/poetry

# Licensed under the MIT license:
# http://www.opensource.org/licenses/MIT-license
# Copyright (c) 2018 Sébastien Eustace

POETRY_RELEASE := $$(sed -n -E "s/__version__ = '(.+)'/\1/p" poetry/__version__.py)

# lists all available targets
list:
	@sh -c "$(MAKE) -p no_targets__ | \
		awk -F':' '/^[a-zA-Z0-9][^\$$#\/\\t=]*:([^=]|$$)/ {\
			split(\$$1,A,/ /);for(i in A)print A[i]\
		}' | grep -v '__\$$' | grep -v 'make\[1\]' | grep -v 'Makefile' | sort"
# required for list
no_targets__:

clean:
	@rm -rf build dist .eggs *.egg-info
	@rm -rf .benchmarks .coverage coverage.xml htmlcov report.xml .tox
	@find . -type d -name '.mypy_cache' -exec rm -rf {} +
	@find . -type d -name '__pycache__' -exec rm -rf {} +
	@find . -type d -name '*pytest_cache*' -exec rm -rf {} +
	@find . -type f -name "*.py[co]" -exec rm -rf {} +

format: clean
	@poetry run black poetry/ tests/

# install all dependencies
setup: setup-python

# test your application (tests in the tests/ directory)
test:
	@poetry run pytest --cov=poetry --cov-config .coveragerc tests/ -sq

release: build linux_release osx_release

build:
	@poetry build
	@python sonnet make release

publish:
	@poetry publish

wheel:
	@poetry build -v

linux_release:
	docker pull quay.io/pypa/manylinux2010_x86_64
	docker run --rm -i -v `pwd`:/io \
		-e PYTHON=/opt/python/cp38-cp38/bin/python \
		-e PYTHON27=/opt/python/cp27-cp27m/bin/python \
		-e PYTHON35=/opt/python/cp35-cp35m/bin/python \
		-e PYTHON36=/opt/python/cp36-cp36m/bin/python \
		-e PYTHON37=/opt/python/cp37-cp37m/bin/python \
		-e PYTHON38=/opt/python/cp38-cp38/bin/python \
		-e PYTHON39=/opt/python/cp39-cp39/bin/python \
		quay.io/pypa/manylinux2010_x86_64 sh -c "cd /io && ./make-nix-release.sh"

# run tests against all supported python versions
tox:
	@tox
