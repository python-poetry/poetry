from poetry.semver.constraints import Constraint


class BaseRepository:

    SEARCH_FULLTEXT = 0
    SEARCH_NAME = 1

    def __init__(self):
        self._packages = []

    @property
    def packages(self):
        return self._packages

    def has_package(self, package):
        raise NotImplementedError()

    def package(self, name, version):
        raise NotImplementedError()

    def find_packages(self, name, constraint=None):
        raise NotImplementedError()

    def search(self, query, mode=SEARCH_FULLTEXT):
        raise NotImplementedError()

    def get_dependents(self, needle,
                       constraint=None, invert=False,
                       recurse=True, packages_found=None):
        results = {}

        needles = needle
        if not isinstance(needles, list):
            needles = [needles]

        # initialize the list with the needles before any recursion occurs
        if packages_found is None:
            packages_found = needles

        # locate root package for use below
        root_package = None
        for package in self.packages:
            if isinstance(package, RootPackage):
                root_package = package
                break

        # Loop over all currently installed packages.
        for package in self.packages:
            links = package.requires

            # each loop needs its own "tree"
            # as we want to show the complete dependent set of every needle
            # without warning all the time about finding circular deps
            packages_in_tree = packages_found

            # Require-dev is only relevant for the root package
            if isinstance(package, RootPackage):
                links += package.dev_requires

            # Cross-reference all discovered links to the needles
            for link in links:
                for needle in needles:
                    if link.target == needle:
                        if (
                            constraint is None
                            or link.constraint.matches(constraint) is not invert
                        ):
                            # already displayed this node's dependencies,
                            # cutting short
                            if link.source in packages_in_tree:
                                results[link.source] = (package, link, False)
                                continue

                            packages_in_tree.append(link.source)
                            if recurse:
                                dependents = self.get_dependents(
                                    link.source, None, False, True, packages_in_tree
                                )
                            else:
                                dependents = {}

                            results[link.source] = (package, link, dependents)

            # When inverting, we need to check for conflicts
            # of the needles against installed packages
            if invert and package.name in needles:
                for link in package.conflicts:
                    for pkg in self.find_packages(link.target):
                        version = Constraint('=', pkg.version)
                        if link.constraint.matches(version) is invert:
                            results[len(results) - 1] = (package, link, False)

            # When inverting, we need to check for conflicts of the needles'
            # requirements against installed packages
            if (
                invert
                and constraint
                and package.name in needles
                and constraint.matches(Constraint('=', package.version))
            ):
                for link in package.requires:
                    for pkg in self._packages:
                        if link.target not in pkg.names:
                            continue

                        version = Constraint('=', pkg.version)
                        if not link.constraint.matches(version):
                            # if we have a root package
                            # we show the root requires as well
                            # to perhaps allow to find an issue there
                            if root_package:
                                for root_req in root_package.requires + root_package.dev_requires:
                                    if root_req.target in pkg.names and not root_req.constraint.matches(link.constraint):
                                        results[len(results) - 1] = (package, link, False)
                                        results[len(results) - 1] = (root_package, root_req, False)
                                        continue

                                    results[len(results) - 1] = (package, link, False)
                                    lnk = Link(
                                        root_package.name,
                                        link.target,
                                        None,
                                        'does not require',
                                        'but {} is installed'.format(
                                            pkg.pretty_version
                                        )
                                    )
                                    results[len(results) - 1] = (package, lnk, False)
                            else:
                                results[len(results) - 1] = (package, link, False)

                        continue

        return results
