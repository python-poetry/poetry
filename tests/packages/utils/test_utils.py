from poetry.packages.utils.utils import convert_markers
from poetry.version.markers import parse_marker


def test_convert_markers():
    marker = parse_marker(
        'sys_platform == "win32" and python_version < "3.6" '
        'or sys_platform == "win32" and python_version < "3.6" and python_version >= "3.3" '
        'or sys_platform == "win32" and python_version < "3.3"'
    )

    converted = convert_markers(marker)

    assert converted["python_version"] == [
        [("<", "3.6")],
        [("<", "3.6"), (">=", "3.3")],
        [("<", "3.3")],
    ]

    marker = parse_marker('python_version == "2.7" or python_version == "2.6"')
    converted = convert_markers(marker)

    assert converted["python_version"] == [[("==", "2.7")], [("==", "2.6")]]
