"""
    This is part of METATUTU library.
    https://pypi.org/project/metatutu/

	:author: max.wu@wooloostudio.com
	:copyright: Copyright (C) 2022 Wooloo Studio.  All rights reserved.
	:license: see LICENSE.
"""

import os
import psutil
import re
from metatutu.debugging import Clocker

class OSUtils:
    """Operating system utilities."""

    @classmethod
    def make_cmdline(cls, arg_list):
        """Make a command line text with arguments of command line.

        :param arg_list: List of command line arguments.
        :returns: Command line text.
        """
        cmdline = ""
        for arg in arg_list:
            if arg.find(" ") >= 0:
                if re.fullmatch('".*"', arg) or re.fullmatch("'.*'", arg):
                    part = arg
                else:
                    part = '"' + arg + '"'
            else:
                part = arg
            if cmdline != "": cmdline += " "
            cmdline += part
        return cmdline

    @classmethod
    @property
    def pid(cls):
        return os.getpid()

    @classmethod
    def Process(cls, pid=None):
        """Create a process object with pid.

        :param pid: Process id.  If it's None, it means current process.
        :returns: Returns a process object or None on failure.
        """
        try:
            if pid is None: pid=cls.pid
            return psutil.Process(pid)
        except:
            return None

    @classmethod
    def process(cls, p=None, cmdline=None):
        """Get a snapshot of process information.

        :param p: Process object.  If it's None, it means current process.
        :param cmdline: Command line data to be filled.  If it's None, it will be generated.
        :returns: Returns a dict with process information or None on failure.
        """
        try:
            if p is None: p = cls.Process()
            return {
                "pid": p.pid,
                "name": p.name(),
                "cmdline": cmdline if cmdline else cls.make_cmdline(p.cmdline()),
                "create_time": p.create_time(),
                "cwd": p.cwd(),
                "username": p.username(),
                "ppid": p.ppid()
            }
        except:
            return None

    @classmethod
    def list_processes(cls, pattern=".*"):
        """Get a snapshot of all processes meeting search criteria.

        :param pattern: Pattern of command line for searching, in RegEx and lower cases.
        :returns: Returns a list of processes found.
            List is as [{process}].
        """
        processes = []
        pids = psutil.pids()
        for pid in pids:
            try:
                p = psutil.Process(pid)
                cmdline = cls.make_cmdline(p.cmdline())
                if not re.fullmatch(pattern, cmdline.lower()): continue
                process = cls.process(p, cmdline)
                if process: processes.append(process)
            except:
                pass
        return processes

    @classmethod
    def list_open_files(cls, pattern=".*"):
        """Get a snapshot of all opened files from processes meeting search criteria.

        :param pattern: Pattern of command line for searching, in RegEx and lower cases.
        :returns: Returns a dict of all open files with the list of processes found.
            Dict is as {filepath: [{process}]}.
        """
        open_files = {}
        pids = psutil.pids()
        for pid in pids:
            try:
                p = psutil.Process(pid)
                cmdline = cls.make_cmdline(p.cmdline())
                if not re.fullmatch(pattern, cmdline.lower()): continue
                pofs = p.open_files()
                for pof in pofs:
                    file_path = pof.path
                    if file_path in open_files.keys():
                        open_files[file_path].append(cls.process(p, cmdline))
                    else:
                        open_files[file_path] = [cls.process(p, cmdline)]
            except:
                pass
        return open_files

    @classmethod
    def who_open_the_file(cls, file_path, pattern=".*"):
        """Find processes who is opening the file.

        :param file_path: File path.
        :param pattern: Pattern of command line for searching, in RegEx and lower cases.
        :returns: Returns a list of processes who is opening the file.
            List is as [{process}].
        """
        fpath_target = os.path.abspath(file_path).lower()
        open_files = cls.list_open_files(pattern)
        processes = []
        for fpath, p_list in open_files.items():
            if not fpath.lower() == fpath_target: continue
            processes += p_list
        return processes