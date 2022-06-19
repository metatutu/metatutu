import os
import re
import shutil

#update build number
print("Updating build number...")

here = os.path.abspath(os.path.dirname(__file__))
filepath = os.path.join(here, "lib", "metatutu", "__version__.py")
about = {}
with open(filepath, "r", encoding="utf-8") as f:
	raw = f.read()
	exec(raw, about)
	contents = raw.splitlines()

build_number = -1
for text_line in contents:
	pos = text_line.find("__BUILD__ = ")
	if pos < 0: continue

	#remove current line
	contents.remove(text_line)

	#get current build number
	t = re.findall("\d+", text_line)
	if len(t) == 1: build_number = int(t[0])

	#stop finding
	break
if build_number < 0: build_number = 0 #reset build number
build_number += 1

contents.append("__BUILD__ = {}".format(build_number))

with open(filepath, "w", encoding="utf-8") as f:
	f.write("\n".join(contents))

print("Version: {}.{}".format(about["__VERSION__"], build_number))

#create package
print("Creating package...")

folderpath = os.path.join(here, "dist")
if os.path.isdir(folderpath):
	answer = input("Do you want to reset dist folder [Yes/No]?  ")
	if answer.lower() in ["y", "yes"]: shutil.rmtree(folderpath)

os.system("ipython setup.py sdist")

#upload package
answer = input("Do you want to upload package(s) [Yes/No]?  ")
if answer.lower() in ["y", "yes"]:
	print("Uploading package(s)...")
	os.system("twine upload dist/*")