from pip import __version__

from poetry.version import parse

if parse(__version__) >= parse('9.0.2'):
    from pip._internal.req import InstallRequirement
    from pip._internal.utils.appdirs import user_cache_dir, user_config_dir
else:
    from pip.req import InstallRequirement
    from pip.utils.appdirs import user_cache_dir, user_config_dir
