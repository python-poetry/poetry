import os
import tarfile

from contextlib import contextmanager

from poetry.factory import Factory
from poetry.io.null_io import NullIO
from poetry.utils._compat import Path
from poetry.utils.helpers import temporary_directory

from .builder import Builder
from .sdist import SdistBuilder
from .wheel import WheelBuilder


class CompleteBuilder(Builder):
    def build(self):
        # We start by building the tarball
        # We will use it to build the wheel
        sdist_builder = SdistBuilder(self._poetry, self._env, self._io)
        build_for_all_formats = False
        for p in self._package.packages:
            formats = p.get("format", [])
            if not isinstance(formats, list):
                formats = [formats]

            if formats and sdist_builder.format not in formats:
                build_for_all_formats = True
                break

        sdist_file = sdist_builder.build()

        self._io.write_line("")

        dist_dir = self._path / "dist"

        if build_for_all_formats:
            sdist_builder = SdistBuilder(
                self._poetry, self._env, NullIO(), ignore_packages_formats=True
            )
            with temporary_directory() as tmp_dir:
                sdist_file = sdist_builder.build(Path(tmp_dir))

                with self.unpacked_tarball(sdist_file) as tmpdir:
                    WheelBuilder.make_in(
                        Factory().create_poetry(tmpdir),
                        self._env,
                        self._io,
                        dist_dir,
                        original=self._poetry,
                    )
        else:
            with self.unpacked_tarball(sdist_file) as tmpdir:
                WheelBuilder.make_in(
                    Factory().create_poetry(tmpdir),
                    self._env,
                    self._io,
                    dist_dir,
                    original=self._poetry,
                )

    @classmethod
    @contextmanager
    def unpacked_tarball(cls, path):
        tf = tarfile.open(str(path))

        with cls.temporary_directory() as tmpdir:
            tf.extractall(tmpdir)
            files = os.listdir(tmpdir)

            assert len(files) == 1, files

            yield Path(tmpdir) / files[0]
