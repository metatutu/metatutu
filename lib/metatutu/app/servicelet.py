"""
    This is part of METATUTU library.
    https://pypi.org/project/metatutu/

	:author: max.wu@wooloostudio.com
	:copyright: Copyright (C) 2022 Wooloo Studio.  All rights reserved.
	:license: see LICENSE.
"""

import os
import threading
import time
import win32api
import win32con
from metatutu.app.cli import CLIApp
from metatutu.logging import ConsoleLogger

class Servicelet(CLIApp):
    """Base class of servicelet applications.

    Servicelet is a console based application which could be used to run some
    background service without user interaction.  The console could display
    some service status information, and the information could be logged as well
    in other forms.

    This class defines the framework of a servicelet application, so that derived
    classes could focus on the service logic.  Derviced class need to override
    `service_processor()` to include the service logic.

    There are 2 ways of user termination defined:
    1. User press CTRL+C in the active console.

    2. User press CTRL+ALT+Z anywhere in the operating system (support Windows
    only for now).  This is optional to the servicelet, and it could be turn
    off by set `self.listen_global_stop_request` to False.

    Both will set `stop_requested` flag.  So in the implementation of
    `service_processor()`, it needs to check the `self.stop_requested` time to
    time and exit the process smoothly.

    Servicelet information could be set in `self.service_info`.  `name` is
    mandatory and others are optional though we strongly suggest to have them set.
    """

    def __init__(self):
        CLIApp.__init__(self)

        self.service_info = {
            "name": None,
            "version": None,
            "copyright": None,
            "license": None
        }

        self.listen_global_stop_request = True

        console_logger = ConsoleLogger()
        console_logger.include_timestamp = False
        self.register_logger(console_logger)

        self._control_lock = threading.Lock()
        self._stop_requested = False

    @property
    def stop_requested(self):
        with self._control_lock:
            return self._stop_requested

    def service_processor(self):
        """Service processor.

        This will be called by framework when starting the service program.
        It will be run in thread.  Derived class must override this to implement the
        process logic of service application.

        The process logic could be a single process taking long time, or repeating or
        even in dead loop.  The process needs to check stop request time to time, and
        exit the process smoothly.  The main thread will take care of the terminal
        signals from users and raise the stop request accordingly.

        When this process routine returns, the main thread and program will
        exit as well.
        """
        raise NotImplementedError

    def __service_processor(self):
        self.log("Entering service processr...")
        try:
            self.service_processor()
        except Exception as ex:
            self.exception(ex)
        self.log("Leaving service processor...")

    def workflow_default(self):
        try:
            #service info
            si = self.service_info
            if si.get("name") is None: return -1
            self.log("Service Name: {}".format(si.get("name")))

            if si.get("version"): self.log("Version: {}".format(si.get("version")))
            if si.get("copyright"): self.log(si.get("copyright"))
            if si.get("license"): self.log(si.get("license"))

            #start service process
            self.log("Starting service processor...")
            self.log("Preparing...", 1)
            self._stop_requested = False
            th = threading.Thread(target=self.__service_processor)
            self.log("Starting...", 1)
            th.start()

            #wait for service stopped or terminated
            while True:
                try:
                    #check global terminate signal (Windows Only)
                    if self.listen_global_stop_request and os.name == "nt":
                        key_ctrl_down = (win32api.GetKeyState(win32con.VK_CONTROL) & 0x80 != 0)
                        key_alt_down = (win32api.GetKeyState(win32con.VK_MENU) & 0x80 != 0)
                        key_z_down = (win32api.GetKeyState(90) & 0x80 != 0)
                        if key_ctrl_down and key_alt_down and key_z_down:
                            self.info("CTRL+ALT+Z is pressed.  Stopping the service processor...")
                            with self._control_lock: self._stop_requested = True
                            break

                    #check processor state
                    if not th.is_alive(): break

                    #sleep
                    time.sleep(0.1)
                except KeyboardInterrupt:
                    self.info("CTRL+C is pressed.  Stopping the service processor...")
                    with self._control_lock: self._stop_requested = True
                    break

            #stop service processor
            th.join()
            self.log("Service processor is stopped.")

            #
            return 0
        except Exception as ex:
            self.exception(ex)
            return -1
