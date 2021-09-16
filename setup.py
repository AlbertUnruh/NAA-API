from distutils.core import setup


with open("requirements.txt") as f:
    requirements = f.readlines()


setup(
    name='NAA',
    packages=['NAA'],
    url='https://github.com/AlbertUnruh/NAA-API',
    license='MIT',
    author='AlbertUnruh',
    description='The API for the NAA (NetworkAttachedAlbert) project',
    install_requires=requirements
)
