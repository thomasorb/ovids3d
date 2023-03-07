from setuptools import setup, Extension, find_namespace_packages
import io
import os

packages = find_namespace_packages(where=".")

here = os.path.abspath(os.path.dirname(__file__))

with io.open(os.path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()
    


setup(
    name='ovids3d',
    version='0.9',
    url='https://github.com/thomasorb/ovids3d',
    license='GPLv3+',
    author='Thomas Martin',
    author_email='thomas.martin.1@ulaval.ca',
    maintainer='Thomas Martin',
    maintainer_email='thomas.martin.1@ulaval.ca',
    description='3d Visualization tools for SITELLE data',
    long_description=long_description,
    packages=packages,
    package_dir={"": "."},
    include_package_data=True,
    package_data={
        '':['LICENSE.txt', '*.rst', '*.txt', 'docs/*', '*.pyx'],
        'ovids3d':['data/*', '*.pyx']},
    exclude_package_data={
        '': ['*~', '*.so', '*.pyc'],
        'ovids3d':['*~', '*.so', '*.pyc', '*.c']},
    platforms='any',
    classifiers = [
        'Programming Language :: Python',
        'Programming Language :: Cython',
        'Development Status :: 4 - Beta',
        'Natural Language :: English',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Operating System :: OS Independent' ],
)
