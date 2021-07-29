import hashlib
import json
import tarfile
import tempfile
import zipfile

from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from typing import TYPE_CHECKING
from typing import List
from typing import Optional

from build import ProjectBuilder
from build.env import IsolatedEnv as BaseIsolatedEnv
from pep517.wrappers import quiet_subprocess_runner

from poetry.core.packages.utils.link import Link

from ..utils.helpers import temporary_directory
from .chooser import InvalidWheelName
from .chooser import Wheel


if TYPE_CHECKING:

    from poetry.config.config import Config
    from poetry.utils.env import Env


class IsolatedEnv(BaseIsolatedEnv):
    def __init__(self, env: "Env") -> None:
        self._env = env

    @property
    def executable(self) -> str:
        return str(self._env.python)

    @property
    def scripts_dir(self) -> str:
        return str(self._env._bin_dir)

    def install(self, requirements) -> None:
        from cleo.io.null_io import NullIO

        from poetry.core.packages.dependency import Dependency
        from poetry.core.packages.project_package import ProjectPackage
        from poetry.factory import Factory
        from poetry.installation.installer import Installer
        from poetry.packages.locker import NullLocker
        from poetry.repositories.installed_repository import InstalledRepository
        from poetry.repositories.pool import Pool
        from poetry.repositories.pypi_repository import PyPiRepository

        # We build Poetry dependencies from the requirements
        package = ProjectPackage("__root__", "0.0.0")
        package.python_versions = ".".join(str(v) for v in self._env.version_info[:3])
        for requirement in requirements:
            dependency = Dependency.create_from_pep_508(requirement)
            package.add_dependency(dependency)

        pool = Pool()
        pool.add_repository(PyPiRepository())
        installer = Installer(
            NullIO(),
            self._env,
            package,
            NullLocker(self._env.path.joinpath("poetry.lock"), {}),
            pool,
            Factory.create_config(NullIO()),
            InstalledRepository.load(self._env),
        )
        installer.update(True)
        installer.run()


class Chef:
    def __init__(self, config: "Config", env: "Env") -> None:
        self._config = config
        self._env = env
        self._cache_dir = (
            Path(config.get("cache-dir")).expanduser().joinpath("artifacts")
        )

    def prepare(self, archive: Path, output_dir: Optional[Path] = None) -> Path:
        if not self.should_prepare(archive):
            return archive

        if archive.is_dir():
            tmp_dir = tempfile.mkdtemp(prefix="poetry-chef-")

            return self._prepare(archive, Path(tmp_dir))

        return self._prepare_sdist(archive, destination=output_dir)

    def _prepare_sdist(self, archive: Path, destination: Optional[Path] = None) -> Path:
        suffix = archive.suffix

        if suffix == ".zip":
            context = zipfile.ZipFile
        else:
            context = tarfile.open

        with temporary_directory() as archive_dir:
            with context(archive.as_posix()) as archive_archive:
                archive_archive.extractall(archive_dir)

            archive_dir = Path(archive_dir)

            elements = list(archive_dir.glob("*"))

            if len(elements) == 1 and elements[0].is_dir():
                sdist_dir = elements[0]
            else:
                sdist_dir = archive_dir / archive.name.rstrip(suffix)
                if not sdist_dir.is_dir():
                    sdist_dir = archive_dir

            if destination is None:
                destination = self.get_cache_directory_for_link(Link(archive.as_uri()))

            destination.mkdir(parents=True, exist_ok=True)

            return self._prepare(
                sdist_dir,
                destination,
            )

    def _prepare(self, directory: Path, destination: Path) -> Path:
        from poetry.utils.env import EnvManager
        from poetry.utils.env import VirtualEnv

        with temporary_directory() as tmp_dir:
            EnvManager.build_venv(tmp_dir, executable=self._env.python, with_pip=True)
            venv = VirtualEnv(Path(tmp_dir))
            env = IsolatedEnv(venv)
            builder = ProjectBuilder(
                directory,
                python_executable=env.executable,
                scripts_dir=env.scripts_dir,
                runner=quiet_subprocess_runner,
            )
            env.install(builder.build_system_requires)
            env.install(
                builder.build_system_requires | builder.get_requires_for_build("wheel")
            )

            stdout = StringIO()
            with redirect_stdout(stdout):
                return Path(
                    builder.build(
                        "wheel",
                        destination.as_posix(),
                    )
                )

    def should_prepare(self, archive: Path) -> bool:
        return archive.is_dir() or not self.is_wheel(archive)

    def is_wheel(self, archive: Path) -> bool:
        return archive.suffix == ".whl"

    def get_cached_archive_for_link(self, link: Link) -> Optional[Link]:
        archives = self.get_cached_archives_for_link(link)

        if not archives:
            return link

        candidates = []
        for archive in archives:
            if not archive.is_wheel:
                candidates.append((float("inf"), archive))
                continue

            try:
                wheel = Wheel(archive.filename)
            except InvalidWheelName:
                continue

            if not wheel.is_supported_by_environment(self._env):
                continue

            candidates.append(
                (wheel.get_minimum_supported_index(self._env.supported_tags), archive),
            )

        if not candidates:
            return link

        return min(candidates)[1]

    def get_cached_archives_for_link(self, link: Link) -> List[Link]:
        cache_dir = self.get_cache_directory_for_link(link)

        archive_types = ["whl", "tar.gz", "tar.bz2", "bz2", "zip"]
        links = []
        for archive_type in archive_types:
            for archive in cache_dir.glob(f"*.{archive_type}"):
                links.append(Link(archive.as_uri()))

        return links

    def get_cache_directory_for_link(self, link: Link) -> Path:
        key_parts = {"url": link.url_without_fragment}

        if link.hash_name is not None and link.hash is not None:
            key_parts[link.hash_name] = link.hash

        if link.subdirectory_fragment:
            key_parts["subdirectory"] = link.subdirectory_fragment

        key_parts["interpreter_name"] = self._env.marker_env["interpreter_name"]
        key_parts["interpreter_version"] = "".join(
            self._env.marker_env["interpreter_version"].split(".")[:2]
        )

        key = hashlib.sha256(
            json.dumps(
                key_parts, sort_keys=True, separators=(",", ":"), ensure_ascii=True
            ).encode("ascii")
        ).hexdigest()

        split_key = [key[:2], key[2:4], key[4:6], key[6:]]

        return self._cache_dir.joinpath(*split_key)
