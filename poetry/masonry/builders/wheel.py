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
from pathlib import Path
from types import SimpleNamespace

from poetry.__version__ import __version__
from poetry.semver.constraints import Constraint
from poetry.semver.constraints import MultiConstraint
from poetry.vcs import get_vcs
from poetry.version.helpers import format_python_constraint

from ..metadata import Metadata
from ..utils.helpers import normalize_file_permissions
from ..utils.tags import get_abbr_impl
from ..utils.tags import get_abi_tag
from ..utils.tags import get_impl_ver
from ..utils.tags import get_platform
from .builder import Builder


wheel_file_template = """\
Wheel-Version: 1.0
Generator: poetry {version}
Root-Is-Purelib: true
""".format(version=__version__)


class WheelBuilder(Builder):

    def __init__(self, poetry, venv, io, target_fp, original=None):
        super().__init__(poetry, venv, io)

        self._records = []
        self._original_path = self._path
        if original:
            self._original_path = original.file.parent

        # Open the zip file ready to write
        self._wheel_zip = zipfile.ZipFile(target_fp, 'w',
                                          compression=zipfile.ZIP_DEFLATED)

    @classmethod
    def make_in(cls, poetry, venv, io, directory, original=None) -> SimpleNamespace:
        # We don't know the final filename until metadata is loaded, so write to
        # a temporary_file, and rename it afterwards.
        (fd, temp_path) = tempfile.mkstemp(suffix='.whl',
                                           dir=str(directory))
        try:
            with open(fd, 'w+b') as fp:
                wb = WheelBuilder(poetry, venv, io, fp, original=original)
                wb.build()

            wheel_path = directory / wb.wheel_filename
            os.replace(temp_path, str(wheel_path))
        except:
            os.unlink(temp_path)
            raise

        return SimpleNamespace(builder=wb, file=wheel_path)

    @classmethod
    def make(cls, poetry, venv, io) -> SimpleNamespace:
        """Build a wheel in the dist/ directory, and optionally upload it.
            """
        dist_dir = poetry.file.parent / 'dist'
        try:
            dist_dir.mkdir()
        except FileExistsError:
            pass

        return cls.make_in(poetry, venv, io, dist_dir)

    def build(self) -> None:
        self._io.writeln(' - Building <info>wheel</info>')
        try:
            self._build()
            self.copy_module()
            self.write_metadata()
            self.write_record()
        finally:
            self._wheel_zip.close()

        self._io.writeln(f' - Built <fg=cyan>{self.wheel_filename}</>')

    def _build(self) -> None:
        if self._package.build:
            setup = self._path / 'setup.py'

            # We need to place ourselves in the temporary
            # directory in order to build the package
            current_path = os.getcwd()
            try:
                os.chdir(str(self._path))
                self._venv.run(
                    'python',
                    str(setup),
                    'build',
                    '-b', str(self._path / 'build')
                )
            finally:
                os.chdir(current_path)

            build_dir = self._path / 'build'
            lib = list(build_dir.glob('lib.*'))[0]
            for pkg in lib.glob('*'):
                shutil.rmtree(str(self._path / pkg.name))
                shutil.copytree(str(pkg), str(self._path / pkg.name))

    def copy_module(self) -> None:
        if self._module.is_package():
            files = self.find_files_to_add()

            # Walk the files and compress them,
            # sorting everything so the order is stable.
            for file in sorted(files):
                full_path = self._path / file

                # Do not include topmost files
                if full_path.relative_to(self._path) == Path(file.name):
                    continue

                self._add_file(full_path, file)
        else:
            self._add_file(str(self._module.path), self._module.path.name)

    def write_metadata(self):
        if 'scripts' in self._poetry.config or 'plugins' in self._poetry.config:
            with self._write_to_zip(self.dist_info + '/entry_points.txt') as f:
                self._write_entry_points(f)

        for base in ('COPYING', 'LICENSE'):
            for path in sorted(self._path.glob(base + '*')):
                self._add_file(path, '%s/%s' % (self.dist_info, path.name))

        with self._write_to_zip(self.dist_info + '/WHEEL') as f:
            self._write_wheel_file(f)

        with self._write_to_zip(self.dist_info + '/METADATA') as f:
            self._write_metadata_file(f)

    def write_record(self):
        # Write a record of the files in the wheel
        with self._write_to_zip(self.dist_info + '/RECORD') as f:
            for path, hash, size in self._records:
                f.write('{},sha256={},{}\n'.format(path, hash, size))
            # RECORD itself is recorded with no hash or size
            f.write(self.dist_info + '/RECORD,,\n')

    def find_excluded_files(self) -> list:
        # Checking VCS
        vcs = get_vcs(self._original_path)
        if not vcs:
            return []

        ignored = vcs.get_ignored_files()
        result = []
        for file in ignored:
            try:
                file = Path(file).absolute().relative_to(self._original_path)
            except ValueError:
                # Should only happen in tests
                continue

            result.append(file)

        return result

    @property
    def dist_info(self) -> str:
        return self.dist_info_name(self._package.name, self._package.version)

    @property
    def wheel_filename(self) -> str:
        if self._package.build:
            platform = get_platform().replace('.', '_').replace('-', '_')
            impl_name = get_abbr_impl()
            impl_ver = get_impl_ver()
            impl = impl_name + impl_ver
            abi_tag = str(get_abi_tag()).lower()
            tag = (impl, abi_tag, platform)
        else:
            platform = 'any'
            if self.supports_python2():
                impl = 'py2.py3'
            else:
                impl = 'py3'

            tag = (impl, 'none', platform)

        tag = '-'.join(tag)

        return '{}-{}-{}.whl'.format(
            re.sub("[^\w\d.]+", "_", self._package.pretty_name, flags=re.UNICODE),
            re.sub("[^\w\d.]+", "_", self._package.version, flags=re.UNICODE),
            tag
        )

    def supports_python2(self):
        return self._package.python_constraint.matches(
            MultiConstraint([
                Constraint('>=', '2.0.0'),
                Constraint('<', '3.0.0')
            ])
        )

    def dist_info_name(self, distribution, version) -> str:
        escaped_name = re.sub("[^\w\d.]+", "_", distribution, flags=re.UNICODE)
        escaped_version = re.sub("[^\w\d.]+", "_", version, flags=re.UNICODE)

        return '{}-{}.dist-info'.format(escaped_name, escaped_version)

    def _add_file(self, full_path, rel_path):
        full_path, rel_path = str(full_path), str(rel_path)
        if os.sep != '/':
            # We always want to have /-separated paths in the zip file and in
            # RECORD
            rel_path = rel_path.replace(os.sep, '/')

        zinfo = zipfile.ZipInfo.from_file(full_path, rel_path)

        # Normalize permission bits to either 755 (executable) or 644
        st_mode = os.stat(full_path).st_mode
        new_mode = normalize_file_permissions(st_mode)
        zinfo.external_attr = (new_mode & 0xFFFF) << 16  # Unix attributes

        if stat.S_ISDIR(st_mode):
            zinfo.external_attr |= 0x10  # MS-DOS directory flag

        hashsum = hashlib.sha256()
        with open(full_path, 'rb') as src, self._wheel_zip.open(zinfo,
                                                                'w') as dst:
            while True:
                buf = src.read(1024 * 8)
                if not buf:
                    break
                hashsum.update(buf)
                dst.write(buf)

        size = os.stat(full_path).st_size
        hash_digest = urlsafe_b64encode(hashsum.digest()).decode(
            'ascii').rstrip('=')

        self._records.append((rel_path, hash_digest, size))

    @contextlib.contextmanager
    def _write_to_zip(self, rel_path):
        sio = StringIO()
        yield sio

        # The default is a fixed timestamp rather than the current time, so
        # that building a wheel twice on the same computer can automatically
        # give you the exact same result.
        date_time = (2016, 1, 1, 0, 0, 0)
        zi = zipfile.ZipInfo(rel_path, date_time)
        b = sio.getvalue().encode('utf-8')
        hashsum = hashlib.sha256(b)
        hash_digest = urlsafe_b64encode(
            hashsum.digest()
        ).decode('ascii').rstrip('=')

        self._wheel_zip.writestr(zi, b, compress_type=zipfile.ZIP_DEFLATED)
        self._records.append((rel_path, hash_digest, len(b)))

    def _write_entry_points(self, fp):
        """
        Write entry_points.txt.
        """
        entry_points = self.convert_entry_points()

        for group_name in sorted(entry_points):
            fp.write('[{}]\n'.format(group_name))
            for ep in sorted(entry_points[group_name]):
                fp.write(ep.replace(' ', ''))

            fp.write('\n')

    def _write_wheel_file(self, fp):
        fp.write(wheel_file_template)

        if self.supports_python2():
            fp.write("Tag: py2-none-any\n")

        fp.write("Tag: py3-none-any\n")

    def _write_metadata_file(self, fp):
        """
        Write out metadata in the 2.x format (email like)
        """
        fp.write('Metadata-Version: 2.1\n')
        fp.write(f'Name: {self._meta.name}\n')
        fp.write(f'Version: {self._meta.version}\n')
        fp.write(f'Summary: {self._meta.summary}\n')
        fp.write(f'Home-page: {self._meta.home_page or "UNKNOWN"}\n')
        fp.write(f'License: {self._meta.license or "UNKOWN"}\n')

        # Optional fields
        if self._meta.keywords:
            fp.write(f"Keywords: {self._meta.keywords}\n")

        if self._meta.author:
            fp.write(f'Author: {self._meta.author}\n')

        if self._meta.author_email:
            fp.write(f'Author-email: {self._meta.author_email}\n')

        if self._meta.requires_python:
            fp.write(f'Requires-Python: {self._meta.requires_python}\n')

        for classifier in self._meta.classifiers:
            fp.write(f'Classifier: {classifier}\n')

        for dep in self._meta.requires_dist:
            fp.write(f'Requires-Dist: {dep}\n')

        if self._meta.description_content_type:
            fp.write(f'Description-Content-Type: '
                     f'{self._meta.description_content_type}\n')

        # TODO: Provides extra

        if self._meta.description is not None:
            fp.write('\n' + self._meta.description + '\n')
