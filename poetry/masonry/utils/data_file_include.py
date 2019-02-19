from .include import Include

# noinspection PyProtectedMember
from poetry.utils._compat import Path


class DataFileInclude(Include):
    def __init__(
        self, base, include, data_file_path_prefix
    ):  # type: (Path, str, str) -> None
        super(DataFileInclude, self).__init__(base, include)
        self._data_file_path_prefix = data_file_path_prefix

    @property
    def data_file_path_prefix(self):  # type: () -> str
        return self._data_file_path_prefix
