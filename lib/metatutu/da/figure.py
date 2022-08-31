import matplotlib
import matplotlib.pyplot as plt

__all__ = ["Figure"]

class Figure:
	"""Base class of figure classes.

	Figure is basically a canvas to be with one or multiple charts on it
	to visualize one set of data, so that reader is able to focus analysing
	the data from different angle.

	This class is wrapping up the common behaviors of matplotlib usage and
	defined a simple framework to help data analyzer to focus on creating
	chart/figure rather than knowing details on how to use matplotlib.  It
	also works around some existing issue in matplotlib in subplots.

	A typical usage of Figure class is as below:

	* Create a class deriving from ``class Figure``
	* Override ``on_paint()`` to include the logic to draw charts
	* In ``on_paint()``, call ``add_chart()`` to get the ``ax`` object
	* Use ``ax`` object to draw specific chart with matplotlib

	.. hint::
		Override ``_get_chart_rect()`` could define the customized layout
		not necessarys to be in cells with rows and columns.
	
	:ivar figsize: Size of the figure in inches.
		It specifies the size in a tuple as (width, height).
	:ivar layout: Layout of the figure.
		It's similar to subplots in matplotlib, defining number of charts
		by (rows, cols).
	:ivar no_show: Defining whether the figure will be displayed.
		It's useful on Jupyter as the figure will be displayed immediately.
		When some figure is not needed to be displayed, for example, to be
		created and further processed, it could set this option to False to
		prevent it be displayed.
	:ivar filepath: File path.  If it is specified, the figure will be saved
		as file.  If it is None, then file saving action will be skipped.
	:ivar save_dpi: DPI for file saving.
	:ivar save_facecolor: Face color of figure when it is saved as file.
	:ivar save_tight: Whether the figure will be cut as "tight" model when
		it's saved to file.
	:ivar data_binding: This variable is used to bundle the source data
		of chart(s) on figure as part of framework defined.
	"""

	def __init__(self):
		# config
		self.figsize = (20, 10)
		self.layout = (1, 1)
		self.no_show = False
		self.filepath = None
		self.save_dpi = 72
		self.save_facecolor = "white"
		self.save_tight = False
		self.data_binding = None

		# control
		self._f = None

	def _get_chart_rect(self, pos=None):
		if pos is None:
			return (0.0, 0.0, 1.0, 1.0)
		elif type(pos) is tuple:
			rows, cols = self.layout
			row, col = pos
			if row >= 0 and row < rows and col >= 0 and col < cols:
				l = col / cols
				t = row / rows
				r = (col + 1) / cols
				b = (row + 1) / rows
				return (l, t, r, b)
		else:
			rows, cols = self.layout
			row = int((pos - 1) / cols)
			col = (pos - 1) % cols
			return self._get_chart_rect((row, col))
		return None

	def add_chart(self, title=None, pos=None, padding=(0.125, 0.12, 0.10, 0.11)):
		"""Add a chart.
		
		It's basically to define an axes system for drawing on the figure (canvas).

		:param title: Chart title.  If it's given, chart title will be created.
		:param pos: Position of the chart.
			If it's None, then the full figure (canvas) will be used for the chart.
			If it's given as a number (int), it will be treated as an index
			value (starting from 1), based on the figure layout, it will locate
			the right cell on figure.  (left to right, up to down)
			If it's given as (row, col), it will locate to the cell on figure
			based on the figure layout.
		:param padding: Padding of the chart area.
			It specifies the padding on each side as (left, top, right, bottom)
			in percentage.  eg. (0.1, 0.1, 0.1, 0.1) means 10% of width padding
			will be on left and right sides, and 10% of height padding will be
			on top and bottom sides.
		"""
		rect = self._get_chart_rect(pos)
		if rect is None: return None
		l, t, r, b = rect
		w = r - l
		h = b - t
		ax = self._f.add_axes([
			l + w * padding[0], 
			1 - (b - h * padding[3]), 
			w * (1.0 - padding[0] - padding[2]), 
			h * (1.0 - padding[1] - padding[3])])
		if title: plt.title(title)
		return ax

	def save_figure(self, filepath):
		"""Save figure as file.

		:param filepath: File path.
		"""
		if filepath:
			self._f.savefig(
				filepath,
				dpi=self.save_dpi,
				facecolor=self.save_facecolor,
				bbox_inches=("tight" if self.save_tight else None))

	def on_create_figure(self):
		"""Event handler called when a figure is being created."""
		self._f = plt.figure(figsize=self.figsize)

	def on_paint(self):
		"""Event handler called when a figure is created and needs to be painted.
		
		:returns: Returns False to stop further workflow.
		"""
		pass

	def on_save_figure(self):
		"""Event handler called when a figure is being saved to file after painted."""
		self.save_figure(self.filepath)

	def on_show_figure(self):
		"""Event handler called when a figure is being displayed after painted."""
		if not self.no_show: self._f.show(warn=False)

	def paint(self, show_error=False):
		"""Paint figure.

		Call this to run the workflow defined by framework to create figure,
		paint charts, save file and display.

		:param show_error: Whether to display errors (typically from matplotlib).
		"""
		old_backend = matplotlib.get_backend()
		backend_switched = False
		try:
			# switch backend if needed
			if self.no_show:
				matplotlib.use("agg")
				backend_switched = True

			# create figure
			self.on_create_figure()

			# paint
			painted = True
			r = self.on_paint()
			if r is not None:
				if r == False: painted = False
			if painted:
				# save figure
				self.on_save_figure()

				# show figure
				self.on_show_figure()

			# delete figure
			del self._f
			self._f = None
		except Exception as e:
			if show_error: print(e)
		finally:
			if backend_switched:
				matplotlib.use(old_backend)


