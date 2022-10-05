"""
    This is part of METATUTU library.
    https://pypi.org/project/metatutu/

	:author: max.wu@wooloostudio.com
	:copyright: Copyright (C) 2022 Wooloo Studio.  All rights reserved.
	:license: see LICENSE.
"""

from abc import ABC, abstractclassmethod
import os
import time
import requests
import hashlib
import chardet
from selenium import webdriver
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
from metatutu.logging import LoggerHelper, MessageLevel
from metatutu.fsds import FileSystemUtils, FileSystemDataStore, TempFile
from metatutu.images import ImageUtils

__all__ = [
    "Cache", "FileSystemCache",
    "Session", "HttpSession", "WebDriverSession",
]

class Cache(ABC):
    """Base class of cache classes.

    Cache is a component in scraping framework to store the raw content obtained
    from web during scraping process, so that it could be reused next time.
    For example, scraping application could cache all pages (aka. source HTML) had
    be load, so when the process stops for some reason, rerun the process doesn't
    need to load the pages already cached.

    Derived class needs to implement below interfaces with specific persistence
    strategy:

    * ``set()``: Set key value.
    * ``remove()``: Remove the key value.
    * ``get()``: Get key value.
    * ``clear()``: Clear all/expired key values..
    """
    @abstractclassmethod
    def set(self, key, value, text_format=False):
        """Set key value.

        :param key: Key.
        :param value: Value.
        :param text_format: Whether the value is in string or bytes format.
        """
        pass

    @abstractclassmethod
    def remove(self, key):
        """Remove the key value.

        :param key: Key.
        """
        pass

    @abstractclassmethod
    def get(self, key, valid_period=0, text_format=False):
        """Get key value.

        :param key: Key.
        :param valid_period: Valid period of cached value (seconds).
            If it's 0, the key value is valid forever.
        :param text_format: Whether the value is in string or bytes format.

        :return: It returns the cached value if it's hit.  Otherwise, it returns None.
        """
        pass

    @abstractclassmethod
    def clear(self, valid_period=0):
        """Clear all/expired key values.

        :param valid_period: Valid period of cached value (seconds).
            If it's 0, all the key values will be removed.
        """
        pass

    @classmethod
    def make_key(cls, resource_id):
        """Make a unique key of a resource.

        :param resource_id: This is a string to identify the resource.
            Typically, it is a URL of a page in web scraping application.
        """
        return hashlib.md5(resource_id.encode(encoding="utf-8")).hexdigest()

class FileSystemCache(Cache):
    """Cache with persistence on file system.

    All cached data will be stored in a folder on file system.
    Each key value will be saved as a single file with the name as same as the key.

    :ivar root_folderpath: Root folder path.
    """
    def __init__(self):
        # config
        self.root_folderpath = None

    def _get_filepath(self, key):
        fsds = FileSystemDataStore(self.root_folderpath)
        return fsds.get_path(key, True)

    def set(self, key, value, text_format=False):
        fpath = self._get_filepath(key)
        if value is None:
            FileSystemUtils.delete_file(fpath)
        else:
            if text_format:
                FileSystemUtils.save_file_contents(fpath, value)
            else:
                FileSystemUtils.save_file_bytes(fpath, value)

    def remove(self, key):
        fpath = self._get_filepath(key)
        FileSystemUtils.delete_file(fpath)

    def get(self, key, valid_period=0, text_format=False):
        fpath = self._get_filepath(key)
        if not FileSystemUtils.file_exists(fpath): return None
        if valid_period > 0:
            if (time.time() - os.path.getctime(fpath)) > valid_period: return None
        if text_format:
            return FileSystemUtils.load_file_contents(fpath)
        else:
            return FileSystemUtils.load_file_bytes(fpath)

    def clear(self, valid_period=0):
        fpaths = FileSystemUtils.list_files(self.root_folderpath)
        t_now = time.time()
        if fpaths is None: return
        if valid_period > 0:
            for fpath in fpaths:
                if (t_now - os.path.getctime(fpath)) > valid_period:
                    FileSystemUtils.delete_file(fpath)
        else:
            for fpath in fpaths:
                FileSystemUtils.delete_file(fpath)

