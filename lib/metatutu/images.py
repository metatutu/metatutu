"""
    This is part of METATUTU library.
    https://pypi.org/project/metatutu/

	:author: max.wu@wooloostudio.com
	:copyright: Copyright (C) 2022 Wooloo Studio.  All rights reserved.
	:license: see LICENSE.
"""

import numpy as np
from PIL import Image, ImageDraw, ImageFont
import imageio

class Images:
	"""Image list.

	It defines a list of Image objects and offer the tools for images processing.

	:ivar images: List of image objects.
	"""
	def __init__(self):
		self.images = []

	def clear(self):
		"""Clear image list."""
		self.images.clear()

	def append(self, image):
		"""Append an image to the list.

		:param image: Image object.
		"""
		self.images.append(image)

	def append_file(self, filepath, mode=None):
		"""Append an image from file to the list.

		:param filepath: Image file path.
		:param mode: Expected image mode in memory.
			If it is specified, it will convert the image into the mode.
			If it is None, then leave it as the image file format.
			See ``PIL.Image.MODES`` for details.

		:returns: Returns True on success or False on failure.
		"""
		try:
			if mode:
				image = Image.open(filepath).convert(mode)
			else:
				image = Image.open(filepath)
			self.images.append(image)
			return True
		except:
			return False

	def append_files(self, filepaths, mode=None):
		"""Append images from files to the list.

		:param filepaths: Image file path list.
		:param mode: See ``append_file()``.

		:returns: Returns True or success or False on failure.
		"""
		for filepath in filepaths:
			if not self.append_file(filepath, mode): return False
		return True

	def stitch(self, vertical=True, auto_crop=True):
		"""Stitch images into one image.

		:param vertical: If it's True, then all images will be stitched in
			**y** direction from up to down.  Otherwise, images will be
			stitched in **x** direction from left to right.
		:param auto_crop: Whether to crop the images to make sure they
			could be stitched together in specified direction.  If it's True,
			it will align the minimal width or height for vertical or horizontal
			direction.  If it's False, if images width or height are not aligned,
			it will return None to stop the process.

		:returns: Returns stitched image object on success or None on failure.
		"""
		# pass 1: get min size
		min_width = 1000000
		max_width = 0
		min_height = 1000000
		max_height = 0
		for image in self.images:
			width, height = image.size
			min_width = min(width, min_width)
			max_width = max(width, max_width)
			min_height = min(height, min_height)
			max_height = max(height, max_height)

		# pass 2： normalize size and create bitmaps
		bitmaps = []
		axis = 0
		if vertical:
			axis = 0
			if (not auto_crop) and (min_width != max_width): return None
			for image in self.images:
				width, height = image.size
				if width > min_width:
					bitmap = np.array(image.crop((0, 0, min_width, height)))
				else:
					bitmap = np.array(image)
				bitmaps.append(bitmap)
		else:
			axis = 1
			if (not auto_crop) and (min_height != max_height): return None
			for image in self.images:
				width, height = image.size
				if height > min_height:
					bitmap = np.array(image.crop((0, 0, width, min_height)))
				else:
					bitmap = np.array(image)
				bitmaps.append(bitmap)

		# stitch bitmaps and create stitched image
		return Image.fromarray(np.concatenate(tuple(bitmaps), axis=axis))

	def create_gif(self, filepath, duration, loop=0):
		"""Create GIF image file with images.

		:param filepath: Output GIF image file path.
		:param duration: Duration of each image frame.
		:param loop: Loop times.
		"""
		imageio.mimsave(filepath, self.images, "gif", duration=duration, loop=loop)
