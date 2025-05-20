from poetry.utils.logging import format_build_wheel_log

class DummyEnv:
    @property
    def marker_env(self):
        return {
            "version_info": (3, 13, 1),
            "sys_platform": "win32",
            "platform_machine": "AMD64",
        }

class DummyPackage:
    pretty_name = "demo"
    full_pretty_version = "1.2.3"

def test_format_build_wheel_log():
    env = DummyEnv()
    package = DummyPackage()
    result = format_build_wheel_log(package, env)
    print(f"result: {result}")
    print("")
    expected = (
        " <info>Building a wheel file for demo "
        "(no prebuilt wheel available for Python 3.13.1 on win32-AMD64)</info>"
    )
    print(f"expected: {expected}")
    assert result == expected