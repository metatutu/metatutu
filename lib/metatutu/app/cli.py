"""
    This is part of METATUTU library.
    https://pypi.org/project/metatutu/

	:author: max.wu@wooloostudio.com
	:copyright: Copyright (C) 2022 Wooloo Studio.  All rights reserved.
	:license: see LICENSE.
"""

import os
import sys
import getopt
from metatutu.logging import LoggerHelper, Loggers

class CLIApp(LoggerHelper):
    """Base class of CLI applications."""
    def __init__(self):
        LoggerHelper.__init__(self)

        #initialize loggers
        self.loggers = Loggers()
        self.bind_logger(self.loggers)

    def register_logger(self, logger):
        self.loggers.register_logger(logger)

    def init_app(self):
        """Initialize the application.

        This will be called by framework at application starts.
        It could be used to initialize the application environment.

        :returns: Returns True to continue the program, or False to exit.
        """
        return True

    def determine_workflow(self):
        """Determine the workflow to run.

        This will be called by framework after initialization.
        Applicaiton could either use command line or menu to determine
        the workflow to run.

        :returns: Returns the workflow name (str) to run.
            Returns None to exit program.
        """
        return "default"

    def _globals(self):
        """Global namespace for workflow handler searching.

        When dispatching workflow, if the handler is not found within
        the members, it could alternatively search in a global namespace,
        so that the workflow handler could be as a regular function.
        If application needs to have this capability, simple implement
        this with below code:

            def _globals(self): return globals()
        """
        return None

    def run_workflow(self, workflow_name):
        """Run the workflow.

        Framework will call this to run the specific workflow.

        :param workflow_name: Workflow name.
        :returns: Returns program exit code gotten from the workflow.
            It returns None on unexpected error.
        """
        def find_workflow_handler(workflow_name):
            try:
                #handler name
                handler_name = "workflow_" + workflow_name

                #find handler in the member
                if hasattr(self, handler_name):
                    f = getattr(self, handler_name)
                    if callable(f): return f

                #find handler in globals
                x_globals = self._globals()
                if x_globals:
                    f = x_globals.get(handler_name)
                    if callable(f): return f
            except:
                pass
            return None

        try:
            f = find_workflow_handler(workflow_name)
            if f is None: return self.on_workflow_not_dispatched(workflow_name)
            return f()
        except:
            return 1

    def workflow_default(self):
        """Handler of default workflow.

        "default" is the workflow name of this framework.
        So for an application with single workflow, simple implement this function
        could make it happens.

        :returns: Returns the exit code of the program.
        """
        return 0

    def on_workflow_not_dispatched(self, workflow_name):
        """Handler for case that workflow is not dispatched.

        This will be called by framework when workflow could not be dispatched.

        :param workflow_name: Workflow name.
        :returns: Returns the exit code of the program.
        """
        return 1

    def cleanup_app(self):
        """Clean up the application.

        This will be called by framework before exiting program.
        """
        #cleanup loggers
        self.loggers.close()

    def main(self):
        """Application framework."""
        exit_code = 1
        try:
            #initialize application
            if not self.init_app(): raise Exception()

            #determine workflow
            workflow_name = self.determine_workflow()
            if workflow_name is None: raise Exception()

            #run workflow
            exit_code = self.run_workflow(workflow_name)
        except:
            pass
        finally:
            #cleanup application
            self.cleanup_app()
        os._exit(exit_code)

    @classmethod
    def parse_command_line(cls, parts):
        """Parse command line.

        Command line syntax is as:
        program <command 1> <command 2> ... [option 1] [option 2] ...

        Commands are required and options are optional.  Commands are
        always before options.

        :param parts: This is a list of argument definitions.
            Each list item specify one arguments to be read from command line.
            The item is in a tuple as (key, short, long).
            "key" is used to query the argument value.
            "__" prefixed key names are reserved for internal use.
            "short" is the short format of option.  eg. "-t:" expects an option
            given as "-t <value>", "-i" expects an option wihtout value.
            "long" is the long format of option.  eg. "time=" expects an option
            given as "--time=<value>", "id" expects an option given as "--id".
            For more information of "short" and "long", check `getopt.getopt()`.
            When "short" and "long" are both empty (""), it specifies a command.
        :returns: Returns a dict as {key: value}.
            "key" is what specified in `parts` for commands and options.
            The value is typically a str value read from command line.
            If the option is not with value, with its existence in the dict,
            it means it had been specified in the command line.
            There are some special keys: "__cmd__" is with the full command line,
            "__argn__" is with the number of arguments and "__argv0__" is
            the first item of `sys.argv[]` which is the program.  "__args__" is
            with remaining arguments not parsed.
            If there is no argument at all (run program directly), it will returns
            "__cmd__", "__argn__" and "__argv0__" only.
            If there is argument given but not matching the syntax as expected,
            it will return None.  If there is other unknown error, it will return
            None as well.
        """
        try:
            #process parts
            parts_commands = []
            parts_options = []
            shortopts = ""
            longopts = []
            for name, short, long in parts:
                if short == "" and long == "":
                    parts_commands.append(name)
                else:
                    shortopts += short
                    longopts.append(long)
                    formats = []
                    if short != "": formats.append(short.replace(":", ""))
                    if long != "": formats.append("--" + long.replace("=", ""))
                    parts_options.append((name, formats))

            #get basic information
            r = {}
            r["__cmd__"] = " ".join(sys.argv)
            r["__argn__"] = len(sys.argv)
            r["__argv0__"] = sys.argv[0]
            if len(sys.argv) <= 1: return r

            #get commands
            command_count = len(parts_commands)
            if len(sys.argv) < 1 + command_count: return None
            for i in range(0, command_count):
                r[parts_commands[i]] = sys.argv[1 + i]

            #get options
            opts, args = getopt.getopt(sys.argv[1 + command_count:], shortopts, longopts)
            for opt_name, opt_value in opts:
                for name, formats in parts_options:
                    if opt_name in formats:
                        r[name] = opt_value

            #get args
            r["__args__"] = args

            #
            return r
        except:
            return None
