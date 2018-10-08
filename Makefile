# This file is part of Poetry
# https://github.com/sdispater/poetry

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

# install all dependencies
setup: setup-python

# test your application (tests in the tests/ directory)
test:
	@py.test --cov=poetry --cov-config .coveragerc tests/ -sq

release: build linux_release osx_release

build:
	@poetry build
	@python sonnet make:release

publish:
	@poetry publish

wheel:
	@poetry build -v

linux_release:
	docker pull quay.io/pypa/manylinux1_x86_64
	docker run --rm -v `pwd`:/io quay.io/pypa/manylinux1_x86_64 /io/make-linux-release.sh

# run tests against all supported python versions
tox:
	@tox
