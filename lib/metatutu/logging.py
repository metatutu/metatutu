"""
    This is part of METATUTU library.
    https://pypi.org/project/metatutu/

	:author: max.wu@wooloostudio.com
	:copyright: Copyright (C) 2022 Wooloo Studio.  All rights reserved.
	:license: see LICENSE.
"""

import os
import time
import threading
import traceback
from abc import ABC, abstractmethod
import metatutu.pipeline

__all__ = [
	"MessageLevel",
	"Logger",
	"TextLogger",
	"ConsoleLogger",
	"TextFileLogger", "FileLogger", "DatedFileLogger",
	"Loggers",
	"LoggerHelper"]

class MessageLevel:
	"""Message level."""
	GENERAL = 5
	DEBUG = 10
	INFO = 20
	WARNING = 30
	ERROR = 40
	CRITICAL = 50
	SEPARATOR = 100

class Logger(ABC):
	"""Base class of logger classes.

	It's an abstract class, implementation of specific logger needs to override
	`_log()` to handle the logging message output in certain format to certain
	output device.

	:ivar enabled_level: Minimal level of message to be logged.
		It's kind of filter of logging messages.  All messages at `enabled_level`
		or higher will be logged.  Otherwise, it will be ignored.  For example,
		if it's set to `MessageLevel.CRITICAL`, then only messages at level of
		50 or above will be logged.
	:ivar async_mode: Whether to use async mode to log messages.
		Async mode is the way to avoid program be blocked by the logging.
		It will cache the logging message and the message will be logged to
		particular devices in a separate thread.
	:ivar async_queuesize: Size of logging message queue (cache).
		It' valid for async mode only to specify how many messages would be
		cached at peak time.
	:ivar async_timeout: Timeout of caching message.
		This is valid for async mode only.  When logging message queue (cache)
		is full, even under async mode, calling thread will be blocked.
		This value is to define how long it will wait or the message will be
		discarded.  Set it to None to wait infinitely.

	.. warning::
		When the logger is running under async mode, make sure `close()` will be
		called explicitly, otherwise, the main program could be dead locked due
		the threading handling mechanism in Python.
	"""
	def __init__(self):
		# config
		self.enabled_level = 0  # record all messages (level >= 0)
		self.async_mode = False
		self.async_queuesize = 100
		self.async_timeout = None

		# control
		self.__async_logger = None
		self._log_lock = threading.Lock()

	def __del__(self):
		if self.__async_logger:
			raise Exception("close() must be called explicitly for async mode.")

	class __AsyncLogger(metatutu.pipeline.Doer):
		def __init__(self, maxsize, logger):
			super().__init__(maxsize)
			self.logger = logger

		def _process_task(self, task):
			with self.logger._log_lock:
				self.logger._log(task[0], task[1], task[2], task[3])

	def open(self):
		"""Open the logger.

		No need to call it explicitly.  Framework will call it automatically.
		"""
		if self.async_mode:
			if self.__async_logger is None:
				self.__async_logger = self.__AsyncLogger(self.async_queuesize, self)
				self.__async_logger.hire()

	def close(self):
		"""Close the logger.

		It's required to call it explicitly for async mode.
		"""
		if self.__async_logger:
			self.__async_logger.dismiss()
			del self.__async_logger
			self.__async_logger = None

	@abstractmethod
	def _log(self, timestamp, message, depth, level): pass

	def __log(self, timestamp, message, depth, level, std_level):
		# open anyway
		self.open()

		# log
		if level >= self.enabled_level:
			if self.async_mode:
				self.__async_logger.task_queue.push_task(
					(timestamp, message, depth, std_level), 100, self.async_timeout
				)
			else:
				with self._log_lock:
					self._log(timestamp, message, depth, std_level)

	def log(self, message, depth=0, level=MessageLevel.GENERAL):
		self.__log(time.time(), message, depth, level, MessageLevel.GENERAL)

	def debug(self, message, depth=0, level=MessageLevel.DEBUG):
		self.__log(time.time(), message, depth, level, MessageLevel.DEBUG)

	def info(self, message, depth=0, level=MessageLevel.INFO):
		self.__log(time.time(), message, depth, level, MessageLevel.INFO)

	def warning(self, message, depth=0, level=MessageLevel.WARNING):
		self.__log(time.time(), message, depth, level, MessageLevel.WARNING)

	def error(self, message, depth=0, level=MessageLevel.ERROR):
		self.__log(time.time(), message, depth, level, MessageLevel.ERROR)

	def critical(self, message, depth=0, level=MessageLevel.CRITICAL):
		self.__log(time.time(), message, depth, level, MessageLevel.CRITICAL)

	def separator(self, ch="=", width=80, level=MessageLevel.SEPARATOR):
		self.__log(time.time(), ch * width, 0, level, MessageLevel.SEPARATOR)

	def exception(self, ex, depth=0, level=MessageLevel.DEBUG):
		message = "EXCEPTION: " + str(ex) + "\n"
		message += traceback.format_exc()
		self.__log(time.time(), message, depth, level, MessageLevel.GENERAL)

