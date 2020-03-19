import json
import os

from io import open

from .license import License
from .updater import Updater


_licenses = None


def license_by_id(identifier):
    if _licenses is None:
        load_licenses()

    id = identifier.lower()

    if id not in _licenses:
        if not identifier:
            raise ValueError("A license identifier is required")
        return License(identifier, identifier, False, False)

    return _licenses[id]


def load_licenses():
    global _licenses

    _licenses = {}

    licenses_file = os.path.join(os.path.dirname(__file__), "data", "licenses.json")

    with open(licenses_file, encoding="utf-8") as f:
        data = json.loads(f.read())

    for name, license_info in data.items():
        license = License(name, license_info[0], license_info[1], license_info[2])
        _licenses[name.lower()] = license

        full_name = license_info[0].lower()
        if full_name in _licenses:
            existing_license = _licenses[full_name]
            if not existing_license.is_deprecated:
                continue

        _licenses[full_name] = license

    # Add a Proprietary license for non-standard licenses
    _licenses["proprietary"] = License("Proprietary", "Proprietary", False, False)


if __name__ == "__main__":
    updater = Updater()
    updater.dump()
