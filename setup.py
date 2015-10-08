#!/usr/bin/env python
#encoding: utf8

from __future__ import print_function

import os
import re
import sys
import inspect

from glob import glob
from itertools import chain
from os.path import join, dirname, abspath

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
except ImportError:
    RESET = ''
    GREEN = ''
    RED = ''

IS_PYPY = '__pypy__' in sys.builtin_module_names
OWN_PATH = abspath(inspect.getfile(inspect.currentframe()))
EXAMPLES_DIR = join(dirname(OWN_PATH), 'examples')

v = open(os.path.join(os.path.dirname(__file__), 'spyne', '__init__.py'), 'r')
VERSION = re.match(r".*__version__ = '(.*?)'", v.read(), re.S).group(1)

SHORT_DESC="""A transport and architecture agnostic rpc library that focuses on
exposing public services with a well-defined API."""

LONG_DESC = """Homepage: http://spyne.io

Spyne aims to save the protocol implementers the hassle of
implementing their own remote procedure call api and the application programmers
the hassle of jumping through hoops just to expose their services using multiple
protocols and transports.
"""

try:
    os.stat('CHANGELOG.rst')
    LONG_DESC += "\n\n" + open('CHANGELOG.rst', 'r').read()
except OSError:
    pass


###############################
# Testing stuff

def call_test(f, a, tests):
    import spyne.test
    from multiprocessing import Process, Queue

    tests_dir = os.path.dirname(spyne.test.__file__)
    a.extend(chain(*[glob(join(tests_dir, test)) for test in tests]))

    queue = Queue()
    p = Process(target=_wrapper(f), args=[a, queue])
    p.start()
    p.join()

    ret = queue.get()
    if ret == 0:
        print(tests, "OK")
    else:
        print(tests, "FAIL")

    return ret


def _wrapper(f):
    def _(args, queue):
        try:
            retval = f(args)
        except TypeError:  # it's a pain to call trial.
            sys.argv = ['trial']
            sys.argv.extend(args)
            retval = f()
        queue.put(retval)

    return _


def run_tests_and_create_report(report_name, *tests, **kwargs):
    import spyne.test
    import pytest

    if os.path.isfile(report_name):
        os.unlink(report_name)

    tests_dir = os.path.dirname(spyne.test.__file__)

    args = ['--twisted', '--tb=short', '--junitxml=%s' % report_name]
    args.extend('--{0}={1}'.format(k, v) for k, v in kwargs.items())
    args.extend(chain(*[glob("%s/%s" % (tests_dir, test)) for test in tests]))

    return pytest.main(args)


_ctr = 0


def call_pytest(*tests, **kwargs):
    global _ctr

    _ctr += 1
    file_name = 'test_result.%d.xml' % _ctr
    return run_tests_and_create_report(file_name, *tests, **kwargs)


def call_pytest_subprocess(*tests, **kwargs):
    global _ctr
    import pytest

    _ctr += 1
    file_name = 'test_result.%d.xml' % _ctr
    if os.path.isfile(file_name):
        os.unlink(file_name)
    args = ['--tb=line', '--junitxml=%s' % file_name]
    args.extend('--{0}={1}'.format(k, v) for k, v in kwargs.items())
    return call_test(pytest.main, args, tests)


class SubUnitTee(object):
    def __init__(self, name):
        self.name = name

    def __enter__(self):
        self.file = open(self.name, 'wb')
        self.stdout = sys.stdout
        self.stderr = sys.stderr
        sys.stdout = sys.stderr = self

    def __exit__(self, *args):
        sys.stdout = self.stdout
        sys.stderr = self.stderr
        print("CLOSED")
        self.file.close()

    def writelines(self, data):
        for d in data:
            self.write(data)
            self.write('\n')

    def write(self, data):
        if data.startswith("test:") \
                or data.startswith("successful:") \
                or data.startswith("error:") \
                or data.startswith("failure:") \
                or data.startswith("skip:") \
                or data.startswith("notsupported:"):
            self.file.write(data)
            if not data.endswith("\n"):
                self.file.write("\n")

        self.stdout.write(data)

    def read(self, d=0):
        return ''

    def flush(self):
        self.stdout.flush()
        self.stderr.flush()


