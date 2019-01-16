from poetry.utils._compat import Path

from .dependency import Dependency


class UrlDependency(Dependency):
    def __init__(
        self,
        name,
        url,  # type: Path
        category="main",  # type: str
        optional=False,  # type: bool
    ):
        self._url = url

        super(UrlDependency, self).__init__(
            name, "*", category=category, optional=optional, allows_prereleases=True
        )

    @property
    def url(self):
        return self._url

    def is_url(self):
        return True
