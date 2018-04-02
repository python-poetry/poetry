"""
This script will install poetry and its dependencies
in isolation from the rest of the system.

It does, in order:

  - Downloads the latest stable version of poetry.
  - Checks if the _vendor directory is empty.
  - If the _vendor directory is not empty, empties it.
  - Installs all dependencies in the _vendor directory

This ensure that poetry will look for its dependencies inside
the _vendor directory without tampering with the base system.

Note, however, that installing poetry via pip will still work,
since if poetry does not find the dependencies in the _vendor
directory, it will look for them in the base system.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

from email.parser import Parser
from pathlib import Path
from urllib.request import urlopen


FOREGROUND_COLORS = {
    'black': 30,
    'red': 31,
    'green': 32,
    'yellow': 33,
    'blue': 34,
    'magenta': 35,
    'cyan': 36,
    'white': 37
}

BACKGROUND_COLORS = {
    'black': 40,
    'red': 41,
    'green': 42,
    'yellow': 43,
    'blue': 44,
    'magenta': 45,
    'cyan': 46,
    'white': 47
}

OPTIONS = {
    'bold': 1,
    'underscore': 4,
    'blink': 5,
    'reverse': 7,
    'conceal': 8
}


def style(fg, bg, options):
    codes = []

    if fg:
        codes.append(FOREGROUND_COLORS[fg])

    if bg:
        codes.append(BACKGROUND_COLORS[bg])

    if options:
        if not isinstance(options, (list, tuple)):
            options = [options]

        for option in options:
            codes.append(OPTIONS[option])

    return '\033[{}m'.format(';'.join(map(str, codes)))


STYLES = {
    'info': style('green', None, None),
    'comment': style('yellow', None, None),
    'error': style('white', 'red', None)
}


def is_decorated():
    return sys.stdout.isatty()


def colorize(style, text):
    if not is_decorated():
        return text

    return '{}{}\033[0m'.format(STYLES[style], text)


class Installer:

    METADATA_URL = 'https://pypi.org/pypi/poetry/json'
    VERSION_REGEX = re.compile(
        'v?(\d+)(?:\.(\d+))?(?:\.(\d+))?(?:\.(\d+))?'
        '('
        '[._-]?'
        '(?:(stable|beta|b|RC|alpha|a|patch|pl|p)((?:[.-]?\d+)*)?)?'
        '([.-]?dev)?'
        ')?'
        '(?:\+[^\s]+)?'
    )

    def __init__(self, version=None, preview=False):
        self._version = version
        self._preview = preview

    def allows_prereleases(self):
        return self._preview

    def run(self):
        print(colorize('info', 'Retrieving metadata'))
        with urlopen(self.METADATA_URL) as r:
            metadata = json.loads(r.read().decode())

        print('')
        releases = sorted(
            metadata['releases'].keys(),
            key=lambda r: (
                '.'.join(self.VERSION_REGEX.match(r).groups()[:3]),
                self.VERSION_REGEX.match(r).group(5)
            )
        )

        if self._version and self._version not in releases:
            print(colorize(
                'error', 'Version {} does not exist'.format(self._version)
            ))

            return 1

        version = self._version
        if not version:
            for release in reversed(releases):
                m = self.VERSION_REGEX.match(release)
                if m.group(5) and not self.allows_prereleases():
                    continue

                version = release

                break

        try:
            import poetry
            poetry_version = poetry.__version__
        except ImportError:
            poetry_version = None

        if poetry_version == version:
            print('Latest version already installed.')
            return 0

        print('Installing version: ' + colorize('info', version))

        return self.install(version)

    def install(self, version):
        # Most of the work will be delegated to pip
        with tempfile.TemporaryDirectory(prefix='poetry-installer-') as dir:
            dir = Path(dir)
            dist = dir / 'dist'
            print('  - Getting dependencies')
            self.call(
                'pip', 'install', 'poetry=={}'.format(version),
                '--target', str(dist)
            )

            print('  - Vendorizing dependencies')

            poetry_dir = dist / 'poetry'
            vendor_dir = poetry_dir / '_vendor'

            # Everything, except poetry itself, should
            # be put in the _vendor directory
            for file in dist.glob('*'):
                if file.name.startswith('poetry'):
                    continue

                dest = vendor_dir / file.name
                if file.is_dir():
                    shutil.copytree(str(file), str(dest))
                    shutil.rmtree(str(file))
                else:
                    shutil.copy(str(file), str(dest))
                    os.unlink(str(file))

            wheel_data = dist / 'poetry-{}.dist-info'.format(version) / 'WHEEL'
            with wheel_data.open() as f:
                wheel_data = Parser().parsestr(f.read())

            tag = wheel_data['Tag']

            # Repack everything and install
            print('  - Installing {}'.format(colorize('info', 'poetry')))

            shutil.make_archive(
                str(dir / 'poetry-{}-{}'.format(version, tag)),
                format='zip',
                root_dir=str(dist)
            )

            os.rename(
                str(dir / 'poetry-{}-{}.zip'.format(version, tag)),
                str(dir / 'poetry-{}-{}.whl'.format(version, tag)),
            )

            self.call(
                'pip', 'install',
                '--upgrade',
                '--no-deps',
                str(dir / 'poetry-{}-{}.whl'.format(version, tag))
            )

        print('')
        print(
            '{} ({}) successfully installed!'.format(
                colorize('info', 'poetry'),
                colorize('comment', version)
            )
        )

    def call(self, *args):
        return subprocess.check_output(args, stderr=subprocess.STDOUT)


def main():
    parser = argparse.ArgumentParser(
        description='Installs the latest (or given) version of poetry'
    )
    parser.add_argument(
        '-p', '--preview',
        dest='preview',
        action='store_true',
        default=False
    )
    parser.add_argument(
        '--version',
        dest='version'
    )

    args = parser.parse_args()

    installer = Installer(version=args.version, preview=args.preview)

    return installer.run()


if __name__ == '__main__':
    sys.exit(main())
