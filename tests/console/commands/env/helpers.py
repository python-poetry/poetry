from pathlib import Path
from typing import Optional
from typing import Union

from poetry.core.semver import Version


def build_venv(
    path, executable=None, flags=None
):  # type: (Union[Path,str], Optional[str], bool) -> ()
    Path(path).mkdir(parents=True, exist_ok=True)


def check_output_wrapper(version=Version.parse("3.7.1")):
    def check_output(cmd, *args, **kwargs):
        if "sys.version_info[:3]" in cmd:
            return version.text
        elif "sys.version_info[:2]" in cmd:
            return "{}.{}".format(version.major, version.minor)
        else:
            return str(Path("/prefix"))

    return check_output
