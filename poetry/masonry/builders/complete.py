import os
import tarfile

import poetry

from contextlib import contextmanager
from tempfile import TemporaryDirectory
from types import SimpleNamespace

from .builder import Builder
from .sdist import SdistBuilder
from .wheel import WheelBuilder


class CompleteBuilder(Builder):

    def build(self):
        # We start by building the tarball
        # We will use it to build the wheel
        sdist_builder = SdistBuilder(self._poetry, self._venv, self._io)
        sdist_file = sdist_builder.build()
        sdist_info = SimpleNamespace(builder=sdist_builder, file=sdist_file)

        self._io.writeln('')

        dist_dir = self._path / 'dist'
        with self.unpacked_tarball(sdist_file) as tmpdir:
            wheel_info = WheelBuilder.make_in(
                poetry.Poetry.create(tmpdir), self._venv, self._io, dist_dir,
                original=self._poetry
            )

        return SimpleNamespace(wheel=wheel_info, sdist=sdist_info)

    @classmethod
    @contextmanager
    def unpacked_tarball(cls, path):
        tf = tarfile.open(str(path))

        with TemporaryDirectory() as tmpdir:
            tf.extractall(tmpdir)
            files = os.listdir(tmpdir)

            assert len(files) == 1, files

            yield os.path.join(tmpdir, files[0])
