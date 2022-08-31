import os
from setuptools import setup, find_packages

# get version information
fpath = os.path.abspath("./lib/metatutu/__version__.py")
about = {}
with open(fpath, "r", encoding="utf-8") as f:
    exec(f.read(), None, about)

# get detailed information
fpath = os.path.abspath("./README.md")
with open(fpath, "r", encoding="utf-8") as f:
    long_description = f.read()

# setup
setup(
    # version information
    name=about["__NAME__"],
    description=about["__DESC__"],
    version="{}.{}".format(about["__VERSION__"], about["__BUILD__"]),
    license=about["__LICENSE__"],
    author=about["__AUTHOR__"],
    author_email=about["__AUTHOR_EMAIL__"],
    url=about["__URL__"],
    project_urls=about["__PROJECT_URLS__"],

    # detailed information
    long_description=long_description,
    long_description_content_type="text/markdown",
    classifiers=[],

    # package information
    package_dir={"": "lib"},
    packages=find_packages("lib"),
    include_package_data=True,
    
    # requirements
    platforms="any",
    python_requires="",
    setup_requires=[],
    install_requires=[]
)
