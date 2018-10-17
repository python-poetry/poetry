import os
import posixpath
import re

from poetry.packages.constraints.constraint import Constraint
from poetry.packages.constraints.multi_constraint import MultiConstraint
from poetry.packages.constraints.union_constraint import UnionConstraint
from poetry.semver import Version
from poetry.semver import VersionUnion
from poetry.version.markers import MarkerUnion
from poetry.version.markers import MultiMarker
from poetry.version.markers import SingleMarker

try:
    import urllib.parse as urlparse
except ImportError:
    import urlparse


try:
    import urllib.request as urllib2
except ImportError:
    import urllib2


BZ2_EXTENSIONS = (".tar.bz2", ".tbz")
XZ_EXTENSIONS = (".tar.xz", ".txz", ".tlz", ".tar.lz", ".tar.lzma")
ZIP_EXTENSIONS = (".zip", ".whl")
TAR_EXTENSIONS = (".tar.gz", ".tgz", ".tar")
ARCHIVE_EXTENSIONS = ZIP_EXTENSIONS + BZ2_EXTENSIONS + TAR_EXTENSIONS + XZ_EXTENSIONS
SUPPORTED_EXTENSIONS = ZIP_EXTENSIONS + TAR_EXTENSIONS

try:
    import bz2  # noqa

    SUPPORTED_EXTENSIONS += BZ2_EXTENSIONS
except ImportError:
    pass

try:
    # Only for Python 3.3+
    import lzma  # noqa

    SUPPORTED_EXTENSIONS += XZ_EXTENSIONS
except ImportError:
    pass


def path_to_url(path):
    """
    Convert a path to a file: URL.  The path will be made absolute and have
    quoted path parts.
    """
    path = os.path.normpath(os.path.abspath(path))
    url = urlparse.urljoin("file:", urllib2.pathname2url(path))
    return url


def is_url(name):
    if ":" not in name:
        return False
    scheme = name.split(":", 1)[0].lower()

    return scheme in [
        "http",
        "https",
        "file",
        "ftp",
        "ssh",
        "git",
        "hg",
        "bzr",
        "sftp",
        "svn" "ssh",
    ]


def strip_extras(path):
    m = re.match(r"^(.+)(\[[^\]]+\])$", path)
    extras = None
    if m:
        path_no_extras = m.group(1)
        extras = m.group(2)
    else:
        path_no_extras = path

    return path_no_extras, extras


def is_installable_dir(path):
    """Return True if `path` is a directory containing a setup.py file."""
    if not os.path.isdir(path):
        return False
    setup_py = os.path.join(path, "setup.py")
    if os.path.isfile(setup_py):
        return True
    return False


def is_archive_file(name):
    """Return True if `name` is a considered as an archive file."""
    ext = splitext(name)[1].lower()
    if ext in ARCHIVE_EXTENSIONS:
        return True
    return False


def splitext(path):
    """Like os.path.splitext, but take off .tar too"""
    base, ext = posixpath.splitext(path)
    if base.lower().endswith(".tar"):
        ext = base[-4:] + ext
        base = base[:-4]
    return base, ext


def group_markers(markers, or_=False):
    groups = [[]]

    for marker in markers:
        if or_:
            groups.append([])

        if isinstance(marker, (MultiMarker, MarkerUnion)):
            groups[-1].append(
                group_markers(marker.markers, isinstance(marker, MarkerUnion))
            )
        elif isinstance(marker, SingleMarker):
            lhs, op, rhs = marker.name, marker.operator, marker.value

            groups[-1].append((lhs, op, rhs))

    return groups


def convert_markers(marker):
    groups = group_markers([marker])

    requirements = {}

    def _group(_groups, or_=False):
        for group in _groups:
            if isinstance(group, tuple):
                variable, op, value = group
                group_name = str(variable)
                if group_name not in requirements:
                    requirements[group_name] = [[]]
                elif or_:
                    requirements[group_name].append([])

                or_ = False

                requirements[group_name][-1].append((str(op), str(value)))
            else:
                _group(group, or_=True)

    _group(groups)

    return requirements


def create_nested_marker(name, constraint):
    if constraint.is_any():
        return ""

    if isinstance(constraint, (MultiConstraint, UnionConstraint)):
        parts = []
        for c in constraint.constraints:
            multi = False
            if isinstance(c, (MultiConstraint, UnionConstraint)):
                multi = True

            parts.append((multi, create_nested_marker(name, c)))

        glue = " and "
        if isinstance(constraint, UnionConstraint):
            parts = ["({})".format(part[1]) if part[0] else part[1] for part in parts]
            glue = " or "
        else:
            parts = [part[1] for part in parts]

        marker = glue.join(parts)
    elif isinstance(constraint, Constraint):
        marker = '{} {} "{}"'.format(name, constraint.operator, constraint.version)
    elif isinstance(constraint, VersionUnion):
        parts = []
        for c in constraint.ranges:
            parts.append(create_nested_marker(name, c))

        glue = " or "
        parts = ["({})".format(part) for part in parts]

        marker = glue.join(parts)
    elif isinstance(constraint, Version):
        marker = '{} == "{}"'.format(name, constraint.text)
    else:
        if constraint.min is not None:
            op = ">="
            if not constraint.include_min:
                op = ">"

            version = constraint.min.text
            if constraint.max is not None:
                text = '{} {} "{}"'.format(name, op, version)

                op = "<="
                if not constraint.include_max:
                    op = "<"

                version = constraint.max

                text += ' and {} {} "{}"'.format(name, op, version)

                return text
        elif constraint.max is not None:
            op = "<="
            if not constraint.include_max:
                op = "<"

            version = constraint.max
        else:
            return ""

        marker = '{} {} "{}"'.format(name, op, version)

    return marker
