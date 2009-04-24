#!/usr/bin/env python

from setuptools import setup, find_packages
import sys

if sys.hexversion < 0x2050000:
   raise RuntimeError("Python 2.5 or higher required")


VERSION = '0.7.2'
LONG_DESC = """\
This is a simple, easily extendible soap library that provides several useful
tools for creating and publishing soap web services in python.  This package
features on-demand wsdl generation for the published services, a
wsgi-compliant web application, support for complex class structures, binary
attachments, simple framework for creating additional serialization mechanisms
and a client library.

This is a fork of the original project that uses lxml as it's XML API.
"""

setup(name='soaplib-lxml',
      version=VERSION,
      description="A simple library for writing soap web services",
      long_description=LONG_DESC,
      classifiers=[
          'Programming Language :: Python',
          'Operating System :: OS Independent',
          'Natural Language :: English',
          'Development Status :: 2 - Pre-Alpha',
          'Intended Audience :: Developers',
          'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
      ],
      keywords='soap',
      author='Aaron Bickell',
      author_email='abickell@optio.com',
      url='http://trac.optio.webfactional.com',
      license='LGPL',
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      zip_safe=False,
      install_requires=['pytz', 'lxml'],
      test_suite='tests.test_suite',
      entry_points="""
      """,
      )
