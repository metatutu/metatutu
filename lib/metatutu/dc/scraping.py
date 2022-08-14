from abc import ABC, abstractclassmethod
import os
import time
import requests
import hashlib
import chardet
from selenium import webdriver
from selenium.webdriver.common.by import By
from metatutu.logging import *
from metatutu.fsds import *

__all__ = [
    "Cache", "FileSystemCache",
    "Session", "HttpSession", "WebDriverSession"
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
        #config
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

        #control
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

    @property
    def handle(self):
        return self.open()

    @classmethod
    def wait(cls, secs=1.0):
        time.sleep(secs)

    @classmethod
    def bytes_str(cls, content_bytes, encoding=None):
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

        #config
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
        #check method
        if method not in ["GET", "POST"]: return None

        #check mode
        if "retries" in kwargs:
            #request with retries
            retries = kwargs["retries"]
            if retries < 0: return None
            del kwargs["retries"]

            response = self.request(method, url, **kwargs)
            retry_count = 0
            while True:
                if response:
                    if response.status_code in self.ok_status_codes: break
                if retry_count >= retries: return None
                retry_count += 1
                kwargs["call_tag"] = "retry {}/{}".format(retry_count, retries)
                response = self.request(method, url, **kwargs)
            return response
        else:
            #request without retry
            try:
                s = self.handle
                if self.user_agent: s.headers["User-Agent"] = self.user_agent

                if "call_tag" in kwargs:
                    call_tag = kwargs.get("call_tag", None)
                    del kwargs["call_tag"]
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
        kwargs["retries"] = retries
        return self.request("GET", url, **kwargs)

    def post(self, url, data=None, json=None, retries=0, **kwargs):
        kwargs["data"] = data
        kwargs["json"] = json
        kwargs["retries"] = retries
        return self.request("POST", url, **kwargs)

class WebDriverSession(Session):
    """Session with selenium web driver."""
    def __init__(self):
        Session.__init__(self)

        #config
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

if __name__ == "__main2__":
    cache = FileSystemCache()
    cache.root_folderpath = "d:\\data\\cache"
    resource_id = "d:\\address_town_ref.xlsx"
    data = FileSystemUtils.load_file_bytes(resource_id)
    key = cache.make_key(resource_id)
    cache.set(key, data)
    data2 = cache.get(key)
    print(data2)
    time.sleep(5)
    data3 = cache.get(key, 3)
    print(data3)

if __name__ == "__main__":
    logger = ConsoleLogger()
    session = HttpSession()
    session.bind_logger(logger)
    session.get("https://google.com", timeout=2, retries=3)

    session.get("https://jobs.51job.com/all/133571945.html?s=sy_fx_fxlb&t=101", timeout=2, retries=3)