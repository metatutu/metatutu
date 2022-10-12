"""
    This is part of METATUTU library.
    https://pypi.org/project/metatutu/

	:author: max.wu@wooloostudio.com
	:copyright: Copyright (C) 2022 Wooloo Studio.  All rights reserved.
	:license: see LICENSE.
"""

from metatutu.osys import OSUtils, Cmdline
from metatutu.logging import LoggerHelper

class Caller(LoggerHelper):
    """Base class of callers of 3rd party applications."""
    def __init__(self):
        LoggerHelper.__init__(self)

        self.mode = "output"
        self.last_output = {}

    @classmethod
    @property
    def is_windows(cls):
        return OSUtils.is_windows

    @classmethod
    @property
    def is_posix(cls):
        return OSUtils.is_posix

    def run(self, cmdline, run_as_command=False, **kwargs):
        """Run a command with shell or an application without shell.

        :param cmdline: Command line.
        :param run_as_command: Whether to run command line as command or application.
            True to run it as command with shell, False to run it as application
            without shell.
        :returns: Returns return code of the command.  Returns None on failure.
        """
        mode = kwargs.pop("mode", None)
        if mode is None: mode = self.mode
        self.last_output = {}
        return OSUtils.run(cmdline, run_as_command, mode=mode, output=self.last_output, **kwargs)

class ShellCaller(Caller):
    """Caller for OS Shell.

    Since most of basic shell commands have solution to be replaced with Python implementation,
    so this is more like an example on how to create callers with `Caller`.
    """
    def __init__(self):
        Caller.__init__(self)

    def ping(self, target, count=5, size=32):
        """Ping target."""
        cmdline = Cmdline()
        if self.is_windows:
            cmdline.add("ping")
            cmdline.add("-n {}".format(count))
            cmdline.add("-l {}".format(size))
            cmdline.add(target)
        elif self.is_posix:
            cmdline.add("ping")
            cmdline.add("-c {}".format(count))
            cmdline.add("-s {}".format(size - 8))
            cmdline.add(target)
        else:
            return None
        return self.run(cmdline, True)

    def env(self):
        """Get system environment variables."""
        cmdline = Cmdline()
        if self.is_windows:
            cmdline.add("set")
        elif self.is_posix:
            cmdline.add("env")
        else:
            return None
        return self.run(cmdline, True)
