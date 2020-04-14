import re
import shutil

import pep517.envbuild
import pep517.wrappers

from poetry.utils.helpers import temporary_directory

from ._compat import Path


try:
    from importlib.metadata import PathDistribution
except ImportError:
    from importlib_metadata import PathDistribution


class SetupReader(object):
    """
    Class that reads a setup.py file without executing it.
    """

    build_backend = "setuptools.build_meta"
    build_requires = "setuptools"

    @classmethod
    def read_from_pep517_hook(cls, directory):
        hooks = pep517.wrappers.Pep517HookCaller(
            str(directory), cls.build_backend, None
        )

        with pep517.envbuild.BuildEnvironment() as env, temporary_directory() as tmp_dir:
            env.pip_install([cls.build_requires])
            reqs = hooks.get_requires_for_build_wheel({})
            env.pip_install(reqs)

            dist_info = hooks.prepare_metadata_for_build_wheel(tmp_dir)
            distribution = PathDistribution(Path(tmp_dir) / dist_info)

            result = {
                "name": distribution.metadata["Name"],
                "version": distribution.version,
                "summary": distribution.metadata.get("Summary"),
                "install_requires": [],
                "python_requires": distribution.metadata.get("Requires-Python"),
                "extras_require": {},
            }

            if distribution.requires:
                for record in distribution.requires:
                    requirements = record.split(";", 1)
                    project_name = (
                        requirements[0]
                        .replace("(", "")
                        .replace(")", "")
                        .replace(" ", "")
                    )

                    try:
                        marker = requirements[1]
                        has_extra = re.search(r".*\bextra == ['\"](.*)['\"]", marker)

                        if has_extra:
                            extra_group = has_extra.groups()[0]
                            marker = re.sub(
                                r"(and |or )?extra == ['\"]{extra_group}['\"]".format(
                                    extra_group=extra_group
                                ),
                                "",
                                marker,
                            ).strip()

                            if marker:
                                extra_group += ":" + marker.strip(" ()")

                            if extra_group in result["extras_require"]:
                                result["extras_require"][extra_group].append(
                                    project_name
                                )
                            else:
                                result["extras_require"][extra_group] = [project_name]
                        else:
                            result["install_requires"].append(
                                "{project_name};{marker}".format(
                                    project_name=project_name, marker=marker
                                )
                            )

                    except IndexError:
                        result["install_requires"].append(project_name)

        egg_info = Path(directory).glob("*.egg-info")
        for egg in egg_info:
            shutil.rmtree(str(egg))

        return result
