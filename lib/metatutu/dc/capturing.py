"""
    This is part of METATUTU library.
    https://pypi.org/project/metatutu/

	:author: max.wu@wooloostudio.com
	:copyright: Copyright (C) 2022 Wooloo Studio.  All rights reserved.
	:license: see LICENSE.
"""

from selenium.webdriver import ChromeOptions
from metatutu.dc.scraping import WebDriverSession

__all__ = ["FullPageCapturer"]

class FullPageCapturer:
    """Capturer of full page."""
    def __init__(self):
        self.init_width = 1280  #initial/exoected width for measurment
        self.init_height = 768  #initial/expected height for measurment
        self.window_width = None  #window width for capturing
        self.window_height = None  #window height for capturing

    def open_session(self, mode):
        """Open a session with container at specific size.

        Default implementation is with Chrome at specific mode.
        Derived classes could override this to meet the needs.

        :param mode: Mode to open session.
            "initial" mode is to open the session for page size measurement.
            "capturing" mode is to open the session for page capturing.
        :returns: Returns a session on success or None on failure.
        """
        session = None
        try:
            #initialize options
            options = ChromeOptions()
            options.add_argument("--incognito")
            if mode == "initial":
                options.add_argument("--window-size={},{}".format(self.init_width, self.init_height))
            elif mode == "capturing":
                options.add_argument("--window-size={},{}".format(self.window_width, self.window_height))
                options.add_argument("--hide-scrollbars")
            else:
                raise Exception()
            options.add_argument("--headless")
            options.add_experimental_option("excludeSwitches", ["enable-logging"])

            #create/open session
            session = WebDriverSession()
            if session.open(options=options) is None: raise Exception()

            #
            return session
        except:
            if session: session.close()
            return None

    def load_page(self, session, url):
        """Load page.

        Default implement is to simply load the page at specific URL.
        Derived classes could override this to add actions to make page
        ready for capture.

        :param session: Session.
        :param url: URL of the page.
        :return: Returns True to continue capturing or False on failure and stop.
        """
        session.get(url)
        return True

    @classmethod
    def capture(cls, url, filepath, init_width=None, init_height=None):
        """Capture a page as image file.

        :param url: URL of the page.
        :param filepath: File path of the output image file.
        :param init_width: Initial/expected width.  This will be used to
            limit the page width.  The actual output will be based on the page
            width gotten under this initial settings for responsive pages.
            If it's None, use default value from class of captuer derived from
            `FullPageCaptuer`.
        :param init_height: Initial/expected height.
        :returns: Returns True on success and False on failure.
        """
        session = None
        try:
            #create capturer
            capturer = cls()
            if init_width: capturer.init_width = init_width
            if init_height: capturer.init_height = init_height

            #pass 1: measure sizes
            session = capturer.open_session("initial")
            if session is None: return False
            result = capturer.load_page(session, url)
            sizes = session.get_sizes()
            print(sizes)
            capturer.window_width = sizes["page.width"] + sizes["window.border.width"]
            capturer.window_height = sizes["page.height"] + sizes["window.border.height"]
            session.close()
            session = None
            if not result: return False

            #pass 2: capture page
            session = capturer.open_session("capturing")
            if session is None: return False
            result = capturer.load_page(session, url)
            if result: result = session.save_screenshot(filepath)
            session.close()
            session = None
            if not result: return False

            #
            return True
        except:
            if session: session.close()
            return False
