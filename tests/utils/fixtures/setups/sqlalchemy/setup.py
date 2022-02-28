from __future__ import annotations

import os
import platform
import re
import sys

from distutils.command.build_ext import build_ext
from distutils.errors import CCompilerError
from distutils.errors import DistutilsExecError
from distutils.errors import DistutilsPlatformError

from setuptools import Distribution as _Distribution
from setuptools import Extension
from setuptools import find_packages
from setuptools import setup
from setuptools.command.test import test as TestCommand


cmdclass = {}

cpython = platform.python_implementation() == "CPython"

ext_modules = [
    Extension(
        "sqlalchemy.cprocessors", sources=["lib/sqlalchemy/cextension/processors.c"]
    ),
    Extension(
        "sqlalchemy.cresultproxy", sources=["lib/sqlalchemy/cextension/resultproxy.c"]
    ),
    Extension("sqlalchemy.cutils", sources=["lib/sqlalchemy/cextension/utils.c"]),
]

ext_errors = (CCompilerError, DistutilsExecError, DistutilsPlatformError)
if sys.platform == "win32":
    # 2.6's distutils.msvc9compiler can raise an IOError when failing to
    # find the compiler
    ext_errors += (IOError,)


class BuildFailed(Exception):
    def __init__(self):
        self.cause = sys.exc_info()[1]  # work around py 2/3 different syntax


class ve_build_ext(build_ext):
    # This class allows C extension building to fail.

    def run(self):
        try:
            build_ext.run(self)
        except DistutilsPlatformError:
            raise BuildFailed()

    def build_extension(self, ext):
        try:
            build_ext.build_extension(self, ext)
        except ext_errors:
            raise BuildFailed()
        except ValueError:
            # this can happen on Windows 64 bit, see Python issue 7511
            if "'path'" in str(sys.exc_info()[1]):  # works with both py 2/3
                raise BuildFailed()
            raise


cmdclass["build_ext"] = ve_build_ext


class Distribution(_Distribution):
    def has_ext_modules(self):
        # We want to always claim that we have ext_modules. This will be fine
        # if we don't actually have them (such as on PyPy) because nothing
        # will get built, however we don't want to provide an overally broad
        # Wheel package when building a wheel without C support. This will
        # ensure that Wheel knows to treat us as if the build output is
        # platform specific.
        return True


class PyTest(TestCommand):
    # from http://pytest.org/latest/goodpractices.html\
    # #integrating-with-setuptools-python-setup-py-test-pytest-runner
    # TODO: prefer pytest-runner package at some point, however it was
    # not working at the time of this comment.
    user_options = [("pytest-args=", "a", "Arguments to pass to py.test")]

    default_options = ["-n", "4", "-q", "--nomemory"]

    def initialize_options(self):
        TestCommand.initialize_options(self)
        self.pytest_args = ""

    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        import shlex

        # import here, cause outside the eggs aren't loaded
        import pytest

        errno = pytest.main(self.default_options + shlex.split(self.pytest_args))
        sys.exit(errno)


cmdclass["test"] = PyTest


def status_msgs(*msgs):
    print("*" * 75)
    for msg in msgs:
        print(msg)
    print("*" * 75)


with open(
    os.path.join(os.path.dirname(__file__), "lib", "sqlalchemy", "__init__.py")
) as v_file:
    VERSION = re.compile(r".*__version__ = '(.*?)'", re.S).match(v_file.read()).group(1)

with open(os.path.join(os.path.dirname(__file__), "README.rst")) as r_file:
    readme = r_file.read()


def run_setup(with_cext):
    kwargs = {}
    if with_cext:
        kwargs["ext_modules"] = ext_modules
    else:
        kwargs["ext_modules"] = []

    setup(
        name="SQLAlchemy",
        version=VERSION,
        description="Database Abstraction Library",
        author="Mike Bayer",
        author_email="mike_mp@zzzcomputing.com",
        url="http://www.sqlalchemy.org",
        packages=find_packages("lib"),
        package_dir={"": "lib"},
        license="MIT License",
        cmdclass=cmdclass,
        tests_require=["pytest >= 2.5.2", "mock", "pytest-xdist"],
        long_description=readme,
        classifiers=[
            "Development Status :: 5 - Production/Stable",
            "Intended Audience :: Developers",
            "License :: OSI Approved :: MIT License",
            "Programming Language :: Python",
            "Programming Language :: Python :: 3",
            "Programming Language :: Python :: Implementation :: CPython",
            "Programming Language :: Python :: Implementation :: PyPy",
            "Topic :: Database :: Front-Ends",
            "Operating System :: OS Independent",
        ],
        distclass=Distribution,
        extras_require={
            "mysql": ["mysqlclient"],
            "pymysql": ["pymysql"],
            "postgresql": ["psycopg2"],
            "postgresql_pg8000": ["pg8000"],
            "postgresql_psycopg2cffi": ["psycopg2cffi"],
            "oracle": ["cx_oracle"],
            "mssql_pyodbc": ["pyodbc"],
            "mssql_pymssql": ["pymssql"],
        },
        **kwargs
    )


if not cpython:
    run_setup(False)
    status_msgs(
        "WARNING: C extensions are not supported on "
        + "this Python platform, speedups are not enabled.",
        "Plain-Python build succeeded.",
    )
elif os.environ.get("DISABLE_SQLALCHEMY_CEXT"):
    run_setup(False)
    status_msgs(
        "DISABLE_SQLALCHEMY_CEXT is set; " + "not attempting to build C extensions.",
        "Plain-Python build succeeded.",
    )

else:
    try:
        run_setup(True)
    except BuildFailed as exc:
        status_msgs(
            exc.cause,
            "WARNING: The C extension could not be compiled, "
            + "speedups are not enabled.",
            "Failure information, if any, is above.",
            "Retrying the build without the C extension now.",
        )

        run_setup(False)

        status_msgs(
            "WARNING: The C extension could not be compiled, "
            + "speedups are not enabled.",
            "Plain-Python build succeeded.",
        )
