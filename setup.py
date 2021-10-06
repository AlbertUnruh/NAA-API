from setuptools import setup
import re


with open("requirements.txt") as f:
    requirements = f.readlines()


with open("NAA/__init__.py") as f:
    version = re.search(r"^__version__\s*=\s*[\'\"]([^\'\"]*)[\'\"]", f.read(), re.MULTILINE).group(1)


setup(
    name='NAA',
    version=version,
    packages=['NAA'],
    url='https://github.com/AlbertUnruh/NAA-API',
    license='MIT',
    author='AlbertUnruh',
    description='The API for the NAA (NetworkAttachedAlbert) project',
    install_requires=requirements
)
