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
from metatutu.fsds import FileSystemUtils, TempFile

class Cmdline:
    """Command line."""
    def __init__(self, cmdline=None):
        self._cmdline = None
        self._args = None
        if cmdline is None:
            self._args = []
        elif type(cmdline) is str:
            self._cmdline = cmdline
        elif type(cmdline) is list:
            self._args = cmdline
        elif type(cmdline) is Cmdline:
            self._cmdline = cmdline._cmdline
            self._args = cmdline._args

    @property
    def cmdline(self):
        if self._cmdline:
            return self._cmdline.strip()
        else:
            return self.args_to_cmdline(self._args).strip()

    def __str__(self):
        return self.cmdline

    def is_valid(self):
        return str(self) != ""

    def reset(self, arg0=None):
        self._cmdline = None
        self._args = []
        self.add(arg0)

    def add(self, arg):
        if arg: self._args.append(arg)

    @classmethod
    def args_to_cmdline(cls, args):
        """Make command line text from argument list.

        :param args: List of arguments.
        :returns: Command line text.
        """
        cmdline = ""
        for arg in args:
            if arg.find(" ") >= 0:
                if arg.find('"') >= 0 or arg.find("'") >= 0:
                    part = arg
                else:
                    part = '"' + arg + '"'
            else:
                part = arg
            if cmdline != "": cmdline += " "
            cmdline += part
        return cmdline

class OSUtils:
    """Operating system utilities."""

    @classmethod
    @property
    def is_windows(cls):
        return os.name == "nt"

    @classmethod
    @property
    def is_posix(cls):
        return os.name == "posix"

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
            If `pid` is given, `p` will be ignored.
        :param p: Process object.  This will be used only when `pid` is None.
        :param cmdline: Command line text to be filled.  If it's None, it will be generated.
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
                "cmdline": cmdline if cmdline else Cmdline.args_to_cmdline(p.cmdline()),
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
                cmdline = Cmdline.args_to_cmdline(p.cmdline())
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
                cmdline = Cmdline.args_to_cmdline(p.cmdline())
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
                cmdline = Cmdline.args_to_cmdline(p.cmdline())
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
    def create_subprocess(cls, cmdline, wait=False, mode="null", output=None, **kwargs):
        """Create a process.

        This is a super implementation based on `class subprocess.Popen`
        to create the process with predefined modes, so that it will be
        easier for application developers.

        Below modes are available:

        * "null": Subprocess, no output.

        * "new": Subprocess, output to the new console.  (Windows only)

        * "current": Subprocess, output to the current console.

        * "output": Subprocess, output to the `output['stdout']`.  This mode
            doesn't work when `wait` is not True.

        :param cmdline: Command line.  Could be str, list of arguments or
            an instance of `Cmdline`.
        :param wait: If it's True, it will wait for subprocess terminated.
            Otherwise, it will returns immediately after subprocess created.
        :param mode: Mode.  If it's None, it will bypass the special settings.
        :param output: Extra output values in dict.  If's None, ignore all
            extra output.
        :returns: Returns a `class subprocess.Popen` object on success,
            or None on failure.
        """
        tf_stdout = None
        f_stdout = None
        try:
            #get settings
            stdout = kwargs.pop("stdout", None)
            creationflags = kwargs.pop("creationflags", 0)

            #apply special settings based on mode
            if mode:
                if mode == "null":
                    stdout = subprocess.DEVNULL
                elif mode == "new":
                    if cls.is_windows:
                        stdout = None
                        creationflags = subprocess.CREATE_NEW_CONSOLE
                elif mode == "current":
                    stdout = None
                elif mode == "output":
                    if not wait: return None
                    tf_stdout = TempFile()
                else:
                    return None

            #output to file
            if tf_stdout:
                f_stdout = open(tf_stdout.path, "w")
                stdout = f_stdout

            #create subprcess
            p = subprocess.Popen(cmdline,
                stdout=stdout,
                creationflags=creationflags,
                **kwargs)

            #wait
            if wait: p.wait()

            #get output
            if f_stdout:
                f_stdout.close()
                f_stdout = None
                content = FileSystemUtils.load_file_contents(tf_stdout.path)
                if content is None: content = ""
                if output is not None: output["stdout"] = content

            #
            return p
        except:
            return None
        finally:
            if f_stdout: f_stdout.close()
            if tf_stdout: tf_stdout.delete()

    @classmethod
    def run(cls, cmdline, run_as_command=False, **kwargs):
        """Run a command with shell or an application without shell.

        :param cmdline: Command line.
        :param run_as_command: Whether to run command line as command or as application.
            True to run it as command with shell, False to run it as application
            without shell.
        :returns: Returns return code of the command.  Returns None on failure.
        """
        kwargs.pop("shell", None)
        kwargs.pop("wait", None)
        mode = kwargs.pop("mode", None)
        if run_as_command:
            if mode == "new":  #for Windows only
                p = cls.create_subprocess("cmd /c " + cmdline, wait=True, shell=False, mode=mode, **kwargs)
            else:
                p = cls.create_subprocess(cmdline, wait=True, shell=True, mode=mode, **kwargs)
        else:
            p = cls.create_subprocess(cmdline, wait=True, shell=False, mode=mode, **kwargs)
        if p is None: return None
        return p.returncode

    @classmethod
    def start(cls, cmdline, **kwargs):
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

    @classmethod
    @property
    def PATH(cls):
        try:
            return os.environ["PATH"].split(os.pathsep)
        except:
            return []

    @classmethod
    def where(cls, filename):
        """Find file in current folder and folders in PATH.

        :param filename: File name.
        :returns: Returns a list of full path of found files in order."""
        filepaths = []
        filepath = os.path.join(os.getcwd(), filename)
        if os.path.isfile(filepath): filepaths.append(filepath)
        for path in cls.PATH:
            filepath = os.path.join(path, filename)
            if os.path.isfile(filepath):
                if filepath not in filepaths: filepaths.append(filepath)
        return filepaths
