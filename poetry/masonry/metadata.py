from poetry.utils.helpers import canonicalize_name
from poetry.utils.helpers import normalize_version
from poetry.version.helpers import format_python_constraint


class Metadata:

    metadata_version = "2.1"
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
    requires_dist = []
    provides_dist = ()
    obsoletes_dist = ()
    project_urls = ()

    # Version 2.1
    description_content_type = None
    provides_extra = []

    @classmethod
    def from_package(cls, package):  # type: (...) -> Metadata
        meta = cls()

        meta.name = canonicalize_name(package.name)
        meta.version = normalize_version(package.version.text)
        meta.summary = package.description
        if package.readme:
            with package.readme.open() as f:
                meta.description = f.read()

        meta.keywords = ",".join(package.keywords)
        meta.home_page = package.homepage or package.repository_url
        meta.author = package.author_name
        meta.author_email = package.author_email

        if package.license:
            meta.license = package.license.id

        meta.classifiers = package.all_classifiers

        # Version 1.2
        meta.maintainer = meta.author
        meta.maintainer_email = meta.author_email

        # Requires python
        if not package.python_constraint.is_any():
            meta.requires_python = format_python_constraint(package.python_constraint)

        meta.requires_dist = [d.to_pep_508() for d in package.requires]

        # Version 2.1
        if package.readme:
            if package.readme.suffix == ".rst":
                meta.description_content_type = "text/x-rst"
            elif package.readme.suffix in [".md", ".markdown"]:
                meta.description_content_type = "text/markdown"
            else:
                meta.description_content_type = "text/plain"

        meta.provides_extra = [e for e in package.extras]

        return meta
