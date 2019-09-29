import re


def normalize_file_permissions(st_mode):
    """
    Normalizes the permission bits in the st_mode field from stat to 644/755

    Popular VCSs only track whether a file is executable or not. The exact
    permissions can vary on systems with different umasks. Normalising
    to 644 (non executable) or 755 (executable) makes builds more reproducible.
    """
    # Set 644 permissions, leaving higher bits of st_mode unchanged
    new_mode = (st_mode | 0o644) & ~0o133
    if st_mode & 0o100:
        new_mode |= 0o111  # Executable: 644 -> 755

    return new_mode


def escape_version(version):
    """
    Escaped version in wheel filename. Doesn't exactly follow
    the escaping specification in :pep:`427#escaping-and-unicode`
    because this conflicts with :pep:`440#local-version-identifiers`.
    """
    return re.sub(r"[^\w\d.+]+", "_", version, flags=re.UNICODE)


def escape_name(name):
    """Escaped wheel name as specified in :pep:`427#escaping-and-unicode`."""
    return re.sub(r"[^\w\d.]+", "_", name, flags=re.UNICODE)
