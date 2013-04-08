#!/usr/bin/env python
#encoding: utf8

from distribute_setup import use_setuptools
use_setuptools()

import os
import re
import sys

from setuptools import setup
from setuptools import find_packages
from setuptools.command.test import test as TestCommand


v = open(os.path.join(os.path.dirname(__file__), 'template', '__init__.py'), 'r')
VERSION = re.match(r".*__version__ = '(.*?)'", v.read(), re.S).group(1)

SHORT_DESC="""A Template project."""

LONG_DESC = """Yes, really, just a Template project."""


setup(
    name='template',
    packages=find_packages(),

    version=VERSION,
    description=SHORT_DESC,
    long_description=LONG_DESC,
    classifiers=[
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.5',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Operating System :: OS Independent',
        'Natural Language :: English',
        'Development Status :: 4 - Beta',
    ],
    keywords=('spyne'),
    author='Jack Brown',
    author_email='jack.brown@arskom.com.tr',
    maintainer='Jack Brown',
    maintainer_email='jack.brown@arskom.com.tr',
    url='http://example.com',
    license='Your Own',
    zip_safe=False,
    install_requires=['spyne>=2.10', 'SQLAlchemy>=0.8.0'],

    entry_points={
        'console_scripts': [
            'template_daemon=template.main:main',
        ]
    },
)
