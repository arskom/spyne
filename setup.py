#!/usr/bin/env python

import os
import re

from unittest import TestLoader
from pkg_resources import resource_exists
from pkg_resources import resource_listdir
from setuptools import setup
from setuptools import find_packages

v = open(os.path.join(os.path.dirname(__file__), 'spyne', '__init__.py'), 'r')
VERSION = re.match(r".*__version__ = '(.*?)'", v.read(), re.S).group(1)

LONG_DESC = """Spyne aims to save the protocol implementers the hassle of
implementing their own remote procedure call api and the application programmers
the hassle of jumping through hoops just to expose their services using multiple
protocols and transports."""


try:
    os.stat('CHANGELOG.rst')
    LONG_DESC += open('CHANGELOG.rst', 'r').read()
except OSError:
    pass


SHORT_DESC="""A transport and architecture agnostic rpc library that focuses on
exposing public services with a well-defined API."""


setup(
    name='spyne',
    packages=find_packages(),

    version=VERSION,
    description=SHORT_DESC,
    long_description=LONG_DESC,
    classifiers=[
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.4',
        'Programming Language :: Python :: 2.5',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Operating System :: OS Independent',
        'Natural Language :: English',
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
    ],
    keywords=('soap', 'wsdl', 'wsgi', 'zeromq', 'rest', 'rpc', 'json', 'http',
              'msgpack', 'xml'),
    author='Burak Arslan',
    author_email='burak+spyne@arskom.com.tr',
    maintainer='Burak Arslan',
    maintainer_email='burak+spyne@arskom.com.tr',
    url='http://github.com/arskom/spyne',
    license='LGPL-2.1',
    zip_safe=False,
    install_requires=[
      'pytz',
      'lxml<3',
    ],

    entry_points = {
        'console_scripts': [
            'sort_wsdl=spyne.test.sort_wsdl:main',
        ]
    },
)
