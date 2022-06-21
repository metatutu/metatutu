import os
import uuid
import datetime
import shutil

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
	def list_files(cls, folderpath, filters=None):
		"""List files in a folder.
		
		:param folderpath: Folder path.
		:param filters: Filters of file extension.  eg. [".jpg", ".bmp"]
			If it's None, then list all files.
			Otherwise, list all files with extension in the filters.

		:returns: A list of full file path meeting criteria.
		"""

		#normalize filters
		exts = [x.lower() for x in filters] if filters else None

		#list files
		filepaths = []
		try:
			fnames = os.listdir(folderpath)
			for fname in fnames:
				filepath = os.path.join(folderpath, fname)
				if not os.path.isfile(filepath): continue
				if exts is None:
					filepaths.append(filepath)
				else:
					if os.path.splitext(fname)[1].lower() in exts:
						filepaths.append(filepath)
		except:
			filepaths = None

		return filepaths

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
		"""
		try:
			if create_parent: cls.create_parent_folder(filepath)
			with open(filepath, "w", encoding=encoding) as f:
				f.write(contents)
		except:
			pass

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
        
	def create(self, temp_folderpath):
		"""Create a temp file/folder.
		
		:param temp_folderpath: Temp folder path.
		
		:returns: Returns temp file/folder path if it's created successfully.
			Otherwise, it returns None.
		"""
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
			When the temp file/folder is detached, it will not be deleted automatically.
			So there should be some logic to manage the file/folder to make sure they
			will not become garbage on file system.

		This is useful for download kind of use cases.  Before a file is fully downloaded,
		it is still in a temp status.  When it is fully downloaded, it could be detached
		and renamed to a permanent file. 

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

	def __init__(self, temp_folderpath):
		super().__init__()
		self._is_folder = False
		if temp_folderpath: self.create(temp_folderpath)

class TempFolder(TempFileSystemObject):
	"""Temp folder."""

	def __init__(self, temp_folderpath):
		super().__init__()
		self._is_folder = True
		if temp_folderpath: self.create(temp_folderpath)

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
		
		:returns:  Returns a TempFile object on success, otherwise it returns None.
		"""
		temp_file = TempFile(self.get_path(self.temp_foldername))
		if temp_file.path is None: return None
		return temp_file

	def create_temp_folder(self):
		"""Create a temp folder.
		
		:returns:  Returns a TempFolder object on success, otherwise it returns None.
		"""
		temp_folder = TempFolder(self.get_path(self.temp_foldername))
		if temp_folder.path is None: return None
		return temp_folder