class Session(ABC, LoggerHelper):
    """Base class of session classes.

    In this scrapping framework, session is defined as the controller to access
    the web.  It's used from the first access to the specific website till the
    last access.  One session instance is with one base method.  Method could
    be implemented with HTTP requests, seleiumn webdrivers, and so on.
    """
    def __init__(self):
        LoggerHelper.__init__(self)

        # control
        self._handle = None

    def __del__(self):
        self.close()

    @abstractclassmethod
    def open(self, **kwargs):
        """Open the session.

        :returns: Returns the open session handle on success or None on failure.
        """
        return None

    @abstractclassmethod
    def close(self):
        """Close the session."""
        pass

    @abstractclassmethod
    def _get_page(self, url, cache, format, **kwargs):
        return None

    def get_page(self, url, cache=None, format="soup", **kwargs):
        """Get page content.

        :param url: URL.
        :param cache: Page cache.
        :param format: Return format of page content.
            Valid options are "html" and "soup".
        :param kwargs: Other parameters.
        :returns: Returns page content in specified format or None on failure.
        """
        if format == "html":
            return self._get_page(url, cache, "html", **kwargs)
        elif format == "soup":
            try:
                html = self.get_page(url, cache, "html", **kwargs)
                if html is None: return None
                return BeautifulSoup(html, "html.parser")
            except Exception as ex:
                self.exception(ex)
                return None
        else:
            return self._get_page(url, cache, format, **kwargs)

    @property
    def handle(self):
        return self.open()

    @classmethod
    def wait(cls, secs=1.0):
        """Wait.

        :param secs: Time to wait, in seconds.
        """
        time.sleep(secs)

    @classmethod
    def bytes_str(cls, content_bytes, encoding=None):
        """Convert bytes to str.

        :param content_bytes: Content in bytes.
        :param encoding: Encoding of content.
            If it's None, it will detect the encoding automatically.
        :returns: The content in string.
        """
        try:
            if content_bytes is None: return ""
            if encoding:
                if encoding == "ISO-8859-1": encoding = None
            if encoding is None: encoding = chardet.detect(content_bytes)["encoding"]
            if encoding == "GB2312": encoding = "GBK"
            content_str = str(content_bytes, encoding, errors='replace')
        except:
            content_str = str(content_bytes, errors='replace')
        return content_str

class HttpSession(Session):
    """Session with HTTP requests."""
    def __init__(self):
        Session.__init__(self)

        # config
        self.user_agent = None
        self.ok_status_codes = [200]

    def open(self, **kwargs):
        try:
            if self._handle: return self._handle
            self.debug("Opening HTTP session...")
            self._handle = requests.Session()
            return self._handle
        except Exception as ex:
            self.exception(ex)
            self._handle = None
            return None

    def close(self):
        if self._handle:
            self.debug("Closing HTTP session...")
            self._handle = None

    def response_is_ok(self, response):
        if response:
            return response.status_code in self.ok_status_codes
        else:
            return False

    def request(self, method, url, **kwargs):
        """HTTP request.

        :param method: The method of HTTP request.
            Valid options are "GET" and "POST".
        :param url: URL to be requested.
        :param retries: Number of retries when request was failed.
            If it's None, request will not be retried.
        :param retry_wait: Time to wait between retries.
            If it's None, no wait will happen.
        :param kwargs: Other request parameters.
        :returns: Response object from HTTP request.
            Returns None for invalid calls.
        """
        # check method
        if method not in ["GET", "POST"]: return None

        # check mode
        if "retries" in kwargs:
            # request with retries
            retries = kwargs.pop("retries", 0)
            if retries < 0: return None

            retry_wait = kwargs.pop("retry_wait", 0)

            response = self.request(method, url, **kwargs)
            retry_count = 0
            while True:
                if response:
                    if response.status_code in self.ok_status_codes: break
                if retry_count >= retries: return None
                retry_count += 1
                if retry_wait > 0: self.wait(retry_wait)
                kwargs["call_tag"] = "retry {}/{}".format(retry_count, retries)
                response = self.request(method, url, **kwargs)
            return response
        else:
            # request without retry
            try:
                if url is None: return None
                if url == "": return None

                s = self.handle
                if self.user_agent: s.headers["User-Agent"] = self.user_agent

                call_tag = kwargs.pop("call_tag", None)
                if call_tag:
                    self.debug("HTTP {} ({}): {}".format(method, call_tag, url))
                else:
                    self.debug("HTTP {}: {}".format(method, url))

                if method == "GET":
                    response = s.get(
                        url,
                        **kwargs)
                elif method == "POST":
                    response = s.post(
                        url,
                        data=kwargs.get("data", None),
                        json=kwargs.get("json", None),
                        **kwargs)
                else:
                    response = None
                self.debug("method={}\nurl={}\nstatus={}".format(method, url, response.status_code), 1)

                return response
            except Exception as ex:
                self.exception(ex)
                return None

    def get(self, url, retries=0, **kwargs):
        """HTTP GET request."""
        kwargs["retries"] = retries
        return self.request("GET", url, **kwargs)

    def post(self, url, data=None, json=None, retries=0, **kwargs):
        """HTTP POST request."""
        kwargs["data"] = data
        kwargs["json"] = json
        kwargs["retries"] = retries
        return self.request("POST", url, **kwargs)

    def _get_page(self, url, cache, format, **kwargs):
        if format == "html":
            # read from cache
            if cache:
                key = Cache.make_key(url)
                content = cache.get(key)
                if content: return self.bytes_str(content)

            # read from online
            retries = kwargs.pop("retries", 0)
            response = self.get(url, retries, **kwargs)
            if response:
                if response.status_code == 200:
                    if cache:
                        key = Cache.make_key(url)
                        cache.set(key, response.content)
                    return self.bytes_str(response.content, response.encoding)

        #
        return None

    @classmethod
    def quick_download(cls, url, filepath, retries=0, create_parent=True, **kwargs):
        """Download an object and save it to a file."""
        success = False
        try:
            session = HttpSession()
            response = session.get(url, retries, **kwargs)
            if response:
                if response.status_code == 200:
                    success = FileSystemUtils.save_file_bytes(filepath, response.content, create_parent)
            session.close()
        except:
            pass
        return success

