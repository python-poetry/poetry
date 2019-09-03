from .dependency import Dependency


class VCSDependency(Dependency):
    """
    Represents a VCS dependency
    """

    def __init__(
        self, name, vcs, source, branch=None, tag=None, rev=None, optional=False
    ):
        self._vcs = vcs
        self._source = source

        if not any([branch, tag, rev]):
            # If nothing has been specified, we assume master
            branch = "master"

        self._branch = branch
        self._tag = tag
        self._rev = rev

        super(VCSDependency, self).__init__(
            name, "*", optional=optional, allows_prereleases=True
        )

    @property
    def vcs(self):
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
    def reference(self):  # type: () -> str
        return self._branch or self._tag or self._rev

    @property
    def pretty_constraint(self):  # type: () -> str
        if self._branch:
            what = "branch"
            version = self._branch
        elif self._tag:
            what = "tag"
            version = self._tag
        else:
            what = "rev"
            version = self._rev

        return "{} {}".format(what, version)

    @property
    def base_pep_508_name(self):  # type: () -> str
        requirement = self.pretty_name

        if self.extras:
            requirement += "[{}]".format(",".join(self.extras))

        requirement += " @ {}+{}@{}".format(self._vcs, self._source, self.reference)

        return requirement

    def is_vcs(self):  # type: () -> bool
        return True

    def accepts_prereleases(self):
        return True
