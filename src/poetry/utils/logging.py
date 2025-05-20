from poetry.core.packages.package import Package
from poetry.utils.env import Env

def format_build_wheel_log(package: Package, env: Env) -> str:
    marker_env = env.marker_env

    python_version_info = marker_env.get("version_info", ("<unknown>", "<unknown>", "<unknown>"))
    python_version = f"{python_version_info[0]}.{python_version_info[1]}.{python_version_info[2]}"
    platform = marker_env.get("sys_platform", "<unknown-platform>")
    architecture = marker_env.get("platform_machine", "<unknown-arch>")

    reason = f"no prebuilt wheel available for Python {python_version} on {platform}-{architecture}"
    return f" <info>Building a wheel file for {package.pretty_name} ({reason})</info>"