class WebDriverSession(Session):
    """Session with selenium web driver."""
    def __init__(self):
        Session.__init__(self)

        # config
        self.webdriver = "chrome"
        self.default_timeout = 10.0
        self.default_wait = 0.5
        self.default_by = By.XPATH

    def open(self, **kwargs):
        try:
            if self._handle: return self._handle
            self.debug("Opening web driver ({}) session...".format(self.webdriver))
            if self.webdriver == "chrome":
                self._handle = webdriver.Chrome(**kwargs)
            elif self.webdriver == "firefox":
                self._handle = webdriver.Firefox(**kwargs)
            elif self.webdriver == "edge":
                self._handle = webdriver.Edge(**kwargs)
            else:
                raise Exception("Invalid webdriver.")
            return self._handle
        except Exception as ex:
            self.exception(ex)
            return None

    def close(self):
        try:
            if self._handle is None: return
            self.debug("Closing web driver ({}) session...".format(self.webdriver))
            self._handle.close()
            self._handle = None
        except Exception as ex:
            self.exception(ex)
            self._handle = None

    def get(self, url):
        """Open URL."""
        try:
            self.debug("Web Driver ({}) GET: {}".format(self.webdriver, url))
            self.handle.get(url)
            return True
        except Exception as ex:
            self.exception(ex)
            return False

    def get_html(self):
        return self.execute("return document.documentElement.outerHTML")

    def get_soup(self):
        try:
            html = self.get_html()
            if html is None: return None
            return BeautifulSoup(html, "html.parser")
        except Exception as ex:
            self.exception(ex)
            return None

    def _get_page(self, url, cache, format, **kwargs):
        if format == "html":
            # read from cache
            if cache:
                key = Cache.make_key(url)
                content = cache.get(key, text_format=True)
                if content: return content

            # read from online
            wait = kwargs.pop("wait", 0)
            self.get(url)
            self.wait(wait)
            html = self.get_html()
            if html:
                if cache:
                    key = Cache.make_key(url)
                    cache.set(key, html, text_format=True)
                return html

        #
        return None

    def get_url(self, leading_wait=2.0, timeout=None, wait=None):
        """Get current URL.

        :param leading_wait: Wait time before getting URL, in seconds.
        :param timeout: Timeout, in seconds.
        :param wait: Wait time between each retry, in seconds.

        :returns: Returns current URL or None on failure.
        """
        if timeout is None: timeout = self.default_timeout
        if wait is None: wait = self.default_wait
        if leading_wait > 0.0: time.sleep(leading_wait)
        ts_0 = time.perf_counter()
        url = None
        while True:
            try:
                url = self.handle.current_url
                if url:
                    self.debug("Current URL is: {}".format(url))
                    return url
            except:
                pass

            if time.perf_counter() - ts_0 > timeout:
                self.warning("URL is not obtained!", level=MessageLevel.DEBUG)
                return None

            time.sleep(wait)

    def find_element(self, value, base=None, timeout=None, wait=None, by=None):
        """Find element from base node.

        :param value: Element to ne searched.
        :param base: Base node.  If it's None, search from root.
        :param timeout: Timeout, in seconds.  It will keep trying to find the
            expected element until timeout.
        :param wait: Wait time between each retry, in seconds.
        :param by: Value type.

        :returns: Returns the element found or None.
        """
        if timeout is None: timeout = self.default_timeout
        if wait is None: wait = self.default_wait
        if by is None: by = self.default_by
        ts_0 = time.perf_counter()
        if base is None: base = self.handle
        while True:
            try:
                element = base.find_element(by, value)
                if element: return element
            except:
                pass

            if time.perf_counter() - ts_0 > timeout:
                self.warning("Element '{}' is not found!".format(value), level=MessageLevel.DEBUG)
                return None

            time.sleep(wait)

    def find_elements(self, value, base=None, timeout=None, wait=None, by=None):
        """Find elements from base node.

        :param value: Elements to ne searched.
        :param base: Base node.  If it's None, search from root.
        :param timeout: Timeout, in seconds.  It will keep trying to find the
            expected element until timeout.
        :param wait: Wait time between each retry, in seconds.
        :param by: Value type.

        :returns: Returns the elements found or None.
        """
        if timeout is None: timeout = self.default_timeout
        if wait is None: wait = self.default_wait
        if by is None: by = self.default_by
        ts_0 = time.perf_counter()
        if base is None: base = self.handle
        while True:
            try:
                elements = base.find_elements(by, value)
                if elements:
                    self.debug("{} elements had been found as '{}'.".format(len(elements), value))
                    return elements
            except:
                pass

            if time.perf_counter() - ts_0 > timeout:
                self.warning("Element(s) '{}' is not found.".format(value), level=MessageLevel.DEBUG)
                return None

            time.sleep(wait)

    def execute(self, script, *args):
        """Execute script.

        :param script: Script to be executed.
        :param *args: Other arguments.

        :returns: Returns script result or None on failure.
        """
        try:
            return self.handle.execute_script(script, *args)
        except Exception as ex:
            self.exception(ex)
            return None

    def get_sizes(self):
        """Get sizes of the screen, window and content.

        :returns: Returns the sizes of current status, or None on failure.
        """
        try:
            sizes = self.execute("""
                return {
                    "screen.width": window.screen.width,
                    "screen.height": window.screen.height,
                    "screen.client.width": window.screen.availWidth,
                    "screen.client.height": window.screen.availHeight,
                    "window.width": window.outerWidth,
                    "window.height": window.outerHeight,
                    "window.client.width": window.innerWidth,
                    "window.client.height": window.innerHeight,
                    "page.width": document.documentElement.scrollWidth,
                    "page.height": document.documentElement.scrollHeight,
                    "page.client.width": document.documentElement.clientWidth,
                    "page.client.height": document.documentElement.clientHeight
                }
            """)
            if sizes is None: return None
            sizes["window.border.width"] = sizes["window.width"] - sizes["window.client.width"]
            sizes["window.border.height"] = sizes["window.height"] - sizes["window.client.height"]
            sizes["window.scrollbar.width"] = sizes["window.client.width"] - sizes["page.client.width"]
            sizes["window.scrollbar.height"] = sizes["window.client.height"] - sizes["page.client.height"]
            return sizes
        except:
            return None

    def get_element_path(self, element):
        """Get element's full path.

        :returns: Returns the full path of the element, or None on failure.
        """
        s = ""
        s += 'function metatutu_get_path(node){'
        s += '  if (node == null) return "";'
        s += '  if (node.parentNode == null) return "/.";'
        s += '  return metatutu_get_path(node.parentNode) + "/" + node.tagName;'
        s += '}'
        s += 'return metatutu_get_path(arguments[0]);'
        return self.execute(s, element)

    def save_screenshot(self, filepath):
        """Save screenshot as png file.

        :param filepath: File path.
        :returns: Returns True on success or False on failure.
        """
        return self.handle.save_screenshot(filepath)

    def get_screenshot_as_png(self):
        """Get screenshot as PNG data."""
        return self.handle.get_screenshot_as_png()

    def get_screenshot_as_base64(self):
        """Get screenshot as base64 data."""
        return self.handle.get_screenshot_as_base64()

    def get_screenshot_as_image(self):
        """Get screenshot as Image object.

        :returns: Returns Image object on success or None on failure.
        """
        try:
            temp_file = TempFile()
            if not self.save_screenshot(temp_file.path): return None
            image = ImageUtils.OpenImage(temp_file.path)
            return image
        except:
            return None

    def save_html(self, filepath):
        """Save current HTML as file.

        :param filepath: File path.
        :returns: Returns True on success or False on failure.
        """
        html = self.get_html()
        if html is None: return False
        return FileSystemUtils.save_file_contents(filepath, html)

    def capture_snapshot(self, filename, folderpath=None, with_html=True, with_screenshot=True):
        """Capture a snapshot.

        :param filename: Filename of the snapshot.  No extension is needed.
        :param folderpath: Where the file will be created.  If's None, use current working folder.
        :param with_html: Whether to save HTML.
        :param with_screenshot: Whether to save screenshot.
        """
        if folderpath is None: folderpath = ""
        filepath = os.path.join(os.path.abspath(folderpath), filename)
        if with_html: self.save_html(FileSystemUtils.alter_ext(filepath, ".html"))
        if with_screenshot: self.save_screenshot(FileSystemUtils.alter_ext(filepath, ".png"))
