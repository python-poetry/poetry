from distutils.core import Extension


extensions = [Extension("extended.extended", ["extended/extended.c"])]


def build(setup_kwargs):
    setup_kwargs.update({"ext_modules": extensions})
