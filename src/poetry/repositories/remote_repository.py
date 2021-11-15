from .repository import Repository


class RemoteRepository(Repository):
    def __init__(self, url: str) -> None:
        self._url = url

        super().__init__()

    @property
    def url(self) -> str:
        return self._url

    @property
    def authenticated_url(self) -> str:
        return self._url
