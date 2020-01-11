class Chef:
    def __init__(self, env):
        self._env = env

    def prepare(self, archive):
        return archive

    def prepare_sdist(self, archive):
        return archive

    def prepare_wheel(self, archive):
        return archive
