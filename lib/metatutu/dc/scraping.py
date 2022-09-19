"""
    This is part of METATUTU library.
    https://pypi.org/project/metatutu/

	:author: max.wu@wooloostudio.com
	:copyright: Copyright 2022 Wooloo Studio.  All rights reserved.
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
from metatutu.logging import *
from metatutu.fsds import *

__all__ = [
    "Cache", "FileSystemCache",
    "Session", "HttpSession", "WebDriverSession",
    "SessionHelper",
    "Parser"
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
    def open(self):
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

    def open(self):
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

class WebDriverSession(Session):
    """Session with selenium web driver."""
    def __init__(self):
        Session.__init__(self)

        # config
        self.webdriver = "chrome"

    def open(self):
        try:
            if self._handle: return self._handle
            self.debug("Opening web driver ({}) session...".format(self.webdriver))
            if self.webdriver == "chrome":
                self._handle = webdriver.Chrome()
            elif self.webdriver == "firefox":
                self._handle = webdriver.Firefox()
            elif self.webdriver == "edge":
                self._handle = webdriver.Edge()
            else:
                raise Exception("Invalid webdriver.")
            return self._handle
        except Exception as ex:
            self.exception(ex)
            return None

    def close(self):
        if self._handle:
            self.debug("Closing web driver ({}) session...".format(self.webdriver))
            self._handle.close()
            self._handle = None

    def get(self, url):
        """Open URL."""
        try:
            s = self.handle
            self.debug("Web Driver ({}) GET: {}".format(self.webdriver, url))
            s.get(url)
        except Exception as ex:
            self.exception(ex)

    def get_html(self):
        try:
            return self.handle.execute_script("return document.documentElement.outerHTML")
        except Exception as ex:
            self.exception(ex)
            return None

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

    def find_element(self, by=By.ID, value=None):
        try:
            return self.handle.find_element(by, value)
        except Exception as ex:
            self.exception(ex)
            return None

    def find_elements(self, by=By.ID, value=None):
        try:
            return self.handle.find_elements(by, value)
        except Exception as ex:
            self.exception(ex)
            return None

    def find_element_by_xpath(self, xpath):
        return self.find_element(By.XPATH, xpath)

    def find_elements_by_xpath(self, xpath):
        return self.find_elements(By.XPATH, xpath)

class SessionHelper:
    """Helper for classes need session."""
    def __init__(self):
        self._session = None

    @property
    def session(self):
        return self._session

    def bind_session(self, session):
        self._session = session

class Parser(SessionHelper, LoggerHelper):
    """Base class of parsers."""
    def __init__(self):
        SessionHelper.__init__(self)
        LoggerHelper.__init__(self)
        self.cache = None

    def get_page(self, url, cache=None, format="soup", **kwargs):
        if self.session is None: return None
        return self.session.get_page(url, self.cache, format, **kwargs)