class TextLogger(Logger):
	"""Base class of text logger classes.

	This is the base class and defines the common behaviors of the loggers
	with text based output.

	:ivar include_timestamp: Whether to include the timestamp.
		This is useful to use logger for console applications.  For the
		logger on console, it could hide the timestamp to show the sequence
		with logging messages only.
	:ivar use_utc: Whether to use UTC or local time for timestamp.
	:ivar indent_size: Size of indent for the depth.
		Depth is the unique functionality in this logging system, to make
		the calling stack for complex workflow clearer.  For the logging
		messages for each depth, it will be displayed in hierachy format.
	:ivar vline: The charactor to be used to represent the vertical line.
	"""
	def __init__(self):
		Logger.__init__(self)

		# config
		self.include_timestamp = True
		self.use_utc = False
		self.indent_size = 4
		self.vline = "|"

	def format_output(self, timestamp, message, depth, level):
		# separator
		if level == MessageLevel.SEPARATOR: return message

		# create timestamp text
		ts_text = ""
		if self.include_timestamp:
			if self.use_utc:
				ts_text = time.strftime("%Y-%m-%d %H:%M:%SZ ", time.gmtime(timestamp))
			else:
				ts_text = time.strftime("%Y-%m-%d %H:%M:%S ", time.localtime(timestamp))

		# create message text
		message_text = ""
		if level == MessageLevel.DEBUG:
			message_text = message
		elif level == MessageLevel.INFO:
			message_text = "INFO: " + message
		elif level == MessageLevel.WARNING:
			message_text = "WARNING: " + message
		elif level == MessageLevel.ERROR:
			message_text = "ERROR: " + message
		elif level == MessageLevel.CRITICAL:
			message_text = "CRITICAL: " + message
		else:
			message_text = message
		message_lines = message_text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
		if len(message_lines) == 0: return ts_text

		# create indent text
		indent_size = self.indent_size
		indent_text = ""
		if depth < 0: depth = 0
		if indent_size < 0: indent_size = 0
		if indent_size < 3:
			indent_text = " " * indent_size
		else:
			if len(self.vline) == 1:
				indent_text = self.vline + " " * (indent_size - 1)
			else:
				indent_text = " " * indent_size

		# format output
		output_text = ""
		for i in range(0, len(message_lines)):
			if i == 0:
				output_text = ts_text + indent_text * depth + message_lines[i]
			else:
				output_text += "\n" + " " * len(ts_text) + indent_text * depth + message_lines[i]

		#
		return output_text

class ConsoleLogger(TextLogger):
	"""Logger for console."""
	def __init__(self):
		TextLogger.__init__(self)

	def _log(self, timestamp, message, depth, level):
		output_text = self.format_output(timestamp, message, depth, level)
		print(output_text)

class TextFileLogger(TextLogger):
	"""Base class of logger classes for text file (log file).

	:ivar encoding: Encoding of text file.
	:ivar mode: Open mode of the text file.
	:ivar auto_flush: Whether to flush on each log activity.
	"""
	def __init__(self):
		TextLogger.__init__(self)

		# config
		self.encoding = "utf-8"
		self.mode = "a"
		self.auto_flush = True

		# control
		self._files = []

	def __del__(self):
		self.close()

	def close(self):
		TextLogger.close(self)

		# close all files
		for file in self._files:
			if file is not None: file.close()
		self._files.clear()

	@abstractmethod
	def _get_file(self, timestamp, message, depth, level): pass

	def _log(self, timestamp, message, depth, level):
		output_text = self.format_output(timestamp, message, depth, level)
		file = self._get_file(timestamp, message, depth, level)
		if file:
			print(output_text, file=file)
			if self.auto_flush: file.flush()

