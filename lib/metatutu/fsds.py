"""
    This is part of METATUTU library.
    https://pypi.org/project/metatutu/

	:author: max.wu@wooloostudio.com
	:copyright: Copyright (C) 2022 Wooloo Studio.  All rights reserved.
	:license: see LICENSE.
"""

import os
import uuid
import datetime
import shutil
import re
import json
import tempfile

__all__ = ["FileSystemUtils", "TempFile", "TempFolder", "FileSystemDataStore"]

class FileSystemUtils:
	"""File system utilities."""

	@classmethod
	def create_folder(cls, folderpath):
		"""Create a folder.

		:param folderpath: Folder path.
		:returns: Returns True if folder exists, otherwise it returns False.
		"""
		try:
			if not os.path.exists(folderpath): os.makedirs(folderpath)
		except:
			pass
		return os.path.isdir(folderpath)

	@classmethod
	def create_parent_folder(cls, fpath):
		"""Create parent folder.

		:param fpath: File/folder path located under parent folder.
		:returns: Returns True if folder exists, otherwise it returns False.
		"""
		parent_folderpath = os.path.split(fpath)[0]
		return cls.create_folder(parent_folderpath)

	@classmethod
	def alter_fname(cls, ref_filepath, fname):
		"""Replace the file/folder name.

		:param ref_filepath: Reference file path.  eg. `__file__`
		:param fname: File/folder name.
		:returns: Returns the full path of new file/folder with new name.
		"""
		return os.path.join(os.path.dirname(os.path.abspath(ref_filepath)), fname)

	@classmethod
	def alter_ext(cls, ref_filepath, ext):
		"""Replace the extension.

		:param ref_filepath: Reference file path.  eg. `__file__`
		:param ext: File extension.  eg. ".log"
		:returns: Returns the full path of new file/folder with new extension.
		"""
		return os.path.splitext(os.path.abspath(ref_filepath))[0] + ext

	@classmethod
	def normalize_fname(cls, fname):
		"""Normalize filename.

		:param fname: Original filename.
		:returns: Returns the normalized filename.
		"""
		fname = fname.strip()
		c_list = ['\\', '/', ':', '*', '?', '<', '>', '|', '"', '\t', '\b', '\n', '\r']
		for c in c_list: fname = fname.replace(c, "")
		return fname

	@classmethod
	def file_exists(cls, filepath):
		"""Check whether file exists.

		:param filepath: File path.
		:returns: True if the file exists and False if it doesn't.
		"""
		return os.path.isfile(filepath)

	@classmethod
	def folder_exists(cls, folderpath):
		"""Check whether folder exists.

		:param folderpath: Folder path.
		:returns: True if the folder exists and False if it doesn't.
		"""
		return os.path.isdir(folderpath)

	@classmethod
	def delete_file(cls, filepath):
		"""Delete a file.

		:param filepath: File path.
		:returns: Result of action.
		"""
		try:
			os.remove(filepath)
		except:
			pass
		return not cls.file_exists(filepath)

	@classmethod
	def delete_folder(cls, folderpath):
		"""Delete a folder.

		:param folderpath: Folder path.
		:returns: Result of action.
		"""
		try:
			shutil.rmtree(folderpath)
		except:
			pass
		return not cls.folder_exists(folderpath)

	@classmethod
	def copy_file(cls, source_filepath, dest_filepath):
		"""Copy a file.

		:param source_filepath: Source file path.
		:param dest_filepath: Destination file path.
		:returns: Result of action.
		"""
		try:
			shutil.copy(source_filepath, dest_filepath)
		except:
			return False
		return True

	@classmethod
	def move_file(cls, source_filepath, dest_filepath):
		"""Move a file.

		:param source_filepath: Source file path.
		:param dest_filepath: Destination file path.
		:returns: Result of action.
		"""
		try:
			shutil.move(source_filepath, dest_filepath)
		except:
			return False
		return True

	@classmethod
	def list_all(cls, folderpath, recursive=False):
		"""List all files and folders in a folder.

		:param folderpath: Folder path.
		:param recursive: Whether to look into subfolders.
		:returns: Returns a list of all files/folders, or None on failure.
			List item is as (path, is_folder), `path` is the full path of the
			file/folder, and `is_folder` is boolean value to show whether it
			is a folder (True) or a file (False).
		"""
		def __walk(folderpath, l, recursive):
			fnames = os.listdir(folderpath)
			for fname in fnames:
				fpath = os.path.join(folderpath, fname)
				if os.path.isfile(fpath):
					l.append((fpath, False))
				else:
					l.append((fpath, True))
					if recursive:
						if not __walk(fpath, l, recursive): return False
			return True

		l = []
		if not __walk(os.path.abspath(folderpath), l, recursive): return None
		return l

	@classmethod
	def list(cls, folderpath, pattern=".*", recursive=False,
		match_fullpath=False,
		include_files=True, include_folders=True):
		"""List all files and folders matching pattern in a folder.

		:param folderpath: Folder path.
		:param pattern: RegEx pattern to match file/folder.  In lower cases.
		:param recursive:  Whether to look into subfolders.
		:param match_fullpath: Whether to match file/folder name or full path.
			If it's True, match full path.  Otherwise, match file/folder name.
		:param include_files: Whether to include files.
		:param include_folders: Whether to include folders.
		:returns: Returns a list of all filees/folders matching pattern, or None
			on failure.
		"""
		l = []
		items = cls.list_all(folderpath, recursive)
		if items is None: return None
		for fpath, is_folder in items:
			#file/folder filter
			if is_folder:
				if not include_folders: continue
			else:
				if not include_files: continue

			#pattern filter
			if match_fullpath:
				text = fpath.lower()
			else:
				text = os.path.basename(fpath).lower()
			if re.fullmatch(pattern, text): l.append((fpath, is_folder))
		return l

	@classmethod
	def list_files(cls, folderpath, pattern=".*", recursive=False, match_fullpath=False):
		"""List all files matching pattern in a folder.

		See `list()` for parameter definitions.

		:returns: Returns a list of file paths matching pattern, or None on failure.
		"""
		l = []
		items = cls.list(folderpath, pattern, recursive, match_fullpath, True, False)
		if items is None: return None
		for item in items: l.append(item[0])
		return l

	@classmethod
	def list_folders(cls, folderpath, pattern=".*", recursive=False, match_fullpath=False):
		"""List all folders matching pattern in a folder.

		See `list()` for parameter definitions.

		:returns: Returns a list of folder paths matching pattern, or None on failure.
		"""
		l = []
		items = cls.list(folderpath, pattern, recursive, match_fullpath, False, True)
		if items is None: return None
		for item in items: l.append(item[0])
		return l

	@classmethod
	def load_file_contents(cls, filepath, encoding="utf-8"):
		"""Load text file into a text string.

		:param filepath: File path.
		:param encoding: Encoding of text file.
		:returns: It returns a string with full text content.
			If it's failed, returns None.
		"""
		try:
			with open(filepath, "r", encoding=encoding) as f:
				contents = f.read()
		except:
			contents = None
		return contents

	@classmethod
	def save_file_contents(cls, filepath, contents, encoding="utf-8", create_parent=True):
		"""Save text string into a text file.

		:param filepath: File path.
		:param contents: Text content.
		:param encoding: Encoding of text file.
		:param create_parent: Whether to create parent before saving.
		:returns: Result of action.
		"""
		try:
			if create_parent: cls.create_parent_folder(filepath)
			with open(filepath, "w", encoding=encoding) as f:
				f.write(contents)
			return True
		except:
			return False

	@classmethod
	def load_file_bytes(cls, filepath):
		"""Load binary file into a bytes object.

		:param filepath: File path.
		:returns: It returns a bytes object with full binary content.
			If it's failed, returns None.
		"""
		try:
			with open(filepath, "rb") as f:
				contents = f.read()
		except:
			contents = None
		return contents

	@classmethod
	def save_file_bytes(cls, filepath, contents, create_parent=True):
		"""Save bytes object into a binary file.

		:param filepath: File path.
		:param contents: Bytes object.
		:param create_parent: Whether to create parent before saving.
		:returns: Result of action.
		"""
		try:
			if create_parent: cls.create_parent_folder(filepath)
			with open(filepath, "wb") as f:
				f.write(contents)
			return True
		except:
			return False

	@classmethod
	def load_file_json(cls, filepath, encoding="utf-8"):
		"""Load JSON file into a data object.

		:param filepath: File path.
		:returns: It returns an object as JSON data describes.
			If it's failed, returns None.
		"""
		try:
			with open(filepath, "r", encoding=encoding) as f:
				data = json.load(f)
			return data
		except:
			return None

	@classmethod
	def save_file_json(cls, filepath, data, encoding="utf-8", create_parent=True):
		"""Save a data object into a JSON file.

		:param filepath: File path.
		:param data: Data object.
		:param encoding: Encoding of JSON file.
		:param create_parent: Whether to create parent before saving.
		:returns: Result of action.
		"""
		try:
			with open(filepath, "w", encoding=encoding) as f:
				json.dump(data, f, indent="\t")
			return True
		except:
			return False

