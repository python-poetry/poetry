from __future__ import annotations

import packaging.tags


GET_SYS_TAGS = f"""
import importlib.util
import json
import sys

from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "packaging", Path(r"{packaging.__file__}")
)
packaging = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = packaging

spec = importlib.util.spec_from_file_location(
    "packaging.tags", Path(r"{packaging.tags.__file__}")
)
packaging_tags = importlib.util.module_from_spec(spec)
spec.loader.exec_module(packaging_tags)

print(
    json.dumps([(t.interpreter, t.abi, t.platform) for t in packaging_tags.sys_tags()])
)
"""

GET_ENVIRONMENT_INFO = """\
import json
import os
import platform
import sys
import sysconfig

INTERPRETER_SHORT_NAMES = {
    "python": "py",
    "cpython": "cp",
    "pypy": "pp",
    "ironpython": "ip",
    "jython": "jy",
}


def interpreter_version():
    version = sysconfig.get_config_var("interpreter_version")
    if version:
        version = str(version)
    else:
        version = _version_nodot(sys.version_info[:2])

    return version


def _version_nodot(version):
    if any(v >= 10 for v in version):
        sep = "_"
    else:
        sep = ""

    return sep.join(map(str, version))


if hasattr(sys, "implementation"):
    info = sys.implementation.version
    iver = "{0.major}.{0.minor}.{0.micro}".format(info)
    kind = info.releaselevel
    if kind != "final":
        iver += kind[0] + str(info.serial)

    implementation_name = sys.implementation.name
else:
    iver = "0"
    implementation_name = platform.python_implementation().lower()

env = {
    "implementation_name": implementation_name,
    "implementation_version": iver,
    "os_name": os.name,
    "platform_machine": platform.machine(),
    "platform_release": platform.release(),
    "platform_system": platform.system(),
    "platform_version": platform.version(),
    "python_full_version": platform.python_version().rstrip("+"),
    "platform_python_implementation": platform.python_implementation(),
    "python_version": ".".join(platform.python_version_tuple()[:2]),
    "sys_platform": sys.platform,
    "version_info": tuple(sys.version_info),
    # Extra information
    "interpreter_name": INTERPRETER_SHORT_NAMES.get(
        implementation_name, implementation_name
    ),
    "interpreter_version": interpreter_version(),
}

print(json.dumps(env))
"""

GET_BASE_PREFIX = """\
import sys

if hasattr(sys, "real_prefix"):
    print(sys.real_prefix)
elif hasattr(sys, "base_prefix"):
    print(sys.base_prefix)
else:
    print(sys.prefix)
"""

GET_PYTHON_VERSION = """\
import sys

print('.'.join([str(s) for s in sys.version_info[:3]]))
"""

GET_PYTHON_VERSION_ONELINER = (
    "import sys; print('.'.join([str(s) for s in sys.version_info[:3]]))"
)
GET_ENV_PATH_ONELINER = "import sys; print(sys.prefix)"

GET_SYS_PATH = """\
import json
import sys

print(json.dumps(sys.path))
"""

GET_PATHS = """\
import json
import sysconfig

print(json.dumps(sysconfig.get_paths()))
"""

GET_PATHS_FOR_GENERIC_ENVS = """\
import json
import site
import sysconfig

paths = sysconfig.get_paths().copy()

if site.check_enableusersite():
    paths["usersite"] = site.getusersitepackages()
    paths["userbase"] = site.getuserbase()

print(json.dumps(paths))
"""
