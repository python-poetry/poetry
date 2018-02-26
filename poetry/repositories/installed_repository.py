from pip.commands.freeze import freeze
from poetry.packages import Package

from .repository import Repository


class InstalledRepository(Repository):

    def __init__(self, packages=None):
        super(InstalledRepository, self).__init__(packages)
