"""
    This is part of METATUTU library.
    https://pypi.org/project/metatutu/

	:author: max.wu@wooloostudio.com
	:copyright: Copyright 2022 Wooloo Studio.  All rights reserved.
	:license: see LICENSE.
"""

import sys
import getopt

class CLIApp:
    """Base class of CLI applications."""
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
                f = globals().get(handler_name)
                if callable(f): return f
            except:
                pass
            return None

        try:
            f = find_workflow_handler(workflow_name)
            if f is None: f = self.workflow_not_dispatched(workflow_name)
            return f()
        except:
            return -1

    def workflow_default(self):
        """Handler of default workflow.
        
        "default" is the workflow name of this framework.
        So for an application with single workflow, simple implement this function
        could make it happens.

        :returns: Returns the exit code of the program.
        """
        return 0

    def workflow_not_dispatched(self, workflow_name):
        """Handler for case that workflow is not dispatched.
        
        This will be called by framework when workflow could not be dispatched.

        :param workflow_name: Workflow name.
        :returns: Returns the exit code of the program.      
        """
        return -1

    def cleanup_app(self):
        """Clean up the application.
        
        This will be called by framework before exiting program.
        """
        pass

    def main(self):
        """Application framework."""
        exit_code = -1
        try:
            #initialize application
            if not self.init_app(): return exit_code

            #determine workflow
            workflow_name = self.determine_workflow()
            if workflow_name is None: return exit_code

            #run workflow
            exit_code = self.run_workflow(workflow_name)
        except:
            pass
        finally:
            #cleanup application
            self.cleanup_app()
        sys.exit(exit_code)
    
    @classmethod
    def parse_command_line(cls, options, command_count=0):
        """Parse command line.

        Command line syntax is as:
        program <command 1> <command 2> ... [option 1] [option 2] ...

        Commands are required and options are optional.

        :param options: A list of option formats stored as (name, short, long).
            "name" is used to query option value.  "short" is the short format.
            "long" is the long format.
        :param command_count: Number of commands.
        :returns: Returns a dict as {"commands": [...], "options": {...}, "args": [...]}
            "commands" is a list of all commands from the command line.
            "options" is a dict with option values.  The key is "name".
            "args" is a list of remaining arguments not parsed.
            If it failed to parse the command line, it will return None.
        """
        try:
            #check command line arguments
            if len(sys.argv) < 1 + command_count: return None
            
            #get commands
            r_commands = []
            for i in range(0, command_count):
                r_commands.append(sys.argv[1 + i])

            #get options
            r_options = {}
            shortopts = ""
            longopts = []
            for option in options:
                shortopts += option[1]
                longopts.append(option[2])
            print(shortopts)
            print(longopts)
            opts, args = getopt.getopt(sys.argv[1 + command_count:], shortopts, longopts)
            print(opts)
            for opt_name, opt_value in opts:
                for option in options:
                    if opt_name in (option[1].replace(":", ""), "--" + option[2].replace("=", "")):
                        r_options[option[0]] = opt_value
            
            #
            return {
                "commands": r_commands,
                "options": r_options,
                "args": args
            }
        except:
            return None
