#!/usr/bin/env python

from setuptools import setup, find_packages

VERSION = '1.1.1'
LONG_DESC = """\
This is a simple, easily extendible rpc library that provides several useful
tools for creating and publishing web services in python.  This package
features on-demand wsdl generation for the published services, a
wsgi-compliant web application, support for complex class structures, binary
attachments, and a simple framework for creating additional serialization 
mechanisms.

This project uses lxml as it's XML API, providing full namespace support.
"""

SHORT_DESC="A transport and architecture agnostic rpc (de)serialization " \
           "library that focuses on making small, rpc-oriented messaging work."

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
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
    ],
    keywords=('soap', 'wsdl', 'wsgi', 'zeromq', 'rest', 'rpc','json'),
    author='Burak Arslan',
    author_email='burak-rpclib@arskom.com.tr',
    maintainer='Burak Arslan',
    maintainer_email='burak-rpclib@arskom.com.tr',
    url='http://github.com/arskom/rpclib',
    license='LGPL',
    zip_safe=False,
    install_requires=[
      'pytz',
      'lxml>=2.2.1',
    ],
    test_suite='tests.test_suite',
)
