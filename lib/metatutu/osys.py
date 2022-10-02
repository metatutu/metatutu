"""
    This is part of METATUTU library.
    https://pypi.org/project/metatutu/

	:author: max.wu@wooloostudio.com
	:copyright: Copyright (C) 2022 Wooloo Studio.  All rights reserved.
	:license: see LICENSE.
"""

import os
import re
import psutil
import subprocess

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
    def process(cls, pid=None, p=None, cmdline=None):
        """Get a snapshot of process information.

        :param pid: Process id.  If both `pid` and `p` are None, it means current process.
            If pid is given, `p` will be ignored.
        :param p: Process object.  This will be used only when `pid` is None.
        :param cmdline: Command line data to be filled.  If it's None, it will be generated.
        :returns: Returns a dict with process information or None on failure.
        """
        try:
            if pid:
                p = cls.Process(pid)
                if p is None: return None
            else:
                if p:
                    pass
                else:
                    p = cls.Process()
                    if p is None: return None
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
                process = cls.process(p=p, cmdline=cmdline)
                if process: processes.append(process)
            except:
                pass
        return processes

    @classmethod
    def list_subprocesses(cls, pid=None, pattern=".*"):
        """Get a snapshot of all subprocesses meeting search criteria.

        :param pid: Process id.  If it's None, it means current process.
        :param pattern: Pattern of command line for searching, in RegEx and lower cases.
        :returns: Returns a list of processes found, or None on failure.
            List is as [{process}].
        """
        processes = []
        try:
            pp = cls.Process(pid)
            if pp is None: return None
            for p in pp.children():
                cmdline = cls.make_cmdline(p.cmdline())
                if not re.fullmatch(pattern, cmdline.lower()): continue
                process = cls.process(p=p, cmdline=cmdline)
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
                        open_files[file_path].append(cls.process(p=p, cmdline=cmdline))
                    else:
                        open_files[file_path] = [cls.process(p=p, cmdline=cmdline)]
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

    @classmethod
    def create_subprocess(cls, cmdline, wait=False, mode="null", **kwargs):
        """Create a process.

        This is a super implementation based on `class subprocess.Popen`
        to create the process with predefined modes, so that it will be
        easier for application developers.

        Below modes are available:

        * "null": Subprocess, no output.

        * "new": Subprocess, output to the new console.  (Windows only)

        * "current": Subprocess, output to the current console.

        :param cmdline: Full command line.
        :param wait: If it's True, it will wait for subprocess terminated.
            Otherwise, it will returns immediately after subprocess created.
        :param mode: Mode.  If it's None, it will bypass the special settings.
        :returns: Returns a `class subprocess.Popen` object on success,
            or None on failure.
        """
        try:
            #get settings
            stdout = kwargs.pop("stdout", None)
            creationflags = kwargs.pop("creationflags", 0)

            #apply special settings based on mode
            if mode:
                if mode == "null":
                    stdout = subprocess.DEVNULL
                elif mode == "new":
                    stdout = None
                    creationflags = subprocess.CREATE_NEW_CONSOLE
                elif mode == "current":
                    stdout = None
                elif mode == "$null":
                    stdout = None
                    creationflags = subprocess.CREATE_NEW_PROCESS_GROUP
                elif mode == "$new":
                    stdout = None
                    creationflags = subprocess.CREATE_NEW_PROCESS_GROUP + subprocess.CREATE_NEW_CONSOLE
                else:
                    return None

            #create subprcess
            p = subprocess.Popen(cmdline,
                stdout=stdout,
                creationflags=creationflags,
                **kwargs)

            #wait
            if wait: p.wait()

            #
            return p
        except:
            return None

    @classmethod
    def run_command(cls, cmdline, **kwargs):
        """Run a command with shell.

        :returns: Returns return code of the command.  Returns None on failure.
        """
        kwargs.pop("shell", None)
        kwargs.pop("wait", None)
        mode = kwargs.pop("mode", None)
        if mode == "new":
            #mode "new" is working for Windows only
            p = cls.create_subprocess("cmd /c " + cmdline, wait=True, shell=False, mode=mode, **kwargs)
        else:
            p = cls.create_subprocess(cmdline, wait=True, shell=True, mode=mode, **kwargs)
        if p is None: return None
        return p.returncode

    @classmethod
    def run_app(cls, cmdline, **kwargs):
        """Run an application without shell.

        :returns: Returns return code of the command.  Returns None on failure.
        """
        kwargs.pop("shell", None)
        kwargs.pop("wait", None)
        p = cls.create_subprocess(cmdline, wait=True, shell=False, **kwargs)
        if p is None: return None
        return p.returncode

    @classmethod
    def start_app(cls, cmdline, **kwargs):
        """Start an application without shell."""
        kwargs.pop("shell", None)
        kwargs.pop("wait", None)
        return cls.create_subprocess(cmdline, wait=False, shell=False, **kwargs)

    @classmethod
    def kill_subprocesses(cls):
        """Kill all subprocesses."""
        try:
            pp = cls.Process()
            if pp is None: return
            for p in pp.children(): p.kill()
        except:
            pass