class ExtendedTestCommand(TestCommand):
    """TestCommand customized to project needs."""

    user_options = TestCommand.user_options + [
        ('capture=', 'k', "py.test output capture control (see py.test "
                          "--capture)"),
    ]

    def initialize_options(self):
        TestCommand.initialize_options(self)
        self.capture = 'fd'

    def finalize_options(self):
        TestCommand.finalize_options(self)

        self.test_args = []
        self.test_suite = True


class RunTests(ExtendedTestCommand):
    def run_tests(self):
        print("Running tests")
        ret = 0
        tests = ['interface', 'model', 'multipython', 'protocol',
                          'test_null_server.py', 'test_service.py',
                          'test_soft_validation.py', 'test_util.py',
                          'test_sqlalchemy.py',
                          'test_sqlalchemy_deprecated.py',
                          'interop/test_pyramid.py',
                          'interop/test_soap_client_http_twisted.py',
                          'transport/test_msgpack.py']

        ret = call_pytest(*tests,capture=self.capture) or ret

        ret = call_pytest_subprocess('interop/test_httprpc.py',
                                     capture=self.capture) or ret
        ret = call_pytest_subprocess('interop/test_soap_client_http.py',
                                     capture=self.capture) or ret
        ret = call_pytest_subprocess('interop/test_soap_client_zeromq.py',
                                     capture=self.capture) or ret
        # excluding PyPy as it brokes here on LXML
        if not IS_PYPY:
            ret = call_pytest_subprocess('interop/test_suds.py',
                                     capture=self.capture) or ret

        if ret == 0:
            print(GREEN + "All that glisters is not gold." + RESET)
        else:
            print(RED + "Something is rotten in the state of Denmark." + RESET)

        raise SystemExit(ret)


class RunPython3Tests(TestCommand):
    """Run tests compatible with different python implementations. """

    def finalize_options(self):
        TestCommand.finalize_options(self)

        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        file_name = 'test_result_py3.xml'
        ret = run_tests_and_create_report(file_name,
                                          'multipython',
                                          'model/test_enum.py',
                                          'model/test_exception.py',
                                          'model/test_include.py',
                                          )

        if ret == 0:
            print(GREEN + "All Python 3 tests passed." + RESET)
        else:
            print(RED + "At one Python 3 test failed." + RESET)

        raise SystemExit(ret)


class SubUnitTee(object):
    def __init__(self, name):
        self.name = name
    def __enter__(self):
        self.file = open(self.name, 'wb')
        self.stdout = sys.stdout
        self.stderr = sys.stderr
        sys.stdout = sys.stderr = self

    def __exit__(self, *args):
        sys.stdout = self.stdout
        sys.stderr = self.stderr
        print("CLOSED")
        self.file.close()

    def writelines(self, data):
        for d in data:
            self.write(data)
            self.write('\n')

    def write(self, data):
        if data.startswith("test:") \
                or data.startswith("successful:") \
                or data.startswith("error:") \
                or data.startswith("failure:") \
                or data.startswith("skip:") \
                or data.startswith("notsupported:"):
            self.file.write(data)
            if not data.endswith("\n"):
                self.file.write("\n")

        self.stdout.write(data)

    def read(self,d=0):
        return ''

    def flush(self):
        self.stdout.flush()
        self.stderr.flush()

# Testing stuff ends here.
###############################

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
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: Implementation :: CPython',
        #'Programming Language :: Python :: Implementation :: Jython',
        'Programming Language :: Python :: Implementation :: PyPy',
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

    cmdclass = {
        'test': RunTests,
        'test_python3': RunPython3Tests
    },
)
