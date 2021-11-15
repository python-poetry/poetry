import re


wheel_file_re = re.compile(
    r"^(?P<namever>(?P<name>.+?)-(?P<ver>\d.*?))"
    r"(-(?P<build>\d.*?))?"
    r"-(?P<pyver>.+?)"
    r"-(?P<abi>.+?)"
    r"-(?P<plat>.+?)"
    r"\.whl|\.dist-info$",
    re.VERBOSE,
)
