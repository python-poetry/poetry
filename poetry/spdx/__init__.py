import json
import os

from .license import License
from .updater import Updater

_licenses = None


def license_by_id(identifier):
    if _licenses is None:
        load_licenses()

    id = identifier.lower()

    if id not in _licenses:
        raise ValueError("Invalid license id: {}".format(identifier))

    return _licenses[id]


def load_licenses():
    global _licenses

    _licenses = {}

    licenses_file = os.path.join(os.path.dirname(__file__), "data", "licenses.json")

    with open(licenses_file) as f:
        data = json.loads(f.read())

    for name, license in data.items():
        _licenses[name.lower()] = License(name, license[0], license[1], license[2])


if __name__ == "__main__":
    updater = Updater()
    updater.dump()
