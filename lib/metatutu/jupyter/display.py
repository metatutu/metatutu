import time
import uuid
import pandas as pd
from IPython.display import *

__all__ = ["Display", "HTMLDisplay", "ProgressDisplay"]

class Display:
	"""Base class of Display classes.
	
	:ivar min_interval: Minimum interval between 2 refreshes.  In seconds.
	"""

	def __init__(self):
		#config
		self.min_interval = 0.5  #minimum interval between 2 refreshes
        
		#control
		self._display_id = None
		self._last_refresh_ts = time.time()
    
	def _refresh(self, content, force=False):
		if (not force) and (self._display_id is not None):
			if (time.time() - self._last_refresh_ts) < self.min_interval: 
				return
		if self._display_id is None:
			self._display_id = str(uuid.uuid4())
			display(content, display_id=self._display_id)
		else:
			update_display(content, display_id=self._display_id)
		self._last_refresh_ts = time.time()
    
	def _display(self, content, force=False):
		self._refresh(content, force)
            
	def clear(self):
		self._refresh(HTML(""))

class HTMLDisplay(Display):
	"""Display HTML data in Jupyter Notebooks.  
	
	This is also the base class of all other Display classes to be displayed
	with HTML content."""

	def __init__(self):
		Display.__init__(self)
    
	def _get_html(self):
		return ""
    
	def _display_html(self, force=False):
		self._display(HTML(self._get_html()), force)

	@classmethod
	def display(cls, html):
		"""Display HTML content.
		
		:param html: HTML content.
		"""
		Display()._display(HTML(html), True)

	@classmethod
	def display_div(cls, html, width=None, height=None, style=None):
		"""Display HTML content in a <div> block.
		
		:param html: HTML content.
		:param width: Width of <div> block.  Optional.
		:param height: Height of <div> block.  Optional.
		:param style: Style of <div> block.  Optional.
		
		.. warning::
			When ``style`` is given, ``width`` and ``height`` will be ignored.
		"""
		div_style = ""
		if style:
			div_style = "style='{}'".format(style)
		else:
			style_width = ""
			if width is None:
				pass
			elif type(width) == str:
				style_width = "width: {}".format(width)
			elif type(width) == int:
				style_width = "width: {}px".format(width)
            
			style_height = ""
			if height is None:
				pass
			elif type(height) == str:
				style_height = "height: {}".format(height)
			elif type(height) == int:
				style_height = "height: {}px".format(height)

			if style_width != "" or style_height != "":
				div_style = "style='{}; {}'".format(style_width, style_height)
        
		cls.display("<div {}>{}</div>".format(div_style, html)) 
        
	@classmethod
	def display_head(cls, text, level=5):
		"""Display content in <h> tags.

		:param text: Text to be displayed.
		:param level: Level of head.
			For example, if level is 5, then ``text`` will be displayed in
			``<h5>`` tags.
		"""
		cls.display("<h{}>{}</h{}>".format(level, text, level))

	@classmethod
	def display_dataframe(cls, df, rows=None, width="100%", height=200, style=None):
		"""Display DataFrame object (pandas) in HTML format.
		
		:param df: DataFrame object.
		:param rows: Rows to be displayed.  
			If it is None, then display all rows.
			If it is a positive number, then display number of head rows.
			If it is a negative number, then display number of tail rows.
		:param width: See ``display_div()``.
		:param height: See ``display_div()``.
		:param style: See ``display_div()``.

		The table heads (columns head) will be sticky.
		"""
		if type(df) != pd.DataFrame: return
		html_df = None
		if rows:
			if rows >= 0:
				html_df = df.head(rows).style.set_sticky(1).to_html()
			else:
				html_df = df.tail(-rows).style.set_sticky(1).to_html()
		else:
			html_df = df.style.set_sticky(1).to_html()
		cls.display_div(html_df, width, height, style)
        
class ProgressDisplay(HTMLDisplay):
	"""Progress display.
	
	:ivar show_text: Whether to show progress text.
	:ivar text_prefix: Text prefix.
	:ivar show_progress_bar: Whether to show progress bar.
	:ivar progress_bar_width: Progress bar width.
	:ivar hide_progress_bar_on_finished: Whether to hide the progress bar
		when workflow is finisihed.

	A typical usage for a workflow could be as below::

		#create progress display object
		p = ProgressDisplay()

		#before workflow start
		p.on_init(total_task_count)

		#workflow
		for task in tasks:
		    #update progress
		    p.on_update(completed_task_count)

		#after workflow
		p.on_finish()

	If you want to customize the progress text, create derived class and
	override ``get_text()`` to specify the text format.
	"""
	def __init__(self):
		HTMLDisplay.__init__(self)
		#config
		self.show_text = True
		self.text_prefix = ""
		self.show_progress_bar = True
		self.progress_bar_width = "100%"
		self.hide_progress_bar_on_finished = True

		#control
		self._progress = 0
		self._total = 100
		self._finished = False
		self._start_ts = time.time()
		self._end_ts = time.time()
    
	def _get_html(self):
		html = "<div>"
		if self.show_progress_bar:
			if self._finished and self.hide_progress_bar_on_finished:
				pass
			else:
				html += "<progress style='width:{}' max='{}' value='{}'></progress>".format(
					self.progress_bar_width, self._total, self._progress)
		if self.show_text:
			html += "<p>{}</p>".format(self.get_text(self._finished))
		html += "</div>"
		return html
    
	def get_text(self, finished):
		"""Create progress text.

		This is called by framework to create progress text.
		Derived class may override it to customize the progress text.
		"""
		if self._total > 0:
			return "{} {} of {}/{:.1f}% (elapsed: {:.1f} seconds)".format(
				self.text_prefix, 
				self._progress, self._total, 
				self._progress / self._total * 100.0, 
				self.elapsed())
		else:
			return "{} {} (elapsed: {:.1f} seconds)".format(
				self.text_prefix, self._progress, self.elapsed())
        
	def elapsed(self):
		"""Get time elapsed for the workflow.
		
		:returns: Time eplased since ``on_init()`` invoked.  In seconds.
		"""
		return self._end_ts - self._start_ts
    
	def on_init(self, total):
		"""Initialize progress.

		Call it before workflow is started.

		:param total: Total workload.
		"""
		self._progress = 0
		self._total = total
		self._finished = False
		self._start_ts = time.time()
		self._display_html(True)
        
	def on_update(self, progress):
		"""Update progress.

		Call it during workflow to specify how much had been achieved.

		:param progress: Progress so far.
		"""
		self._end_ts = time.time()
		self._progress = progress
		self._display_html(False)
		
	def on_finish(self, total=None):
		"""Finish progress.

		Call it after workflow is finished.

		:param total: Reset the total workload for the cases total was
			unknown until finished.
		"""
		self._end_ts = time.time()
		if total: self._total = total
		self._finished = True
		self._display_html(True)