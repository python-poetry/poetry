import json
import os

from functools import cmp_to_key

from poetry.mixology.contracts import SpecificationProvider
from poetry.packages import Package, Dependency

from poetry.semver import less_than
from poetry.semver.constraints import Constraint

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), 'fixtures')
FIXTURE_INDEX_DIR = os.path.join(FIXTURE_DIR, 'index')


class Index(SpecificationProvider):

    _specs_from_fixtures = {}

    def __init__(self, packages_by_name):
        self._packages = packages_by_name
        self._search_for = {}

    @property
    def packages(self):
        return self._packages

    @classmethod
    def from_fixture(cls, fixture_name):
        return cls(cls.specs_from_fixtures(fixture_name))

    @classmethod
    def specs_from_fixtures(cls, fixture_name):
        if fixture_name in cls._specs_from_fixtures:
            return cls._specs_from_fixtures[fixture_name]

        packages_by_name = {}
        with open(os.path.join(FIXTURE_INDEX_DIR, fixture_name + '.json')) as fd:
            content = json.load(fd)

            for name, releases in content.items():
                packages_by_name[name] = []

                for release in releases:
                    package = Package(
                        name,
                        release['version'],
                        release['version']
                    )

                    for dependency_name, requirements in release['dependencies'].items():
                        package.requires.append(
                            Dependency(dependency_name, requirements)
                        )

                    packages_by_name[name].append(package)

                packages_by_name[name].sort(
                    key=cmp_to_key(
                        lambda x, y:
                            0 if x.version[1] == y.version[1]
                            else -1 * int(less_than(x[1], y[1]) or -1)
                    )
                )

        return packages_by_name

    def is_requirement_satisfied_by(self, requirement, activated, package):
        if isinstance(requirement, Package):
            return requirement == package

        if package.is_prerelease() and not requirement.accepts_prereleases():
            vertex = activated.vertex_named(package.name)

            if not any([r.allows_prereleases() for r in vertex.requirements]):
                return False

        return requirement.constraint.matches(Constraint('==', package.version))

    def search_for(self, dependency):
        if dependency in self._search_for:
            return self._search_for[dependency]

        results = []
        for spec in self._packages[dependency.name]:
            if not dependency.allows_prereleases() and spec.is_prerelease():
                continue

            if dependency.constraint.matches(Constraint('==', spec.version)):
                results.append(spec)

        return results

    def name_for(self, dependency):
        return dependency.name

    def dependencies_for(self, dependency):
        return dependency.requires

    def sort_dependencies(self,
                          dependencies,
                          activated,
                          conflicts):
        return sorted(dependencies, key=lambda d: [
            0 if activated.vertex_named(d.name).payload else 1,
            0 if d.allows_prereleases() else 1,
            0 if d.name in conflicts else 1,
            0 if activated.vertex_named(d.name).payload else len(self.search_for(d))
        ])
