"""
    This is part of METATUTU library.
    https://pypi.org/project/metatutu/

	:author: max.wu@wooloostudio.com
	:copyright: Copyright (C) 2022 Wooloo Studio.  All rights reserved.
	:license: see LICENSE.
"""

import re
from urllib.parse import urlparse
from metatutu.logging import LoggerHelper
from metatutu.dc.scraping import HttpSession

class SiteScanner(LoggerHelper):
	"""Site scanner."""
	def __init__(self):
		LoggerHelper.__init__(self)

		self.search_paths = []
		self.detectors = {}

	def clear_search_paths(self):
		"""Remove all search paths."""
		self.search_paths = []

	def add_search_path(self, path):
		"""Add a search path.

		Search paths are alternative paths to be scanned in addition to the
		entrance URL.

		:param path: Path to be scanned.  eg. "/about"
		"""
		if path not in self.search_paths: self.search_paths.append(path)

	def clear_detectors(self):
		"""Remove all detectors."""
		self.detectors = {}

	def add_detector(self, name, patterns, exclusions):
		"""Add a detector.

		:param name: Detector name.  It will be used for output dataset as well.
		:param patterns: List of regex patterns to search the data from content.
		:param exclusions: List of regex patterns to exclude the data from search results.
			If the found data from content is fully matching any pattern in exclusions,
			it will not be included in the search results.
		"""
		self.detectors[name] = {
			"patterns": patterns,
			"exclusions": exclusions
		}

	def scan_content(self, content):
		"""Scan content and extract data.

		:param content: Content to be scanned.
		:returns: Returns a dict with found data of each detector or None on failure.
		"""
		try:
			#initialize data
			data = {}

			#go thru all detectors to extract data
			for name, detector in self.detectors.items():
				#initialize search results
				search_results = []

				#try each pattern to find the matching data
				for pattern in detector["patterns"]:
					candidates = re.findall(pattern, content)
					for candidate in candidates:
						#whether it had already been included
						if candidate in search_results: continue

						#whether it should be excluded
						excluded = False
						for exclusion in detector["exclusions"]:
							if re.fullmatch(exclusion, candidate):
								excluded = True
								break
						if excluded: continue

						#add to results
						search_results.append(candidate)

				#save search results
				data[name] = search_results

			#
			return data
		except Exception as ex:
			self.exception(ex)
			return None

	def get_page_content(self, url):
		"""Get content of the page at given URL.

		Derived classes could override this to implement different method
		to get the page content.

		:param url: URL of the page.
		:returns: Returns to content for scanning or None on failure.
		"""
		try:
			session = HttpSession()
			html = session.get_page(url, format="html", timeout=10.0)
			session.close()
			return html
		except Exception as ex:
			self.exception(ex)
			return None

	def scan_page(self, url):
		"""Scan page content and extract data.

		:param url: Page URL.
		:returns: Returns a dict with found data or None on failure.
		"""
		try:
			content = self.get_page_content(url)
			if content is None: return None
			return self.scan_content(content)
		except Exception as ex:
			self.exception(ex)
			return None

	def _get_search_urls(self, url, scan_search_paths_for_home_only):
		"""Get search URLs.

		Derived class could override it to add more search URLs based on
		searching strategies.  For example, to look into all linked pages
		on entrance page.

		:param url: Entrance page URL.
		:param scan_search_paths_for_home_only: see `scan_site()`.
		:returns: Returns a list of search URLs.
		"""
		search_urls = []
		urlparts = urlparse(url)
		if urlparts.scheme == "": return search_urls
		if urlparts.netloc == "": return search_urls
		if scan_search_paths_for_home_only:
			if urlparts.path not in ("", "/"): return search_urls
		base_url = urlparts.scheme + "://" + urlparts.netloc
		for search_path in self.search_paths:
			search_urls.append(base_url + search_path)
		return search_urls

	def _check_data_status(self, data):
		"""Check data status to see whether it should stop scanning.

		Derived class could override it to check the status of data, and judge
		whether the scanning could be stopped based on scanning strategy.
		The check will happen when switching page.

		:param data: Snapshot of data.
		:returns: Returns True to continue scanning.  It it returns False,
			scanning will be stopped.
		"""
		return True

	def scan_site(self, url, scan_search_paths_for_home_only=True):
		"""Scan site content and extract data.

		:param url: Entrance page URL.
		:param scan_search_paths_for_home_only: Whether to scan search paths if url is not for home page.
			If it's True, if url is not a home page, it will NOT scan search paths.
		:returns: Returns a dict with all data found in list by each detector regardless whether it's
			empty or whether any error had occurred.
		"""
		#initialize data
		data = {}
		for name in self.detectors.keys(): data[name] = []

		#get data
		try:
			#scan entrance page
			data_page = self.scan_page(url)
			if data_page:
				for name in self.detectors.keys():
					for item in data_page[name]:
						if item not in data[name]: data[name].append(item)

			#scan search paths
			search_urls = self._get_search_urls(url, scan_search_paths_for_home_only)
			for search_url in search_urls:
				if not self._check_data_status(data): break
				data_page = self.scan_page(search_url)
				if data_page:
					for name in self.detectors.keys():
						for item in data_page[name]:
							if item not in data[name]: data[name].append(item)
		except Exception as ex:
			self.exception(ex)

		#
		return data
