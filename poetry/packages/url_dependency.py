from poetry.utils._compat import urlparse

from .dependency import Dependency


class URLDependency(Dependency):
    def __init__(
        self,
        name,
        url,  # type: str
        category="main",  # type: str
        optional=False,  # type: bool
    ):
        self._url = url

        parsed = urlparse.urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError("{} does not seem like a valid url".format(url))

        super(URLDependency, self).__init__(
            name, "*", category=category, optional=optional, allows_prereleases=True
        )

    @property
    def url(self):
        return self._url

    @property
    def base_pep_508_name(self):  # type: () -> str
        requirement = self.pretty_name

        if self.extras:
            requirement += "[{}]".format(",".join(self.extras))

        requirement += " @ {}".format(self._url)

        return requirement

    def is_url(self):  # type: () -> bool
        return True

    def __str__(self):
        return "{} ({} url)".format(self._pretty_name, self._pretty_constraint)

    def __hash__(self):
        return hash((self._name, self._url))
