import pytest

from poetry.semver.helpers import normalize_version


@pytest.mark.parametrize(
    'version,expected',
    [
        ('1.0.0', '1.0.0.0'),
        ('1.2.3.4', '1.2.3.4'),
        ('1.0.0RC1', '1.0.0.0-rc.1'),
        ('1.0.0rC13', '1.0.0.0-rc.13'),
        ('1.0.0.RC.15-dev', '1.0.0.0-rc.15'),
        ('1.0.0-rc1', '1.0.0.0-rc.1'),
        ('1.0.0.pl3', '1.0.0.0-patch.3'),
        ('1.0', '1.0.0.0'),
        ('0', '0.0.0.0'),
        ('10.4.13-b', '10.4.13.0-beta'),
        ('10.4.13-b5', '10.4.13.0-beta.5'),
        ('v1.0.0', '1.0.0.0'),
        ('2010.01', '2010.01.0.0'),
        ('2010.01.02', '2010.01.02.0'),
        ('v20100102', '20100102'),
        ('2010-01-02', '2010.01.02'),
        ('2010-01-02.5', '2010.01.02.5'),
        ('20100102-203040', '20100102.203040'),
        ('20100102203040-10', '20100102203040.10'),
        ('20100102-203040-p1', '20100102.203040-patch.1'),
        ('1.0.0-beta.5+foo', '1.0.0.0-beta.5'),
        ('0.6c', '0.6.0.0-rc'),
        ('3.0.17-20140602', '3.0.17.0-post.20140602'),
        ('3.0pre', '3.0.0.0-rc')
    ]
)
def test_normalize(version, expected):
    assert normalize_version(version) == expected


@pytest.mark.parametrize(
    'version',
    [
        '',
        '1.0.0-meh',
        '1.0.0.0.0',
        '1.0.0+foo bar',
    ]
)
def test_normalize_fail(version):
    with pytest.raises(ValueError):
        normalize_version(version)
