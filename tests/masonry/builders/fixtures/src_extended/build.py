from distutils.core import Extension


extensions = [Extension("extended.extended", ["src/extended/extended.c"])]


def build(setup_kwargs):
    setup_kwargs.update({"ext_modules": extensions})
