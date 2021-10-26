from setuptools import setup
import re


with open("NAA/__init__.py") as f:
    file = f.read()

version = re.search(r"^__version__\s*=\s*[\'\"]([^\'\"]*)[\'\"]", file, re.MULTILINE).group(1)
url = re.search(r"^__url__\s*=\s*[\'\"]([^\'\"]*)[\'\"]", file, re.MULTILINE).group(1)
license = re.search(r"^__license__\s*=\s*[\'\"]([^\'\"]*)[\'\"]", file, re.MULTILINE).group(1)  # noqa
author = re.search(r"^__author__\s*=\s*[\'\"]([^\'\"]*)[\'\"]", file, re.MULTILINE).group(1)


with open("requirements.txt") as f:
    requirements = f.readlines()


name = "NAA"
packages = [
    f"{name}"
]


setup(
    name=name,
    version=version,
    packages=packages,
    url=url,
    license=license,
    author=author,
    install_requires=requirements
)
