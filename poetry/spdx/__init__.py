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
        err = "Invalid license id: {}\nPoetry uses SPDX license identifiers: https://spdx.org/licenses/".format(
            identifier
        )

        # Covers the licenses listed as common for python packages in https://snyk.io/blog/over-10-of-python-packages-on-pypi-are-distributed-without-any-license/
        # MIT/WTFPL/Unlicense are excluded as their ids are simply their name - if someone types "mit", they've already found the license they were looking for

        common_strings = ["agpl", "lgpl", "gpl", "bsd", "apache", "mpl", "cc0"]
        for string in common_strings:
            if string in id:

                err += "\n"
                err += "Did you mean one of the following?"

                matches = sorted(
                    {
                        license.id
                        for license in _licenses.values()
                        if license.id.lower().startswith(string)
                        and not license.is_deprecated
                    }
                )

                for license in matches:
                    err += "\n * {}".format(license)

                # Don't match agpl for "gpl"
                break

        raise ValueError(err)

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