class TempFileSystemObject:
	"""Base class of TempFile and TempFolder."""

	def __init__(self):
		self._is_folder = False
		self._fpath = None

	def __del__(self):
		self.delete()

	@property
	def path(self):
		"""Temp file/folder path."""
		return self._fpath

	def create(self, temp_folderpath=None):
		"""Create a temp file/folder.

		:param temp_folderpath: Temp folder path.

		:returns: Returns temp file/folder path if it's created successfully.
			Otherwise, it returns None.
		"""
		if temp_folderpath is None: temp_folderpath = tempfile.gettempdir()
		while True:
			fpath = os.path.join(temp_folderpath, str(uuid.uuid4()))
			if not os.path.exists(fpath): break
		if self._is_folder:
			if not FileSystemUtils.create_folder(fpath): return None
		else:
			FileSystemUtils.save_file_contents(fpath, "")
			if not FileSystemUtils.file_exists(fpath): return None
		return self.attach(fpath)

	def attach(self, fpath):
		"""Attach a file/folder as temp file.

		:param fpath: File/folder path.
		"""
		self.delete()
		self._fpath = fpath

	def detach(self):
		"""Detach the temp file/folder.

		.. warning::
			When the temp file/folder is detached, it will not be deleted
			automatically.  So there should be some logic to manage the
			file/folder to make sure they will not become garbage on file
			system.

		This is useful for download kind of use cases.  Before a file is
		fully downloaded, it is still in a temp status.  When it is fully
		downloaded, it could be detached and renamed to a permanent file.

		:returns: Detached temp file/folder path.
		"""
		fpath = self._fpath
		self._fpath = None
		return fpath

	def delete(self):
		"""Delete the temp file/folder."""
		if self._fpath:
			if self._is_folder:
				FileSystemUtils.delete_folder(self._fpath)
			else:
				FileSystemUtils.delete_file(self._fpath)
			self._fpath = None

