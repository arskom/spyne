#!/usr/bin/env python

import os
import re

from unittest import TestLoader
from pkg_resources import resource_exists
from pkg_resources import resource_listdir
from setuptools import setup
from setuptools import find_packages

v = open(os.path.join(os.path.dirname(__file__), 'src', 'rpclib', '__init__.py'), 'r')
VERSION = re.match(r".*__version__ = '(.*?)'", v.read(), re.S).group(1)

LONG_DESC = """\
This is a simple, easily extendible rpc library that provides several useful
tools for creating and publishing web services in python.  This package
features on-demand wsdl generation for the published services, a
wsgi-compliant web application, support for complex class structures, binary
attachments, and a simple framework for creating additional serialization 
mechanisms.

This project uses lxml as it's XML API, providing full namespace support.
"""

try:
    os.stat('CHANGELOG.rst')
    LONG_DESC += open('CHANGELOG.rst', 'r').read()
except OSError:
    pass


SHORT_DESC="A transport and architecture agnostic rpc (de)serialization " \
           "library that focuses on making small, rpc-oriented messaging work."

class NoInteropLoader(TestLoader):
    def loadTestsFromModule(self, module):
        """Load unit test (skip 'interop' package).

        Hacked from the version in 'setuptools.command.test.ScanningLoader'.
        """
        tests = []
        tests.append(TestLoader.loadTestsFromModule(self,module))

        if hasattr(module, '__path__'):
            for file in resource_listdir(module.__name__, ''):
                if file == 'interop':
                    # These tests require installing a bunch of extra
                    # code:  see 'src/soaplib/test/README'.
                    continue

                if file.endswith('.py') and file != '__init__.py':
                    submodule = module.__name__ + '.' + file[:-3]
                else:
                    if resource_exists(
                        module.__name__, file + '/__init__.py'
                    ):
                        submodule = module.__name__ + '.' + file
                    else:
                        continue
                tests.append(self.loadTestsFromName(submodule))

        return self.suiteClass(tests)

setup(
    name='rpclib',
    packages=find_packages('src'),
    package_dir={'':'src'},

    version=VERSION,
    description=SHORT_DESC,
    long_description=LONG_DESC,
    classifiers=[
        'Programming Language :: Python',
        'Operating System :: OS Independent',
        'Natural Language :: English',
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
    ],
    keywords=('soap', 'wsdl', 'wsgi', 'zeromq', 'rest', 'rpc', 'json', 'http'),
    author='Burak Arslan',
    author_email='burak+rpclib@arskom.com.tr',
    maintainer='Burak Arslan',
    maintainer_email='burak+rpclib@arskom.com.tr',
    url='http://github.com/arskom/rpclib',
    license='LGPL',
    zip_safe=False,
    install_requires=[
      'pytz',
      'lxml>=2.2.1',
    ],

    entry_points = {
        'console_scripts': [
            'sort_wsdl=rpclib.test.sort_wsdl:main',
        ]
    },

    test_suite='rpclib.test',
    test_loader='__main__:NoInteropLoader',
)
