import pytest

from poetry.spdx import license_by_id


def test_license_by_id():
    license = license_by_id("MIT")

    assert license.id == "MIT"
    assert license.name == "MIT License"
    assert license.is_osi_approved
    assert not license.is_deprecated

    license = license_by_id("LGPL-3.0-or-later")

    assert license.id == "LGPL-3.0-or-later"
    assert license.name == "GNU Lesser General Public License v3.0 or later"
    assert license.is_osi_approved
    assert not license.is_deprecated


def test_license_by_id_is_case_insensitive():
    license = license_by_id("mit")

    assert license.id == "MIT"

    license = license_by_id("miT")

    assert license.id == "MIT"


def test_license_by_id_with_full_name():
    license = license_by_id("GNU Lesser General Public License v3.0 or later")

    assert license.id == "LGPL-3.0-or-later"
    assert license.name == "GNU Lesser General Public License v3.0 or later"
    assert license.is_osi_approved
    assert not license.is_deprecated


def test_license_by_id_invalid():
    with pytest.raises(ValueError):
        license_by_id("invalid")