class TempFile(TempFileSystemObject):
	"""Temp file."""

	def __init__(self, temp_folderpath=None):
		super().__init__()
		self._is_folder = False
		self.create(temp_folderpath)

class TempFolder(TempFileSystemObject):
	"""Temp folder."""

	def __init__(self, temp_folderpath=None):
		super().__init__()
		self._is_folder = True
		self.create(temp_folderpath)

class FileSystemDataStore(FileSystemUtils):
	r"""File system data store.

	This class is typically used to define a workspace on file system to store
	the application related data.

	It requires to specify a root folder as data store and all permanent or
	temporary data could be stored in this data store.

	It also enables the model of "dated" which could automatically managed the
	data by date.  For example, it could store the daily reports under "dated"
	folder with same filename.

	The class is derived from ``FileSystemUtils`` so that the usage of utilities
	could be easily called by a single object.

	Example::

		#global fsds object
		fsds = FileSystemDataStore(r"c:\data")

		#get a file path in workspace
		print(fsds.get_path("shared.dat"))
		# => c:\data\shared.dat

		#get a file path in workspace in date model
		print(fsds.get_dated_path("report.dat"))
		# => c:\data\2022-06-01\report.dat

		#call utilities with fsds object
		fsds.save_file_contents(fsds.get_path("raw.txt"), text)

	:ivar root_folderpath: Root folder path.
	:ivar temp_foldername: Temp folder name.
	"""

	def __init__(self, root_folderpath=None):
		#config
		self.root_folderpath = root_folderpath
		self.temp_foldername = ".temp"

	def get_path(self, fname, create_parent=False):
		"""Get full path of a file/folder in data store.

		:param fname: File/folder name.
		:param create_parent: Whether to create the parent folder.

		:returns: Full path of the file/folder.

		.. hint::
			``fname`` could be a specific name (eg. "abc.txt") or it could be
			with relative path included (eg. "reports/report1.txt").
		"""
		fpath = os.path.join(self.root_folderpath, fname)
		if create_parent: self.create_parent_folder(fpath)
		return fpath

	def get_parent_path(self, fname):
		"""Get the parent folder path of the file/folder in data store.

		:param fname: File/folder name.

		:returns: Full path of the parent folder path of the file/folder.
		"""
		return os.path.split(self.get_path(fname))[0]

	def get_dated_path(self, fname, date=None, create_parent=False):
		"""Get full path of a dated file/folder in data store.

		:param fname: File/folder name.
		:param date: Specify the date.  If it is None, use today's date.
		:param create_parent: Whether to create the parent folder.

		:returns: Full path of the dated file/folder.
		"""
		date_part = None
		if date:
			if type(date) == str:
				date_part = date
			elif type(date) == datetime.datetime:
				date_part = date.strftime("%Y-%m-%d")
		if date_part is None:
			date_part = datetime.datetime.today().strftime("%Y-%m-%d")
		fpath = os.path.join(self.root_folderpath, date_part, fname)
		if create_parent: self.create_parent_folder(fpath)
		return fpath

	def get_dated_parent_path(self, fname, date=None):
		"""Get the parent folder path of the dated file/folder in data store.

		:param fname: File/folder name.
		:param date: Specify the date.  If it is None, use today's date.

		:returns: Full path of the parent folder path of the dated file/folder.
		"""
		return os.path.split(self.get_dated_path(fname, date))[0]

	def create_temp_file(self):
		"""Create a temp file.

		:returns: Returns a TempFile object on success, otherwise it returns None.
		"""
		temp_file = TempFile(self.get_path(self.temp_foldername))
		if temp_file.path is None: return None
		return temp_file

	def create_temp_folder(self):
		"""Create a temp folder.

		:returns: Returns a TempFolder object on success, otherwise it returns None.
		"""
		temp_folder = TempFolder(self.get_path(self.temp_foldername))
		if temp_folder.path is None: return None
		return temp_folder
