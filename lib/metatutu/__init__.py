import os

__all__ = ["about"]

def about():
	about = {}
	here = os.path.abspath(os.path.dirname(__file__))
	filepath = os.path.join(here, "__version__.py")
	with open(filepath, "r", encoding="utf-8") as f:
		exec(f.read(), None, about)
	print(about["__NAME__"])
	print("Version: " + about["__VERSION__"])
	print("Author: " + about["__AUTHOR__"])
	print("Email: " + about["__AUTHOR_EMAIL__"])
