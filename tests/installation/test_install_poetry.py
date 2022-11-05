import re
import typing
from unittest.mock import MagicMock, patch
import importlib
import unittest


module = importlib.import_module("install-poetry")


class InstallPoetryTestCase(unittest.TestCase):
    def setUp(self):
        self.__patchers = []

        self.__patchers.append(patch("install-poetry.Installer"))
        self.__mock_installer_cls = self.__patchers[-1].start()
        self.__installer = MagicMock()
        self.__mock_installer_cls.return_value = self.__installer

        self.__patchers.append(patch("install-poetry.argparse.ArgumentParser"))
        self.__mock_argument_parser_cls = self.__patchers[-1].start()
        self.__parser = MagicMock()
        self.__args = MagicMock()
        self.__args.version = None
        self.__args.preview = False
        self.__args.force = False
        self.__args.accept_all = False
        self.__args.path = None
        self.__args.git = None
        self.__args.uninstall = False
        self.__mock_argument_parser_cls.return_value = self.__parser
        self.__parser.parse_args.return_value = self.__args

        self.__patchers.append(patch("install-poetry.os"))
        self.__mock_os = self.__patchers[-1].start()
        self.__mock_os.getenv.side_effect = self.__getenv
        self.__env = {}

        self.__patchers.append(patch("install-poetry.colorize"))
        self.__mock_colorize = self.__patchers[-1].start()
        self.__mock_colorize.side_effect = self.__colorize
        self.__messages = []

        self.__patchers.append(patch("install-poetry.tempfile"))
        self.__mock_tempfile = self.__patchers[-1].start()
        self.__mock_tempfile.mkstemp.side_effect = self.__mkstemp
        self.__tmp_file = None

    def tearDown(self):
        for patcher in self.__patchers:
            patcher.stop()

    def test_install_poetry_main__happy(self):
        self.__installer.run.return_value = 0

        return_code = module.main()

        self.__mock_installer_cls.assert_called_with(
            version=None,
            preview=False,
            force=False,
            accept_all=True,
            path=None,
            git=None,
        )

        self.__installer.uninstall.assert_not_called()

        self.assertEqual(return_code, 0)

    def test_install_poetry_main__default_install_error(self):
        self.__installer.run.side_effect = [
            module.PoetryInstallationError(1, "a fake poetry installation error")
        ]

        return_code = module.main()

        self.__assert_no_matching_message("error", re.compile("a fake poetry installation error"))
        self.__assert_any_matching_message("error", re.compile(f"See {self.__tmp_file} for error logs"))

        self.assertEqual(return_code, 1)

    def test_install_poetry_main__log_stderr(self):
        self.__env["POETRY_LOG_STDERR"] = "1"
        self.__installer.run.side_effect = [
            module.PoetryInstallationError(1, "a fake poetry installation error")
        ]

        return_code = module.main()

        self.__assert_no_matching_message("info", re.compile("CI environment detected"))
        self.__assert_any_matching_message("error", re.compile("a fake poetry installation error"))

        self.assertEqual(return_code, 1)

    def test_install_poetry_main__ci(self):
        self.__env["CI"] = "1"
        self.__installer.run.side_effect = [
            module.PoetryInstallationError(1, "a fake poetry installation error")
        ]

        return_code = module.main()

        self.__assert_any_matching_message("info", re.compile("CI environment detected"))
        self.__assert_any_matching_message("error", re.compile("a fake poetry installation error"))

        self.assertEqual(return_code, 1)

    def __colorize(self, severity: str, message: str) -> str:
        self.__messages.append((severity, message))
        return f"{severity}:{message}"

    def __getenv(self, key: str, default: typing.Optional[str] = None) -> typing.Optional[str]:
        return self.__env.get(key, default)

    def __mkstemp(self, suffix="suffix", prefix="prefix", dir=None, text=None):
        self.__tmp_file = f"{prefix}unitest{suffix}"
        return None, self.__tmp_file

    def __assert_any_matching_message(self, severity: str, pattern: re.Pattern):
        self.assertGreater(self.__count_matching_message(severity, pattern), 0)

    def __assert_no_matching_message(self, severity: str, pattern: re.Pattern):
        self.assertEqual(self.__count_matching_message(severity, pattern), 0)

    def __count_matching_message(self, severity: str, pattern: re.Pattern):
        return len([message for message in self.__messages if severity == message[0] and pattern.search(message[1])])
