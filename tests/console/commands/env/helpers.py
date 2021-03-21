from pathlib import Path
from typing import Any
from typing import Union

from poetry.core.semver.version import Version


def build_venv(path: Union[Path, str], **_: Any) -> ():
    Path(path).mkdir(parents=True, exist_ok=True)


def check_output_wrapper(version=Version.parse("3.7.1")):
    def check_output(cmd, *_, **__):
        if "sys.version_info[:3]" in cmd:
            return version.text
        elif "sys.version_info[:2]" in cmd:
            return "{}.{}".format(version.major, version.minor)
        else:
            return str(Path("/prefix"))

    return check_output
