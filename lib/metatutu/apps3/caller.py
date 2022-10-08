"""
    This is part of METATUTU library.
    https://pypi.org/project/metatutu/

	:author: max.wu@wooloostudio.com
	:copyright: Copyright (C) 2022 Wooloo Studio.  All rights reserved.
	:license: see LICENSE.
"""

from metatutu.osys import OSUtils
from metatutu.logging import LoggerHelper

class Caller(LoggerHelper):
    """Base class of callers of 3rd party applications."""
    def __init__(self):
        LoggerHelper.__init__(self)

        self.program_filename = None

    @property
    def arg0(self):
        """Get full path of the program."""
        if self.program_filename is None: return None
        programs = OSUtils.where(self.program_filename)
        if len(programs) == 0: return None
        return programs[0]

    def run(self, cmdline, run_as_command=False, **kwargs):
        """Run a command with shell or an application without shell.

        :param cmdline: Command line.
        :param run_as_command: Whether to run command line as command or as application.
            True to run it as command with shell, False to run it as application
            without shell.
        :returns: Returns return code of the command.  Returns None on failure.
        """
        return OSUtils.run(cmdline, run_as_command, **kwargs)

