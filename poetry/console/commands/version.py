import re

from .command import Command


class VersionCommand(Command):
    """
    Bumps the version of the project.

    version
        { version=patch }
    """

    help = """\
The version command bumps the version of the project
and writes the new version back to <comment>pyproject.toml</>.

The new version should ideally be a valid semver string or a valid bump rule:
patch, minor, major, prepatch, preminor, premajor, prerelease.
"""

    RESERVED = {
        'major', 'minor', 'patch',
        'premajor', 'preminor', 'prepatch',
        'prerelease'
    }

    def handle(self):
        version = self.argument('version')

        if version in self.RESERVED:
            version = self.increment_version(
                self.poetry.package.pretty_version, version
            )

        self.line(
            'Bumping version from <comment>{}</> to <info>{}</>'.format(
                self.poetry.package.pretty_version, version
            )
        )

        content = self.poetry.file.read()
        poetry_content = content['tool']['poetry']
        poetry_content['version'] = version

        self.poetry.file.write(content)

    def increment_version(self, version, rule):
        from poetry.semver.version_parser import VersionParser

        parser = VersionParser()
        version_regex = (
            'v?(\d+)(?:\.(\d+))?(?:\.(\d+))?(?:\.(\d+))?{}(?:\+[^\s]+)?'
        ).format(parser._modifier_regex)

        m = re.match(version_regex, version)
        if not m:
            raise ValueError(
                'The project\'s version doesn\'t seem to follow semver'
            )

        if m.group(3):
            index = 2
        elif m.group(2):
            index = 1
        else:
            index = 0

        matches = m.groups()[:index+1]
        base = '.'.join(matches)
        extra_matches = list(g or '' for g in m.groups()[4:])
        extras = version[len('.'.join(matches)):]
        increment = 1
        is_prerelease = (extra_matches[0] or extra_matches[1]) != ''
        bump_prerelease = rule in {
            'premajor', 'preminor', 'prepatch', 'prerelease'
        }
        position = -1

        if rule in {'major', 'premajor'}:
            if m.group(1) != '0' or m.group(2) != '0' or not is_prerelease:
                position = 0
        elif rule in {'minor', 'preminor'}:
            if m.group(2) != '0' or not is_prerelease:
                position = 1
        elif rule in {'patch', 'prepatch'}:
            if not is_prerelease:
                position = 2
        elif rule == 'prerelease' and not is_prerelease:
            position = 2

        if position != -1:
            extra_matches[0] = None

            base = parser._manipulate_version_string(
                matches,
                position,
                increment=increment
            )

        if bump_prerelease:
            # We bump the prerelease part of the version
            sep = ''
            if not extra_matches[0]:
                extra_matches[0] = 'a'
                extra_matches[1] = '0'
                sep = ''
            else:
                if extras.startswith(('.', '_', '-')):
                    sep = extras[0]

                prerelease = extra_matches[1]
                if not prerelease:
                    prerelease = '.1'

                psep = ''
                if prerelease.startswith(('.', '-')):
                    psep = prerelease[0]
                    prerelease = prerelease[1:]

                new_prerelease = str(int(prerelease) + 1)
                extra_matches[1] = '{}{}'.format(psep, new_prerelease)

            extras = '{}{}{}{}'.format(
                sep,
                extra_matches[0],
                extra_matches[1],
                extra_matches[2]
            )
        else:
            extras = ''

        return '.'.join(base.split('.')[:max(index, position)+1]) + extras
