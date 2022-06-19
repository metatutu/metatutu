import os
import re
import shutil

root_path = os.path.abspath(".")

class task:
	def __init__(self, name):
		self.name = name
	
	def __enter__(self):
		print(">>>>>>>> Begin {} >>>>>>>>".format(self.name))
	
	def __exit__(self, exc_type, exc_val, exc_tb):
		print("<<<<<<<< End {} <<<<<<<<".format(self.name))

def delete_file(fpath):
	if os.path.isfile(fpath):
		print("Deleting file: {}...".format(fpath))
		os.remove(fpath)

def delete_folder(fpath):
	if os.path.isdir(fpath):
		print("Deleting folder: {}".format(fpath))
		shutil.rmtree(fpath)

def task_doc_clean():
	with task("Clean Doc"):
		doc_path = os.path.join(root_path, "doc")
		delete_folder(os.path.join(doc_path, "build"))
		delete_file(os.path.join(doc_path, "source", "metatutu.rst"))
		delete_file(os.path.join(doc_path, "source", "modules.rst"))

def task_doc_build():
	with task("Build Doc"):
		doc_path = os.path.join(root_path, "doc")
		os.chdir(doc_path)
		os.system("sphinx-apidoc -o ./source ../lib/metatutu")
		os.system("make html")

def task_version_update():
	with task("Update Version"):
		file_path = os.path.join(root_path, "lib", "metatutu", "__version__.py")
		about = {}
		with open(file_path, "r", encoding="utf-8") as f:
			source = f.read()
			exec(source, about)
			contents = source.splitlines()

		build_number = -1
		for text_line in contents:
			pos = text_line.find("__BUILD__ = ")
			if pos < 0: continue
			contents.remove(text_line)
			t = re.findall("\d+", text_line)
			if len(t) == 1: build_number = int(t[0])
			break
		if build_number < 0: build_number = 0  #reset
		build_number += 1

		contents.append("__BUILD__ = {}".format(build_number))
		with open(file_path, "w", encoding="utf-8") as f:
			f.write("\n".join(contents))

		print("Version: {}.{}".format(about["__VERSION__"], build_number))

def task_package_clean():
	with task("Clean Package(s)"):
		delete_folder(os.path.join(root_path, "dist"))
		delete_folder(os.path.join(root_path, "lib", "metatutu.egg-info"))

def task_package_build():
	with task("Build Package(s)"):
		os.chdir(root_path)
		os.system("python setup.py sdist")

def task_package_upload():
	with task("Upload Package(s)"):
		os.chdir(root_path)
		os.system("twine upload dist/*")

def menu():
	print("BUILD tool for Metatutu Library")
	print("Copyright (C) 2022 Wooloo Studio.  All rights reserved.")
	print("=" * 60)
	print("Single Task Commands:")
	print("  [A] Clean Doc")
	print("  [B] Build Doc")
	print("  [C] Update Version")
	print("  [D] Clean Package(s)")
	print("  [E] Build Package(s)")
	print("  [F] Upload Package(s)")
	print("-" * 60)
	print("Workflow Commands:")
	print("  [0] Clean All (A/D)")
	print("  [1] Build All (B/C/E)")
	print("  [2] Rebuild All & Upload (A/B/C/D/E/F)")
	print("=" * 60)
	return input("Please enter the command of task or workflow to proceed: ")

command = menu().upper()
if command == "A":
	task_doc_clean()
elif command == "B":
	task_doc_build()
elif command == "C":
	task_version_update()
elif command == "D":
	task_package_clean()
elif command == "E":
	task_package_build()
elif command == "F":
	task_package_upload()
elif command == "0":
	task_doc_clean()
	task_package_clean()
elif command == "1":
	task_doc_build()
	task_version_update()
	task_package_build()
elif command == "2":
	task_doc_clean()
	task_doc_build()
	task_version_update()
	task_package_clean()
	task_package_build()
	task_package_upload()