#!/usr/bin/env python
#encoding: utf8

import os
import re
import sys

from setuptools import setup
from setuptools import find_packages
from setuptools.command.test import test as TestCommand

try:
    import colorama
    colorama.init()
    from colorama import Fore
    RESET = Fore.RESET
    GREEN = Fore.GREEN
    RED = Fore.RED


except ImportError, e:
    RESET = ''
    GREEN = ''
    RED = ''


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


def call_test(f, a, tests):
    import spyne.test
    from glob import glob
    from itertools import chain
    from multiprocessing import Process, Queue

    tests_dir = os.path.dirname(spyne.test.__file__)
    a.extend(chain(*[glob("%s/%s" % (tests_dir, test)) for test in tests]))

    queue = Queue()
    p = Process(target=_wrapper(f), args=[a, queue])
    p.start()
    p.join()

    ret = queue.get()
    if ret == 0:
        print tests, "OK"
    else:
        print tests, "FAIL"

    return ret


def _wrapper(f):
    def _(args, queue):
        try:
            retval = f(args)
        except TypeError: # it's a pain to call trial.
            sys.argv = ['trial']
            sys.argv.extend(args)
            retval = f()
        queue.put(retval)
    return _


_ctr = 0

def call_pytest(*tests):
    global _ctr
    import pytest
    _ctr += 1
    file_name = 'test_result.%d.xml' % _ctr
    if os.path.isfile(file_name):
        os.unlink(file_name)
    return call_test(pytest.main, ['-v', '--tb=short', '--junitxml=%s' % file_name], tests)


def call_trial(*tests):
    from twisted.scripts.trial import usage
    from twisted.scripts.trial import Options
    from twisted.scripts.trial import _makeRunner
    from twisted.scripts.trial import _getSuite

    def run():
        config = Options()
        config.parseOptions()

        trialRunner = _makeRunner(config)
        suite = _getSuite(config)
        test_result = trialRunner.run(suite)

        return int(not test_result.wasSuccessful())

    return call_test(run, [], tests)


class RunTests(TestCommand):
    def finalize_options(self):
        TestCommand.finalize_options(self)

        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        print "running tests"
        ret = 0
        ret = call_pytest('interface', 'model', 'protocol',
                          'test_null_server.py', 'test_service.py',
                          'test_soft_validation.py', 'test_util.py') or ret
        ret = call_pytest('test_sqlalchemy.py') or ret
        ret = call_pytest('interop/test_httprpc.py') or ret
        ret = call_pytest('interop/test_soap_client_http.py') or ret
        ret = call_pytest('interop/test_soap_client_zeromq.py') or ret
        ret = call_pytest('interop/test_suds.py') or ret
        ret = call_trial('interop/test_soap_client_http_twisted.py') or ret
        ret = call_pytest('test_op_req_suffix.py') or ret

        if ret == 0:
            print GREEN + "All that glisters is not gold." + RESET
        else:
            print RED + "Something is rotten in the state of Denmark." + RESET

        raise SystemExit(ret)

test_reqs = [
    'pytest', 'werkzeug', 'sqlalchemy', 'suds',
    'pyparsing<1.99', 'lxml>=2.3', 'pyyaml', 'pyzmq',
    'twisted', 'colorama', 'msgpack-python', 'webtest',
    ]

setup(
    name='spyne',
    packages=find_packages(),

    version=VERSION,
    description=SHORT_DESC,
    long_description=LONG_DESC,
    classifiers=[
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Operating System :: OS Independent',
        'Natural Language :: English',
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
    ],
    keywords=('soap', 'wsdl', 'wsgi', 'zeromq', 'rest', 'rpc', 'json', 'http',
              'msgpack', 'xml', 'django', 'pyramid', 'postgresql', 'sqlalchemy',
              'werkzeug', 'twisted', 'yaml'),
    author='Burak Arslan',
    author_email='burak+spyne@arskom.com.tr',
    maintainer='Burak Arslan',
    maintainer_email='burak+spyne@arskom.com.tr',
    url='http://spyne.io',
    license='LGPL-2.1',
    zip_safe=False,
    install_requires=[
      'pytz',
    ],

    entry_points={
        'console_scripts': [
            'sort_wsdl=spyne.test.sort_wsdl:main',
        ]
    },

    tests_require = test_reqs,
    cmdclass = {'test': RunTests},
)
