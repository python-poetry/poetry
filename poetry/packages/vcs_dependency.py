from .dependency import Dependency


class VCSDependency(Dependency):
    """
    Represents a VCS dependency
    """

    def __init__(self, name, vcs, source,
                 branch=None, tag=None, rev=None,
                 optional=False):
        self._vcs = vcs
        self._source = source

        if not any([branch, tag, rev]):
            # If nothing has been specified, we assume master
            branch = 'master'

        self._branch = branch
        self._tag = tag
        self._rev = rev
        
        super(VCSDependency, self).__init__(name, '*', optional=optional)

    @property
    def vcs(self) -> str:
        return self._vcs

    @property
    def source(self):
        return self._source

    @property
    def branch(self):
        return self._branch

    @property
    def tag(self):
        return self._tag

    @property
    def rev(self):
        return self._rev

    @property
    def reference(self) -> str:
        return self._branch or self._tag or self._rev

    @property
    def pretty_constraint(self) -> str:
        if self._branch:
            what = 'branch'
            version = self._branch
        elif self._tag:
            what = 'tag'
            version = self._tag
        else:
            what = 'rev'
            version = self._rev

        return f'{what} {version}'

    def is_vcs(self) -> bool:
        return True

    def accepts_prereleases(self):
        return True
