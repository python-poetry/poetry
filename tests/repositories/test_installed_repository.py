from poetry.repositories.installed_repository import InstalledRepository
from poetry.utils.env import MockEnv as BaseMockEnv


FREEZE_RESULTS = """cleo==0.6.8
-e git+https://github.com/sdispater/pendulum.git@bb058f6b78b2d28ef5d9a5e759cfa179a1a713d6#egg=pendulum
orator===0.9.8
"""


class MockEnv(BaseMockEnv):
    def run(self, bin, *args):
        if bin == "pip" and args[0] == "freeze":
            return FREEZE_RESULTS

        super(MockEnv, self).run(bin, *args)


def test_load():
    repository = InstalledRepository.load(MockEnv())

    assert len(repository.packages) == 3

    cleo = repository.packages[0]
    assert cleo.name == "cleo"
    assert cleo.version.text == "0.6.8"

    pendulum = repository.packages[1]
    assert pendulum.name == "pendulum"
    assert pendulum.version.text == "0.0.0"
    assert pendulum.source_type == "git"
    assert pendulum.source_url == "https://github.com/sdispater/pendulum.git"
    assert pendulum.source_reference == "bb058f6b78b2d28ef5d9a5e759cfa179a1a713d6"

    orator = repository.packages[2]
    assert orator.name == "orator"
    assert orator.version.text == "0.9.8"
