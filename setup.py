#!/usr/bin/env python

import os
import re

from subprocess import call

from setuptools import setup
from setuptools import find_packages
from setuptools.command.test import test as TestCommand

from pkg_resources import resource_exists
from pkg_resources import resource_listdir


v = open(os.path.join(os.path.dirname(__file__), 'spyne', '__init__.py'), 'r')
VERSION = re.match(r".*__version__ = '(.*?)'", v.read(), re.S).group(1)

LONG_DESC = """Spyne aims to save the protocol implementers the hassle of
implementing their own remote procedure call api and the application programmers
the hassle of jumping through hoops just to expose their services using multiple
protocols and transports.
"""


try:
    os.stat('CHANGELOG.rst')
    LONG_DESC += "\n\n" + open('CHANGELOG.rst', 'r').read()
except OSError:
    pass


SHORT_DESC="""A transport and architecture agnostic rpc library that focuses on
exposing public services with a well-defined API."""


def call_test(cmd, tests):
    import spyne.test

    tests_dir = os.path.dirname(spyne.test.__file__)
    tests = ["%s/%s" % (tests_dir, test) for test in tests]
    ret = call(cmd + " " + ' '.join(tests), shell=True)

    if ret == 0:
        print tests, "OK"
    else:
        print tests, "FAIL"

    return ret


def call_pytest(*tests):
    return call_test("py.test -v --tb=short", tests)


def call_trial(*tests):
    return call_test("trial", tests)


class RunTests(TestCommand):
    def finalize_options(self):
        TestCommand.finalize_options(self)

        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        print "running tests"
        ret = 0
        ret = call_pytest('test_*', 'interface','model','protocol','wsdl') or ret
        ret = call_pytest('interop/test_httprpc.py') or ret
        ret = call_pytest('interop/test_soap_client_http.py') or ret
        ret = call_pytest('interop/test_soap_client_zeromq.py') or ret
        ret = call_pytest('interop/test_suds.py') or ret
        ret = call_trial('interop/test_soap_client_http_twisted.py') or ret
        raise SystemExit(ret)


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

    tests_require=['pytest'],
    cmdclass = {'test': RunTests},
)
