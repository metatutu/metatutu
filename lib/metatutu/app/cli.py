"""
    This is part of METATUTU library.
    https://pypi.org/project/metatutu/

	:author: max.wu@wooloostudio.com
	:copyright: Copyright 2022 Wooloo Studio.  All rights reserved.
	:license: see LICENSE.
"""

import sys

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
