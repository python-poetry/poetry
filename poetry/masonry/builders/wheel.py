from __future__ import unicode_literals

import contextlib
import hashlib
import os
import re
import tempfile
import shutil
import stat
import zipfile

from base64 import urlsafe_b64encode
from io import StringIO
from typing import Set

from poetry.__version__ import __version__
from poetry.semver import parse_constraint
from poetry.utils._compat import decode

from ..utils.helpers import normalize_file_permissions
from ..utils.package_include import PackageInclude
from ..utils.tags import get_abbr_impl
from ..utils.tags import get_abi_tag
from ..utils.tags import get_impl_ver
from ..utils.tags import get_platform
from .builder import Builder


wheel_file_template = """\
Wheel-Version: 1.0
Generator: poetry {version}
Root-Is-Purelib: {pure_lib}
Tag: {tag}
"""


class WheelBuilder(Builder):
    def __init__(self, poetry, env, io, target_dir=None, original=None):
        super(WheelBuilder, self).__init__(poetry, env, io)

        self._records = []
        self._original_path = self._path
        self._target_dir = target_dir or (self._poetry.file.parent / "dist")
        if original:
            self._original_path = original.file.parent

    @classmethod
    def make_in(cls, poetry, env, io, directory=None, original=None):
        wb = WheelBuilder(poetry, env, io, target_dir=directory, original=original)
        wb.build()

        return wb.wheel_filename

    @classmethod
    def make(cls, poetry, env, io):
        """Build a wheel in the dist/ directory, and optionally upload it."""
        cls.make_in(poetry, env, io)

    def build(self):
        self._io.writeln(" - Building <info>wheel</info>")

        dist_dir = self._target_dir
        if not dist_dir.exists():
            dist_dir.mkdir()

        (fd, temp_path) = tempfile.mkstemp(suffix=".whl")

        with zipfile.ZipFile(
            os.fdopen(fd, "w+b"), mode="w", compression=zipfile.ZIP_DEFLATED
        ) as zip_file:
            self._copy_module(zip_file)
            self._build(zip_file)
            self._write_metadata(zip_file)
            self._write_record(zip_file)

        wheel_path = dist_dir / self.wheel_filename
        if wheel_path.exists():
            wheel_path.unlink()
        shutil.move(temp_path, str(wheel_path))

        self._io.writeln(" - Built <fg=cyan>{}</>".format(self.wheel_filename))

    def _build(self, wheel):
        if self._package.build:
            setup = self._path / "setup.py"

            # We need to place ourselves in the temporary
            # directory in order to build the package
            current_path = os.getcwd()
            try:
                os.chdir(str(self._path))
                self._env.run(
                    "python", str(setup), "build", "-b", str(self._path / "build")
                )
            finally:
                os.chdir(current_path)

            build_dir = self._path / "build"
            lib = list(build_dir.glob("lib.*"))
            if not lib:
                # The result of building the extensions
                # does not exist, this may due to conditional
                # builds, so we assume that it's okay
                return

            lib = lib[0]
            excluded = self.find_excluded_files()
            for pkg in lib.glob("**/*"):
                if pkg.is_dir() or pkg in excluded:
                    continue

                rel_path = str(pkg.relative_to(lib))

                if rel_path in wheel.namelist():
                    continue

                self._io.writeln(
                    " - Adding: <comment>{}</comment>".format(rel_path),
                    verbosity=self._io.VERBOSITY_VERY_VERBOSE,
                )

                self._add_file(wheel, pkg, rel_path)

    def _copy_module(self, wheel):
        excluded = self.find_excluded_files()
        to_add = []

        for include in self._module.includes:
            include.refresh()

            for file in include.elements:
                if "__pycache__" in str(file):
                    continue

                if file.is_dir():
                    continue

                if isinstance(include, PackageInclude) and include.source:
                    rel_file = file.relative_to(include.base)
                else:
                    rel_file = file.relative_to(self._path)

                if file in excluded:
                    continue

                if file.suffix == ".pyc":
                    continue

                if (file, rel_file) in to_add:
                    # Skip duplicates
                    continue

                self._io.writeln(
                    " - Adding: <comment>{}</comment>".format(str(file)),
                    verbosity=self._io.VERBOSITY_VERY_VERBOSE,
                )
                to_add.append((file, rel_file))

        # Walk the files and compress them,
        # sorting everything so the order is stable.
        for full_path, rel_path in sorted(to_add, key=lambda x: x[1]):
            self._add_file(wheel, full_path, rel_path)

    def _write_metadata(self, wheel):
        if (
            "scripts" in self._poetry.local_config
            or "plugins" in self._poetry.local_config
        ):
            with self._write_to_zip(wheel, self.dist_info + "/entry_points.txt") as f:
                self._write_entry_points(f)

        for base in ("COPYING", "LICENSE"):
            for path in sorted(self._path.glob(base + "*")):
                self._add_file(wheel, path, "%s/%s" % (self.dist_info, path.name))

        with self._write_to_zip(wheel, self.dist_info + "/WHEEL") as f:
            self._write_wheel_file(f)

        with self._write_to_zip(wheel, self.dist_info + "/METADATA") as f:
            self._write_metadata_file(f)

    def _write_record(self, wheel):
        # Write a record of the files in the wheel
        with self._write_to_zip(wheel, self.dist_info + "/RECORD") as f:
            for path, hash, size in self._records:
                f.write("{},sha256={},{}\n".format(path, hash, size))
            # RECORD itself is recorded with no hash or size
            f.write(self.dist_info + "/RECORD,,\n")

    def find_excluded_files(self):  # type: () -> Set
        # Checking VCS
        return set()

    @property
    def dist_info(self):  # type: () -> str
        return self.dist_info_name(self._package.name, self._meta.version)

    @property
    def wheel_filename(self):  # type: () -> str
        return "{}-{}-{}.whl".format(
            re.sub(r"[^\w\d.]+", "_", self._package.pretty_name, flags=re.UNICODE),
            re.sub(r"[^\w\d.]+", "_", self._meta.version, flags=re.UNICODE),
            self.tag,
        )

    def supports_python2(self):
        return self._package.python_constraint.allows_any(
            parse_constraint(">=2.0.0 <3.0.0")
        )

    def dist_info_name(self, distribution, version):  # type: (...) -> str
        escaped_name = re.sub(r"[^\w\d.]+", "_", distribution, flags=re.UNICODE)
        escaped_version = re.sub(r"[^\w\d.]+", "_", version, flags=re.UNICODE)

        return "{}-{}.dist-info".format(escaped_name, escaped_version)

    @property
    def tag(self):
        if self._package.build:
            platform = get_platform().replace(".", "_").replace("-", "_")
            impl_name = get_abbr_impl(self._env)
            impl_ver = get_impl_ver(self._env)
            impl = impl_name + impl_ver
            abi_tag = str(get_abi_tag(self._env)).lower()
            tag = (impl, abi_tag, platform)
        else:
            platform = "any"
            if self.supports_python2():
                impl = "py2.py3"
            else:
                impl = "py3"

            tag = (impl, "none", platform)

        return "-".join(tag)

    def _add_file(self, wheel, full_path, rel_path):
        full_path, rel_path = str(full_path), str(rel_path)
        if os.sep != "/":
            # We always want to have /-separated paths in the zip file and in
            # RECORD
            rel_path = rel_path.replace(os.sep, "/")

        zinfo = zipfile.ZipInfo(rel_path)

        # Normalize permission bits to either 755 (executable) or 644
        st_mode = os.stat(full_path).st_mode
        new_mode = normalize_file_permissions(st_mode)
        zinfo.external_attr = (new_mode & 0xFFFF) << 16  # Unix attributes

        if stat.S_ISDIR(st_mode):
            zinfo.external_attr |= 0x10  # MS-DOS directory flag

        hashsum = hashlib.sha256()
        with open(full_path, "rb") as src:
            while True:
                buf = src.read(1024 * 8)
                if not buf:
                    break
                hashsum.update(buf)

            src.seek(0)
            wheel.writestr(zinfo, src.read(), compress_type=zipfile.ZIP_DEFLATED)

        size = os.stat(full_path).st_size
        hash_digest = urlsafe_b64encode(hashsum.digest()).decode("ascii").rstrip("=")

        self._records.append((rel_path, hash_digest, size))

    @contextlib.contextmanager
    def _write_to_zip(self, wheel, rel_path):
        sio = StringIO()
        yield sio

        # The default is a fixed timestamp rather than the current time, so
        # that building a wheel twice on the same computer can automatically
        # give you the exact same result.
        date_time = (2016, 1, 1, 0, 0, 0)
        zi = zipfile.ZipInfo(rel_path, date_time)
        zi.external_attr = (0o644 & 0xFFFF) << 16  # Unix attributes
        b = sio.getvalue().encode("utf-8")
        hashsum = hashlib.sha256(b)
        hash_digest = urlsafe_b64encode(hashsum.digest()).decode("ascii").rstrip("=")

        wheel.writestr(zi, b, compress_type=zipfile.ZIP_DEFLATED)
        self._records.append((rel_path, hash_digest, len(b)))

    def _write_entry_points(self, fp):
        """
        Write entry_points.txt.
        """
        entry_points = self.convert_entry_points()

        for group_name in sorted(entry_points):
            fp.write("[{}]\n".format(group_name))
            for ep in sorted(entry_points[group_name]):
                fp.write(ep.replace(" ", "") + "\n")

            fp.write("\n")

    def _write_wheel_file(self, fp):
        fp.write(
            wheel_file_template.format(
                version=__version__,
                pure_lib="true" if self._package.build is None else "false",
                tag=self.tag,
            )
        )

    def _write_metadata_file(self, fp):
        """
        Write out metadata in the 2.x format (email like)
        """
        fp.write(decode(self.get_metadata_content()))
