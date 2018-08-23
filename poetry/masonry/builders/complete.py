import os
import tarfile

import poetry.poetry

from contextlib import contextmanager

from .builder import Builder
from .sdist import SdistBuilder
from .wheel import WheelBuilder


class CompleteBuilder(Builder):
    def build(self):
        # We start by building the tarball
        # We will use it to build the wheel
        sdist_builder = SdistBuilder(self._poetry, self._env, self._io)
        sdist_file = sdist_builder.build()

        self._io.writeln("")

        dist_dir = self._path / "dist"
        with self.unpacked_tarball(sdist_file) as tmpdir:
            WheelBuilder.make_in(
                poetry.poetry.Poetry.create(tmpdir),
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

            yield os.path.join(tmpdir, files[0])
