#!/usr/bin/env python3
"""
Specter Setup Script
A sleek AI-powered desktop assistant
"""

from setuptools import setup, find_packages
import os
import sys

# Add the package directory to the path to import version
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'specter'))
from __version__ import (
    __version__,
    __title__,
    __description__,
    __author__,
    __author_email__,
    __license__,
    __url__,
    __keywords__,
)

# Read the contents of README file
this_directory = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

# Read requirements
with open(os.path.join(this_directory, 'requirements.txt')) as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]

setup(
    name=__title__,
    version=__version__,
    author=__author__,
    author_email=__author_email__,
    description=__description__,
    long_description=long_description,
    long_description_content_type="text/markdown",
    url=__url__,
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: POSIX :: Linux",
        "Operating System :: MacOS",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.12",
        "Topic :: Communications :: Chat",
        "Topic :: Desktop Environment",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    python_requires=">=3.12",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "specter=specter.__main__:main",
        ],
    },
    include_package_data=True,
    package_data={
        "specter": [
            "assets/**/*",
            "config/**/*",
        ],
    },
    zip_safe=False,
    keywords=", ".join(__keywords__),
    project_urls={
        "Bug Reports": "https://github.com/ghost-ng/ghost-ng/issues",
        "Source": "https://github.com/ghost-ng/ghost-ng",
        "Documentation": "https://github.com/ghost-ng/ghost-ng/tree/main/docs",
        "Releases": "https://github.com/ghost-ng/ghost-ng/releases",
    },
)
