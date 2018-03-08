from poetry.semver.constraints import MultiConstraint
from poetry.utils.helpers import canonicalize_name


class Metadata:

    metadata_version = '1.2'
    # version 1.0
    name = None
    version = None
    platforms = ()
    supported_platforms = ()
    summary = None
    description = None
    keywords = None
    home_page = None
    download_url = None
    author = None
    author_email = None
    license = None
    # version 1.1
    classifiers = ()
    requires = ()
    provides = ()
    obsoletes = ()
    # version 1.2
    maintainer = None
    maintainer_email = None
    requires_python = None
    requires_external = ()
    requires_dist = ()
    provides_dist = ()
    obsoletes_dist = ()
    project_urls = ()

    @classmethod
    def from_package(cls, package) -> 'Metadata':
        meta = cls()

        meta.name = canonicalize_name(package.name)
        meta.version = package.version
        meta.summary = package.description
        meta.description = package.readme
        meta.keywords = ','.join(package.keywords)
        meta.home_page = package.homepage or package.repository_url
        meta.author = package.author_name
        meta.author_email = package.author_email
        meta.license = package.license
        meta.classifiers = package.classifiers

        # Version 1.2
        meta.maintainer = meta.author
        meta.maintainer_email = meta.author_email
        meta.requires_python = package.python_constraint
        meta.requires_dist = [d.to_pep_508() for d in package.requires]

        # Requires python
        constraint = package.python_constraint
        if isinstance(constraint, MultiConstraint):
            python_requires = ','.join(
                [str(c).replace(' ', '') for c in constraint.constraints]
            )
        else:
            python_requires = str(constraint).replace(' ', '')

        meta.requires_python = python_requires

        return meta