class FileLogger(TextFileLogger):
	"""Logger for a standalone log file."""
	def __init__(self, filepath, reset=False):
		TextFileLogger.__init__(self)

		# control
		self._files = [None]
		self._filepath = filepath
		if reset: self.mode = "w"

	def _get_file(self, timestamp, message, depth, level):
		f = self._files[0]
		if f: return f
		try:
			f = open(self._filepath, mode=self.mode, encoding=self.encoding)
			if f: self._files[0] = f
		except:
			f = None
		return f

class DatedFileLogger(TextFileLogger):
	"""Logger for dated log files."""
	def __init__(self, folderpath):
		TextFileLogger.__init__(self)

		# control
		self._files = [None]
		self._folderpath = folderpath
		self._current_filepath = ""

	def _get_file(self, timestamp, message, depth, level):
		# get file path
		filename = ""
		if self.use_utc:
			filename = time.strftime("%Y-%m-%d.log", time.gmtime(timestamp))
		else:
			filename = time.strftime("%Y-%m-%d.log", time.localtime(timestamp))
		filepath = os.path.join(self._folderpath, filename)
		if filepath == self._current_filepath: return self._files[0]

		# close current file
		if self._files[0]:
			self._files[0].close()
			self._files[0] = None
			self._current_filepath = ""

		# open file
		f = None
		try:
			f = open(filepath, mode=self.mode, encoding=self.encoding)
			if f:
				self._files[0] = f
				self._current_filepath = filepath
		except:
			f = None
		return f

class Loggers:
	"""Aggregator of loggers.

	It will distribute the log messages to all loggers registered.
	"""
	def __init__(self):
		self.loggers = []

	def __del__(self):
		self.close()

	def close(self):
		for logger in self.loggers: logger.close()
		self.loggers.clear()

	def register_logger(self, logger):
		"""Register a logger.

		:param logger: A logger instance.
		"""
		self.loggers.append(logger)

	def log(self, message, depth=0, level=MessageLevel.GENERAL):
		for logger in self.loggers: logger.log(message, depth, level)

	def debug(self, message, depth=0, level=MessageLevel.DEBUG):
		for logger in self.loggers: logger.debug(message, depth, level)

	def info(self, message, depth=0, level=MessageLevel.INFO):
		for logger in self.loggers: logger.info(message, depth, level)

	def warning(self, message, depth=0, level=MessageLevel.WARNING):
		for logger in self.loggers: logger.warning(message, depth, level)

	def error(self, message, depth=0, level=MessageLevel.ERROR):
		for logger in self.loggers: logger.error(message, depth, level)

	def critical(self, message, depth=0, level=MessageLevel.CRITICAL):
		for logger in self.loggers: logger.critical(message, depth, level)

	def separator(self, ch="=", width=80, level=MessageLevel.SEPARATOR):
		for logger in self.loggers: logger.separator(ch, width, level)

	def exception(self, ex, depth=0, level=MessageLevel.DEBUG):
		for logger in self.loggers: logger.exception(ex, depth, level)

class LoggerHelper:
	"""Helper for classes need logging.

	This is to be used to bind a logger with a class which needs logging
	functions.
	"""
	def __init__(self):
		self._logger = None

	@property
	def logger(self):
		return self._logger

	def bind_logger(self, logger):
		self._logger = logger

	def log(self, message, depth=0, level=MessageLevel.GENERAL):
		if self._logger: self._logger.log(message, depth, level)

	def debug(self, message, depth=0, level=MessageLevel.DEBUG):
		if self._logger: self._logger.debug(message, depth, level)

	def info(self, message, depth=0, level=MessageLevel.INFO):
		if self._logger: self._logger.info(message, depth, level)

	def warning(self, message, depth=0, level=MessageLevel.WARNING):
		if self._logger: self._logger.warning(message, depth, level)

	def error(self, message, depth=0, level=MessageLevel.ERROR):
		if self._logger: self._logger.error(message, depth, level)

	def critical(self, message, depth=0, level=MessageLevel.CRITICAL):
		if self._logger: self._logger.critical(message, depth, level)

	def separator(self, ch="=", width=80, level=MessageLevel.SEPARATOR):
		if self._logger: self._logger.separator(ch, width, level)

	def exception(self, ex, depth=0, level=MessageLevel.DEBUG):
		if self._logger: self._logger.exception(ex, depth, level)
