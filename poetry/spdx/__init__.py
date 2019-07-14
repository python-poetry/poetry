import json
import os

from io import open

from .license import License
from .updater import Updater

_licensesByShortIdentifier = None
_licensesByLongName = None


def license_by_id(identifier):
    if _licensesByShortIdentifier is None or _licensesByLongName is None:
        load_licenses()

    id = identifier.lower()

    if id not in _licensesByShortIdentifier and id not in _licensesByLongName:
        raise ValueError("Invalid license id: {}".format(identifier))

    return _licensesByShortIdentifier.get(id) or _licensesByLongName.get(id)


def load_licenses():
    global _licensesByShortIdentifier, _licensesByLongName

    _licensesByShortIdentifier = {}
    _licensesByLongName = {}

    licenses_file = os.path.join(os.path.dirname(__file__), "data", "licenses.json")

    with open(licenses_file, encoding="utf-8") as f:
        data = json.loads(f.read())

    for name, license in data.items():
        _licensesByShortIdentifier[name.lower()] = License(
            name, name=license[0], is_osi_approved=license[1], is_deprecated=license[2]
        )
        _licensesByLongName[license[0].lower()] = License(
            name, name=license[0], is_osi_approved=license[1], is_deprecated=license[2]
        )


if __name__ == "__main__":
    updater = Updater()
    updater.dump()
