from poetry.vcs import git

from .dependency import Dependency


class VCSDependency(Dependency):
    """
    Represents a VCS dependency
    """

    def __init__(
        self,
        name,
        vcs,
        source,
        branch=None,
        tag=None,
        rev=None,
        category="main",
        optional=False,
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
            name, "*", category=category, optional=optional, allows_prereleases=True
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
        parsed_url = git.ParsedUrl.parse(self._source)

        if self.extras:
            requirement += "[{}]".format(",".join(self.extras))

        if parsed_url.protocol is not None:
            requirement += " @ {}+{}@{}".format(self._vcs, self._source, self.reference)
        else:
            requirement += " @ {}+ssh://{}@{}".format(
                self._vcs, parsed_url.format(), self.reference
            )

        return requirement

    def is_vcs(self):  # type: () -> bool
        return True

    def accepts_prereleases(self):  # type: () -> bool
        return True

    def __str__(self):
        return "{} ({} {})".format(
            self._pretty_name, self._pretty_constraint, self._vcs
        )

    def __hash__(self):
        return hash((self._name, self._vcs, self._branch, self._tag, self._rev))
