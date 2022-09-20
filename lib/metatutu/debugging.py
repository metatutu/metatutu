"""
    This is part of METATUTU library.
    https://pypi.org/project/metatutu/

	:author: max.wu@wooloostudio.com
	:copyright: Copyright 2022 Wooloo Studio.  All rights reserved.
	:license: see LICENSE.
"""

import time

class Clocker:
	"""Clocker for debugging."""

	def __init__(self):
		self.checkpoints = []
		self.reset()
	
	def reset(self):
		"""Reset."""
		self.checkpoints.clear()
		self.record()

	def record(self, label=""):
		"""Record a checkpoint.

		:param label: Label of the checkpoint to identify the phase
			from previous checkpoint to current one.
		"""
		self.checkpoints.append((label, time.perf_counter()))

	def __enter__(self):
		self.reset()
		return self

	def __exit__(self, exc_type, exc_val, exc_tb):
		self.record()

	def results(self):
		"""Get summary of timing results.

		:returns: A list of timing results for each phase (end by checkpoint).
			Each result is in format of (label, duration in seconds).
		"""
		results = []
		if len(self.checkpoints) <= 1: return results
		last_timestamp = None
		for (label, timestamp) in self.checkpoints:
			if last_timestamp is not None:
				results.append((label, timestamp - last_timestamp))
			last_timestamp = timestamp
		return results

	def results_text(self):
		"""Get summary of timing results in text.
		
		:returns: Text of summary of timing results for display.
		"""
		results = self.results()
		text = ""
		index = 1
		for (label, duration) in results:
			if text != "": text += "\r\n"
			if label == "":
				text += "(#{}): {:.1f} seconds".format(index, duration)
			else:
				text += "{}: {:.1f} seconds".format(label, duration)
			index += 1
		return text

	def duration(self, label=None):
		"""Get duration of the phase.

		:param label: Checkpoint label of the phase to be queried.
			If it's None, return the duration of the last phase.
		
		:returns: The duration of the phase in seconds.
			Returns None when the checkpoint is not found.
		"""
		results = self.results()
		results.reverse()
		if label is None:
			if len(results) > 0: return results[0][1]
		else:
			for (label2, duration) in results:
				if label2 == label: return duration
		return None
