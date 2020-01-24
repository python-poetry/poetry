import sys


try:
    from functools32 import lru_cache
except ImportError:
    from functools import lru_cache

try:
    from glob2 import glob
except ImportError:
    from glob import glob

try:
    from importlib import metadata
    import zipfile as zipp
except ImportError:
    import importlib_metadata as metadata
    import zipp

try:
    import urllib.parse as urlparse
except ImportError:
    import urlparse

try:  # Python 2
    long = long
    unicode = unicode
    basestring = basestring
except NameError:  # Python 3
    long = int
    unicode = str
    basestring = str


PY2 = sys.version_info[0] == 2
PY34 = sys.version_info >= (3, 4)
PY35 = sys.version_info >= (3, 5)
PY36 = sys.version_info >= (3, 6)

WINDOWS = sys.platform == "win32"

if PY2:
    import pipes

    shell_quote = pipes.quote
else:
    import shlex

    shell_quote = shlex.quote


if PY35:
    from pathlib import Path
else:
    from pathlib2 import Path

if not PY36:
    from collections import OrderedDict
else:
    OrderedDict = dict


if PY35:
    import subprocess as subprocess
    from subprocess import CalledProcessError
else:
    import subprocess32 as subprocess
    from subprocess32 import CalledProcessError


if PY34:
    # subprocess32 pass the calls directly to subprocess
    # on Python 3.3+ but Python 3.4 does not provide run()
    # so we backport it
    import signal

    from subprocess import PIPE
    from subprocess import Popen
    from subprocess import SubprocessError
    from subprocess import TimeoutExpired

    class CalledProcessError(SubprocessError):
        """Raised when run() is called with check=True and the process
        returns a non-zero exit status.

        Attributes:
          cmd, returncode, stdout, stderr, output
        """

        def __init__(self, returncode, cmd, output=None, stderr=None):
            self.returncode = returncode
            self.cmd = cmd
            self.output = output
            self.stderr = stderr

        def __str__(self):
            if self.returncode and self.returncode < 0:
                try:
                    return "Command '%s' died with %r." % (
                        self.cmd,
                        signal.Signals(-self.returncode),
                    )
                except ValueError:
                    return "Command '%s' died with unknown signal %d." % (
                        self.cmd,
                        -self.returncode,
                    )
            else:
                return "Command '%s' returned non-zero exit status %d." % (
                    self.cmd,
                    self.returncode,
                )

        @property
        def stdout(self):
            """Alias for output attribute, to match stderr"""
            return self.output

        @stdout.setter
        def stdout(self, value):
            # There's no obvious reason to set this, but allow it anyway so
            # .stdout is a transparent alias for .output
            self.output = value

    class CompletedProcess(object):
        """A process that has finished running.
        This is returned by run().
        Attributes:
          args: The list or str args passed to run().
          returncode: The exit code of the process, negative for signals.
          stdout: The standard output (None if not captured).
          stderr: The standard error (None if not captured).
        """

        def __init__(self, args, returncode, stdout=None, stderr=None):
            self.args = args
            self.returncode = returncode
            self.stdout = stdout
            self.stderr = stderr

        def __repr__(self):
            args = [
                "args={!r}".format(self.args),
                "returncode={!r}".format(self.returncode),
            ]
            if self.stdout is not None:
                args.append("stdout={!r}".format(self.stdout))
            if self.stderr is not None:
                args.append("stderr={!r}".format(self.stderr))
            return "{}({})".format(type(self).__name__, ", ".join(args))

        def check_returncode(self):
            """Raise CalledProcessError if the exit code is non-zero."""
            if self.returncode:
                raise CalledProcessError(
                    self.returncode, self.args, self.stdout, self.stderr
                )

    def run(*popenargs, **kwargs):
        """Run command with arguments and return a CompletedProcess instance.
        The returned instance will have attributes args, returncode, stdout and
        stderr. By default, stdout and stderr are not captured, and those attributes
        will be None. Pass stdout=PIPE and/or stderr=PIPE in order to capture them.
        If check is True and the exit code was non-zero, it raises a
        CalledProcessError. The CalledProcessError object will have the return code
        in the returncode attribute, and output & stderr attributes if those streams
        were captured.
        If timeout is given, and the process takes too long, a TimeoutExpired
        exception will be raised.
        There is an optional argument "input", allowing you to
        pass a string to the subprocess's stdin.  If you use this argument
        you may not also use the Popen constructor's "stdin" argument, as
        it will be used internally.
        The other arguments are the same as for the Popen constructor.
        If universal_newlines=True is passed, the "input" argument must be a
        string and stdout/stderr in the returned object will be strings rather than
        bytes.
        """
        input = kwargs.pop("input", None)
        timeout = kwargs.pop("timeout", None)
        check = kwargs.pop("check", False)
        if input is not None:
            if "stdin" in kwargs:
                raise ValueError("stdin and input arguments may not both be used.")
            kwargs["stdin"] = PIPE

        process = Popen(*popenargs, **kwargs)
        try:
            process.__enter__()  # No-Op really... illustrate "with in 2.4"
            try:
                stdout, stderr = process.communicate(input, timeout=timeout)
            except TimeoutExpired:
                process.kill()
                stdout, stderr = process.communicate()
                raise TimeoutExpired(
                    process.args, timeout, output=stdout, stderr=stderr
                )
            except:
                process.kill()
                process.wait()
                raise
            retcode = process.poll()
            if check and retcode:
                raise CalledProcessError(
                    retcode, process.args, output=stdout, stderr=stderr
                )
        finally:
            # None because our context manager __exit__ does not use them.
            process.__exit__(None, None, None)

        return CompletedProcess(process.args, retcode, stdout, stderr)

    subprocess.run = run
    subprocess.CalledProcessError = CalledProcessError


def decode(string, encodings=None):
    if not PY2 and not isinstance(string, bytes):
        return string

    if PY2 and isinstance(string, unicode):
        return string

    encodings = encodings or ["utf-8", "latin1", "ascii"]

    for encoding in encodings:
        try:
            return string.decode(encoding)
        except (UnicodeEncodeError, UnicodeDecodeError):
            pass

    return string.decode(encodings[0], errors="ignore")


def encode(string, encodings=None):
    if not PY2 and isinstance(string, bytes):
        return string

    if PY2 and isinstance(string, str):
        return string

    encodings = encodings or ["utf-8", "latin1", "ascii"]

    for encoding in encodings:
        try:
            return string.encode(encoding)
        except (UnicodeEncodeError, UnicodeDecodeError):
            pass

    return string.encode(encodings[0], errors="ignore")


def to_str(string):
    if isinstance(string, str) or not isinstance(string, (unicode, bytes)):
        return string

    if PY2:
        method = "encode"
    else:
        method = "decode"

    encodings = ["utf-8", "latin1", "ascii"]

    for encoding in encodings:
        try:
            return getattr(string, method)(encoding)
        except (UnicodeEncodeError, UnicodeDecodeError):
            pass

    return getattr(string, method)(encodings[0], errors="ignore")


def list_to_shell_command(cmd):
    executable = cmd[0]

    if " " in executable:
        executable = '"{}"'.format(executable)
        cmd[0] = executable

    return " ".join(cmd)
